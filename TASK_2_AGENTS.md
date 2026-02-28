# Task 2 — Agent Layer (CrewAI + FastAPI)
**Owner:** Person 2 (Backend / AI Engineer)
**Your folders:** `agents/` + `tools/` + `api.py` (root) + `requirements.txt` (root)
**You touch ONLY these files — zero overlap with P1 or P3.**

---

## Snowflake Access
| Field    | Value |
|----------|-------|
| URL      | https://sfsehol-llama_lounge_hackathon_sudhag.snowflakecomputing.com |
| Username | USER |
| Password | sn0wf@ll |

---

## Prerequisites (get from P1 first)
Wait for P1 to confirm their branch is merged, then:
```bash
cp .env.example .env   # fill in your API_HOST and API_PORT
pip install -r requirements.txt
```

P1's tables you'll query:
- `RAW.RUNBOOKS` via `RAW.RUNBOOK_SEARCH` cortex search service
- `RAW.PAST_INCIDENTS` via `AI_SIMILARITY`
- `AI.ANOMALY_EVENTS` — read anomaly input
- `AI.AGENT_RUNS` — write your agent outputs here
- `AI.ACTIONS` — write before every Composio action (idempotency check)
- `ANALYTICS.INCIDENT_DNA` — write resolved incident as DNA

---

## Your Deliverables

### Step 1 — `requirements.txt`
```
crewai==0.28.0
snowflake-connector-python==3.6.0
snowflake-snowpark-python==1.13.0
fastapi==0.110.0
uvicorn==0.29.0
composio-crewai==0.4.7
composio-core==0.4.7
streamlit==1.33.0
plotly==5.20.0
python-dotenv==1.0.1
requests==2.31.0
```

---

### Step 2 — `tools/snowflake_tool.py`
Shared Snowflake connector used by all agents.

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
        schema=os.getenv("SNOWFLAKE_SCHEMA", "AI"),
        warehouse=os.getenv("SNOWFLAKE_WAREHOUSE", "COMPUTE_WH"),
        role=os.getenv("SNOWFLAKE_ROLE", "ACCOUNTADMIN"),
    )

def run_query(sql: str, params: tuple = None) -> list[dict]:
    conn = get_connection()
    cur = conn.cursor(snowflake.connector.DictCursor)
    cur.execute(sql, params)
    return cur.fetchall()

def run_dml(sql: str, params: tuple = None):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(sql, params)
    conn.commit()
```

---

### Step 3 — `tools/search_runbooks.py`
Tool for Ag2 — vector search over runbooks via Cortex Search.

```python
from crewai.tools import BaseTool
from tools.snowflake_tool import run_query

class SearchRunbooksTool(BaseTool):
    name: str = "search_runbooks"
    description: str = "Search runbooks by symptom description using Cortex vector search"

    def _run(self, query: str, limit: int = 3) -> str:
        results = run_query(f"""
            SELECT SNOWFLAKE.CORTEX.SEARCH_PREVIEW(
              'RAW.RUNBOOK_SEARCH',
              '{query.replace("'", "''")}',
              {limit}
            ) AS results
        """)
        return str(results[0]["RESULTS"]) if results else "No runbooks found."
```

---

### Step 4 — `tools/find_similar_incidents.py`
Tool for Ag2 — find past incidents similar to current anomaly.

```python
from crewai.tools import BaseTool
from tools.snowflake_tool import run_query

class FindSimilarIncidentsTool(BaseTool):
    name: str = "find_similar_incidents"
    description: str = "Find past incidents similar to the current anomaly using AI_SIMILARITY"

    def _run(self, incident_description: str, limit: int = 3) -> str:
        results = run_query(f"""
            SELECT title, root_cause, fix_applied, service, mttr_minutes,
                   SNOWFLAKE.CORTEX.SIMILARITY(
                     '{incident_description.replace("'", "''")}',
                     title || ' ' || root_cause
                   ) AS similarity_score
            FROM RAW.PAST_INCIDENTS
            ORDER BY similarity_score DESC
            LIMIT {limit}
        """)
        return str(results) if results else "No similar incidents found."
```

---

### Step 5 — `tools/query_snowflake.py`
Tool for any agent — run arbitrary SELECT queries.

```python
from crewai.tools import BaseTool
from tools.snowflake_tool import run_query

