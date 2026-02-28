"""
Quick test script — run this to verify the agent pipeline works end-to-end.
LLM: Snowflake Cortex llama3.1-70b (free, no external API key needed).

Levels of testing:
  python test_agent.py snowflake   → test Snowflake connection + Cortex LLM
  python test_agent.py agents      → full agent pipeline (Ag1 + Ag2 + Ag5)
  python test_agent.py full        → full pipeline including Composio actions
"""

import sys
import os
from dotenv import load_dotenv

load_dotenv()


# ── LEVEL 1: Snowflake connection ─────────────────────────────────────────────
def test_snowflake():
    print("\n[TEST] Checking Snowflake connection...")
    from utils.snowflake_conn import run_query

    try:
        rows = run_query("SELECT CURRENT_USER(), CURRENT_DATABASE(), CURRENT_WAREHOUSE()")
        print(f"  ✅ Connected: {rows[0]}")
    except Exception as e:
        print(f"  ❌ Snowflake connection failed: {e}")
        return False

    print("\n[TEST] Checking required tables exist...")
    tables = [
        ("RAW.RUNBOOKS",            "SELECT COUNT(*) AS n FROM RAW.RUNBOOKS"),
        ("RAW.PAST_INCIDENTS",      "SELECT COUNT(*) AS n FROM RAW.PAST_INCIDENTS"),
        ("RAW.SERVICE_DEPENDENCIES","SELECT COUNT(*) AS n FROM RAW.SERVICE_DEPENDENCIES"),
        ("AI.ANOMALY_EVENTS",       "SELECT COUNT(*) AS n FROM AI.ANOMALY_EVENTS"),
        ("AI.DECISIONS",            "SELECT COUNT(*) AS n FROM AI.DECISIONS"),
        ("AI.ACTIONS",              "SELECT COUNT(*) AS n FROM AI.ACTIONS"),
        ("AI.INCIDENT_HISTORY",     "SELECT COUNT(*) AS n FROM AI.INCIDENT_HISTORY"),
    ]
    all_ok = True
    for name, sql in tables:
        try:
            rows = run_query(sql)
            print(f"  ✅ {name} — {rows[0]['N']} rows")
        except Exception as e:
            print(f"  ❌ {name} — {e}")
            all_ok = False

    print("\n[TEST] Checking ANALYTICS.METRIC_DEVIATIONS dynamic table...")
    try:
        rows = run_query("SELECT * FROM ANALYTICS.METRIC_DEVIATIONS LIMIT 5")
        print(f"  ✅ METRIC_DEVIATIONS — {len(rows)} rows (dynamic table refreshing)")
        for r in rows:
            print(f"     service={r.get('SERVICE_NAME')} metric={r.get('METRIC_NAME')} z_score={r.get('Z_SCORE')}")
    except Exception as e:
        print(f"  ⚠️  METRIC_DEVIATIONS: {e} — run P1's 03_dynamic_tables.sql first")

    return all_ok


# ── LEVEL 2: Agent pipeline (uses Snowflake Cortex — no extra key needed) ────
def test_agents():
    print("\n[TEST] Running agent pipeline with a simulated incident...")
    print("       LLM: Snowflake Cortex llama3.1-70b (free)")
    from agents.manager import run_incident_crew

    test_event = {
        "event_id":    "test-001",
        "service":     "payment-service",
        "anomaly_type": "db_pool_exhaustion",
        "severity":    "P2",
        "details": {
            "deploy_id": "deploy_001",
            "simulated": True,
        },
    }

    try:
        result = run_incident_crew(test_event)
        print("\n[TEST] ✅ Pipeline completed!")
        print(f"  severity      : {result['severity']}")
        print(f"  root_cause    : {result['root_cause']}")
        print(f"  fix           : {result['fix']}")
        print(f"  confidence    : {result['confidence']}")
        print(f"  approved      : {result['approved']}")
        print(f"  debate_rounds : {result['debate_rounds']}")
        print(f"  slack         : {result['slack']}")
        print(f"  github        : {result['github']}")
        return True
    except Exception as e:
        print(f"\n[TEST] ❌ Pipeline failed: {e}")
        import traceback
        traceback.print_exc()
        return False


# ── LEVEL 3: Just Snowflake connection check (no agents) ─────────────────────
def test_tools_only():
    """Test individual tools without running full agents."""
    # Tools only need Snowflake connection (no external LLM key needed)

    print("\n[TEST] Testing search_runbooks tool...")
    from tools.search_runbooks import SearchRunbooksTool
    t = SearchRunbooksTool()
    result = t._run("database connection timeout high latency")
    print(f"  Result: {result[:300]}...")

    print("\n[TEST] Testing find_similar_incidents tool...")
    from tools.find_similar_incidents import FindSimilarIncidentsTool
    t2 = FindSimilarIncidentsTool()
    result2 = t2._run("payment-service database connection pool exhausted after deploy")
    print(f"  Result: {result2[:300]}...")

    print("\n[TEST] Testing query_snowflake tool...")
    from tools.query_snowflake import QuerySnowflakeTool
    t3 = QuerySnowflakeTool()
    result3 = t3._run("SELECT service_name, metric_name, z_score FROM ANALYTICS.METRIC_DEVIATIONS LIMIT 3")
    print(f"  Result: {result3}")


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "snowflake"

    print("=" * 60)
    print("  IncidentDNA — Agent Test")
    print(f"  Mode: {mode}")
    print("=" * 60)

    if mode == "snowflake":
        test_snowflake()
        print("\nNext: python test_agent.py agents   (uses Snowflake Cortex LLM - no extra key needed)")

    elif mode == "tools":
        test_snowflake()
        test_tools_only()

    elif mode in ("agents", "full"):
        ok = test_snowflake()
        if ok or mode == "full":
            test_agents()
    else:
        print("Usage: python test_agent.py [snowflake|tools|agents|full]")
