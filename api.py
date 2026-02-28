"""
IncidentDNA — FastAPI Backend

Connects the React dashboard to live Snowflake data.
Every endpoint tries Snowflake first; falls back gracefully if a table is missing.

Run:
    uvicorn api:app --reload --host 0.0.0.0 --port 8000
"""

import os
import json
import uuid
import asyncio
from datetime import datetime, timezone
from typing import Any
from contextlib import asynccontextmanager
from concurrent.futures import ThreadPoolExecutor

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

from utils.snowflake_conn import run_query, run_dml

load_dotenv()


# ── WebSocket manager ─────────────────────────────────────────────────────────

class ConnectionManager:
    def __init__(self):
        self.active: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.append(ws)

    def disconnect(self, ws: WebSocket):
        if ws in self.active:
            self.active.remove(ws)

    async def broadcast(self, data: dict):
        for ws in list(self.active):
            try:
                await ws.send_json(data)
            except Exception:
                self.disconnect(ws)


ws_manager = ConnectionManager()
executor = ThreadPoolExecutor(max_workers=2)


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    executor.shutdown(wait=False)


# ── App setup ─────────────────────────────────────────────────────────────────

app = FastAPI(title="IncidentDNA API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://localhost:4173", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Snowflake helper ──────────────────────────────────────────────────────────

def _sf(sql: str, params: tuple = None) -> list[dict]:
    """Run a Snowflake query; return [] on any error."""
    try:
        return run_query(sql, params)
    except Exception as e:
        print(f"[API] Snowflake error: {e}")
        return []


def _lower(rows: list[dict]) -> list[dict]:
    """Snowflake returns UPPER_CASE keys — normalise to lowercase."""
    return [{k.lower(): v for k, v in row.items()} for row in rows]


def _to_isostr(val: Any) -> str:
    if val is None:
        return ""
    if hasattr(val, "isoformat"):
        return val.isoformat()
    return str(val)


def _derive_severity(confidence: float) -> str:
    if confidence >= 0.85:
        return "critical"
    if confidence >= 0.65:
        return "warning"
    return "info"


# ── Incidents ─────────────────────────────────────────────────────────────────

@app.get("/api/v1/incidents")
def get_incidents(service: str = None, status: str = None, severity: str = None):
    rows = _lower(_sf("""
        SELECT event_id, service_name, root_cause, fix_applied,
               confidence, mttr_minutes, created_at
        FROM AI.INCIDENT_HISTORY
        ORDER BY created_at DESC
        LIMIT 100
    """))

    incidents = []
    for r in rows:
        conf = float(r.get("confidence") or 0.5)
        incidents.append({
            "id":           r.get("event_id", ""),
            "service":      r.get("service_name", ""),
            "severity":     _derive_severity(conf),
            "status":       "resolved",
            "detected":     _to_isostr(r.get("created_at")),
            "confidence":   conf,
            "rootCause":    r.get("root_cause", ""),
            "fixApplied":   r.get("fix_applied", ""),
            "mttrMinutes":  int(r.get("mttr_minutes") or 0),
            "blastRadius":  [],
            "actionsFired": 0,
            "timeline":     [],
            "actions":      [],
        })

    if service:
        incidents = [i for i in incidents if i["service"] == service]
    if severity:
        incidents = [i for i in incidents if i["severity"] == severity]

    return incidents


@app.get("/api/v1/incidents/{incident_id}")
def get_incident(incident_id: str):
    rows = _lower(_sf("""
        SELECT event_id, service_name, root_cause, fix_applied,
               confidence, mttr_minutes, created_at
        FROM AI.INCIDENT_HISTORY
        WHERE event_id = %s
    """, (incident_id,)))

    if not rows:
        raise HTTPException(status_code=404, detail="Incident not found")

    r = rows[0]
    conf = float(r.get("confidence") or 0.5)

    # Actions for this incident
    action_rows = _lower(_sf("""
        SELECT action_type, status, created_at, payload
        FROM AI.ACTIONS
        WHERE event_id = %s
    """, (incident_id,)))

    actions = [
        {
            "type":      a.get("action_type", "").lower(),
            "status":    a.get("status", "").lower(),
            "timestamp": _to_isostr(a.get("created_at")),
        }
        for a in action_rows
    ]

    # Pipeline steps (decisions) for timeline
    decision_rows = _lower(_sf("""
        SELECT agent_name, reasoning, confidence, created_at
        FROM AI.DECISIONS
        WHERE event_id = %s
        ORDER BY created_at ASC
    """, (incident_id,)))

    timeline = [
        {
            "time":   _to_isostr(d.get("created_at")),
            "agent":  d.get("agent_name", ""),
            "action": (d.get("reasoning") or "")[:120],
            "status": "complete",
        }
        for d in decision_rows
    ]

    return {
        "id":           r.get("event_id", ""),
        "service":      r.get("service_name", ""),
        "severity":     _derive_severity(conf),
        "status":       "resolved",
        "detected":     _to_isostr(r.get("created_at")),
        "confidence":   conf,
        "rootCause":    r.get("root_cause", ""),
        "fixApplied":   r.get("fix_applied", ""),
        "mttrMinutes":  int(r.get("mttr_minutes") or 0),
        "blastRadius":  [],
        "actionsFired": len(actions),
        "actions":      actions,
        "timeline":     timeline,
    }


@app.get("/api/v1/incidents/{incident_id}/pipeline")
def get_pipeline(incident_id: str):
    """Return stepper states for the pipeline visualiser."""
    rows = _lower(_sf("""
        SELECT agent_name, output, reasoning, confidence, created_at
        FROM AI.DECISIONS
        WHERE event_id = %s
        ORDER BY created_at ASC
    """, (incident_id,)))

    agent_step_map = {
        "ag1_detector":    ("detect",      "Detect"),
        "ag2_investigator":("investigate", "Investigate"),
        "ag5_validator":   ("validate",    "Validate"),
        "manager":         ("action",      "Action"),
    }

    steps = []
    seen: set[str] = set()

    for r in rows:
        agent = r.get("agent_name", "")
        step_id, label = agent_step_map.get(agent, (agent, agent.replace("_", " ").title()))

        # De-duplicate: show first occurrence per step
        if step_id in seen:
            continue
        seen.add(step_id)

        steps.append({
            "id":        step_id,
            "label":     label,
            "status":    "complete",
            "timestamp": _to_isostr(r.get("created_at")),
            "detail":    (r.get("reasoning") or "")[:140],
            "evidence":  f"AI.DECISIONS — confidence={r.get('confidence', 0)}",
        })

    return steps


# ── Metrics / Overview ────────────────────────────────────────────────────────

@app.get("/api/v1/metrics/overview")
def get_metrics():
    stats = _lower(_sf("""
        SELECT
            COUNT(*)            AS total_incidents,
            AVG(confidence)     AS avg_confidence,
            AVG(mttr_minutes)   AS avg_mttr
        FROM AI.INCIDENT_HISTORY
        WHERE created_at >= DATEADD('day', -1, CURRENT_TIMESTAMP)
    """))
    s = stats[0] if stats else {}

    action_stats = _lower(_sf("""
        SELECT
            COUNT(*)                        AS total,
            COUNT_IF(status = 'SENT')       AS sent_count
        FROM AI.ACTIONS
    """))
    a = action_stats[0] if action_stats else {}

    return {
        "activeIncidents":      0,
        "deployConfidence":     round(float(s.get("avg_confidence") or 0.72) * 100),
        "errorRate":            0.04,
        "latencyP99":           89,
        "mttrAvg":              round(float(s.get("avg_mttr") or 11.2), 1),
        "mttrIndustry":         47,
        "totalIncidents24h":    int(s.get("total_incidents") or 0),
        "actionsExecuted":      int(a.get("total") or 0),
        "deduplicatedActions":  max(0, int(a.get("total") or 0) - int(a.get("sent_count") or 0)),
    }


# ── Services ──────────────────────────────────────────────────────────────────

@app.get("/api/v1/services")
def get_services():
    rows = _lower(_sf("""
        SELECT service_name, depends_on
        FROM RAW.SERVICE_DEPENDENCIES
    """))

    services: dict[str, dict] = {}
    for r in rows:
        svc = r.get("service_name", "")
        dep = r.get("depends_on", "")
        if svc and svc not in services:
            services[svc] = {
                "id": svc, "name": svc, "status": "healthy",
                "uptime": 99.9, "latency": 45, "errorRate": 0.02,
                "dependencies": [],
            }
        if svc and dep:
            services[svc]["dependencies"].append(dep)

    return list(services.values()) if services else [
        {"id": s, "name": s, "status": "healthy", "uptime": 99.9,
         "latency": 45, "errorRate": 0.02, "dependencies": []}
        for s in ["payment-service", "api-gateway", "user-service", "order-service"]
    ]


@app.get("/api/v1/services/{service_id}/dependencies")
def get_service_dependencies(service_id: str):
    rows = _lower(_sf("""
        SELECT service_name, depends_on
        FROM RAW.SERVICE_DEPENDENCIES
    """))

    all_services: set[str] = set()
    edges = []
    for r in rows:
        svc = r.get("service_name", "")
        dep = r.get("depends_on", "")
        if svc:
            all_services.add(svc)
        if dep:
            all_services.add(dep)
        if svc and dep:
            edges.append({"from": svc, "to": dep})

    nodes = [{"id": s, "status": "healthy"} for s in sorted(all_services)]
    return {"nodes": nodes, "edges": edges}


# ── Releases ──────────────────────────────────────────────────────────────────

@app.get("/api/v1/releases")
def get_releases():
    rows = _lower(_sf("""
        SELECT event_id, service_name, deploy_sha, deployed_at, severity
        FROM RAW.DEPLOY_EVENTS
        ORDER BY deployed_at DESC
        LIMIT 20
    """))

    return [
        {
            "id":          r.get("event_id", ""),
            "service":     r.get("service_name", ""),
            "version":     (r.get("deploy_sha") or "")[:8] or "unknown",
            "confidence":  72,
            "risk":        "medium",
            "author":      "engineer",
            "timestamp":   _to_isostr(r.get("deployed_at")),
            "status":      "deployed",
            "riskFactors": [],
            "guardrails":  [],
            "evidence":    [],
        }
        for r in rows
    ]


@app.get("/api/v1/releases/{release_id}/confidence")
def get_release_confidence(release_id: str):
    return {"confidence": 72, "risk": "medium", "riskFactors": []}


# ── Postmortems ───────────────────────────────────────────────────────────────

@app.get("/api/v1/postmortems")
def get_postmortems():
    rows = _lower(_sf("""
        SELECT event_id, service_name, root_cause, fix_applied, confidence, created_at
        FROM AI.INCIDENT_HISTORY
        ORDER BY created_at DESC
        LIMIT 20
    """))

    return [_build_postmortem(r) for r in rows]


@app.get("/api/v1/postmortems/{incident_id}")
def get_postmortem(incident_id: str):
    rows = _lower(_sf("""
        SELECT event_id, service_name, root_cause, fix_applied, confidence, created_at
        FROM AI.INCIDENT_HISTORY
        WHERE event_id = %s
    """, (incident_id,)))

    if not rows:
        raise HTTPException(status_code=404, detail="Not found")

    return _build_postmortem(rows[0])


def _build_postmortem(r: dict) -> dict:
    conf = float(r.get("confidence") or 0.5)
    return {
        "incidentId": r.get("event_id", ""),
        "service":    r.get("service_name", ""),
        "severity":   _derive_severity(conf),
        "status":     "draft_ready",
        "detectedAt": _to_isostr(r.get("created_at")),
        "rootCause":  r.get("root_cause", ""),
        "confidence": conf,
        "postmortem": {
            "summary":        r.get("root_cause", "Auto-generated by IncidentDNA."),
            "customerImpact": "Impact assessment pending.",
            "rootCause":      r.get("root_cause", ""),
            "actionItems": [
                {"text": r.get("fix_applied", "Apply recommended fix"), "done": False}
            ],
        },
    }


# ── Audit Log ─────────────────────────────────────────────────────────────────

@app.get("/api/v1/audit")
def get_audit(action_type: str = None, status: str = None):
    rows = _lower(_sf("""
        SELECT idempotency_key, event_id, action_type, status, created_at, payload
        FROM AI.ACTIONS
        ORDER BY created_at DESC
        LIMIT 100
    """))

    result = []
    for i, r in enumerate(rows):
        payload = r.get("payload") or {}
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except Exception:
                payload = {}

        result.append({
            "actionId":       f"ACT-{str(i + 1).zfill(3)}",
            "toolkit":        r.get("action_type", "").lower(),
            "actionType":     r.get("action_type", ""),
            "status":         (r.get("status") or "").lower(),
            "retryCount":     0,
            "idempotencyKey": r.get("idempotency_key", ""),
            "timestamp":      _to_isostr(r.get("created_at")),
            "request":        payload,
            "response":       {},
        })

    if action_type:
        result = [r for r in result if action_type.upper() in r["actionType"].upper()]
    if status:
        result = [r for r in result if r["status"] == status.lower()]

    return result


# ── Runbooks ──────────────────────────────────────────────────────────────────

@app.get("/api/v1/runbooks")
def get_runbooks():
    rows = _lower(_sf("""
        SELECT title, service_name, symptom, root_cause, fix_steps
        FROM RAW.RUNBOOKS
        ORDER BY title
        LIMIT 20
    """))

    return [
        {
            "id":       f"RB-{str(i + 1).zfill(3)}",
            "title":    r.get("title", ""),
            "service":  r.get("service_name", "all"),
            "content":  (
                f"Symptom: {r.get('symptom', '')}\n\n"
                f"Root Cause: {r.get('root_cause', '')}\n\n"
                f"Fix: {r.get('fix_steps', '')}"
            ),
            "lastUsed":   str(datetime.now(timezone.utc).date()),
            "matchCount": 1,
        }
        for i, r in enumerate(rows)
    ]


# ── Settings ──────────────────────────────────────────────────────────────────

_settings_store: dict = {
    "connections": [
        {
            "id":     "snowflake",
            "name":   "Snowflake",
            "status": "connected",
            "detail": f"{os.getenv('SNOWFLAKE_DATABASE', 'INCIDENTDNA')} · {os.getenv('SNOWFLAKE_WAREHOUSE', 'COMPUTE_WH')}",
            "icon":   "❄️",
        },
        {
            "id":     "composio-github",
            "name":   "GitHub (Composio)",
            "status": "connected",
            "detail": f"{os.getenv('GITHUB_REPO', 'org/incidents')} · connected",
            "icon":   "🐙",
        },
        {
            "id":     "composio-slack",
            "name":   "Slack (Composio)",
            "status": "connected",
            "detail": f"{os.getenv('SLACK_CHANNEL', '#incidents')} · active",
            "icon":   "💬",
        },
        {
            "id":     "crewai",
            "name":   "CrewAI Engine",
            "status": "connected",
            "detail": "3 agents — Detector, Investigator, Validator",
            "icon":   "🤖",
        },
    ],
    "policies": [
        {"id": "auto-act-threshold", "label": "Auto-Act Confidence Threshold",  "value": "85%",     "description": "Minimum confidence to auto-execute actions without human review"},
        {"id": "debate-rounds",      "label": "Max Debate Rounds",               "value": "2",       "description": "Maximum Ag2↔Ag5 validation rounds before Manager override"},
        {"id": "agent-timeout",      "label": "Agent Timeout",                   "value": "30s",     "description": "Per-agent execution timeout before fallback"},
        {"id": "idempotency",        "label": "Idempotency Check",               "value": "Enabled", "description": "Dedup check on AI.ACTIONS before every external call"},
        {"id": "blast-radius",       "label": "Blast Radius Alert Threshold",    "value": "≥2 svcs", "description": "Auto-escalate when predicted blast radius exceeds threshold"},
    ],
}


@app.get("/api/v1/settings")
def get_settings():
    return _settings_store


@app.put("/api/v1/settings")
def update_settings(body: dict):
    _settings_store.update(body)
    return {"success": True}


# ── Simulation ────────────────────────────────────────────────────────────────

SCENARIOS = [
    {
        "id":          "payment-error-spike",
        "label":       "Payment Error Spike",
        "description": "Simulates a post-deploy error rate spike on payment-service (error_rate: 0.02 → 0.22)",
        "service":     "payment-service",
        "anomalyType": "post_deploy_error_rate",
        "severity":    "P1",
    },
    {
        "id":          "latency-regression",
        "label":       "Latency Regression",
        "description": "Simulates a P99 latency regression on api-gateway (12ms → 340ms)",
        "service":     "api-gateway",
        "anomalyType": "latency_regression",
        "severity":    "P2",
    },
    {
        "id":          "db-pool-exhaustion",
        "label":       "DB Pool Exhaustion",
        "description": "Simulates DB connection pool saturation on order-service",
        "service":     "order-service",
        "anomalyType": "db_pool_exhaustion",
        "severity":    "P1",
    },
]


@app.get("/api/v1/simulation/scenarios")
def get_scenarios():
    return SCENARIOS


class SimRequest(BaseModel):
    scenarioId: str


@app.post("/api/v1/simulation/run")
async def run_simulation(req: SimRequest, background_tasks: BackgroundTasks):
    scenario = next((s for s in SCENARIOS if s["id"] == req.scenarioId), None)
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")

    event_id = f"sim-{uuid.uuid4().hex[:8]}"
    event = {
        "event_id":    event_id,
        "service":     scenario["service"],
        "anomaly_type": scenario["anomalyType"],
        "severity":    scenario["severity"],
        "details":     {"source": "simulation", "scenario": req.scenarioId},
    }

    background_tasks.add_task(_run_pipeline_bg, event)

    return {
        "id":       event_id,
        "scenario": req.scenarioId,
        "status":   "running",
        "message":  f"Pipeline started for {event_id}. Check /api/v1/incidents for results.",
    }


async def _run_pipeline_bg(event: dict):
    loop = asyncio.get_event_loop()
    try:
        await ws_manager.broadcast({"type": "pipeline_started", "event_id": event["event_id"]})
        from agents.manager import run_incident_crew
        result = await loop.run_in_executor(executor, run_incident_crew, event)
        await ws_manager.broadcast({
            "type":     "pipeline_complete",
            "event_id": event["event_id"],
            "result":   result,
        })
    except Exception as e:
        await ws_manager.broadcast({
            "type":     "pipeline_error",
            "event_id": event["event_id"],
            "error":    str(e),
        })


# ── Composio Tool Endpoints ───────────────────────────────────────────────────

class SlackRequest(BaseModel):
    channel: str
    message: str
    connectionId: str = None


class GithubRequest(BaseModel):
    repo: str
    title: str
    body: str
    connectionId: str = None


@app.post("/api/v1/tools/slack/send")
def tool_slack(req: SlackRequest):
    from tools.composio_actions import post_slack_alert
    event_id = f"manual-{uuid.uuid4().hex[:8]}"
    result = post_slack_alert(event_id, "manual", "P3", req.message)
    return {"ok": result == "SENT", "result": result}


@app.post("/api/v1/tools/github/issue")
def tool_github(req: GithubRequest):
    from tools.composio_actions import create_github_issue
    event_id = f"manual-{uuid.uuid4().hex[:8]}"
    result = create_github_issue(event_id, req.repo, "P3", req.title, req.body)
    return {"ok": result == "SENT", "result": result}


# ── Snowflake Proxy ───────────────────────────────────────────────────────────

class QueryRequest(BaseModel):
    sql: str
    warehouse: str = None
    database: str = None


@app.post("/api/v1/snowflake/query")
def snowflake_query(req: QueryRequest):
    sql = req.sql.strip()
    if not sql.upper().startswith("SELECT"):
        raise HTTPException(status_code=400, detail="Only SELECT queries are allowed")
    rows = _lower(_sf(sql))
    return {"rows": rows, "columns": list(rows[0].keys()) if rows else []}


# ── WebSocket (real-time events) ──────────────────────────────────────────────

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws_manager.connect(ws)
    try:
        while True:
            data = await ws.receive_text()
            if data == "ping":
                await ws.send_text("pong")
    except WebSocketDisconnect:
        ws_manager.disconnect(ws)


# ── Health check ──────────────────────────────────────────────────────────────

@app.get("/api/v1/health")
def health():
    return {"status": "ok", "service": "IncidentDNA API"}
