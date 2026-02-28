# IncidentDNA — Claude Code Guide

## What This Project Does
Autonomous incident management system. When a deploy triggers an anomaly, 3 AI agents
investigate → validate → act (Slack alert + GitHub issue). No human in the loop.

Built for: **Llama Lounge × Snowflake Hackathon**

---

## Architecture (High-Level)

```
GitHub commit / Slack message
        │
        ▼
ingestion/trigger_listener.py      ← Composio WebSocket listener (P3)
        │  inserts RAW.DEPLOY_EVENTS, injects metric spike
        │  waits 35s for dynamic table refresh
        │  calls run_incident_crew() directly
        ▼
agents/manager.py::run_incident_crew(event)
        │
        ├─► Ag1 (ag1_detector.py)       → severity + blast radius
        │         uses: query_snowflake
        │         reads: ANALYTICS.METRIC_DEVIATIONS, RAW.SERVICE_DEPENDENCIES
        │         writes: AI.DECISIONS
        │
        ├─► Ag2 (ag2_investigator.py)   → root cause + recommended action
        │         uses: search_runbooks, find_similar_incidents, query_snowflake
        │         reads: RAW.RUNBOOKS (cortex search), RAW.PAST_INCIDENTS, ANALYTICS.METRIC_DEVIATIONS
        │         writes: AI.DECISIONS
        │
        └─► Ag5 (ag5_validator.py)      → APPROVE or DEBATE (max 2 rounds)
                  uses: query_snowflake
                  reads: ANALYTICS.METRIC_DEVIATIONS
                  writes: AI.DECISIONS
        │
        ▼
tools/composio_actions.py
        │   post_slack_alert()          → Slack #incidents
        │   create_github_issue()       → GitHub repo
        │   (both idempotent — checked against AI.ACTIONS before executing)
        ▼
AI.INCIDENT_HISTORY                    ← final resolved record (MTTR, root cause, fix)

        ▼
dashboard/ (React/Vite — P3)           ← reads via FastAPI or mock data (VITE_USE_LIVE_DATA)
```

---

## Key File Map

```
IncidentDNA/
├── agents/
│   ├── manager.py          ← ENTRY POINT: run_incident_crew(event) orchestrates everything
│   ├── ag1_detector.py     ← classifies severity (P1/P2/P3) + blast radius
│   ├── ag2_investigator.py ← 3-source evidence chain → root cause
│   ├── ag5_validator.py    ← adversarial judge → APPROVE | DEBATE
│   └── crew.py             ← CrewAI Crew factory (sequential process)
│
├── tools/
│   ├── query_snowflake.py        ← generic SELECT tool (used by all agents)
│   ├── search_runbooks.py        ← Cortex Search on RAW.RUNBOOKS
│   ├── find_similar_incidents.py ← CORTEX.SIMILARITY on RAW.PAST_INCIDENTS
│   ├── composio_actions.py       ← Slack + GitHub via Composio SDK
│   └── idempotency.py            ← SHA256 key check before any external action
│
├── utils/
│   ├── snowflake_conn.py   ← get_connection(), run_query(), run_dml()
│   └── snowflake_llm.py    ← SnowflakeCortexLLM (BaseChatModel wrapper for CrewAI)
│                              calls SNOWFLAKE.CORTEX.COMPLETE('llama3.1-70b', messages)
│
├── snowflake/              ← SQL files (P1 — NOT YET CREATED)
│   ├── 01_schema.sql       ← CREATE TABLE for RAW.*, AI.*, ANALYTICS.*
│   ├── 02_seed_data.sql    ← runbooks, past incidents, service deps, sample metrics
│   └── 03_dynamic_tables.sql ← ANALYTICS.METRIC_DEVIATIONS (z-score, 30s refresh)
│
├── ingestion/              ← NOT YET CREATED (P3)
│   └── trigger_listener.py ← Composio listener → calls run_incident_crew()
│
├── dashboard/              ← React/Vite app (P3 — done, uses mock data for now)
│   └── src/services/api.js ← set VITE_USE_LIVE_DATA=true to switch to real backend
│
├── test_agent.py           ← python test_agent.py [snowflake|agents]
├── requirements.txt
└── .env                    ← Snowflake + Composio credentials
```

