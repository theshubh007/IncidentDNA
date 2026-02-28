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
        safe = query.strip().replace("'", "''")
        try:
            results = run_query(f"""
                SELECT SNOWFLAKE.CORTEX.SEARCH_PREVIEW(
                  'INCIDENTDNA.RAW.RUNBOOK_SEARCH',
                  '{safe}',
                  3
                ) AS results
            """)
            if results and results[0].get("RESULTS"):
                return str(results[0]["RESULTS"])
            return "No matching runbooks found."
        except Exception as e:
            return f"Runbook search error: {e}"
