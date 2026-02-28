"""
IncidentDNA Composio Trigger Listener
Listens for GitHub commits and triggers the incident pipeline
"""
import os
import sys
from dotenv import load_dotenv
from composio import Composio

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.snowflake_conn import run_query, run_dml

load_dotenv()

# Initialize Composio with user session
composio = Composio()
session = composio.create(user_id="incidentdna_system")

def inject_synthetic_spike(service_name: str):
    """Inject synthetic metric spike to simulate incident"""
    print(f"[INGESTION] Injecting synthetic spike for {service_name}")
    
    # Insert spike metrics
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
    """Trigger CrewAI agent pipeline (Person 2's code)"""
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
        'deploy_001',  # Link to deploy event
        anomaly['SERVICE_NAME'],
        f"{anomaly['METRIC_NAME']}_spike",
        anomaly['SEVERITY'],
        f'{{"z_score": {anomaly["Z_SCORE"]}, "current_value": {anomaly["CURRENT_VALUE"]}, "baseline_avg": {anomaly["BASELINE_AVG"]}}}'
    ))
    
    # TODO: Person 2 will implement this
    # from agents.manager import run_pipeline
    # run_pipeline(anomaly_payload)
    
    print(f"[INGESTION] Anomaly event created in AI.ANOMALY_EVENTS")

def handle_github_push(event):
    """Handle GitHub push event from Composio"""
    print("\n" + "="*60)
    print("[COMPOSIO TRIGGER] GitHub push event received!")
    print("="*60)
    
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
            event_id,
            service_name,
            commit_hash,
            author,
            branch
        ) VALUES (%s, %s, %s, %s, %s)
    """, (
        f"deploy_{commit_sha}",
        repo_name,
        commit_sha,
        pusher,
        branch
    ))
    print(f"  ✓ Deploy event created: deploy_{commit_sha}")
    
    # Step 2: Inject synthetic spike
    print(f"\n[STEP 2] Injecting synthetic metric spike")
    inject_synthetic_spike(repo_name)
    print(f"  ✓ Spike injected")
    
    # Step 3: Check for anomalies
    print(f"\n[STEP 3] Checking for anomalies")
    anomalies = check_for_anomalies(repo_name)
    
    if anomalies:
        print(f"  ✓ Found {len(anomalies)} anomalies")
        
        # Step 4: Trigger incident pipeline for highest severity anomaly
        print(f"\n[STEP 4] Triggering incident pipeline")
        trigger_incident_pipeline(anomalies[0])
        print(f"  ✓ Pipeline triggered")
    else:
        print(f"  ℹ No anomalies detected (all metrics within 2 std dev)")
    
    print("\n" + "="*60)
    print("[COMPOSIO TRIGGER] Processing complete!")
    print("="*60 + "\n")

def main():
    """Start listening for Composio triggers"""
    print("="*60)
    print("IncidentDNA Trigger Listener Starting...")
    print("="*60)
    print(f"Listening for GitHub push events via Composio")
    print(f"Press Ctrl+C to stop\n")
    
    github_owner = os.getenv("GITHUB_OWNER")
    github_repo = os.getenv("GITHUB_REPO")
    
    print(f"Target repository: {github_owner}/{github_repo}")
    print(f"✓ Composio session created")
    print("Waiting for GitHub push events...\n")
    
    # Note: In production, you would use Composio triggers
    # For now, use the simulation script: python test_crewai_trigger.py
    print("💡 To test the system, run:")
    print("   python test_crewai_trigger.py")
    print("\nThis will simulate a GitHub push event and trigger the full pipeline.")
    print("\nPress Ctrl+C to exit...")
    
    try:
        import time
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\nShutting down...")

if __name__ == "__main__":
    main()
