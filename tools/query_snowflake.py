from crewai.tools import BaseTool
from utils.snowflake_conn import run_query


class QuerySnowflakeTool(BaseTool):
    name: str = "query_snowflake"
    description: str = (
        "Run a SELECT query against Snowflake and return results as a string. "
        "Input must be a valid SQL SELECT statement. Only SELECT is allowed. "
        "Example: SELECT metric_name, current_value FROM ANALYTICS.METRIC_DEVIATIONS WHERE service='payment-service' LIMIT 10"
    )

    def _run(self, sql: str) -> str:
        sql = sql.strip()
        upper = sql.upper()
        if not (upper.startswith("SELECT") or upper.startswith("WITH")):
            return "Error: only SELECT queries (and CTEs) are allowed."
        if ";" in sql:
            return "Error: multi-statement queries are not allowed."
        try:
            rows = run_query(sql)
            if not rows:
                return "Query returned 0 rows."
            return str(rows[:20])  # cap at 20 rows to avoid LLM context overflow
        except Exception as e:
            return f"Query error: {e}"
