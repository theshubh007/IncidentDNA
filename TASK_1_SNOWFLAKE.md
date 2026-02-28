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

## Architecture Context
No Snowflake Tasks, Streams, or Stored Procedures. Everything runs locally (Python). Your job is:
1. Create the schema + tables
2. Seed realistic test data
3. Set up the dynamic table for anomaly detection
4. Set up Cortex Search for runbook retrieval

P2's agents query your tables directly. P3's dashboard reads `AI.DECISIONS` and `AI.ACTIONS` directly from Snowflake.

---

## Your Deliverables (run in this exact order)

### Step 1 — `snowflake/01_schema.sql`
Create all schemas and tables.

```sql
-- ── SCHEMAS ─────────────────────────────────────────────────────────
CREATE DATABASE IF NOT EXISTS INCIDENTDNA;

CREATE SCHEMA IF NOT EXISTS INCIDENTDNA.RAW;
CREATE SCHEMA IF NOT EXISTS INCIDENTDNA.AI;
CREATE SCHEMA IF NOT EXISTS INCIDENTDNA.ANALYTICS;

-- ── RAW LAYER ───────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS INCIDENTDNA.RAW.DEPLOY_EVENTS (
  deploy_id      VARCHAR        PRIMARY KEY,
  service        VARCHAR,
  version        VARCHAR,
  deployed_at    TIMESTAMP_NTZ  DEFAULT CURRENT_TIMESTAMP(),
  deployed_by    VARCHAR,
  diff_summary   VARCHAR
);

CREATE TABLE IF NOT EXISTS INCIDENTDNA.RAW.METRICS (
  metric_id      VARCHAR        DEFAULT UUID_STRING() PRIMARY KEY,
  service        VARCHAR,
  metric_name    VARCHAR,   -- error_rate | latency_p99 | cpu_pct | memory_pct
  metric_value   FLOAT,
  recorded_at    TIMESTAMP_NTZ  DEFAULT CURRENT_TIMESTAMP()
);

CREATE TABLE IF NOT EXISTS INCIDENTDNA.RAW.RUNBOOKS (
  runbook_id     VARCHAR        DEFAULT UUID_STRING() PRIMARY KEY,
  title          VARCHAR,
  symptom        VARCHAR,
  root_cause     VARCHAR,
  fix_steps      VARCHAR,
  service        VARCHAR,
  created_at     TIMESTAMP_NTZ  DEFAULT CURRENT_TIMESTAMP()
);

CREATE TABLE IF NOT EXISTS INCIDENTDNA.RAW.PAST_INCIDENTS (
  incident_id    VARCHAR        DEFAULT UUID_STRING() PRIMARY KEY,
  title          VARCHAR,
  root_cause     VARCHAR,
  fix_applied    VARCHAR,
  service        VARCHAR,
  resolved_at    TIMESTAMP_NTZ,
  mttr_minutes   INTEGER
);

CREATE TABLE IF NOT EXISTS INCIDENTDNA.RAW.SERVICE_DEPENDENCIES (
  service        VARCHAR,
  depends_on     VARCHAR
);

-- ── AI LAYER ────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS INCIDENTDNA.AI.ANOMALY_EVENTS (
  event_id       VARCHAR        DEFAULT UUID_STRING() PRIMARY KEY,
  deploy_id      VARCHAR,
  service        VARCHAR,
  anomaly_type   VARCHAR,
  severity       VARCHAR,   -- P1 | P2 | P3
  details        VARIANT,
  detected_at    TIMESTAMP_NTZ  DEFAULT CURRENT_TIMESTAMP(),
  status         VARCHAR        DEFAULT 'NEW'  -- NEW | PROCESSING | RESOLVED
);

CREATE TABLE IF NOT EXISTS INCIDENTDNA.AI.DECISIONS (
  decision_id    VARCHAR        DEFAULT UUID_STRING() PRIMARY KEY,
  event_id       VARCHAR,
  agent_name     VARCHAR,   -- ag1_detector | ag2_investigator | ag5_validator | manager
  input          VARIANT,
  output         VARIANT,
  reasoning      VARCHAR,
  confidence     FLOAT,
  created_at     TIMESTAMP_NTZ  DEFAULT CURRENT_TIMESTAMP()
);

CREATE TABLE IF NOT EXISTS INCIDENTDNA.AI.ACTIONS (
  action_id         VARCHAR        DEFAULT UUID_STRING() PRIMARY KEY,
  event_id          VARCHAR,
  action_type       VARCHAR,   -- SLACK_ALERT | GITHUB_ISSUE
  idempotency_key   VARCHAR        UNIQUE,
  payload           VARIANT,
  status            VARCHAR,   -- SENT | SKIPPED_DUPLICATE | FAILED
  executed_at       TIMESTAMP_NTZ  DEFAULT CURRENT_TIMESTAMP()
);

CREATE TABLE IF NOT EXISTS INCIDENTDNA.AI.INCIDENT_HISTORY (
  history_id     VARCHAR        DEFAULT UUID_STRING() PRIMARY KEY,
  event_id       VARCHAR,
  service        VARCHAR,
  root_cause     VARCHAR,
  fix_applied    VARCHAR,
  severity       VARCHAR,
  confidence     FLOAT,
  mttr_minutes   INTEGER,
  resolved_at    TIMESTAMP_NTZ  DEFAULT CURRENT_TIMESTAMP()
);
```

