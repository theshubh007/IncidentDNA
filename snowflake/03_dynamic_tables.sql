-- IncidentDNA Dynamic Tables, Streams, Tasks, and AI Functions
-- Run after 01_schema.sql and 02_seed_data.sql
-- These objects auto-refresh to detect and respond to anomalies in real-time

USE DATABASE INCIDENTDNA;

-- ═══════════════════════════════════════════════════════════════════
-- DYNAMIC TABLE 1: Real-time anomaly detection with AI_CLASSIFY
-- ═══════════════════════════════════════════════════════════════════
CREATE OR REPLACE DYNAMIC TABLE ANALYTICS.METRIC_DEVIATIONS
  TARGET_LAG = '1 minute'
  WAREHOUSE = COMPUTE_WH
AS
SELECT
  m.service_name,
  m.metric_name,
  m.metric_value AS current_value,
  b.baseline_avg,
  b.baseline_std,
  ROUND((m.metric_value - b.baseline_avg) / NULLIF(b.baseline_std, 0), 2) AS z_score,
  m.recorded_at,
  SNOWFLAKE.CORTEX.CLASSIFY_TEXT(
    'Metric ' || m.metric_name || ' for service ' || m.service_name
    || ' has value ' || m.metric_value::STRING
    || ' (baseline avg ' || b.baseline_avg::STRING || ', std ' || b.baseline_std::STRING
    || ', z-score ' || ROUND((m.metric_value - b.baseline_avg) / NULLIF(b.baseline_std, 0), 2)::STRING || ')',
    ARRAY_CONSTRUCT('P1_CRITICAL', 'P2_HIGH', 'P3_MEDIUM')
  ):label::STRING AS ai_severity,
  CASE
    WHEN ABS((m.metric_value - b.baseline_avg) / NULLIF(b.baseline_std, 0)) > 3 THEN 'P1'
    WHEN ABS((m.metric_value - b.baseline_avg) / NULLIF(b.baseline_std, 0)) > 2 THEN 'P2'
    ELSE 'P3'
  END AS severity
FROM RAW.METRICS m
JOIN ANALYTICS.METRIC_BASELINES b
  ON m.service_name = b.service_name
  AND m.metric_name = b.metric_name
WHERE m.recorded_at >= DATEADD('minute', -5, CURRENT_TIMESTAMP())
  AND ABS((m.metric_value - b.baseline_avg) / NULLIF(b.baseline_std, 0)) >= 2;

-- ═══════════════════════════════════════════════════════════════════
-- DYNAMIC TABLE 2: Blast radius — which services are at risk
-- ═══════════════════════════════════════════════════════════════════
CREATE OR REPLACE DYNAMIC TABLE ANALYTICS.BLAST_RADIUS
  TARGET_LAG = '1 minute'
  WAREHOUSE = COMPUTE_WH
AS
SELECT
  md.service_name AS source_service,
  md.severity AS source_severity,
  md.z_score AS source_z_score,
  d.depends_on AS affected_service,
  md.recorded_at
FROM ANALYTICS.METRIC_DEVIATIONS md
JOIN RAW.SERVICE_DEPENDENCIES d
  ON md.service_name = d.service_name
WHERE md.severity IN ('P1', 'P2');

-- ═══════════════════════════════════════════════════════════════════
-- DYNAMIC TABLE 3: MTTR metrics with phase breakdown
-- ═══════════════════════════════════════════════════════════════════
CREATE OR REPLACE DYNAMIC TABLE ANALYTICS.MTTR_METRICS
  TARGET_LAG = '5 minutes'
  WAREHOUSE = COMPUTE_WH
