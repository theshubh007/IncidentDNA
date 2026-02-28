# Design Document

## Overview

IncidentDNA is a lean, local-execution autonomous incident response system built for the Snowflake Cortex hackathon. The architecture eliminates HTTP bridges and stored procedures in favor of direct Python execution, making it simpler, faster, and more deterministic.

**Core Philosophy:** Everything runs locally. No FastAPI. No Snowflake Tasks. No Streams. Just Python → Snowflake → Composio.

## Architecture

```
GitHub Commit (Composio Trigger)
         ↓
ingestion/trigger_listener.py
         ↓
Insert RAW.DEPLOY_EVENTS
Inject synthetic metric spike
         ↓
Query ANALYTICS.METRIC_DEVIATIONS
         ↓
If anomaly detected:
    agents/manager.py orchestrates:
        - Ag1 Detector (severity + blast radius)
        - Ag2 Investigator (3-source evidence)
        - Ag5 Validator (adversarial debate)
         ↓
    tools/composio_actions.py executes:
        - Slack alert (idempotent)
        - GitHub issue (idempotent)
         ↓
    Log to Snowflake:
        - AI.DECISIONS (agent reasoning)
        - AI.ACTIONS (composio executions)
        - AI.INCIDENT_HISTORY (resolved incidents)
         ↓
dashboard/app.py reads Snowflake directly
    - Live Console (AI.ANOMALY_EVENTS)
    - Reasoning Trace (AI.DECISIONS)
    - Actions Log (AI.ACTIONS)
```

## Components and Interfaces

### 1. Snowflake Layer (`snowflake/`)

**Files:**
- `01_schema.sql` - DDL for RAW, AI, ANALYTICS schemas
- `02_seed_data.sql` - 5 runbooks, 10 past incidents, metrics, baselines
- `03_dynamic_tables.sql` - ANALYTICS.METRIC_DEVIATIONS, RAW.RUNBOOK_SEARCH

**Key Tables:**
- `RAW.DEPLOY_EVENTS` - Deployment records
- `RAW.METRICS` - Time-series metrics (error_rate, latency_p99, cpu_pct)
- `RAW.RUNBOOKS` - Operational runbooks for common issues
- `RAW.PAST_INCIDENTS` - Historical incident resolutions
- `AI.ANOMALY_EVENTS` - Detected anomalies (NEW → PROCESSING → RESOLVED)
- `AI.DECISIONS` - Agent reasoning logs
- `AI.ACTIONS` - Composio action executions with idempotency
- `AI.INCIDENT_HISTORY` - Resolved incidents with MTTR
- `ANALYTICS.METRIC_DEVIATIONS` - Real-time z-score anomalies (dynamic table)

**Cortex Services:**
- `RAW.RUNBOOK_SEARCH` - Vector search over runbooks using Cortex Search
- `CORTEX.SIMILARITY()` - Semantic similarity for past incident matching
- `CORTEX.COMPLETE()` - LLM reasoning via Llama 3.1-70B

### 2. Ingestion Layer (`ingestion/`)

**File:** `trigger_listener.py`

**Responsibilities:**
- Listen for GitHub commit events via Composio webhooks
- Insert deploy event into `RAW.DEPLOY_EVENTS`
- Inject synthetic metric spike into `RAW.METRICS`
- Query `ANALYTICS.METRIC_DEVIATIONS` for anomalies
- If anomaly exists, call `agents.manager.run_pipeline()` directly (no HTTP)

**Interface:**
```python
def handle_github_commit(event_data: dict) -> None:
    # Insert deploy event
    # Inject metric spike
    # Check for anomalies
    if anomaly_detected:
        from agents.manager import run_pipeline
        run_pipeline(anomaly_payload)
```

### 3. Agent Layer (`agents/`)

**Files:**
- `manager.py` - Orchestrates 3 agents with debate loop
- `ag1_detector.py` - Severity classification + blast radius
- `ag2_investigator.py` - 3-source root cause investigation
- `ag5_validator.py` - Adversarial hypothesis validation

**Agent 1: Detector**
- Input: Anomaly event (service, metric, z-score)
- Tools: `query_snowflake`, `ai_complete`
- Output: `{"severity": "P1|P2|P3", "blast_radius": ["svc1"], "classification": "..."}`
- Logic: Query dependencies, confirm severity, map affected services

**Agent 2: Investigator**
- Input: Detection result + anomaly details
- Tools: `search_runbooks`, `find_similar_incidents`, `query_snowflake`, `ai_complete`
- Output: `{"root_cause": "...", "confidence": 0.82, "evidence": ["runbook", "past_incident", "metrics"]}`
- Logic: Search runbooks via Cortex Search, find similar incidents via SIMILARITY, query live metrics, synthesize hypothesis

**Agent 5: Validator**
- Input: Investigation hypothesis
- Tools: `query_snowflake`, `ai_complete`
- Output: `{"decision": "APPROVE|DEBATE", "objections": [...], "adjusted_confidence": 0.75}`
- Logic: Apply 4 stress tests (alternative causes, evidence quality, fix safety, simplicity), approve if confidence >= 0.7