**Verify:** `SHOW TABLES IN SCHEMA INCIDENTDNA.RAW;` → 5 tables. `SHOW TABLES IN SCHEMA INCIDENTDNA.AI;` → 4 tables.

---

### Step 2 — `snowflake/02_seed_data.sql`
Seed realistic test data so agents have something to work with from day 1.

```sql
USE DATABASE INCIDENTDNA;
USE SCHEMA RAW;

-- ── DEPLOY EVENT ────────────────────────────────────────────────────
INSERT INTO RAW.DEPLOY_EVENTS VALUES (
  'deploy_001', 'payment-service', 'v2.4.1',
  CURRENT_TIMESTAMP(), 'github-actions', 'Added retry logic to DB pool'
);

-- ── METRICS — normal baseline then spike ────────────────────────────
INSERT INTO RAW.METRICS (service, metric_name, metric_value, recorded_at) VALUES
  ('payment-service', 'error_rate',  0.02, DATEADD('minute', -60, CURRENT_TIMESTAMP())),
  ('payment-service', 'error_rate',  0.02, DATEADD('minute', -30, CURRENT_TIMESTAMP())),
  ('payment-service', 'error_rate',  0.18, DATEADD('minute',  -5, CURRENT_TIMESTAMP())),  -- spike
  ('payment-service', 'latency_p99', 210,  DATEADD('minute', -60, CURRENT_TIMESTAMP())),
  ('payment-service', 'latency_p99', 220,  DATEADD('minute', -30, CURRENT_TIMESTAMP())),
  ('payment-service', 'latency_p99', 1850, DATEADD('minute',  -5, CURRENT_TIMESTAMP())), -- spike
  ('payment-service', 'cpu_pct',     45,   DATEADD('minute', -60, CURRENT_TIMESTAMP())),
  ('payment-service', 'cpu_pct',     48,   DATEADD('minute',  -5, CURRENT_TIMESTAMP())),
  ('api-gateway',     'error_rate',  0.01, DATEADD('minute',  -5, CURRENT_TIMESTAMP())),
  ('api-gateway',     'latency_p99', 95,   DATEADD('minute',  -5, CURRENT_TIMESTAMP()));

-- ── RUNBOOKS (5) ────────────────────────────────────────────────────
INSERT INTO RAW.RUNBOOKS (title, symptom, root_cause, fix_steps, service) VALUES
  ('DB Pool Exhaustion',
   'High latency and DB connection errors after deploy',
   'Connection pool maxed out — too many concurrent connections or connection leak after code change',
   '1. Check pool: SHOW PARAMETERS LIKE connection_pool_size\n2. Kill idle connections\n3. Increase pool: SET max_pool_size=50\n4. Rolling restart service',
   'payment-service'),

  ('Memory Leak — Node.js Service',
   'Memory grows unbounded, OOM kills, service restarts',
   'Event listeners not removed or large objects held in closure in hot code path',
   '1. Heap dump via node --inspect\n2. Identify leak in Chrome DevTools Memory tab\n3. Remove uncleaned listeners\n4. Rolling restart',
   'api-gateway'),

  ('Rate Limit Breach — External API',
   '429 Too Many Requests from downstream service',
   'Burst traffic exceeded upstream rate limits without backoff',
   '1. Check rate limit headers in logs\n2. Add exponential backoff with jitter\n3. Enable request queue\n4. Contact upstream for temporary limit increase',
   'notification-service'),

  ('Cache Cold Start After Deploy',
   'Latency spike immediately after deploy — returns to baseline after ~5 min',
   'Redis cache flushed during deploy rollout; cold start fills cache slowly',
   '1. Confirm cache miss rate via Redis INFO stats\n2. Pre-warm with synthetic read requests\n3. Use cache-aside pattern for next deploy',
   'product-service'),

  ('Disk Full — Log Accumulation',
   'Service crashes with I/O errors, disk usage at 100%',
   'Log rotation not configured; uncompressed logs accumulated over time',
   '1. df -h to confirm disk usage\n2. logrotate -f /etc/logrotate.conf\n3. Delete old .gz archives\n4. Set maxSize in logger config',
   'worker-service');

-- ── PAST INCIDENTS (10 for AI_SIMILARITY training) ──────────────────
INSERT INTO RAW.PAST_INCIDENTS (title, root_cause, fix_applied, service, resolved_at, mttr_minutes) VALUES
  ('Payment DB pool exhausted Dec-2024',
   'DB connection pool hit max 20 during Black Friday traffic surge',
   'Increased pool size to 50, added 30s connection timeout',
   'payment-service', '2024-12-01 14:30:00', 22),

  ('API Gateway OOM Jan-2025',
   'Memory leak in request logging middleware — console.log in hot path',
   'Removed console.log from hot path, added log sampling at 1%',
   'api-gateway', '2025-01-15 09:15:00', 34),

  ('Notification rate-limited Feb-2025',
   'SendGrid 429 during promotional email blast — no backoff configured',
   'Added token bucket limiter, retry queue with exponential backoff',
   'notification-service', '2025-02-10 16:00:00', 18),

  ('Worker disk full Mar-2025',
   'Log rotation disabled after config migration — 3 weeks of unrotated logs',
   'Cleared old logs, re-enabled logrotate with 7-day retention',
   'worker-service', '2025-03-05 02:30:00', 45),

  ('Product service cache thrash Apr-2025',
   'Cache key collision after schema change caused constant eviction',
   'Added service version prefix to all cache keys',
   'product-service', '2025-04-12 11:00:00', 27),

  ('Payment timeout cascade May-2025',
   'Upstream payment gateway latency caused connection pool starvation',
   'Added circuit breaker with 5s timeout, fallback to queue',
   'payment-service', '2025-05-20 18:45:00', 31),

  ('API gateway CPU spike Jun-2025',
   'Regex in auth middleware catastrophic backtrack on malformed tokens',
   'Replaced regex with fixed-length token validation',
   'api-gateway', '2025-06-03 08:20:00', 19),

  ('Notification duplicate sends Jul-2025',
   'Missing idempotency check allowed retry storm to send 5x duplicates',
   'Added SHA256 idempotency key per notification event',
   'notification-service', '2025-07-14 14:00:00', 38),

  ('Product service cold start Aug-2025',
   'Blue-green deploy flushed Redis during traffic cutover',
   'Pre-warm cache before traffic switch using canary requests',
   'product-service', '2025-08-22 09:30:00', 15),

  ('Payment DB index bloat Sep-2025',
   'Unvacuumed dead tuples inflated query plans — 8x slower',
   'VACUUM ANALYZE on transactions table, added autovacuum tuning',
   'payment-service', '2025-09-10 13:15:00', 52);

-- ── SERVICE DEPENDENCIES ─────────────────────────────────────────────
INSERT INTO RAW.SERVICE_DEPENDENCIES VALUES
  ('api-gateway',          'payment-service'),
  ('api-gateway',          'product-service'),
  ('api-gateway',          'notification-service'),
  ('payment-service',      'postgres-primary'),
  ('notification-service', 'sendgrid-api'),
  ('worker-service',       'redis-cache'),
  ('product-service',      'redis-cache');
```

