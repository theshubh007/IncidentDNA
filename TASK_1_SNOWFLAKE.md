# Task 1 — Snowflake Data Layer
**Owner:** Person 1 (Data Engineer)
**Your folders:** `snowflake/` + `.env.example` (root)
**You touch ONLY these files — zero overlap with P2 or P3.**

---

## Snowflake Access
| Field    | Value |
|----------|-------|
| URL      | https://sfsehol-llama_lounge_hackathon_sudhag.snowflakecomputing.com |
| Username | USER |
| Password | sn0wf@ll |

---

## Your Deliverables (run in this exact order)

### Step 1 — `snowflake/01_schema_ddl.sql`
Create all schemas and tables.

```sql
-- Schemas
CREATE SCHEMA IF NOT EXISTS RAW;
CREATE SCHEMA IF NOT EXISTS AI;
CREATE SCHEMA IF NOT EXISTS ANALYTICS;

-- RAW layer
CREATE TABLE IF NOT EXISTS RAW.DEPLOYS (
  deploy_id      VARCHAR PRIMARY KEY,
  service        VARCHAR,
  version        VARCHAR,
  deployed_at    TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
  deployed_by    VARCHAR,
  diff_summary   VARCHAR
);

CREATE TABLE IF NOT EXISTS RAW.METRICS (
  metric_id      VARCHAR DEFAULT UUID_STRING() PRIMARY KEY,
  service        VARCHAR,
  metric_name    VARCHAR,       -- error_rate, latency_p99, cpu_pct, memory_pct
  metric_value   FLOAT,
  recorded_at    TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

CREATE TABLE IF NOT EXISTS RAW.RUNBOOKS (
  runbook_id     VARCHAR DEFAULT UUID_STRING() PRIMARY KEY,
  title          VARCHAR,
  symptom        VARCHAR,
  root_cause     VARCHAR,
  fix_steps      VARCHAR,
  service        VARCHAR,
  created_at     TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

CREATE TABLE IF NOT EXISTS RAW.PAST_INCIDENTS (
  incident_id    VARCHAR DEFAULT UUID_STRING() PRIMARY KEY,
  title          VARCHAR,
  root_cause     VARCHAR,
  fix_applied    VARCHAR,
  service        VARCHAR,
  resolved_at    TIMESTAMP_NTZ,
  mttr_minutes   INTEGER
);

CREATE TABLE IF NOT EXISTS RAW.SERVICE_DEPENDENCIES (
  service        VARCHAR,
  depends_on     VARCHAR
);

-- AI layer
CREATE TABLE IF NOT EXISTS AI.ANOMALY_EVENTS (
  event_id       VARCHAR DEFAULT UUID_STRING() PRIMARY KEY,
  deploy_id      VARCHAR,
  service        VARCHAR,
  anomaly_type   VARCHAR,
  severity       VARCHAR,       -- P1 / P2 / P3
  details        VARIANT,
  detected_at    TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
  status         VARCHAR DEFAULT 'NEW'  -- NEW / PROCESSING / RESOLVED
);

CREATE TABLE IF NOT EXISTS AI.AGENT_RUNS (
  run_id         VARCHAR DEFAULT UUID_STRING() PRIMARY KEY,
  event_id       VARCHAR,
  agent_name     VARCHAR,
  input          VARIANT,
  output         VARIANT,
  started_at     TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
  finished_at    TIMESTAMP_NTZ,
  status         VARCHAR        -- SUCCESS / FAILED / DEBATING
);

CREATE TABLE IF NOT EXISTS AI.ACTIONS (
  action_id      VARCHAR DEFAULT UUID_STRING() PRIMARY KEY,
  event_id       VARCHAR,
  action_type    VARCHAR,       -- SLACK_ALERT / GITHUB_ISSUE
  idempotency_key VARCHAR UNIQUE,
  payload        VARIANT,
  executed_at    TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
  status         VARCHAR        -- SENT / SKIPPED_DUPLICATE / FAILED
);

-- ANALYTICS layer
CREATE TABLE IF NOT EXISTS ANALYTICS.INCIDENT_DNA (
  dna_id         VARCHAR DEFAULT UUID_STRING() PRIMARY KEY,
  event_id       VARCHAR,
  service        VARCHAR,
  root_cause     VARCHAR,
  fix_applied    VARCHAR,
  mttr_minutes   INTEGER,
  confidence     FLOAT,
  resolved_at    TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

CREATE TABLE IF NOT EXISTS ANALYTICS.MTTR_METRICS (
  period_date    DATE,
  avg_mttr       FLOAT,
  total_incidents INTEGER,
  p1_count       INTEGER,
  p2_count       INTEGER,
  p3_count       INTEGER
);
```