AS
SELECT
  ih.service_name,
  COUNT(*) AS total_incidents,
  AVG(ih.mttr_minutes) AS avg_mttr_minutes,
  AVG(DATEDIFF('second', ih.detected_at, ih.investigated_at) / 60.0) AS avg_detect_to_investigate_min,
  AVG(DATEDIFF('second', ih.investigated_at, ih.alerted_at) / 60.0) AS avg_investigate_to_alert_min,
  AVG(DATEDIFF('second', ih.alerted_at, ih.resolved_at) / 60.0) AS avg_alert_to_resolve_min,
  AVG(ih.confidence) AS avg_confidence,
  MIN(ih.mttr_minutes) AS best_mttr,
  MAX(ih.mttr_minutes) AS worst_mttr
FROM AI.INCIDENT_HISTORY ih
WHERE ih.resolved_at IS NOT NULL
GROUP BY ih.service_name;

-- ═══════════════════════════════════════════════════════════════════
-- FORECAST: Predict metric trajectory for blast radius prediction
-- Uses Snowflake CORTEX.FORECAST to project service metrics 30 min ahead
-- ═══════════════════════════════════════════════════════════════════

-- Step 1: Build forecast model on metric timeseries
CREATE OR REPLACE SNOWFLAKE.ML.FORECAST ANALYTICS.METRIC_FORECAST_MODEL(
  INPUT_DATA => SYSTEM$REFERENCE('TABLE', 'RAW.METRICS'),
  SERIES_COLNAME => 'SERVICE_NAME',
  TIMESTAMP_COLNAME => 'RECORDED_AT',
  TARGET_COLNAME => 'METRIC_VALUE'
);

-- Step 2: View that calls the forecast model to predict next 30 minutes
CREATE OR REPLACE VIEW ANALYTICS.METRIC_FORECAST AS
SELECT
  series AS service_name,
  ts AS forecast_time,
  forecast AS predicted_value,
  lower_bound,
  upper_bound
FROM TABLE(ANALYTICS.METRIC_FORECAST_MODEL!FORECAST(
  FORECASTING_PERIODS => 6,        -- 6 periods x 5-min intervals = 30 minutes
  CONFIG_OBJECT => {'prediction_interval': 0.95}
));

-- Step 3: Blast radius forecast — which services are predicted to breach thresholds
CREATE OR REPLACE VIEW ANALYTICS.BLAST_RADIUS_FORECAST AS
SELECT
  f.service_name,
  f.forecast_time,
  f.predicted_value,
  f.upper_bound,
  b.baseline_avg,
  b.baseline_std,
  ROUND((f.predicted_value - b.baseline_avg) / NULLIF(b.baseline_std, 0), 2) AS predicted_z_score,
  CASE
    WHEN ABS((f.predicted_value - b.baseline_avg) / NULLIF(b.baseline_std, 0)) > 3 THEN 'P1_PREDICTED'
    WHEN ABS((f.predicted_value - b.baseline_avg) / NULLIF(b.baseline_std, 0)) > 2 THEN 'P2_PREDICTED'
    ELSE 'NORMAL'
  END AS predicted_severity,
  ARRAY_AGG(d.depends_on) WITHIN GROUP (ORDER BY d.depends_on) AS at_risk_services
FROM ANALYTICS.METRIC_FORECAST f
JOIN ANALYTICS.METRIC_BASELINES b
  ON f.service_name = b.service_name
LEFT JOIN RAW.SERVICE_DEPENDENCIES d
  ON f.service_name = d.service_name
WHERE ABS((f.predicted_value - b.baseline_avg) / NULLIF(b.baseline_std, 0)) > 2
GROUP BY f.service_name, f.forecast_time, f.predicted_value,
         f.upper_bound, b.baseline_avg, b.baseline_std;

-- ═══════════════════════════════════════════════════════════════════
-- CORTEX SEARCH SERVICE: Hybrid vector search over runbooks
-- ═══════════════════════════════════════════════════════════════════
CREATE OR REPLACE CORTEX SEARCH SERVICE RAW.RUNBOOK_SEARCH
  ON title, symptom, root_cause, fix_steps
  WAREHOUSE = COMPUTE_WH
  TARGET_LAG = '1 hour'
