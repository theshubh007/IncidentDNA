"""
IncidentDNA Composio Trigger Listener
Listens for GitHub push events via Composio trigger and runs the incident pipeline.

Two modes:
  1. Composio webhook mode (production): Registers GITHUB_COMMIT_EVENT trigger
  2. Polling mode (fallback): Checks RAW.DEPLOY_EVENTS for unprocessed deploys
"""
import os
import sys
import time
import uuid
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.snowflake_conn import run_query, run_dml

load_dotenv()


def inject_synthetic_spike(service_name: str):
    """Inject synthetic metric spike to simulate incident"""
    print(f"[INGESTION] Injecting synthetic spike for {service_name}")

    run_dml("""
        INSERT INTO RAW.METRICS (service_name, metric_name, metric_value)
        VALUES
            (%s, 'error_rate', 0.25),
            (%s, 'latency_p99', 2500)
    """, (service_name, service_name))

    print(f"[INGESTION] Spike injected for {service_name}")


def check_for_anomalies(service_name: str) -> list:
    """Query ANALYTICS.METRIC_DEVIATIONS for anomalies"""
    print(f"[INGESTION] Checking for anomalies on {service_name}")

    anomalies = run_query("""
        SELECT
            service_name,
            metric_name,
            current_value,
            baseline_avg,
            z_score,
            severity
        FROM ANALYTICS.METRIC_DEVIATIONS
        WHERE service_name = %s
        ORDER BY ABS(z_score) DESC
        LIMIT 5
    """, (service_name,))

    return anomalies


def trigger_incident_pipeline(anomaly: dict):
    """Trigger CrewAI agent pipeline"""
    print(f"[INGESTION] Anomaly detected! Triggering incident pipeline...")
    print(f"  Service: {anomaly['SERVICE_NAME']}")
    print(f"  Metric: {anomaly['METRIC_NAME']}")
    print(f"  Z-Score: {anomaly['Z_SCORE']}")
    print(f"  Severity: {anomaly['SEVERITY']}")

    # Insert anomaly event
    run_dml("""
        INSERT INTO AI.ANOMALY_EVENTS (
            deploy_id,
            service_name,
            anomaly_type,
            severity,
            details,
            status
        ) VALUES (
            %s,
            %s,
            %s,
            %s,
            PARSE_JSON(%s),
            'NEW'
        )
    """, (
        'deploy_001',
        anomaly['SERVICE_NAME'],
        f"{anomaly['METRIC_NAME']}_spike",
        anomaly['SEVERITY'],
        f'{{"z_score": {anomaly["Z_SCORE"]}, "current_value": {anomaly["CURRENT_VALUE"]}, "baseline_avg": {anomaly["BASELINE_AVG"]}}}'
    ))

    print(f"[INGESTION] Anomaly event created in AI.ANOMALY_EVENTS")

    # Trigger the CrewAI agent pipeline
    try:
        from agents.manager import run_incident_crew
        event_payload = {
            "event_id": f"evt-{uuid.uuid4().hex[:8]}",
            "service": anomaly["SERVICE_NAME"],
            "anomaly_type": f"{anomaly['METRIC_NAME']}_spike",
            "severity": anomaly["SEVERITY"],
            "details": {
                "z_score": anomaly["Z_SCORE"],
                "current_value": anomaly["CURRENT_VALUE"],
                "baseline_avg": anomaly["BASELINE_AVG"],
            },
        }
        result = run_incident_crew(event_payload)
        print(f"[INGESTION] Pipeline completed: severity={result['severity']}, confidence={result['confidence']}")
    except Exception as e:
        print(f"[INGESTION] Pipeline error: {e}")