**Verify:** Run `SHOW TABLES IN SCHEMA RAW;` — should show 5 tables.

---

### Step 2 — `snowflake/02_seed_data.sql`
Seed realistic test data so agents have something to work with from day 1.

```sql
-- Seed a deploy event
INSERT INTO RAW.DEPLOYS VALUES (
  'deploy_001', 'payment-service', 'v2.4.1',
  CURRENT_TIMESTAMP(), 'github-actions', 'Added retry logic to DB pool'
);

-- Seed metrics showing an incident (error rate spike)
INSERT INTO RAW.METRICS (service, metric_name, metric_value) VALUES
  ('payment-service', 'error_rate',   0.02),
  ('payment-service', 'error_rate',   0.18),   -- spike after deploy
  ('payment-service', 'latency_p99',  210),
  ('payment-service', 'latency_p99',  1850),   -- spike
  ('payment-service', 'cpu_pct',      45),
  ('payment-service', 'cpu_pct',      48),
  ('api-gateway',     'error_rate',   0.01),
  ('api-gateway',     'latency_p99',  95);

-- Seed 5 runbooks
INSERT INTO RAW.RUNBOOKS (title, symptom, root_cause, fix_steps, service) VALUES
('DB Pool Exhaustion',
 'High latency + DB connection errors',
 'Connection pool maxed out — too many concurrent requests or connection leak',
 '1. Check pool size: SHOW PARAMETERS LIKE connection_pool_size;\n2. Kill idle connections\n3. Scale pool: SET max_pool_size=50;\n4. Restart service',
 'payment-service'),

('Memory Leak — Node.js',
 'Memory grows unbounded, OOM kills',
 'Event listeners not removed or large objects held in closure',
 '1. Heap dump: node --inspect\n2. Find leak with Chrome DevTools\n3. Fix listener cleanup\n4. Rolling restart',
 'api-gateway'),

('Rate Limit Breach',
 '429 errors from downstream APIs',
 'Burst traffic exceeded upstream rate limits',
 '1. Check rate limit headers\n2. Add exponential backoff\n3. Enable request queue\n4. Contact upstream for limit increase',
 'notification-service'),

('Cache Cold Start',
 'Latency spike after deploy — returns to normal after ~5 min',
 'Redis cache flushed during deploy; cold start fills cache slowly',
 '1. Confirm cache miss rate in Redis INFO\n2. Pre-warm cache with synthetic requests\n3. Use cache-aside pattern next deploy',
 'product-service'),

('Disk Full — Log Accumulation',
 'Service crashes, disk I/O errors in logs',
 'Log rotation not configured; logs filled disk',
 '1. df -h to confirm\n2. logrotate -f /etc/logrotate.conf\n3. Delete old .gz logs\n4. Set max log size in config',
 'worker-service');

-- Seed past incidents (training data for AI_SIMILARITY)
INSERT INTO RAW.PAST_INCIDENTS (title, root_cause, fix_applied, service, resolved_at, mttr_minutes) VALUES
('Payment DB pool exhausted Dec-2024',
 'DB connection pool hit max 20 during Black Friday traffic',
 'Increased pool to 50, added connection timeout of 30s',
 'payment-service', '2024-12-01 14:30:00', 22),

('API Gateway OOM Jan-2025',
 'Memory leak in request logging middleware',
 'Removed console.log in hot path, added log sampling',
 'api-gateway', '2025-01-15 09:15:00', 34),

('Notification rate-limited Feb-2025',
 'SendGrid 429 during promotional blast',
 'Added token bucket limiter, retry queue with backoff',
 'notification-service', '2025-02-10 16:00:00', 18);

-- Seed service dependencies
INSERT INTO RAW.SERVICE_DEPENDENCIES VALUES
  ('api-gateway',          'payment-service'),
  ('api-gateway',          'product-service'),
  ('payment-service',      'postgres-primary'),
  ('notification-service', 'sendgrid-api'),
  ('worker-service',       'redis-cache');
```

