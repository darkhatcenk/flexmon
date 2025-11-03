# FlexMON Architecture

## System Overview

FlexMON is a distributed monitoring platform with multi-tenancy support, designed for high scalability and reliability.

## Components

### 1. Data Collection Layer

#### Agents (Go)
- Cross-platform binary (Windows/Linux/macOS)
- Collects system metrics every 30s (configurable 10-300s)
- Metrics: CPU, Memory, Disk, Network, Processes
- Communication: XMPP (primary), HTTPS (fallback)
- Exponential backoff on failures (up to 300s)

#### Pollers
- **VMware Poller**: vCenter API integration
- **SNMP Poller**: Network device monitoring
- Both counted against tenant license

### 2. Messaging Layer

#### XMPP Server (Ejabberd)
- Agent pub/sub: `metrics.<tenant_id>.<host>`
- Low latency, persistent connections
- Automatic reconnection

### 3. API Layer

#### Main API (FastAPI)
- RESTful API with OpenAPI documentation
- JWT authentication with role-based access
- Multi-tenancy isolation
- Rate limiting (1000 req/min default)
- Batch ingestion (max 15MB / 3000 records)

**Key Endpoints:**
- `/v1/ingest/metrics/batch` - Metrics ingestion (NDJSON)
- `/v1/alerts/*` - Alert management
- `/v1/webhooks/*` - External integrations
- `/v1/discovery/*` - Agent discovery
- `/v1/ai/explain/*` - AI-powered insights

#### License API (FastAPI)
- Separate service for license validation
- Daily license checks
- Grace period: 7 days
- Agent limit enforcement

#### Gateway (Optional)
- Regional proxy for distributed deployments
- Rate limiting per client IP
- Retry logic with exponential backoff
- Request forwarding to central API

### 4. Storage Layer

#### TimescaleDB
**Hypertables:**
- `metrics_cpu`, `metrics_memory`, `metrics_disk`, `metrics_network`, `metrics_process`
- Chunk interval: 1 day
- Automatic partitioning by time

**Continuous Aggregates:**
- 5-minute averages (30-day retention)
- 1-hour averages (365-day retention)

**Retention:**
- Raw metrics: 7 days
- 5-min aggregates: 30 days
- 1-hour aggregates: 365 days

**Compression:**
- Enabled after 1 day
- Automatic compression on older chunks

#### Elasticsearch
**Indices:**
- `logs-<tenant>-YYYY.MM.DD` - Application logs
- `platform-logs-<tenant>-YYYY.MM.DD` - Audit trail

**ILM Policy:**
- Hot phase: 20GB/1day rollover
- Warm phase: 7 days (forcemerge, shrink)
- Delete: 90 days

### 5. Alert Engine

**Rule Types:**
- **Threshold**: Single metric comparison
- **Ratio**: Two metric comparison
- **Anomaly**: Spike detection (3x baseline)
- **Absence**: Node down detection
- **Log Query**: Elasticsearch query-based

**Features:**
- Evaluation interval: 60 seconds
- Deduplication: 15 minutes (configurable)
- Fingerprint-based identification
- Multi-channel routing by severity

**Notification Channels:**
- Email (SMTP)
- Slack (Webhook)
- Microsoft Teams (Webhook)
- Telegram (Bot API)
- WhatsApp (Cloud API)

### 6. Frontend (React)

**Pages:**
- Dashboard: Top-10 metrics, recent alarms
- Servers: Agent list, license management
- Server Detail: 7-day graphs, running apps
- Logs: Elasticsearch search with KQL
- Alarms: Merged internal + external alerts
- Reports: Monthly summaries
- Discover: Agent discovery and configuration
- Users: RBAC management
- Platform Logs: Audit trail
- Settings: TLS, notifications, backup, AI

**Tech Stack:**
- React 18
- Vite
- TanStack Query
- ApexCharts
- React Router

## Data Flow

### Metrics Collection
```
Agent → XMPP → API → TimescaleDB
      ↓ (fallback)
      HTTPS → API
```

### Log Collection
```
Agent → API → Elasticsearch
           ↓ (bulk)
      Index templates + ILM
```

### Alert Processing
```
Alert Engine → Evaluate Rules → Fire Alert
                                    ↓
                            Deduplication Check
                                    ↓
                            Notification Router
                                    ↓
                        Multi-channel Delivery
```

### Webhook Integration
```
External System → Webhook Endpoint → alerts_external table
                                          ↓
                                    Merged in UI
```

## Security

### Authentication
- JWT tokens (60-min expiration)
- Password hashing: bcrypt
- One-time passwords for emergency access

### Authorization
- **Roles:**
  - `platform_admin`: Full access, cross-tenant
  - `tenant_admin`: Tenant management
  - `tenant_reporter`: Read-only

### TLS/mTLS
- Self-signed certificates (auto-generated)
- Custom certificate upload via UI
- Optional mutual TLS for agents

### Webhook Security
- HMAC-SHA256 signature verification
- IP allowlist (optional)

## Scalability

### Horizontal Scaling
- **API**: Stateless, scale behind load balancer
- **Agents**: Unlimited, license-based
- **TimescaleDB**: Replication + read replicas
- **Elasticsearch**: Multi-node cluster

### Vertical Scaling
- API: Increase CPU for faster processing
- Database: More memory for query performance
- Elasticsearch: More disk for retention

### Performance Targets
- Metrics ingestion: 100K/sec per API instance
- Alert evaluation: <1s latency
- UI response time: <200ms (cached)
- Log search: <2s (90th percentile)

## High Availability

### Database
- TimescaleDB streaming replication
- Automatic failover with Patroni

### Elasticsearch
- 3-node cluster minimum
- Replica shards for fault tolerance

### API
- Multiple instances behind load balancer
- Health checks every 30s
- Graceful shutdown

### XMPP
- Clustered deployment
- Automatic agent reconnection

## Monitoring

### Self-Monitoring
- All FlexMON components monitored by FlexMON
- Platform logs in Elasticsearch
- System metrics in TimescaleDB

### Health Checks
- `/v1/health` endpoint
- Database connectivity
- Elasticsearch cluster status
- XMPP server status

## Backup & Disaster Recovery

### Automated Backup
- TimescaleDB: pg_dump daily
- Elasticsearch: Snapshot to S3
- Configuration: Git repository

### Recovery
- Database restore: <30 minutes
- Full system restore: <2 hours
- RPO: 24 hours
- RTO: 2 hours

## License Model

### Per-Tenant Licensing
- Agent limit per license
- Grace period: 7 days
- Daily validation
- Automatic enforcement (stop ingestion)

### Counted Resources
- Installed agents
- VMware pollers
- SNMP devices

## Deployment Scenarios

### Single-Server
- All-in-one Docker Compose
- Suitable for <100 agents
- Min: 4GB RAM, 2 CPU cores

### Multi-Server
- Separate API, DB, ES instances
- Suitable for <1000 agents
- Load balanced APIs

### Distributed
- Regional gateways
- Central processing
- Suitable for 1000+ agents

## Future Enhancements

- Kubernetes deployment
- Advanced ML anomaly detection
- Mobile app
- Custom dashboard builder
- Integration marketplace
