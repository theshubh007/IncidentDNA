"""Snowflake connection utilities for IncidentDNA"""
import os
import snowflake.connector
from dotenv import load_dotenv

load_dotenv()

def get_connection():
    """Get Snowflake connection with credentials from .env"""
    return snowflake.connector.connect(
        account=os.getenv("SNOWFLAKE_ACCOUNT"),
        user=os.getenv("SNOWFLAKE_USER"),
        password=os.getenv("SNOWFLAKE_PASSWORD"),
        database=os.getenv("SNOWFLAKE_DATABASE", "INCIDENTDNA"),
        schema=os.getenv("SNOWFLAKE_SCHEMA", "AI"),
        warehouse=os.getenv("SNOWFLAKE_WAREHOUSE", "COMPUTE_WH"),
        role=os.getenv("SNOWFLAKE_ROLE", "ACCOUNTADMIN"),
    )

def run_query(sql: str, params: tuple = None) -> list[dict]:
    """Execute SELECT query and return results as list of dicts"""
    conn = get_connection()
    cur = conn.cursor(snowflake.connector.DictCursor)
    try:
        cur.execute(sql, params or ())
        return cur.fetchall()
    finally:
        cur.close()
        conn.close()

def run_dml(sql: str, params: tuple = None):
    """Execute INSERT/UPDATE/DELETE and commit"""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(sql, params or ())
        conn.commit()
    finally:
        cur.close()
        conn.close()