**Verify:** `SELECT COUNT(*) FROM RAW.RUNBOOKS;` → 5 rows.

---

### Step 3 — `snowflake/03_dynamic_tables.sql`
Auto-compute anomalies whenever new metrics land.

```sql
-- Baseline per service/metric (rolling 1-hour average before deploy)
CREATE OR REPLACE DYNAMIC TABLE AI.METRIC_BASELINES
  TARGET_LAG = '1 minute'
  WAREHOUSE = COMPUTE_WH
AS
SELECT
  service,
  metric_name,
  AVG(metric_value)    AS baseline_avg,
  STDDEV(metric_value) AS baseline_std,
  MAX(recorded_at)     AS last_updated
FROM RAW.METRICS
WHERE recorded_at >= DATEADD('hour', -1, CURRENT_TIMESTAMP())
GROUP BY service, metric_name;

-- Deviation detection: flag when current value is 2+ std devs from baseline
CREATE OR REPLACE DYNAMIC TABLE AI.METRIC_DEVIATIONS
  TARGET_LAG = '30 seconds'
  WAREHOUSE = COMPUTE_WH
AS
SELECT
  m.service,
  m.metric_name,
  m.metric_value                                              AS current_value,
  b.baseline_avg,
  b.baseline_std,
  ROUND((m.metric_value - b.baseline_avg) / NULLIF(b.baseline_std, 0), 2) AS z_score,
  m.recorded_at,
  CASE
    WHEN ABS((m.metric_value - b.baseline_avg) / NULLIF(b.baseline_std, 0)) > 3 THEN 'P1'
    WHEN ABS((m.metric_value - b.baseline_avg) / NULLIF(b.baseline_std, 0)) > 2 THEN 'P2'
    ELSE 'P3'
  END AS severity
FROM RAW.METRICS m
JOIN AI.METRIC_BASELINES b
  ON m.service = b.service AND m.metric_name = b.metric_name
WHERE m.recorded_at >= DATEADD('minute', -5, CURRENT_TIMESTAMP())
  AND ABS((m.metric_value - b.baseline_avg) / NULLIF(b.baseline_std, 0)) >= 2;

-- Classified anomaly results using Cortex AI_CLASSIFY
CREATE OR REPLACE DYNAMIC TABLE AI.ANOMALY_RESULTS
  TARGET_LAG = '1 minute'
  WAREHOUSE = COMPUTE_WH
AS
SELECT
  d.service,
  d.metric_name,
  d.current_value,
  d.severity,
  d.z_score,
  d.recorded_at,
  SNOWFLAKE.CORTEX.CLASSIFY_TEXT(
    'Anomaly: service=' || d.service ||
    ' metric=' || d.metric_name ||
    ' value=' || d.current_value::VARCHAR ||
    ' z_score=' || d.z_score::VARCHAR,
    ['database_issue', 'memory_issue', 'network_issue', 'rate_limit', 'cpu_spike', 'unknown']
  ):label::VARCHAR AS anomaly_class
FROM AI.METRIC_DEVIATIONS d;
```

