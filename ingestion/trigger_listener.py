"""
Composio Trigger Listener for IncidentDNA
==========================================
WebSocket listener for GitHub commits and Slack messages.
Inserts deploy event → injects spike → checks for anomaly → calls agent pipeline.

Usage:
  python ingestion/trigger_listener.py          # Listen for real events
  python ingestion/trigger_listener.py --demo   # Run a demo simulation
"""

import os
import sys
import uuid
import json
import time
import argparse
import snowflake.connector
from dotenv import load_dotenv

# Add parent dir to path so we can import agents/utils
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.snowflake_conn import get_connection, run_dml, run_query, close_connection

load_dotenv()


# ── Snowflake helpers ────────────────────────────────────────────────

def insert_deploy_event(deploy_id: str, service: str, version: str, deployed_by: str, diff: str):
    """Record a deploy event in RAW.DEPLOY_EVENTS."""
    run_dml(
        """
        INSERT INTO RAW.DEPLOY_EVENTS (deploy_id, service, version, deployed_by, diff_summary)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (deploy_id, service, version, deployed_by, diff),
    )
    print(f"[TRIGGER] Deploy recorded: {deploy_id} → {service} {version}")


def inject_metric_spike(service: str):
    """Simulate a post-deploy error rate spike in Snowflake metrics."""
    conn = get_connection()
    cur = None
    try:
        cur = conn.cursor()
        cur.executemany(
            "INSERT INTO RAW.METRICS (service, metric_name, metric_value) VALUES (%s, %s, %s)",
            [
                (service, "error_rate", 0.22),    # spike: normal is ~0.02
                (service, "latency_p99", 2100),    # spike: normal is ~200ms
            ],
        )
        conn.commit()
    finally:
        if cur:
            cur.close()
    print(f"[TRIGGER] Injected metric spike for {service}")


def check_anomaly(service: str) -> dict | None:
    """Poll ANALYTICS.METRIC_DEVIATIONS for this service."""
    print(f"[TRIGGER] Waiting 35s for dynamic table refresh...")
    time.sleep(35)  # wait for dynamic table to refresh (30s lag)
    rows = run_query(
        """
        SELECT service, metric_name, current_value, z_score, severity
        FROM ANALYTICS.METRIC_DEVIATIONS
        WHERE service = %s
        ORDER BY z_score DESC
        LIMIT 1
        """,
        (service,),
    )
    return rows[0] if rows else None


# ── GitHub commit handler ────────────────────────────────────────────

def handle_github_commit(payload: dict):
    """Process a GitHub commit event through the full pipeline."""
    repo = payload.get("repository", {}).get("name", "unknown-service")
    sha = payload.get("after", uuid.uuid4().hex)[:8]
    pusher = payload.get("pusher", {}).get("name", "unknown")
    message = payload.get("head_commit", {}).get("message", "")

    deploy_id = f"deploy-{sha}"
    service = repo  # map repo name to service name

    print(f"\n[TRIGGER] GitHub commit on {repo} by {pusher} — {sha}")

    # 1. Record deploy
    insert_deploy_event(deploy_id, service, f"sha-{sha}", pusher, message)

    # 2. Inject spike to simulate post-deploy anomaly
    inject_metric_spike(service)

    # 3. Wait and check for anomaly
    anomaly = check_anomaly(service)
    if not anomaly:
        print(f"[TRIGGER] No anomaly detected for {service} — pipeline skipped")
        return

    # 4. Call agent pipeline
    from agents.manager import run_incident_crew

    event = {
        "event_id": f"evt-{sha}-{int(time.time())}",
        "service": service,
        "anomaly_type": f"post_deploy_{anomaly['METRIC_NAME']}",
        "severity": anomaly["SEVERITY"],
        "details": {
            "deploy_id": deploy_id,
            "metric_name": anomaly["METRIC_NAME"],
            "current_value": anomaly["CURRENT_VALUE"],
            "z_score": anomaly["Z_SCORE"],
        },
    }
    print(f"[TRIGGER] Anomaly detected — starting agent pipeline for {event['event_id']}")
    result = run_incident_crew(event)
    print(f"[TRIGGER] Pipeline done: {result}")


# ── Slack message handler ────────────────────────────────────────────

def handle_slack_message(payload: dict):
    """Process a Slack message that looks like an incident report."""
    text = payload.get("text", "").lower()
    keywords = ["incident", "down", "outage", "error", "spike", "alert", "p1", "p2"]
    if not any(kw in text for kw in keywords):
        return

    from agents.manager import run_incident_crew

    ts = payload.get("ts", str(time.time())).replace(".", "")[:12]
    event = {
        "event_id": f"slack-{ts}",
        "service": "unknown",
        "anomaly_type": "slack_report",
        "severity": "P2",
        "details": {
            "channel": payload.get("channel"),
            "user": payload.get("user"),
            "text": payload.get("text"),
        },
    }
    print(f"[TRIGGER] Slack incident message → {event['event_id']}")
    result = run_incident_crew(event)
    print(f"[TRIGGER] Pipeline done: {result}")


# ── Demo mode ────────────────────────────────────────────────────────

def run_demo():
    """Run a demo simulation without Composio (for testing)."""
    print("\n" + "=" * 60)
    print("  IncidentDNA — Demo Trigger Simulation")
    print("=" * 60)

    fake_payload = {
        "repository": {"name": "payment-service"},
        "after": uuid.uuid4().hex,
        "pusher": {"name": "demo-user"},
        "head_commit": {"message": "fix: update connection pool settings"},
    }

    print(f"\n[DEMO] Simulating GitHub commit event...")
    print(f"  Repo: {fake_payload['repository']['name']}")
    print(f"  SHA:  {fake_payload['after'][:8]}")
    print(f"  By:   {fake_payload['pusher']['name']}")

    try:
        handle_github_commit(fake_payload)
    except Exception as e:
        print(f"\n[DEMO] Pipeline error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        close_connection()


# ── Composio listeners ───────────────────────────────────────────────

def start_listener():
    """Start Composio WebSocket listener for GitHub + Slack events."""
    api_key = os.getenv("COMPOSIO_API_KEY")
    if not api_key or api_key == "your_composio_api_key":
        print("❌ COMPOSIO_API_KEY not set. Run: python scripts/setup_composio.py")
        print("   Or use --demo mode: python ingestion/trigger_listener.py --demo")
        sys.exit(1)

    try:
        from composio import Composio, Trigger
    except ImportError:
        print("❌ Composio not installed. Run: pip install composio")
        sys.exit(1)

    client = Composio(api_key=api_key)

    @client.trigger(Trigger.GITHUB_COMMIT_EVENT)
    def on_github_commit(event):
        try:
            handle_github_commit(event.payload)
        except Exception as e:
            print(f"[TRIGGER] Error handling GitHub commit: {e}")

    @client.trigger(Trigger.SLACK_RECEIVE_MESSAGE)
    def on_slack_message(event):
        try:
            handle_slack_message(event.payload)
        except Exception as e:
            print(f"[TRIGGER] Error handling Slack message: {e}")

    print("[TRIGGER LISTENER] Waiting for GitHub commits and Slack messages...")
    print("  Press Ctrl+C to stop")
    try:
        client.listen()
    except KeyboardInterrupt:
        print("\n[TRIGGER] Shutting down...")
    finally:
        close_connection()


# ── Main ─────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="IncidentDNA Trigger Listener")
    parser.add_argument("--demo", action="store_true", help="Run a demo simulation without Composio")
    args = parser.parse_args()

    if args.demo:
        run_demo()
    else:
        start_listener()


if __name__ == "__main__":
    main()
