import json
import re

from crewai.tools import BaseTool
from utils.snowflake_conn import run_query


class SearchRunbooksTool(BaseTool):
    name: str = "search_runbooks"
    description: str = (
        "Search the runbook knowledge base using Cortex vector search. "
        "Input a natural language description of the symptoms or anomaly. "
        "Returns the top 3 most relevant runbooks with title, symptom, root_cause, and fix_steps. "
        "Example input: 'database connection timeout high latency payment service'"
    )

    def _fallback_search(self, query: str) -> str:
        rows = run_query(
            """SELECT title, service_name, symptom, root_cause, fix_steps
                 FROM RAW.RUNBOOKS"""
        )
        terms = [
            term
            for term in re.findall(r"[a-z0-9]+", query.lower())
            if len(term) > 2
        ]

        scored_rows = []
        for row in rows:
            haystack = " ".join(
                str(row.get(field, "")).lower()
                for field in ("TITLE", "SERVICE_NAME", "SYMPTOM", "ROOT_CAUSE", "FIX_STEPS")
            )
            score = sum(1 for term in terms if term in haystack)
            if score:
                scored_rows.append((score, row))

        if scored_rows:
            scored_rows.sort(key=lambda item: item[0], reverse=True)
            return str([row for _, row in scored_rows[:3]])

        return "No matching runbooks found."

    def _run(self, query: str) -> str:
        try:
            payload = json.dumps({
                "query": query.strip(),
                "columns": ["title", "service_name", "symptom", "root_cause", "fix_steps"],
                "limit": 3,
            })
            results = run_query(
                """SELECT SNOWFLAKE.CORTEX.SEARCH_PREVIEW(
                  'INCIDENTDNA.RAW.RUNBOOK_SEARCH',
                  %s
                ) AS results""",
                (payload,),
            )
            if results and results[0].get("RESULTS"):
                return str(results[0]["RESULTS"])
            return self._fallback_search(query)
        except Exception as e:
            try:
                return self._fallback_search(query)
            except Exception as fallback_error:
                return f"Runbook search error: {e}; fallback failed: {fallback_error}"