**Verify:** `SELECT * FROM AI.ANOMALY_RESULTS LIMIT 5;` — shows classified anomalies.

---

### Step 4 — `snowflake/04_cortex_search.sql`
Vector search over runbooks for the Investigator agent.

```sql
-- Cortex Search Service for runbook retrieval
CREATE OR REPLACE CORTEX SEARCH SERVICE RAW.RUNBOOK_SEARCH
  ON title, symptom, root_cause, fix_steps
  WAREHOUSE = COMPUTE_WH
  TARGET_LAG = '1 hour'
AS (
  SELECT
    runbook_id,
    title,
    symptom,
    root_cause,
    fix_steps,
    service,
    title || ' ' || symptom || ' ' || root_cause AS search_text
  FROM RAW.RUNBOOKS
);

-- Test it
SELECT SNOWFLAKE.CORTEX.SEARCH_PREVIEW(
  'RUNBOOK_SEARCH',
  'database connection timeout errors high latency',
  3
);
```

**Verify:** The `SEARCH_PREVIEW` call returns 3 relevant runbook results.

---

### Step 5 — `snowflake/05_stream_task.sql`
Stream on new anomalies → trigger Python agent pipeline.

```sql
-- Stream on new anomaly events
CREATE OR REPLACE STREAM AI.ANOMALY_STREAM
  ON TABLE AI.ANOMALY_EVENTS
  APPEND_ONLY = TRUE;

-- Task: fires every 30s when new rows arrive in stream
CREATE OR REPLACE TASK AI.TRIGGER_AGENT_PIPELINE
  WAREHOUSE = COMPUTE_WH
  SCHEDULE = '1 minute'
  WHEN SYSTEM$STREAM_HAS_DATA('AI.ANOMALY_STREAM')
AS
CALL AI.RUN_INCIDENT_PIPELINE(
  (SELECT ARRAY_AGG(event_id) FROM AI.ANOMALY_STREAM WHERE METADATA$ACTION = 'INSERT')
);

-- Enable the task
ALTER TASK AI.TRIGGER_AGENT_PIPELINE RESUME;
```

**Verify:** `SHOW TASKS IN SCHEMA AI;` → task shows as `started`.

---

### Step 6 — `snowflake/06_stored_procedure.sql`
Stored proc that calls P2's FastAPI endpoint when an anomaly is detected.

```sql
-- Stored procedure: calls the CrewAI agent API
CREATE OR REPLACE PROCEDURE AI.RUN_INCIDENT_PIPELINE(event_ids ARRAY)
RETURNS VARCHAR
LANGUAGE PYTHON
RUNTIME_VERSION = '3.10'
PACKAGES = ('snowflake-snowpark-python', 'requests')
HANDLER = 'run_pipeline'
AS $$
import requests
import json

def run_pipeline(session, event_ids):
    # P2 will provide this URL after deploying their FastAPI server
    # Replace with actual URL when P2 deploys
    API_URL = "http://localhost:8000/run-pipeline"

    results = []
    for event_id in event_ids:
        # Fetch event details from Snowflake
        row = session.sql(f"""
            SELECT event_id, service, anomaly_type, severity, details
            FROM AI.ANOMALY_EVENTS
            WHERE event_id = '{event_id}'
        """).collect()

        if not row:
            continue

        payload = {
            "event_id":    row[0]["EVENT_ID"],
            "service":     row[0]["SERVICE"],
            "anomaly_type": row[0]["ANOMALY_TYPE"],
            "severity":    row[0]["SEVERITY"],
            "details":     row[0]["DETAILS"]
        }

        try:
            resp = requests.post(API_URL, json=payload, timeout=300)
            results.append(f"{event_id}: {resp.status_code}")
        except Exception as e:
            results.append(f"{event_id}: ERROR - {str(e)}")

    return json.dumps(results)
$$;

-- Test call (use a real event_id after seeding anomaly events)
-- CALL AI.RUN_INCIDENT_PIPELINE(ARRAY_CONSTRUCT('test-event-001'));
```

