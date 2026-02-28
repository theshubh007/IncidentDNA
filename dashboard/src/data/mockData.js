// ═══════════════════════════════════════════════════════════════
// ReleaseShield — Mock Data Layer
// Deterministic demo data for all pages
// ═══════════════════════════════════════════════════════════════

export const SERVICES = [
    { id: 'payment-service', name: 'payment-service', status: 'healthy', uptime: 99.97, latency: 42, errorRate: 0.02, dependencies: ['db-primary', 'redis-cluster', 'stripe-api'] },
    { id: 'api-gateway', name: 'api-gateway', status: 'healthy', uptime: 99.99, latency: 12, errorRate: 0.01, dependencies: ['payment-service', 'user-service', 'notification-service'] },
    { id: 'user-service', name: 'user-service', status: 'healthy', uptime: 99.95, latency: 38, errorRate: 0.03, dependencies: ['db-primary', 'redis-cluster'] },
    { id: 'notification-service', name: 'notification-service', status: 'healthy', uptime: 99.92, latency: 85, errorRate: 0.04, dependencies: ['redis-cluster', 'sns-queue'] },
    { id: 'order-service', name: 'order-service', status: 'healthy', uptime: 99.88, latency: 67, errorRate: 0.05, dependencies: ['payment-service', 'db-primary', 'inventory-service'] },
    { id: 'inventory-service', name: 'inventory-service', status: 'healthy', uptime: 99.91, latency: 55, errorRate: 0.03, dependencies: ['db-replica', 'redis-cluster'] },
];

