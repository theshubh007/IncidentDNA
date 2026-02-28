# Task 3 — Frontend + Integration Layer (Streamlit + Composio)
**Owner:** Person 3 (Frontend / Integration Engineer)
**Your folders:** `app/` + `utils/` + `trigger_listener.py` (root)
**You touch ONLY these files — zero overlap with P1 or P2.**

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
cp .env.example .env
# Fill in: COMPOSIO_API_KEY, GITHUB_REPO, SLACK_CHANNEL
# P1 fills SNOWFLAKE_* keys — just copy from .env.example after P1 merges
pip install -r requirements.txt   # P2 owns this file, install after they create it
```

**You can start `utils/` immediately** — P2 imports your utils, so finish these first.
**Start `app/` next** — it calls P2's API at `http://localhost:8000`.

P2's API endpoints you'll call:
- `POST /run-pipeline` — trigger agent pipeline (simulate button)
- `GET /incidents` — list resolved incidents for dashboard
- `GET /anomalies` — live anomaly feed for console
- `GET /health` — API health check

P1's Snowflake tables you'll query directly (for live metrics charts):
- `AI.METRIC_DEVIATIONS` — z-score data for charts
- `AI.ANOMALY_RESULTS` — classified anomalies

---

## Your Deliverables

### Step 1 — `utils/idempotency.py`
**Build this FIRST — P2 imports it before they can complete their tools.**

```python
import os
import json
import hashlib
import snowflake.connector
from dotenv import load_dotenv

load_dotenv()

def _get_conn():
    return snowflake.connector.connect(
        account=os.getenv("SNOWFLAKE_ACCOUNT"),
        user=os.getenv("SNOWFLAKE_USER"),
        password=os.getenv("SNOWFLAKE_PASSWORD"),
        database=os.getenv("SNOWFLAKE_DATABASE", "INCIDENTDNA"),
        schema="AI",
        warehouse=os.getenv("SNOWFLAKE_WAREHOUSE", "COMPUTE_WH"),
        role=os.getenv("SNOWFLAKE_ROLE", "ACCOUNTADMIN"),
    )

def _make_key(action_type: str, event_id: str) -> str:
    """Deterministic key — same event + action always produces same key."""
    return hashlib.sha256(f"{action_type}:{event_id}".encode()).hexdigest()[:32]

def safe_execute(action_type: str, event_id: str, payload: dict, executor_fn=None) -> str:
    """
    Check AI.ACTIONS table before executing any Composio action.
    Returns 'SENT', 'SKIPPED_DUPLICATE', or 'FAILED'.

    Usage:
        result = safe_execute(
            action_type="SLACK_ALERT",
            event_id="evt-001",
            payload={"blocks": [...]},
            executor_fn=lambda p: composio_client.post_slack(p)
        )
    """
    idempotency_key = _make_key(action_type, event_id)
    conn = _get_conn()
    cur = conn.cursor()

    # Check for existing action
    cur.execute("""
        SELECT status FROM AI.ACTIONS
        WHERE idempotency_key = %s
    """, (idempotency_key,))
    existing = cur.fetchone()

    if existing:
        return f"SKIPPED_DUPLICATE (previous status: {existing[0]})"

    # Record intent before executing (prevents race conditions)
    cur.execute("""
        INSERT INTO AI.ACTIONS (event_id, action_type, idempotency_key, payload, status)
        VALUES (%s, %s, %s, PARSE_JSON(%s), 'PENDING')
    """, (event_id, action_type, idempotency_key, json.dumps(payload)))
    conn.commit()

    # Execute the action
    if executor_fn:
        try:
            executor_fn(payload)
            status = "SENT"
        except Exception as e:
            status = "FAILED"
            payload["error"] = str(e)
    else:
        status = "SENT"  # dry-run mode

    # Update status
    cur.execute("""
        UPDATE AI.ACTIONS SET status = %s WHERE idempotency_key = %s
    """, (status, idempotency_key))
    conn.commit()
    return status
```

---

### Step 2 — `utils/slack_formatter.py`
**Build this second — P2 imports it.**

