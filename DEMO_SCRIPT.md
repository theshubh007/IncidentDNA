# IncidentDNA Demo Script

This is a single end-to-end demo runbook for IncidentDNA. It is written for a live presentation where you want to show the full chain clearly:

1. Composio receives or simulates a GitHub-triggered release event.
2. Snowflake detects the anomaly, stores evidence, and powers retrieval.
3. CrewAI agents investigate, validate, recommend, and act.
4. The dashboard, Slack, GitHub, and Snowflake all show visible proof.

Use this as the default 7-10 minute judge demo.

## What This Demo Must Prove

By the end of the demo, the audience should have seen:

1. A release signal enter the system.
2. Snowflake create and surface an anomaly.
3. CrewAI run a multi-agent reasoning loop.
4. Composio send a Slack alert and create a GitHub issue.
5. The React dashboard show the incident visually.

## Exact Tool Coverage

| Platform | Exact Tool / Capability | Where It Is Used | What You Show |
|---|---|---|---|
| Composio | `GITHUB_COMMIT_EVENT` trigger | `ingestion/trigger_listener.py` | Trigger listener output showing a release event |
| Composio | `SLACK_SEND_MESSAGE` | `tools/composio_actions.py` | New incident alert in Slack |
| Composio | `GITHUB_CREATE_AN_ISSUE` | `tools/composio_actions.py` | Auto-created issue in GitHub |
| Snowflake | `RAW.DEPLOY_EVENTS` | Ingestion layer | New deploy row |
| Snowflake | `RAW.METRICS` | Synthetic spike injection | New bad metrics |
| Snowflake | `ANALYTICS.METRIC_DEVIATIONS` | Dynamic table | Visible anomaly and z-score |
| Snowflake | `ANALYTICS.BLAST_RADIUS` | Dynamic table | Affected downstream services |
| Snowflake | `AI.ANOMALY_EVENTS` | Ingestion -> AI handoff | New anomaly event |
| Snowflake | `AI.DECISIONS` | Agent audit log | Every agent step recorded |
| Snowflake | `AI.ACTIONS` | Action log | Slack/GitHub action receipts |
| Snowflake | `AI.INCIDENT_HISTORY` | Incident DNA memory | Final learned incident record |
| Snowflake Cortex | `CLASSIFY_TEXT` | `snowflake/03_dynamic_tables.sql` | AI-generated severity on anomalies |
| Snowflake Cortex | `SEARCH_PREVIEW` via `RAW.RUNBOOK_SEARCH` | `tools/search_runbooks.py` | Runbook retrieval used by Ag2/Ag3 |
| Snowflake Cortex | `SIMILARITY` | `tools/find_similar_incidents.py` | Similar incident retrieval |
| CrewAI | `query_snowflake` | Ag1, Ag2, Ag4, Ag5 | Live SQL-backed reasoning |
| CrewAI | `search_runbooks` | Ag2, Ag3 | Runbook evidence |
| CrewAI | `find_similar_incidents` | Ag2, Ag3 | Past incident evidence |
| CrewAI | Sequential crew execution | `agents/crew.py` and `agents/manager.py` | Agent-by-agent reasoning trace |

## Pre-Demo Setup

Run these once before the live presentation.

### 1. Confirm environment

Make sure `.env` has working values for:

```bash
SNOWFLAKE_ACCOUNT=
SNOWFLAKE_USER=
SNOWFLAKE_PASSWORD=
SNOWFLAKE_DATABASE=INCIDENTDNA
SNOWFLAKE_SCHEMA=AI
SNOWFLAKE_WAREHOUSE=COMPUTE_WH
SNOWFLAKE_ROLE=ACCOUNTADMIN
COMPOSIO_API_KEY=
GITHUB_REPO=owner/repo
SLACK_CHANNEL=#incidents
```

Make sure `dashboard/.env` has live mode enabled:

```bash
VITE_USE_LIVE_DATA=true
VITE_API_BASE_URL=http://localhost:8000/api/v1
VITE_WS_URL=ws://localhost:8000/ws
VITE_ENABLE_REALTIME=true
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
cd dashboard && npm install
```

### 3. Verify Composio is authenticated

```bash
python scripts/setup_composio.py --check
python scripts/setup_composio.py --test
```

If this passes, you know Slack and GitHub actions are available before the judges arrive.

### 4. Verify Snowflake and core tools

```bash
python test_agent.py snowflake
python test_agent.py tools
```

This confirms:

1. Snowflake connectivity works.
2. `query_snowflake` works.
3. `search_runbooks` works.
4. `find_similar_incidents` works.

## Live Demo Screen Layout

Keep these open before you start speaking:

