"""
ci_watcher.py — IncidentDNA CI Failure Monitor
===============================================
Runs continuously in the background.
Polls GitHub API every 30s for failed workflow runs on theshubh007/IncidentDNA.
When a NEW failure is detected → triggers the IncidentDNA incident pipeline.

Demo mode (no Snowflake): prints the full agent pipeline simulation.
Live mode (Snowflake available): calls run_incident_crew() with real agents.

Run:
    python ci_watcher.py                  # normal (30s poll interval)
    python ci_watcher.py --interval 10    # faster polling
    python ci_watcher.py --demo           # force demo mode (no Snowflake)
"""

import json
import os
import sys
import time
import uuid
import urllib.request
import textwrap
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ── Config ────────────────────────────────────────────────────────────────────
REPO_OWNER   = "theshubh007"
REPO_NAME    = "FortressAI_AI_Agent_Security_Platform"
POLL_SECONDS = int(next((sys.argv[sys.argv.index("--interval") + 1]
                         for _ in [1] if "--interval" in sys.argv), 30))
FORCE_DEMO   = "--demo" in sys.argv
DEMO_LOGS    = Path(__file__).parent / "demo_logs"

# ── Helpers ───────────────────────────────────────────────────────────────────

def W(n=70): return "=" * n
def D(n=70): return "-" * n
def ts(): return datetime.now().strftime("%H:%M:%S")

def _github_get(path: str) -> dict:
    """Hit GitHub REST API (public repo — no token needed)."""
    url = f"https://api.github.com{path}"
    req = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": "IncidentDNA-CI-Watcher/1.0",
    })
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        return {"error": str(e)}


def _fetch_recent_runs() -> list:
    """Return the 10 most recent workflow runs (any status)."""
    data = _github_get(f"/repos/{REPO_OWNER}/{REPO_NAME}/actions/runs?per_page=10")
    if "error" in data:
        print(f"  [WATCHER] GitHub API error: {data['error']}")
        return []
    return data.get("workflow_runs", [])


def _snowflake_available() -> bool:
    """Quick check — can we connect to Snowflake?"""
    if FORCE_DEMO:
        return False
    try:
        from utils.snowflake_conn import get_connection
        conn = get_connection()
        conn.close()
        return True
    except Exception:
        return False


# ── Demo pipeline output (no Snowflake) ───────────────────────────────────────

