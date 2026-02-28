# Demo Setup: Monitor CrewAI Repo with Composio Triggers

## Goal
Monitor the official CrewAI GitHub repo (`joaomdmoura/crewAI`) for new commits, and when detected, trigger your IncidentDNA pipeline to create GitHub issues and Slack alerts.

## Step-by-Step Setup

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Environment
```bash
cp .env.example .env
```

Edit `.env`:
```bash
# Snowflake (already configured)
SNOWFLAKE_ACCOUNT=sfsehol-llama_lounge_hackathon_sudhag
SNOWFLAKE_USER=USER
SNOWFLAKE_PASSWORD=sn0wf@ll
SNOWFLAKE_DATABASE=INCIDENTDNA
SNOWFLAKE_SCHEMA=AI
SNOWFLAKE_WAREHOUSE=COMPUTE_WH
SNOWFLAKE_ROLE=ACCOUNTADMIN

# Composio (get from https://app.composio.dev)
COMPOSIO_API_KEY=your_actual_composio_api_key

# Demo: Monitor CrewAI repo
GITHUB_OWNER=joaomdmoura
GITHUB_REPO=crewAI

# Slack (your channel)
SLACK_CHANNEL=#incidents
```

### 3. Authenticate with Composio
```bash
# Login to Composio
composio login

# Connect GitHub (will open browser for OAuth)
composio add github

# Connect Slack (will open browser for OAuth)
composio add slack

# Verify connections
composio connected-accounts
```

### 4. Run Snowflake Setup
```sql
-- In Snowflake, run these in order:
@snowflake/01_schema.sql
@snowflake/02_seed_data.sql
@snowflake/03_dynamic_tables.sql

-- Verify it works:
SELECT * FROM ANALYTICS.METRIC_DEVIATIONS;
SELECT COUNT(*) FROM RAW.RUNBOOKS;
```

### 5. Start the Trigger Listener
```bash
python ingestion/trigger_listener.py
```

You should see:
```
============================================================
IncidentDNA Trigger Listener Starting...
============================================================
Listening for GitHub push events via Composio
Press Ctrl+C to stop

✓ Subscribed to GitHub push events (trigger_id: xxx)
Waiting for events...
```

## What Happens Next

### When CrewAI Repo Gets a New Commit:

```
1. Composio detects push event on joaomdmoura/crewAI
         ↓
2. trigger_listener.py receives event
         ↓
3. Inserts deploy event into RAW.DEPLOY_EVENTS
         ↓
4. Injects synthetic metric spike into RAW.METRICS
         ↓
5. Queries ANALYTICS.METRIC_DEVIATIONS for anomalies
         ↓
6. If anomaly detected:
   - Creates entry in AI.ANOMALY_EVENTS
   - Triggers CrewAI agent pipeline (Person 2's code)
   - Agents investigate and create GitHub issue
   - Posts Slack alert
```

## Demo Flow (What You'll Show)

### Before Demo:
1. Have trigger listener running
2. Have Snowflake query open: `SELECT * FROM AI.ANOMALY_EVENTS ORDER BY detected_at DESC LIMIT 5;`
3. Have Slack channel open
4. Have GitHub issues page open

### During Demo:
1. **Show trigger listener running** (terminal output)
2. **Wait for CrewAI repo commit** (or simulate one)
3. **Show real-time detection:**
   - Terminal shows: "GitHub push event received!"
   - Terminal shows: "Anomaly detected! Triggering pipeline..."
4. **Show Snowflake data:**
   - Query `AI.ANOMALY_EVENTS` - new row appears
   - Query `AI.DECISIONS` - agent reasoning logged
   - Query `AI.ACTIONS` - Slack/GitHub actions logged
5. **Show Slack alert** - formatted incident alert appears
6. **Show GitHub issue** - auto-created issue with incident details

## Alternative: Use Your Own Repo

If you want to control the timing (instead of waiting for CrewAI commits):

1. Fork the CrewAI repo or use your own repo
2. Update `.env`:
   ```bash
   GITHUB_OWNER=your-username
   GITHUB_REPO=your-repo-name
   ```
3. Push a test commit to trigger the pipeline

## Troubleshooting

**Issue:** "No trigger events received"
- Check Composio dashboard: https://app.composio.dev/triggers
- Verify webhook is active
- Check GitHub repo has webhooks enabled

**Issue:** "Authentication failed"
- Run `composio login` again
- Run `composio add github` and `composio add slack` again
- Check `composio connected-accounts` shows both

**Issue:** "Anomaly not detected"
- Check `ANALYTICS.METRIC_DEVIATIONS` has data
- Verify baselines exist in `ANALYTICS.METRIC_BASELINES`
- Lower the z-score threshold in `03_dynamic_tables.sql` (change `>= 2` to `>= 1`)

## Quick Test (Without Waiting for Real Commits)

```python
# test_trigger.py
from ingestion.trigger_listener import handle_github_push

# Simulate a GitHub push event
fake_event = {
    "repository": {"name": "crewAI"},
    "after": "abc1234",
    "pusher": {"name": "test-user"},
    "ref": "refs/heads/main"
}

handle_github_push(fake_event)
```

Run: `python test_trigger.py`

This will trigger the full pipeline without waiting for a real commit.