```python
from datetime import datetime

SEVERITY_COLORS = {
    "P1": "#FF0000",  # red
    "P2": "#FF8C00",  # orange
    "P3": "#FFD700",  # yellow
}

SEVERITY_EMOJI = {
    "P1": ":rotating_light:",
    "P2": ":warning:",
    "P3": ":information_source:",
}

def format_slack_alert(event_id: str, message: str, severity: str) -> list:
    """
    Returns Slack Block Kit blocks for rich incident alert.
    P2's PostSlackAlertTool passes these directly to Composio.
    """
    color = SEVERITY_COLORS.get(severity, "#808080")
    emoji = SEVERITY_EMOJI.get(severity, ":bell:")
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    return [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"{emoji} [{severity}] IncidentDNA Alert",
                "emoji": True
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": message
            }
        },
        {
            "type": "context",
            "elements": [
                {"type": "mrkdwn", "text": f"*Event ID:* `{event_id}`"},
                {"type": "mrkdwn", "text": f"*Time:* {timestamp}"},
                {"type": "mrkdwn", "text": f"*Severity:* {severity}"},
            ]
        },
        {
            "type": "divider"
        }
    ]
```

---

### Step 3 — `utils/github_formatter.py`
**Build this third — P2 imports it.**

```python
from datetime import datetime

def format_github_issue(event_id: str, title: str, body: str) -> str:
    """
    Returns formatted GitHub issue markdown body.
    P2's CreateGitHubIssueTool passes this to Composio.
    """
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    return f"""## IncidentDNA — Automated Incident Report

**Event ID:** `{event_id}`
**Detected:** {timestamp}
**Auto-generated by:** IncidentDNA Autonomous Agent

---

{body}

---

### Investigation Trace
> Full agent reasoning trace available in the IncidentDNA Streamlit dashboard.

### Resolution
- [ ] Root cause confirmed
- [ ] Fix applied
- [ ] Service restored
- [ ] Post-mortem scheduled

---
*This issue was automatically created by IncidentDNA. Do not close manually until resolution is confirmed.*
"""
```

---

### Step 4 — `utils/fallback.py`
Fallback mode when Composio is unavailable.

```python
import json
from datetime import datetime

def log_fallback_action(action_type: str, event_id: str, payload: dict):
    """Write action to local file if Composio is down."""
    entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "action_type": action_type,
        "event_id": event_id,
        "payload": payload
    }
    with open("fallback_actions.jsonl", "a") as f:
        f.write(json.dumps(entry) + "\n")
    print(f"[FALLBACK] {action_type} for {event_id} logged to fallback_actions.jsonl")
    return "FALLBACK_LOGGED"
```

---

### Step 5 — `trigger_listener.py` (root)
WebSocket listener for GitHub + Slack events via Composio.

```python
import os
import requests
from composio import Composio, Trigger
from dotenv import load_dotenv

load_dotenv()

COMPOSIO_API_KEY = os.getenv("COMPOSIO_API_KEY")
PIPELINE_API_URL = os.getenv("PIPELINE_API_URL", "http://localhost:8000/run-pipeline")

client = Composio(api_key=COMPOSIO_API_KEY)

def handle_github_commit(event_data: dict):
    """Called when a GitHub commit is pushed."""
    payload = {
        "event_id":    f"gh-{event_data.get('after', 'unknown')[:8]}",
        "service":     event_data.get("repository", {}).get("name", "unknown-service"),
        "anomaly_type": "post_deploy_check",
        "severity":    "P3",  # default — agents will reclassify
        "details": {
            "commit_sha": event_data.get("after"),
            "pusher":     event_data.get("pusher", {}).get("name"),
            "message":    event_data.get("head_commit", {}).get("message"),
        }
    }
    print(f"[TRIGGER] GitHub commit → {payload['event_id']}")
    resp = requests.post(PIPELINE_API_URL, json=payload, timeout=10)
    print(f"[TRIGGER] Pipeline response: {resp.status_code}")

def handle_slack_message(event_data: dict):
    """Called when a Slack message mentions an incident keyword."""
    text = event_data.get("text", "").lower()
    keywords = ["incident", "down", "outage", "error", "spike", "alert", "p1", "p2"]

    if not any(kw in text for kw in keywords):
        return  # ignore non-incident messages

    payload = {
        "event_id":    f"slack-{event_data.get('ts', 'unknown').replace('.', '')[:12]}",
        "service":     "unknown",
        "anomaly_type": "slack_report",
        "severity":    "P2",
        "details": {
            "channel": event_data.get("channel"),
            "user":    event_data.get("user"),
            "text":    event_data.get("text"),
        }
    }
    print(f"[TRIGGER] Slack incident message → {payload['event_id']}")
    resp = requests.post(PIPELINE_API_URL, json=payload, timeout=10)
    print(f"[TRIGGER] Pipeline response: {resp.status_code}")

# Register Composio triggers
@client.trigger(Trigger.GITHUB_COMMIT_EVENT)
def on_github_commit(event):
    handle_github_commit(event.payload)

@client.trigger(Trigger.SLACK_RECEIVE_MESSAGE)
def on_slack_message(event):
    handle_slack_message(event.payload)

if __name__ == "__main__":
    print("[TRIGGER LISTENER] Starting... waiting for GitHub + Slack events")
    client.listen()
```

