# Installation Guide

## Prerequisites

- Python 3.8+
- pip or pip3
- Access to Snowflake account
- Composio account (free at https://app.composio.dev)

## Step 1: Create Virtual Environment (Recommended)

```bash
# Create virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate  # Mac/Linux
# OR
venv\Scripts\activate  # Windows

# Verify activation (should show venv path)
which python
```

## Step 2: Install Dependencies

```bash
pip install -r requirements.txt
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

If you get "externally-managed-environment" error:
```bash
# Create and activate venv first
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
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
source venv/bin/activate

# Install deps
pip install -r requirements.txt

# Test
python test_setup.py

# Run
python ingestion/trigger_listener.py
```

Done! 🎉
