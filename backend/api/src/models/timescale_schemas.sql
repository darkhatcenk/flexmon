-- FlexMON TimescaleDB Schema
-- Time-series metrics storage with automatic partitioning and compression

-- Enable TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

-- =============================================================================
-- USERS AND TENANTS
-- =============================================================================

CREATE TABLE IF NOT EXISTS tenants (
    id VARCHAR(255) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    license_key VARCHAR(255),
    license_expires_at TIMESTAMP,
    license_agent_limit INTEGER DEFAULT 10,
    licensed_agents INTEGER DEFAULT 0,
    grace_period_until TIMESTAMP,
    enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255),
    password_hash TEXT NOT NULL,
    role VARCHAR(50) NOT NULL CHECK (role IN ('platform_admin', 'tenant_admin', 'tenant_reporter')),
    tenant_id VARCHAR(255) REFERENCES tenants(id) ON DELETE CASCADE,
    enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    last_login TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_users_tenant ON users(tenant_id);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);

-- =============================================================================
-- AGENTS AND DISCOVERY
-- =============================================================================

CREATE TABLE IF NOT EXISTS agents (
    id SERIAL PRIMARY KEY,
    fingerprint VARCHAR(255) UNIQUE NOT NULL,
    hostname VARCHAR(255) NOT NULL,
    tenant_id VARCHAR(255) REFERENCES tenants(id) ON DELETE CASCADE,
    uuid VARCHAR(255),
    mac_address VARCHAR(255),
    ip_address VARCHAR(255),
    os VARCHAR(100),
    os_version VARCHAR(100),
    architecture VARCHAR(50),
    licensed BOOLEAN DEFAULT FALSE,
    ignore_logs BOOLEAN DEFAULT FALSE,
    ignore_alerts BOOLEAN DEFAULT FALSE,
    collection_interval_sec INTEGER DEFAULT 30,
    last_seen TIMESTAMP,
    registered_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_agents_tenant ON agents(tenant_id);
CREATE INDEX IF NOT EXISTS idx_agents_hostname ON agents(hostname);
CREATE INDEX IF NOT EXISTS idx_agents_fingerprint ON agents(fingerprint);

-- =============================================================================
-- HOST INFO
-- =============================================================================

CREATE TABLE IF NOT EXISTS host_info (
    timestamp TIMESTAMP NOT NULL,
    tenant_id VARCHAR(255) NOT NULL,
    host VARCHAR(255) NOT NULL,
    os VARCHAR(100),
    os_version VARCHAR(100),
    kernel_version VARCHAR(100),
    architecture VARCHAR(50),
    cpu_count INTEGER,
    cpu_model VARCHAR(255),
    memory_total BIGINT,
    uptime_seconds BIGINT,
    boot_time TIMESTAMP
);

SELECT create_hypertable('host_info', 'timestamp',
    chunk_time_interval => INTERVAL '7 days',
    if_not_exists => TRUE
);

CREATE INDEX IF NOT EXISTS idx_host_info_tenant_host ON host_info(tenant_id, host, timestamp DESC);

-- =============================================================================
-- CPU METRICS
-- =============================================================================

CREATE TABLE IF NOT EXISTS metrics_cpu (
    timestamp TIMESTAMP NOT NULL,
    tenant_id VARCHAR(255) NOT NULL,
    host VARCHAR(255) NOT NULL,
    cpu_percent DOUBLE PRECISION,
    cpu_user DOUBLE PRECISION,
    cpu_system DOUBLE PRECISION,
    cpu_idle DOUBLE PRECISION,
    cpu_iowait DOUBLE PRECISION
);

SELECT create_hypertable('metrics_cpu', 'timestamp',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

CREATE INDEX IF NOT EXISTS idx_metrics_cpu_tenant_host ON metrics_cpu(tenant_id, host, timestamp DESC);

-- Continuous aggregates for 5-minute averages
CREATE MATERIALIZED VIEW IF NOT EXISTS metrics_cpu_5min
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('5 minutes', timestamp) AS bucket,
    tenant_id,
    host,
    AVG(cpu_percent) AS cpu_percent_avg,
    MAX(cpu_percent) AS cpu_percent_max,
    AVG(cpu_user) AS cpu_user_avg,
    AVG(cpu_system) AS cpu_system_avg,
    AVG(cpu_idle) AS cpu_idle_avg,
    AVG(cpu_iowait) AS cpu_iowait_avg
FROM metrics_cpu
GROUP BY bucket, tenant_id, host;

-- Continuous aggregates for 1-hour averages
CREATE MATERIALIZED VIEW IF NOT EXISTS metrics_cpu_1h
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 hour', timestamp) AS bucket,
    tenant_id,
    host,
    AVG(cpu_percent) AS cpu_percent_avg,
    MAX(cpu_percent) AS cpu_percent_max,
    MIN(cpu_percent) AS cpu_percent_min
FROM metrics_cpu
GROUP BY bucket, tenant_id, host;

-- =============================================================================
-- MEMORY METRICS
-- =============================================================================

CREATE TABLE IF NOT EXISTS metrics_memory (
    timestamp TIMESTAMP NOT NULL,
    tenant_id VARCHAR(255) NOT NULL,
    host VARCHAR(255) NOT NULL,
    memory_total BIGINT,
    memory_used BIGINT,
    memory_free BIGINT,
    memory_percent DOUBLE PRECISION,
    swap_total BIGINT,
    swap_used BIGINT,
    swap_free BIGINT,
    swap_percent DOUBLE PRECISION
);

SELECT create_hypertable('metrics_memory', 'timestamp',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

CREATE INDEX IF NOT EXISTS idx_metrics_memory_tenant_host ON metrics_memory(tenant_id, host, timestamp DESC);

-- Continuous aggregates
CREATE MATERIALIZED VIEW IF NOT EXISTS metrics_memory_5min
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('5 minutes', timestamp) AS bucket,
    tenant_id,
    host,
    AVG(memory_percent) AS memory_percent_avg,
    MAX(memory_percent) AS memory_percent_max,
    AVG(swap_percent) AS swap_percent_avg
FROM metrics_memory
GROUP BY bucket, tenant_id, host;

-- =============================================================================
-- DISK METRICS
-- =============================================================================

CREATE TABLE IF NOT EXISTS metrics_disk (
    timestamp TIMESTAMP NOT NULL,
    tenant_id VARCHAR(255) NOT NULL,
    host VARCHAR(255) NOT NULL,
    device VARCHAR(255) NOT NULL,
    mountpoint VARCHAR(255) NOT NULL,
    total_bytes BIGINT,
    used_bytes BIGINT,
    free_bytes BIGINT,
    percent DOUBLE PRECISION
);

SELECT create_hypertable('metrics_disk', 'timestamp',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

CREATE INDEX IF NOT EXISTS idx_metrics_disk_tenant_host ON metrics_disk(tenant_id, host, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_metrics_disk_device ON metrics_disk(device, mountpoint, timestamp DESC);

-- =============================================================================
-- NETWORK METRICS
-- =============================================================================

CREATE TABLE IF NOT EXISTS metrics_network (
    timestamp TIMESTAMP NOT NULL,
    tenant_id VARCHAR(255) NOT NULL,
    host VARCHAR(255) NOT NULL,
    interface VARCHAR(255) NOT NULL,
    bytes_sent BIGINT,
    bytes_recv BIGINT,
    packets_sent BIGINT,
    packets_recv BIGINT,
    errors_in INTEGER,
    errors_out INTEGER,
    drops_in INTEGER,
    drops_out INTEGER
);

SELECT create_hypertable('metrics_network', 'timestamp',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

CREATE INDEX IF NOT EXISTS idx_metrics_network_tenant_host ON metrics_network(tenant_id, host, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_metrics_network_interface ON metrics_network(interface, timestamp DESC);

-- Continuous aggregates for network rates
CREATE MATERIALIZED VIEW IF NOT EXISTS metrics_network_5min
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('5 minutes', timestamp) AS bucket,
    tenant_id,
    host,
    interface,
    MAX(bytes_sent) - MIN(bytes_sent) AS bytes_sent_delta,
    MAX(bytes_recv) - MIN(bytes_recv) AS bytes_recv_delta,
    SUM(errors_in) AS errors_in_sum,
    SUM(errors_out) AS errors_out_sum
FROM metrics_network
GROUP BY bucket, tenant_id, host, interface;

-- =============================================================================
-- PROCESS METRICS
-- =============================================================================

CREATE TABLE IF NOT EXISTS metrics_process (
    timestamp TIMESTAMP NOT NULL,
    tenant_id VARCHAR(255) NOT NULL,
    host VARCHAR(255) NOT NULL,
    pid INTEGER NOT NULL,
    name VARCHAR(255) NOT NULL,
    cpu_percent DOUBLE PRECISION,
    memory_percent DOUBLE PRECISION,
    status VARCHAR(50),
    username VARCHAR(255)
);

SELECT create_hypertable('metrics_process', 'timestamp',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

CREATE INDEX IF NOT EXISTS idx_metrics_process_tenant_host ON metrics_process(tenant_id, host, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_metrics_process_name ON metrics_process(name, timestamp DESC);

-- =============================================================================
-- ALERTS
-- =============================================================================

CREATE TABLE IF NOT EXISTS alert_rules (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    type VARCHAR(50) NOT NULL CHECK (type IN ('threshold', 'ratio', 'anomaly', 'absence', 'log_query')),
    metric VARCHAR(255),
    condition VARCHAR(10),
    threshold DOUBLE PRECISION,
    duration_minutes INTEGER DEFAULT 5,
    severity VARCHAR(50) NOT NULL CHECK (severity IN ('info', 'warning', 'error', 'critical')),
    enabled BOOLEAN DEFAULT TRUE,
    tenant_id VARCHAR(255) REFERENCES tenants(id) ON DELETE CASCADE,
    tags TEXT[],
    config JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(name, tenant_id)
);

CREATE INDEX IF NOT EXISTS idx_alert_rules_tenant ON alert_rules(tenant_id);
CREATE INDEX IF NOT EXISTS idx_alert_rules_enabled ON alert_rules(enabled);

CREATE TABLE IF NOT EXISTS alerts (
    id SERIAL PRIMARY KEY,
    rule_id INTEGER REFERENCES alert_rules(id) ON DELETE SET NULL,
    rule_name VARCHAR(255) NOT NULL,
    tenant_id VARCHAR(255) NOT NULL,
    host VARCHAR(255) NOT NULL,
    severity VARCHAR(50) NOT NULL,
    message TEXT NOT NULL,
    value DOUBLE PRECISION,
    threshold DOUBLE PRECISION,
    triggered_at TIMESTAMP NOT NULL,
    resolved_at TIMESTAMP,
    acknowledged_at TIMESTAMP,
    acknowledged_by VARCHAR(255),
    tags JSONB,
    fingerprint VARCHAR(255) UNIQUE
);

CREATE INDEX IF NOT EXISTS idx_alerts_tenant ON alerts(tenant_id, triggered_at DESC);
CREATE INDEX IF NOT EXISTS idx_alerts_host ON alerts(host, triggered_at DESC);
CREATE INDEX IF NOT EXISTS idx_alerts_severity ON alerts(severity);
CREATE INDEX IF NOT EXISTS idx_alerts_fingerprint ON alerts(fingerprint);

-- External alerts from webhooks
CREATE TABLE IF NOT EXISTS alerts_external (
    id SERIAL PRIMARY KEY,
    source VARCHAR(100) NOT NULL,
    tenant_id VARCHAR(255) NOT NULL,
    host VARCHAR(255),
    severity VARCHAR(50) NOT NULL,
    message TEXT NOT NULL,
    raw_payload JSONB,
    received_at TIMESTAMP DEFAULT NOW(),
    fingerprint VARCHAR(255) UNIQUE
);

CREATE INDEX IF NOT EXISTS idx_alerts_external_tenant ON alerts_external(tenant_id, received_at DESC);
CREATE INDEX IF NOT EXISTS idx_alerts_external_source ON alerts_external(source);

-- =============================================================================
-- NOTIFICATION CHANNELS
-- =============================================================================

CREATE TABLE IF NOT EXISTS notification_channels (
    id SERIAL PRIMARY KEY,
    tenant_id VARCHAR(255) REFERENCES tenants(id) ON DELETE CASCADE,
    channel_type VARCHAR(50) NOT NULL CHECK (channel_type IN ('email', 'slack', 'teams', 'telegram', 'whatsapp')),
    name VARCHAR(255) NOT NULL,
    enabled BOOLEAN DEFAULT TRUE,
    config JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_notification_channels_tenant ON notification_channels(tenant_id);

-- =============================================================================
-- PLATFORM LOGS (Audit Trail)
-- =============================================================================

CREATE TABLE IF NOT EXISTS platform_logs (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT NOW(),
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    username VARCHAR(255),
    action VARCHAR(255) NOT NULL,
    resource_type VARCHAR(100),
    resource_id VARCHAR(255),
    details JSONB,
    ip_address VARCHAR(50),
    user_agent TEXT
);

CREATE INDEX IF NOT EXISTS idx_platform_logs_timestamp ON platform_logs(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_platform_logs_user ON platform_logs(user_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_platform_logs_action ON platform_logs(action);

-- =============================================================================
-- RETENTION POLICIES
-- =============================================================================

-- Raw metrics: 7 days
SELECT add_retention_policy('metrics_cpu', INTERVAL '7 days', if_not_exists => TRUE);
SELECT add_retention_policy('metrics_memory', INTERVAL '7 days', if_not_exists => TRUE);
SELECT add_retention_policy('metrics_disk', INTERVAL '7 days', if_not_exists => TRUE);
SELECT add_retention_policy('metrics_network', INTERVAL '7 days', if_not_exists => TRUE);
SELECT add_retention_policy('metrics_process', INTERVAL '7 days', if_not_exists => TRUE);

-- 5-minute aggregates: 30 days
SELECT add_retention_policy('metrics_cpu_5min', INTERVAL '30 days', if_not_exists => TRUE);
SELECT add_retention_policy('metrics_memory_5min', INTERVAL '30 days', if_not_exists => TRUE);
SELECT add_retention_policy('metrics_network_5min', INTERVAL '30 days', if_not_exists => TRUE);

-- 1-hour aggregates: 365 days
SELECT add_retention_policy('metrics_cpu_1h', INTERVAL '365 days', if_not_exists => TRUE);

-- Alerts: 90 days
CREATE OR REPLACE FUNCTION cleanup_old_alerts() RETURNS void AS $$
BEGIN
    DELETE FROM alerts WHERE triggered_at < NOW() - INTERVAL '90 days';
    DELETE FROM alerts_external WHERE received_at < NOW() - INTERVAL '90 days';
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- COMPRESSION
-- =============================================================================

-- Enable compression settings on hypertables (must be done before adding policies)
ALTER TABLE metrics_cpu
  SET (timescaledb.compress,
       timescaledb.compress_orderby = 'timestamp DESC',
       timescaledb.compress_segmentby = 'tenant_id,host');

ALTER TABLE metrics_memory
  SET (timescaledb.compress,
       timescaledb.compress_orderby = 'timestamp DESC',
       timescaledb.compress_segmentby = 'tenant_id,host');

ALTER TABLE metrics_disk
  SET (timescaledb.compress,
       timescaledb.compress_orderby = 'timestamp DESC',
       timescaledb.compress_segmentby = 'tenant_id,host,device');

ALTER TABLE metrics_network
  SET (timescaledb.compress,
       timescaledb.compress_orderby = 'timestamp DESC',
       timescaledb.compress_segmentby = 'tenant_id,host,interface');

ALTER TABLE metrics_process
  SET (timescaledb.compress,
       timescaledb.compress_orderby = 'timestamp DESC',
       timescaledb.compress_segmentby = 'tenant_id,host,name');

ALTER TABLE host_info
  SET (timescaledb.compress,
       timescaledb.compress_orderby = 'timestamp DESC',
       timescaledb.compress_segmentby = 'tenant_id,host');

-- Add compression policies (compress chunks older than 1 day)
SELECT add_compression_policy('metrics_cpu', INTERVAL '1 day', if_not_exists => TRUE);
SELECT add_compression_policy('metrics_memory', INTERVAL '1 day', if_not_exists => TRUE);
SELECT add_compression_policy('metrics_disk', INTERVAL '1 day', if_not_exists => TRUE);
SELECT add_compression_policy('metrics_network', INTERVAL '1 day', if_not_exists => TRUE);
SELECT add_compression_policy('metrics_process', INTERVAL '1 day', if_not_exists => TRUE);
SELECT add_compression_policy('host_info', INTERVAL '1 day', if_not_exists => TRUE);

-- =============================================================================
-- HELPER FUNCTIONS
-- =============================================================================

-- Function to get latest metrics for a host
CREATE OR REPLACE FUNCTION get_latest_metrics(p_tenant_id VARCHAR, p_host VARCHAR)
RETURNS TABLE (
    metric_type VARCHAR,
    ts TIMESTAMPTZ,
    value JSONB
) AS $$
BEGIN
    RETURN QUERY
    SELECT 'cpu'::VARCHAR, timestamp, jsonb_build_object(
        'cpu_percent', cpu_percent,
        'cpu_user', cpu_user,
        'cpu_system', cpu_system
    )
    FROM metrics_cpu
    WHERE tenant_id = p_tenant_id AND host = p_host
    ORDER BY timestamp DESC
    LIMIT 1;
END;
$$ LANGUAGE plpgsql;

-- Function to check if agent is licensed
CREATE OR REPLACE FUNCTION is_agent_licensed(p_tenant_id VARCHAR, p_fingerprint VARCHAR)
RETURNS BOOLEAN AS $$
DECLARE
    v_licensed BOOLEAN;
BEGIN
    SELECT licensed INTO v_licensed
    FROM agents
    WHERE tenant_id = p_tenant_id AND fingerprint = p_fingerprint;

    RETURN COALESCE(v_licensed, FALSE);
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- INITIAL DATA
-- =============================================================================

-- This will be populated by install.sh
-- Platform admin user will be created during installation