**Verify:** `SELECT COUNT(*) FROM RAW.RUNBOOKS;` → 5. `SELECT COUNT(*) FROM RAW.PAST_INCIDENTS;` → 10.

---

### Step 3 — `snowflake/03_dynamic_tables.sql`
Dynamic table for anomaly detection + Cortex Search for runbooks.

```sql
USE DATABASE INCIDENTDNA;

-- ── BASELINE: rolling 1-hour average per service/metric ─────────────
CREATE OR REPLACE DYNAMIC TABLE ANALYTICS.METRIC_BASELINES
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

-- ── DEVIATIONS: flag when current value is 2+ std devs above baseline
CREATE OR REPLACE DYNAMIC TABLE ANALYTICS.METRIC_DEVIATIONS
  TARGET_LAG = '30 seconds'
  WAREHOUSE = COMPUTE_WH
AS
SELECT
  m.service,
  m.metric_name,
  m.metric_value                                                              AS current_value,
  b.baseline_avg,
  b.baseline_std,
  ROUND(
    (m.metric_value - b.baseline_avg) / NULLIF(b.baseline_std, 0), 2
  )                                                                           AS z_score,
  m.recorded_at,
  CASE
    WHEN ABS((m.metric_value - b.baseline_avg) / NULLIF(b.baseline_std, 0)) > 3 THEN 'P1'
    WHEN ABS((m.metric_value - b.baseline_avg) / NULLIF(b.baseline_std, 0)) > 2 THEN 'P2'
    ELSE 'P3'
  END                                                                         AS severity
FROM RAW.METRICS m
JOIN ANALYTICS.METRIC_BASELINES b
  ON m.service = b.service AND m.metric_name = b.metric_name
WHERE m.recorded_at >= DATEADD('minute', -5, CURRENT_TIMESTAMP())
  AND ABS((m.metric_value - b.baseline_avg) / NULLIF(b.baseline_std, 0)) >= 2;

-- ── CORTEX SEARCH: vector search over runbooks ──────────────────────
CREATE OR REPLACE CORTEX SEARCH SERVICE INCIDENTDNA.RAW.RUNBOOK_SEARCH
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

-- Test the dynamic table (run after seeding metrics)
SELECT * FROM ANALYTICS.METRIC_DEVIATIONS;

-- Test Cortex Search
SELECT SNOWFLAKE.CORTEX.SEARCH_PREVIEW(
  'INCIDENTDNA.RAW.RUNBOOK_SEARCH',
  'database connection timeout errors high latency',
  3
);
```