1. Terminal A: `python ingestion/trigger_listener.py`
2. Terminal B: `uvicorn api:app --reload --host 0.0.0.0 --port 8000`
3. Terminal C: `cd dashboard && npm run dev`
4. Browser Tab 1: `http://localhost:5173/` on the Control Tower page
5. Browser Tab 2: `http://localhost:5173/incidents`
6. Browser Tab 3: Snowflake worksheet
7. Browser Tab 4: Slack channel used by `SLACK_CHANNEL`
8. Browser Tab 5: GitHub issues page for `GITHUB_REPO`

This layout gives you live visuals for every layer without switching context too often.

## Snowflake Queries To Keep Ready

Paste these into separate Snowflake worksheets or keep them in one worksheet and run them in order.

### Query 1: deploy event proof

```sql
SELECT event_id, service_name, commit_hash, author, branch, deployed_at
FROM RAW.DEPLOY_EVENTS
ORDER BY deployed_at DESC
LIMIT 5;
```

### Query 2: metric spike proof

```sql
SELECT service_name, metric_name, metric_value, recorded_at
FROM RAW.METRICS
ORDER BY recorded_at DESC
LIMIT 10;
```

### Query 3: anomaly detection proof

```sql
SELECT service_name, metric_name, current_value, baseline_avg, z_score, ai_severity, severity, recorded_at
FROM ANALYTICS.METRIC_DEVIATIONS
ORDER BY recorded_at DESC
LIMIT 10;
```

### Query 4: blast radius proof

```sql
SELECT source_service, source_severity, source_z_score, affected_service, recorded_at
FROM ANALYTICS.BLAST_RADIUS
ORDER BY recorded_at DESC
LIMIT 10;
```

### Query 5: AI handoff proof

```sql
SELECT event_id, service_name, anomaly_type, severity, status, detected_at
FROM AI.ANOMALY_EVENTS
ORDER BY detected_at DESC
LIMIT 10;
```

### Query 6: CrewAI reasoning trace

```sql
SELECT event_id, agent_name, confidence, created_at
FROM AI.DECISIONS
ORDER BY created_at DESC
LIMIT 20;
```

### Query 7: Composio action proof

```sql
SELECT event_id, action_type, status, executed_at
FROM AI.ACTIONS
ORDER BY executed_at DESC
LIMIT 20;
```

### Query 8: learned DNA proof

```sql
SELECT event_id, service_name, root_cause, fix_applied, confidence, mttr_minutes, resolved_at
FROM AI.INCIDENT_HISTORY
ORDER BY resolved_at DESC
LIMIT 10;
```

## 7-10 Minute Live Script

## Step 1: Open with the problem (30-45 seconds)

Say:
"Every release can create an incident, but most tools only alert after the fact. IncidentDNA turns a release event into an autonomous investigation, action, and learning loop."

Show:

1. The Control Tower page in the dashboard.
2. The key cards and the "Live Agent Loop" panel.

What the audience should understand:

1. This is not just alerting.
2. The product is built to detect, reason, act, and remember.

## Step 2: Explain the three-system stack (45-60 seconds)

Say:
"Composio is our integration layer, Snowflake is the operational brain and memory, and CrewAI is the reasoning layer that decides what to do."

Show:

1. Terminal A already running the trigger listener.
2. Briefly mention FastAPI and the dashboard are the visualization layer.

Use this exact mapping:

1. Composio listens and acts.
2. Snowflake stores, detects, retrieves, and scores.
3. CrewAI investigates and orchestrates the response.

## Step 3: Start the services (30 seconds)

If they are not already running, start them in front of the audience.

### Terminal A

```bash
python ingestion/trigger_listener.py
```

Expected visual:

1. "IncidentDNA Trigger Listener Starting..."
2. Target repo output
3. Either Composio trigger registration, or fallback mode if Composio is unavailable

### Terminal B

```bash
uvicorn api:app --reload --host 0.0.0.0 --port 8000
```

### Terminal C

```bash
cd dashboard && npm run dev
```

Expected visual:

1. Dashboard loads at `http://localhost:5173`
2. Overview and Incidents pages are populated

## Step 4: Trigger the incident (60-90 seconds)

Use the real path first. Use the deterministic fallback only if timing is risky.

### Preferred path: real GitHub push

Push a tiny commit to the repo configured in `GITHUB_REPO`.

Say:
"A release lands. Composio sees that GitHub event immediately and hands it to our trigger listener."

Expected visual in Terminal A:

1. "[COMPOSIO TRIGGER] GitHub push event received!"
2. Step 1 insert into `RAW.DEPLOY_EVENTS`
3. Step 2 synthetic metric spike into `RAW.METRICS`
4. Step 3 wait for dynamic table refresh
5. Step 4 anomaly check
6. Step 5 incident pipeline starts

### Safe fallback: deterministic trigger simulation

