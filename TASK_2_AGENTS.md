# Task 2 — Agent Layer (CrewAI + Tools)
**Owner:** Person 2 (Backend / AI Engineer)
**Your folders:** `agents/` + `tools/` + `utils/` + `requirements.txt` (root)
**You touch ONLY these files — zero overlap with P1 or P3.**

> No FastAPI server. No HTTP bridge. Everything runs locally — `trigger_listener.py` (P3) calls your `run_incident_crew()` function directly.

---

## All Credentials

| Service | Field | Value |
|---------|-------|-------|
| **Snowflake** | URL | https://sfsehol-llama_lounge_hackathon_sudhag.snowflakecomputing.com |
| **Snowflake** | Username | `USER` |
| **Snowflake** | Password | `sn0wf@ll` |
| **Composio** | API Key | `ak_Pv532zVAVQJoFTReaSgt` |
| **LLM (Groq)** | Free key | Get at https://console.groq.com → add as `GROQ_API_KEY` in `.env` |

> Copy `.env.example` → `.env` — Snowflake + Composio are pre-filled. Only `GROQ_API_KEY` needs adding.
> After getting Groq key, connect Composio integrations: `composio add github` + `composio add slack`

---

## Prerequisites (wait for P1 first)
```bash
cp .env.example .env      # P1 creates this — fill in COMPOSIO_API_KEY
pip install -r requirements.txt
```

P1's tables you query:
- `RAW.RUNBOOKS` via `INCIDENTDNA.RAW.RUNBOOK_SEARCH` cortex search
- `RAW.PAST_INCIDENTS` via `AI_SIMILARITY`
- `RAW.SERVICE_DEPENDENCIES` for blast radius
- `ANALYTICS.METRIC_DEVIATIONS` for live anomaly data

Tables you **write** to:
- `AI.DECISIONS` — every agent step goes here (P3 dashboard reads this)
- `AI.ACTIONS` — every Composio action attempt (idempotency + audit)
- `AI.INCIDENT_HISTORY` — final resolved incident record

---

## Your Deliverables

### Step 1 — `requirements.txt`
```
crewai==0.28.0
snowflake-connector-python==3.6.0
composio-crewai==0.4.7
composio-core==0.4.7
streamlit==1.33.0
plotly==5.20.0
python-dotenv==1.0.1
requests==2.31.0
```

---

### Step 2 — `utils/snowflake_conn.py`
Shared connection helper used by all agents and tools.

```python
import os
import snowflake.connector
from dotenv import load_dotenv

load_dotenv()

def get_connection():
    return snowflake.connector.connect(
        account=os.getenv("SNOWFLAKE_ACCOUNT"),
        user=os.getenv("SNOWFLAKE_USER"),
        password=os.getenv("SNOWFLAKE_PASSWORD"),
        database=os.getenv("SNOWFLAKE_DATABASE", "INCIDENTDNA"),
        warehouse=os.getenv("SNOWFLAKE_WAREHOUSE", "COMPUTE_WH"),
        role=os.getenv("SNOWFLAKE_ROLE", "ACCOUNTADMIN"),
    )

def run_query(sql: str, params: tuple = None) -> list[dict]:
    conn = get_connection()
    cur = conn.cursor(snowflake.connector.DictCursor)
    cur.execute(sql, params or ())
    return cur.fetchall()

def run_dml(sql: str, params: tuple = None):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(sql, params or ())
    conn.commit()
    conn.close()
```

---

### Step 3 — `tools/query_snowflake.py`

```python
from crewai.tools import BaseTool
from utils.snowflake_conn import run_query

class QuerySnowflakeTool(BaseTool):
    name: str = "query_snowflake"
    description: str = "Run a SELECT query against Snowflake and return results. Only SELECT allowed."

    def _run(self, sql: str) -> str:
        if not sql.strip().upper().startswith("SELECT"):
            return "Error: only SELECT queries allowed"
        try:
            return str(run_query(sql)[:20])   # cap at 20 rows
        except Exception as e:
            return f"Query error: {e}"
```

