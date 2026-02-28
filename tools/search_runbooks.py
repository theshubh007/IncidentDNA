import json

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
            return "No matching runbooks found."
        except Exception as e:
            return f"Runbook search error: {e}"
