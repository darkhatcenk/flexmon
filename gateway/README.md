# FlexMON Regional Gateway

A lightweight FastAPI-based regional gateway that forwards agent and poller traffic to the central FlexMON API with rate limiting, retry logic, HMAC signing, and IP allowlist support.

## Features

- **Traffic Forwarding**: Proxy all agent/poller requests to central API
- **Rate Limiting**: Per-IP and global rate limits to prevent abuse
- **Retry Logic**: Exponential backoff retry on network failures
- **HMAC Signing**: Optional HMAC-SHA256 signing of forwarded requests
- **IP Allowlist**: Optional IP-based access control with wildcard support
- **Statistics**: Real-time request statistics via `/stats` endpoint
- **Health Check**: Health endpoint for monitoring
- **Regional Identification**: Tags requests with gateway region

## Use Cases

### Regional Deployment
Deploy gateways in different geographic regions to:
- Reduce latency for agents
- Load balance traffic across regions
- Provide regional failover
- Implement regional access controls

### Edge Gateway
Deploy at network edge to:
- Rate limit agent traffic before reaching central API
- Filter traffic by IP allowlist
- Add HMAC signatures for request authentication
- Provide local retry logic

### Development/Testing
Use for local development to:
- Test rate limiting behavior
- Simulate network failures with retry
- Test HMAC signature validation

## Configuration

All configuration is via environment variables:

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `CENTRAL_API_URL` | Central FlexMON API URL | `http://api:8000` | Yes |
| `HMAC_SECRET` | Secret for HMAC signing | - | No |
| `ENABLE_HMAC_SIGNING` | Enable HMAC signing (true/false) | `false` | No |
| `RATE_LIMIT_PER_MIN` | Global rate limit (requests/min) | `1000` | No |
| `RATE_LIMIT_PER_IP` | Per-IP rate limit (requests/min) | `100` | No |
| `IP_ALLOWLIST` | Comma-separated list of allowed IPs | - | No |
| `MAX_RETRIES` | Maximum retry attempts | `3` | No |
| `TIMEOUT_SECONDS` | Request timeout in seconds | `30` | No |
| `GATEWAY_REGION` | Gateway region identifier | `default` | No |

## Quick Start

### Docker Run

```bash
docker build -t flexmon-gateway .

docker run -d \
  --name flexmon-gateway \
  -p 8002:8002 \
  -e CENTRAL_API_URL=https://api.flexmon.io \
  -e GATEWAY_REGION=us-east-1 \
  -e ENABLE_HMAC_SIGNING=true \
  -e HMAC_SECRET=your-secret-key \
  flexmon-gateway
```

### Docker Compose

```yaml
version: '3.8'

services:
  gateway:
    build: .
    ports:
      - "8002:8002"
    environment:
      - CENTRAL_API_URL=https://api.flexmon.io
      - GATEWAY_REGION=us-west-2
      - ENABLE_HMAC_SIGNING=true
      - HMAC_SECRET=your-secret-key
      - RATE_LIMIT_PER_MIN=1000
      - RATE_LIMIT_PER_IP=100
      - IP_ALLOWLIST=10.0.0.0/8,192.168.*
    restart: unless-stopped
```

### Python Development

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export CENTRAL_API_URL=http://localhost:8000
export GATEWAY_REGION=dev

# Run gateway
python -m uvicorn src.main:app --host 0.0.0.0 --port 8002 --reload
```

## Endpoints

### Health Check
```bash
curl http://localhost:8002/health
```

Response:
```json
{
  "status": "healthy",
  "service": "flexmon-gateway",
  "region": "us-east-1",
  "central_api": "https://api.flexmon.io",
  "hmac_enabled": true,
  "ip_allowlist_enabled": true
}
```

### Statistics
```bash
curl http://localhost:8002/stats
```

Response:
```json
{
  "total_requests": 1250,
  "forwarded": 1200,
  "rate_limited": 45,
  "blocked": 5,
  "active_clients": 23,
  "region": "us-east-1"
}
```

### Forward Request
All other paths are forwarded to central API:

```bash
# Agent metrics ingestion
curl -X POST http://localhost:8002/v1/ingest/metrics/batch \
  -H "Content-Type: application/x-ndjson" \
  -H "Authorization: Bearer agent-token" \
  --data-binary @metrics.ndjson
```

## Rate Limiting

The gateway implements two levels of rate limiting:

### Global Rate Limit
- Limits total requests per minute across all clients
- Default: 1000 requests/minute
- Returns HTTP 429 when exceeded

### Per-IP Rate Limit
- Limits requests per client IP per minute
- Default: 100 requests/minute
- Returns HTTP 429 when exceeded

### Configuration Example

```bash
# Allow 5000 req/min globally, 200 req/min per IP
docker run -d \
  -e RATE_LIMIT_PER_MIN=5000 \
  -e RATE_LIMIT_PER_IP=200 \
  flexmon-gateway
