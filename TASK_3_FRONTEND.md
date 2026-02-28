# Task 3 — Frontend + Trigger Layer (Streamlit + Composio Listener)
**Owner:** Person 3 (Frontend / Integration Engineer)
**Your folders:** `ingestion/` + `dashboard/`
**You touch ONLY these files — zero overlap with P1 or P2.**

> No FastAPI calls. Your dashboard reads Snowflake directly. Your trigger listener calls P2's `run_incident_crew()` function directly — no HTTP bridge.

---

## Snowflake Access
| Field    | Value |
|----------|-------|
| URL      | https://sfsehol-llama_lounge_hackathon_sudhag.snowflakecomputing.com |
| Username | USER |
| Password | sn0wf@ll |

---

## Prerequisites
```bash
cp .env.example .env    # fill in COMPOSIO_API_KEY, GITHUB_REPO, SLACK_CHANNEL
pip install -r requirements.txt   # P2 owns this — install after they create it
```

**Build order:**
1. Start with `ingestion/trigger_listener.py` — it's the pipeline entry point
2. Then build `dashboard/` — reads directly from Snowflake tables

**Depends on:**
- P1: `ANALYTICS.METRIC_DEVIATIONS` (trigger reads this), `RAW.DEPLOY_EVENTS` (trigger writes here)
- P2: `from agents.manager import run_incident_crew` (trigger calls this)
- P2: `AI.DECISIONS`, `AI.ACTIONS`, `AI.INCIDENT_HISTORY` tables (dashboard reads these)

---

## Your Deliverables

### Step 1 — `ingestion/trigger_listener.py`
WebSocket listener for Composio triggers. Inserts deploy event → injects spike → checks for anomaly → calls agent pipeline.

```python
import os
import uuid
import json
import time
import snowflake.connector
from composio import Composio, Trigger
from dotenv import load_dotenv

# Import P2's pipeline directly — no HTTP bridge
from agents.manager import run_incident_crew

load_dotenv()

# ── Snowflake connection ─────────────────────────────────────────────
def get_conn():
    return snowflake.connector.connect(
        account=os.getenv("SNOWFLAKE_ACCOUNT"),
        user=os.getenv("SNOWFLAKE_USER"),
        password=os.getenv("SNOWFLAKE_PASSWORD"),
        database=os.getenv("SNOWFLAKE_DATABASE", "INCIDENTDNA"),
        warehouse=os.getenv("SNOWFLAKE_WAREHOUSE", "COMPUTE_WH"),
        role=os.getenv("SNOWFLAKE_ROLE", "ACCOUNTADMIN"),
    )

def insert_deploy_event(deploy_id: str, service: str, version: str, deployed_by: str, diff: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO RAW.DEPLOY_EVENTS (deploy_id, service, version, deployed_by, diff_summary)
        VALUES (%s, %s, %s, %s, %s)
    """, (deploy_id, service, version, deployed_by, diff))
    conn.commit()
    conn.close()

def inject_metric_spike(service: str):
    """Simulate a post-deploy error rate spike in Snowflake metrics."""
    conn = get_conn()
    cur = conn.cursor()
    cur.executemany(
        "INSERT INTO RAW.METRICS (service, metric_name, metric_value) VALUES (%s, %s, %s)",
        [
            (service, "error_rate",  0.22),   # spike: normal is ~0.02
            (service, "latency_p99", 2100),   # spike: normal is ~200ms
        ]
    )
    conn.commit()
    conn.close()
    print(f"[TRIGGER] Injected metric spike for {service}")

def check_anomaly(service: str) -> dict | None:
    """Poll ANALYTICS.METRIC_DEVIATIONS for this service."""
    time.sleep(35)  # wait for dynamic table to refresh (30s lag)
    conn = get_conn()
    cur = conn.cursor(snowflake.connector.DictCursor)
    cur.execute("""
        SELECT service, metric_name, current_value, z_score, severity
        FROM ANALYTICS.METRIC_DEVIATIONS
        WHERE service = %s
        ORDER BY z_score DESC
        LIMIT 1
    """, (service,))
    row = cur.fetchone()
    conn.close()
    return row

# ── GitHub commit handler ────────────────────────────────────────────
def handle_github_commit(payload: dict):
    repo    = payload.get("repository", {}).get("name", "unknown-service")
    sha     = payload.get("after", uuid.uuid4().hex)[:8]
    pusher  = payload.get("pusher", {}).get("name", "unknown")
    message = payload.get("head_commit", {}).get("message", "")

    deploy_id = f"deploy-{sha}"
    service   = repo   # map repo name to service name

    print(f"\n[TRIGGER] GitHub commit on {repo} by {pusher} — {sha}")

    # 1. Record deploy
    insert_deploy_event(deploy_id, service, f"sha-{sha}", pusher, message)

    # 2. Inject spike to simulate post-deploy anomaly
    inject_metric_spike(service)

    # 3. Wait and check for anomaly
    anomaly = check_anomaly(service)
    if not anomaly:
        print(f"[TRIGGER] No anomaly detected for {service} — pipeline skipped")
        return

    # 4. Call agent pipeline
    event = {
        "event_id":    f"evt-{sha}-{int(time.time())}",
        "service":     service,
        "anomaly_type": f"post_deploy_{anomaly['METRIC_NAME']}",
        "severity":    anomaly["SEVERITY"],
        "details": {
            "deploy_id":    deploy_id,
            "metric_name":  anomaly["METRIC_NAME"],
            "current_value": anomaly["CURRENT_VALUE"],
            "z_score":      anomaly["Z_SCORE"],
        }
    }
    print(f"[TRIGGER] Anomaly detected — starting agent pipeline for {event['event_id']}")
    result = run_incident_crew(event)
    print(f"[TRIGGER] Pipeline done: {result}")

# ── Slack message handler ────────────────────────────────────────────
def handle_slack_message(payload: dict):
    text     = payload.get("text", "").lower()
    keywords = ["incident", "down", "outage", "error", "spike", "alert", "p1", "p2"]
    if not any(kw in text for kw in keywords):
        return

    ts = payload.get("ts", str(time.time())).replace(".", "")[:12]
    event = {
        "event_id":    f"slack-{ts}",
        "service":     "unknown",
        "anomaly_type": "slack_report",
        "severity":    "P2",
        "details": {
            "channel": payload.get("channel"),
            "user":    payload.get("user"),
            "text":    payload.get("text"),
        }
    }
    print(f"[TRIGGER] Slack incident message → {event['event_id']}")
    result = run_incident_crew(event)
    print(f"[TRIGGER] Pipeline done: {result}")

# ── Composio listeners ───────────────────────────────────────────────
client = Composio(api_key=os.getenv("COMPOSIO_API_KEY"))

@client.trigger(Trigger.GITHUB_COMMIT_EVENT)
def on_github_commit(event):
    handle_github_commit(event.payload)

@client.trigger(Trigger.SLACK_RECEIVE_MESSAGE)
def on_slack_message(event):
    handle_slack_message(event.payload)

if __name__ == "__main__":
    print("[TRIGGER LISTENER] Waiting for GitHub commits and Slack messages...")
    client.listen()
```

