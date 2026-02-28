# Implementation Plan

- [ ] 1. Set up Snowflake foundation
  - Create all schemas (RAW, AI, ANALYTICS) and tables
  - Seed 5 runbooks, 10 past incidents, metrics, and baselines
  - Create dynamic table for ANALYTICS.METRIC_DEVIATIONS
  - Create Cortex Search service RAW.RUNBOOK_SEARCH
  - Verify anomaly detection: `SELECT * FROM ANALYTICS.METRIC_DEVIATIONS LIMIT 5;`
  - _Requirements: 1.1, 1.2, 8.1, 8.2_

- [ ]* 1.1 Write property test for anomaly severity classification
  - **Property 1: Anomaly detection threshold consistency**
  - **Validates: Requirements 1.2, 1.3**

- [ ] 2. Create shared utilities
  - Implement `utils/snowflake_conn.py` with get_connection(), run_query(), run_dml()
  - Add connection pooling and error handling
  - Test connection with sample query
  - _Requirements: 5.4_

- [ ] 3. Build agent tools
  - [ ] 3.1 Implement `tools/search_runbooks.py` using Cortex Search
    - Wrap SNOWFLAKE.CORTEX.SEARCH_PREVIEW
    - Return top 3 results
    - _Requirements: 2.1_

  - [ ] 3.2 Implement `tools/find_similar_incidents.py` using CORTEX.SIMILARITY
    - Query RAW.PAST_INCIDENTS with similarity scoring
    - Return top 3 matches
    - _Requirements: 2.2_

  - [ ] 3.3 Implement `tools/query_snowflake.py` for generic SELECT queries
    - Validate query starts with SELECT
    - Cap results at 20 rows
    - _Requirements: 2.3_

  - [ ] 3.4 Implement `tools/ai_complete_tool.py` using CORTEX.COMPLETE
    - Use Llama 3.1-70B model
    - Set temperature=0 for determinism
    - _Requirements: 2.5_

  - [ ] 3.5 Implement `tools/idempotency.py` with safe_execute()
    - Generate SHA256 idempotency keys
    - Check AI.ACTIONS for duplicates
    - Record PENDING before execution
    - _Requirements: 4.4, 4.5, 9.1, 9.2, 9.3, 9.4, 9.5_

  - [ ]* 3.6 Write property test for idempotency
    - **Property 4: Idempotency guarantee**
    - **Validates: Requirements 4.4, 4.5, 9.1, 9.2, 9.3**

  - [ ] 3.7 Implement `tools/composio_actions.py` for Slack and GitHub
    - Create PostSlackAlertTool with Block Kit formatting
    - Create CreateGitHubIssueTool with markdown template
    - Wrap both with safe_execute() for idempotency
    - _Requirements: 4.1, 4.2, 4.3_

- [ ] 4. Build Agent 1: Detector
  - Implement `agents/ag1_detector.py` with severity classification logic
  - Add tools: query_snowflake, ai_complete
  - Define DETECTOR_TASK_TEMPLATE with clear instructions
  - Query RAW.SERVICE_DEPENDENCIES for blast radius
  - Output JSON: severity, blast_radius, classification
  - _Requirements: 1.3, 10.1, 10.2, 10.3_

- [ ]* 4.1 Write property test for blast radius traversal depth
  - **Property 11: Blast radius traversal depth**
  - **Validates: Requirements 10.5**

- [ ] 5. Build Agent 2: Investigator
  - Implement `agents/ag2_investigator.py` with 3-source evidence chain
  - Add tools: search_runbooks, find_similar_incidents, query_snowflake, ai_complete
  - Define INVESTIGATOR_TASK_TEMPLATE requiring all 3 sources
  - Synthesize hypothesis from runbooks + past incidents + live metrics
  - Output JSON: root_cause, confidence, evidence
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

- [ ]* 5.1 Write property test for evidence source completeness
  - **Property 2: Evidence source completeness**
  - **Validates: Requirements 2.1, 2.2, 2.3, 2.4**

- [ ] 6. Build Agent 5: Validator
  - Implement `agents/ag5_validator.py` with adversarial validation
  - Add tools: query_snowflake, ai_complete
  - Define VALIDATOR_TASK_TEMPLATE with 4 stress tests
  - Apply checks: alternative causes, evidence quality, fix safety, simplicity
  - Output JSON: decision (APPROVE/DEBATE), objections, adjusted_confidence
  - _Requirements: 3.1, 3.2, 3.3, 3.5_

