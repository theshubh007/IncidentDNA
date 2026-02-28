# IncidentDNA — Autonomous Incident Intelligence

> **Hackathon:** Llama Lounge × Snowflake
> **Stack:** Snowflake · CrewAI · Composio · FastAPI · React

When a deploy goes wrong, IncidentDNA detects the anomaly, runs 3 AI agents to investigate and validate the root cause, then automatically posts a Slack alert and creates a GitHub issue — all in under 2 minutes, no human required.

---

## Snowflake Access

| Field    | Value |
|----------|-------|
| Account  | `sfsehol-llama_lounge_hackathon_sudhag` |
| URL      | https://sfsehol-llama_lounge_hackathon_sudhag.snowflakecomputing.com |
| Username | `USER` |
| Password | `sn0wf@ll` |
| Database | `INCIDENTDNA` |
| Warehouse | `COMPUTE_WH` |

---

## Quick Start

```bash
# 1. Install Python deps
pip install -r requirements.txt

# 2. Copy credentials
cp .env.example .env        # already filled in — just copy it

# 3. Verify Snowflake connection
python test_agent.py snowflake

# 4. Run the full AI pipeline (Slack + GitHub will fire)
python test_agent.py agents

# 5. Start the backend API
python3 -m uvicorn api:app --reload --port 8000

# 6. Start the dashboard (new terminal)
cd dashboard && npm install && npm run dev
# → http://localhost:5173
```

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
    ├── post_slack_alert()      → Slack #incidents
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
SNOWFLAKE_ACCOUNT=sfsehol-llama_lounge_hackathon_sudhag
SNOWFLAKE_USER=USER
SNOWFLAKE_PASSWORD=sn0wf@ll
SNOWFLAKE_DATABASE=INCIDENTDNA
SNOWFLAKE_WAREHOUSE=COMPUTE_WH
SNOWFLAKE_ROLE=ACCOUNTADMIN
GEMINI_API_KEY=<your key — free at aistudio.google.com/apikey>
GROQ_API_KEY=<backup LLM — free at console.groq.com>
COMPOSIO_API_KEY=ak_Pv532zVAVQJoFTReaSgt
GITHUB_REPO=theshubh007/IncidentDNA
SLACK_CHANNEL=#incidents
```

---

## Project Structure

```
agents/         3 AI agents + manager (CrewAI)
tools/          Snowflake queries, runbook search, Composio actions
utils/          Snowflake connection, LLM selector (Gemini → Groq → OpenAI)
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
| LLM | Gemini 2.5 Flash (auto-falls back to Groq) |
| GitHub issues → | [theshubh007/IncidentDNA](https://github.com/theshubh007/IncidentDNA) |
| Slack alerts → | `#incidents` |
| Composio user | `pg-test-a6c32032-f3c5-43d2-9090-e16ffbd46f0d` |

> See [ARCHITECTURE.md](ARCHITECTURE.md) for full diagrams.
