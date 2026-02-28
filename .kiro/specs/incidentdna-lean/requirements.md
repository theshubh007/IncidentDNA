# Requirements Document

## Introduction

IncidentDNA is an autonomous incident response system that detects production anomalies, investigates root causes using multi-agent AI reasoning, and takes automated remediation actions. The system leverages Snowflake Cortex for AI capabilities, CrewAI for agent orchestration, and Composio for external integrations (Slack, GitHub).

## Glossary

- **System**: IncidentDNA autonomous incident response platform
- **Agent**: AI-powered component that performs specific incident response tasks
- **Anomaly**: Statistical deviation in service metrics beyond acceptable thresholds
- **Dynamic Table**: Snowflake table that auto-refreshes based on source data changes
- **Cortex Search**: Snowflake's vector search service for semantic retrieval
- **Idempotency**: Property ensuring duplicate actions are not executed twice
- **MTTR**: Mean Time To Resolution - average time to resolve incidents
- **Blast Radius**: Set of services affected by an incident
- **Debate Loop**: Iterative validation process where agents challenge hypotheses

## Requirements

### Requirement 1

**User Story:** As a DevOps engineer, I want the system to automatically detect metric anomalies after deployments, so that incidents are identified before users report them.

#### Acceptance Criteria

1. WHEN a deployment event is recorded THEN the System SHALL insert the event into RAW.DEPLOY_EVENTS with timestamp and metadata
2. WHEN metrics are ingested THEN the System SHALL compute z-scores against baseline averages and standard deviations
3. WHEN a metric z-score exceeds 2 standard deviations THEN the System SHALL classify it as an anomaly with severity P1, P2, or P3
4. WHEN an anomaly is detected THEN the System SHALL create an entry in AI.ANOMALY_EVENTS with status NEW
5. WHEN multiple metrics deviate simultaneously THEN the System SHALL correlate them into a single incident event

### Requirement 2

**User Story:** As an SRE, I want the system to investigate root causes using historical knowledge, so that I receive evidence-based diagnoses rather than guesses.

#### Acceptance Criteria

1. WHEN investigating an anomaly THEN the System SHALL search runbooks using Cortex Search with semantic similarity
2. WHEN searching past incidents THEN the System SHALL use Snowflake CORTEX.SIMILARITY to find similar historical cases
3. WHEN querying live metrics THEN the System SHALL retrieve current deviation data from ANALYTICS.METRIC_DEVIATIONS
4. WHEN synthesizing evidence THEN the System SHALL combine results from all three sources into a hypothesis
5. WHEN no matching runbook exists THEN the System SHALL reason from first principles using Cortex COMPLETE

### Requirement 3

**User Story:** As a system architect, I want agents to validate hypotheses through adversarial debate, so that incorrect diagnoses are caught before actions are taken.

#### Acceptance Criteria

1. WHEN a root cause hypothesis is proposed THEN the System SHALL validate it against four criteria: alternative causes, evidence quality, fix safety, and simplicity
2. WHEN validation fails THEN the System SHALL return specific objections and adjusted confidence score
3. WHEN validation succeeds THEN the System SHALL approve the hypothesis for action execution
4. WHEN debate exceeds 2 rounds THEN the System SHALL terminate and proceed with best available hypothesis
5. WHEN confidence is below 0.7 THEN the System SHALL flag the incident for human review

### Requirement 4

**User Story:** As an incident responder, I want automated alerts sent to Slack and GitHub, so that the team is notified immediately without manual intervention.

#### Acceptance Criteria

1. WHEN an incident is validated THEN the System SHALL post a formatted alert to Slack with severity, service, and root cause
2. WHEN posting to Slack THEN the System SHALL use Block Kit formatting with color-coded severity indicators
3. WHEN creating a GitHub issue THEN the System SHALL include event ID, root cause, evidence sources, and resolution checklist
4. WHEN executing any action THEN the System SHALL check AI.ACTIONS for duplicate idempotency keys
5. WHEN a duplicate action is detected THEN the System SHALL skip execution and return SKIPPED_DUPLICATE status

