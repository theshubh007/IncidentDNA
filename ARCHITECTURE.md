# IncidentDNA - Architecture

> **Auto-updated.** Run `python3 scripts/gen_architecture.py` manually,
> or it runs automatically on every `git pull` / `git commit` via hooks.
>
> **View diagrams:** Open this file in VSCode and press `Cmd+Shift+V` (Mac) or `Ctrl+Shift+V` (Windows/Linux).
> Requires extension: **Markdown Preview Mermaid Support** (`bierner.markdown-mermaid`) — install from VSCode Extensions sidebar.
> Or just open on **GitHub** — Mermaid renders natively there.

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
| Backend API | api.py | ❌ Missing |

_Last updated: 2026-02-27 23:11 by scripts/gen_architecture.py_
<!-- STATUS_END -->

---

## 1. System Overview

```mermaid
flowchart TD
    A["GitHub Commit"] --> B
    C["Slack Message"] --> B

    B["Composio WebSocket<br/>ingestion/trigger_listener.py"]

    B --> D["RAW.DEPLOY_EVENTS<br/>insert record"]
    B --> E["RAW.METRICS<br/>inject spike: error_rate=0.22, latency=2100ms"]

    E --> F["ANALYTICS.METRIC_DEVIATIONS<br/>dynamic table, refreshes every 30s<br/>z-score anomaly detection"]

    F --> G{"Anomaly detected?<br/>z_score > 2"}
    G -- No --> H["Skip pipeline"]
    G -- Yes --> I

    I["run_incident_crew<br/>agents/manager.py"]

    I --> AG1["Ag1 - Detector<br/>Severity + Blast Radius"]
    AG1 --> AG2["Ag2 - Investigator<br/>3-source evidence chain"]
    AG2 --> AG5["Ag5 - Validator<br/>Adversarial judge"]

    AG5 --> V{"APPROVE or DEBATE?"}
    V -- "DEBATE - max 2 rounds" --> AG2
    V -- APPROVED --> ACT["Execute Actions"]

    ACT --> SL["Slack Alert<br/>#incidents"]
    ACT --> GH["GitHub Issue<br/>theshubh007/IncidentDNA"]
    ACT --> DB["AI.INCIDENT_HISTORY<br/>MTTR, root cause, fix"]

    DB --> UI["React Dashboard<br/>dashboard/"]

    style A fill:#2da44e,color:#fff
    style C fill:#4a154b,color:#fff
    style I fill:#0066cc,color:#fff
    style ACT fill:#e36209,color:#fff
    style SL fill:#4a154b,color:#fff
    style GH fill:#24292f,color:#fff
```

---

## 2. Agent Pipeline (Detail)

```mermaid
flowchart TD
    EVT["event dict<br/>event_id, service, anomaly_type, severity"]

    EVT --> AG1

    subgraph P1["Phase 1 - Detect"]
        AG1["Ag1 Detector<br/>ag1_detector.py"]
        AG1 -->|"query_snowflake<br/>SERVICE_DEPENDENCIES"| SF_DEP[("SERVICE_DEPENDENCIES")]
        AG1 -->|"query_snowflake<br/>METRIC_DEVIATIONS"| SF_MET[("METRIC_DEVIATIONS")]
        AG1 --> OUT1["severity: P1/P2/P3<br/>blast_radius: list<br/>classification: string"]
    end

    OUT1 --> AG2

    subgraph P2["Phase 2 - Investigate"]
        AG2["Ag2 Investigator<br/>ag2_investigator.py"]
        AG2 -->|"search_runbooks<br/>CORTEX.SEARCH_PREVIEW"| SF_RB[("RAW.RUNBOOKS")]
        AG2 -->|"find_similar_incidents<br/>CORTEX.SIMILARITY"| SF_PI[("RAW.PAST_INCIDENTS")]
        AG2 -->|"query_snowflake<br/>baseline_avg, z_score"| SF_MET2[("METRIC_DEVIATIONS")]
        AG2 --> OUT2["root_cause: string<br/>confidence: 0.0-1.0<br/>evidence_sources: list<br/>recommended_action: string"]
    end

    OUT2 --> AG5

    subgraph P3["Phase 3 - Validate, max 2 rounds"]
        AG5["Ag5 Validator<br/>ag5_validator.py"]
        AG5 -->|"query_snowflake<br/>alternative causes check"| SF_MET3[("METRIC_DEVIATIONS")]
        AG5 --> OUT3["verdict: APPROVED or DEBATE<br/>confidence_adjustment: float<br/>objections: list"]
    end

    OUT3 -->|"DEBATE - re-investigate"| AG2
    OUT3 -->|"APPROVED"| MGR

    subgraph P4["Phase 4 - Act"]
        MGR["Manager<br/>agents/manager.py"]
        MGR -->|"post_slack_alert"| SLA["Slack"]
        MGR -->|"create_github_issue"| GHA["GitHub"]
        MGR -->|"INSERT"| DEC[("AI.DECISIONS<br/>every agent step")]
        MGR -->|"INSERT"| INC[("AI.INCIDENT_HISTORY<br/>final record")]
    end

    style P1 fill:#e8f4f8,stroke:#0066cc
    style P2 fill:#e8f8e8,stroke:#2da44e
    style P3 fill:#fff8e8,stroke:#e36209
    style P4 fill:#f8e8e8,stroke:#cf222e
```