**Run:** `python trigger_listener.py`

---

### Step 6 — `app/main.py`
Streamlit app entry point with 4-page navigation.

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

pages = {
    "Live Console":      "app/pages/live_console.py",
    "Simulate Deploy":   "app/pages/simulate_deploy.py",
    "Reasoning Trace":   "app/pages/reasoning_trace.py",
    "MTTR Analytics":    "app/pages/mttr_analytics.py",
}

page = st.sidebar.radio("Navigate", list(pages.keys()))
st.sidebar.divider()
st.sidebar.caption("Llama Lounge × Snowflake Hackathon")

if page == "Live Console":
    exec(open("app/pages/live_console.py").read())
elif page == "Simulate Deploy":
    exec(open("app/pages/simulate_deploy.py").read())
elif page == "Reasoning Trace":
    exec(open("app/pages/reasoning_trace.py").read())
elif page == "MTTR Analytics":
    exec(open("app/pages/mttr_analytics.py").read())
```

**Run:** `streamlit run app/main.py`

---

### Step 7 — `app/pages/live_console.py`
Real-time anomaly chart pulled from Snowflake.

```python
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import requests
import pandas as pd

API_URL = "http://localhost:8000"

st.title("🔴 Live Incident Console")
st.markdown("Real-time anomaly feed — auto-refreshes every 30 seconds")

# Auto-refresh
if st.button("🔄 Refresh Now"):
    st.rerun()

col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("Active Anomalies")
    try:
        resp = requests.get(f"{API_URL}/anomalies", params={"limit": 20}, timeout=5)
        if resp.status_code == 200:
            anomalies = resp.json()["anomalies"]
            if anomalies:
                df = pd.DataFrame(anomalies)
                # Color rows by severity
                def color_severity(val):
                    colors = {"P1": "background-color: #ff4444; color: white",
                              "P2": "background-color: #ff8c00; color: white",
                              "P3": "background-color: #ffd700"}
                    return colors.get(val, "")
                st.dataframe(
                    df[["service", "anomaly_type", "severity", "detected_at", "status"]],
                    use_container_width=True
                )
            else:
                st.success("✅ No active anomalies")
        else:
            st.error(f"API error: {resp.status_code}")
    except Exception as e:
        st.error(f"Cannot connect to agent API: {e}")
        st.info("Make sure P2's API is running: `python api.py`")

with col2:
    st.subheader("Severity Breakdown")
    try:
        resp = requests.get(f"{API_URL}/anomalies", params={"limit": 50}, timeout=5)
        if resp.status_code == 200:
            anomalies = resp.json()["anomalies"]
            if anomalies:
                df = pd.DataFrame(anomalies)
                severity_counts = df["severity"].value_counts().reset_index()
                fig = px.pie(severity_counts, values="count", names="severity",
                             color="severity",
                             color_discrete_map={"P1": "#ff4444", "P2": "#ff8c00", "P3": "#ffd700"})
                st.plotly_chart(fig, use_container_width=True)
    except:
        st.empty()
```

---

### Step 8 — `app/pages/simulate_deploy.py`
One-click deploy simulation for demo / judges.

```python
import streamlit as st
import requests
import json

API_URL = "http://localhost:8000"

st.title("🚀 Simulate Deploy")
st.markdown("Trigger a fake deploy and watch IncidentDNA detect + respond in real-time")

col1, col2 = st.columns(2)

with col1:
    service = st.selectbox("Service", ["payment-service", "api-gateway", "notification-service", "worker-service"])
    version = st.text_input("Version", value="v2.4.1")
    anomaly_type = st.selectbox("Anomaly to inject", [
        "db_pool_exhaustion",
        "memory_leak",
        "rate_limit_breach",
        "cache_cold_start",
        "cpu_spike",
    ])
    severity = st.select_slider("Severity", options=["P3", "P2", "P1"])

