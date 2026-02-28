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
import urllib.request
import urllib.error
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


_incident_history_has_detected_at: bool | None = None


def _incident_history_supports_detected_at() -> bool:
    global _incident_history_has_detected_at
    if _incident_history_has_detected_at is None:
        cols = {
            r.get("name", "").lower()
            for r in _lower(_sf("DESC TABLE AI.INCIDENT_HISTORY"))
        }
        _incident_history_has_detected_at = "detected_at" in cols
    return _incident_history_has_detected_at


def _incident_history_rows(where_clause: str = "", params: tuple | None = None) -> list[dict]:
    select_sql = (
        """
        SELECT event_id, service_name, root_cause, fix_applied,
               confidence, mttr_minutes, detected_at, resolved_at
        FROM AI.INCIDENT_HISTORY
        """
        if _incident_history_supports_detected_at()
        else
        """
        SELECT event_id, service_name, root_cause, fix_applied,
               confidence, mttr_minutes, NULL AS detected_at, resolved_at
        FROM AI.INCIDENT_HISTORY
        """
    )
    return _lower(_sf(f"{select_sql} {where_clause}".strip(), params))


# ── Incidents ─────────────────────────────────────────────────────────────────

@app.get("/api/v1/incidents")
def get_incidents(service: str = None, status: str = None, severity: str = None):
    rows = _incident_history_rows("ORDER BY resolved_at DESC LIMIT 100")

    incidents = []
    for r in rows:
        conf = float(r.get("confidence") or 0.5)
        incidents.append({
            "id":           r.get("event_id", ""),
            "service":      r.get("service_name", ""),
            "severity":     _derive_severity(conf),
            "status":       "resolved",
            "detected":     _to_isostr(r.get("detected_at") or r.get("resolved_at")),
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
    rows = _incident_history_rows("WHERE event_id = %s", (incident_id,))

    if not rows:
        raise HTTPException(status_code=404, detail="Incident not found")

    r = rows[0]
    conf = float(r.get("confidence") or 0.5)

    # Actions for this incident
    action_rows = _lower(_sf("""
        SELECT action_type, status, executed_at, payload
        FROM AI.ACTIONS
        WHERE event_id = %s
    """, (incident_id,)))

    actions = [
        {
            "type":      a.get("action_type", "").lower(),
            "status":    a.get("status", "").lower(),
            "timestamp": _to_isostr(a.get("executed_at")),
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
        "detected":     _to_isostr(r.get("detected_at") or r.get("resolved_at")),
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
        WHERE resolved_at >= DATEADD('day', -1, CURRENT_TIMESTAMP)
    """))
    s = stats[0] if stats else {}

    action_stats = _lower(_sf("""
        SELECT
            COUNT(*)                        AS total,
            COUNT_IF(status = 'SENT')       AS sent_count
        FROM AI.ACTIONS
    """))
    a = action_stats[0] if action_stats else {}

    # Query live metrics for error rate and latency instead of hardcoding
    live_metrics = _lower(_sf("""
        SELECT
            metric_name,
            AVG(current_value) AS avg_value
        FROM ANALYTICS.METRIC_DEVIATIONS
        WHERE metric_name IN ('error_rate', 'latency_p99')
        GROUP BY metric_name
    """))
    metric_map = {r.get("metric_name", ""): float(r.get("avg_value") or 0) for r in live_metrics}

    # Count active (unresolved) anomalies
    active_rows = _lower(_sf("""
        SELECT COUNT(*) AS active_count
        FROM AI.ANOMALY_EVENTS
        WHERE status IN ('NEW', 'PROCESSING')
    """))
    active_count = int((active_rows[0] if active_rows else {}).get("active_count") or 0)

    return {
        "activeIncidents":      active_count,
        "deployConfidence":     round(float(s.get("avg_confidence") or 0.72) * 100),
        "errorRate":            round(metric_map.get("error_rate", 0.02), 4),
        "latencyP99":           round(metric_map.get("latency_p99", 45), 1),
        "mttrAvg":              round(float(s.get("avg_mttr") or 11.2), 1),
        "mttrIndustry":         47,
        "totalIncidents24h":    int(s.get("total_incidents") or 0),
        "actionsExecuted":      int(a.get("total") or 0),
        "deduplicatedActions":  max(0, int(a.get("total") or 0) - int(a.get("sent_count") or 0)),
    }


# ── MTTR Analytics ────────────────────────────────────────────────────────────

@app.get("/api/v1/metrics/mttr")
def get_mttr():
    rows = _lower(_sf("""
        SELECT service_name, total_incidents, avg_mttr_minutes,
               avg_detect_to_investigate_min, avg_investigate_to_alert_min,
               avg_alert_to_resolve_min, avg_confidence, best_mttr, worst_mttr
        FROM ANALYTICS.MTTR_METRICS
    """))
    return rows if rows else []


# ── Metric Deviations ────────────────────────────────────────────────────────

@app.get("/api/v1/metrics/deviations")
def get_deviations():
    rows = _lower(_sf("""
        SELECT service_name, metric_name, current_value, baseline_avg,
               z_score, severity, ai_severity, recorded_at
        FROM ANALYTICS.METRIC_DEVIATIONS
        ORDER BY recorded_at DESC
        LIMIT 50
    """))
    return rows if rows else []


# ── Blast Radius ─────────────────────────────────────────────────────────────

@app.get("/api/v1/metrics/blast-radius")
def get_blast_radius():
    rows = _lower(_sf("""
        SELECT source_service, source_severity, source_z_score,
               affected_service, recorded_at
        FROM ANALYTICS.BLAST_RADIUS
        ORDER BY recorded_at DESC
        LIMIT 50
    """))
    return rows if rows else []


# ── Reasoning Trace ──────────────────────────────────────────────────────────

@app.get("/api/v1/reasoning/{event_id}")
def get_reasoning(event_id: str):
    rows = _lower(_sf("""
        SELECT agent_name, reasoning, output, confidence, created_at
        FROM AI.DECISIONS
        WHERE event_id = %s
        ORDER BY created_at ASC
    """, (event_id,)))
    return rows if rows else []


# ── Metric Forecast ──────────────────────────────────────────────────────────

@app.get("/api/v1/metrics/forecast")
def get_forecast():
    rows = _lower(_sf("""
        SELECT service_name, forecast_time, predicted_value,
               predicted_z_score, predicted_severity, at_risk_services
        FROM ANALYTICS.BLAST_RADIUS_FORECAST
        ORDER BY forecast_time ASC
        LIMIT 30
    """))
    return rows if rows else []


# ── Slack Sentiment ──────────────────────────────────────────────────────────

@app.get("/api/v1/metrics/sentiment")
def get_sentiment():
    rows = _lower(_sf("""
        SELECT message_id, channel, author, message_text,
               sentiment_score, sentiment_label, created_at
        FROM ANALYTICS.SLACK_SENTIMENT
        ORDER BY created_at DESC
        LIMIT 20
    """))
    return rows if rows else []


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
        SELECT event_id, service_name, commit_hash, author, branch, deployed_at
        FROM RAW.DEPLOY_EVENTS
        ORDER BY deployed_at DESC
        LIMIT 20
    """))

    # Get per-service confidence from recent incidents
    confidence_rows = _lower(_sf("""
        SELECT service_name, AVG(confidence) AS avg_conf
        FROM AI.INCIDENT_HISTORY
        GROUP BY service_name
    """))
    svc_conf = {r.get("service_name", ""): float(r.get("avg_conf") or 0.72) for r in confidence_rows}

    # Get active deviations for risk assessment
    deviation_svcs = {r.get("service_name", "") for r in _lower(_sf(
        "SELECT DISTINCT service_name FROM ANALYTICS.METRIC_DEVIATIONS"
    ))}

    releases = []
    for r in rows:
        svc = r.get("service_name", "")
        conf = round(svc_conf.get(svc, 0.72) * 100)
        has_deviations = svc in deviation_svcs
        risk = "high" if has_deviations and conf < 60 else "medium" if has_deviations else "low"
        risk_factors = []
        if has_deviations:
            risk_factors.append("Active metric deviations detected")
        if conf < 70:
            risk_factors.append(f"Below-average confidence ({conf}%)")

        releases.append({
            "id":          r.get("event_id", ""),
            "service":     svc,
            "version":     (r.get("commit_hash") or "")[:8] or "unknown",
            "confidence":  conf,
            "risk":        risk,
            "author":      r.get("author", "engineer"),
            "timestamp":   _to_isostr(r.get("deployed_at")),
            "status":      "deployed",
            "branch":      r.get("branch", "main"),
            "riskFactors": risk_factors,
            "guardrails":  [],
            "evidence":    [],
        })

    return releases


@app.get("/api/v1/releases/{release_id}/confidence")
def get_release_confidence(release_id: str):
    rows = _lower(_sf("""
        SELECT d.service_name, ih.confidence
        FROM RAW.DEPLOY_EVENTS d
        LEFT JOIN AI.INCIDENT_HISTORY ih ON d.service_name = ih.service_name
        WHERE d.event_id = %s
        ORDER BY ih.resolved_at DESC
        LIMIT 1
    """, (release_id,)))

    if rows and rows[0].get("confidence"):
        conf = round(float(rows[0]["confidence"]) * 100)
        risk = "high" if conf < 60 else "medium" if conf < 80 else "low"
        risk_factors = []
        if conf < 70:
            risk_factors.append(f"Historical confidence: {conf}%")
        return {"confidence": conf, "risk": risk, "riskFactors": risk_factors}

    return {"confidence": 72, "risk": "medium", "riskFactors": []}


# ── Postmortems ───────────────────────────────────────────────────────────────

@app.get("/api/v1/postmortems")
def get_postmortems():
    rows = _incident_history_rows("ORDER BY resolved_at DESC LIMIT 20")

    return [_build_postmortem(r) for r in rows]


@app.get("/api/v1/postmortems/{incident_id}")
def get_postmortem(incident_id: str):
    rows = _incident_history_rows("WHERE event_id = %s", (incident_id,))

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
        "detectedAt": _to_isostr(r.get("detected_at") or r.get("resolved_at")),
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
        SELECT idempotency_key, event_id, action_type, status, executed_at, payload
        FROM AI.ACTIONS
        ORDER BY executed_at DESC
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
            "timestamp":      _to_isostr(r.get("executed_at")),
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


# ── Repository Info (live from GitHub API) ────────────────────────────────────

_repo_cache: dict = {}
_repo_cache_ts: float = 0.0

def _github_api(path: str) -> Any:
    """Fetch from GitHub public API with caching."""
    url = f"https://api.github.com{path}"
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github.v3+json", "User-Agent": "IncidentDNA"})
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        print(f"[API] GitHub API error for {path}: {e}")
        return None

@app.get("/api/v1/repo")
def get_repo_info():
    """Dynamically fetch repo details, recent commits, languages, and contributors from GitHub."""
    import time
    global _repo_cache, _repo_cache_ts

    # Cache for 60s to avoid rate limits
    if _repo_cache and (time.time() - _repo_cache_ts) < 60:
        return _repo_cache

    repo_slug = os.getenv("GITHUB_REPO", "theshubh007/FortressAI_AI_Agent_Security_Platform")

    # Parallel-ish fetches (sequential but fast)
    repo_data = _github_api(f"/repos/{repo_slug}") or {}
    commits = _github_api(f"/repos/{repo_slug}/commits?per_page=10") or []
    languages = _github_api(f"/repos/{repo_slug}/languages") or {}
    contributors = _github_api(f"/repos/{repo_slug}/contributors?per_page=10") or []
    contents = _github_api(f"/repos/{repo_slug}/contents") or []

    # Build file tree (top-level)
    file_tree = []
    for item in (contents if isinstance(contents, list) else []):
        file_tree.append({
            "name": item.get("name", ""),
            "type": item.get("type", "file"),
            "size": item.get("size", 0),
            "path": item.get("path", ""),
        })

    # Build recent commits
    recent_commits = []
    for c in commits[:10]:
        cm = c.get("commit", {})
        recent_commits.append({
            "sha": c.get("sha", "")[:7],
            "message": cm.get("message", "").split("\n")[0][:120],
            "author": cm.get("author", {}).get("name", "Unknown"),
            "date": cm.get("author", {}).get("date", ""),
            "avatar": (c.get("author") or {}).get("avatar_url", ""),
        })

    # Build contributors
    contribs = []
    for ct in contributors[:10]:
        contribs.append({
            "login": ct.get("login", ""),
            "avatar": ct.get("avatar_url", ""),
            "contributions": ct.get("contributions", 0),
            "url": ct.get("html_url", ""),
        })

    # Total language bytes for percentage calculation
    total_lang = sum(languages.values()) if languages else 1

    result = {
        "name": repo_data.get("name", repo_slug.split("/")[-1]),
        "fullName": repo_data.get("full_name", repo_slug),
        "description": repo_data.get("description", ""),
        "url": repo_data.get("html_url", f"https://github.com/{repo_slug}"),
        "defaultBranch": repo_data.get("default_branch", "main"),
        "stars": repo_data.get("stargazers_count", 0),
        "forks": repo_data.get("forks_count", 0),
        "openIssues": repo_data.get("open_issues_count", 0),
        "watchers": repo_data.get("watchers_count", 0),
        "size": repo_data.get("size", 0),
        "createdAt": repo_data.get("created_at", ""),
        "updatedAt": repo_data.get("updated_at", ""),
        "pushedAt": repo_data.get("pushed_at", ""),
        "visibility": repo_data.get("visibility", "public"),
        "languages": {k: round(v / total_lang * 100, 1) for k, v in languages.items()},
        "recentCommits": recent_commits,
        "contributors": contribs,
        "fileTree": sorted(file_tree, key=lambda x: (0 if x["type"] == "dir" else 1, x["name"])),
        "topics": repo_data.get("topics", []),
    }

    _repo_cache = result
    _repo_cache_ts = time.time()
    return result


@app.get("/api/v1/repo/features")
def get_repo_features():
    """Return IncidentDNA platform features derived from live system state."""
    # Pull live counts from Snowflake
    incident_count = 0
    action_count = 0
    decision_count = 0
    try:
        rows = _sf("SELECT COUNT(*) AS cnt FROM AI.INCIDENT_HISTORY")
        incident_count = int(rows[0].get("CNT", 0)) if rows else 0
        rows2 = _sf("SELECT COUNT(*) AS cnt FROM AI.ACTIONS")
        action_count = int(rows2[0].get("CNT", 0)) if rows2 else 0
        rows3 = _sf("SELECT COUNT(*) AS cnt FROM AI.DECISIONS")
        decision_count = int(rows3[0].get("CNT", 0)) if rows3 else 0
    except Exception:
        pass

    auto_fix = os.getenv("AUTO_FIX_ENABLED", "false") == "true"
    demo_mode = os.getenv("DEMO_MODE", "false") == "true"
    threshold = float(os.getenv("AUTO_FIX_CONFIDENCE_THRESHOLD", "0.90"))
    whitelist = [s.strip() for s in os.getenv("AUTO_FIX_WHITELIST", "").split(",") if s.strip()]

    return {
        "platform": "IncidentDNA",
        "tagline": "Autonomous Incident Detection, Investigation & Resolution",
        "features": [
            {
                "id": "multi-agent",
                "title": "Multi-Agent AI Pipeline",
                "description": "4 specialized AI agents (Detector, Investigator, Fix Advisor, Validator) orchestrated in a debate loop for high-confidence decisions.",
                "status": "active",
                "stats": f"{decision_count} decisions made",
            },
            {
                "id": "snowflake-cortex",
                "title": "Snowflake Cortex LLM",
                "description": "All AI inference runs natively inside Snowflake using Cortex — zero external API keys needed for LLM calls.",
                "status": "active",
                "stats": "claude-sonnet-4-5 via Cortex",
            },
            {
                "id": "threshold-engine",
                "title": "Autonomous Resolution Threshold Engine",
                "description": f"7-rule decision engine auto-resolves incidents when confidence >= {threshold:.0%}, risk is LOW, and fix is proven.",
                "status": "active" if auto_fix else "disabled",
                "stats": f"Threshold: {threshold:.0%} | Whitelist: {', '.join(whitelist) if whitelist else 'all'}",
            },
            {
                "id": "composio-actions",
                "title": "Slack & GitHub Integration",
                "description": "Automated Slack alerts (auto-resolved / escalation bands) and GitHub issue creation via Composio SDK.",
                "status": "active",
                "stats": f"{action_count} actions executed",
            },
            {
                "id": "incident-dna",
                "title": "Incident DNA Storage",
                "description": "Every incident is stored with full context — root cause, fix, MTTR, confidence — enabling pattern matching for future incidents.",
                "status": "active",
                "stats": f"{incident_count} incidents in DNA",
            },
            {
                "id": "demo-mode",
                "title": "Demo Mode",
                "description": "Injects synthetic anomalous metrics and simulates fix execution for live demonstrations.",
                "status": "active" if demo_mode else "standby",
                "stats": "DEMO_MODE=" + ("true" if demo_mode else "false"),
            },
            {
                "id": "vector-search",
                "title": "Cortex Vector Search",
                "description": "Semantic search across runbooks and past incidents using Snowflake's built-in embedding + cosine similarity.",
                "status": "active",
                "stats": "e5-base-v2 embeddings",
            },
            {
                "id": "ci-trigger",
                "title": "CI Pipeline Trigger",
                "description": "GitHub push events automatically trigger the full incident detection pipeline — fully autonomous, zero human intervention.",
                "status": "active",
                "stats": "GitHub → Snowflake → Agents → Slack/GitHub",
            },
        ],
        "architecture": {
            "agents": ["Ag1 Detector", "Ag2 Investigator", "Ag3 Fix Advisor", "Ag5 Validator"],
            "dataStore": "Snowflake (INCIDENTDNA)",
            "llm": "Snowflake Cortex (claude-sonnet-4-5)",
            "integrations": ["Composio SDK", "Slack", "GitHub"],
            "pipeline": "GitHub Push → Deploy Event → Metric Injection → Anomaly Detection → Agent Pipeline → Threshold Engine → Auto-Resolve / Escalate",
        },
    }


# ── Health check ──────────────────────────────────────────────────────────────

@app.get("/api/v1/health")
def health():
    return {"status": "ok", "service": "IncidentDNA API"}
