import os
import threading
import snowflake.connector
from dotenv import load_dotenv

load_dotenv()

# Thread-local connection pool
_local = threading.local()
_lock = threading.Lock()


def get_connection():
    """Get a thread-local Snowflake connection (reused within same thread)."""
    if not hasattr(_local, 'conn') or _local.conn is None or _local.conn.is_closed():
        _local.conn = snowflake.connector.connect(
            account=os.getenv("SNOWFLAKE_ACCOUNT"),
            user=os.getenv("SNOWFLAKE_USER"),
            password=os.getenv("SNOWFLAKE_PASSWORD"),
            database=os.getenv("SNOWFLAKE_DATABASE", "INCIDENTDNA"),
            warehouse=os.getenv("SNOWFLAKE_WAREHOUSE", "COMPUTE_WH"),
            role=os.getenv("SNOWFLAKE_ROLE", "ACCOUNTADMIN"),
        )
    return _local.conn


def get_new_connection():
    """Get a fresh Snowflake connection (not pooled)."""
    return snowflake.connector.connect(
        account=os.getenv("SNOWFLAKE_ACCOUNT"),
        user=os.getenv("SNOWFLAKE_USER"),
        password=os.getenv("SNOWFLAKE_PASSWORD"),
        database=os.getenv("SNOWFLAKE_DATABASE", "INCIDENTDNA"),
        warehouse=os.getenv("SNOWFLAKE_WAREHOUSE", "COMPUTE_WH"),
        role=os.getenv("SNOWFLAKE_ROLE", "ACCOUNTADMIN"),
    )


def run_query(sql: str, params: tuple = None) -> list[dict]:
    """Run a SELECT and return rows as list of dicts."""
    conn = get_connection()
    cur = None
    try:
        cur = conn.cursor(snowflake.connector.DictCursor)
        cur.execute(sql, params or ())
        return cur.fetchall()
    finally:
        if cur:
            cur.close()


def run_dml(sql: str, params: tuple = None) -> None:
    """Run an INSERT / UPDATE / DELETE and commit."""
    conn = get_connection()
    cur = None
    try:
        cur = conn.cursor()
        cur.execute(sql, params or ())
        conn.commit()
    finally:
        if cur:
            cur.close()


def close_connection() -> None:
    """Close the thread-local connection if it exists."""
    if hasattr(_local, 'conn') and _local.conn is not None:
        try:
            _local.conn.close()
        except Exception:
            pass
        _local.conn = None