---

## Snowflake Tables

| Schema | Table | Owner | Purpose |
|--------|-------|-------|---------|
| RAW | RUNBOOKS | P1 | Runbook text → Cortex Search |
| RAW | PAST_INCIDENTS | P1 | Historical incidents → similarity search |
| RAW | SERVICE_DEPENDENCIES | P1 | service → depends_on (blast radius) |
| RAW | METRICS | P1 | Raw metric timeseries |
| RAW | DEPLOY_EVENTS | P1 | Written by trigger_listener |
| ANALYTICS | METRIC_DEVIATIONS | P1 | **Dynamic table** — z-scores, refreshes every 30s |
| AI | DECISIONS | P2 | Every agent step (agent_name, output, confidence) |
| AI | ACTIONS | P2 | Every Composio action attempt (idempotency key, status) |
| AI | INCIDENT_HISTORY | P2 | Final resolved incident + MTTR |

---

## LLM

**All LLM calls go through Snowflake Cortex — no external API key needed.**

`utils/snowflake_llm.py` → `SNOWFLAKE.CORTEX.COMPLETE('llama3.1-70b', messages)`

Model: `llama3.1-70b` | Temperature: `0.0` | Singleton: `cortex_llm`

All 3 agents use: `from utils.snowflake_llm import cortex_llm`

---

## Run Commands

```bash
# Test Snowflake connection + table existence
python test_agent.py snowflake

# Run full agent pipeline (needs Snowflake tables from P1)
python test_agent.py agents

# Start trigger listener (needs Snowflake + Composio)
python ingestion/trigger_listener.py

# Start React dashboard (mock data — works now)
cd dashboard && npm install && npm run dev

# Start React dashboard (live data — needs backend API)
cd dashboard && VITE_USE_LIVE_DATA=true npm run dev
```

---

## Credentials (.env)

```
SNOWFLAKE_ACCOUNT=sfsehol-llama_lounge_hackathon_sudhag
SNOWFLAKE_USER=USER
SNOWFLAKE_PASSWORD=sn0wf@ll
SNOWFLAKE_DATABASE=INCIDENTDNA
SNOWFLAKE_WAREHOUSE=COMPUTE_WH
SNOWFLAKE_ROLE=ACCOUNTADMIN
COMPOSIO_API_KEY=ak_Pv532zVAVQJoFTReaSgt
GITHUB_REPO=theshubh007/IncidentDNA
SLACK_CHANNEL=#incidents
```

---

## What's Done vs. Remaining

| Component | Status |
|-----------|--------|
| Agent layer (agents/ + tools/ + utils/) | ✅ Done |
| React dashboard (dashboard/) | ✅ Done (mock data) |
| Snowflake SQL (snowflake/) | ❌ P1 — not created yet |
| Trigger listener (ingestion/) | ❌ P3 — not created yet |
| Backend API (for React live data) | ❌ Not decided — may need FastAPI |

---

## Common Gotchas

- **Agents output JSON wrapped in markdown fences** — `_safe_parse()` in manager.py strips them
- **Idempotency is SHA256 of `action_type:event_id`** — checked in `AI.ACTIONS` before every Slack/GitHub call
- **Dynamic table has 30s lag** — trigger_listener.py waits 35s after injecting a spike
- **Composio SDK** uses `composio.tools.execute("TOOL_NAME", payload, user_id=...)` — NOT the old `ComposioToolSet`
- **CrewAI 0.28.0** — older API; `crew.kickoff()` returns object with `.raw` attribute
- **Snowflake tables don't exist yet** — `python test_agent.py agents` will fail until P1 runs SQL files