export const INCIDENTS_DATA = [
    {
        id: 'INC-001', severity: 'critical', service: 'payment-service', detected: '2026-02-27T14:23:00Z', status: 'resolved',
        confidence: 0.94, blastRadius: ['order-service', 'api-gateway'], actionsFired: 3,
        rootCause: 'DB connection pool exhaustion after deploy sha-a1b2c3d4. Pool limit 50 saturated under 2x normal load.',
        timeline: [
            { time: '14:23:00', agent: 'Ag1-Detector', action: 'Anomaly detected: error_rate 0.22 (z=4.8)', status: 'complete' },
            { time: '14:23:12', agent: 'Ag1-Detector', action: 'Blast radius: order-service, api-gateway at risk (ETA 12m)', status: 'complete' },
            { time: '14:23:18', agent: 'Ag2-Investigator', action: 'Runbook match: "DB Pool Tuning Guide" (relevance: 0.91)', status: 'complete' },
            { time: '14:23:25', agent: 'Ag2-Investigator', action: 'Similar incident INC-012 found (92% match) — fix: increase pool to 100', status: 'complete' },
            { time: '14:23:32', agent: 'Ag5-Validator', action: 'Hypothesis APPROVED — 2/2 alternatives eliminated', status: 'complete' },
            { time: '14:23:38', agent: 'Ag3-FixAdvisor', action: 'Fix: increase pool 50→100 (8-12m recovery, medium risk)', status: 'complete' },
            { time: '14:23:42', agent: 'Ag4-Action', action: 'Slack alert sent to #incident-alerts', status: 'complete' },
            { time: '14:23:44', agent: 'Ag4-Action', action: 'GitHub issue GH-347 created', status: 'complete' },
            { time: '14:35:00', agent: 'System', action: 'Metrics normalized — incident resolved', status: 'complete' },
        ],
        blastRadiusDetail: {
            primary: 'payment-service',
            affected: [
                { service: 'order-service', impact: 'high', eta: '12m', reason: 'Direct dependency on payment-service' },
                { service: 'api-gateway', impact: 'medium', eta: '15m', reason: 'Routes 40% traffic through payment-service' },
            ]
        },
        patternMemory: [
            { id: 'INC-012', similarity: 0.92, service: 'payment-service', cause: 'DB pool exhaustion during peak', fix: 'Increased pool_max from 50 to 100', date: '2026-01-15' },
            { id: 'INC-008', similarity: 0.87, service: 'order-service', cause: 'Connection timeout cascade', fix: 'Added circuit breaker with 5s timeout', date: '2026-01-02' },
            { id: 'INC-003', similarity: 0.71, service: 'user-service', cause: 'Redis connection leak', fix: 'Patched connection pool cleanup', date: '2025-12-18' },
        ],
        actions: [
            { type: 'slack', target: '#incident-alerts', status: 'sent', timestamp: '14:23:42', receipt: 'msg-ts-1709045022.001' },
            { type: 'github', target: 'GH-347', status: 'created', timestamp: '14:23:44', receipt: 'https://github.com/org/repo/issues/347' },
            { type: 'dna_store', target: 'AI.INCIDENT_HISTORY', status: 'stored', timestamp: '14:35:02', receipt: 'row-id-a1b2c3' },
        ],
        postmortem: {
            summary: 'Payment service experienced DB connection pool exhaustion following deploy sha-a1b2c3d4, causing cascading failures to order-service and api-gateway.',
            customerImpact: '~2,400 transactions failed over 12 minutes. Estimated revenue impact: $18,200.',
            rootCause: 'Deploy introduced a new query pattern that held connections 3x longer than baseline. Pool limit of 50 was insufficient under 2x normal load.',
            actionItems: [
                { text: 'Increase DB pool_max from 50 to 100 in production config', done: true },
                { text: 'Add connection pool utilization alert at 80% threshold', done: false },
                { text: 'Implement query timeout of 5s for non-critical paths', done: false },
                { text: 'Add pre-deploy connection pool load test to CI pipeline', done: false },
            ]
        }
    },
    {
        id: 'INC-002', severity: 'warning', service: 'api-gateway', detected: '2026-02-27T10:15:00Z', status: 'investigating',
        confidence: 0.78, blastRadius: ['user-service'], actionsFired: 2,
        rootCause: 'Latency regression after rate limiter config change. P99 latency increased from 12ms to 340ms.',
        timeline: [
            { time: '10:15:00', agent: 'Ag1-Detector', action: 'Anomaly detected: latency_p99 340ms (z=3.2)', status: 'complete' },
            { time: '10:15:14', agent: 'Ag2-Investigator', action: 'Deploy context: rate limiter config updated in sha-f4e5d6c7', status: 'complete' },
            { time: '10:15:22', agent: 'Ag5-Validator', action: 'Hypothesis CONDITIONALLY APPROVED — 2 viable hypotheses', status: 'in-progress' },
        ],
        blastRadiusDetail: {
            primary: 'api-gateway',
            affected: [
                { service: 'user-service', impact: 'medium', eta: '20m', reason: 'Downstream of api-gateway routing' },
            ]
        },
        patternMemory: [
            { id: 'INC-009', similarity: 0.85, service: 'api-gateway', cause: 'Rate limiter misconfiguration', fix: 'Reverted rate limit to 1000 req/s', date: '2026-01-10' },
        ],
        actions: [
            { type: 'slack', target: '#incident-alerts', status: 'sent', timestamp: '10:15:28', receipt: 'msg-ts-1709030128.002' },
            { type: 'github', target: 'GH-348', status: 'created', timestamp: '10:15:30', receipt: 'https://github.com/org/repo/issues/348' },
        ],
        postmortem: null,
    },
    {
        id: 'INC-003', severity: 'critical', service: 'order-service', detected: '2026-02-26T22:45:00Z', status: 'resolved',
        confidence: 0.91, blastRadius: ['payment-service', 'inventory-service'], actionsFired: 3,
        rootCause: 'Memory leak in order processing worker. Heap usage grew from 512MB to 3.2GB over 4 hours.',
        timeline: [
            { time: '22:45:00', agent: 'Ag1-Detector', action: 'Anomaly detected: memory_usage 3.2GB (z=5.1)', status: 'complete' },
            { time: '22:45:18', agent: 'Ag2-Investigator', action: 'Pattern: gradual memory climb — likely memory leak', status: 'complete' },
            { time: '22:45:30', agent: 'Ag5-Validator', action: 'Hypothesis APPROVED after Round 2', status: 'complete' },
            { time: '22:45:38', agent: 'Ag4-Action', action: 'Slack alert sent, GitHub issue GH-345 created', status: 'complete' },
            { time: '22:58:00', agent: 'System', action: 'Worker pods restarted — metrics normalized', status: 'complete' },
        ],
        blastRadiusDetail: {
            primary: 'order-service',
            affected: [
                { service: 'payment-service', impact: 'high', eta: '8m', reason: 'Orders queue payment requests' },
                { service: 'inventory-service', impact: 'medium', eta: '15m', reason: 'Stock reservation depends on order processing' },
            ]
        },
        patternMemory: [
            { id: 'INC-005', similarity: 0.88, service: 'order-service', cause: 'Event listener leak', fix: 'Added cleanup in disconnect handler', date: '2025-12-28' },
        ],
        actions: [
            { type: 'slack', target: '#incident-alerts', status: 'sent', timestamp: '22:45:40', receipt: 'msg-ts-1709001940.003' },
            { type: 'github', target: 'GH-345', status: 'created', timestamp: '22:45:42', receipt: 'https://github.com/org/repo/issues/345' },
            { type: 'dna_store', target: 'AI.INCIDENT_HISTORY', status: 'stored', timestamp: '22:58:05', receipt: 'row-id-d4e5f6' },
        ],
        postmortem: {
            summary: 'Order service memory leak caused by event listener accumulation in order processing worker.',
            customerImpact: '~800 orders delayed by 13 minutes. No data loss.',
            rootCause: 'Event listeners were not properly cleaned up on WebSocket disconnect, causing heap growth from 512MB to 3.2GB over 4 hours.',
            actionItems: [
                { text: 'Add cleanup logic in WebSocket disconnect handler', done: true },
                { text: 'Set memory limit alerts at 2GB threshold', done: true },
                { text: 'Implement graceful restart on memory pressure', done: false },
            ]
        }
    },
    {
        id: 'INC-004', severity: 'info', service: 'notification-service', detected: '2026-02-26T08:30:00Z', status: 'resolved',
        confidence: 0.96, blastRadius: [], actionsFired: 1,
        rootCause: 'Scheduled job causing periodic latency spike. Expected behavior — no action required.',
        timeline: [
            { time: '08:30:00', agent: 'Ag1-Detector', action: 'Anomaly detected: latency spike (periodic pattern)', status: 'complete' },
            { time: '08:30:15', agent: 'Ag2-Investigator', action: 'Temporal pattern: same time daily — scheduled job', status: 'complete' },
            { time: '08:30:20', agent: 'Ag5-Validator', action: 'APPROVED — periodic anomaly, not deploy-related', status: 'complete' },
        ],
        blastRadiusDetail: { primary: 'notification-service', affected: [] },
        patternMemory: [],
        actions: [
            { type: 'slack', target: '#incident-alerts', status: 'sent', timestamp: '08:30:22', receipt: 'msg-ts-1708950622.004' },
        ],
        postmortem: null,
    },
    {
        id: 'INC-005', severity: 'warning', service: 'inventory-service', detected: '2026-02-25T16:10:00Z', status: 'resolved',
        confidence: 0.83, blastRadius: ['order-service'], actionsFired: 2,
        rootCause: 'Cache cold start after Redis cluster failover. Read latency spiked from 5ms to 450ms.',
        timeline: [
            { time: '16:10:00', agent: 'Ag1-Detector', action: 'Anomaly: read_latency 450ms (z=3.8)', status: 'complete' },
            { time: '16:10:20', agent: 'Ag2-Investigator', action: 'Redis cluster failover detected at 16:08', status: 'complete' },
            { time: '16:10:35', agent: 'Ag5-Validator', action: 'Hypothesis APPROVED', status: 'complete' },
            { time: '16:22:00', agent: 'System', action: 'Cache warmed — latency normalized', status: 'complete' },
        ],
        blastRadiusDetail: {
            primary: 'inventory-service',
            affected: [
                { service: 'order-service', impact: 'low', eta: '20m', reason: 'Inventory lookups slower but functional' },
            ]
        },
        patternMemory: [
            { id: 'INC-011', similarity: 0.79, service: 'user-service', cause: 'Redis failover cold start', fix: 'Pre-warm cache script on failover', date: '2026-01-12' },
        ],
        actions: [
            { type: 'slack', target: '#incident-alerts', status: 'sent', timestamp: '16:10:38', receipt: 'msg-ts-1708881038.005' },
            { type: 'github', target: 'GH-342', status: 'created', timestamp: '16:10:40', receipt: 'https://github.com/org/repo/issues/342' },
        ],
        postmortem: {
            summary: 'Inventory service experienced cache cold start following Redis cluster failover.',
            customerImpact: 'Product pages loaded 3-5s slower for ~12 minutes. No failed requests.',
            rootCause: 'Automatic Redis failover cleared hot cache. No pre-warming mechanism existed.',
            actionItems: [
                { text: 'Implement cache pre-warming script triggered on failover', done: true },
                { text: 'Add Redis cluster health to service dashboard', done: false },
            ]
        }
    },
];