with col2:
    st.info("""
    **What happens when you click Simulate:**
    1. Event sent to Agent API (`POST /run-pipeline`)
    2. Ag1 classifies severity + blast radius
    3. Ag2 investigates root cause (3 sources)
    4. Ag3 generates ranked fix options
    5. Ag5 validates the hypothesis (debate if needed)
    6. Ag4 posts Slack alert + creates GitHub issue
    7. Incident stored as DNA in Snowflake
    """)

st.divider()

if st.button("🔴 Simulate Deploy Incident", type="primary", use_container_width=True):
    import uuid
    event = {
        "event_id":    f"sim-{uuid.uuid4().hex[:8]}",
        "service":     service,
        "anomaly_type": anomaly_type,
        "severity":    severity,
        "details": {
            "version": version,
            "simulated": True,
            "injected_anomaly": anomaly_type
        }
    }

    st.markdown("### Pipeline Running...")
    with st.spinner("Agents working... (this may take 30-90 seconds)"):
        try:
            resp = requests.post(f"{API_URL}/run-pipeline", json=event, timeout=180)
            if resp.status_code == 200:
                result = resp.json()["result"]
                st.success("✅ Pipeline complete!")

                st.json(result)

                # Show summary
                st.markdown(f"""
                | Field | Value |
                |-------|-------|
                | Event ID | `{result.get('event_id')}` |
                | Severity | **{result.get('detection', {}).get('severity')}** |
                | Root Cause | {result.get('root_cause', 'N/A')} |
                | Debate Rounds | {result.get('debate_rounds', 0)} |
                | Validated | {'✅ Yes' if result.get('validated') else '⚠️ Max rounds hit'} |
                """)
            else:
                st.error(f"Pipeline failed: {resp.status_code} — {resp.text}")
        except Exception as e:
            st.error(f"Error: {e}")
```

---

### Step 9 — `app/pages/reasoning_trace.py`
Show live agent reasoning steps.

```python
import streamlit as st
import requests
import pandas as pd

API_URL = "http://localhost:8000"

st.title("🧠 Agent Reasoning Trace")
st.markdown("Step-by-step view of how agents investigated and validated each incident")

try:
    resp = requests.get(f"{API_URL}/incidents", params={"limit": 10}, timeout=5)
    if resp.status_code == 200:
        incidents = resp.json()["incidents"]
        if not incidents:
            st.info("No resolved incidents yet. Run a simulation first.")
        else:
            # Incident selector
            incident_options = {f"{i['service']} — {i['root_cause'][:40]}...": i for i in incidents}
            selected_label = st.selectbox("Select Incident", list(incident_options.keys()))
            selected = incident_options[selected_label]

            col1, col2, col3 = st.columns(3)
            col1.metric("Service", selected["service"])
            col2.metric("MTTR", f"{selected['mttr_minutes']} min")
            col3.metric("Confidence", f"{selected['confidence']:.0%}")

            st.divider()

            # Agent trace steps
            st.subheader("Investigation Steps")
            steps = [
                ("🔍 Ag1 — Detector",     "Classified severity and mapped blast radius"),
                ("🔬 Ag2 — Investigator",  "Searched runbooks + past incidents + live metrics"),
                ("🛠 Ag3 — Fix Advisor",   "Generated 3 ranked fix options"),
                ("⚖️ Ag5 — Validator",     "Stress-tested hypothesis (adversarial check)"),
                ("⚡ Ag4 — Action Agent",  "Posted Slack alert + created GitHub issue"),
            ]
            for agent, description in steps:
                with st.expander(agent):
                    st.write(description)
                    st.write(f"**Root cause found:** {selected['root_cause']}")
                    st.write(f"**Fix applied:** {selected['fix_applied']}")
    else:
        st.error(f"API error: {resp.status_code}")
except Exception as e:
    st.error(f"Cannot connect to agent API: {e}")
```

---

### Step 10 — `app/pages/mttr_analytics.py`
MTTR analytics vs industry baseline.

```python
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import requests
import pandas as pd

API_URL = "http://localhost:8000"
INDUSTRY_BASELINE_MTTR = 47  # minutes (Gartner benchmark)

st.title("📊 MTTR Analytics")
st.markdown("Mean Time to Resolution — IncidentDNA vs industry baseline")