### Requirement 5

**User Story:** As a platform engineer, I want all agent decisions logged to Snowflake, so that I can audit reasoning and improve the system over time.

#### Acceptance Criteria

1. WHEN an agent completes a task THEN the System SHALL insert a record into AI.DECISIONS with agent name, reasoning, output, and confidence
2. WHEN an action is executed THEN the System SHALL insert a record into AI.ACTIONS with action type, payload, and status
3. WHEN an incident is resolved THEN the System SHALL insert a record into AI.INCIDENT_HISTORY with root cause, fix applied, and MTTR
4. WHEN writing to Snowflake THEN the System SHALL use parameterized queries to prevent SQL injection
5. WHEN a database write fails THEN the System SHALL log the error and continue processing

### Requirement 6

**User Story:** As a team lead, I want a dashboard showing live incidents and agent reasoning, so that I can monitor system behavior and intervene when needed.

#### Acceptance Criteria

1. WHEN the dashboard loads THEN the System SHALL display active anomalies from AI.ANOMALY_EVENTS ordered by severity
2. WHEN viewing reasoning trace THEN the System SHALL show step-by-step agent decisions from AI.DECISIONS
3. WHEN viewing actions log THEN the System SHALL display Slack and GitHub actions with timestamps and status
4. WHEN refreshing data THEN the System SHALL query Snowflake directly without intermediate API layer
5. WHEN no incidents exist THEN the System SHALL display a success message indicating system health

### Requirement 7

**User Story:** As a developer, I want to simulate incidents for testing, so that I can verify the system works before real incidents occur.

#### Acceptance Criteria

1. WHEN the simulate button is clicked THEN the System SHALL inject a synthetic anomaly event with configurable service and severity
2. WHEN simulation starts THEN the System SHALL trigger the full agent pipeline synchronously
3. WHEN simulation completes THEN the System SHALL display the complete result including detection, investigation, validation, and actions
4. WHEN simulation fails THEN the System SHALL display error details and partial results
5. WHEN multiple simulations run THEN the System SHALL prevent duplicate actions via idempotency layer

### Requirement 8

**User Story:** As a data engineer, I want metric baselines computed automatically, so that anomaly detection adapts to changing traffic patterns.

#### Acceptance Criteria

1. WHEN metrics are ingested THEN the System SHALL update ANALYTICS.METRIC_BASELINES with rolling averages and standard deviations
2. WHEN computing baselines THEN the System SHALL use a 1-hour rolling window
3. WHEN a new service is added THEN the System SHALL initialize baseline with first 10 metric samples
4. WHEN baseline data is stale THEN the System SHALL mark it with last_updated timestamp
5. WHEN querying deviations THEN the System SHALL join metrics with baselines on service_name and metric_name

### Requirement 9

**User Story:** As a security engineer, I want all external actions to be idempotent, so that system retries do not cause duplicate alerts or issues.

#### Acceptance Criteria

1. WHEN generating an idempotency key THEN the System SHALL use SHA256 hash of action_type and event_id
2. WHEN checking for duplicates THEN the System SHALL query AI.ACTIONS for matching idempotency_key
3. WHEN a duplicate is found THEN the System SHALL return the previous status without re-executing
4. WHEN recording an action THEN the System SHALL insert with status PENDING before execution
5. WHEN execution completes THEN the System SHALL update status to SENT or FAILED

### Requirement 10

**User Story:** As an operations manager, I want the system to identify blast radius, so that I understand which downstream services are affected.

#### Acceptance Criteria

1. WHEN detecting an anomaly THEN the System SHALL query RAW.SERVICE_DEPENDENCIES for dependent services
2. WHEN computing blast radius THEN the System SHALL traverse the dependency graph recursively
3. WHEN multiple services are affected THEN the System SHALL list all impacted services in the detection output
4. WHEN no dependencies exist THEN the System SHALL return an empty blast radius list
5. WHEN a circular dependency is detected THEN the System SHALL limit traversal depth to 3 levels
