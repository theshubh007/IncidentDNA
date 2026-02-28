from crewai.tools import BaseTool
from utils.snowflake_conn import run_query


class FindSimilarIncidentsTool(BaseTool):
    name: str = "find_similar_incidents"
    description: str = (
        "Find past resolved incidents that are semantically similar to the current anomaly. "
        "Uses Snowflake Cortex AI_SIMILARITY to rank past incidents by relevance. "
        "Input a description of the current anomaly or service and symptoms. "
        "Returns title, root_cause, fix_applied, service, mttr_minutes, and similarity_score "
        "for the top matches. "
        "Example input: 'payment-service database connection pool exhausted after deploy'"
    )

    def _run(self, incident_description: str) -> str:
        try:
            # Primary: Cortex AI_SIMILARITY for semantic search
            results = run_query(
                """SELECT
                    title,
                    root_cause,
                    fix_applied,
                    service_name,
                    mttr_minutes,
                    SNOWFLAKE.CORTEX.SIMILARITY(
                        title || ' ' || root_cause,
                        %s
                    ) AS similarity_score
                FROM RAW.PAST_INCIDENTS
                ORDER BY similarity_score DESC
                LIMIT 5""",
                (incident_description,),
            )
            if results:
                return str(results)
        except Exception:
            # Fallback: keyword LIKE search if AI_SIMILARITY unavailable
            pass

        try:
            words = [w for w in incident_description.strip().split() if len(w) > 3][:3]
            keyword = words[0] if words else incident_description.split()[0]
            results = run_query(
                """SELECT
                    title,
                    root_cause,
                    fix_applied,
                    service_name,
                    mttr_minutes
                FROM RAW.PAST_INCIDENTS
                WHERE LOWER(title || ' ' || root_cause) LIKE %s
                ORDER BY mttr_minutes ASC
                LIMIT 5""",
                (f"%{keyword.lower()}%",),
            )
            if not results:
                results = run_query(
                    """SELECT title, root_cause, fix_applied, service_name, mttr_minutes
                    FROM RAW.PAST_INCIDENTS
                    ORDER BY mttr_minutes ASC
                    LIMIT 3""",
                )
            if not results:
                return "No similar past incidents found."
            return str(results)
        except Exception as e:
            return f"Similarity search error: {e}"