**Verify:**
- `SELECT * FROM ANALYTICS.METRIC_DEVIATIONS;` → shows z-score rows for payment-service
- Cortex Search preview returns 3 runbook results

---

### Step 4 — `.env.example` (root)

```env
# ── SNOWFLAKE (P1 fills these) ───────────────────────────────────────
SNOWFLAKE_ACCOUNT=sfsehol-llama_lounge_hackathon_sudhag
SNOWFLAKE_USER=USER
SNOWFLAKE_PASSWORD=sn0wf@ll
SNOWFLAKE_DATABASE=INCIDENTDNA
SNOWFLAKE_WAREHOUSE=COMPUTE_WH
SNOWFLAKE_ROLE=ACCOUNTADMIN

# ── COMPOSIO (P2 fills these) ────────────────────────────────────────
COMPOSIO_API_KEY=your_composio_api_key_here
GITHUB_REPO=your-org/your-repo
SLACK_CHANNEL=#incidents
```

---

## Integration Outputs (Post in team chat when done)

```
✅ P1 Done. Tables ready:

RAW schema:
  RAW.DEPLOY_EVENTS   ← trigger_listener.py inserts here after every commit
  RAW.METRICS         ← trigger_listener.py injects spike rows here
  RAW.RUNBOOKS        ← 5 runbooks seeded
  RAW.PAST_INCIDENTS  ← 10 past incidents seeded
  RAW.SERVICE_DEPENDENCIES

AI schema:
  AI.ANOMALY_EVENTS   ← trigger_listener.py writes detected anomalies here
  AI.DECISIONS        ← P2 agents write reasoning steps here (P3 dashboard reads this)
  AI.ACTIONS          ← P2 idempotency layer writes here (P3 dashboard reads this)
  AI.INCIDENT_HISTORY ← P2 manager writes final resolved incident here

ANALYTICS schema:
  ANALYTICS.METRIC_DEVIATIONS  ← auto-refreshes every 30s (P3 trigger_listener reads this)
  ANALYTICS.METRIC_BASELINES   ← auto-refreshes every 1min

Cortex Search: INCIDENTDNA.RAW.RUNBOOK_SEARCH
  Use: SNOWFLAKE.CORTEX.SEARCH_PREVIEW('INCIDENTDNA.RAW.RUNBOOK_SEARCH', query, limit)

.env.example at repo root — copy to .env and fill your keys.
```

---

## Merge Instructions

```bash
git checkout -b feature/snowflake-layer

git add snowflake/ .env.example
git commit -m "feat: snowflake schema, seed data, dynamic tables, cortex search"

git checkout main
git merge feature/snowflake-layer   # zero conflicts guaranteed
```

---

## Checklist

- [ ] `snowflake/01_schema.sql` — all schemas + 9 tables created
- [ ] `snowflake/02_seed_data.sql` — 5 runbooks + 10 past incidents + metrics + deps seeded
- [ ] `snowflake/03_dynamic_tables.sql` — `ANALYTICS.METRIC_DEVIATIONS` refreshing + Cortex Search live
- [ ] `.env.example` created at repo root
- [ ] `SELECT * FROM ANALYTICS.METRIC_DEVIATIONS;` returns rows with z_score
- [ ] Cortex Search preview returns relevant runbooks
- [ ] Posted integration outputs in team chat
- [ ] Merged `feature/snowflake-layer` into `main`