def handle_github_push(event):
    """Handle GitHub push event from Composio trigger"""
    print("\n" + "=" * 60)
    print("[COMPOSIO TRIGGER] GitHub push event received!")
    print("=" * 60)

    # Extract event data
    repo_name = event.get('repository', {}).get('name', 'unknown-service')
    commit_sha = event.get('after', 'unknown')[:7]
    pusher = event.get('pusher', {}).get('name', 'unknown')
    branch = event.get('ref', 'refs/heads/main').split('/')[-1]

    print(f"  Repository: {repo_name}")
    print(f"  Commit: {commit_sha}")
    print(f"  Pusher: {pusher}")
    print(f"  Branch: {branch}")

    # Step 1: Insert deploy event
    print(f"\n[STEP 1] Inserting deploy event into RAW.DEPLOY_EVENTS")
    run_dml("""
        INSERT INTO RAW.DEPLOY_EVENTS (
            event_id, service_name, commit_hash, author, branch
        ) VALUES (%s, %s, %s, %s, %s)
    """, (f"deploy_{commit_sha}", repo_name, commit_sha, pusher, branch))

    # Step 2: Inject synthetic spike
    print(f"\n[STEP 2] Injecting synthetic metric spike")
    inject_synthetic_spike(repo_name)

    # Step 3: Wait for dynamic table refresh
    print(f"\n[STEP 3] Waiting 35s for METRIC_DEVIATIONS dynamic table refresh...")
    time.sleep(35)

    # Step 4: Check for anomalies
    print(f"\n[STEP 4] Checking for anomalies")
    anomalies = check_for_anomalies(repo_name)

    if anomalies:
        print(f"  Found {len(anomalies)} anomalies")
        print(f"\n[STEP 5] Triggering incident pipeline")
        trigger_incident_pipeline(anomalies[0])
    else:
        print(f"  No anomalies detected (all metrics within 2 std dev)")

    print("\n" + "=" * 60)
    print("[COMPOSIO TRIGGER] Processing complete!")
    print("=" * 60 + "\n")


def start_composio_trigger():
    """Register Composio GITHUB_COMMIT_EVENT trigger and listen."""
    from composio import Composio

    composio_key = os.getenv("COMPOSIO_API_KEY")
    if not composio_key:
        print("[TRIGGER] No COMPOSIO_API_KEY set — falling back to polling mode")
        return False

    try:
        client = Composio(api_key=composio_key)

        # Register trigger for GitHub push events
        print("[TRIGGER] Registering GITHUB_COMMIT_EVENT trigger via Composio...")
        listener = client.triggers.subscribe(
            trigger_name="GITHUB_COMMIT_EVENT",
            user_id="pg-test-a6c32032-f3c5-43d2-9090-e16ffbd46f0d",
        )

        print("[TRIGGER] Composio trigger registered. Listening for GitHub push events...")

        @listener.callback
        def on_trigger(event_data):
            """Callback when GitHub push event fires"""
            print(f"[TRIGGER] Event received: {type(event_data)}")
            handle_github_push(event_data)

        listener.listen()  # blocks
        return True

    except Exception as e:
        print(f"[TRIGGER] Composio trigger registration failed: {e}")
        print("[TRIGGER] Falling back to polling mode")
        return False


def start_polling_mode():
    """Fallback: poll RAW.DEPLOY_EVENTS for unprocessed deploys."""
    print("[POLLING] Starting polling mode — checking for new deploys every 30s")
    seen_deploys = set()

    # Load already-processed deploys
    try:
        existing = run_query("SELECT event_id FROM RAW.DEPLOY_EVENTS")
        seen_deploys = {r["EVENT_ID"] for r in existing}
        print(f"[POLLING] {len(seen_deploys)} existing deploys tracked")
    except Exception:
        pass

    while True:
        try:
            deploys = run_query("""
                SELECT event_id, service_name, commit_hash, author, branch
                FROM RAW.DEPLOY_EVENTS
                ORDER BY deployed_at DESC
                LIMIT 10
            """)
            for deploy in deploys:
                eid = deploy["EVENT_ID"]
                if eid not in seen_deploys:
                    seen_deploys.add(eid)
                    print(f"[POLLING] New deploy detected: {eid}")
                    # Simulate a push event
                    handle_github_push({
                        "repository": {"name": deploy["SERVICE_NAME"]},
                        "after": deploy.get("COMMIT_HASH", "unknown"),
                        "pusher": {"name": deploy.get("AUTHOR", "unknown")},
                        "ref": f"refs/heads/{deploy.get('BRANCH', 'main')}",
                    })
        except Exception as e:
            print(f"[POLLING] Error: {e}")

        time.sleep(30)


def main():
    """Start listening for events — tries Composio trigger first, falls back to polling."""
    print("=" * 60)
    print("IncidentDNA Trigger Listener Starting...")
    print("=" * 60)

    github_repo = os.getenv("GITHUB_REPO", "unknown")
    print(f"Target repository: {github_repo}")

    # Try Composio trigger first
    if not start_composio_trigger():
        # Fallback to polling mode
        try:
            start_polling_mode()
        except KeyboardInterrupt:
            print("\n\nShutting down...")


if __name__ == "__main__":
    main()
