from crewai.tools import BaseTool
from utils.snowflake_conn import run_query


class FindSimilarIncidentsTool(BaseTool):
    name: str = "find_similar_incidents"
    description: str = (
        "Find past resolved incidents that are semantically similar to the current anomaly. "
        "Uses Snowflake Cortex SIMILARITY to rank past incidents by relevance. "
        "Input a description of the current anomaly or service and symptoms. "
        "Returns title, root_cause, fix_applied, service, and mttr_minutes for top matches. "
        "Example input: 'payment-service database connection pool exhausted after deploy'"
    )

    def _run(self, incident_description: str) -> str:
        safe = incident_description.strip().replace("'", "''")
        try:
            results = run_query(f"""
                SELECT
                    title,
                    root_cause,
                    fix_applied,
                    service,
                    mttr_minutes,
                    ROUND(
                        SNOWFLAKE.CORTEX.SIMILARITY(
                            '{safe}',
                            title || ' ' || root_cause
                        ), 3
                    ) AS similarity_score
                FROM RAW.PAST_INCIDENTS
                ORDER BY similarity_score DESC
                LIMIT 3
            """)
            if not results:
                return "No similar past incidents found."
            return str(results)
        except Exception as e:
            return f"Similarity search error: {e}"