**Run:** `python ingestion/trigger_listener.py`

---

### Step 2 — `dashboard/app.py`
Streamlit entry point with 3-page navigation. Reads Snowflake directly.

```python
import streamlit as st

st.set_page_config(
    page_title="IncidentDNA",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.sidebar.title("🧬 IncidentDNA")
st.sidebar.markdown("Autonomous Incident Intelligence")
st.sidebar.divider()

page = st.sidebar.radio(
    "Navigate",
    ["Live Console", "Reasoning Trace", "Actions Log"]
)

st.sidebar.divider()
st.sidebar.caption("Llama Lounge × Snowflake Hackathon")

from dashboard import components

if page == "Live Console":
    components.live_console()
elif page == "Reasoning Trace":
    components.reasoning_trace()
elif page == "Actions Log":
    components.actions_log()
```

**Run:** `streamlit run dashboard/app.py`

---

### Step 3 — `dashboard/components.py`
All 3 dashboard pages — query Snowflake tables directly.

```python
import os
import uuid
import time
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import snowflake.connector
from dotenv import load_dotenv

load_dotenv()

# ── Snowflake helper ─────────────────────────────────────────────────
def _query(sql: str, params: tuple = None) -> pd.DataFrame:
    conn = snowflake.connector.connect(
        account=os.getenv("SNOWFLAKE_ACCOUNT"),
        user=os.getenv("SNOWFLAKE_USER"),
        password=os.getenv("SNOWFLAKE_PASSWORD"),
        database=os.getenv("SNOWFLAKE_DATABASE", "INCIDENTDNA"),
        warehouse=os.getenv("SNOWFLAKE_WAREHOUSE", "COMPUTE_WH"),
        role=os.getenv("SNOWFLAKE_ROLE", "ACCOUNTADMIN"),
    )
    cur = conn.cursor(snowflake.connector.DictCursor)
    cur.execute(sql, params or ())
    rows = cur.fetchall()
    conn.close()
    return pd.DataFrame(rows) if rows else pd.DataFrame()


# ════════════════════════════════════════════════════════════════════
# PAGE 1 — Live Console
# ════════════════════════════════════════════════════════════════════
def live_console():
    st.title("🔴 Live Incident Console")
    st.markdown("Real-time anomaly feed from `ANALYTICS.METRIC_DEVIATIONS`")

    if st.button("🔄 Refresh"):
        st.rerun()

    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("Active Deviations")
        df = _query("""
            SELECT service, metric_name, current_value, baseline_avg,
                   z_score, severity, recorded_at
            FROM ANALYTICS.METRIC_DEVIATIONS
            ORDER BY z_score DESC
            LIMIT 20
        """)
        if df.empty:
            st.success("✅ No active anomalies")
        else:
            st.dataframe(df, use_container_width=True)

    with col2:
        st.subheader("Severity Breakdown")
        df_sev = _query("""
            SELECT severity, COUNT(*) AS count
            FROM ANALYTICS.METRIC_DEVIATIONS
            GROUP BY severity
        """)
        if not df_sev.empty:
            fig = px.pie(df_sev, values="COUNT", names="SEVERITY",
                         color="SEVERITY",
                         color_discrete_map={"P1": "#ff4444", "P2": "#ff8c00", "P3": "#ffd700"})
            st.plotly_chart(fig, use_container_width=True)

    st.divider()
    st.subheader("Simulate Deploy (for demo)")
    _simulate_panel()


def _simulate_panel():
    """Inline simulate widget — calls run_incident_crew directly."""
    col1, col2 = st.columns(2)
    with col1:
        service      = st.selectbox("Service", ["payment-service", "api-gateway", "notification-service", "worker-service"])
        anomaly_type = st.selectbox("Anomaly", ["db_pool_exhaustion", "memory_leak", "rate_limit_breach", "cache_cold_start", "cpu_spike"])
        severity     = st.select_slider("Severity", options=["P3", "P2", "P1"])
    with col2:
        st.info("Triggers the full agent pipeline:\nAg1 → Ag2 → Ag5 debate → Slack + GitHub")

    if st.button("🔴 Simulate Incident", type="primary", use_container_width=True):
        event = {
            "event_id":    f"sim-{uuid.uuid4().hex[:8]}",
            "service":     service,
            "anomaly_type": anomaly_type,
            "severity":    severity,
            "details":     {"simulated": True},
        }
        with st.spinner("Agents working... (30–90 seconds)"):
            try:
                from agents.manager import run_incident_crew
                result = run_incident_crew(event)
                st.success("✅ Pipeline complete!")
                st.json(result)
            except Exception as e:
                st.error(f"Pipeline error: {e}")


# ════════════════════════════════════════════════════════════════════
# PAGE 2 — Reasoning Trace
# ════════════════════════════════════════════════════════════════════
def reasoning_trace():
    st.title("🧠 Agent Reasoning Trace")
    st.markdown("Step-by-step view from `AI.DECISIONS`")

    df_events = _query("""
        SELECT DISTINCT event_id, service, MAX(created_at) AS last_seen
        FROM AI.DECISIONS
        GROUP BY event_id, service
        ORDER BY last_seen DESC
        LIMIT 20
    """)

    if df_events.empty:
        st.info("No decisions yet. Run a simulation from the Live Console.")
        return

    options = {f"{r['SERVICE']} — {r['EVENT_ID']}": r["EVENT_ID"] for _, r in df_events.iterrows()}
    selected_label = st.selectbox("Select Incident", list(options.keys()))
    selected_event_id = options[selected_label]

    df = _query("""
        SELECT agent_name, output, reasoning, confidence, created_at
        FROM AI.DECISIONS
        WHERE event_id = %s
        ORDER BY created_at ASC
    """, (selected_event_id,))

    st.divider()

    AGENT_LABELS = {
        "ag1_detector":    "🔍 Ag1 — Detector",
        "ag2_investigator": "🔬 Ag2 — Investigator",
        "ag5_validator":   "⚖️ Ag5 — Validator",
        "manager":         "🧠 Manager",
    }

    for _, row in df.iterrows():
        label = AGENT_LABELS.get(row["AGENT_NAME"], row["AGENT_NAME"])
        conf  = row.get("CONFIDENCE", 0)
        with st.expander(f"{label}   |   confidence: {conf:.0%}", expanded=True):
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Output**")
                st.json(row["OUTPUT"] if row["OUTPUT"] else {})
            with col2:
                st.markdown("**Reasoning**")
                st.write(row["REASONING"] or "—")
            st.caption(f"At: {row['CREATED_AT']}")


# ════════════════════════════════════════════════════════════════════
# PAGE 3 — Actions Log
# ════════════════════════════════════════════════════════════════════
def actions_log():
    st.title("⚡ Actions Log")
    st.markdown("Slack + GitHub actions from `AI.ACTIONS` and resolved incidents from `AI.INCIDENT_HISTORY`")

    col1, col2, col3, col4 = st.columns(4)

    df_actions = _query("SELECT * FROM AI.ACTIONS ORDER BY executed_at DESC LIMIT 50")
    df_history = _query("SELECT * FROM AI.INCIDENT_HISTORY ORDER BY resolved_at DESC LIMIT 50")

    total_actions  = len(df_actions)
    sent           = len(df_actions[df_actions["STATUS"] == "SENT"]) if not df_actions.empty else 0
    deduped        = len(df_actions[df_actions["STATUS"] == "SKIPPED_DUPLICATE"]) if not df_actions.empty else 0
    avg_confidence = df_history["CONFIDENCE"].mean() if not df_history.empty else 0

    col1.metric("Total Actions", total_actions)
    col2.metric("Sent", sent)
    col3.metric("Deduplicated", deduped)
    col4.metric("Avg Confidence", f"{avg_confidence:.0%}")

    st.divider()

    st.subheader("Actions")
    if df_actions.empty:
        st.info("No actions yet.")
    else:
        # Color status column
        def color_status(val):
            return {"SENT": "color: green", "FAILED": "color: red", "SKIPPED_DUPLICATE": "color: orange"}.get(val, "")
        st.dataframe(
            df_actions[["EVENT_ID", "ACTION_TYPE", "STATUS", "EXECUTED_AT"]],
            use_container_width=True
        )

    st.divider()

    st.subheader("Resolved Incidents (DNA)")
    if df_history.empty:
        st.info("No resolved incidents yet.")
    else:
        avg_mttr = df_history["MTTR_MINUTES"].mean()
        industry = 47  # Gartner baseline

        fig = go.Figure()
        fig.add_trace(go.Bar(name="IncidentDNA", x=["Avg MTTR"], y=[avg_mttr], marker_color="#00CC96"))
        fig.add_trace(go.Bar(name="Industry Baseline", x=["Avg MTTR"], y=[industry], marker_color="#EF553B"))
        fig.update_layout(barmode="group", yaxis_title="Minutes", title="MTTR vs Industry")
        st.plotly_chart(fig, use_container_width=True)

        st.dataframe(
            df_history[["SERVICE", "ROOT_CAUSE", "FIX_APPLIED", "SEVERITY", "CONFIDENCE", "RESOLVED_AT"]],
            use_container_width=True
        )
```

