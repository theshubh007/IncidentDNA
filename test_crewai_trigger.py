"""
Test script to simulate a CrewAI commit without waiting for real events
"""
from ingestion.trigger_listener import handle_github_push

print("=" * 60)
print("Testing CrewAI Trigger (Simulation)")
print("=" * 60)
print()

# Simulate a CrewAI repository push event
fake_event = {
    "repository": {
        "name": "crewAI",
        "full_name": "joaomdmoura/crewAI"
    },
    "after": "abc1234567890",
    "pusher": {
        "name": "test-user"
    },
    "ref": "refs/heads/main",
    "head_commit": {
        "message": "Test commit for IncidentDNA demo",
        "author": {
            "name": "Test User",
            "email": "test@example.com"
        }
    }
}

print("Simulating GitHub push event...")
print(f"  Repository: {fake_event['repository']['full_name']}")
print(f"  Commit: {fake_event['after'][:7]}")
print(f"  Message: {fake_event['head_commit']['message']}")
print()

# Trigger the handler
handle_github_push(fake_event)

print()
print("=" * 60)
print("Test Complete!")
print("=" * 60)
print()
print("Check Snowflake to verify:")
print("  SELECT * FROM RAW.DEPLOY_EVENTS ORDER BY deployed_at DESC LIMIT 1;")
print("  SELECT * FROM AI.ANOMALY_EVENTS ORDER BY detected_at DESC LIMIT 1;")
print()