class QuerySnowflakeTool(BaseTool):
    name: str = "query_snowflake"
    description: str = "Run a SELECT query against Snowflake and return results as a string"

    def _run(self, sql: str) -> str:
        if not sql.strip().upper().startswith("SELECT"):
            return "Error: only SELECT queries are allowed"
        try:
            results = run_query(sql)
            return str(results[:20])  # cap at 20 rows
        except Exception as e:
            return f"Query error: {e}"
```

---

### Step 6 — `tools/ai_complete_tool.py`
Tool for agents — call Snowflake Cortex COMPLETE (Llama 3.1-70B).

```python
from crewai.tools import BaseTool
from tools.snowflake_tool import run_query

class AICompleteTool(BaseTool):
    name: str = "ai_complete"
    description: str = "Call Snowflake Cortex COMPLETE with Llama 3.1-70B for reasoning"

    def _run(self, prompt: str) -> str:
        safe_prompt = prompt.replace("'", "''")
        results = run_query(f"""
            SELECT SNOWFLAKE.CORTEX.COMPLETE(
              'llama3.1-70b',
              '{safe_prompt}'
            ) AS response
        """)
        return results[0]["RESPONSE"] if results else "No response."
```

---

### Step 7 — `tools/composio_tool.py`
Tool for Ag4 — import P3's Composio utilities.
> **Wait for P3 to create `utils/`** before completing this file.

```python
# Import P3's utility functions — do NOT duplicate their code
from utils.slack_formatter import format_slack_alert
from utils.github_formatter import format_github_issue
from utils.idempotency import safe_execute
from crewai.tools import BaseTool

class PostSlackAlertTool(BaseTool):
    name: str = "post_slack_alert"
    description: str = "Post a formatted alert to Slack via Composio (idempotent)"

    def _run(self, event_id: str, message: str, severity: str) -> str:
        blocks = format_slack_alert(event_id, message, severity)
        return safe_execute(
            action_type="SLACK_ALERT",
            event_id=event_id,
            payload={"blocks": blocks}
        )

class CreateGitHubIssueTool(BaseTool):
    name: str = "create_github_issue"
    description: str = "Create a GitHub issue via Composio (idempotent)"

    def _run(self, event_id: str, title: str, body: str) -> str:
        formatted_body = format_github_issue(event_id, title, body)
        return safe_execute(
            action_type="GITHUB_ISSUE",
            event_id=event_id,
            payload={"title": title, "body": formatted_body}
        )
```

---

### Step 8 — `agents/ag1_detector.py`
Classify severity and blast radius.

```python
from crewai import Agent
from tools.query_snowflake import QuerySnowflakeTool
from tools.ai_complete_tool import AICompleteTool

def make_detector():
    return Agent(
        role="Incident Detector",
        goal="Classify the severity of the anomaly and identify blast radius — which other services are affected",
        backstory=(
            "You are a senior SRE who has seen every type of production incident. "
            "You look at anomaly metrics, determine P1/P2/P3 severity, and immediately "
            "map which downstream services are at risk using the dependency graph."
        ),
        tools=[QuerySnowflakeTool(), AICompleteTool()],
        verbose=True,
    )

DETECTOR_TASK_TEMPLATE = """
Analyze this anomaly and classify it:

Event ID: {event_id}
Service: {service}
Anomaly Type: {anomaly_type}
Severity Signal: {severity}
Details: {details}

Steps:
1. Query RAW.SERVICE_DEPENDENCIES to find what services depend on {service}
2. Query AI.METRIC_DEVIATIONS for the latest metrics on {service}
3. Confirm or upgrade the severity (P1=critical, P2=high, P3=medium)
4. List affected downstream services

Return JSON: {{"severity": "P1|P2|P3", "blast_radius": ["svc1","svc2"], "classification": "brief description"}}
"""
```

---

### Step 9 — `agents/ag2_investigator.py`
Root cause investigation via 3-source evidence chain.

```python
from crewai import Agent
from tools.search_runbooks import SearchRunbooksTool
from tools.find_similar_incidents import FindSimilarIncidentsTool
from tools.query_snowflake import QuerySnowflakeTool
from tools.ai_complete_tool import AICompleteTool

def make_investigator():
    return Agent(
        role="Root Cause Investigator",
        goal=(
            "Find the root cause using 3 evidence sources: "
            "(1) Runbooks via Cortex Search, "
            "(2) Past incidents via AI_SIMILARITY, "
            "(3) Current Snowflake metrics"
        ),
        backstory=(
            "You are a forensic engineer. You never guess — you always evidence-chain. "
            "You search runbooks, compare to past incidents, and cross-check with live data. "
            "If no known issue matches, you reason from first principles."
        ),
        tools=[
            SearchRunbooksTool(),
            FindSimilarIncidentsTool(),
            QuerySnowflakeTool(),
            AICompleteTool(),
        ],
        verbose=True,
    )

