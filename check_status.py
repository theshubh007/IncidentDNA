"""Quick status check"""
import os
from dotenv import load_dotenv

load_dotenv()

print("="*60)
print("IncidentDNA Setup Status Check")
print("="*60)

# Check 1: Environment variables
print("\n[1] Environment Variables:")
required_vars = {
    "COMPOSIO_API_KEY": os.getenv("COMPOSIO_API_KEY"),
    "SNOWFLAKE_ACCOUNT": os.getenv("SNOWFLAKE_ACCOUNT"),
    "SNOWFLAKE_USER": os.getenv("SNOWFLAKE_USER"),
    "SNOWFLAKE_PASSWORD": os.getenv("SNOWFLAKE_PASSWORD"),
    "GITHUB_OWNER": os.getenv("GITHUB_OWNER"),
    "GITHUB_REPO": os.getenv("GITHUB_REPO"),
}

all_set = True
for key, value in required_vars.items():
    if value and not value.startswith("your_"):
        if "KEY" in key or "PASSWORD" in key:
            print(f"  ✅ {key}: {value[:10]}...")
        else:
            print(f"  ✅ {key}: {value}")
    else:
        print(f"  ❌ {key}: NOT SET")
        all_set = False

# Check 2: Composio
print("\n[2] Composio:")
try:
    from composio import Composio
    composio = Composio(api_key=os.getenv('COMPOSIO_API_KEY'))
    session = composio.create(user_id="status_check")
    print("  ✅ API Key valid")
    print("  ✅ Can create sessions")
except Exception as e:
    print(f"  ❌ Error: {e}")
    all_set = False

# Check 3: Snowflake (will test connection)
print("\n[3] Snowflake:")
try:
    from utils.snowflake_conn import get_connection
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT CURRENT_VERSION()")
    version = cur.fetchone()[0]
    print(f"  ✅ Connection successful")
    print(f"  ✅ Version: {version}")
    cur.close()
    conn.close()
except Exception as e:
    print(f"  ⚠️  Connection failed: {e}")
    print("  💡 Make sure you've run the SQL files in Snowflake")

# Check 4: Tables
print("\n[4] Snowflake Tables:")
try:
    from utils.snowflake_conn import run_query
    
    tables = [
        "RAW.DEPLOY_EVENTS",
        "RAW.METRICS",
        "RAW.RUNBOOKS",
        "AI.ANOMALY_EVENTS",
        "ANALYTICS.METRIC_BASELINES"
    ]
    
    for table in tables:
        try:
            result = run_query(f"SELECT COUNT(*) as cnt FROM {table}")
            count = result[0]['CNT']
            print(f"  ✅ {table}: {count} rows")
        except Exception as e:
            print(f"  ❌ {table}: NOT FOUND")
            print(f"     Run: snowflake/01_schema.sql")
            break
            
except Exception as e:
    print(f"  ⚠️  Cannot check tables (Snowflake not connected)")

# Summary
print("\n" + "="*60)
if all_set:
    print("✅ READY TO RUN!")
    print("\nNext steps:")
    print("  1. Run Snowflake SQL files (if not done)")
    print("  2. python test_setup.py")
    print("  3. python ingestion/trigger_listener.py")
else:
    print("⚠️  SETUP INCOMPLETE")
    print("\nPlease complete the steps above")
print("="*60)
