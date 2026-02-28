# Setup Status

## ✅ Completed Steps

1. ✅ Virtual environment created (`venv/`)
2. ✅ All Python dependencies installed
3. ✅ `.env` file created from template

## ⚠️ Manual Steps Required

### Step 1: Get Composio API Key

1. Go to: https://app.composio.dev
2. Sign up / Login
3. Copy your API key
4. Edit `.env` file and replace:
   ```
   COMPOSIO_API_KEY=your_composio_api_key_here
   ```
   with your actual key

### Step 2: Authenticate with Composio

```bash
# Activate venv
source venv/bin/activate

# Login (will open browser)
composio login

# Connect GitHub (will open browser)
composio add github

# Connect Slack (will open browser)
composio add slack

# Verify connections
composio connected-accounts
```

### Step 3: Setup Snowflake

1. Login to Snowflake:
   - URL: https://sfsehol-llama_lounge_hackathon_sudhag.snowflakecomputing.com
   - User: `USER`
   - Password: `sn0wf@ll`

2. Open a new SQL worksheet

3. Run these files in order:
   ```sql
   -- File 1: Create schemas and tables
   @snowflake/01_schema.sql
   
   -- File 2: Insert seed data
   @snowflake/02_seed_data.sql
   
   -- File 3: Create dynamic tables
   @snowflake/03_dynamic_tables.sql
   ```

4. Verify:
   ```sql
   SELECT COUNT(*) FROM RAW.RUNBOOKS;  -- Should return 5
   SELECT * FROM ANALYTICS.METRIC_DEVIATIONS;  -- Should show anomalies
   ```

### Step 4: Test Setup

```bash
source venv/bin/activate
python test_setup.py
```

All checks should pass ✅

### Step 5: Run the System

```bash
# Option A: Start monitoring CrewAI repo
python ingestion/trigger_listener.py

# Option B: Test with simulation
python test_crewai_trigger.py
```

## Current Status

- ✅ Code: Ready
- ✅ Dependencies: Installed
- ⚠️ Composio: Needs authentication
- ⚠️ Snowflake: Needs SQL execution
- ⏳ Ready to run after manual steps

## Quick Start After Manual Steps

```bash
# Always activate venv first
source venv/bin/activate

# Test everything works
python test_setup.py

# Start the system
python ingestion/trigger_listener.py
```

---

**Next:** Complete the manual steps above, then run `python test_setup.py` to verify everything works!