INVESTIGATOR_TASK_TEMPLATE = """
Investigate the root cause of this incident:

Service: {service}
Anomaly Class: {anomaly_class}
Severity: {severity}
Blast Radius: {blast_radius}

Required steps (do ALL three):
1. search_runbooks("{service} {anomaly_class} symptoms fix")
2. find_similar_incidents("{service} {anomaly_class}")
3. query_snowflake("SELECT * FROM AI.METRIC_DEVIATIONS WHERE service='{service}' LIMIT 10")

Synthesize the 3 sources. If no runbook matches, reason from first principles.

Return JSON: {{"root_cause": "...", "confidence": 0.0-1.0, "evidence": ["source1","source2","source3"]}}
"""
```

---

### Step 10 — `agents/ag3_fix_advisor.py`
Generate ranked fix options.

```python
from crewai import Agent
from tools.search_runbooks import SearchRunbooksTool
from tools.ai_complete_tool import AICompleteTool

def make_fix_advisor():
    return Agent(
        role="Fix Advisor",
        goal="Produce 3 ranked fix options with time estimates and risk levels",
        backstory=(
            "You are a pragmatic SRE lead. You always provide options — never a single answer. "
            "Each fix option includes steps, estimated MTTR, and rollback plan."
        ),
        tools=[SearchRunbooksTool(), AICompleteTool()],
        verbose=True,
    )

FIX_ADVISOR_TASK_TEMPLATE = """
Root cause confirmed: {root_cause}
Service: {service}
Severity: {severity}

Generate 3 ranked fix options. For each:
- fix_steps: ordered list of commands/actions
- estimated_mttr_minutes: realistic time to resolve
- risk: low/medium/high
- rollback: how to undo if it makes things worse

Return JSON: {{"fixes": [{{"rank":1,"title":"...","steps":[...],"mttr":N,"risk":"...","rollback":"..."}}]}}
"""
```

---

### Step 11 — `agents/ag4_action_agent.py`
Execute the chosen fix action via Composio.

```python
from crewai import Agent
from tools.composio_tool import PostSlackAlertTool, CreateGitHubIssueTool

def make_action_agent():
    return Agent(
        role="Action Agent",
        goal="Execute the validated fix: post Slack alert and create GitHub issue",
        backstory=(
            "You are the executor. Once a fix is validated, you act immediately and precisely. "
            "You never duplicate actions — you always check idempotency first. "
            "You post clear, actionable Slack alerts and well-structured GitHub issues."
        ),
        tools=[PostSlackAlertTool(), CreateGitHubIssueTool()],
        verbose=True,
    )

ACTION_TASK_TEMPLATE = """
Validated fix ready. Execute these actions for event {event_id}:

Service: {service}
Severity: {severity}
Root cause: {root_cause}
Recommended fix: {fix}

Actions to take:
1. post_slack_alert(event_id="{event_id}", message="[severity] service root_cause fix", severity="{severity}")
2. create_github_issue(event_id="{event_id}", title="[severity] service - root_cause", body="full details")

IMPORTANT: The idempotency layer will skip duplicate actions automatically.
Return confirmation of actions taken.
"""
```

---

### Step 12 — `agents/ag5_validator.py`
Adversarial LLM-as-Judge — stress-test the hypothesis.

```python
from crewai import Agent
from tools.query_snowflake import QuerySnowflakeTool
from tools.ai_complete_tool import AICompleteTool

def make_validator():
    return Agent(
        role="Adversarial Validator",
        goal=(
            "Challenge every hypothesis. Find holes in the root cause. "
            "Only approve if it survives 4 validation checks."
        ),
        backstory=(
            "You are a skeptical senior engineer who has seen wrong diagnoses cause worse outages. "
            "You apply 4 stress tests: (1) What else could cause this? "
            "(2) Does the evidence actually support this root cause? "
            "(3) Is the fix safe / could it make things worse? "
            "(4) Is there a simpler explanation?"
        ),
        tools=[QuerySnowflakeTool(), AICompleteTool()],
        verbose=True,
    )