---

### Step 4 — `tools/search_runbooks.py`

```python
from crewai.tools import BaseTool
from utils.snowflake_conn import run_query

class SearchRunbooksTool(BaseTool):
    name: str = "search_runbooks"
    description: str = "Search runbooks by symptom using Cortex vector search. Returns top matching runbooks."

    def _run(self, query: str, limit: int = 3) -> str:
        safe = query.replace("'", "''")
        results = run_query(f"""
            SELECT SNOWFLAKE.CORTEX.SEARCH_PREVIEW(
              'INCIDENTDNA.RAW.RUNBOOK_SEARCH',
              '{safe}',
              {limit}
            ) AS results
        """)
        return str(results[0]["RESULTS"]) if results else "No runbooks found."
```

---

### Step 5 — `tools/find_similar_incidents.py`

```python
from crewai.tools import BaseTool
from utils.snowflake_conn import run_query

class FindSimilarIncidentsTool(BaseTool):
    name: str = "find_similar_incidents"
    description: str = "Find past incidents similar to the current anomaly using AI_SIMILARITY."

    def _run(self, incident_description: str, limit: int = 3) -> str:
        safe = incident_description.replace("'", "''")
        results = run_query(f"""
            SELECT title, root_cause, fix_applied, service, mttr_minutes,
                   SNOWFLAKE.CORTEX.SIMILARITY(
                     '{safe}',
                     title || ' ' || root_cause
                   ) AS score
            FROM RAW.PAST_INCIDENTS
            ORDER BY score DESC
            LIMIT {limit}
        """)
        return str(results) if results else "No similar incidents found."
```

---

### Step 6 — `tools/composio_actions.py`
Composio execution — Slack alert + GitHub issue.

```python
import os
import json
import hashlib
from composio_crewai import ComposioToolSet, Action
from utils.snowflake_conn import run_dml, run_query
from dotenv import load_dotenv

load_dotenv()

toolset = ComposioToolSet(api_key=os.getenv("COMPOSIO_API_KEY"))

def _idempotency_key(action_type: str, event_id: str) -> str:
    return hashlib.sha256(f"{action_type}:{event_id}".encode()).hexdigest()[:32]

def post_slack_alert(event_id: str, service: str, severity: str, root_cause: str) -> str:
    """Post Slack alert. Skips if already sent for this event."""
    key = _idempotency_key("SLACK_ALERT", event_id)
    existing = run_query("SELECT status FROM AI.ACTIONS WHERE idempotency_key = %s", (key,))
    if existing:
        return f"SKIPPED_DUPLICATE (previous: {existing[0]['STATUS']})"

    message = f"[{severity}] *{service}* incident detected.\n*Root cause:* {root_cause}\n*Event:* `{event_id}`"
    payload = {"channel": os.getenv("SLACK_CHANNEL", "#incidents"), "text": message}

    run_dml(
        "INSERT INTO AI.ACTIONS (event_id, action_type, idempotency_key, payload, status) VALUES (%s,%s,%s,PARSE_JSON(%s),'PENDING')",
        (event_id, "SLACK_ALERT", key, json.dumps(payload))
    )

    try:
        toolset.execute_action(
            action=Action.SLACKBOT_CHAT_POST_MESSAGE,
            params=payload
        )
        run_dml("UPDATE AI.ACTIONS SET status='SENT' WHERE idempotency_key=%s", (key,))
        return "SENT"
    except Exception as e:
        run_dml("UPDATE AI.ACTIONS SET status='FAILED' WHERE idempotency_key=%s", (key,))
        return f"FAILED: {e}"

def create_github_issue(event_id: str, service: str, severity: str, root_cause: str, fix: str) -> str:
    """Create GitHub issue. Skips if already created for this event."""
    key = _idempotency_key("GITHUB_ISSUE", event_id)
    existing = run_query("SELECT status FROM AI.ACTIONS WHERE idempotency_key = %s", (key,))
    if existing:
        return f"SKIPPED_DUPLICATE (previous: {existing[0]['STATUS']})"

    title = f"[{severity}] {service} — {root_cause[:60]}"
    body = f"""## IncidentDNA Automated Report

**Event ID:** `{event_id}`
**Service:** {service}
**Severity:** {severity}

### Root Cause
{root_cause}

### Recommended Fix
{fix}

### Resolution Checklist
- [ ] Root cause confirmed
- [ ] Fix applied
- [ ] Service restored
- [ ] Post-mortem scheduled

---
*Auto-generated by IncidentDNA. Do not close until resolution confirmed.*
"""
    payload = {"repo": os.getenv("GITHUB_REPO"), "title": title, "body": body}

    run_dml(
        "INSERT INTO AI.ACTIONS (event_id, action_type, idempotency_key, payload, status) VALUES (%s,%s,%s,PARSE_JSON(%s),'PENDING')",
        (event_id, "GITHUB_ISSUE", key, json.dumps(payload))
    )

    try:
        toolset.execute_action(
            action=Action.GITHUB_CREATE_ISSUE,
            params=payload
        )
        run_dml("UPDATE AI.ACTIONS SET status='SENT' WHERE idempotency_key=%s", (key,))
        return "SENT"
    except Exception as e:
        run_dml("UPDATE AI.ACTIONS SET status='FAILED' WHERE idempotency_key=%s", (key,))
        return f"FAILED: {e}"
```

