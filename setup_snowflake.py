"""
Automated Snowflake Setup Script
Runs all SQL files in the correct order
"""
import os
from dotenv import load_dotenv
from utils.snowflake_conn import get_connection

load_dotenv()

def run_sql_file(conn, filepath, description):
    """Execute a SQL file"""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"File: {filepath}")
    print('='*60)

    # Read SQL file
    with open(filepath, 'r') as f:
        sql_content = f.read()

    # Remove comments and split by semicolon
    lines = []
    for line in sql_content.split('\n'):
        # Skip comment lines
        if line.strip().startswith('--'):
            continue
        lines.append(line)

    sql_clean = '\n'.join(lines)

    # Split by semicolon but keep multi-line statements together
    statements = []
    current = []
    for line in sql_clean.split('\n'):
        current.append(line)
        if line.strip().endswith(';'):
            stmt = '\n'.join(current).strip()
            if stmt:
                statements.append(stmt)
            current = []

    # Add any remaining statement
    if current:
        stmt = '\n'.join(current).strip()
        if stmt and not stmt.startswith('--'):
            statements.append(stmt)

    cur = conn.cursor()
    success_count = 0

    for i, statement in enumerate(statements, 1):
        if not statement or len(statement) < 5:
            continue

        try:
            print(f"  [{i}/{len(statements)}] Executing...")
            cur.execute(statement)
            success_count += 1
            print(f"  ✅ Success")
        except Exception as e:
            error_msg = str(e)
            if "already exists" in error_msg.lower():
                print(f"  ⚠️  Already exists (skipping)")
                success_count += 1
            else:
                print(f"  ❌ Error: {e}")

    cur.close()
    print(f"✅ Completed: {description} ({success_count}/{len(statements)} successful)")

