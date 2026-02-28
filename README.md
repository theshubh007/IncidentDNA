# IncidentDNA — Autonomous Incident Intelligence

> **Hackathon:** Llama Lounge × Snowflake
> **Stack:** Snowflake · CrewAI · Composio · FastAPI · React

When a deploy goes wrong, IncidentDNA detects the anomaly, runs 3 AI agents to investigate and validate the root cause, then automatically posts a Slack alert and creates a GitHub issue — all in under 2 minutes, no human required.

---

## Quick Start

```bash
# 1. Activate the virtual environment (Python 3.11 — required)
source .venv/bin/activate

# 2. Install Python deps
uv pip install -r requirements.txt

# 3. Copy credentials (already filled in)
cp .env.example .env

# 4. Verify Snowflake connection
python test_agent.py snowflake

# 5. Run the full AI pipeline (Slack + GitHub will fire)
python test_agent.py agents

# 6. Start the backend API
python -m uvicorn api:app --reload --port 8000

# 7. Start the dashboard (new terminal)
cd dashboard && npm install && npm run dev
# → http://localhost:5173
```

> ⚠️ Always use `source .venv/bin/activate` before running any Python command.
> The system Python is 3.9 and is incompatible — `.venv` uses Python 3.11.

---

## How It Works

```
GitHub push / Slack event
        ↓
ingestion/trigger_listener.py   ← Composio WebSocket listener
        ↓
agents/manager.py               ← Orchestrates the pipeline
    ├── Ag1 Detector            → Severity (P1/P2/P3) + blast radius
    ├── Ag2 Investigator        → Root cause (runbooks + past incidents + metrics)
    └── Ag5 Validator           → Approve or challenge (max 2 debate rounds)
        ↓
tools/composio_actions.py
    ├── post_slack_alert()      → Slack #all-shubh
    └── create_github_issue()   → theshubh007/IncidentDNA
        ↓
AI.INCIDENT_HISTORY             ← Stored in Snowflake
        ↓
api.py (FastAPI :8000)          ← REST + WebSocket
        ↓
dashboard/ (React :5173)        ← Live dashboard
```

---

## .env

```
SNOWFLAKE_ACCOUNT=<your-account>
SNOWFLAKE_USER=<username>
SNOWFLAKE_PASSWORD=<password>
SNOWFLAKE_DATABASE=INCIDENTDNA
SNOWFLAKE_WAREHOUSE=COMPUTE_WH
SNOWFLAKE_ROLE=ACCOUNTADMIN
SNOWFLAKE_CORTEX_ENABLED=true
GROQ_API_KEY=<fallback LLM — free at console.groq.com>
COMPOSIO_API_KEY=<your key>
GITHUB_REPO=<owner/repo>
SLACK_CHANNEL=all-shubh
```

---

## Project Structure

```
agents/         3 AI agents + manager (CrewAI)
tools/          Snowflake queries, runbook search, Composio actions
utils/          Snowflake connection, LLM selector (Cortex → Groq → OpenAI)
snowflake/      SQL files — run once to set up all tables
ingestion/      trigger_listener.py — Composio WebSocket → pipeline
dashboard/      React/Vite dashboard (live data via api.py)
api.py          FastAPI backend — serves all dashboard endpoints from Snowflake
test_agent.py   python test_agent.py [snowflake|agents]
```

---

## Snowflake Tables

| Table | Purpose |
|-------|---------|
| `RAW.DEPLOY_EVENTS` | Incoming deploy events |
| `RAW.METRICS` | Raw metric timeseries |
| `RAW.RUNBOOKS` | Runbook knowledge base (Cortex Search) |
| `RAW.PAST_INCIDENTS` | Historical incidents for similarity search |
| `RAW.SERVICE_DEPENDENCIES` | Blast radius graph |
| `ANALYTICS.METRIC_DEVIATIONS` | Dynamic table — z-scores, refreshes every 30s |
| `AI.DECISIONS` | Every agent step (full audit trail) |
| `AI.ACTIONS` | Slack/GitHub actions with idempotency keys |
| `AI.INCIDENT_HISTORY` | Final resolved incident + MTTR |

---

## Live Connections

| What | Value |
|------|-------|
| LLM | claude-sonnet-4-5 via Snowflake Cortex |
| GitHub issues → | [theshubh007/IncidentDNA](https://github.com/theshubh007/IncidentDNA) |
| Slack alerts → | `#all-shubh` |
| Composio user | `pg-test-a6c32032-f3c5-43d2-9090-e16ffbd46f0d` |

> See [ARCHITECTURE.md](ARCHITECTURE.md) for full diagrams.
