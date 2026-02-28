-- IncidentDNA Schema Setup (Full Architecture)
-- Run this first to create all foundation tables

USE DATABASE INCIDENTDNA;

-- ═══════════════════════════════════════════════════════════════════
-- RAW LAYER — Ingestion tables
-- ═══════════════════════════════════════════════════════════════════
CREATE SCHEMA IF NOT EXISTS RAW;

CREATE TABLE IF NOT EXISTS RAW.DEPLOY_EVENTS (
    event_id VARCHAR PRIMARY KEY,
    service_name VARCHAR,
    commit_hash VARCHAR,
    author VARCHAR,
    branch VARCHAR,
    deployed_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    metadata VARIANT
);

CREATE TABLE IF NOT EXISTS RAW.METRICS (
    metric_id VARCHAR DEFAULT UUID_STRING() PRIMARY KEY,
    service_name VARCHAR,
    metric_name VARCHAR,  -- error_rate, latency_p99, cpu_pct, memory_pct
    metric_value FLOAT,
    recorded_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

CREATE TABLE IF NOT EXISTS RAW.RUNBOOKS (
    runbook_id VARCHAR DEFAULT UUID_STRING() PRIMARY KEY,
    title VARCHAR,
    service_name VARCHAR,
    symptom VARCHAR,
    root_cause VARCHAR,
    fix_steps VARCHAR,
    created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

CREATE TABLE IF NOT EXISTS RAW.PAST_INCIDENTS (
    incident_id VARCHAR DEFAULT UUID_STRING() PRIMARY KEY,
    title VARCHAR,
    service_name VARCHAR,
    root_cause VARCHAR,
    fix_applied VARCHAR,
    resolved_at TIMESTAMP_NTZ,
    mttr_minutes INTEGER
);

CREATE TABLE IF NOT EXISTS RAW.SERVICE_DEPENDENCIES (
    service_name VARCHAR,
    depends_on VARCHAR
);

CREATE TABLE IF NOT EXISTS RAW.SLACK_MESSAGES (
    message_id VARCHAR DEFAULT UUID_STRING() PRIMARY KEY,
    channel VARCHAR,
    author VARCHAR,
    message_text VARCHAR,
    thread_ts VARCHAR,
    created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- ═══════════════════════════════════════════════════════════════════
-- CURATED LAYER — Cleaned/enriched data
-- ═══════════════════════════════════════════════════════════════════
CREATE SCHEMA IF NOT EXISTS CURATED;

CREATE TABLE IF NOT EXISTS CURATED.ENRICHED_DEPLOYS (
    event_id VARCHAR PRIMARY KEY,
    service_name VARCHAR,
    commit_hash VARCHAR,
    author VARCHAR,
    branch VARCHAR,
    deployed_at TIMESTAMP_NTZ,
    files_changed INTEGER DEFAULT 0,
    risk_score FLOAT DEFAULT 0.0,
    enriched_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- ═══════════════════════════════════════════════════════════════════
-- AI LAYER — Agent decisions and actions
-- ═══════════════════════════════════════════════════════════════════
CREATE SCHEMA IF NOT EXISTS AI;

CREATE TABLE IF NOT EXISTS AI.ANOMALY_EVENTS (
    event_id VARCHAR DEFAULT UUID_STRING() PRIMARY KEY,
    deploy_id VARCHAR,
    service_name VARCHAR,
    anomaly_type VARCHAR,
    severity VARCHAR,  -- P1 / P2 / P3
    details VARIANT,
    detected_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    status VARCHAR DEFAULT 'NEW'  -- NEW / PROCESSING / RESOLVED
);

CREATE TABLE IF NOT EXISTS AI.DECISIONS (
    decision_id VARCHAR DEFAULT UUID_STRING() PRIMARY KEY,
    event_id VARCHAR,
    agent_name VARCHAR,
    reasoning VARCHAR,
    output VARIANT,
    confidence FLOAT,
    created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

CREATE TABLE IF NOT EXISTS AI.ACTIONS (
    action_id VARCHAR DEFAULT UUID_STRING() PRIMARY KEY,
    event_id VARCHAR,
    action_type VARCHAR,  -- SLACK_ALERT / GITHUB_ISSUE
    idempotency_key VARCHAR UNIQUE,
    payload VARIANT,
    status VARCHAR,  -- SENT / SKIPPED_DUPLICATE / FAILED
    executed_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

CREATE TABLE IF NOT EXISTS AI.INCIDENT_HISTORY (
    incident_id VARCHAR DEFAULT UUID_STRING() PRIMARY KEY,
    event_id VARCHAR,
    service_name VARCHAR,
    root_cause VARCHAR,
    fix_applied VARCHAR,
    mttr_minutes INTEGER,
    confidence FLOAT,
    detected_at TIMESTAMP_NTZ,
    investigated_at TIMESTAMP_NTZ,
    alerted_at TIMESTAMP_NTZ,
    resolved_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

CREATE TABLE IF NOT EXISTS AI.PENDING_INVESTIGATIONS (
    investigation_id VARCHAR DEFAULT UUID_STRING() PRIMARY KEY,
    event_id VARCHAR,
    service_name VARCHAR,
    triggered_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    status VARCHAR DEFAULT 'PENDING'
);

-- ═══════════════════════════════════════════════════════════════════
-- ANALYTICS LAYER — Computed views and metrics
-- ═══════════════════════════════════════════════════════════════════
CREATE SCHEMA IF NOT EXISTS ANALYTICS;

CREATE TABLE IF NOT EXISTS ANALYTICS.METRIC_BASELINES (
    service_name VARCHAR,
    metric_name VARCHAR,
    baseline_avg FLOAT,
    baseline_std FLOAT,
    last_updated TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    PRIMARY KEY (service_name, metric_name)
);

-- ═══════════════════════════════════════════════════════════════════
-- APP LAYER — Dashboard views and application state
-- ═══════════════════════════════════════════════════════════════════
CREATE SCHEMA IF NOT EXISTS APP;

CREATE TABLE IF NOT EXISTS APP.DASHBOARD_STATE (
    key VARCHAR PRIMARY KEY,
    value VARIANT,
    updated_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);