If you do not want to rely on a live commit during judging, run:

```bash
python test_crewai_trigger.py
```

Say:
"This uses the exact same downstream handler as a real GitHub event, so we get a predictable demo without waiting on webhook timing."

Important note:

This proves the same ingestion and pipeline path after the trigger callback, but the strongest version of the story is still the real Composio trigger.

## Step 5: Show Snowflake as the operational brain (90-120 seconds)

Go to the Snowflake worksheet and run the queries in order.

### First show ingestion

Run Query 1 and Query 2.

Say:
"The release event is now durable in Snowflake, and we immediately write synthetic metrics so the anomaly pipeline has something to react to in a deterministic demo."

What to point at:

1. New row in `RAW.DEPLOY_EVENTS`
2. `error_rate` and `latency_p99` rows in `RAW.METRICS`

### Then show detection

Run Query 3 and Query 4.

Say:
"Now Snowflake dynamic tables compute z-scores in real time. This is where anomaly detection and blast-radius prediction happen."

What to point at:

1. `z_score`
2. `ai_severity`
3. final `severity`
4. affected downstream services in `ANALYTICS.BLAST_RADIUS`

Make this explicit:

1. `CLASSIFY_TEXT` gives the AI severity label.
2. The dynamic table refresh is the automated detection engine.

### Then show AI handoff

Run Query 5.

Say:
"Once the anomaly is confirmed, we create an AI event record. That is the exact handoff point into the CrewAI pipeline."

## Step 6: Narrate the CrewAI reasoning loop (2-3 minutes)

Stay on Terminal A while the pipeline logs, then use Query 6 and the dashboard for proof.

Say:
"The manager now runs five specialized agents in sequence, with a validator that can force a debate loop before any external action is taken."

Use this exact agent narrative.

### Agent 1: Detector

What it does:

1. Uses `query_snowflake`
2. Reads `RAW.SERVICE_DEPENDENCIES`
3. Reads `ANALYTICS.METRIC_DEVIATIONS`
4. Confirms severity and blast radius

What to say:

"Agent 1 does not guess. It queries live Snowflake state to confirm the severity and identify the blast radius."

### Agent 2: Investigator

What it does:

1. Uses `search_runbooks`
2. Uses `find_similar_incidents`
3. Uses `query_snowflake`
4. Produces root cause, confidence, and recommended action

What to say:

"Agent 2 must use all three evidence sources: runbooks, past incidents, and live metrics. That is how we force evidence-based reasoning instead of generic LLM guessing."

Make this explicit:

1. `search_runbooks` hits the Snowflake Cortex Search service `RAW.RUNBOOK_SEARCH`
2. `find_similar_incidents` uses Snowflake Cortex `SIMILARITY`
3. `query_snowflake` checks the live metrics directly

### Agent 5: Validator

What it does:

1. Uses `query_snowflake`
2. Challenges the diagnosis
3. Can return `DEBATE`
4. Forces a re-investigation loop if confidence is weak

What to say:

"We added an adversarial validator so the system can disagree with itself before it touches Slack or GitHub."

### Agent 3: Fix Advisor

What it does:

1. Uses `search_runbooks`
2. Uses `find_similar_incidents`
3. Generates ranked fix options with rollback guidance

What to say:

"After the root cause is accepted, we do not stop at diagnosis. We turn it into concrete remediation choices."

### Agent 4: Action Agent plus manager execution

What it does:

1. Composes the message and issue content
2. Manager executes Composio actions
3. Writes results into `AI.ACTIONS`
4. Stores final memory in `AI.INCIDENT_HISTORY`

What to say:

"The AI decides the content, but actions are still logged and deduplicated so we can audit exactly what happened."

### Proof of agent execution

Run Query 6.

Point at:

1. `ag1_detector`
2. `ag2_investigator`
3. `ag5_validator`
4. `ag3_fix_advisor`
5. `ag4_action_agent`
6. `manager`

Say:
"This is the persistent reasoning trace. Every step is written into Snowflake so the demo is not just terminal theater."

## Step 7: Show Composio actions happening live (60-90 seconds)

Now switch to Slack and GitHub, then return to Snowflake Query 7.

### Slack visual

Show:

1. New message in the configured channel
2. Severity
3. Service
4. Root cause
5. Blast radius
6. Top fix options

Say:
"This Slack message was sent through Composio using `SLACK_SEND_MESSAGE`."

### GitHub visual

Show:

1. Newly created issue
2. Severity in the title
3. Root cause section
4. Recommended fix
5. Resolution checklist

Say:
"The issue was created through Composio using `GITHUB_CREATE_AN_ISSUE`, so engineering gets a tracked artifact immediately."

### Action log proof

Run Query 7.