---

## Integration Outputs (Post in team chat when done)

```
✅ P3 Done.

Trigger listener: python ingestion/trigger_listener.py
  - Listens for GitHub commits via Composio
  - Inserts RAW.DEPLOY_EVENTS, injects metric spike into RAW.METRICS
  - Reads ANALYTICS.METRIC_DEVIATIONS after 35s
  - Calls run_incident_crew() directly (from agents.manager)

Dashboard: streamlit run dashboard/app.py
  - Page 1: Live Console — reads ANALYTICS.METRIC_DEVIATIONS + simulate button
  - Page 2: Reasoning Trace — reads AI.DECISIONS per event
  - Page 3: Actions Log — reads AI.ACTIONS + AI.INCIDENT_HISTORY + MTTR chart
  - Reads Snowflake directly — no API server needed
```

---

## Merge Instructions

```bash
git checkout -b feature/frontend-layer

git add ingestion/ dashboard/
git commit -m "feat: composio trigger listener + streamlit dashboard (3 pages)"

# Can merge in parallel with P2 — no shared files
git checkout main
git merge feature/frontend-layer   # zero conflicts guaranteed
```

> **No conflicts guaranteed:** You own `ingestion/` and `dashboard/`. P1 owns `snowflake/`. P2 owns `agents/`, `tools/`, `utils/`, `requirements.txt`.

---

## Checklist

- [ ] `ingestion/trigger_listener.py` — Composio listener starts without errors
- [ ] `ingestion/trigger_listener.py` — test `handle_github_commit()` manually with a fake payload
- [ ] `ingestion/trigger_listener.py` — confirms anomaly detection via `ANALYTICS.METRIC_DEVIATIONS` after spike injection
- [ ] `ingestion/trigger_listener.py` — calls `run_incident_crew()` and gets a result dict back
- [ ] `dashboard/app.py` — `streamlit run dashboard/app.py` loads without errors
- [ ] `dashboard/components.py` — Live Console shows rows from `ANALYTICS.METRIC_DEVIATIONS`
- [ ] `dashboard/components.py` — Simulate button triggers pipeline and shows `st.json(result)`
- [ ] `dashboard/components.py` — Reasoning Trace shows agent steps from `AI.DECISIONS`
- [ ] `dashboard/components.py` — Actions Log shows rows from `AI.ACTIONS` and MTTR chart
- [ ] End-to-end tested: simulate → decisions logged → actions logged → dashboard shows everything
- [ ] Posted outputs in team chat
- [ ] Merged `feature/frontend-layer` into `main`