def _run_demo_pipeline(run: dict):
    """Print full agent pipeline simulation for a CI failure."""
    workflow  = run.get("name", "CI")
    sha       = run.get("head_sha", "unknown")[:7]
    branch    = run.get("head_branch", "main")
    html_url  = run.get("html_url", "")
    conclusion = run.get("conclusion", "failure")

    print()
    print(W())
    print(f"  ⚡ CI FAILURE DETECTED — IncidentDNA Pipeline Activated")
    print(W())
    print()
    print(f"  Workflow  : {workflow}")
    print(f"  Watching  : github.com/{REPO_OWNER}/{REPO_NAME}")
    print(f"  Branch    : {branch}")
    print(f"  Commit    : {sha}")
    print(f"  Conclusion: {conclusion.upper()}")
    print(f"  URL       : {html_url}")
    print()
    time.sleep(0.5)

    # Immediate Slack alert (before agents run)
    print(f"  [{ts()}]  ⚡ Immediate Slack alert fired  →  #incidents")
    print(f"           '⚠️ CI failed on {branch} ({sha}) — IncidentDNA investigating...'")
    time.sleep(0.6)
    print()

    # Agent pipeline
    print(D())
    print(f"  Ag1 — Detector")
    print(D())
    time.sleep(0.5)
    print(f"  [{ts()}]  Ag1 querying ANALYTICS.METRIC_DEVIATIONS for {REPO_NAME}...")
    time.sleep(0.8)
    print(f"  [{ts()}]  Ag1 querying service dependency graph...")
    time.sleep(0.6)
    print()
    print(f"  Severity   : P2")
    print(f"  Type       : CI_FAILURE (build broken on main)")
    print(f"  Blast Radius: 0 downstream services (build-time failure — not runtime)")
    time.sleep(0.5)
    print()

    print(D())
    print(f"  Ag2 — Investigator")
    print(D())
    time.sleep(0.5)
    print(f"  [{ts()}]  Ag2 searching RAW.RUNBOOKS — 'CI failure {REPO_NAME}'...")
    time.sleep(0.8)
    print(f"  [{ts()}]  Ag2 finding similar past CI failures (CORTEX.SIMILARITY)...")
    time.sleep(0.8)
    print(f"  [{ts()}]  Ag2 querying recent deploy events + metric deviations...")
    time.sleep(0.8)
    print()

    root_cause_lines = textwrap.wrap(
        f"GitHub Actions workflow '{workflow}' failed on commit {sha} (branch: {branch}). "
        "Analysis of recent changes: FortressAI/broker/db_pool.py introduced a "
        "@with_db_retry decorator that holds DB connections during exponential backoff sleeps. "
        "Under load, 20 concurrent requests each holding a connection for 7s exhausted "
        "the pool (max=20). CI tests exposed the race condition via integration test "
        "test_pool_under_concurrent_load — 3 retries × 7s = 21s timeout exceeded.",
        width=66,
    )
    print("  Root Cause:")
    for line in root_cause_lines:
        print(f"    {line}")
        time.sleep(0.04)
    print()
    print(f"  Confidence : 85%")
    print(f"  Evidence   : runbook, past_incident, metrics")
    print()
    print(f"  Recommended Fix:")
    print(f"    Option 1 → Fix @with_db_retry to release connection before sleep")
    print(f"    Commands:")
    print(f"      $ git revert {sha}")
    print(f"      $ git push origin {branch}")
    print(f"    Risk: LOW  |  Est. time: 5 minutes")
    time.sleep(0.8)
    print()

    print(D())
    print(f"  Ag5 — Validator (Adversarial Review)")
    print(D())
    time.sleep(0.5)
    print(f"  [{ts()}]  Ag5 stress-testing Ag2's hypothesis...")
    time.sleep(0.8)
    print(f"  [{ts()}]  Ag5 checking alternative causes...")
    time.sleep(0.8)
    print()
    print(f"  Verdict    : APPROVED ✅")
    print(f"  Confidence : 85%  (no stronger alternative explanation found)")
    time.sleep(0.5)
    print()

    # Threshold engine
    print(W())
    print(f"  THRESHOLD ENGINE")
    print(W())
    time.sleep(0.3)
    print(f"  [RULE 1]  SECURITY or DATA_INTEGRITY?  →  No")
    time.sleep(0.3)
    print(f"  [RULE 2]  Validator APPROVED?           →  Yes")
    time.sleep(0.3)
    print(f"  [RULE 3]  Blast radius ≤ 2?             →  Yes  (0 services)")
    time.sleep(0.3)
    print(f"  [RULE 4]  Confidence ≥ 90%, risk LOW?   →  No  (risk=HIGH for CI failures)")
    time.sleep(0.3)
    print(f"  [RULE 5]  Confidence ≥ 75%?             →  Yes  →  🔴 HUMAN_ESCALATION")
    time.sleep(0.4)
    print()
    print(f"  DECISION   : 🔴 HUMAN_ESCALATION")
    print(f"  Rule       : RULE_5  (CI failures always escalate — never auto-resolve)")
    print(f"  Urgency    : HIGH_CONFIDENCE")
    print()
    print(W())
    time.sleep(0.6)

    # Actions
    print()
    print(f"  [{ts()}]  GitHub issue created  →  {REPO_OWNER}/{REPO_NAME}")
    time.sleep(0.5)
    print(f"  [{ts()}]  Slack Block Kit alert posted  →  #incidents")
    print(f"           '🔴 CI FAILURE — {REPO_NAME} | Root cause found | Fix ready'")
    time.sleep(0.5)
    print(f"  [{ts()}]  AI.INCIDENT_HISTORY record written")
    print()
    print(f"  MTTR  : ~2 min 30s")
    print(f"  Human average for CI triage: ~20 minutes")
    print(f"  Speedup: ~8x faster  💨")
    print()
    print(W())
    print(f"  ✅ CI failure handled — human alerted with full context + fix commands")
    print(W())
    print()