VALIDATOR_TASK_TEMPLATE = """
VALIDATE this proposed root cause — do NOT accept it at face value:

Root cause: {root_cause}
Evidence: {evidence}
Confidence: {confidence}
Proposed fix: {fix}

Run all 4 checks:
1. Alternative causes: What else could cause these exact metrics?
2. Evidence quality: Does each piece of evidence directly support the root cause?
3. Fix safety: Could the proposed fix make things worse? Any risk?
4. Simplicity check: Is there a simpler explanation that fits the evidence better?

Decision: APPROVE (confidence >= 0.7 and fix is safe) or DEBATE (send back with specific objections)

Return JSON: {{"decision":"APPROVE|DEBATE","objections":["..."],"adjusted_confidence":0.0-1.0}}
"""
```

---

### Step 13 — `agents/manager.py`
Orchestrate all 5 agents with debate loop.

```python
from crewai import Crew, Task, Process
from agents.ag1_detector import make_detector, DETECTOR_TASK_TEMPLATE
from agents.ag2_investigator import make_investigator, INVESTIGATOR_TASK_TEMPLATE
from agents.ag3_fix_advisor import make_fix_advisor, FIX_ADVISOR_TASK_TEMPLATE
from agents.ag4_action_agent import make_action_agent, ACTION_TASK_TEMPLATE
from agents.ag5_validator import make_validator, VALIDATOR_TASK_TEMPLATE
from tools.snowflake_tool import run_dml
import json

MAX_DEBATE_ROUNDS = 2

