# 🧬 IncidentDNA — Autonomous Incident Intelligence on Snowflake

> **Hackathon:** Llama Lounge × Snowflake  
> **Team size:** 4  
> **Stack:** Snowflake Cortex · CrewAI · Composio · Streamlit  
> **Goal:** Detect, investigate, and resolve production incidents autonomously — learning from every incident like DNA.

---

## 📑 Table of Contents

1. [What Is IncidentDNA?](#1-what-is-incidentdna)
2. [System Architecture](#2-system-architecture)
3. [End-to-End Data Flow](#3-end-to-end-data-flow)
4. [Snowflake Data Model](#4-snowflake-data-model)
5. [Agent Design — 5 Agents + Manager](#5-agent-design--5-agents--manager)
6. [How Agents Debate & Reach a Decision](#6-how-agents-debate--reach-a-decision)
7. [Cortex AI Functions — Which Model Does What](#7-cortex-ai-functions--which-model-does-what)
8. [Composio Integration — Triggers + Actions](#8-composio-integration--triggers--actions)
9. [Duplicate Prevention — Idempotency Layer](#9-duplicate-prevention--idempotency-layer)
10. [Handling Brand-New / Unknown Issues](#10-handling-brand-new--unknown-issues)
11. [Evaluation Metrics](#11-evaluation-metrics)
12. [Team Task Assignments](#12-team-task-assignments)
13. [Hour-by-Hour Execution Plan](#13-hour-by-hour-execution-plan)
14. [Project Folder Structure](#14-project-folder-structure)
15. [Quick Setup Checklist](#15-quick-setup-checklist)
16. [Demo Strategy](#16-demo-strategy)
17. [FAQ for Judges](#17-faq-for-judges)

---

## 1. What Is IncidentDNA?

IncidentDNA is an **autonomous incident management system** that:

- **Detects** production anomalies the moment a deploy lands — using Snowflake Dynamic Tables and `AI_CLASSIFY`  
- **Investigates** root cause using a 3-source evidence chain: Runbooks (Cortex Search) + Past Incidents (AI_SIMILARITY) + Slack Context (Composio)  
- **Validates** every diagnosis using an adversarial LLM-as-Judge agent (Ag5) that stress-tests hypotheses before any action is taken  
- **Acts** by posting Slack alerts and creating GitHub issues via Composio — with full idempotency (no duplicates)  
- **Learns** by storing every resolved incident as new DNA, so unknown issues become known ones over time  

**The pitch in one sentence:**  
> *"IncidentDNA doesn't alert you to problems — it diagnoses them, debates the diagnosis internally, acts on the best answer, and gets smarter with every incident."*

---

## 2. System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          COMPOSIO TRIGGERS (Real-time)                       │
│                                                                               │
│   GitHub Repo                              Slack Workspace                   │
│   GITHUB_COMMIT_EVENT ──────────────────▶  SLACK_RECEIVE_MESSAGE            │
│   GITHUB_PR_EVENT                                                             │
└──────────────────────────────┬────────────────────────────┬──────────────────┘
                               │ WebSocket                   │ WebSocket
                               ▼                             ▼
               ┌──────────────────────────────────────────────────┐
               │             trigger_listener.py                   │
               │  on_github_commit()  →  INSERT RAW.DEPLOY_EVENTS  │
               │  on_github_pr()      →  INSERT RAW.DEPLOY_EVENTS  │
               │  on_slack_message()  →  INSERT RAW.SLACK_MESSAGES │
               │  inject_metric_spike() → INSERT RAW.METRICS       │
               └───────────────────────┬──────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                       SNOWFLAKE — The Brain                                  │
│                                                                               │
│  RAW Schema              AI Schema               ANALYTICS Schema            │
│  ─────────────           ──────────               ────────────────           │
│  METRICS                 ANOMALY_RESULTS          MTTR_METRICS (DT)          │
│  DEPLOY_EVENTS           DECISIONS                BLAST_RADIUS (DT)          │
│  SLACK_MESSAGES          ACTIONS                  METRIC_DEVIATIONS (DT)     │
│  RUNBOOKS                INCIDENT_HISTORY                                     │
│  SERVICE_DEPS            AUDIT_LOG                                            │
│                          INCIDENT_LIFECYCLE                                   │
│                                                                               │
│  Dynamic Tables: AUTO-COMPUTE anomalies every 60s                            │
│  Stream on anomaly_results: TRIGGERS Snowflake Task                          │
│  Task: CALLS stored procedure → fires CrewAI                                 │
│                                                                               │
│  Cortex AI Functions:                                                         │
│  • AI_CLASSIFY  • AI_SIMILARITY  • AI_SENTIMENT  • AI_COMPLETE               │
│  Cortex Search Service: RUNBOOK_SEARCH (hybrid semantic + keyword)           │
└───────────────────────────────┬───────────────────────────────────────────────┘
                                │ Stored Procedure triggers CrewAI
                                ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                     CREWAI — 5 Agents + Manager                              │
│                                                                               │
│   🧠 MANAGER                                                                 │
│      ├─▶ Ag1 DETECTOR      — Classify severity, measure blast radius         │
│      ├─▶ Ag2 INVESTIGATOR  — 3-source evidence chain (runbook+past+slack)    │
│      ├─▶ Ag5 VALIDATOR     — LLM-as-Judge, adversarial stress-test           │
│      │        (Ag2 ↔ Ag5 debate loop, max 2 rounds)                          │
│      ├─▶ Ag3 FIX ADVISOR   — Ranked fix options with time estimates          │
│      └─▶ Ag4 ACTION AGENT  — Composio: Slack alert + GitHub issue + DNA store│
└───────────────────────────────┬───────────────────────────────────────────────┘
                                │ Composio Actions
          ┌─────────────────────┼─────────────────────┐
          ▼                     ▼                       ▼
   Slack #incident-alerts   GitHub Issue           Snowflake
   (Composio)               (Composio)             AI.INCIDENT_HISTORY
                                                   AI.ACTIONS
                                                   AI.DECISIONS
```

---

## 3. End-to-End Data Flow

```
[1]  Teammate pushes commit to GitHub repo
         │
         ▼
[2]  Composio GITHUB_COMMIT_EVENT trigger fires
     trigger_listener.py receives the event
         │
         ├─▶ INSERT into RAW.DEPLOY_EVENTS  (real commit data)
         └─▶ inject_metric_spike()          (simulated metric spike for demo)
         │
         ▼
[3]  Snowflake Dynamic Table METRIC_DEVIATIONS refreshes (every 60s)
     Compares current metrics against 7-day rolling baseline
     Flags services with deviation > 2 standard deviations
         │
         ▼
[4]  Dynamic Table ANOMALY_RESULTS computes severity + blast radius
     AI_CLASSIFY categorizes: HIGH / MEDIUM / LOW
         │
         ▼
[5]  Snowflake Stream captures new anomaly row
     Snowflake Task fires → calls Stored Procedure
     Stored Procedure → HTTP call to CrewAI endpoint
         │
         ▼
[6]  CrewAI Manager receives: {service, severity, metrics, deploy_id}
     Orchestrates agents in hierarchical process
         │
         ├─▶ Ag1: Classify severity, find blast radius dependencies
         ├─▶ Ag2: Search runbooks (Cortex Search)
         │         Search past incidents (AI_SIMILARITY)
         │         Search Slack (Composio tool)
         │         → Produce hypothesis + confidence score
         ├─▶ Ag5: Challenge hypothesis
         │         Test 2-3 alternatives against Snowflake data
         │         Approve / Reject / Conditionally Approve
         │   (if Rejected → Ag2 revises → Ag5 re-evaluates, max 2 rounds)
         ├─▶ Ag3: Generate ranked fix options
         └─▶ Ag4: Check idempotency → Execute Composio actions
                   → POST Slack alert
                   → CREATE GitHub issue
                   → STORE incident DNA
                   → LOG to AI.ACTIONS
         │
         ▼
[7]  Snowflake Task RESOLUTION_CHECK polls metrics every 5 min
     When metrics return to baseline → marks incident RESOLVED
     MTTR_METRICS Dynamic Table updates automatically
         │
         ▼
[8]  Streamlit dashboard shows:
     - Live anomaly chart (Plotly)
     - Real-time reasoning trace (agent steps)
     - MTTR analytics
     - Actions log (what was done, when, by whom)
```

---

## 4. Snowflake Data Model

### 4.1 Schemas

| Schema | Purpose |
|---|---|
| `RAW` | Raw ingested data: metrics, deploys, Slack messages, runbooks, dependencies |
| `AI` | Agent outputs: decisions, actions, incident history, anomaly results |
| `ANALYTICS` | Dynamic Tables: computed deviations, MTTR breakdowns, blast radius |

### 4.2 Key Tables

```sql
-- RAW Schema
RAW.METRICS              (service, metric_name, value, timestamp)
RAW.DEPLOY_EVENTS        (event_id, service, pr_title, actor, files_changed, commit_sha, timestamp)
RAW.SLACK_MESSAGES       (msg_id, channel, user, text, timestamp)
RAW.RUNBOOKS             (doc_id, title, service, content)
RAW.SERVICE_DEPENDENCIES (service, depends_on, criticality)

-- AI Schema
AI.ANOMALY_RESULTS       (anomaly_id, service, severity, metric_name, deviation_pct, detected_at)
AI.DECISIONS             (decision_id, incident_id, agent_name, step, reasoning, confidence, timestamp)
AI.ACTIONS               (action_id, incident_id, action_type, target, status, composio_id, executed_at)
AI.INCIDENT_HISTORY      (incident_id, service, description, root_cause, resolution, mttr_minutes)
AI.INCIDENT_LIFECYCLE    (incident_id, event_type, timestamp)  -- detected/investigated/acted/resolved
AI.AUDIT_LOG             (incident_id, action_type, status, note, timestamp)

-- ANALYTICS Schema (Dynamic Tables — auto-computed)
ANALYTICS.METRIC_DEVIATIONS  (service, metric, deviation_pct, is_anomaly)
ANALYTICS.ANOMALY_RESULTS    (service, severity, blast_radius, classified_at)
ANALYTICS.BLAST_RADIUS       (incident_id, affected_service, predicted_impact)
ANALYTICS.MTTR_METRICS       (incident_id, detection_min, investigation_min, action_min, resolution_min, total_mttr)
```

### 4.3 Cortex Search Service

```sql
CREATE OR REPLACE CORTEX SEARCH SERVICE AI.RUNBOOK_SEARCH
  ON RAW.RUNBOOKS
  WAREHOUSE = COMPUTE_WH
  TARGET_LAG = '1 hour'
  EMBEDDING_MODEL = 'snowflake-arctic-embed-l-v2.0'
  ATTRIBUTES = service, title
  COLUMNS = doc_id, title, service, content
  AS (SELECT doc_id, title, service, content FROM RAW.RUNBOOKS);
```

> **No external embedding model needed.** Snowflake generates and manages all embeddings automatically.

---

## 5. Agent Design — 5 Agents + Manager

### 🧠 Manager Agent
- **Role:** Orchestrator. Hierarchical process. Controls task routing.  
- **Inputs:** Anomaly alert from Snowflake Task  
- **Decisions:** Route to agents, score debate outcomes, pick final hypothesis, enforce 2-round limit  
- **Who builds it:** P2

---

### 🔵 Ag1 — Detector
- **Role:** Severity classification + blast radius mapping  
- **Tools:** `query_snowflake` (reads METRIC_DEVIATIONS, SERVICE_DEPENDENCIES)  
- **Outputs:** `{severity, error_rate_delta, blast_radius[], re_verify_after_investigation}`  
- **Special:** Gets called TWICE — once to classify, once to re-verify after Ag2 + Ag5 finish  
- **Who builds it:** P2

---

### 🔍 Ag2 — Investigator
- **Role:** Root cause evidence gathering — 3 sources  
- **Tools:**  
  - `search_runbooks` → queries Cortex Search (semantic + keyword)  
  - `find_similar_incidents` → uses `AI_SIMILARITY` on `AI.INCIDENT_HISTORY`  
  - `search_slack` → Composio `SLACKBOT_SEARCH_MESSAGES`  
  - `analyze_deploy_context` → Composio `GITHUB_GET_COMMIT` on triggering commit  
  - `ai_complete_reasoning` → `AI_COMPLETE(Llama-3.1-70b)` for first-principles when no match  
- **Outputs:** `{root_cause, confidence, evidence[], hypothesis_type}` (known / first-principles)  
- **Who builds it:** P2

---

### ⚖️ Ag5 — Validator (LLM-as-Judge)
- **Role:** Adversarial stress-testing of Ag2's hypothesis  
- **Tools:**  
  - `query_contradiction_metrics` → queries metrics Ag2 did NOT look at  
  - `check_blast_scope` → verifies actual vs predicted blast radius  
  - `check_temporal_pattern` → checks if anomaly happened before without a deploy  
  - `generate_alternatives` → `AI_COMPLETE` with skeptical system prompt  
- **Logic:**
  - Tests 2-3 alternative hypotheses against data  
  - If alternative eliminated → confidence goes UP  
  - If alternative survives → include as secondary hypothesis  
  - If internal inconsistency found → REJECT, Ag2 revises  
- **Exit conditions:**
  - `APPROVED` — proceed to Ag3  
  - `REJECTED` — Ag2 re-investigates with Ag5's feedback (max 2 rounds)  
  - `CONDITIONALLY_APPROVED` — multiple hypotheses passed to Ag3 + Ag4  
- **Who builds it:** P2

---

### 🔧 Ag3 — Fix Advisor
- **Role:** Generate ranked, actionable fix options  
- **Input:** Validated hypothesis from Manager  
- **Outputs:** `fix_options[]` with `{description, time_to_recover, risk_level, recommended}`  
- **Example output:**
  ```
  Option A: Rollback deploy — 3-5 min recovery, low risk → RECOMMENDED (Friday evening)
  Option B: Increase connection pool 50→100 — 8-12 min recovery, medium risk
  ```
- **Who builds it:** P2

---

### 🚀 Ag4 — Action Agent
- **Role:** Execute real-world actions via Composio — with idempotency  
- **Tools:** Composio `SLACKBOT_CHAT_POST_MESSAGE`, `GITHUB_CREATE_ISSUE`, `store_incident_dna`, `log_action`  
- **Logic:** Checks `AI.ACTIONS` table before EVERY call (see Section 9)  
- **Outputs:** `actions_taken[]` → each action logged to `AI.ACTIONS`  
- **Who builds it:** P3

---

## 6. How Agents Debate & Reach a Decision

### The Debate Loop

```
Ag2 produces hypothesis
        │
        ▼
Ag5 challenges it (runs 4 checks)
        │
        ├── APPROVED (all alternatives eliminated, no inconsistencies)
        │       └─▶ Confidence +5-10 pts → Proceed to Ag3
        │
        ├── REJECTED (inconsistency or better alternative found)
        │       └─▶ Ag2 gets Ag5's feedback → revises hypothesis → Round 2
        │               Ag5 re-evaluates
        │               If still REJECTED → Manager overrides with CONDITIONALLY_APPROVED
        │
        └── CONDITIONALLY_APPROVED (>1 viable hypothesis)
                └─▶ Both hypotheses ranked → Ag4 sends alert with both + diagnostic commands
```

### Manager Scoring (Tiebreaker)

| Factor | Max Points |
|---|---|
| Number of corroborating evidence sources (0-5) | 5 |
| Number of alternatives eliminated by Ag5 (0-3) | 3 |
| Timing alignment (instant vs gradual vs periodic) | 2 |
| Scope alignment (blast radius matches prediction) | 2 |

> **Hard limits:** Max 2 debate rounds. Max 30s per agent. If rounds exhausted → Manager picks highest-scored hypothesis, includes secondary, proceeds.

### Confidence Score Rules

| Situation | Confidence |
|---|---|
| 3 sources agree (runbook + past incident + Slack) | 85-95% → AUTO-ACT |
| 2 sources agree | 60-80% → ACT with NEEDS-REVIEW tag |
| First principles only (no matches) | 40-60% → ALERT with HUMAN-VERIFY flag |
| Sources disagree or < 40% | < 40% → ESCALATE, no auto-action |

---

## 7. Cortex AI Functions — Which Model Does What

| Task | Snowflake Function | Model | Managed By |
|---|---|---|---|
| Find matching runbooks | `Cortex Search` | `snowflake-arctic-embed-l-v2.0` | ✅ Snowflake — automatic |
| Find similar past incidents | `AI_SIMILARITY(text1, text2)` | Snowflake embedding model | ✅ Snowflake — automatic |
| Severity classification | `AI_CLASSIFY(text, categories)` | Built-in classifier | ✅ Snowflake — automatic |
| Slack sentiment | `AI_SENTIMENT(text)` | Built-in sentiment model | ✅ Snowflake — automatic |
| Root cause reasoning | `AI_COMPLETE('llama3.1-70b', prompt)` | Llama 3.1-70B | 🟡 You specify model name |
| Fix recommendation | `AI_COMPLETE('llama3.1-70b', prompt)` | Llama 3.1-70B | 🟡 You specify model name |
| Alternative hypothesis generation | `AI_COMPLETE('llama3.1-70b', prompt)` | Llama 3.1-70B | 🟡 You specify model name (skeptical prompt) |
| Simple summaries | `AI_COMPLETE('llama3.1-8b', prompt)` | Llama 3.1-8B | 🟡 Cheaper, for simple tasks |

> **Critical:** No OpenAI API. No external embedding service. No vector database. Zero self-managed embedding pipelines. Snowflake handles all retrieval. Llama 3.1-70B runs inside Snowflake Cortex.

---

## 8. Composio Integration — Triggers + Actions

### 8.1 Setup (P3 does this in Hour 0-2)

```bash
pip install composio-crewai
composio login
composio add github      # OAuth in browser → 5 min
composio add slack       # OAuth in browser → 5 min

# Enable triggers
composio triggers enable github_commit_event
composio triggers enable github_pull_request_event
composio triggers enable slack_receive_message

# Test: push a commit → check listener output
```

### 8.2 Trigger Listener (trigger_listener.py)

```python
from composio import Composio
from composio_crewai import ComposioToolSet

composio_client = Composio()
listener = composio_client.triggers.subscribe()

@listener.callback(filters={"trigger_name": "GITHUB_COMMIT_EVENT"})
def on_github_commit(event):
    payload = event.payload
    deploy_event = {
        "event_id": f"DEP-{payload['commit_id'][:8]}",
        "service": detect_service(payload['files_changed']),
        "pr_title": payload['message'],
        "actor": payload['author'],
        "files_changed": len(payload.get('added', []) + payload.get('modified', [])),
        "commit_sha": payload['commit_id'],
        "timestamp": payload['timestamp'],
    }
    insert_deploy_event(snowflake_conn, deploy_event)
    inject_metric_spike(snowflake_conn, deploy_event['service'])  # sim spike

@listener.callback(filters={"trigger_name": "SLACK_RECEIVE_MESSAGE"})
def on_slack_message(event):
    payload = event.payload
    insert_slack_message(snowflake_conn, {
        "channel": payload['channel'],
        "user": payload['user'],
        "text": payload['text'],
        "timestamp": payload['ts'],
    })

print("👂 Listening for events...")
listener.wait_forever()
```

### 8.3 Composio Actions Used by Ag4

```python
from composio_crewai import ComposioToolSet, Action

toolset = ComposioToolSet()

# Slack alert
toolset.execute_action(
    action=Action.SLACKBOT_CHAT_POST_MESSAGE,
    params={"channel": "#incident-alerts", "text": format_slack_message(findings)}
)

# GitHub issue
toolset.execute_action(
    action=Action.GITHUB_CREATE_ISSUE,
    params={
        "owner": "your-org",
        "repo": "incidents",
        "title": f"[{incident_id}] {service} — {root_cause}",
        "body": format_github_body(findings),
        "labels": ["incident", severity.lower(), "auto-generated"]
    }
)
```

### 8.4 Data Sources — Real vs Simulated

| Data | Source | Trigger | Real or Simulated? |
|---|---|---|---|
| Deploy events | GitHub | `GITHUB_COMMIT_EVENT` | ✅ **REAL** |
| Slack team messages | Slack | `SLACK_RECEIVE_MESSAGE` | ✅ **REAL** |
| Metric spikes | `inject_metric_spike()` | After deploy trigger | ⚠️ Simulated |
| Baseline metrics | Seed script | 7-day historical data | ⚠️ Seeded |
| Runbooks | Hand-written (5 docs) | Loaded once | ⚠️ Written by team |
| Past incidents | Seed script (10 rows) | Training DNA | ⚠️ Seeded |
| Service dependencies | Hand-written (6 rows) | Loaded once | ⚠️ Hand-crafted |

---

## 9. Duplicate Prevention — Idempotency Layer

### The Problem
If Snowflake Task re-triggers (network glitch, retry), Ag4 would send duplicate Slack messages and create duplicate GitHub issues.

### The Solution — `utils/idempotency.py`

```python
def safe_execute(conn, incident_id, action_type, execute_fn):
    """
    Universal wrapper for every external action.
    1. Check AI.ACTIONS for existing successful execution
    2. If found → SKIP + log to audit
    3. If not found → try execute → log success
    4. If execute fails → log failure → return fallback (Streamlit shows 'Simulated' badge)
    """
    # Step 1: Dedup check
    cursor = conn.cursor()
    cursor.execute("""
        SELECT COUNT(*) FROM AI.ACTIONS
        WHERE incident_id = %s AND action_type = %s
          AND status IN ('sent', 'created', 'stored')
    """, (incident_id, action_type))
    if cursor.fetchone()[0] > 0:
        log_audit(conn, incident_id, action_type, "SKIPPED_DUPLICATE")
        return {"status": "skipped", "reason": "duplicate"}

    # Step 2: Execute
    try:
        result = execute_fn()
        log_action(conn, incident_id, action_type, "sent", str(result))
        return {"status": "sent", "result": result}
    except Exception as e:
        log_action(conn, incident_id, action_type, "FAILED", str(e))
        return {"status": "fallback", "error": str(e)}
```

### Each scenario — what happens

| Scenario | Result |
|---|---|
| First run | Check: not found → Execute → Success → Log `sent` |
| Pipeline retry (same incident_id) | Check: found → SKIP → Log `SKIPPED_DUPLICATE` → No duplicate sent |
| Composio fails | Check: not found → Execute → Exception → Log `FAILED` → Streamlit shows "Simulated" badge |

---

## 10. Handling Brand-New / Unknown Issues

### When No Runbook and No Past Incident Match

```
Ag2 searches Cortex Search    → best relevance: 0.41  (below 0.5 threshold) → SKIP
Ag2 searches AI_SIMILARITY    → best match: 0.38       (below 0.6 threshold) → SKIP
                                       │
                      ┌────────────────▼────────────────┐
                      │   FIRST PRINCIPLES MODE           │
                      │                                   │
                      │  Input to AI_COMPLETE:            │
                      │  • Files changed (from GitHub)    │
                      │  • Metric pattern shape           │
                      │  • Timing: deploy → anomaly gap   │
                      │  • Blast radius observed          │
                      │                                   │
                      │  Output from AI_COMPLETE:         │
                      │  • Hypothesis + 55% confidence    │
                      │  • Evidence type: "reasoning"     │
                      └────────────────┬────────────────┘
                                       │
                      ┌────────────────▼────────────────┐
                      │   Ag5 VALIDATES (skeptical mode) │
                      │  Tests alternatives               │
                      │  Eliminates what it can           │
                      │  Narrows down resource type       │
                      │  Adds diagnostic commands         │
                      └────────────────┬────────────────┘
                                       │
                      ┌────────────────▼────────────────┐
                      │   ALERT (HUMAN VERIFY needed)    │
                      │  "New issue — no historical match│
                      │   Primary guess: X (68%)          │
                      │   Secondary: Y (15%)              │
                      │   Diagnostic commands attached"  │
                      └────────────────┬────────────────┘
                                       │
                      ┌────────────────▼────────────────┐
                      │   LEARNING LOOP                  │
                      │  Human resolves → root cause     │
                      │  stored in AI.INCIDENT_HISTORY   │
                      │                                  │
                      │  Next time: AI_SIMILARITY hits   │
                      │  Unknown → Known. System learned.│
                      └──────────────────────────────────┘
```

### Metric Pattern → Failure Type Mapping

| Metric Pattern | Most Likely Cause |
|---|---|
| Instant error rate spike, latency normal | External dependency failure or logic bug |
| Instant latency spike + error rate spike | Resource exhaustion (connection pool, CPU) |
| Gradual latency climb over hours | Memory leak |
| Only one service affected (not dependents) | Code change on that specific service |
| Multiple unrelated services degrading | Shared infrastructure issue |
| Periodic anomaly (same time each day) | Scheduled job, not a deploy issue |

---

## 11. Evaluation Metrics

| Metric | Definition | Target | How to Measure |
|---|---|---|---|
| **MTTD** (Mean Time to Detect) | Deploy → Anomaly classified | < 2 min | `AI.INCIDENT_LIFECYCLE`: `detected_at - deploy_at` |
| **MTTI** (Mean Time to Investigate) | Detected → Root cause produced | < 60 sec | `DECISIONS`: last_agent_step_at - detected_at |
| **MTTA** (Mean Time to Act) | Root cause → Composio actions done | < 10 sec | `ACTIONS`: executed_at - investigation_done_at |
| **MTTR** (Mean Time to Resolve) | Deploy → Metrics back to normal | < 15 min | `MTTR_METRICS` Dynamic Table |
| **Investigation Accuracy** | Correct root cause vs designed cause | > 90% (known issues) | Run 3 scenarios, compare hypothesis to truth |
| **False Positive Rate** | Alerts when nothing is wrong | 0% | Run 10 min with baseline data only |
| **Validation Pass Rate** | % hypotheses Ag5 approves first try | 70-80% | Count APPROVED vs REJECTED in DECISIONS table |
| **Confidence Calibration** | HIGH confidence → actually correct | HIGH ≥ 90% correct | Cross-reference with resolved incidents |
| **Debate Rounds** | Ag2 ↔ Ag5 round count per incident | 1 (known) / 2 (unknown) | Count re-investigation tasks per incident |

> **Industry baseline for comparison:**  
> MTTR industry average: **47 minutes.** IncidentDNA target: **< 15 minutes.**

---

## 12. Team Task Assignments

### 🔵 P1 — Prem (Data Engineer + Snowflake)

> **You own everything inside Snowflake.** Tables, Dynamic Tables, Streams, Tasks, AI functions — all yours.

**Responsibilities:**
- Create Snowflake database, schemas (`RAW`, `AI`, `ANALYTICS`)
- Write all DDL (11 tables)
- Seed ALL data: metrics (7-day baseline), runbooks (5 docs), past incidents (10 rows), service dependencies, Slack messages
- Create `CORTEX SEARCH SERVICE` for runbooks
- Create 3 Dynamic Tables: `METRIC_DEVIATIONS`, `ANOMALY_RESULTS`, `MTTR_METRICS`
- Create `BLAST_RADIUS` Dynamic Table with `AI_CLASSIFY` for severity
- Create Snowflake Stream on `AI.ANOMALY_RESULTS`
- Create 2 Snowflake Tasks: investigation trigger + resolution check
- Create Stored Procedure that calls CrewAI HTTP endpoint
- Tune Dynamic Table lag < 90s end-to-end
- Support P2/P3/P4 with Snowflake debugging

**Key files you own:**
```
snowflake/
  01_schema_ddl.sql
  02_seed_data.sql
  03_dynamic_tables.sql
  04_cortex_search.sql
  05_stream_task.sql
  06_stored_procedure.sql
```

---

### 🟣 P2 — Person 2 (Backend + CrewAI Agents)

> **You own all 5 agents + Manager.** If it thinks, reasons, or decides — it's yours.

**Responsibilities:**
- Install CrewAI, scaffold project structure
- Build `Manager` with hierarchical process
- Build **Ag1** (Detector): severity + blast radius
- Build **Ag2** (Investigator): 3 custom tools — `search_runbooks`, `find_similar_incidents`, `analyze_deploy_context`
- Build **Ag5** (Validator/LLM-Judge): 4 validation checks, debate loop logic
- Build **Ag3** (Fix Advisor): ranked fix options
- Build **Ag4** (Action Agent): wraps Composio tools with idempotency
- Implement Manager scoring rubric (evidence sources, elimination count, timing, scope)
- Enforce debate loop limits (max 2 rounds, 30s timeout)
- Ensure all agents log reasoning to `AI.DECISIONS`
- Set `temperature=0` on all agents for deterministic output

**Key files you own:**
```
agents/
  manager.py
  ag1_detector.py
  ag2_investigator.py
  ag3_fix_advisor.py
  ag4_action_agent.py
  ag5_validator.py

tools/
  search_runbooks.py
  find_similar_incidents.py
  query_snowflake.py
  analyze_deploy_context.py
  ai_complete_reasoning.py
```

---

### 🟢 P3 — Person 3 (Integrations + Composio)

> **You own everything that touches the outside world.** Triggers, Slack, GitHub, idempotency — all yours.

**Responsibilities:**
- Set up Composio account, authenticate GitHub + Slack
- Enable triggers: `GITHUB_COMMIT_EVENT`, `GITHUB_PR_EVENT`, `SLACK_RECEIVE_MESSAGE`
- Write `trigger_listener.py` — WebSocket listener connecting Composio to Snowflake
- Write `inject_metric_spike()` — simulates metric anomaly after real deploy
- Build Slack message formatter (rich, structured Slack Block Kit format)
- Build GitHub issue formatter (markdown body with evidence chain)
- Write `utils/idempotency.py` (the `safe_execute` wrapper)
- Build fallback mode: if Composio fails → write to AI.FALLBACK_DISPLAY → Streamlit shows "Simulated" badge
- Integration testing with P2's Ag4

**Key files you own:**
```
trigger_listener.py
utils/
  idempotency.py
  slack_formatter.py
  github_formatter.py
  fallback.py
```

---

### 🟠 P4 — Person 4 (Frontend + Streamlit + Demo)

> **You own everything the judge sees.** If it's on screen — it's yours.

**Responsibilities:**
- Streamlit app with 4-page navigation
- **Page 1 — Live Console:** Real-time anomaly chart (Plotly), current incident status
- **Page 2 — Simulate Deploy:** Big button → triggers pipeline; shows timer to resolution
- **Page 3 — Reasoning Trace:** Shows AI.DECISIONS table live; each agent step with timestamp, evidence, confidence
- **Page 4 — MTTR Analytics:** Bar chart breakdown (detection + investigation + action + recovery) vs industry baseline
- Real-time polling (every 3 seconds) using `st.empty()` + `time.sleep(3)`
- Status indicators: 🟢 Healthy / 🔴 Anomaly Detected / 🔵 Investigating / ✅ Resolved
- When Ag5 debates: show round 1 / round 2 in reasoning trace with CHALLENGE → VERDICT labels
- "Simulated" badge on fallback actions
- RUN_ID reset button for judge demo re-runs
- Stretch: Cortex Analyst chat window (natural language SQL queries)
- Record demo video, prep judge pitch

**Key files you own:**
```
app/
  main.py                (navigation)
  pages/
    live_console.py
    simulate_deploy.py
    reasoning_trace.py
    mttr_analytics.py
  utils/
    snowflake_connector.py
    polling.py
```

---

## 13. Hour-by-Hour Execution Plan

```
HOUR 0-2: Independent Setup (NO dependencies between people)
──────────────────────────────────────────────────────────────
P1: Create Snowflake account, database, schemas, run DDL
P2: pip install crewai composio-crewai, scaffold project, Agent skeletons
P3: composio login, add github, add slack, enable triggers, test with real push
P4: Streamlit boilerplate 4 pages, GitHub repo, navigation working

HOUR 2-6: Build Foundation (P1 critical path)
──────────────────────────────────────────────────────────────
P1: Seed all data, create Dynamic Tables, create Cortex Search Service
    ── P2 needs tables to test tools ──▶ DONE by hour 4
P2: Build 3 creai tools (query_snowflake, search_runbooks, find_similar)
P3: Write trigger_listener.py, connect to Snowflake INSERT, test end-to-end with push
P4: Page 1 (Live Console with Plotly chart), Page 2 (Simulate button)

HOUR 6-12: Everything Connects (Critical Integration)
──────────────────────────────────────────────────────────────
P1: Create Stream + Task, Stored Procedure calling CrewAI, full pipeline test
P2: Build all 5 agents + Manager, debate loop, reasoning logging
P3: Wire Composio tools into Ag4, build idempotency.py, test Slack + GitHub
P4: Page 3 (Reasoning Trace from AI.DECISIONS), Page 4 (MTTR chart)

HOUR 12-18: Integration Testing (ALL 4 TOGETHER)
──────────────────────────────────────────────────────────────
ALL: End-to-end test — push commit → see Slack alert + GitHub issue + reasoning trace
P1: Fix timing, tune Dynamic Table lag < 90s
P2: Fix agent reliability, temperature=0, deterministic output
P3: Fix auth issues, test fallback mode
P4: Fix polling, status indicators, show debate rounds in trace

HOUR 18-22: Polish
──────────────────────────────────────────────────────────────
P4: UI polish, RUN_ID reset, confidence color coding
P2: STRETCH — auto-postmortem generation by Ag3
P1: STRETCH — Semantic View + Cortex Analyst
P3: STRETCH — approval-gated fix (human clicks approve before action executes)

HOUR 22-24: Demo Prep
──────────────────────────────────────────────────────────────
P4: Record demo video (Screen + audio)
ALL: Rehearse judge pitch — 2 min setup, 3 min live demo, 2 min Q&A prep
Prep answers for: "Is the data fake?" "Why not PagerDuty?" "What about new issues?"
```

---

## 14. Project Folder Structure

```
IncidentDNA/
├── README.md
│
├── snowflake/
│   ├── 01_schema_ddl.sql           # P1 — Create all tables
│   ├── 02_seed_data.sql            # P1 — Seed metrics, runbooks, past incidents
│   ├── 03_dynamic_tables.sql       # P1 — METRIC_DEVIATIONS, ANOMALY_RESULTS, MTTR_METRICS
│   ├── 04_cortex_search.sql        # P1 — Create RUNBOOK_SEARCH cortex service
│   ├── 05_stream_task.sql          # P1 — Stream on anomaly + Task trigger
│   └── 06_stored_procedure.sql     # P1 — Calls CrewAI endpoint
│
├── agents/
│   ├── manager.py                  # P2 — Hierarchical manager, debate loop, scoring
│   ├── ag1_detector.py             # P2 — Severity + blast radius
│   ├── ag2_investigator.py         # P2 — 3-source investigation + first principles
│   ├── ag3_fix_advisor.py          # P2 — Ranked fix options
│   ├── ag4_action_agent.py         # P2+P3 — Composio execution
│   └── ag5_validator.py            # P2 — LLM-as-Judge adversarial validation
│
├── tools/
│   ├── search_runbooks.py          # P2 — Cortex Search query tool
│   ├── find_similar_incidents.py   # P2 — AI_SIMILARITY query tool
│   ├── query_snowflake.py          # P2 — General Snowflake query tool
│   ├── analyze_deploy_context.py   # P2 — Composio GitHub context fetch
│   └── ai_complete_reasoning.py    # P2 — AI_COMPLETE wrapper
│
├── utils/
│   ├── idempotency.py              # P3 — safe_execute dedup wrapper
│   ├── slack_formatter.py          # P3 — Slack message format
│   ├── github_formatter.py         # P3 — GitHub issue markdown format
│   └── fallback.py                 # P3 — Fallback display for failed Composio
│
├── trigger_listener.py             # P3 — Composio WebSocket trigger handler
│
├── app/
│   ├── main.py                     # P4 — Streamlit navigation
│   └── pages/
│       ├── live_console.py         # P4 — Real-time Plotly chart
│       ├── simulate_deploy.py      # P4 — Simulate button + timer
│       ├── reasoning_trace.py      # P4 — Agent step-by-step with debate rounds
│       └── mttr_analytics.py       # P4 — MTTR breakdown chart vs industry
│
├── requirements.txt
└── .env.example                    # SNOWFLAKE_ACCOUNT, COMPOSIO_API_KEY, etc.
```

---

## 15. Quick Setup Checklist

### Everyone does (Hour 0)

```bash
git clone <repo>
cd IncidentDNA
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # fill in your credentials
```

### P1 — Snowflake (Hour 0-1)

```bash
# Run in order:
snowsql -f snowflake/01_schema_ddl.sql
snowsql -f snowflake/02_seed_data.sql
snowsql -f snowflake/03_dynamic_tables.sql
snowsql -f snowflake/04_cortex_search.sql
snowsql -f snowflake/05_stream_task.sql
snowsql -f snowflake/06_stored_procedure.sql

# Verify Dynamic Tables are refreshing:
SELECT * FROM ANALYTICS.METRIC_DEVIATIONS LIMIT 10;
SELECT * FROM AI.ANOMALY_RESULTS LIMIT 10;
```

### P2 — CrewAI (Hour 0-1)

```bash
pip install crewai==0.28.0 crewai-tools composio-crewai
python -c "import crewai; print(crewai.__version__)"

# Test Snowflake connection:
python tools/query_snowflake.py
```

### P3 — Composio (Hour 0-1)

```bash
pip install composio-crewai
composio login
composio add github
composio add slack
composio triggers enable github_commit_event
composio triggers enable slack_receive_message

# Test — push a commit and check:
python trigger_listener.py
# Should print: "🚀 Real deploy detected: <your commit message>"
```

### P4 — Streamlit (Hour 0-1)

```bash
pip install streamlit plotly pandas
streamlit run app/main.py
# Should open 4-page app in browser
```

### Required `.env` Keys

```
SNOWFLAKE_ACCOUNT=
SNOWFLAKE_USER=
SNOWFLAKE_PASSWORD=
SNOWFLAKE_DATABASE=INCIDENTDNA
SNOWFLAKE_WAREHOUSE=COMPUTE_WH
COMPOSIO_API_KEY=
CREWAI_ENDPOINT=http://localhost:8000
```

---

## 16. Demo Strategy

### Option A — Live Trigger Demo (Impressive, risky)

1. Judge watches screen  
2. Teammate pushes a real commit to the GitHub repo  
3. Composio trigger fires → `trigger_listener.py` → Snowflake INSERT  
4. Dynamic Table detects anomaly → Task fires → Agents run  
5. Slack alert appears in #incident-alerts  
6. GitHub issue created in incidents repo  
7. Reasoning trace fills up live on Streamlit  

**Judge reaction:** *"Wait, that was a real commit? The whole thing fired automatically?"*

### Option B — Simulate Button (Safe, reliable — use this for demo)

1. Click "Simulate Deploy" button on Page 2  
2. Same pipeline runs — just triggered from Streamlit instead of GitHub  
3. Everything else identical  

**Recommendation:** Use Option B as primary, Option A as bonus if time permits.

### Second Demo Run — Change the Scenario

After the first demo run, tell judges:  
*"Let me show you it's not hardcoded — I'll change which service gets the anomaly."*

Change simulated spike from `payment-service` to `notification-service`.  
The pipeline should now:
- Find a **different** runbook (RB-003: API Rate Limit instead of RB-001: DB Pool)  
- Produce a **different** root cause  
- Show a **different** blast radius  

This proves the system isn't hardcoded.

### Judge Q&A Prep

**"Is your data fake?"**  
> "The data is synthetic — we can't bring a production system to a hackathon. But the pipeline is completely real. Cortex Search does real semantic retrieval. AI_SIMILARITY computes real vector distances. Agents make real decisions. The architecture is production-ready — only the data source would change."

**"Why not just use PagerDuty?"**  
> "PagerDuty requires data to leave your warehouse. IncidentDNA runs entirely inside Snowflake — no egress costs, no separate security perimeter, no additional SaaS contract. Your incident knowledge stays co-located with your data. And because it's SQL-native, any data team can extend it without learning a new platform."

**"What happens with a brand-new issue?"**  
> "Great question. When our knowledge base has no match, IncidentDNA switches to first-principles investigation — analyzes the deploy diff, classifies the metric pattern, checks timing correlation, and generates a hypothesis with AI_COMPLETE. It's honest: when confidence is low, it says so and escalates to humans. But here's the key — once that human resolves it, the incident DNA gets stored. Next time: AI_SIMILARITY recognizes it instantly. Unknown becomes known."

**"How do we know the agents are actually debating?"**  
> "Look at the Reasoning Trace on Page 3 — every Ag5 challenge has a real timestamp, real alternative tested, real score from Snowflake. And I'll show you: watch what happens when Ag5 rejects Ag2's hypothesis [demonstrate round 2 in trace]. No hardcoded answer would have a 're-investigation' event."

---

## 17. FAQ for Judges

| Question | Answer |
|---|---|
| Is this just RAG? | No. RAG is retrieval + generation. IncidentDNA adds: adversarial validation (Ag5), multi-source triangulation (3 evidence sources), confidence scoring, learning loop, and idempotent real-world actions. |
| Which LLM are you using? | Llama 3.1-70B running inside Snowflake Cortex. Data never leaves Snowflake. |
| How is this different from basic alerting? | Alerting detects. IncidentDNA detects + investigates + debates + acts + learns. |
| What's the most novel part? | Ag5 — the LLM-as-Judge agent that stress-tests every hypothesis before action. No other team has adversarial validation in their agent pipeline. |
| Can it run in production? | The architecture is production-ready. Swap synthetic data for real Datadog metrics, real runbooks, real incident history. |
| What's the MTTR improvement? | Industry average MTTR: 47 minutes. IncidentDNA target: < 15 minutes. Demo shows the breakdown. |

---

**Built by:** Prem Shah + Team at Llama Lounge × Snowflake Hackathon, 2026  
**Stack:** Snowflake Cortex · CrewAI · Composio · Streamlit · Llama 3.1-70B · Python  

*"First time is hard. Second time is instant. That's the DNA."* 🧬