---

### Step 7 — `tools/idempotency.py`
Generic safe-execute wrapper (used by manager for custom actions).

```python
import json
import hashlib
from utils.snowflake_conn import run_dml, run_query

def safe_execute(action_type: str, event_id: str, payload: dict, executor_fn=None) -> str:
    """
    Check AI.ACTIONS before executing any external action.
    Returns: 'SENT' | 'SKIPPED_DUPLICATE' | 'FAILED'
    """
    key = hashlib.sha256(f"{action_type}:{event_id}".encode()).hexdigest()[:32]
    existing = run_query("SELECT status FROM AI.ACTIONS WHERE idempotency_key = %s", (key,))
    if existing:
        return f"SKIPPED_DUPLICATE"

    run_dml(
        "INSERT INTO AI.ACTIONS (event_id, action_type, idempotency_key, payload, status) VALUES (%s,%s,%s,PARSE_JSON(%s),'PENDING')",
        (event_id, action_type, key, json.dumps(payload))
    )

    try:
        if executor_fn:
            executor_fn(payload)
        run_dml("UPDATE AI.ACTIONS SET status='SENT' WHERE idempotency_key=%s", (key,))
        return "SENT"
    except Exception as e:
        run_dml("UPDATE AI.ACTIONS SET status='FAILED' WHERE idempotency_key=%s", (key,))
        return f"FAILED: {e}"
```

---

### Step 8 — `agents/ag1_detector.py`
Classify severity + blast radius.

```python
from crewai import Agent, Task
from tools.query_snowflake import QuerySnowflakeTool

def make_detector() -> Agent:
    return Agent(
        role="Incident Detector",
        goal="Classify anomaly severity and identify which services are in the blast radius",
        backstory=(
            "You are a senior SRE. You look at anomaly metrics and service dependency graphs. "
            "You output clean JSON — always P1, P2, or P3 severity with affected services listed."
        ),
        tools=[QuerySnowflakeTool()],
        verbose=True,
        temperature=0,
    )

def detector_task(agent: Agent, event: dict) -> Task:
    return Task(
        description=f"""
Analyze this anomaly and classify it.

Event ID: {event['event_id']}
Service: {event['service']}
Anomaly: {event['anomaly_type']}
Raw Severity Signal: {event['severity']}
Details: {event.get('details', {})}

Steps:
1. query_snowflake: SELECT depends_on FROM RAW.SERVICE_DEPENDENCIES WHERE service='{event['service']}'
2. query_snowflake: SELECT metric_name, current_value, z_score, severity FROM ANALYTICS.METRIC_DEVIATIONS WHERE service='{event['service']}' LIMIT 10
3. Confirm or upgrade severity based on z_score (>3 = P1, >2 = P2, else P3)

Return ONLY valid JSON:
{{"severity": "P1|P2|P3", "blast_radius": ["svc1", "svc2"], "classification": "one-line description"}}
""",
        agent=agent,
        expected_output='JSON with severity, blast_radius, classification'
    )
```