---

## 3. Snowflake Data Model

```mermaid
erDiagram
    RAW_DEPLOY_EVENTS {
        string deploy_id PK
        string service
        string version
        string deployed_by
        string diff_summary
        timestamp deployed_at
    }

    RAW_METRICS {
        timestamp recorded_at
        string service
        string metric_name
        float metric_value
    }

    RAW_RUNBOOKS {
        string id PK
        string service
        string symptom
        string runbook_text
        string severity
    }

    RAW_PAST_INCIDENTS {
        string id PK
        string title
        string service
        string root_cause
        string fix_applied
        int mttr_minutes
    }

    RAW_SERVICE_DEPENDENCIES {
        string service
        string depends_on
    }

    ANALYTICS_METRIC_DEVIATIONS {
        string service
        string metric_name
        float current_value
        float baseline_avg
        float z_score
        string severity
        timestamp recorded_at
    }

    AI_DECISIONS {
        string id PK
        string event_id
        string agent_name
        variant input
        variant output
        string reasoning
        float confidence
        timestamp created_at
    }

    AI_ACTIONS {
        string id PK
        string event_id
        string action_type
        string idempotency_key
        variant payload
        string status
        timestamp executed_at
    }

    AI_INCIDENT_HISTORY {
        string id PK
        string event_id
        string service
        string root_cause
        string fix_applied
        string severity
        float confidence
        int mttr_minutes
        timestamp resolved_at
    }

    RAW_METRICS ||--o{ ANALYTICS_METRIC_DEVIATIONS : "aggregated into dynamic table"
    RAW_DEPLOY_EVENTS ||--o{ AI_DECISIONS : "triggers pipeline"
    AI_DECISIONS }o--|| AI_INCIDENT_HISTORY : "resolved into"
    AI_DECISIONS }o--o{ AI_ACTIONS : "causes"
```

---

## 4. Tool to Agent Matrix

```mermaid
graph LR
    subgraph Agents
        AG1["Ag1 Detector"]
        AG2["Ag2 Investigator"]
        AG5["Ag5 Validator"]
        MGR["Manager"]
    end

    subgraph Tools["tools/"]
        T1["query_snowflake.py<br/>Generic SELECT"]
        T2["search_runbooks.py<br/>CORTEX.SEARCH_PREVIEW"]
        T3["find_similar_incidents.py<br/>CORTEX.SIMILARITY"]
        T4["composio_actions.py<br/>Slack + GitHub"]
        T5["idempotency.py<br/>SHA256 dedup"]
    end

    subgraph External
        SF[("Snowflake<br/>IncidentDNA DB")]
        SL["Slack<br/>#incidents"]
        GH["GitHub<br/>theshubh007/IncidentDNA"]
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

    style AG1 fill:#dbeafe
    style AG2 fill:#dcfce7
    style AG5 fill:#fef9c3
    style MGR fill:#fee2e2
```

---

## 5. LLM Architecture

```mermaid
flowchart LR
    A["CrewAI Agent<br/>ag1, ag2, ag5"] --> B

    B["utils/snowflake_llm.py<br/>SnowflakeCortexLLM<br/>extends BaseChatModel"]

    B --> C["utils/snowflake_conn.py<br/>get_connection()"]
    C --> D[("Snowflake<br/>CORTEX.COMPLETE<br/>llama3.1-70b")]

    D --> E["Raw JSON response<br/>_extract_text()"]
    E --> F["AIMessage<br/>back to CrewAI"]

    style B fill:#0066cc,color:#fff
    style D fill:#29B5E8,color:#fff
```

---

## 6. Directory Structure

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

## 7. Integration Contracts (P1 to P2 to P3)

```mermaid
sequenceDiagram
    participant P1 as P1 Snowflake SQL
    participant P2 as P2 Agent Layer
    participant P3 as P3 Frontend

    P1->>P2: RAW.RUNBOOKS (Cortex Search enabled)
    P1->>P2: RAW.PAST_INCIDENTS
    P1->>P2: RAW.SERVICE_DEPENDENCIES
    P1->>P2: ANALYTICS.METRIC_DEVIATIONS (dynamic table)

    P2->>P3: run_incident_crew(event) returns result dict
    P2->>P3: AI.DECISIONS table (agent reasoning steps)
    P2->>P3: AI.ACTIONS table (Slack/GitHub audit log)
    P2->>P3: AI.INCIDENT_HISTORY (MTTR + resolution)

    P3->>P1: Writes RAW.DEPLOY_EVENTS (trigger_listener)
    P3->>P1: Writes RAW.METRICS (spike injection)
```
