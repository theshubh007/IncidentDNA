-- IncidentDNA Seed Data
-- Run after 01_schema.sql to populate test data

USE DATABASE INCIDENTDNA;

-- ═══════════════════════════════════════════════════════════════════
-- SEED DEPLOY EVENT
-- ═══════════════════════════════════════════════════════════════════
INSERT INTO RAW.DEPLOY_EVENTS (event_id, service_name, commit_hash, author, branch) VALUES
('deploy_001', 'payment-service', 'a3f9c2d', 'github-actions', 'main');

-- ═══════════════════════════════════════════════════════════════════
-- SEED METRICS (showing normal baseline + spike)
-- ═══════════════════════════════════════════════════════════════════
INSERT INTO RAW.METRICS (service_name, metric_name, metric_value) VALUES
-- Normal baseline
('payment-service', 'error_rate', 0.02),
('payment-service', 'error_rate', 0.03),
('payment-service', 'error_rate', 0.02),
-- Spike after deploy
('payment-service', 'error_rate', 0.18),
('payment-service', 'error_rate', 0.22),
-- Latency baseline
('payment-service', 'latency_p99', 210),
('payment-service', 'latency_p99', 195),
-- Latency spike
('payment-service', 'latency_p99', 1850),
('payment-service', 'latency_p99', 2100),
-- Other services (normal)
('api-gateway', 'error_rate', 0.01),
('api-gateway', 'latency_p99', 95),
('order-service', 'error_rate', 0.015),
('order-service', 'cpu_pct', 45);

-- ═══════════════════════════════════════════════════════════════════
-- SEED 5 RUNBOOKS
-- ═══════════════════════════════════════════════════════════════════
INSERT INTO RAW.RUNBOOKS (title, service_name, symptom, root_cause, fix_steps) VALUES
(
  'DB Connection Pool Exhaustion',
  'payment-service',
  'High latency, DB connection timeout errors, error rate spike',
  'Connection pool maxed out due to traffic surge or connection leak',
  '1. Check pool size: SHOW PARAMETERS LIKE connection_pool_size\n2. Kill idle connections\n3. Scale pool: SET max_pool_size=50\n4. Rolling restart service\n5. Monitor connection usage'
),
(
  'Memory Leak - Node.js',
  'api-gateway',
  'Memory usage grows unbounded, eventual OOM kills, service restarts',
  'Event listeners not removed or large objects held in closure',
  '1. Heap dump: node --inspect\n2. Analyze with Chrome DevTools\n3. Fix listener cleanup in code\n4. Deploy fix\n5. Rolling restart'
),
(
  'Rate Limit Breach',
  'notification-service',
  '429 errors from downstream APIs, failed notifications',
  'Burst traffic exceeded upstream rate limits',
  '1. Check rate limit headers\n2. Implement exponential backoff\n3. Enable request queue\n4. Contact upstream for limit increase'
),
(
  'Cache Cold Start',
  'product-service',
  'Latency spike after deploy, returns to normal after 5 minutes',
  'Redis cache flushed during deploy, cold start fills cache slowly',
  '1. Confirm cache miss rate in Redis INFO\n2. Pre-warm cache with synthetic requests\n3. Use cache-aside pattern for next deploy'
),
(
  'Disk Full - Log Accumulation',
  'worker-service',
  'Service crashes, disk I/O errors in logs',
  'Log rotation not configured, logs filled disk',
  '1. df -h to confirm disk usage\n2. logrotate -f /etc/logrotate.conf\n3. Delete old .gz logs\n4. Set max log size in config'
);

-- ═══════════════════════════════════════════════════════════════════
-- SEED 10 PAST INCIDENTS
-- ═══════════════════════════════════════════════════════════════════
INSERT INTO RAW.PAST_INCIDENTS (title, service_name, root_cause, fix_applied, resolved_at, mttr_minutes) VALUES
(
  'Payment DB pool exhausted Dec-2024',
  'payment-service',
  'DB connection pool hit max 20 during Black Friday traffic',
  'Increased pool to 50, added connection timeout of 30s',
  '2024-12-01 14:30:00',
  22
),
(
  'API Gateway OOM Jan-2025',
  'api-gateway',
  'Memory leak in request logging middleware',
  'Removed console.log in hot path, added log sampling',
  '2025-01-15 09:15:00',
  34
),
(
  'Notification rate-limited Feb-2025',
  'notification-service',
  'SendGrid 429 during promotional blast',
  'Added token bucket limiter, retry queue with backoff',
  '2025-02-10 16:00:00',
  18
),
(
  'Product cache cold start',
  'product-service',
  'Redis cache flushed during deploy',
  'Implemented cache pre-warming script',
  '2025-02-15 11:20:00',
  12
),
(
  'Worker disk full',
  'worker-service',
  'Logs filled disk, no rotation configured',
  'Configured logrotate, cleaned old logs',
  '2025-02-18 08:45:00',
  28
),
(
  'Payment latency spike',
  'payment-service',
  'Slow query without index on orders table',
  'Added composite index on (user_id, created_at)',
  '2025-02-20 13:10:00',
  15
),
(
  'API Gateway timeout cascade',
  'api-gateway',
  'Downstream service timeout caused retry storm',
  'Implemented circuit breaker pattern',
  '2025-02-22 10:30:00',
  42
),
(
  'Order service CPU spike',
  'order-service',
  'Inefficient JSON parsing in hot path',
  'Switched to streaming parser',
  '2025-02-23 15:00:00',
  19
),
(
  'Payment deadlock',
  'payment-service',
  'Database deadlock on concurrent transactions',
  'Changed transaction isolation level to READ COMMITTED',
  '2025-02-24 09:20:00',
  31
),
(
  'Notification queue backup',
  'notification-service',
  'Worker threads blocked on external API',
  'Increased worker pool size, added timeout',
  '2025-02-25 14:45:00',
  25
);

-- ═══════════════════════════════════════════════════════════════════
-- SEED SERVICE DEPENDENCIES
-- ═══════════════════════════════════════════════════════════════════
INSERT INTO RAW.SERVICE_DEPENDENCIES (service_name, depends_on) VALUES
('api-gateway', 'payment-service'),
('api-gateway', 'product-service'),
('api-gateway', 'order-service'),
('payment-service', 'postgres-primary'),
('order-service', 'payment-service'),
('notification-service', 'sendgrid-api'),
('worker-service', 'redis-cache');

-- ═══════════════════════════════════════════════════════════════════
-- SEED METRIC BASELINES (computed from historical data)
-- ═══════════════════════════════════════════════════════════════════
INSERT INTO ANALYTICS.METRIC_BASELINES (service_name, metric_name, baseline_avg, baseline_std) VALUES
('payment-service', 'error_rate', 0.023, 0.008),
('payment-service', 'latency_p99', 205, 15),
('api-gateway', 'error_rate', 0.01, 0.003),
('api-gateway', 'latency_p99', 95, 10),
('order-service', 'error_rate', 0.015, 0.005),
('order-service', 'cpu_pct', 45, 8);