---

### Step 9 — `agents/ag2_investigator.py`
Root cause via 3-source evidence chain.

```python
from crewai import Agent, Task
from tools.search_runbooks import SearchRunbooksTool
from tools.find_similar_incidents import FindSimilarIncidentsTool
from tools.query_snowflake import QuerySnowflakeTool

def make_investigator() -> Agent:
    return Agent(
        role="Root Cause Investigator",
        goal="Find root cause using 3 evidence sources: runbooks, past incidents, live metrics",
        backstory=(
            "You are a forensic engineer. You never guess — you evidence-chain. "
            "You search runbooks via Cortex, compare to past incidents via similarity, "
            "and cross-check with live deviation data. "
            "If nothing matches, you reason from first principles. "
            "You always output a confidence score 0.0–1.0."
        ),
        tools=[SearchRunbooksTool(), FindSimilarIncidentsTool(), QuerySnowflakeTool()],
        verbose=True,
        temperature=0,
    )

def investigator_task(agent: Agent, event: dict, detection: dict) -> Task:
    return Task(
        description=f"""
Investigate the root cause of this incident.

Service: {event['service']}
Severity: {detection['severity']}
Classification: {detection['classification']}
Blast Radius: {detection['blast_radius']}

REQUIRED — run ALL 3 steps:
1. search_runbooks("{event['service']} {event['anomaly_type']} symptoms")
2. find_similar_incidents("{event['service']} {detection['classification']}")
3. query_snowflake: SELECT metric_name, current_value, baseline_avg, z_score FROM ANALYTICS.METRIC_DEVIATIONS WHERE service='{event['service']}' LIMIT 10

Synthesize all 3 sources. If confidence < 0.6 on known causes, reason from first principles.

Return ONLY valid JSON:
{{"root_cause": "detailed description", "confidence": 0.0-1.0, "evidence_sources": ["runbook|past_incident|metrics|first_principles"], "recommended_action": "rollback|fix_config|restart|escalate"}}
""",
        agent=agent,
        expected_output='JSON with root_cause, confidence, evidence_sources, recommended_action'
    )
```

---

### Step 10 — `agents/ag5_validator.py`
Adversarial LLM-as-Judge.

```python
from crewai import Agent, Task
from tools.query_snowflake import QuerySnowflakeTool

def make_validator() -> Agent:
    return Agent(
        role="Adversarial Validator",
        goal="Challenge every hypothesis. Only approve if it survives 4 stress tests.",
        backstory=(
            "You are a skeptical senior engineer. Wrong diagnoses cause worse outages. "
            "You apply 4 stress tests: "
            "(1) What else could cause these exact metrics? "
            "(2) Does the evidence actually support this root cause? "
            "(3) Could the recommended fix make things worse? "
            "(4) Is there a simpler explanation? "
            "You are not here to agree — you are here to find holes."
        ),
        tools=[QuerySnowflakeTool()],
        verbose=True,
        temperature=0,
    )

def validator_task(agent: Agent, investigation: dict, event: dict) -> Task:
    return Task(
        description=f"""
CHALLENGE this proposed root cause — do NOT accept it at face value.

Root cause: {investigation['root_cause']}
Confidence: {investigation['confidence']}
Evidence: {investigation['evidence_sources']}
Recommended action: {investigation['recommended_action']}
Service: {event['service']}

Run ALL 4 checks:
1. Alternative causes: What else could produce these metrics for {event['service']}?
2. Evidence quality: Does each evidence source directly support the root cause, or is it circumstantial?
3. Fix safety: Could "{investigation['recommended_action']}" make things worse? Any rollback risk?
4. Simplicity: Is there a simpler explanation that fits the evidence better?

APPROVE if: confidence >= 0.7 AND fix is safe AND no strong alternatives found.
DEBATE if: any check raises a serious concern.

Return ONLY valid JSON:
{{"verdict": "APPROVED|DEBATE", "confidence_adjustment": -0.2 to +0.1, "objections": ["objection1"], "notes": "summary"}}
""",
        agent=agent,
        expected_output='JSON with verdict, confidence_adjustment, objections, notes'
    )
```

