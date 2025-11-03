# FlexMON - Flexible Monitoring and Observability Platform

FlexMON is a comprehensive monitoring and observability platform designed for multi-tenant environments with agent-based and agentless monitoring capabilities.

## Features

- **Multi-tenant Architecture**: Isolated data and RBAC per tenant
- **Agent-based Monitoring**: Cross-platform Go agent (Windows/Linux/macOS)
- **Agentless Polling**: VMware vCenter and SNMP device support
- **Time-series Metrics**: TimescaleDB with automatic aggregation and retention
- **Log Management**: Elasticsearch with ILM policies
- **Real-time Alerts**: Rule-based alerting with deduplication
- **Multi-channel Notifications**: Email, Slack, Teams, Telegram, WhatsApp
- **AI-powered Insights**: Alert explanation using Ollama
- **Webhook Integration**: Zabbix, Alertmanager, and generic webhooks
- **TLS/mTLS Support**: Secure communications with certificate management
- **S3 Backup**: Automated backup to CloudFlex S3

## Architecture

```
┌─────────────┐
│   Agents    │──┐
└─────────────┘  │
                 ├──→ XMPP ──┐
┌─────────────┐  │           │
│   Pollers   │──┘           ├──→ API ──→ TimescaleDB
└─────────────┘              │           └──→ Elasticsearch
                             │
┌─────────────┐              │
│  Webhooks   │──────────────┘
└─────────────┘

┌─────────────┐
│  Frontend   │──→ API
└─────────────┘
```

## Quick Start

### Prerequisites

- Docker & Docker Compose
- 4GB RAM minimum
- 20GB disk space

### Installation

```bash
cd infra
make install
```

This will:
1. Generate secrets and TLS certificates
2. Build all Docker images
3. Start all services
4. Run database migrations
5. Load default alert rules
6. Create platform admin user

### Access

- **Frontend**: http://localhost:3000
- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **License API**: http://localhost:8001

Default credentials will be displayed during installation.

## Services

### Core Services

- **API (Port 8000)**: Main FastAPI application
- **License API (Port 8001)**: License validation service
- **Frontend (Port 3000)**: React UI
- **TimescaleDB (Port 5432)**: Time-series metrics database
- **Elasticsearch (Port 9200)**: Log storage and search
- **XMPP (Ports 5222, 5269)**: Agent messaging

### Optional Services

- **Gateway (Port 8002)**: Regional proxy with rate limiting

## Agent Deployment

### Download Agent

```bash
# Linux
wget https://your-domain/agent/flexmon-agent-linux-amd64

# Windows
# Download from https://your-domain/agent/flexmon-agent-windows-amd64.exe
```

### Configure Agent

```bash
export TENANT_ID=your-tenant-id
export API_ENDPOINT=https://your-flexmon-api:8000
export AGENT_TOKEN=your-agent-token
export COLLECTION_INTERVAL=30

./flexmon-agent
```

### Windows Service

```powershell
# Install as service
sc create FlexMONAgent binPath="C:\flexmon\flexmon-agent.exe"
sc start FlexMONAgent
```

## Configuration

### Environment Variables

See `infra/.env.example` for all configuration options.

### TLS Certificates

Self-signed certificates are generated automatically. For production:

1. Place your certificates in `infra/certificates/`
2. Update paths in `.env`
3. Restart services: `make restart`

Or upload via UI: **Settings → Security → Upload Certificates**

### Notification Channels

Configure in UI: **Settings → Notifications**

Supported channels:
- Email (SMTP)
- Slack (Webhook)
- Microsoft Teams (Webhook)
- Telegram (Bot API)
- WhatsApp (Cloud API)

## Alert Rules

Default rules are loaded automatically:
- High CPU Usage (>85%)
- High Memory Usage (>90%)
- High Disk Usage (>90%)
- Node Down
- Network Spike Detection

Customize via UI: **Alarms → Rules**

## Backup

### Manual Backup

```bash
make backup
```

### S3 Automated Backup

Configure in `.env`:
```
S3_ENDPOINT=https://s3.cloudflex.tr
S3_BUCKET=flexmon-backups
S3_ACCESS_KEY=your-key
S3_SECRET_KEY=your-secret
```

## Monitoring

### Health Checks

```bash
make health
```

### View Logs

```bash
make logs
```

### Load Demo Data

```bash
make demo
```

## API Documentation

See [API.md](docs/API.md) for detailed API documentation.

## Architecture

See [ARCHITECTURE.md](docs/ARCHITECTURE.md) for system architecture details.

## License

Commercial license. Contact CloudFlex for licensing.

## Support

- Email: support@cloudflex.tr
- Documentation: https://docs.flexmon.io
- Issues: Create ticket in support portal

## Release Notes

See [releases.md](releases.md) for version history and changes.