export const RELEASES_DATA = [
    {
        id: 'REL-042', service: 'payment-service', version: 'v2.14.0', confidence: 34, risk: 'high',
        author: 'sarah.chen', timestamp: '2026-02-27T15:30:00Z', status: 'pending',
        riskFactors: ['Friday deploy', 'Touches DB schema', 'High churn area (12 files)', 'No load test in CI'],
        guardrails: [
            { text: 'Run connection pool load test', checked: false },
            { text: 'Verify rollback script exists', checked: true },
            { text: 'Stage canary at 5% traffic', checked: false },
            { text: 'Confirm on-call engineer available', checked: true },
        ],
        evidence: ['3 similar deploys caused incidents in past 30 days', 'DB migration alters payments table index'],
    },
    {
        id: 'REL-041', service: 'api-gateway', version: 'v3.8.2', confidence: 82, risk: 'low',
        author: 'mike.johnson', timestamp: '2026-02-27T11:00:00Z', status: 'deployed',
        riskFactors: ['Config-only change'],
        guardrails: [
            { text: 'Verify config syntax', checked: true },
            { text: 'Test in staging', checked: true },
        ],
        evidence: ['Config changes have 98% safe deploy rate'],
    },
    {
        id: 'REL-040', service: 'order-service', version: 'v1.22.0', confidence: 58, risk: 'medium',
        author: 'alex.wong', timestamp: '2026-02-26T09:00:00Z', status: 'deployed',
        riskFactors: ['Touches order processing logic', 'New dependency added'],
        guardrails: [
            { text: 'Integration test suite passes', checked: true },
            { text: 'Canary deployment at 10%', checked: true },
            { text: 'Monitor error rate for 30min post-deploy', checked: false },
        ],
        evidence: ['Similar change pattern to INC-003 root cause'],
    },
    {
        id: 'REL-039', service: 'notification-service', version: 'v2.5.1', confidence: 91, risk: 'low',
        author: 'lisa.park', timestamp: '2026-02-25T14:00:00Z', status: 'deployed',
        riskFactors: [],
        guardrails: [
            { text: 'Unit tests pass', checked: true },
        ],
        evidence: ['Patch release — bug fix only, no new features'],
    },
];

