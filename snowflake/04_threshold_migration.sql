-- ============================================================================
-- IncidentDNA — Threshold Engine Schema Migration
-- Adds columns required by the Autonomous Resolution Threshold Engine.
-- Safe to run multiple times (IF NOT EXISTS).
-- ============================================================================

USE DATABASE INCIDENTDNA;

ALTER TABLE AI.INCIDENT_HISTORY ADD COLUMN IF NOT EXISTS auto_fixed BOOLEAN DEFAULT FALSE;
ALTER TABLE AI.INCIDENT_HISTORY ADD COLUMN IF NOT EXISTS incident_type VARCHAR DEFAULT 'PERFORMANCE';
ALTER TABLE AI.INCIDENT_HISTORY ADD COLUMN IF NOT EXISTS threshold_decision VARCHAR;
ALTER TABLE AI.INCIDENT_HISTORY ADD COLUMN IF NOT EXISTS rule_applied VARCHAR;
