-- IncidentDNA Dynamic Tables
-- Run after 01_schema.sql and 02_seed_data.sql
-- These tables auto-refresh to detect anomalies in real-time

USE DATABASE INCIDENTDNA;

-- ═══════════════════════════════════════════════════════════════════
-- DYNAMIC TABLE: Real-time anomaly detection
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
-- CORTEX SEARCH SERVICE: Vector search over runbooks
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