- [ ] 7. Build Manager orchestration
  - Implement `agents/manager.py` with run_pipeline() function
  - Phase 1: Run Detector agent
  - Phase 2: Run Investigator agent
  - Phase 3: Run Validator agent with max 2 debate rounds
  - Phase 4: Execute Composio actions (Slack + GitHub)
  - Phase 5: Log all decisions to AI.DECISIONS
  - Phase 6: Log actions to AI.ACTIONS
  - Phase 7: Log resolved incident to AI.INCIDENT_HISTORY
  - _Requirements: 3.4, 4.1, 4.2, 4.3, 5.1, 5.2, 5.3_

- [ ]* 7.1 Write property test for debate termination
  - **Property 3: Debate termination**
  - **Validates: Requirements 3.4**

- [ ]* 7.2 Write property test for decision logging completeness
  - **Property 5: Decision logging completeness**
  - **Validates: Requirements 5.1**

- [ ]* 7.3 Write property test for action logging completeness
  - **Property 6: Action logging completeness**
  - **Validates: Requirements 5.2**

- [ ]* 7.4 Write property test for incident history persistence
  - **Property 7: Incident history persistence**
  - **Validates: Requirements 5.3**

- [ ] 8. Build ingestion trigger listener
  - Implement `ingestion/trigger_listener.py` with Composio webhook handlers
  - Handle GitHub commit events
  - Insert deploy event into RAW.DEPLOY_EVENTS
  - Inject synthetic metric spike into RAW.METRICS
  - Query ANALYTICS.METRIC_DEVIATIONS for anomalies
  - If anomaly detected, call agents.manager.run_pipeline() directly
  - _Requirements: 1.1, 1.4, 7.2_

- [ ] 9. Build Streamlit dashboard
  - [ ] 9.1 Create `dashboard/app.py` with navigation
    - Set up page routing for 3 pages
    - Add sidebar with IncidentDNA branding
    - _Requirements: 6.1_

  - [ ] 9.2 Create Live Console page
    - Query AI.ANOMALY_EVENTS for active anomalies
    - Display table with service, anomaly_type, severity, detected_at, status
    - Add severity breakdown pie chart
    - Add refresh button
    - _Requirements: 6.1, 6.5_

  - [ ] 9.3 Create Reasoning Trace page
    - Query AI.DECISIONS for agent reasoning
    - Display step-by-step agent decisions
    - Show agent name, reasoning, output, confidence
    - Group by event_id
    - _Requirements: 6.2_

  - [ ] 9.4 Create Actions Log page
    - Query AI.ACTIONS for Slack and GitHub actions
    - Display action_type, status, executed_at, payload
    - Color-code by status (SENT=green, FAILED=red, SKIPPED_DUPLICATE=yellow)
    - _Requirements: 6.3_

  - [ ]* 9.5 Write property test for dashboard data freshness
    - **Property 8: Dashboard data freshness**
    - **Validates: Requirements 6.4**

- [ ] 10. Add simulation capability
  - Add simulate button to dashboard
  - Create form: service, anomaly_type, severity
  - On submit, inject synthetic event and call run_pipeline()
  - Display full result: detection, investigation, validation, actions
  - Show debate rounds and final confidence
  - _Requirements: 7.1, 7.2, 7.3, 7.4_

- [ ]* 10.1 Write property test for simulation idempotency
  - **Property 9: Simulation idempotency**
  - **Validates: Requirements 7.5**

- [ ] 11. Create requirements.txt and .env.example
  - Pin all dependencies: crewai, snowflake-connector-python, composio-crewai, streamlit, plotly
  - Create .env.example with Snowflake credentials, Composio API key, GitHub repo, Slack channel
  - _Requirements: All_

- [ ] 12. Checkpoint - Ensure all tests pass
  - Run all unit tests
  - Run all property-based tests (100 iterations each)
  - Verify Snowflake connection
  - Verify Cortex Search returns results
  - Verify idempotency prevents duplicates
  - Ask user if questions arise

- [ ] 13. End-to-end integration test
  - Start trigger_listener.py
  - Push test commit to GitHub
  - Verify deploy event inserted
  - Verify metric spike injected
  - Verify anomaly detected
  - Verify agents run (Detector → Investigator → Validator)
  - Verify Slack alert sent
  - Verify GitHub issue created
  - Verify all logs in Snowflake (AI.DECISIONS, AI.ACTIONS, AI.INCIDENT_HISTORY)
  - Verify dashboard displays results
  - _Requirements: All_

- [ ] 14. Final polish and demo prep
  - Add error handling for all external API calls
  - Add loading spinners in Streamlit
  - Add success/error messages
  - Test with 3 different anomaly types
  - Prepare demo script
  - Create backup simulation scenarios
  - _Requirements: All_