AS (
  SELECT
    runbook_id,
    title,
    service_name,
    symptom,
    root_cause,
    fix_steps,
    title || ' ' || symptom || ' ' || root_cause AS search_text
  FROM RAW.RUNBOOKS
);

-- ═══════════════════════════════════════════════════════════════════
-- STREAM: CDC on ANOMALY_EVENTS for real-time trigger
-- ═══════════════════════════════════════════════════════════════════
CREATE OR REPLACE STREAM AI.ANOMALY_STREAM
  ON TABLE AI.ANOMALY_EVENTS
  APPEND_ONLY = TRUE
  SHOW_INITIAL_ROWS = FALSE;

-- ═══════════════════════════════════════════════════════════════════
-- TASK 1: Auto-investigate when anomalies arrive via stream
-- ═══════════════════════════════════════════════════════════════════
CREATE OR REPLACE TASK AI.INVESTIGATE_TASK
  WAREHOUSE = COMPUTE_WH
  SCHEDULE = '1 minute'
  WHEN SYSTEM$STREAM_HAS_DATA('AI.ANOMALY_STREAM')
AS
  INSERT INTO AI.PENDING_INVESTIGATIONS (event_id, service_name, triggered_at)
  SELECT
    event_id,
    service_name,
    CURRENT_TIMESTAMP()
  FROM AI.ANOMALY_STREAM
  WHERE METADATA$ACTION = 'INSERT'
    AND status = 'NEW';

ALTER TASK AI.INVESTIGATE_TASK RESUME;

-- ═══════════════════════════════════════════════════════════════════
-- TASK 2: Auto-detect recovery (check metrics returning to normal)
-- ═══════════════════════════════════════════════════════════════════
CREATE OR REPLACE TASK AI.RESOLUTION_CHECK_TASK
  WAREHOUSE = COMPUTE_WH
  SCHEDULE = '5 minutes'
AS
BEGIN
  -- Mark anomalies as RESOLVED when no deviations remain for that service
  UPDATE AI.ANOMALY_EVENTS ae
  SET
    ae.status = 'RESOLVED'
  WHERE ae.status IN ('NEW', 'PROCESSING')
    AND ae.service_name NOT IN (
      SELECT DISTINCT service_name FROM ANALYTICS.METRIC_DEVIATIONS
    )
    AND DATEDIFF('minute', ae.detected_at, CURRENT_TIMESTAMP()) > 5;

  -- Update MTTR for resolved incidents
  UPDATE AI.INCIDENT_HISTORY ih
  SET
    ih.resolved_at = CURRENT_TIMESTAMP(),
    ih.mttr_minutes = DATEDIFF('minute', ih.detected_at, CURRENT_TIMESTAMP())
  WHERE ih.mttr_minutes = 0
    AND ih.event_id IN (
      SELECT event_id FROM AI.ANOMALY_EVENTS WHERE status = 'RESOLVED'
    );
END;

ALTER TASK AI.RESOLUTION_CHECK_TASK RESUME;

-- ═══════════════════════════════════════════════════════════════════
-- AI_SENTIMENT: Analyze Slack message sentiment
-- ═══════════════════════════════════════════════════════════════════
CREATE OR REPLACE VIEW ANALYTICS.SLACK_SENTIMENT AS
SELECT
  message_id,
  channel,
  author,
  message_text,
  SNOWFLAKE.CORTEX.SENTIMENT(message_text) AS sentiment_score,
  CASE
    WHEN SNOWFLAKE.CORTEX.SENTIMENT(message_text) < -0.3 THEN 'NEGATIVE'
    WHEN SNOWFLAKE.CORTEX.SENTIMENT(message_text) > 0.3 THEN 'POSITIVE'
    ELSE 'NEUTRAL'
  END AS sentiment_label,
  created_at
FROM RAW.SLACK_MESSAGES;