**Manager Orchestration:**
```python
def run_pipeline(event: dict) -> dict:
    # Phase 1: Detect
    detection = run_agent(ag1, event)
    
    # Phase 2: Investigate
    investigation = run_agent(ag2, {**event, **detection})
    
    # Phase 3: Validate (max 2 debate rounds)
    for round in range(MAX_DEBATE_ROUNDS):
        validation = run_agent(ag5, investigation)
        if validation["decision"] == "APPROVE":
            break
        investigation["confidence"] = validation["adjusted_confidence"]
    
    # Phase 4: Execute Actions
    execute_composio_actions(event, investigation, detection)
    
    # Phase 5: Log to Snowflake
    log_decisions(event, detection, investigation, validation)
    log_incident_history(event, investigation)
    
    return result
```

### 4. Tools Layer (`tools/`)

**Files:**
- `snowflake_conn.py` - Connection utilities (get_connection, run_query, run_dml)
- `search_runbooks.py` - Cortex Search wrapper
- `find_similar_incidents.py` - CORTEX.SIMILARITY wrapper
- `query_snowflake.py` - Generic SELECT tool for agents
- `ai_complete_tool.py` - CORTEX.COMPLETE wrapper
- `composio_actions.py` - Slack + GitHub execution with idempotency
- `idempotency.py` - Duplicate action prevention

**Idempotency Design:**
```python
def safe_execute(action_type: str, event_id: str, payload: dict, executor_fn) -> str:
    key = sha256(f"{action_type}:{event_id}")
    
    # Check for duplicate
    existing = query("SELECT status FROM AI.ACTIONS WHERE idempotency_key = ?", key)
    if existing:
        return f"SKIPPED_DUPLICATE ({existing.status})"
    
    # Record intent (prevents race conditions)
    insert("AI.ACTIONS", {idempotency_key: key, status: "PENDING"})
    
    # Execute
    try:
        executor_fn(payload)
        status = "SENT"
    except Exception as e:
        status = "FAILED"
    
    # Update status
    update("AI.ACTIONS", {status: status}, where={idempotency_key: key})
    return status
```

### 5. Dashboard Layer (`dashboard/`)

**Files:**
- `app.py` - Streamlit entry point with navigation
- `components.py` - Reusable UI components

**Pages:**
1. **Live Console** - Active anomalies from `AI.ANOMALY_EVENTS`, severity breakdown chart
2. **Reasoning Trace** - Step-by-step agent decisions from `AI.DECISIONS`
3. **Actions Log** - Slack/GitHub actions from `AI.ACTIONS` with status

**Data Flow:**
- Dashboard queries Snowflake directly (no API layer)
- Uses `utils/snowflake_conn.py` for connections
- Refreshes on button click or auto-refresh timer

### 6. Utilities Layer (`utils/`)

**File:** `snowflake_conn.py`

Shared connection utilities used by both agents and dashboard.

## Data Models

### RAW.DEPLOY_EVENTS
```sql
event_id VARCHAR PRIMARY KEY
service_name VARCHAR
commit_hash VARCHAR
author VARCHAR
branch VARCHAR
deployed_at TIMESTAMP_NTZ
metadata VARIANT
```

### RAW.METRICS
```sql
metric_id VARCHAR PRIMARY KEY
service_name VARCHAR
metric_name VARCHAR  -- error_rate, latency_p99, cpu_pct, memory_pct
metric_value FLOAT
recorded_at TIMESTAMP_NTZ
```

### AI.DECISIONS
```sql
decision_id VARCHAR PRIMARY KEY
event_id VARCHAR
agent_name VARCHAR  -- Detector, Investigator, Validator
reasoning VARCHAR
output VARIANT
confidence FLOAT
created_at TIMESTAMP_NTZ
```

### AI.ACTIONS
```sql
action_id VARCHAR PRIMARY KEY
event_id VARCHAR
action_type VARCHAR  -- SLACK_ALERT, GITHUB_ISSUE
idempotency_key VARCHAR UNIQUE
payload VARIANT
status VARCHAR  -- PENDING, SENT, SKIPPED_DUPLICATE, FAILED
executed_at TIMESTAMP_NTZ
```