---

### Step 7 — `.env.example` (root of repo)
Create this file at the project root so P2 and P3 can copy it:

```
# ── SNOWFLAKE (P1 fills these) ──────────────────────────────────────
SNOWFLAKE_ACCOUNT=sfsehol-llama_lounge_hackathon_sudhag
SNOWFLAKE_USER=USER
SNOWFLAKE_PASSWORD=sn0wf@ll
SNOWFLAKE_DATABASE=INCIDENTDNA
SNOWFLAKE_SCHEMA=AI
SNOWFLAKE_WAREHOUSE=COMPUTE_WH
SNOWFLAKE_ROLE=ACCOUNTADMIN

# ── COMPOSIO (P3 fills these) ────────────────────────────────────────
COMPOSIO_API_KEY=your_composio_api_key_here
GITHUB_REPO=your-org/your-repo
SLACK_CHANNEL=#incidents

# ── API SERVER (P2 fills these) ──────────────────────────────────────
API_HOST=0.0.0.0
API_PORT=8000
```

---

## Integration Outputs (What P2 + P3 Need From You)

When you finish, post in team chat:

```
✅ P1 Done. Here's what you need:

Tables ready:
  - RAW.DEPLOYS, RAW.METRICS, RAW.RUNBOOKS, RAW.PAST_INCIDENTS, RAW.SERVICE_DEPENDENCIES
  - AI.ANOMALY_EVENTS, AI.AGENT_RUNS, AI.ACTIONS
  - ANALYTICS.INCIDENT_DNA, ANALYTICS.MTTR_METRICS

Dynamic Tables (auto-refreshing):
  - AI.METRIC_BASELINES → baseline per service
  - AI.METRIC_DEVIATIONS → z-score flagged rows
  - AI.ANOMALY_RESULTS → classified anomaly type

Cortex Search: RAW.RUNBOOK_SEARCH (use SNOWFLAKE.CORTEX.SEARCH_PREVIEW)
Stream: AI.ANOMALY_STREAM (fires when new rows in ANOMALY_EVENTS)
Task: AI.TRIGGER_AGENT_PIPELINE (calls stored proc every 1 min)
Stored Proc: AI.RUN_INCIDENT_PIPELINE(event_ids ARRAY) → calls P2's API

.env.example is at repo root — copy it to .env and fill your keys.
Snowflake connection: account=sfsehol-llama_lounge_hackathon_sudhag user=USER pass=sn0wf@ll
```

---

## Merge Instructions

```bash
# Work on your own branch
git checkout -b feature/snowflake-layer

# Only commit files in snowflake/ and .env.example
git add snowflake/ .env.example
git commit -m "feat: snowflake data layer — schemas, seed data, dynamic tables, cortex search, stream/task, stored proc"

# When P2 and P3 are ready to integrate
git checkout main
git merge feature/snowflake-layer   # clean merge — no conflicts possible
```

> **No conflicts guaranteed**: You only touch `snowflake/` and `.env.example`. P2 owns `agents/` + `tools/` + `api.py`. P3 owns `app/` + `utils/` + `trigger_listener.py`.

---

## Checklist

- [ ] `snowflake/01_schema_ddl.sql` — all 10 tables created
- [ ] `snowflake/02_seed_data.sql` — 5 runbooks + 3 past incidents + metrics seeded
- [ ] `snowflake/03_dynamic_tables.sql` — 3 dynamic tables auto-refreshing
- [ ] `snowflake/04_cortex_search.sql` — RUNBOOK_SEARCH service live
- [ ] `snowflake/05_stream_task.sql` — stream + task enabled and running
- [ ] `snowflake/06_stored_procedure.sql` — stored proc created (update API_URL when P2 deploys)
- [ ] `.env.example` — created at repo root
- [ ] Posted integration outputs in team chat
- [ ] Merged `feature/snowflake-layer` into `main`
