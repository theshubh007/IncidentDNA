# IncidentDNA - Architecture

> **Auto-updated.** Run `python3 scripts/gen_architecture.py` manually,
> or it runs automatically on every `git pull` / `git commit` via hooks.
>
> **View diagrams:** Open this file in VSCode and press `Cmd+Shift+V` (Mac) or `Ctrl+Shift+V` (Windows/Linux).
> Requires extension: **Markdown Preview Mermaid Support** (`bierner.markdown-mermaid`) — install from VSCode Extensions sidebar.
> Or just open on **GitHub** — Mermaid renders natively there.

---

## 0. What Is This? (Beginner Friendly)

**IncidentDNA** is an AI system that watches your software services and automatically investigates problems — without a human having to do anything.

### The Problem It Solves
When something breaks in production (e.g. a database crashes, an API slows down), engineers normally have to:
1. Get paged at 3am
2. Manually look at logs and metrics
3. Figure out what went wrong
4. Create a ticket and alert the team on Slack

**IncidentDNA does all of that automatically, in under 2 minutes.**

### What Triggers It
A code deployment (git push) can introduce bugs. Our system listens for deployments via **Composio** (a tool that connects to GitHub and Slack), then injects a simulated metric spike into Snowflake to test the detection pipeline.

### What Happens Next (the full flow in plain English)
```
1. Developer pushes code to GitHub
2. Composio sees the push → writes a record in Snowflake
3. Snowflake detects a metric anomaly (e.g. error rate spiked)
4. 3 AI agents wake up and investigate:
      Agent 1 → "How bad is this? Which services are affected?"
      Agent 2 → "What caused this? Check runbooks + past incidents + live metrics"
      Agent 5 → "Do I trust Agent 2's answer? Challenge it."
5. If approved → post Slack alert + create GitHub issue automatically
6. Everything is stored in Snowflake for the dashboard
```

---

## 0b. Live Connections (What Is Connected Right Now)