### ANALYTICS.METRIC_DEVIATIONS (Dynamic Table)
```sql
service_name VARCHAR
metric_name VARCHAR
current_value FLOAT
baseline_avg FLOAT
baseline_std FLOAT
z_score FLOAT
severity VARCHAR  -- P1 (z>3), P2 (z>2), P3 (z>1.5)
recorded_at TIMESTAMP_NTZ
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Anomaly detection threshold consistency
*For any* metric with baseline average and standard deviation, when the z-score exceeds 2, the system should classify it as an anomaly with appropriate severity (P1 if z>3, P2 if z>2)
**Validates: Requirements 1.2, 1.3**

### Property 2: Evidence source completeness
*For any* investigation, the system should query all three evidence sources (runbooks, past incidents, live metrics) and include results in the evidence array
**Validates: Requirements 2.1, 2.2, 2.3, 2.4**

### Property 3: Debate termination
*For any* validation loop, the system should terminate after at most 2 rounds regardless of approval status
**Validates: Requirements 3.4**

### Property 4: Idempotency guarantee
*For any* action with the same event_id and action_type, executing it multiple times should result in only one actual execution and subsequent calls should return SKIPPED_DUPLICATE
**Validates: Requirements 4.4, 4.5, 9.1, 9.2, 9.3**

### Property 5: Decision logging completeness
*For any* agent execution, a corresponding record should exist in AI.DECISIONS with agent_name, reasoning, output, and confidence
**Validates: Requirements 5.1**

### Property 6: Action logging completeness
*For any* Composio action execution, a corresponding record should exist in AI.ACTIONS with action_type, payload, and status
**Validates: Requirements 5.2**

### Property 7: Incident history persistence
*For any* resolved incident, a record should exist in AI.INCIDENT_HISTORY with root_cause, fix_applied, and mttr_minutes
**Validates: Requirements 5.3**

### Property 8: Dashboard data freshness
*For any* dashboard query, the data returned should be from Snowflake tables without intermediate caching or API transformation
**Validates: Requirements 6.4**

### Property 9: Simulation idempotency
*For any* simulated incident, running it multiple times should not create duplicate Slack alerts or GitHub issues
**Validates: Requirements 7.5**

### Property 10: Baseline computation window
*For any* metric baseline calculation, the system should use exactly a 1-hour rolling window of historical data
**Validates: Requirements 8.2**

### Property 11: Blast radius traversal depth
*For any* service dependency graph, the system should traverse at most 3 levels deep to prevent infinite loops on circular dependencies
**Validates: Requirements 10.5**

## Error Handling

### Database Connection Failures
- Retry with exponential backoff (3 attempts)
- Log error to stderr
- Return partial results if available
- Do not crash the pipeline

### Cortex API Failures
- Fallback to empty results for search/similarity
- Log warning
- Continue with available evidence
- Mark confidence as reduced

### Composio Action Failures
- Record status as FAILED in AI.ACTIONS
- Include error message in payload
- Do not retry (idempotency prevents duplicates)
- Alert human via fallback mechanism

### Agent Timeout
- Set 60-second timeout per agent
- If exceeded, use partial output
- Log timeout event
- Continue pipeline with degraded results

### Invalid JSON Output
- Attempt to parse with lenient parser
- Extract structured data from text
- Log parsing error
- Use default values for missing fields

## Testing Strategy

### Unit Tests
- Test idempotency key generation (same inputs → same key)
- Test z-score calculation edge cases (zero stddev, negative values)
- Test SQL query parameterization (prevent injection)
- Test Composio payload formatting (valid Block Kit JSON)

### Property-Based Tests
- **Property 1:** Generate random metrics with known z-scores, verify severity classification
- **Property 4:** Generate random event_id and action_type, execute twice, verify only one execution
- **Property 10:** Generate random time windows, verify baseline uses exactly 1 hour
- **Property 11:** Generate random dependency graphs with cycles, verify max depth 3

### Integration Tests
- End-to-end simulation: inject anomaly → verify Slack alert sent → verify GitHub issue created
- Database round-trip: insert event → query → verify data integrity
- Cortex Search: seed runbooks → search → verify top-3 results are relevant

### Testing Framework
- Use `pytest` for unit and integration tests
- Use `hypothesis` for property-based tests (100 iterations per property)
- Configure tests to run against local Snowflake trial account
- Mock Composio API calls in unit tests, use real API in integration tests

**Property Test Configuration:**
```python
from hypothesis import given, strategies as st

@given(
    metric_value=st.floats(min_value=0, max_value=1000),
    baseline_avg=st.floats(min_value=0, max_value=500),
    baseline_std=st.floats(min_value=0.1, max_value=100)
)
def test_anomaly_severity_classification(metric_value, baseline_avg, baseline_std):
    z_score = (metric_value - baseline_avg) / baseline_std
    severity = classify_severity(z_score)
    
    if abs(z_score) > 3:
        assert severity == "P1"
    elif abs(z_score) > 2:
        assert severity == "P2"
    else:
        assert severity == "P3"
```

## Risk Controls

### Determinism
- Set `temperature=0` for all Cortex COMPLETE calls
- Use fixed random seeds for testing
- Hard-limit debate rounds to 2
- Use deterministic idempotency keys (SHA256)

### Performance
- Limit Cortex Search results to top 3
- Cap SQL query results at 20 rows
- Set 60-second timeout per agent
- Use connection pooling for Snowflake

### Security
- Use parameterized SQL queries (prevent injection)
- Validate all user inputs in simulation UI
- Store credentials in .env (never commit)
- Use read-only Snowflake role for dashboard

### Reliability
- Implement idempotency for all external actions
- Log all errors to Snowflake for debugging
- Provide fallback mode when Composio is down
- Gracefully degrade when Cortex APIs fail
