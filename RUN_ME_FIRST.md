# ✅ Dependencies Installed!

## Next Steps:

### 1. Configure Environment
```bash
# Copy template
cp .env.example .env

# Edit .env and add your COMPOSIO_API_KEY
# Get it from: https://app.composio.dev
nano .env
```

### 2. Authenticate with Composio
```bash
# Activate virtual environment
source venv/bin/activate

# Login to Composio
composio login

# Connect GitHub
composio add github

# Connect Slack
composio add slack

# Verify
composio connected-accounts
```

### 3. Setup Snowflake

Login to Snowflake:
- URL: https://sfsehol-llama_lounge_hackathon_sudhag.snowflakecomputing.com
- User: `USER`
- Password: `sn0wf@ll`

Run these SQL files in order:
```sql
@snowflake/01_schema.sql
@snowflake/02_seed_data.sql
@snowflake/03_dynamic_tables.sql
```

### 4. Test Everything
```bash
python test_setup.py
```

### 5. Run the System
```bash
# Option A: Start trigger listener
python ingestion/trigger_listener.py

# Option B: Test with simulation
python test_crewai_trigger.py
```

## Quick Commands

```bash
# Always activate venv first
source venv/bin/activate

# Then run any script
python test_setup.py
python ingestion/trigger_listener.py
```

Done! 🎉