export const AUDIT_LOG_DATA = [
    { actionId: 'ACT-001', decisionId: 'DEC-001', toolkit: 'composio-slack', actionType: 'SLACK_POST_MESSAGE', status: 'sent', retryCount: 0, idempotencyKey: 'INC-001:slack:alert', timestamp: '2026-02-27T14:23:42Z', request: { channel: '#incident-alerts', text: '[P1] payment-service: DB pool exhaustion...' }, response: { ok: true, ts: '1709045022.001' } },
    { actionId: 'ACT-002', decisionId: 'DEC-001', toolkit: 'composio-github', actionType: 'GITHUB_CREATE_ISSUE', status: 'created', retryCount: 0, idempotencyKey: 'INC-001:github:issue', timestamp: '2026-02-27T14:23:44Z', request: { repo: 'org/incidents', title: '[INC-001] payment-service — DB pool exhaustion' }, response: { number: 347, html_url: 'https://github.com/org/repo/issues/347' } },
    { actionId: 'ACT-003', decisionId: 'DEC-001', toolkit: 'snowflake', actionType: 'STORE_DNA', status: 'stored', retryCount: 0, idempotencyKey: 'INC-001:dna:store', timestamp: '2026-02-27T14:35:02Z', request: { table: 'AI.INCIDENT_HISTORY', incident_id: 'INC-001' }, response: { rows_inserted: 1 } },
    { actionId: 'ACT-004', decisionId: 'DEC-002', toolkit: 'composio-slack', actionType: 'SLACK_POST_MESSAGE', status: 'sent', retryCount: 0, idempotencyKey: 'INC-002:slack:alert', timestamp: '2026-02-27T10:15:28Z', request: { channel: '#incident-alerts', text: '[P2] api-gateway: latency regression...' }, response: { ok: true, ts: '1709030128.002' } },
    { actionId: 'ACT-005', decisionId: 'DEC-002', toolkit: 'composio-github', actionType: 'GITHUB_CREATE_ISSUE', status: 'created', retryCount: 0, idempotencyKey: 'INC-002:github:issue', timestamp: '2026-02-27T10:15:30Z', request: { repo: 'org/incidents', title: '[INC-002] api-gateway — latency regression' }, response: { number: 348, html_url: 'https://github.com/org/repo/issues/348' } },
    { actionId: 'ACT-006', decisionId: 'DEC-002', toolkit: 'composio-slack', actionType: 'SLACK_POST_MESSAGE', status: 'skipped_duplicate', retryCount: 0, idempotencyKey: 'INC-002:slack:alert', timestamp: '2026-02-27T10:15:35Z', request: { channel: '#incident-alerts' }, response: { skipped: true, reason: 'duplicate' } },
    { actionId: 'ACT-007', decisionId: 'DEC-003', toolkit: 'composio-slack', actionType: 'SLACK_POST_MESSAGE', status: 'sent', retryCount: 1, idempotencyKey: 'INC-003:slack:alert', timestamp: '2026-02-26T22:45:40Z', request: { channel: '#incident-alerts', text: '[P1] order-service: memory leak...' }, response: { ok: true, ts: '1709001940.003' } },
    { actionId: 'ACT-008', decisionId: 'DEC-003', toolkit: 'composio-github', actionType: 'GITHUB_CREATE_ISSUE', status: 'failed', retryCount: 3, idempotencyKey: 'INC-003:github:issue:attempt1', timestamp: '2026-02-26T22:45:42Z', request: { repo: 'org/incidents', title: '[INC-003] order-service — memory leak' }, response: { error: 'rate_limited', retry_after: 60 } },
    { actionId: 'ACT-009', decisionId: 'DEC-003', toolkit: 'composio-github', actionType: 'GITHUB_CREATE_ISSUE', status: 'created', retryCount: 0, idempotencyKey: 'INC-003:github:issue', timestamp: '2026-02-26T22:46:44Z', request: { repo: 'org/incidents', title: '[INC-003] order-service — memory leak' }, response: { number: 345, html_url: 'https://github.com/org/repo/issues/345' } },
    { actionId: 'ACT-010', decisionId: 'DEC-003', toolkit: 'snowflake', actionType: 'STORE_DNA', status: 'stored', retryCount: 0, idempotencyKey: 'INC-003:dna:store', timestamp: '2026-02-26T22:58:05Z', request: { table: 'AI.INCIDENT_HISTORY', incident_id: 'INC-003' }, response: { rows_inserted: 1 } },
];