Say:
"Even external actions are written back into Snowflake so we can prove what was sent, when it was sent, and whether it was deduplicated."

If Composio is temporarily unavailable:

Point out that the code falls back to `FALLBACK_LOGGED` in `AI.ACTIONS` rather than silently dropping the alert.

## Step 8: Show the visuals in the dashboard (60-90 seconds)

Go back to the React dashboard.

### Overview page

Show:

1. "Control Tower"
2. "Live Agent Loop"
3. "Blast Radius"
4. "Similar Past Incidents"
5. "Quick Simulate"

Say:
"This page is the operator view. It turns the Snowflake state and the CrewAI audit log into something immediately readable."

### Incidents page

Open the newest incident, then show:

1. Timeline tab
2. Blast Radius tab
3. Actions tab
4. Postmortem tab if available

Say:
"This is where a human can inspect what the agents concluded, what actions were fired, and what the system learned."

## Step 9: Close with the learning loop (30-45 seconds)

Run Query 8.

Say:
"The important part is not just resolution. Every incident becomes new operational memory. The next time a similar issue appears, the system is faster and more confident."

Point at:

1. `root_cause`
2. `fix_applied`
3. `confidence`
4. `mttr_minutes`

## Strong Closing Line

Use this exact final line:

"Composio gives us real-world triggers and actions, Snowflake gives us live detection plus memory, and CrewAI gives us structured reasoning. Together, IncidentDNA does not just alert on incidents. It investigates, acts, and gets smarter after every release."

## Optional Judge Drill-Downs

If a judge asks for more proof, use one of these fast follow-ups.

### A. Prove Composio tools directly

With the API running, call the manual endpoints. These helpers still send to the destinations configured in `.env`, so use the same Slack channel and GitHub repo you already prepared for the live demo.

```bash
curl -X POST http://localhost:8000/api/v1/tools/slack/send \
  -H "Content-Type: application/json" \
  -d '{"channel":"incidents","message":"Manual Composio Slack proof from demo"}'
```

```bash
curl -X POST http://localhost:8000/api/v1/tools/github/issue \
  -H "Content-Type: application/json" \
  -d '{"repo":"owner/repo","title":"Manual Composio GitHub proof","body":"Created during demo"}'
```

Use this only if they specifically want to isolate the Composio action layer from the full pipeline.

### B. Prove the UI can trigger a visible pipeline

Use the "Quick Simulate" button on the dashboard.

Important note:

This is great for visuals, but it is not the same as the full Composio-triggered ingestion path. Use it as a UI backup, not as the primary proof of the trigger architecture.

## Failure Recovery During The Demo

If something breaks, do not improvise. Use the correct fallback.

### If the GitHub webhook does not fire

Run:

```bash
python test_crewai_trigger.py
```

### If Composio actions fail

Show:

1. `AI.ACTIONS` rows with `FALLBACK_LOGGED`
2. Explain that no alert is lost because the action is still recorded for manual replay

### If runbook search fails

If `search_runbooks` reports that `RAW.RUNBOOK_SEARCH` does not exist or is not authorized:

1. Re-run `snowflake/03_dynamic_tables.sql`
2. Confirm `SHOW CORTEX SEARCH SERVICES IN SCHEMA RAW` returns `RUNBOOK_SEARCH`
3. Re-run the demo after the search service finishes provisioning

### If the agent pipeline fails with a Cortex model authorization error

If you see `Model does not exist or is not authorized` from `SNOWFLAKE.CORTEX.COMPLETE`:

1. Use a Snowflake account with Cortex `COMPLETE` entitlement enabled
2. Or add `GEMINI_API_KEY`, `GROQ_API_KEY`, or `OPENAI_API_KEY` to `.env`
3. Then set `SNOWFLAKE_CORTEX_ENABLED=false` if you want the external provider to take over

### If the dashboard is stale

Check:

1. `uvicorn api:app --reload --host 0.0.0.0 --port 8000`
2. `dashboard/.env` has `VITE_USE_LIVE_DATA=true`
3. Refresh the browser

### If Snowflake looks empty

Run:

```bash
python test_agent.py snowflake
```

If needed, re-run:

1. `snowflake/01_schema.sql`
2. `snowflake/02_seed_data.sql`
3. `snowflake/03_dynamic_tables.sql`

## Best Demo Order Summary

If you need the shortest possible sequence, do it in this order:

1. Open dashboard overview.
2. Start trigger listener, API, and dashboard.
3. Trigger with real GitHub push or `python test_crewai_trigger.py`.
4. Show Terminal A logs.
5. Show Snowflake queries 1 through 7.
6. Show Slack and GitHub.
7. Show dashboard Overview and Incidents.
8. End on `AI.INCIDENT_HISTORY`.

That sequence gives you the cleanest proof that all three systems are working together.
