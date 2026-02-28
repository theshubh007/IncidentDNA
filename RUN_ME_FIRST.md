# ✅ Dependencies Installed!

## IMPORTANT: Use the .venv (Python 3.11)

The system Python is 3.9 and is **incompatible** with crewai/litellm.
Always activate `.venv` first:

```bash
source .venv/bin/activate
python --version  # Must show Python 3.11
```

---

## Next Steps:

### 1. Configure Environment
```bash
# .env is already configured — verify it exists
cat .env
```

### 2. Test Snowflake Connection
```bash
source .venv/bin/activate
python test_agent.py snowflake
```

### 3. Run the Agent Pipeline
```bash
source .venv/bin/activate
python test_agent.py agents
```

### 4. Start Backend API
```bash
source .venv/bin/activate
python -m uvicorn api:app --reload --port 8000
```

### 5. Start Dashboard (new terminal)
```bash
cd dashboard && npm run dev
# → http://localhost:5173
```

## Quick Commands

```bash
# Always activate .venv first
source .venv/bin/activate

# Test Snowflake
python test_agent.py snowflake

# Run full agent pipeline
python test_agent.py agents

# Start API backend
python -m uvicorn api:app --reload --port 8000
```

Done! 🎉
