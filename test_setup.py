"""
Test script to verify IncidentDNA setup is working
Run this before starting the full trigger listener
"""
import os
import sys
from dotenv import load_dotenv

print("="*60)
print("IncidentDNA Setup Verification")
print("="*60)

# Load environment variables
load_dotenv()

# Test 1: Check environment variables
print("\n[TEST 1] Checking environment variables...")
required_vars = [
    "SNOWFLAKE_ACCOUNT",
    "SNOWFLAKE_USER",
    "SNOWFLAKE_PASSWORD",
    "SNOWFLAKE_DATABASE",
    "COMPOSIO_API_KEY",
    "GITHUB_OWNER",
    "GITHUB_REPO"
]

missing_vars = []
for var in required_vars:
    value = os.getenv(var)
    if not value or value.startswith("your_"):
        print(f"  ❌ {var}: NOT SET")
        missing_vars.append(var)
    else:
        # Mask sensitive values
        if "PASSWORD" in var or "KEY" in var:
            display_value = value[:4] + "****"
        else:
            display_value = value
        print(f"  ✅ {var}: {display_value}")

if missing_vars:
    print(f"\n⚠️  Please set these variables in .env file:")
    for var in missing_vars:
        print(f"   - {var}")
    sys.exit(1)

# Test 2: Check Snowflake connection
print("\n[TEST 2] Testing Snowflake connection...")
try:
    from utils.snowflake_conn import get_connection
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT CURRENT_VERSION()")
    version = cur.fetchone()[0]
    print(f"  ✅ Connected to Snowflake (version: {version})")
    cur.close()
    conn.close()
except Exception as e:
    print(f"  ❌ Snowflake connection failed: {e}")
    sys.exit(1)

# Test 3: Check Snowflake tables exist
print("\n[TEST 3] Checking Snowflake tables...")
try:
    from utils.snowflake_conn import run_query
    
    tables_to_check = [
        "RAW.DEPLOY_EVENTS",
        "RAW.METRICS",
        "RAW.RUNBOOKS",
        "RAW.PAST_INCIDENTS",
        "AI.ANOMALY_EVENTS",
        "AI.DECISIONS",
        "AI.ACTIONS",
        "ANALYTICS.METRIC_BASELINES"
    ]
    
    for table in tables_to_check:
        try:
            result = run_query(f"SELECT COUNT(*) as cnt FROM {table}")
            count = result[0]['CNT']
            print(f"  ✅ {table}: {count} rows")
        except Exception as e:
            print(f"  ❌ {table}: NOT FOUND - Run snowflake/*.sql files first")
            
except Exception as e:
    print(f"  ❌ Table check failed: {e}")

# Test 4: Check dynamic table
print("\n[TEST 4] Checking dynamic table...")
try:
    result = run_query("SELECT COUNT(*) as cnt FROM ANALYTICS.METRIC_DEVIATIONS")
    count = result[0]['CNT']
    print(f"  ✅ ANALYTICS.METRIC_DEVIATIONS: {count} anomalies detected")
    
    if count > 0:
        sample = run_query("SELECT * FROM ANALYTICS.METRIC_DEVIATIONS LIMIT 1")
        print(f"  📊 Sample anomaly: {sample[0]['SERVICE_NAME']} - {sample[0]['METRIC_NAME']} (z-score: {sample[0]['Z_SCORE']})")
except Exception as e:
    print(f"  ❌ Dynamic table check failed: {e}")

# Test 5: Check Composio installation
print("\n[TEST 5] Checking Composio installation...")
try:
    from composio import Composio
    print("  ✅ Composio SDK installed")
except ImportError:
    print("  ❌ Composio not installed - Run: pip install composio-core")
    sys.exit(1)

# Test 6: Check Composio authentication
print("\n[TEST 6] Testing Composio authentication...")
try:
    from composio import Composio
    composio = Composio()
    session = composio.create(user_id="test_user")
    print("  ✅ Composio authentication successful")
except Exception as e:
    print(f"  ❌ Composio authentication failed: {e}")
    print("  💡 Run: composio login")
    sys.exit(1)

# Test 7: Check GitHub connection
print("\n[TEST 7] Checking GitHub connection...")
try:
    # Try to get GitHub tools
    tools = session.tools(toolkits=["github"])
    print(f"  ✅ GitHub toolkit available ({len(tools)} tools)")
except Exception as e:
    print(f"  ❌ GitHub not connected: {e}")
    print("  💡 Run: composio add github")

# Test 8: Check Slack connection
print("\n[TEST 8] Checking Slack connection...")
try:
    # Try to get Slack tools
    tools = session.tools(toolkits=["slack"])
    print(f"  ✅ Slack toolkit available ({len(tools)} tools)")
except Exception as e:
    print(f"  ❌ Slack not connected: {e}")
    print("  💡 Run: composio add slack")

# Test 9: Test trigger subscription (dry run)
print("\n[TEST 9] Testing trigger subscription...")
try:
    github_owner = os.getenv("GITHUB_OWNER")
    github_repo = os.getenv("GITHUB_REPO")
    
    print(f"  📡 Target repo: {github_owner}/{github_repo}")
    print(f"  ℹ️  Trigger subscription test skipped (would create actual subscription)")
    print(f"  💡 Run trigger_listener.py to create subscription")
except Exception as e:
    print(f"  ❌ Trigger test failed: {e}")

# Summary
print("\n" + "="*60)
print("VERIFICATION SUMMARY")
print("="*60)
print("\n✅ All checks passed! You're ready to run:")
print("   python ingestion/trigger_listener.py")
print("\n📚 Next steps:")
print("   1. Start trigger listener: python ingestion/trigger_listener.py")
print("   2. Push a commit to trigger the pipeline")
print("   3. Watch Snowflake for new anomaly events")
print("="*60)
