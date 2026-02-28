"""
Import CrewAI repository history into Snowflake
This populates your AI training data with real incidents
"""
import os
import json
from dotenv import load_dotenv
from composio import Composio
from utils.snowflake_conn import run_dml, run_query

load_dotenv()

# Initialize Composio
composio = Composio()
session = composio.create(user_id="incidentdna_import")
github_tools = session.tools(toolkits=["github"])

GITHUB_OWNER = os.getenv("GITHUB_OWNER", "joaomdmoura")
GITHUB_REPO = os.getenv("GITHUB_REPO", "crewAI")

print("="*60)
print(f"Importing {GITHUB_OWNER}/{GITHUB_REPO} History to Snowflake")
print("="*60)

# ============================================================
# 1. IMPORT CLOSED ISSUES AS PAST INCIDENTS
# ============================================================
print("\n[1] Importing closed issues as past incidents...")
try:
    issues_tool = next((t for t in github_tools if "list_issues" in t.name.lower()), None)
    
    if issues_tool:
        # Fetch closed issues
        result = issues_tool.execute({
            "owner": GITHUB_OWNER,
            "repo": GITHUB_REPO,
            "state": "closed",
            "per_page": 50  # Import last 50 closed issues
        })
        
        issues = result.get("data", [])
        imported_count = 0
        
        for issue in issues:
            # Extract issue data
            title = issue.get("title", "")
            body = issue.get("body", "")
            number = issue.get("number")
            closed_at = issue.get("closed_at")
            created_at = issue.get("created_at")
            labels = [l.get("name") for l in issue.get("labels", [])]
            
            # Skip if not a bug/incident
            if not any(label in ["bug", "incident", "error", "crash"] for label in labels):
                continue
            
            # Calculate MTTR (time to resolve)
            if created_at and closed_at:
                from datetime import datetime
                created = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                closed = datetime.fromisoformat(closed_at.replace("Z", "+00:00"))
                mttr_minutes = int((closed - created).total_seconds() / 60)
            else:
                mttr_minutes = None
            
            # Extract root cause and fix from body (simple heuristic)
            root_cause = title  # Use title as root cause
            fix_applied = body[:500] if body else "See issue for details"
            
            # Insert into Snowflake
            try:
                run_dml("""
                    INSERT INTO RAW.PAST_INCIDENTS (
                        title,
                        service_name,
                        root_cause,
                        fix_applied,
                        resolved_at,
                        mttr_minutes
                    ) VALUES (%s, %s, %s, %s, %s, %s)
                """, (
                    f"CrewAI Issue #{number}: {title}",
                    GITHUB_REPO,
                    root_cause,
                    fix_applied,
                    closed_at,
                    mttr_minutes
                ))
                imported_count += 1
                print(f"  ✅ Imported issue #{number}: {title[:50]}...")
            except Exception as e:
                print(f"  ⚠️  Skipped issue #{number} (duplicate or error): {e}")
        
        print(f"\n  📊 Imported {imported_count} issues as past incidents")
        
except Exception as e:
    print(f"  ❌ Error importing issues: {e}")

# ============================================================
# 2. IMPORT COMMITS AS DEPLOY EVENTS
# ============================================================
print("\n[2] Importing recent commits as deploy events...")
try:
    commits_tool = next((t for t in github_tools if "list_commits" in t.name.lower()), None)
    
    if commits_tool:
        result = commits_tool.execute({
            "owner": GITHUB_OWNER,
            "repo": GITHUB_REPO,
            "per_page": 20  # Last 20 commits
        })
        
        commits = result.get("data", [])
        imported_count = 0
        
        for commit in commits:
            sha = commit.get("sha", "")
            message = commit.get("commit", {}).get("message", "")
            author = commit.get("commit", {}).get("author", {}).get("name", "Unknown")
            date = commit.get("commit", {}).get("author", {}).get("date")
            
            # Insert into Snowflake
            try:
                run_dml("""
                    INSERT INTO RAW.DEPLOY_EVENTS (
                        event_id,
                        service_name,
                        commit_hash,
                        author,
                        branch,
                        deployed_at
                    ) VALUES (%s, %s, %s, %s, %s, %s)
                """, (
                    f"import_{sha[:7]}",
                    GITHUB_REPO,
                    sha[:7],
                    author,
                    "main",
                    date
                ))
                imported_count += 1
                print(f"  ✅ Imported commit {sha[:7]}: {message[:50]}...")
            except Exception as e:
                print(f"  ⚠️  Skipped commit {sha[:7]} (duplicate)")
        
        print(f"\n  📊 Imported {imported_count} commits as deploy events")
        
except Exception as e:
    print(f"  ❌ Error importing commits: {e}")

# ============================================================
# 3. VERIFY IMPORT
# ============================================================
print("\n[3] Verifying import...")
try:
    # Count past incidents
    result = run_query("SELECT COUNT(*) as cnt FROM RAW.PAST_INCIDENTS")
    incident_count = result[0]['CNT']
    print(f"  ✅ Total past incidents in Snowflake: {incident_count}")
    
    # Count deploy events
    result = run_query("SELECT COUNT(*) as cnt FROM RAW.DEPLOY_EVENTS")
    deploy_count = result[0]['CNT']
    print(f"  ✅ Total deploy events in Snowflake: {deploy_count}")
    
    # Show sample incident
    result = run_query("""
        SELECT title, root_cause, mttr_minutes 
        FROM RAW.PAST_INCIDENTS 
        WHERE service_name = %s
        LIMIT 1
    """, (GITHUB_REPO,))
    
    if result:
        sample = result[0]
        print(f"\n  📋 Sample incident:")
        print(f"     Title: {sample['TITLE']}")
        print(f"     Root Cause: {sample['ROOT_CAUSE'][:60]}...")
        print(f"     MTTR: {sample['MTTR_MINUTES']} minutes")
    
except Exception as e:
    print(f"  ❌ Error verifying: {e}")

# ============================================================
# 4. SUMMARY
# ============================================================
print("\n" + "="*60)
print("IMPORT COMPLETE")
print("="*60)
print(f"""
✅ Imported CrewAI repository history into Snowflake

Now your AI agents can:
   - Search past incidents using AI_SIMILARITY
   - Learn from real CrewAI bug fixes
   - Analyze patterns in closed issues
   - Use actual MTTR data for predictions

📊 Data available in:
   - RAW.PAST_INCIDENTS (closed issues)
   - RAW.DEPLOY_EVENTS (commits)

🧠 Next steps:
   1. Run agents/manager.py to test investigation
   2. Agents will use this data for root cause analysis
   3. Compare new incidents to historical patterns
""")
print("="*60)