---

### Step 11 — `agents/crew.py`
Crew factory helpers.

```python
from crewai import Crew, Process

def make_crew(agents: list, tasks: list) -> Crew:
    return Crew(
        agents=agents,
        tasks=tasks,
        process=Process.sequential,
        verbose=True,
    )
```

---

### Step 12 — `agents/manager.py`
Orchestrate 3 agents with debate loop. Write every step to `AI.DECISIONS`.

```python
import json
from agents.ag1_detector import make_detector, detector_task
from agents.ag2_investigator import make_investigator, investigator_task
from agents.ag5_validator import make_validator, validator_task
from agents.crew import make_crew
from tools.composio_actions import post_slack_alert, create_github_issue
from utils.snowflake_conn import run_dml

MAX_DEBATE_ROUNDS = 2

def _log_decision(event_id: str, agent_name: str, input_data: dict, output_data: dict, reasoning: str, confidence: float):
    run_dml(
        """INSERT INTO AI.DECISIONS (event_id, agent_name, input, output, reasoning, confidence)
           VALUES (%s, %s, PARSE_JSON(%s), PARSE_JSON(%s), %s, %s)""",
        (event_id, agent_name, json.dumps(input_data), json.dumps(output_data), reasoning, confidence)
    )

def _safe_parse(raw: str) -> dict:
    try:
        # Strip markdown code fences if present
        cleaned = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        return json.loads(cleaned)
    except Exception:
        return {"error": "parse_failed", "raw": raw}

def run_incident_crew(event: dict) -> dict:
    """
    Main entry point called by P3's trigger_listener.py.
    event = {event_id, service, anomaly_type, severity, details}
    """
    print(f"\n[MANAGER] Starting pipeline for event {event['event_id']}")

    # ── Phase 1: Detect ──────────────────────────────────────────────
    ag1 = make_detector()
    t1 = detector_task(ag1, event)
    crew1 = make_crew([ag1], [t1])
    detection_raw = crew1.kickoff().raw
    detection = _safe_parse(detection_raw)
    _log_decision(event["event_id"], "ag1_detector", event, detection, detection_raw, 1.0)
    print(f"[AG1] {detection}")

    # ── Phase 2: Investigate ─────────────────────────────────────────
    ag2 = make_investigator()
    t2 = investigator_task(ag2, event, detection)
    crew2 = make_crew([ag2], [t2])
    investigation_raw = crew2.kickoff().raw
    investigation = _safe_parse(investigation_raw)
    _log_decision(event["event_id"], "ag2_investigator", {**event, **detection}, investigation, investigation_raw, investigation.get("confidence", 0.5))
    print(f"[AG2] {investigation}")

    # ── Phase 3: Validate with debate loop ───────────────────────────
    debate_round = 0
    approved = False

    while debate_round < MAX_DEBATE_ROUNDS and not approved:
        ag5 = make_validator()
        t5 = validator_task(ag5, investigation, event)
        crew5 = make_crew([ag5], [t5])
        validation_raw = crew5.kickoff().raw
        validation = _safe_parse(validation_raw)
        _log_decision(event["event_id"], "ag5_validator", investigation, validation, validation_raw, investigation.get("confidence", 0.5))
        print(f"[AG5] Round {debate_round + 1}: {validation}")

        if validation.get("verdict") == "APPROVED":
            approved = True
            # Apply confidence adjustment
            investigation["confidence"] = min(1.0, investigation.get("confidence", 0.5) + validation.get("confidence_adjustment", 0))
        else:
            debate_round += 1
            # Adjust confidence and let manager decide after max rounds
            investigation["confidence"] = max(0.0, investigation.get("confidence", 0.5) + validation.get("confidence_adjustment", -0.1))

    # ── Phase 4: Act ─────────────────────────────────────────────────
    root_cause = investigation.get("root_cause", "Unknown")
    fix = investigation.get("recommended_action", "Investigate manually")
    severity = detection.get("severity", event["severity"])

    slack_result = post_slack_alert(event["event_id"], event["service"], severity, root_cause)
    github_result = create_github_issue(event["event_id"], event["service"], severity, root_cause, fix)
    print(f"[ACTIONS] Slack: {slack_result} | GitHub: {github_result}")

    # ── Phase 5: Store DNA ───────────────────────────────────────────
    run_dml(
        """INSERT INTO AI.INCIDENT_HISTORY (event_id, service, root_cause, fix_applied, severity, confidence, mttr_minutes)
           VALUES (%s, %s, %s, %s, %s, %s, %s)""",
        (event["event_id"], event["service"], root_cause, fix, severity, investigation.get("confidence", 0.5), 0)
    )

    return {
        "event_id":     event["event_id"],
        "severity":     severity,
        "root_cause":   root_cause,
        "fix":          fix,
        "confidence":   investigation.get("confidence"),
        "approved":     approved,
        "debate_rounds": debate_round,
        "slack":        slack_result,
        "github":       github_result,
    }
```