def run_pipeline(event: dict) -> dict:
    ag1 = make_detector()
    ag2 = make_investigator()
    ag3 = make_fix_advisor()
    ag4 = make_action_agent()
    ag5 = make_validator()

    # Phase 1: Detect
    t1 = Task(description=DETECTOR_TASK_TEMPLATE.format(**event), agent=ag1, expected_output="JSON severity + blast radius")
    crew1 = Crew(agents=[ag1], tasks=[t1], process=Process.sequential, verbose=True)
    detection = json.loads(crew1.kickoff().raw)

    # Phase 2: Investigate + Advise
    context = {**event, **detection}
    t2 = Task(description=INVESTIGATOR_TASK_TEMPLATE.format(**context), agent=ag2, expected_output="JSON root cause + evidence")
    t3 = Task(description=FIX_ADVISOR_TASK_TEMPLATE.format(**{**context, "root_cause": "{root_cause}"}), agent=ag3, expected_output="JSON ranked fixes", context=[t2])
    crew2 = Crew(agents=[ag2, ag3], tasks=[t2, t3], process=Process.sequential, verbose=True)
    investigation = crew2.kickoff()

    # Parse investigation results
    inv_result = json.loads(investigation.tasks_output[0].raw)
    fix_result = json.loads(investigation.tasks_output[1].raw)
    top_fix = fix_result["fixes"][0]

    # Phase 3: Validate with debate loop
    debate_round = 0
    validated = False
    while debate_round < MAX_DEBATE_ROUNDS and not validated:
        t5 = Task(
            description=VALIDATOR_TASK_TEMPLATE.format(
                root_cause=inv_result["root_cause"],
                evidence=inv_result["evidence"],
                confidence=inv_result["confidence"],
                fix=top_fix
            ),
            agent=ag5,
            expected_output="JSON decision"
        )
        crew5 = Crew(agents=[ag5], tasks=[t5], process=Process.sequential, verbose=True)
        validation = json.loads(crew5.kickoff().raw)

        if validation["decision"] == "APPROVE":
            validated = True
        else:
            debate_round += 1
            # Investigator re-runs with validator's objections
            inv_result["confidence"] = validation["adjusted_confidence"]

    # Phase 4: Act (only if validated or max rounds hit)
    final_context = {
        **event,
        "root_cause": inv_result["root_cause"],
        "fix": json.dumps(top_fix),
        "severity": detection["severity"],
    }
    t4 = Task(description=ACTION_TASK_TEMPLATE.format(**final_context), agent=ag4, expected_output="Action confirmation")
    crew4 = Crew(agents=[ag4], tasks=[t4], process=Process.sequential, verbose=True)
    action_result = crew4.kickoff()

    # Write DNA to Snowflake
    run_dml("""
        INSERT INTO ANALYTICS.INCIDENT_DNA (event_id, service, root_cause, fix_applied, mttr_minutes, confidence)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (event["event_id"], event["service"], inv_result["root_cause"], top_fix["title"], top_fix["mttr"], inv_result["confidence"]))

    return {
        "event_id": event["event_id"],
        "detection": detection,
        "root_cause": inv_result["root_cause"],
        "fix": top_fix,
        "validated": validated,
        "debate_rounds": debate_round,
        "action": action_result.raw,
    }
```

---

### Step 14 — `api.py` (root)
FastAPI server — **this is the contract P3's Streamlit calls**.

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from agents.manager import run_pipeline
from tools.snowflake_tool import run_query
import uvicorn

app = FastAPI(title="IncidentDNA Agent API", version="1.0.0")

class AnomalyEvent(BaseModel):
    event_id: str
    service: str
    anomaly_type: str
    severity: str
    details: dict = {}

# ── REST API Contract for P3 ────────────────────────────────────────
# P3's Streamlit dashboard calls ONLY these two endpoints:

@app.post("/run-pipeline")
async def trigger_pipeline(event: AnomalyEvent):
    """Called by Snowflake stored proc AND P3's simulate button."""
    try:
        result = run_pipeline(event.dict())
        return {"status": "success", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/incidents")
async def list_incidents(limit: int = 20):
    """Called by P3's Streamlit dashboard to show resolved incidents."""
    rows = run_query(f"""
        SELECT dna_id, event_id, service, root_cause, fix_applied,
               mttr_minutes, confidence, resolved_at
        FROM ANALYTICS.INCIDENT_DNA
        ORDER BY resolved_at DESC
        LIMIT {limit}
    """)
    return {"incidents": rows}

@app.get("/anomalies")
async def list_anomalies(limit: int = 20):
    """Called by P3's live console page."""
    rows = run_query(f"""
        SELECT event_id, service, anomaly_type, severity, detected_at, status
        FROM AI.ANOMALY_EVENTS
        ORDER BY detected_at DESC
        LIMIT {limit}
    """)
    return {"anomalies": rows}

@app.get("/health")
async def health():
    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
```

**Start server:** `python api.py`

---

## Integration Outputs (What P3 Needs From You)

When your server is running, post in team chat:

```
✅ P2 Done. Here's the API contract for P3:

Base URL: http://localhost:8000

Endpoints:
  POST /run-pipeline   — body: {event_id, service, anomaly_type, severity, details}
  GET  /incidents      — returns last N resolved incidents from ANALYTICS.INCIDENT_DNA
  GET  /anomalies      — returns last N anomaly events from AI.ANOMALY_EVENTS
  GET  /health         — returns {"status": "ok"}

Also need from P3 before completing tools/composio_tool.py:
  - utils/idempotency.py  → safe_execute() function
  - utils/slack_formatter.py → format_slack_alert()
  - utils/github_formatter.py → format_github_issue()
```

---

## Merge Instructions

```bash
git checkout -b feature/agent-layer

# Only commit your files
git add agents/ tools/ api.py requirements.txt
git commit -m "feat: crewai agent layer — 5 agents, manager, tools, fastapi"

# Integrate after P1 merges (you need their schema)
# Integrate with P3 simultaneously (you share no files, just import utils/)
git checkout main
git merge feature/agent-layer   # clean merge — no conflicts
```

> **No conflicts guaranteed**: You own `agents/`, `tools/`, `api.py`, `requirements.txt`. P1 owns `snowflake/`. P3 owns `app/`, `utils/`, `trigger_listener.py`.

---

## Checklist

- [ ] `requirements.txt` — all dependencies pinned
- [ ] `tools/snowflake_tool.py` — connection + query + dml helpers
- [ ] `tools/search_runbooks.py` — Cortex Search tool
- [ ] `tools/find_similar_incidents.py` — AI_SIMILARITY tool
- [ ] `tools/query_snowflake.py` — generic SELECT tool
- [ ] `tools/ai_complete_tool.py` — Cortex COMPLETE (Llama 3.1-70B)
- [ ] `tools/composio_tool.py` — Slack + GitHub tools (finish after P3 creates utils/)
- [ ] `agents/ag1_detector.py` — severity + blast radius
- [ ] `agents/ag2_investigator.py` — 3-source root cause
- [ ] `agents/ag3_fix_advisor.py` — ranked fix options
- [ ] `agents/ag4_action_agent.py` — Composio executor
- [ ] `agents/ag5_validator.py` — adversarial validator
- [ ] `agents/manager.py` — orchestrator + debate loop + DNA storage
- [ ] `api.py` — FastAPI server running on port 8000
- [ ] `POST /run-pipeline` tested with a sample event
- [ ] Posted API contract in team chat
- [ ] Merged `feature/agent-layer` into `main`