try:
    resp = requests.get(f"{API_URL}/incidents", params={"limit": 50}, timeout=5)
    if resp.status_code == 200:
        incidents = resp.json()["incidents"]
        if not incidents:
            st.info("No resolved incidents yet. Run simulations to generate data.")
        else:
            df = pd.DataFrame(incidents)
            avg_mttr = df["mttr_minutes"].mean()
            improvement = ((INDUSTRY_BASELINE_MTTR - avg_mttr) / INDUSTRY_BASELINE_MTTR) * 100

            # KPI cards
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Our Avg MTTR", f"{avg_mttr:.0f} min", f"-{improvement:.0f}% vs baseline")
            col2.metric("Industry Baseline", f"{INDUSTRY_BASELINE_MTTR} min")
            col3.metric("Total Incidents", len(incidents))
            col4.metric("Avg Confidence", f"{df['confidence'].mean():.0%}")

            st.divider()

            # MTTR comparison bar chart
            fig = go.Figure()
            fig.add_trace(go.Bar(name="IncidentDNA", x=["MTTR"], y=[avg_mttr], marker_color="#00CC96"))
            fig.add_trace(go.Bar(name="Industry Baseline", x=["MTTR"], y=[INDUSTRY_BASELINE_MTTR], marker_color="#EF553B"))
            fig.update_layout(title="MTTR Comparison", barmode="group", yaxis_title="Minutes")
            st.plotly_chart(fig, use_container_width=True)

            # Per-incident MTTR table
            st.subheader("Incident Breakdown")
            st.dataframe(
                df[["service", "root_cause", "mttr_minutes", "confidence", "resolved_at"]],
                use_container_width=True
            )
    else:
        st.error(f"API error: {resp.status_code}")
except Exception as e:
    st.error(f"Cannot connect to agent API: {e}")
```

---

## Integration Outputs (What P2 Needs From You)

As soon as `utils/` is done, post in team chat:

```
✅ P3 utils/ ready. P2 can now complete tools/composio_tool.py:

  from utils.slack_formatter import format_slack_alert
  from utils.github_formatter import format_github_issue
  from utils.idempotency import safe_execute

Functions:
  format_slack_alert(event_id, message, severity) → list of Slack blocks
  format_github_issue(event_id, title, body) → markdown string
  safe_execute(action_type, event_id, payload, executor_fn) → "SENT" | "SKIPPED_DUPLICATE" | "FAILED"

Streamlit dashboard runs on: http://localhost:8501
  - Calls GET /incidents and GET /anomalies from P2's API
  - Calls POST /run-pipeline for the simulate button
```

---

## Merge Instructions

```bash
git checkout -b feature/frontend-layer

# Build utils/ FIRST (P2 depends on it)
git add utils/
git commit -m "feat: composio utils — idempotency, slack formatter, github formatter, fallback"

# Tell P2 their utils are ready, they can finish tools/composio_tool.py

# Then build app/ and trigger_listener.py
git add app/ trigger_listener.py
git commit -m "feat: streamlit dashboard (4 pages) + composio trigger listener"

# Final integration
git checkout main
git merge feature/frontend-layer   # clean merge — no conflicts
```

> **No conflicts guaranteed**: You own `app/`, `utils/`, `trigger_listener.py`. P1 owns `snowflake/`. P2 owns `agents/`, `tools/`, `api.py`, `requirements.txt`.

---

## Checklist

**Build utils/ FIRST (P2 is blocked on these):**
- [ ] `utils/idempotency.py` — `safe_execute()` with Snowflake dedup check
- [ ] `utils/slack_formatter.py` — `format_slack_alert()` returning Block Kit blocks
- [ ] `utils/github_formatter.py` — `format_github_issue()` returning markdown
- [ ] `utils/fallback.py` — `log_fallback_action()` for when Composio is down
- [ ] Committed `utils/` and posted in team chat that P2 can unblock

**Then build the rest:**
- [ ] `trigger_listener.py` — Composio WebSocket listener for GitHub + Slack
- [ ] `app/main.py` — Streamlit navigation
- [ ] `app/pages/live_console.py` — real-time anomaly table + severity chart
- [ ] `app/pages/simulate_deploy.py` — one-click simulate button calling POST /run-pipeline
- [ ] `app/pages/reasoning_trace.py` — agent step-by-step viewer
- [ ] `app/pages/mttr_analytics.py` — MTTR vs industry baseline charts
- [ ] `streamlit run app/main.py` — dashboard loads without errors
- [ ] Simulate a deploy end-to-end through the dashboard
- [ ] Merged `feature/frontend-layer` into `main`
