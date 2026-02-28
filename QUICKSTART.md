# IncidentDNA - Quick Start Guide

## Setup

### 1. Activate the Virtual Environment (Python 3.11)

```bash
source .venv/bin/activate
python --version  # Must show Python 3.11
```

> ⚠️ Do NOT use the system `python3` (3.9) — it is incompatible with crewai/litellm.

### 2. Install / Update Dependencies
```bash
uv pip install -r requirements.txt
```

---

## Manual Setup (Step-by-Step)

### 2. Configure Environment
```bash
cp .env.example .env
```

Edit `.env` and add your `COMPOSIO_API_KEY`:
```bash
# Get your API key from: https://app.composio.dev
COMPOSIO_API_KEY=your_actual_api_key_here
```

### 3. Authenticate with Composio
```bash
# Login (opens browser)
composio login

# Connect GitHub (opens browser)
composio add github

# Connect Slack (opens browser)
composio add slack

# Verify connections
composio connected-accounts
```

### 4. Setup Snowflake

Login to Snowflake:
- URL: https://sfsehol-llama_lounge_hackathon_sudhag.snowflakecomputing.com
- User: `USER`
- Password: `sn0wf@ll`
- Database: `INCIDENTDNA`

Run these SQL files in order:
```sql
-- 1. Create schemas and tables
@snowflake/01_schema.sql

-- 2. Seed test data
@snowflake/02_seed_data.sql

-- 3. Create dynamic tables and Cortex Search
@snowflake/03_dynamic_tables.sql
```

Verify it worked:
```sql
-- Should show 5 runbooks
SELECT COUNT(*) FROM RAW.RUNBOOKS;

-- Should show anomalies
SELECT * FROM ANALYTICS.METRIC_DEVIATIONS;
```

### 5. Verify Setup
```bash
python test_setup.py
```

You should see all green checkmarks ✅

---

## Running the System

### Option A: Monitor Real CrewAI Repo
```bash
# Start listening for commits on joaomdmoura/crewAI
python ingestion/trigger_listener.py
```

Wait for someone to push to the CrewAI repo (1-5 min delay due to polling).

### Option B: Test with Simulation
```bash
# Simulate a CrewAI commit instantly
python test_crewai_trigger.py
```

This triggers the full pipeline without waiting.

### Option C: Import Historical Data
```bash
# Import past CrewAI issues as training data
python import_crewai_to_snowflake.py
```

This populates `RAW.PAST_INCIDENTS` with real CrewAI bugs.

---

## What Happens When Triggered

```
1. GitHub Push Event (CrewAI repo)
         ↓
2. Composio detects event
         ↓
3. trigger_listener.py receives event
         ↓
4. Insert deploy event → RAW.DEPLOY_EVENTS
         ↓
5. Inject synthetic spike → RAW.METRICS
         ↓
6. Query anomaly detection → ANALYTICS.METRIC_DEVIATIONS
         ↓
7. If anomaly found → Insert AI.ANOMALY_EVENTS
         ↓
8. Ready for CrewAI agents (Person 2's code)
```

---

## Verification Queries

Check Snowflake after running:

```sql
-- See deploy events
SELECT * FROM RAW.DEPLOY_EVENTS ORDER BY deployed_at DESC LIMIT 5;

-- See detected anomalies
SELECT * FROM AI.ANOMALY_EVENTS ORDER BY detected_at DESC LIMIT 5;

-- See metric deviations
SELECT * FROM ANALYTICS.METRIC_DEVIATIONS ORDER BY recorded_at DESC LIMIT 5;

-- See past incidents (if imported)
SELECT * FROM RAW.PAST_INCIDENTS WHERE service_name = 'crewAI' LIMIT 5;
```

---

## Troubleshooting

### "Composio authentication failed"
```bash
# Re-authenticate
composio login
composio add github
composio add slack
```

### "Snowflake connection failed"
- Check `.env` has correct credentials
- Verify you can login to Snowflake UI
- Check database name is `INCIDENTDNA`

### "No anomalies detected"
- Check `ANALYTICS.METRIC_BASELINES` has data
- Verify `ANALYTICS.METRIC_DEVIATIONS` dynamic table exists
- Lower z-score threshold in `03_dynamic_tables.sql` (change `>= 2` to `>= 1`)

### "No trigger events received"
- For public repos, wait 1-5 minutes (polling delay)
- Check Composio dashboard: https://app.composio.dev/triggers
- Use simulation script for instant testing

---

## Next Steps

Once Task 1 is complete:

1. **Person 2** builds CrewAI agents:
   - `agents/ag1_detector.py`
   - `agents/ag2_investigator.py`
   - `agents/ag5_validator.py`
   - `agents/manager.py`

2. **Person 3** builds Streamlit dashboard:
   - `dashboard/app.py`
   - Live console
   - Reasoning trace
   - Actions log

3. **Integration**: All three merge their branches

---

## Files Created

```
IncidentDNA/
├── snowflake/
│   ├── 01_schema.sql           # Database schema
│   ├── 02_seed_data.sql        # Test data
│   └── 03_dynamic_tables.sql   # Anomaly detection
├── ingestion/
│   └── trigger_listener.py     # Composio trigger handler
├── utils/
│   └── snowflake_conn.py       # Database utilities
├── .env.example                # Configuration template
├── requirements.txt            # Python dependencies
├── setup.sh                    # Automated setup (bash)
├── setup.py                    # Automated setup (python)
├── test_setup.py               # Verification script
├── test_crewai_trigger.py      # Simulation script
├── fetch_crewai_history.py     # Fetch repo history
└── import_crewai_to_snowflake.py  # Import history
```

---

## Support

- **Composio Docs**: https://docs.composio.dev
- **CrewAI Docs**: https://docs.crewai.com
- **Snowflake Docs**: https://docs.snowflake.com

---

**Your Task 1 is complete! Ready for Person 2 and Person 3 to build their components.** 🎉