| What | Value | Purpose |
|------|-------|---------|
| **LLM (AI Brain)** | Claude Sonnet 4.5 via Snowflake Cortex | Powers all 3 agents' reasoning |
| **Database** | Snowflake — `INCIDENTDNA` | Stores all metrics, incidents, decisions |
| **Snowflake Account** | `sfsehol-llama_lounge_hackathon_sudhag` | Hackathon account |
| **GitHub Repo (target)** | [`theshubh007/IncidentDNA`](https://github.com/theshubh007/IncidentDNA) | Where GitHub issues are auto-created |
| **Slack Channel** | `#incidents` | Where Slack alerts are posted |
| **Composio User ID** | `pg-test-a6c32032-f3c5-43d2-9090-e16ffbd46f0d` | Identity used to send Slack/GitHub actions |
| **Composio API** | `ak_Pv532zVAVQJoFTReaSgt` | Auth key for Composio |

> **To change the GitHub repo**: edit `GITHUB_REPO=` in `.env`
> **To change the Slack channel**: edit `SLACK_CHANNEL=` in `.env`

---

## 0c. How to Run It

```bash
# Step 1 — Check Snowflake connection and tables
python test_agent.py snowflake

# Step 2 — Run the full AI agent pipeline (triggers Slack + GitHub)
python test_agent.py agents

# Step 3 — Start the FastAPI backend (connects dashboard to live Snowflake data)
uvicorn api:app --reload --host 0.0.0.0 --port 8000

# Step 4 — Start the React dashboard (live data mode — needs Step 3 running)
cd dashboard && npm install && npm run dev
```

> All credentials are in `.env`. Ask a teammate for the file if you don't have it.
> The dashboard automatically uses live Snowflake data — `dashboard/.env` has `VITE_USE_LIVE_DATA=true`.

---

<!-- STATUS_START -->
## Status Dashboard

| Component | Key Files | Status |
|-----------|-----------|--------|
| Agent Layer | manager.py, ag1_detector.py, ag2_investigator.py, ... | ✅ Done |
| Tools | query_snowflake.py, search_runbooks.py, find_similar_incidents.py, ... | ✅ Done |
| Utils | snowflake_conn.py, snowflake_llm.py | ✅ Done |
| React Dashboard | App.jsx, api.js, mockData.js | ✅ Done (mock data) |
| Snowflake SQL | 01_schema.sql, 02_seed_data.sql, 03_dynamic_tables.sql | ✅ Done |
| Trigger Listener | trigger_listener.py | ✅ Done |
| Backend API | api.py | ✅ Done (for React live data) |

_Last updated: 2026-02-28 16:02 by scripts/gen_architecture.py_
<!-- STATUS_END -->

---

## 1. System Overview

> **How to read this diagram:** Follow the arrows top to bottom. Each box is a step. The blue box is the brain (AI pipeline). Orange box = actions taken automatically.

```mermaid
flowchart TD
    A["👨‍💻 Developer pushes code\nto GitHub"] --> B
    C["💬 Slack message detected"] --> B

    B["🔌 Composio WebSocket Listener\ningestion/trigger_listener.py\n\nListens for GitHub push events\nand Slack messages in real-time"]

    B --> D["📝 RAW.DEPLOY_EVENTS\nRecord the deploy in Snowflake"]
    B --> E["📈 RAW.METRICS\nInject a metric spike\ne.g. error_rate=0.22, latency=2100ms"]

    E --> F["⚡ ANALYTICS.METRIC_DEVIATIONS\nDynamic table — auto-refreshes every 30s\nCalculates z-score: how abnormal is this metric?"]

    F --> G{"🚨 Anomaly detected?\nz_score > 2 = unusual spike"}
    G -- "No — normal traffic" --> H["✅ Skip — no action needed"]
    G -- "Yes — something is wrong!" --> I

    I["🤖 run_incident_crew\nagents/manager.py\n\nEntry point for the AI pipeline"]

    I --> AG1["Agent 1 — Detector\nHow severe? P1/P2/P3\nWhich services are affected?"]
    AG1 --> AG2["Agent 2 — Investigator\nSearches runbooks + past incidents + metrics\nBuilds root cause hypothesis"]
    AG2 --> AG5["Agent 5 — Validator\nAdversarial judge\nChallenges Agent 2's answer"]

    AG5 --> V{"APPROVE or DEBATE?"}
    V -- "DEBATE — max 2 rounds\nAgent 2 tries again with feedback" --> AG2
    V -- "APPROVED ✅" --> ACT["🚀 Execute Actions"]

    ACT --> SL["💬 Slack Alert\nChannel: #incidents\nPosted via Composio"]
    ACT --> GH["🐙 GitHub Issue\nRepo: theshubh007/IncidentDNA\nCreated via Composio"]
    ACT --> DB["🗄️ AI.INCIDENT_HISTORY\nStores: MTTR, root cause, fix applied"]

    DB --> API["⚙️ FastAPI Backend\napi.py — port 8000\n\nREST endpoints + WebSocket\nServes live Snowflake data to dashboard"]
    API --> UI["📊 React Dashboard\ndashboard/ — port 5173\n\nLive mode: VITE_USE_LIVE_DATA=true\nShows real incidents, pipeline steps, audit log"]

    style A fill:#2da44e,color:#fff
    style C fill:#4a154b,color:#fff
    style I fill:#0066cc,color:#fff
    style ACT fill:#e36209,color:#fff
    style SL fill:#4a154b,color:#fff
    style GH fill:#24292f,color:#fff
    style API fill:#6366f1,color:#fff
```

---

## 2. Agent Pipeline (Detail)

> **3 agents run sequentially.** Each agent uses AI (Claude Sonnet 4.5 via Snowflake Cortex) to reason about the incident. Each agent has specific tools it can call — like querying Snowflake or searching runbooks.

```mermaid
flowchart TD
    EVT["📥 Incident Event\nevent_id, service name,\nanomaly type, severity signal"]

    EVT --> AG1

    subgraph P1["🔴 Phase 1 — Detect (Agent 1)"]
        AG1["Ag1 Detector\nag1_detector.py\n\nTask: Classify the incident"]
        AG1 -->|"Queries Snowflake:\nWho depends on this service?"| SF_DEP[("RAW.SERVICE_DEPENDENCIES\nBlast radius lookup")]
        AG1 -->|"Queries Snowflake:\nIs z_score > 3 (P1) or > 2 (P2)?"| SF_MET[("ANALYTICS.METRIC_DEVIATIONS\nLive metric anomalies")]
        AG1 --> OUT1["Output JSON:\nseverity: P1 / P2 / P3\nblast_radius: services affected\nclassification: what is happening"]
    end

    OUT1 --> AG2

    subgraph P2["🟡 Phase 2 — Investigate (Agent 2)"]
        AG2["Ag2 Investigator\nag2_investigator.py\n\nTask: Find the root cause"]
        AG2 -->|"Searches runbooks\n(Cortex vector search)"| SF_RB[("RAW.RUNBOOKS\n5 runbooks about known issues")]
        AG2 -->|"Finds similar past incidents\n(keyword search fallback)"| SF_PI[("RAW.PAST_INCIDENTS\n10 historical incidents")]
        AG2 -->|"Checks live metrics"| SF_MET2[("ANALYTICS.METRIC_DEVIATIONS")]
        AG2 --> OUT2["Output JSON:\nroot_cause: detailed explanation\nconfidence: 0.0 to 1.0\nevidence_sources: which tools helped\nrecommended_action: rollback/fix_config/etc"]
    end

    OUT2 --> AG5

    subgraph P3["🟠 Phase 3 — Validate (Agent 5) — max 2 rounds"]
        AG5["Ag5 Validator\nag5_validator.py\n\nTask: Challenge Agent 2's answer\nBe adversarial — find holes in the logic"]
        AG5 -->|"Double-checks metrics\nfor alternative causes"| SF_MET3[("ANALYTICS.METRIC_DEVIATIONS")]
        AG5 --> OUT3["Output JSON:\nverdict: APPROVED or DEBATE\nconfidence_adjustment: e.g. +0.05 or -0.2\nobjections: list of concerns"]
    end

    OUT3 -->|"DEBATE: Agent 2 re-investigates\nwith Agent 5's objections as context"| AG2
    OUT3 -->|"APPROVED ✅\nor max rounds reached"| MGR

    subgraph P4["🔵 Phase 4 — Act (Manager)"]
        MGR["Manager\nagents/manager.py\n\nOrchestrates everything"]
        MGR -->|"SLACK_SEND_MESSAGE\nvia Composio SDK"| SLA["💬 Slack\n#incidents channel"]
        MGR -->|"GITHUB_CREATE_AN_ISSUE\nvia Composio SDK"| GHA["🐙 GitHub\ntheshubh007/IncidentDNA"]
        MGR -->|"INSERT (every agent step)"| DEC[("AI.DECISIONS\nFull audit trail of reasoning")]
        MGR -->|"INSERT (final record)"| INC[("AI.INCIDENT_HISTORY\nMTTR, root cause, fix")]
    end

    style P1 fill:#e8f4f8,stroke:#0066cc
    style P2 fill:#e8f8e8,stroke:#2da44e
    style P3 fill:#fff8e8,stroke:#e36209
    style P4 fill:#f8e8e8,stroke:#cf222e
```

---

## 3. Snowflake Data Model

> **Snowflake** is the database. It has 3 schemas (folders): RAW (raw inputs), ANALYTICS (computed data), AI (agent outputs).

```mermaid
erDiagram
    RAW_DEPLOY_EVENTS {
        string deploy_id PK "e.g. deploy_001"
        string service "e.g. payment-service"
        string version "e.g. v2.1.4"
        string deployed_by "GitHub username"
        string diff_summary "What changed"
        timestamp deployed_at "When it happened"
    }

    RAW_METRICS {
        timestamp recorded_at "When measured"
        string service "Which service"
        string metric_name "e.g. error_rate, latency_ms"
        float metric_value "e.g. 0.22 or 2100"
    }

    RAW_RUNBOOKS {
        string id PK
        string service "Which service this runbook is for"
        string symptom "What went wrong"
        string runbook_text "How to fix it"
        string severity "P1/P2/P3"
    }

    RAW_PAST_INCIDENTS {
        string id PK
        string title "Short description"
        string service "Which service was affected"
        string root_cause "What caused it"
        string fix_applied "What fixed it"
        int mttr_minutes "Minutes to resolve"
    }

    RAW_SERVICE_DEPENDENCIES {
        string service "Service name"
        string depends_on "What it depends on"
    }

    ANALYTICS_METRIC_DEVIATIONS {
        string service "Which service"
        string metric_name "Which metric"
        float current_value "Current reading"
        float baseline_avg "Normal average"
        float z_score "How abnormal: >2=alert, >3=critical"
        string severity "P1/P2/P3 based on z_score"
        timestamp recorded_at
    }

    AI_DECISIONS {
        string id PK
        string event_id "Links to the incident"
        string agent_name "ag1_detector / ag2_investigator / ag5_validator"
        variant output "JSON: what the agent decided"
        string reasoning "Full text of agent's thinking"
        float confidence "0.0 to 1.0"
        timestamp created_at
    }

    AI_ACTIONS {
        string id PK
        string event_id "Links to the incident"
        string action_type "SLACK_ALERT or GITHUB_ISSUE"
        string idempotency_key "SHA256 hash — prevents duplicate sends"
        variant payload "What was sent"
        string status "PENDING / SENT / FAILED"
        timestamp executed_at
    }

    AI_INCIDENT_HISTORY {
        string id PK
        string event_id "Links to the incident"
        string service_name "Affected service"
        string root_cause "Final diagnosis"
        string fix_applied "What action was taken"
        float confidence "Final confidence score"
        int mttr_minutes "Time to resolve (updated later)"
        timestamp resolved_at
    }

    RAW_METRICS ||--o{ ANALYTICS_METRIC_DEVIATIONS : "aggregated every 30s"
    RAW_DEPLOY_EVENTS ||--o{ AI_DECISIONS : "triggers pipeline"
    AI_DECISIONS }o--|| AI_INCIDENT_HISTORY : "resolved into final record"
    AI_DECISIONS }o--o{ AI_ACTIONS : "causes Slack/GitHub actions"
```

---

## 4. Tool to Agent Matrix

> **Tools** are functions that agents can call during their reasoning. Think of them as the agent's hands — it can look things up, query databases, or fire alerts.

```mermaid
graph LR
    subgraph Agents["🤖 AI Agents"]
        AG1["Agent 1\nDetector"]
        AG2["Agent 2\nInvestigator"]
        AG5["Agent 5\nValidator"]
        MGR["Manager\nOrchestrator"]
    end

    subgraph Tools["🔧 Tools (tools/)"]
        T1["query_snowflake.py\nRun any SELECT query\nUsed by all agents"]
        T2["search_runbooks.py\nCortex vector search\nFinds relevant runbooks"]
        T3["find_similar_incidents.py\nKeyword search fallback\nFinds past similar incidents"]
        T4["composio_actions.py\nSends Slack alerts\nCreates GitHub issues"]
        T5["idempotency.py\nSHA256 dedup check\nPrevents duplicate alerts"]
    end

    subgraph External["🌐 External Services"]
        SF[("❄️ Snowflake\nDatabase: INCIDENTDNA\nAccount: sfsehol-llama_lounge_hackathon_sudhag")]
        SL["💬 Slack\nChannel: #incidents"]
        GH["🐙 GitHub\nRepo: theshubh007/IncidentDNA\nIssues created here automatically"]
        GM["🧠 Claude Sonnet 4.5\nSnowflake Cortex\nPowers all agent reasoning"]
    end

    AG1 --> T1
    AG2 --> T1
    AG2 --> T2
    AG2 --> T3
    AG5 --> T1
    MGR --> T4

    T1 --> SF
    T2 --> SF
    T3 --> SF
    T4 --> T5
    T4 --> SL
    T4 --> GH

    AG1 -.->|"LLM calls"| GM
    AG2 -.->|"LLM calls"| GM
    AG5 -.->|"LLM calls"| GM

    style AG1 fill:#dbeafe
    style AG2 fill:#dcfce7
    style AG5 fill:#fef9c3
    style MGR fill:#fee2e2
    style GH fill:#24292f,color:#fff
    style SL fill:#4a154b,color:#fff
    style GM fill:#4285f4,color:#fff
```

---

## 5. FastAPI Backend — Dashboard ↔ Snowflake Bridge

> **`api.py`** is the glue between the React dashboard and Snowflake. It runs at `http://localhost:8000` and exposes every endpoint the dashboard needs.

```mermaid
flowchart LR
    UI["📊 React Dashboard\ndashboard/ — port 5173\napi.js fetches from /api/v1/*"]

    subgraph API["⚙️ api.py — FastAPI — port 8000"]
        R1["/api/v1/incidents\n/api/v1/incidents/:id\n/api/v1/incidents/:id/pipeline"]
        R2["/api/v1/metrics/overview\n/api/v1/audit\n/api/v1/runbooks"]
        R3["/api/v1/services\n/api/v1/releases\n/api/v1/postmortems"]
        R4["/api/v1/simulation/run\nPOST → calls run_incident_crew()"]
        R5["/api/v1/tools/slack/send\n/api/v1/tools/github/issue"]
        WS["/ws\nWebSocket — real-time pipeline events"]
    end

    subgraph SF["❄️ Snowflake — INCIDENTDNA"]
        T1[("AI.INCIDENT_HISTORY")]
        T2[("AI.DECISIONS")]
        T3[("AI.ACTIONS")]
        T4[("RAW.RUNBOOKS\nRAW.PAST_INCIDENTS\nRAW.SERVICE_DEPENDENCIES")]
        T5[("RAW.DEPLOY_EVENTS")]
    end

    UI -->|"HTTP GET/POST + WebSocket"| API
    R1 --> T1
    R1 --> T2
    R2 --> T3
    R2 --> T4
    R3 --> T4
    R3 --> T5
    R4 -->|"background task"| MGR["agents/manager.py\nrun_incident_crew()"]
    WS -->|"broadcast"| UI

    style API fill:#6366f1,color:#fff
    style SF fill:#29b5e8,color:#fff
```

**Key design decisions in `api.py`:**
- Every endpoint queries Snowflake first; falls back gracefully if a table is missing (returns `[]`)
- `/api/v1/simulation/run` runs the full agent pipeline in a FastAPI background task — returns immediately, broadcasts result via WebSocket when done
- `/api/v1/snowflake/query` is a SELECT-only proxy (rejects non-SELECT SQL)
- CORS is open to `localhost:5173` (Vite) and `localhost:3000`
- Idempotency is preserved — tool endpoints re-use the same `composio_actions.py` functions

---

## 6. LLM Architecture

> **How the AI brain works.** All 3 agents use Claude Sonnet 4.5 via Snowflake Cortex. The `snowflake_llm.py` file picks the LLM based on what is configured in `.env`.

```mermaid
flowchart LR
    A["🤖 CrewAI Agent\nag1, ag2, or ag5"] --> B

    B["utils/snowflake_llm.py\n\nLLM priority:\n1st: Snowflake Cortex ✅ ACTIVE\n2nd: Groq llama-3.3-70b\n3rd: OpenAI GPT-4o-mini"]

    B --> C["Snowflake Cortex\nClaude Sonnet 4.5\nSNOWFLAKE.CORTEX.COMPLETE()"]

    C --> D["LLM Response\nAgent reads it and\ndecides next action"]

    style B fill:#0066cc,color:#fff
    style C fill:#29b5e8,color:#fff
```

**Current LLM config in `.env`:**
```
SNOWFLAKE_CORTEX_ENABLED=true   ← uses claude-sonnet-4-5 via Snowflake Cortex
GROQ_API_KEY=gsk_K13...         ← fallback if Cortex unavailable
```

---

## 7. Directory Structure

<!-- FILES_START -->
```
IncidentDNA/
├── agents/                     ✅
│   ├── manager.py                      ← ENTRY POINT: run_incident_crew()
│   ├── ag1_detector.py                 Classify severity + blast radius
│   ├── ag2_investigator.py             3-source root cause investigation
│   ├── ag5_validator.py                Adversarial judge (APPROVE|DEBATE)
│   ├── crew.py                         CrewAI Crew factory
│
├── tools/                      ✅
│   ├── query_snowflake.py              Generic SELECT (used by all agents)
│   ├── search_runbooks.py              Cortex Search on RAW.RUNBOOKS
│   ├── find_similar_incidents.py       CORTEX.SIMILARITY on RAW.PAST_INCIDENTS
│   ├── composio_actions.py             Slack + GitHub via Composio SDK
│   ├── idempotency.py                  SHA256 dedup before any external action
│
├── utils/                      ✅
│   ├── snowflake_conn.py               get_connection(), run_query(), run_dml()
│   ├── snowflake_llm.py                SnowflakeCortexLLM wrapper (BaseChatModel)
│
├── snowflake/                  ✅
│   ├── 01_schema.sql                 ✅  DDL: RAW.*, AI.*, ANALYTICS.*
│   ├── 02_seed_data.sql              ✅  Runbooks, past incidents, sample metrics
│   ├── 03_dynamic_tables.sql         ✅  ANALYTICS.METRIC_DEVIATIONS (z-score)
│
├── ingestion/                  ✅
│   └── trigger_listener.py         ✅  Composio WebSocket → run_incident_crew()
│
├── dashboard/                  ✅ (mock data)
│   └── src/
│       ├── pages/              8 pages: Overview, Incidents, Releases...
│       ├── api.js                      Toggle VITE_USE_LIVE_DATA for real data
│       ├── mockData.js                 Offline demo data
│
├── CLAUDE.md                          ✅  Claude Code auto-loads this every session
├── ARCHITECTURE.md                    ✅  This file — auto-updated by hooks
├── gen_architecture.py                ✅  Auto-updates this file
├── requirements.txt                   ✅
├── test_agent.py                      ✅  python test_agent.py [snowflake|agents]
├── .env                               ✅  Credentials
```
<!-- FILES_END -->

---

## 8. Integration Contracts (Who Talks to Who)

> This shows the data flow between the 3 team members' work areas.

```mermaid
sequenceDiagram
    participant P1 as 🗄️ P1 — Snowflake SQL
    participant P2 as 🤖 P2 — Agent Layer
    participant P3 as 🖥️ P3 — Frontend & Listener

    Note over P1: Creates all tables and seeds data

    P1->>P2: RAW.RUNBOOKS (5 runbooks, Cortex Search enabled)
    P1->>P2: RAW.PAST_INCIDENTS (10 historical incidents)
    P1->>P2: RAW.SERVICE_DEPENDENCIES (blast radius data)
    P1->>P2: ANALYTICS.METRIC_DEVIATIONS (z-score dynamic table, 30s refresh)

    Note over P2: Agents read from P1's tables, write decisions

    P2->>P3: AI.DECISIONS (every agent reasoning step)
    P2->>P3: AI.ACTIONS (Slack/GitHub audit log with status)
    P2->>P3: AI.INCIDENT_HISTORY (MTTR + root cause + fix)

    Note over P3: Listener writes triggers, dashboard reads results

    P3->>P1: Writes RAW.DEPLOY_EVENTS (when deploy detected)
    P3->>P1: Writes RAW.METRICS spike (simulates anomaly)
```

---

## 9. Credentials Quick Reference

> Keep this handy when setting up on a new machine. All values also live in `.env`.

| Service | How to Get Access | Used For |
|---------|------------------|----------|
| **Snowflake** | Use shared credentials in `.env` | Database for everything |
| **Snowflake Cortex** | Included with Snowflake account | LLM for agents (claude-sonnet-4-5) |
| **Groq API** | [console.groq.com](https://console.groq.com) — free | Fallback LLM |
| **Composio** | [app.composio.dev](https://app.composio.dev) — shared API key in `.env` | Slack + GitHub integration |
| **GitHub** | Connect your GitHub account in Composio dashboard | Creates issues in `theshubh007/IncidentDNA` |
| **Slack** | Connect your Slack workspace in Composio dashboard | Posts to `#incidents` |
