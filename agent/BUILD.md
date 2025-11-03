# FlexMON Agent - Build Instructions

The FlexMON agent is a cross-platform monitoring agent written in Go that supports Windows, Linux, and macOS.

## Prerequisites

- Go 1.21 or higher
- Make (optional, for convenience)
- Docker (for containerized builds)

## Quick Start

### Build for Current Platform

```bash
cd agent
go build -o flexmon-agent ./cmd/flexmon-agent
```

## Cross-Platform Builds

### Build for Linux (amd64)

```bash
GOOS=linux GOARCH=amd64 go build -o flexmon-agent-linux-amd64 ./cmd/flexmon-agent
```

### Build for Linux (arm64)

```bash
GOOS=linux GOARCH=arm64 go build -o flexmon-agent-linux-arm64 ./cmd/flexmon-agent
```

### Build for Windows (amd64)

```bash
GOOS=windows GOARCH=amd64 go build -o flexmon-agent-windows-amd64.exe ./cmd/flexmon-agent
```

### Build for macOS (amd64)

```bash
GOOS=darwin GOARCH=amd64 go build -o flexmon-agent-darwin-amd64 ./cmd/flexmon-agent
```

### Build for macOS (arm64 - Apple Silicon)

```bash
GOOS=darwin GOARCH=arm64 go build -o flexmon-agent-darwin-arm64 ./cmd/flexmon-agent
```

## Build All Platforms at Once

Create a simple build script `build-all.sh`:

```bash
#!/bin/bash

# Build all platforms
echo "Building for all platforms..."

# Linux
GOOS=linux GOARCH=amd64 go build -o dist/flexmon-agent-linux-amd64 ./cmd/flexmon-agent
GOOS=linux GOARCH=arm64 go build -o dist/flexmon-agent-linux-arm64 ./cmd/flexmon-agent

# Windows
GOOS=windows GOARCH=amd64 go build -o dist/flexmon-agent-windows-amd64.exe ./cmd/flexmon-agent

# macOS
GOOS=darwin GOARCH=amd64 go build -o dist/flexmon-agent-darwin-amd64 ./cmd/flexmon-agent
GOOS=darwin GOARCH=arm64 go build -o dist/flexmon-agent-darwin-arm64 ./cmd/flexmon-agent

echo "Build complete! Binaries in dist/"
```

Make it executable and run:

```bash
chmod +x build-all.sh
./build-all.sh
```

## Docker Build

### Build Docker Image

```bash
cd agent
docker build -t flexmon-agent:latest .
```

### Run Agent in Docker

```bash
docker run -d \
  --name flexmon-agent \
  -e TENANT_ID=my-tenant \
  -e API_ENDPOINT=http://api.example.com \
  -e AGENT_TOKEN=your-token-here \
  flexmon-agent:latest
```

## Configuration

The agent is configured via environment variables:

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `TENANT_ID` | Tenant identifier | `default` | Yes |
| `API_ENDPOINT` | FlexMON API URL | `http://localhost:8000` | Yes |
| `AGENT_TOKEN` | Authentication token | - | Yes |
| `COLLECTION_INTERVAL` | Metrics collection interval (10-300s) | `30` | No |
| `ES_ENDPOINT` | Elasticsearch URL for logs | `http://localhost:9200` | No |
| `XMPP_SERVER` | XMPP server address | - | No |
| `XMPP_JID` | XMPP JID for metrics publishing | - | No |
| `XMPP_PASSWORD` | XMPP password | - | No |
| `USE_XMPP` | Enable XMPP publishing (true/false) | `false` | No |
| `ENABLE_TLS` | Enable TLS verification | `false` | No |

## Running the Agent

### Linux/macOS

```bash
export TENANT_ID=my-tenant
export API_ENDPOINT=https://flexmon.example.com
export AGENT_TOKEN=your-token
export COLLECTION_INTERVAL=30

./flexmon-agent
```

### Windows (PowerShell)

```powershell
$env:TENANT_ID="my-tenant"
$env:API_ENDPOINT="https://flexmon.example.com"
$env:AGENT_TOKEN="your-token"
$env:COLLECTION_INTERVAL="30"

.\flexmon-agent-windows-amd64.exe
```

### Windows (CMD)

```cmd
set TENANT_ID=my-tenant
set API_ENDPOINT=https://flexmon.example.com
set AGENT_TOKEN=your-token
set COLLECTION_INTERVAL=30

flexmon-agent-windows-amd64.exe
```

