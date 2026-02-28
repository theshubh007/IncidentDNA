"""
Fetch historical data from CrewAI repository
- Past commits
- Past issues
- Past actions/workflows
"""
import os
from dotenv import load_dotenv
from composio import Composio

load_dotenv()

# Initialize Composio
composio = Composio()
session = composio.create(user_id="incidentdna_history")

# Get GitHub tools
github_tools = session.tools(toolkits=["github"])

print("="*60)
print("Fetching CrewAI Repository History")
print("="*60)

# Configuration
GITHUB_OWNER = os.getenv("GITHUB_OWNER", "joaomdmoura")
GITHUB_REPO = os.getenv("GITHUB_REPO", "crewAI")

print(f"\nTarget: {GITHUB_OWNER}/{GITHUB_REPO}\n")

# ============================================================
# 1. FETCH RECENT COMMITS
# ============================================================
print("[1] Fetching recent commits...")
try:
    # Use Composio's GitHub toolkit to get commits
    commits_tool = next((t for t in github_tools if "list_commits" in t.name.lower()), None)
    
    if commits_tool:
        result = commits_tool.execute({
            "owner": GITHUB_OWNER,
            "repo": GITHUB_REPO,
            "per_page": 10  # Last 10 commits
        })
        
        commits = result.get("data", [])
        print(f"  ✅ Found {len(commits)} recent commits:")
        for i, commit in enumerate(commits[:5], 1):
            sha = commit.get("sha", "")[:7]
            message = commit.get("commit", {}).get("message", "").split("\n")[0]
            author = commit.get("commit", {}).get("author", {}).get("name", "Unknown")
            date = commit.get("commit", {}).get("author", {}).get("date", "")
            print(f"     {i}. {sha} - {message[:50]}... by {author}")
    else:
        print("  ⚠️  Commits tool not found, using direct API call")
        
except Exception as e:
    print(f"  ❌ Error fetching commits: {e}")

# ============================================================
# 2. FETCH OPEN ISSUES
# ============================================================
print("\n[2] Fetching open issues...")
try:
    issues_tool = next((t for t in github_tools if "list_issues" in t.name.lower()), None)
    
    if issues_tool:
        result = issues_tool.execute({
            "owner": GITHUB_OWNER,
            "repo": GITHUB_REPO,
            "state": "open",
            "per_page": 10
        })
        
        issues = result.get("data", [])
        print(f"  ✅ Found {len(issues)} open issues:")
        for i, issue in enumerate(issues[:5], 1):
            number = issue.get("number")
            title = issue.get("title", "")
            labels = [l.get("name") for l in issue.get("labels", [])]
            print(f"     {i}. #{number} - {title[:50]}...")
            if labels:
                print(f"        Labels: {', '.join(labels)}")
    else:
        print("  ⚠️  Issues tool not found")
        
except Exception as e:
    print(f"  ❌ Error fetching issues: {e}")

# ============================================================
# 3. FETCH CLOSED ISSUES (for training data)
# ============================================================
print("\n[3] Fetching closed issues (for AI training)...")
try:
    if issues_tool:
        result = issues_tool.execute({
            "owner": GITHUB_OWNER,
            "repo": GITHUB_REPO,
            "state": "closed",
            "per_page": 10
        })
        
        closed_issues = result.get("data", [])
        print(f"  ✅ Found {len(closed_issues)} recently closed issues:")
        for i, issue in enumerate(closed_issues[:5], 1):
            number = issue.get("number")
            title = issue.get("title", "")
            closed_at = issue.get("closed_at", "")
            print(f"     {i}. #{number} - {title[:50]}... (closed: {closed_at[:10]})")
        
except Exception as e:
    print(f"  ❌ Error fetching closed issues: {e}")

# ============================================================
# 4. FETCH WORKFLOW RUNS (GitHub Actions)
# ============================================================
print("\n[4] Fetching GitHub Actions workflow runs...")
try:
    workflows_tool = next((t for t in github_tools if "workflow" in t.name.lower()), None)
    
    if workflows_tool:
        result = workflows_tool.execute({
            "owner": GITHUB_OWNER,
            "repo": GITHUB_REPO,
            "per_page": 10
        })
        
        runs = result.get("data", {}).get("workflow_runs", [])
        print(f"  ✅ Found {len(runs)} recent workflow runs:")
        for i, run in enumerate(runs[:5], 1):
            name = run.get("name", "")
            status = run.get("status", "")
            conclusion = run.get("conclusion", "")
            created = run.get("created_at", "")[:10]
            print(f"     {i}. {name} - {status}/{conclusion} ({created})")
    else:
        print("  ⚠️  Workflows tool not found")
        
except Exception as e:
    print(f"  ❌ Error fetching workflows: {e}")

# ============================================================
# 5. FETCH PULL REQUESTS
# ============================================================
print("\n[5] Fetching pull requests...")
try:
    pr_tool = next((t for t in github_tools if "pull" in t.name.lower() and "list" in t.name.lower()), None)
    
    if pr_tool:
        result = pr_tool.execute({
            "owner": GITHUB_OWNER,
            "repo": GITHUB_REPO,
            "state": "open",
            "per_page": 10
        })
        
        prs = result.get("data", [])
        print(f"  ✅ Found {len(prs)} open pull requests:")
        for i, pr in enumerate(prs[:5], 1):
            number = pr.get("number")
            title = pr.get("title", "")
            author = pr.get("user", {}).get("login", "Unknown")
            print(f"     {i}. #{number} - {title[:50]}... by {author}")
    else:
        print("  ⚠️  Pull requests tool not found")
        
except Exception as e:
    print(f"  ❌ Error fetching pull requests: {e}")

# ============================================================
# 6. SUMMARY
# ============================================================
print("\n" + "="*60)
print("SUMMARY")
print("="*60)
print(f"""
✅ You can access ALL historical data from {GITHUB_OWNER}/{GITHUB_REPO}:
   - Commits (all history)
   - Issues (open + closed)
   - Pull requests
   - GitHub Actions runs
   - Comments, reviews, etc.

💡 Use this data to:
   - Train your AI agents on past incidents
   - Analyze patterns in issues
   - Learn from closed issues (root causes + fixes)
   - Monitor CI/CD failures
   - Build incident knowledge base

📚 Next steps:
   1. Store this data in Snowflake (RAW.PAST_INCIDENTS)
   2. Use it for AI_SIMILARITY searches
   3. Train agents on real CrewAI incident patterns
""")
print("="*60)