---

## Integration Outputs (Post in team chat when done)

```
✅ P2 Done. How to call the pipeline (for P3's trigger_listener.py):

  from agents.manager import run_incident_crew

  result = run_incident_crew({
      "event_id":    "evt-001",
      "service":     "payment-service",
      "anomaly_type": "db_pool_exhaustion",
      "severity":    "P2",
      "details":     {"deploy_id": "deploy_001"}
  })

P3's dashboard reads these tables directly from Snowflake:
  AI.DECISIONS   — agent reasoning steps (agent_name, output, reasoning, confidence, created_at)
  AI.ACTIONS     — Slack + GitHub actions (action_type, status, executed_at)
  AI.INCIDENT_HISTORY — final resolved incidents

No API server needed.
```

---

## Merge Instructions

```bash
git checkout -b feature/agent-layer

git add agents/ tools/ utils/ requirements.txt
git commit -m "feat: crewai agents (detector, investigator, validator), tools, manager with debate loop"

# Can merge in parallel with P3 — no shared files
git checkout main
git merge feature/agent-layer   # zero conflicts guaranteed
```

---

## Checklist

- [ ] `requirements.txt` — all deps pinned
- [ ] `utils/snowflake_conn.py` — `get_connection()`, `run_query()`, `run_dml()`
- [ ] `tools/query_snowflake.py` — generic SELECT tool
- [ ] `tools/search_runbooks.py` — Cortex Search tool
- [ ] `tools/find_similar_incidents.py` — AI_SIMILARITY tool
- [ ] `tools/composio_actions.py` — `post_slack_alert()` + `create_github_issue()` with idempotency
- [ ] `tools/idempotency.py` — `safe_execute()` wrapper
- [ ] `agents/ag1_detector.py` — severity + blast radius
- [ ] `agents/ag2_investigator.py` — 3-source investigation
- [ ] `agents/ag5_validator.py` — adversarial validator
- [ ] `agents/crew.py` — crew factory
- [ ] `agents/manager.py` — orchestrator + debate loop + DNA storage
- [ ] `run_incident_crew({"event_id": "test-001", "service": "payment-service", "anomaly_type": "db_pool_exhaustion", "severity": "P2", "details": {}})` — runs end-to-end
- [ ] `AI.DECISIONS` populated after test run
- [ ] Posted interface contract in team chat
- [ ] Merged `feature/agent-layer` into `main`