## Systemd Service (Linux)

Create `/etc/systemd/system/flexmon-agent.service`:

```ini
[Unit]
Description=FlexMON Monitoring Agent
After=network.target

[Service]
Type=simple
User=flexmon
Environment="TENANT_ID=my-tenant"
Environment="API_ENDPOINT=https://flexmon.example.com"
Environment="AGENT_TOKEN=your-token"
Environment="COLLECTION_INTERVAL=30"
ExecStart=/usr/local/bin/flexmon-agent
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable flexmon-agent
sudo systemctl start flexmon-agent
sudo systemctl status flexmon-agent
```

## Windows Service

Use [NSSM](https://nssm.cc/) (Non-Sucking Service Manager):

```cmd
nssm install FlexMONAgent "C:\Program Files\FlexMON\flexmon-agent.exe"
nssm set FlexMONAgent AppEnvironmentExtra TENANT_ID=my-tenant
nssm set FlexMONAgent AppEnvironmentExtra API_ENDPOINT=https://flexmon.example.com
nssm set FlexMONAgent AppEnvironmentExtra AGENT_TOKEN=your-token
nssm start FlexMONAgent
```

## macOS LaunchAgent

Create `~/Library/LaunchAgents/com.flexmon.agent.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.flexmon.agent</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/local/bin/flexmon-agent</string>
    </array>
    <key>EnvironmentVariables</key>
    <dict>
        <key>TENANT_ID</key>
        <string>my-tenant</string>
        <key>API_ENDPOINT</key>
        <string>https://flexmon.example.com</string>
        <key>AGENT_TOKEN</key>
        <string>your-token</string>
        <key>COLLECTION_INTERVAL</key>
        <string>30</string>
    </dict>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
</dict>
</plist>
```

Load and start:

```bash
launchctl load ~/Library/LaunchAgents/com.flexmon.agent.plist
launchctl start com.flexmon.agent
```

## Features

### Metrics Collection

The agent collects the following metrics:

- **CPU**: percent, user, system, idle, iowait
- **Memory**: total, used, free, percent, swap stats
- **Disk**: per-partition usage (total, used, free, percent)
- **Network**: per-interface I/O stats (bytes, packets, errors, drops)
- **Processes**: top 10 by CPU (pid, name, cpu%, memory%, RSS, VMS)
- **USB Devices**: connected USB devices
- **Host Info**: OS, platform, kernel, uptime, boot time, process count

### Fingerprinting

The agent generates a unique fingerprint based on:
- Hostname
- Machine UUID
- Primary MAC address
- Primary IP address

### XMPP Publishing

When enabled, the agent publishes metrics via XMPP to:
```
metrics.<tenant_id>.<hostname>
```

If XMPP fails, it automatically falls back to HTTP POST.

### Exponential Backoff

Network failures trigger exponential backoff:
- Initial: 1 second
- Doubles on each failure
- Maximum: 300 seconds (5 minutes)
- Resets on success

### Server-Side Configuration

The agent pulls configuration from the server on each collection cycle:
- `collection_interval_sec`: Override collection interval (10-300s)
- `ignore_logs`: Disable log sending
- `ignore_alerts`: Disable alert processing (future use)

### Demo Values

When OS APIs are unavailable or fail, the agent uses demo values to ensure continuous operation. This is particularly useful during development or in restricted environments.

## Troubleshooting

### Agent won't start

- Check environment variables are set correctly
- Verify API_ENDPOINT is reachable
- Ensure AGENT_TOKEN is valid

### No metrics appearing

- Check agent logs for errors
- Verify tenant is enabled and licensed
- Check network connectivity to API endpoint
- Verify firewall allows outbound connections

### XMPP connection fails

- Verify XMPP credentials are correct
- Check XMPP server is reachable
- Agent will fall back to HTTP automatically

### High CPU usage

- Consider increasing COLLECTION_INTERVAL
- Check for excessive logging
- Verify process enumeration isn't too frequent

## Development

### Running Tests

```bash
go test ./...
```

### Running with Verbose Logging

```bash
./flexmon-agent 2>&1 | tee agent.log
```

### Updating Dependencies

```bash
go get -u ./...
go mod tidy
```

## Support

For issues and questions:
- GitHub Issues: https://github.com/flexmon/flexmon
- Documentation: https://docs.flexmon.io
- Community: https://community.flexmon.io