export const METRICS_OVERVIEW = {
    activeIncidents: 1,
    deployConfidence: 72,
    errorRate: 0.04,
    latencyP99: 89,
    mttrAvg: 11.2,
    mttrIndustry: 47,
    totalIncidents24h: 3,
    actionsExecuted: 10,
    deduplicatedActions: 1,
};

export const STEPPER_STATES = [
    { id: 'detect', label: 'Detect', status: 'complete', timestamp: '14:23:00', detail: 'error_rate anomaly detected (z=4.8)', evidence: 'ANALYTICS.METRIC_DEVIATIONS' },
    { id: 'classify', label: 'Classify', status: 'complete', timestamp: '14:23:12', detail: 'Severity: P1 — blast radius: 2 services', evidence: 'AI_CLASSIFY output' },
    { id: 'blast-radius', label: 'Blast Radius', status: 'complete', timestamp: '14:23:12', detail: 'order-service at risk (ETA 12m), api-gateway (ETA 15m)', evidence: 'SERVICE_DEPENDENCIES graph' },
    { id: 'investigate', label: 'Investigate', status: 'complete', timestamp: '14:23:25', detail: '3-source evidence: runbook (0.91) + past incident INC-012 (92%) + deploy context', evidence: 'Cortex Search + AI_SIMILARITY' },
    { id: 'validate', label: 'Validate', status: 'complete', timestamp: '14:23:32', detail: 'Hypothesis APPROVED — 2 alternatives eliminated by Ag5', evidence: 'Debate log' },
    { id: 'action', label: 'Action', status: 'complete', timestamp: '14:23:44', detail: 'Slack alert sent + GitHub issue GH-347 created', evidence: 'Composio receipts' },
    { id: 'postmortem', label: 'Postmortem', status: 'complete', timestamp: '14:35:02', detail: 'Auto-drafted: DB pool exhaustion, 4 action items', evidence: 'AI.INCIDENT_HISTORY' },
];

