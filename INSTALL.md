# Installation Guide

## Prerequisites

- Python 3.11+ (system has `uv` which manages this automatically)
- Access to Snowflake account
- Composio account (free at https://app.composio.dev)

## Step 1: Activate the Virtual Environment

The `.venv` (Python 3.11) is already created. Just activate it:

```bash
source .venv/bin/activate

# Verify — should show Python 3.11
python --version
```

> **Note:** Do NOT use `python3 -m venv venv` or `pip install` directly.
> The system Python is 3.9 and is incompatible with crewai/litellm.
> Always use `.venv` (created with `uv`, Python 3.11).

## Step 2: Install Dependencies

```bash
uv pip install -r requirements.txt
```

## Step 3: Configure Environment

```bash
# Copy template
cp .env.example .env

# Edit .env and add your COMPOSIO_API_KEY
# Get it from: https://app.composio.dev
nano .env  # or use any editor
```

## Step 4: Authenticate with Composio

```bash
# Login (opens browser)
composio login

# Connect GitHub
composio add github

# Connect Slack
composio add slack

# Verify
composio connected-accounts
```

## Step 5: Setup Snowflake

1. Login to Snowflake:
   - URL: https://sfsehol-llama_lounge_hackathon_sudhag.snowflakecomputing.com
   - User: `USER`
   - Password: `sn0wf@ll`

2. Run SQL files in order:
   ```sql
   @snowflake/01_schema.sql
   @snowflake/02_seed_data.sql
   @snowflake/03_dynamic_tables.sql
   ```

3. Verify:
   ```sql
   SELECT COUNT(*) FROM RAW.RUNBOOKS;  -- Should return 5
   SELECT * FROM ANALYTICS.METRIC_DEVIATIONS;  -- Should show anomalies
   ```

## Step 6: Test Setup

```bash
python test_setup.py
```

All checks should pass ✅

## Step 7: Run the System

```bash
# Option A: Start trigger listener
python ingestion/trigger_listener.py

# Option B: Test with simulation
python test_crewai_trigger.py

# Option C: Import CrewAI history
python import_crewai_to_snowflake.py
```

## Troubleshooting

### Virtual Environment Issues

Always use the `.venv` with Python 3.11 — system Python 3.9 will fail:
```bash
source .venv/bin/activate
uv pip install -r requirements.txt
```

### Composio Not Found

```bash
# Make sure you're in the venv
which composio

# If not found, reinstall
pip install composio-core composio-crewai
```

### Snowflake Connection Failed

Check `.env` file has correct values:
```bash
SNOWFLAKE_ACCOUNT=sfsehol-llama_lounge_hackathon_sudhag
SNOWFLAKE_USER=USER
SNOWFLAKE_PASSWORD=sn0wf@ll
SNOWFLAKE_DATABASE=INCIDENTDNA
```

## Quick Commands

```bash
# Activate venv
source .venv/bin/activate

# Install deps
uv pip install -r requirements.txt

# Test
python test_agent.py snowflake

# Run
python ingestion/trigger_listener.py
```

Done! 🎉