```

## IP Allowlist

Restrict access to specific IPs or IP ranges:

### Exact IP Match
```bash
-e IP_ALLOWLIST=10.0.1.5,192.168.1.100
```

### Wildcard Match
```bash
-e IP_ALLOWLIST=10.0.*,192.168.1.*
```

### Mixed
```bash
-e IP_ALLOWLIST=10.0.0.0/8,192.168.*,172.16.1.50
```

**Note**: If `IP_ALLOWLIST` is not set or empty, all IPs are allowed.

## HMAC Signing

When enabled, the gateway signs forwarded requests with HMAC-SHA256:

### Enable HMAC
```bash
-e ENABLE_HMAC_SIGNING=true \
-e HMAC_SECRET=your-shared-secret-key
```

### Signature Header
The gateway adds:
```
X-Gateway-Signature: sha256=<hex-digest>
```

### Central API Verification
The central API should verify the signature:

```python
import hmac
import hashlib

def verify_gateway_signature(signature: str, body: bytes, secret: str) -> bool:
    sig_value = signature.replace("sha256=", "")
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(sig_value, expected)
```

## Gateway Headers

The gateway adds metadata headers to forwarded requests:

- `X-Gateway-Region`: Gateway region identifier
- `X-Forwarded-For`: Original client IP
- `X-Gateway-Timestamp`: Unix timestamp of forwarding
- `X-Gateway-Signature`: HMAC signature (if enabled)

## Retry Logic

The gateway implements exponential backoff retry:

1. **First attempt**: Immediate
2. **Second attempt**: Wait 1 second (2^0)
3. **Third attempt**: Wait 2 seconds (2^1)
4. **Fourth attempt**: Wait 4 seconds (2^2)

After all retries fail, returns HTTP 503.

### Configure Retries
```bash
-e MAX_RETRIES=5 \
-e TIMEOUT_SECONDS=60
```

## Production Deployment

### Multiple Regions

Deploy gateways in multiple regions:

```yaml
# us-east-1
services:
  gateway-east:
    image: flexmon-gateway
    environment:
      - GATEWAY_REGION=us-east-1
      - CENTRAL_API_URL=https://api.flexmon.io

# us-west-2
services:
  gateway-west:
    image: flexmon-gateway
    environment:
      - GATEWAY_REGION=us-west-2
      - CENTRAL_API_URL=https://api.flexmon.io

# eu-central-1
services:
  gateway-eu:
    image: flexmon-gateway
    environment:
      - GATEWAY_REGION=eu-central-1
      - CENTRAL_API_URL=https://api.flexmon.io
```

### Load Balancer

Use nginx or HAProxy to load balance across gateways:

```nginx
upstream flexmon_gateways {
    server gateway-1:8002;
    server gateway-2:8002;
    server gateway-3:8002;
}

server {
    listen 80;
    location / {
        proxy_pass http://flexmon_gateways;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

### Monitoring

Monitor gateway health and statistics:

```bash
# Prometheus-style metrics (coming soon)
curl http://gateway:8002/metrics

# Current statistics
watch -n 5 'curl -s http://gateway:8002/stats | jq'
```

### Logging

Gateway logs include:
- Request forwarding (INFO level)
- Rate limiting events (WARNING level)
- IP blocking events (WARNING level)
- Retry attempts (WARNING level)
- Errors (ERROR level)

View logs:
```bash
docker logs -f flexmon-gateway
```

## Security Considerations

1. **HMAC Secret**: Use a strong, randomly generated secret
2. **IP Allowlist**: Restrict to known agent networks
3. **TLS**: Deploy behind TLS termination (nginx, ALB, etc.)
4. **Rate Limits**: Tune based on expected agent count
5. **Network Isolation**: Deploy in private subnet, expose via load balancer

## Troubleshooting

### Gateway returns 429 Too Many Requests
- Check rate limits with `/stats` endpoint
- Increase `RATE_LIMIT_PER_MIN` or `RATE_LIMIT_PER_IP`
- Verify agents aren't sending excessive requests

### Gateway returns 403 Forbidden
- Client IP not in allowlist
- Check IP with: `curl http://gateway:8002/health` from client
- Add client IP to `IP_ALLOWLIST`

### Gateway returns 503 Service Unavailable
- Central API is down or unreachable
- Check `CENTRAL_API_URL` is correct
- Verify network connectivity to central API
- Check central API health

### Requests not forwarded
- Check gateway logs: `docker logs flexmon-gateway`
- Verify central API is reachable: `curl $CENTRAL_API_URL/health`
- Check for rate limiting or IP blocking

## Performance

Benchmarked performance (Python 3.11, uvicorn, single worker):

- **Throughput**: ~2000 req/s (no HMAC), ~1800 req/s (with HMAC)
- **Latency**: < 5ms added latency (local network)
- **Memory**: ~50MB base, +1MB per 1000 active clients

For higher throughput:
- Deploy multiple gateway instances
- Use load balancer for distribution
- Consider upgrading to `uvicorn` with `--workers` flag

## Support

- Documentation: https://docs.flexmon.io/gateway
- Issues: https://github.com/flexmon/flexmon/issues
- Community: https://community.flexmon.io