export const DEPENDENCY_GRAPH = {
    nodes: [
        { id: 'api-gateway', x: 250, y: 40, status: 'healthy' },
        { id: 'payment-service', x: 120, y: 140, status: 'critical' },
        { id: 'user-service', x: 380, y: 140, status: 'healthy' },
        { id: 'order-service', x: 60, y: 240, status: 'warning' },
        { id: 'notification-service', x: 320, y: 240, status: 'healthy' },
        { id: 'inventory-service', x: 190, y: 240, status: 'healthy' },
        { id: 'db-primary', x: 120, y: 340, status: 'healthy' },
        { id: 'redis-cluster', x: 300, y: 340, status: 'healthy' },
    ],
    edges: [
        { from: 'api-gateway', to: 'payment-service' },
        { from: 'api-gateway', to: 'user-service' },
        { from: 'api-gateway', to: 'notification-service' },
        { from: 'payment-service', to: 'db-primary' },
        { from: 'payment-service', to: 'redis-cluster' },
        { from: 'order-service', to: 'payment-service' },
        { from: 'order-service', to: 'inventory-service' },
        { from: 'order-service', to: 'db-primary' },
        { from: 'user-service', to: 'db-primary' },
        { from: 'user-service', to: 'redis-cluster' },
        { from: 'notification-service', to: 'redis-cluster' },
        { from: 'inventory-service', to: 'redis-cluster' },
    ],
};

export const SIMULATION_SCENARIOS = [
    {
        id: 'payment-error-spike',
        label: 'Payment Error Spike',
        description: 'Simulates a post-deploy error rate spike on payment-service (error_rate: 0.02 → 0.22)',
        service: 'payment-service',
        anomalyType: 'post_deploy_error_rate',
        severity: 'P1',
    },
    {
        id: 'latency-regression',
        label: 'Latency Regression',
        description: 'Simulates a P99 latency regression on api-gateway (12ms → 340ms)',
        service: 'api-gateway',
        anomalyType: 'latency_regression',
        severity: 'P2',
    },
    {
        id: 'db-pool-exhaustion',
        label: 'DB Pool Exhaustion',
        description: 'Simulates DB connection pool saturation on order-service',
        service: 'order-service',
        anomalyType: 'db_pool_exhaustion',
        severity: 'P1',
    },
];

// Sparkline data generators
export function generateSparkline(length = 24, base = 50, variance = 10, spike = null) {
    const data = [];
    for (let i = 0; i < length; i++) {
        let value = base + (Math.random() * variance * 2 - variance);
        if (spike && i === spike.index) value = spike.value;
        data.push(Math.max(0, Math.round(value * 100) / 100));
    }
    return data;
}

export const SERVICE_SPARKLINES = {
    'payment-service': { latency: generateSparkline(24, 42, 8, { index: 20, value: 320 }), errorRate: generateSparkline(24, 0.02, 0.01, { index: 20, value: 0.22 }) },
    'api-gateway': { latency: generateSparkline(24, 12, 3, { index: 18, value: 340 }), errorRate: generateSparkline(24, 0.01, 0.005) },
    'user-service': { latency: generateSparkline(24, 38, 6), errorRate: generateSparkline(24, 0.03, 0.01) },
    'notification-service': { latency: generateSparkline(24, 85, 15), errorRate: generateSparkline(24, 0.04, 0.02) },
    'order-service': { latency: generateSparkline(24, 67, 12, { index: 22, value: 280 }), errorRate: generateSparkline(24, 0.05, 0.02) },
    'inventory-service': { latency: generateSparkline(24, 55, 10), errorRate: generateSparkline(24, 0.03, 0.01) },
};

export const POSTMORTEMS_DATA = INCIDENTS_DATA.filter(i => i.postmortem !== null).map(i => ({
    incidentId: i.id,
    service: i.service,
    severity: i.severity,
    status: 'draft_ready',
    detectedAt: i.detected,
    postmortem: i.postmortem,
    rootCause: i.rootCause,
    confidence: i.confidence,
}));