# ── Live pipeline (Snowflake available) ───────────────────────────────────────

def _run_live_pipeline(run: dict):
    """Call run_incident_crew() with real agents."""
    from agents.manager import run_incident_crew

    workflow   = run.get("name", "CI")
    sha        = run.get("head_sha", "unknown")[:7]
    branch     = run.get("head_branch", "main")
    html_url   = run.get("html_url", "")
    conclusion = run.get("conclusion", "failure")

    event_payload = {
        "event_id":    f"ci-{uuid.uuid4().hex[:8]}",
        "service":     REPO_NAME,
        "anomaly_type": "ci_failure",
        "severity":    "P2",
        "details": {
            "workflow":           workflow,
            "conclusion":         conclusion,
            "branch":             branch,
            "commit_sha":         sha,
            "run_url":            html_url,
            "approved_override":  True,
            "confidence_override": 0.85,
            "risk_level_override": "HIGH",
            "blast_radius_override": 0,
        },
    }

    print(f"\n[CI WATCHER] Triggering live agent pipeline for run {run.get('id')}...")
    result = run_incident_crew(event_payload)
    print(f"[CI WATCHER] Pipeline done — decision={result.get('threshold_decision')} slack={result.get('slack')}")


# ── Main loop ─────────────────────────────────────────────────────────────────

def main():
    seen_run_ids: set = set()
    live_mode = _snowflake_available()

    print()
    print(W())
    print("  IncidentDNA — CI Failure Watcher")
    print(W())
    print(f"  Watching  : github.com/{REPO_OWNER}/{REPO_NAME}")
    print(f"  Poll      : every {POLL_SECONDS}s")
    print(f"  Mode      : {'LIVE (Snowflake connected)' if live_mode else 'DEMO (pre-recorded pipeline)'}")
    print(f"  Started   : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(W())
    print()

    # Seed seen_run_ids with current runs so we don't fire on old failures at startup
    print(f"  [{ts()}]  Seeding known run IDs (ignoring pre-existing failures)...")
    for run in _fetch_recent_runs():
        seen_run_ids.add(run["id"])
    print(f"  [{ts()}]  Tracking {len(seen_run_ids)} existing runs. Watching for NEW failures...")
    print()

    while True:
        try:
            runs = _fetch_recent_runs()
            for run in runs:
                run_id     = run.get("id")
                status     = run.get("status", "")
                conclusion = run.get("conclusion", "")

                # Only process completed, failed runs we haven't seen yet
                if run_id in seen_run_ids:
                    continue
                seen_run_ids.add(run_id)

                if status != "completed":
                    continue

                if conclusion in ("failure", "timed_out", "action_required"):
                    print(f"\n  [{ts()}]  🔴 NEW CI FAILURE detected!")
                    print(f"          Workflow : {run.get('name')}")
                    print(f"          Commit   : {run.get('head_sha', '')[:7]}")
                    print(f"          Branch   : {run.get('head_branch')}")
                    print(f"          Conclusion: {conclusion}")

                    if live_mode:
                        _run_live_pipeline(run)
                    else:
                        _run_demo_pipeline(run)

                elif conclusion == "success":
                    print(f"  [{ts()}]  ✅ CI passed — {run.get('name')} on {run.get('head_branch')} ({run.get('head_sha','')[:7]})")

        except KeyboardInterrupt:
            print("\n\n  [CI WATCHER] Stopped.")
            sys.exit(0)
        except Exception as e:
            print(f"  [{ts()}]  [CI WATCHER] Error: {e}")

        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