def main():
    print("="*60)
    print("IncidentDNA Snowflake Setup")
    print("="*60)
    print("\nThis script will:")
    print("  1. Create database INCIDENTDNA")
    print("  2. Create all schemas (RAW, CURATED, AI, ANALYTICS, APP)")
    print("  3. Create all tables (13 tables)")
    print("  4. Insert seed data")
    print("  5. Create dynamic tables (METRIC_DEVIATIONS, BLAST_RADIUS, MTTR_METRICS)")
    print("  6. Create Cortex Search Service")
    print("  7. Create Stream (ANOMALY_STREAM)")
    print("  8. Create Tasks (INVESTIGATE_TASK, RESOLUTION_CHECK_TASK)")
    print("  9. Create AI_SENTIMENT view")
    print()

    # Connect to Snowflake
    print("Connecting to Snowflake...")
    try:
        conn = get_connection()
        print("✅ Connected successfully")
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print("\nCheck your .env file:")
        print("  - SNOWFLAKE_ACCOUNT")
        print("  - SNOWFLAKE_USER")
        print("  - SNOWFLAKE_PASSWORD")
        return

    try:
        # Step 0: Create database and warehouse
        print("\n" + "="*60)
        print("Step 0: Creating database and warehouse")
        print("="*60)
        cur = conn.cursor()

        # Create database
        cur.execute("CREATE DATABASE IF NOT EXISTS INCIDENTDNA")
        cur.execute("USE DATABASE INCIDENTDNA")
        print("✅ Database INCIDENTDNA ready")

        # Check if warehouse exists, create if not
        try:
            cur.execute("USE WAREHOUSE COMPUTE_WH")
            print("✅ Warehouse COMPUTE_WH selected")
        except:
            print("⚠️  COMPUTE_WH not found, creating it...")
            try:
                cur.execute("""
                    CREATE WAREHOUSE IF NOT EXISTS COMPUTE_WH
                    WITH WAREHOUSE_SIZE = 'XSMALL'
                    AUTO_SUSPEND = 60
                    AUTO_RESUME = TRUE
                """)
                cur.execute("USE WAREHOUSE COMPUTE_WH")
                print("✅ Warehouse COMPUTE_WH created and selected")
            except Exception as e:
                print(f"❌ Could not create warehouse: {e}")
                print("   Using default warehouse from connection")

        cur.close()

        # Step 1: Schema
        run_sql_file(
            conn,
            "snowflake/01_schema.sql",
            "Step 1: Creating schemas and tables (RAW, CURATED, AI, ANALYTICS, APP)"
        )

        # Step 2: Seed data
        run_sql_file(
            conn,
            "snowflake/02_seed_data.sql",
            "Step 2: Inserting seed data"
        )

        # Step 3: Dynamic tables, streams, tasks
        run_sql_file(
            conn,
            "snowflake/03_dynamic_tables.sql",
            "Step 3: Creating dynamic tables, Cortex Search, streams, and tasks"
        )

        # Verify
        print("\n" + "="*60)
        print("Verification")
        print("="*60)

        cur = conn.cursor()

        # Check schemas
        print("\nChecking schemas:")
        for schema in ["RAW", "CURATED", "AI", "ANALYTICS", "APP"]:
            try:
                cur.execute(f"SHOW TABLES IN SCHEMA {schema}")
                print(f"  ✅ {schema}: exists")
            except Exception as e:
                print(f"  ❌ {schema}: {e}")

        # Check tables
        tables = [
            "RAW.DEPLOY_EVENTS",
            "RAW.METRICS",
            "RAW.RUNBOOKS",
            "RAW.PAST_INCIDENTS",
            "RAW.SERVICE_DEPENDENCIES",
            "RAW.SLACK_MESSAGES",
            "CURATED.ENRICHED_DEPLOYS",
            "AI.ANOMALY_EVENTS",
            "AI.DECISIONS",
            "AI.ACTIONS",
            "AI.INCIDENT_HISTORY",
            "AI.PENDING_INVESTIGATIONS",
            "ANALYTICS.METRIC_BASELINES",
            "APP.DASHBOARD_STATE",
        ]

        print("\nChecking tables:")
        for table in tables:
            try:
                cur.execute(f"SELECT COUNT(*) FROM {table}")
                count = cur.fetchone()[0]
                print(f"  ✅ {table}: {count} rows")
            except Exception as e:
                print(f"  ❌ {table}: {e}")

        # Check dynamic tables
        print("\nChecking dynamic tables:")
        for dt in ["ANALYTICS.METRIC_DEVIATIONS", "ANALYTICS.BLAST_RADIUS", "ANALYTICS.MTTR_METRICS"]:
            try:
                cur.execute(f"SELECT COUNT(*) FROM {dt}")
                count = cur.fetchone()[0]
                print(f"  ✅ {dt}: {count} rows")
            except Exception as e:
                print(f"  ⚠️  {dt}: {e}")

        # Check stream
        print("\nChecking stream:")
        try:
            cur.execute("SHOW STREAMS IN SCHEMA AI")
            result = cur.fetchall()
            if result:
                print(f"  ✅ AI.ANOMALY_STREAM: exists ({len(result)} stream(s))")
            else:
                print(f"  ⚠️  No streams found")
        except Exception as e:
            print(f"  ⚠️  Streams: {e}")

        # Check tasks
        print("\nChecking tasks:")
        try:
            cur.execute("SHOW TASKS IN SCHEMA AI")
            result = cur.fetchall()
            if result:
                print(f"  ✅ AI tasks: {len(result)} task(s)")
                for row in result:
                    print(f"     - {row[1]}: state={row[10] if len(row) > 10 else 'unknown'}")
            else:
                print(f"  ⚠️  No tasks found")
        except Exception as e:
            print(f"  ⚠️  Tasks: {e}")

        # Check Cortex Search
        print("\nChecking Cortex Search:")
        try:
            cur.execute("SHOW CORTEX SEARCH SERVICES IN SCHEMA RAW")
            result = cur.fetchall()
            if result:
                print(f"  ✅ RAW.RUNBOOK_SEARCH: Service exists")
            else:
                print(f"  ⚠️  RAW.RUNBOOK_SEARCH: Not found")
        except Exception as e:
            print(f"  ⚠️  RAW.RUNBOOK_SEARCH: {e}")

        # Check sentiment view
        print("\nChecking AI_SENTIMENT view:")
        try:
            cur.execute("SELECT COUNT(*) FROM ANALYTICS.SLACK_SENTIMENT")
            count = cur.fetchone()[0]
            print(f"  ✅ ANALYTICS.SLACK_SENTIMENT: {count} messages analyzed")
        except Exception as e:
            print(f"  ⚠️  ANALYTICS.SLACK_SENTIMENT: {e}")

        cur.close()

        # Success!
        print("\n" + "="*60)
        print("✅ SNOWFLAKE SETUP COMPLETE!")
        print("="*60)
        print("\nCreated:")
        print("  - 5 schemas (RAW, CURATED, AI, ANALYTICS, APP)")
        print("  - 13 tables")
        print("  - 3 dynamic tables (METRIC_DEVIATIONS, BLAST_RADIUS, MTTR_METRICS)")
        print("  - 1 stream (ANOMALY_STREAM)")
        print("  - 2 tasks (INVESTIGATE_TASK, RESOLUTION_CHECK_TASK)")
        print("  - 1 Cortex Search (RUNBOOK_SEARCH)")
        print("  - 1 AI_SENTIMENT view (SLACK_SENTIMENT)")
        print("\nNext steps:")
        print("  1. Run: python test_setup.py")
        print("  2. Run: python -m uvicorn api:app --reload")
        print("  3. Run: cd dashboard && npm run dev")
        print()

    except Exception as e:
        print(f"\n❌ Setup failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()
        print("\nConnection closed.")

if __name__ == "__main__":
    main()
