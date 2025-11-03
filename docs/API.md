# FlexMON API Documentation

Base URL: `http://your-domain:8000`

All endpoints are prefixed with `/v1`

## Authentication

### POST /v1/auth/login
Login and receive JWT token.

**Request:**
```json
{
  "username": "admin",
  "password": "secret"
}
```

**Response:**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

**Usage:**
```
Authorization: Bearer <access_token>
```

## Health

### GET /v1/health
Check API health and service status.

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2025-11-03T00:00:00Z",
  "services": {
    "timescaledb": "healthy",
    "elasticsearch": "green"
  }
}
```

## Metrics Ingestion

### POST /v1/ingest/metrics/batch
Ingest batch of metrics in NDJSON format.

**Headers:**
- `Content-Type: application/x-ndjson`
- `Authorization: Bearer <token>`

**Request Body (NDJSON):**
```ndjson
{"metric_type":"cpu","timestamp":"2025-11-03T00:00:00Z","tenant_id":"demo","host":"server-01","cpu_percent":45.2,"cpu_user":30.1,"cpu_system":15.1,"cpu_idle":54.8,"cpu_iowait":2.0}
{"metric_type":"memory","timestamp":"2025-11-03T00:00:00Z","tenant_id":"demo","host":"server-01","memory_total":16777216000,"memory_used":10737418240,"memory_free":6039797760,"memory_percent":64.0}
```

**Limits:**
- Max size: 15 MB
- Max records: 3000

**Response:**
```json
{
  "message": "Metrics ingested successfully",
  "count": 150,
  "breakdown": {
    "cpu": 50,
    "memory": 50,
    "disk": 25,
    "network": 25
  }
}
```

### GET /v1/metrics/{metric_type}/query
Query historical metrics.

**Parameters:**
- `metric_type`: cpu|memory|disk|network|process
- `host`: Hostname
- `start_time`: ISO 8601 timestamp
- `end_time`: ISO 8601 timestamp

**Response:**
```json
{
  "metric_type": "cpu",
  "host": "server-01",
  "count": 100,
  "data": [
    {
      "timestamp": "2025-11-03T00:00:00Z",
      "cpu_percent": 45.2,
      "cpu_user": 30.1,
      "cpu_system": 15.1
    }
  ]
}
```

## Alert Rules

### GET /v1/alerts/rules
List all alert rules for current tenant.

**Response:**
```json
[
  {
    "id": 1,
    "name": "High CPU Usage",
    "type": "threshold",
    "metric": "cpu_percent",
    "condition": ">",
    "threshold": 85,
    "duration_minutes": 5,
    "severity": "warning",
    "enabled": true
  }
]
```

### POST /v1/alerts/rules
Create new alert rule.

**Request:**
```json
{
  "name": "High Memory Usage",
  "description": "Memory exceeds 90%",
  "type": "threshold",
  "metric": "memory_percent",
  "condition": ">",
  "threshold": 90,
  "duration_minutes": 5,
  "severity": "warning",
  "enabled": true,
  "tags": ["memory", "performance"]
}
```

### PATCH /v1/alerts/rules/{rule_id}
Enable/disable alert rule.

**Request:**
```json
{
  "enabled": false
}
```

### DELETE /v1/alerts/rules/{rule_id}
Delete alert rule.

## Alerts

### GET /v1/alerts
List recent alerts.

**Parameters:**
- `limit`: Max results (default: 100)

**Response:**
```json
[
  {
    "id": 123,
    "rule_name": "High CPU Usage",
    "host": "server-01",
    "severity": "warning",
    "message": "CPU usage 92% exceeds threshold 85%",
    "value": 92,
    "threshold": 85,
    "triggered_at": "2025-11-03T00:00:00Z",
    "resolved_at": null,
    "acknowledged_at": null
  }
]
```

### POST /v1/alerts/{alert_id}/acknowledge
Acknowledge an alert.

**Response:**
```json
{
  "message": "Alert acknowledged"
}
```

## Webhooks

### POST /v1/webhooks/zabbix
Receive Zabbix alerts.

**Headers:**
- `X-Webhook-Signature`: HMAC-SHA256 signature (optional)

**Request:**
```json
{
  "tenant_id": "demo",
  "host": "server-01",
  "severity": "warning",
  "message": "High CPU detected"
}
```

### POST /v1/webhooks/alertmanager
Receive Prometheus Alertmanager alerts.

**Request:**
```json
{
  "alerts": [
    {
      "labels": {
        "tenant_id": "demo",
        "instance": "server-01",
        "severity": "warning"
      },
      "annotations": {
        "summary": "High CPU usage"
      },
      "status": "firing"
    }
  ]
}
```

### POST /v1/webhooks/generic
Generic webhook endpoint.

**Request:**
```json
{
  "tenant_id": "demo",
  "host": "server-01",
  "severity": "info",
  "message": "Custom alert"
}
```

## Agent Discovery

### POST /v1/discovery/register
Register a new agent.

**Request:**
```json
{
  "fingerprint": {
    "hostname": "server-01",
    "uuid": "550e8400-e29b-41d4-a716-446655440000",
    "mac_address": "00:0a:95:9d:68:16",
    "ip_address": "192.168.1.100",
    "os": "Linux",
    "os_version": "Ubuntu 22.04",
    "architecture": "x86_64"
  },
  "tenant_id": "demo"
}
```

**Response:**
```json
{
  "message": "Agent registered successfully",
  "agent_id": 42,
  "licensed": false,
  "fingerprint": "abc123..."
}
```

### GET /v1/discovery/agents
List all discovered agents.

**Response:**
```json
[
  {
    "id": 42,
    "hostname": "server-01",
    "ip_address": "192.168.1.100",
    "os": "Linux",
    "licensed": true,
    "last_seen": "2025-11-03T00:00:00Z"
  }
]
```

### PATCH /v1/discovery/agents/{agent_id}/license
Bind/unbind license to agent.

**Request:**
```json
{
  "licensed": true
}
```

### PATCH /v1/discovery/agents/{agent_id}/config
Update agent configuration.

**Request:**
```json
{
  "ignore_logs": false,
  "ignore_alerts": false,
  "collection_interval_sec": 60
}
```

## AI Explanation

### POST /v1/ai/explain/alert/{alert_id}
Get AI-powered explanation for an alert.

**Response:**
```json
{
  "alert_id": 123,
  "explanation": "The CPU usage spike is likely caused by...",
  "context_used": 100,
  "model": "llama2"
}
```

### POST /v1/ai/explain/metrics
Get AI explanation for metric anomalies.

**Request:**
```json
{
  "host": "server-01",
  "metric_type": "cpu"
}
```

**Response:**
```json
{
  "host": "server-01",
  "metric_type": "cpu",
  "explanation": "CPU usage is elevated but within normal range...",
  "statistics": {
    "average": 45.2,
    "maximum": 92.5,
    "minimum": 12.1,
    "current": 67.8
  }
}
```

## Notifications

### GET /v1/notifications/channels
List notification channels.

**Response:**
```json
[
  {
    "id": 1,
    "channel_type": "slack",
    "name": "slack_channel",
    "enabled": true,
    "config": {
      "webhook_url": "https://hooks.slack.com/..."
    }
  }
]
```

### POST /v1/notifications/channels
Create notification channel.

**Request:**
```json
{
  "channel": "slack",
  "enabled": true,
  "config": {
    "webhook_url": "https://hooks.slack.com/..."
  }
}
```

### POST /v1/notifications/send
Send test notification.

**Request:**
```json
{
  "channel": "slack",
  "tenant_id": "demo",
  "severity": "info",
  "subject": "Test Alert",
  "message": "This is a test notification"
}
```

## Users

### GET /v1/users
List users (filtered by tenant).

**Response:**
```json
[
  {
    "id": 1,
    "username": "admin",
    "email": "admin@example.com",
    "role": "tenant_admin",
    "tenant_id": "demo",
    "enabled": true
  }
]
```

### POST /v1/users
Create new user.

**Request:**
```json
{
  "username": "newuser",
  "password": "secret123",
  "email": "user@example.com",
  "role": "tenant_reporter",
  "tenant_id": "demo"
}
```

### PATCH /v1/users/{user_id}
Enable/disable user.

**Request:**
```json
{
  "enabled": false
}
```

### DELETE /v1/users/{user_id}
Delete user.

## Rate Limits

- Default: 1000 requests/minute per IP
- Metrics batch: 15 MB / 3000 records per request
- Exceeded: HTTP 429 Too Many Requests

## Error Responses

```json
{
  "detail": "Error message",
  "error": "Additional details"
}
```

**Status Codes:**
- 400: Bad Request
- 401: Unauthorized
- 403: Forbidden
- 404: Not Found
- 413: Payload Too Large
- 429: Too Many Requests
- 500: Internal Server Error
- 503: Service Unavailable

## Interactive Documentation

OpenAPI documentation available at:
- Swagger UI: `/v1/docs`
- ReDoc: `/v1/redoc`
- OpenAPI JSON: `/v1/openapi.json`
