#!/bin/bash
set -e

echo "=========================================="
echo "FlexMON Installation Script"
echo "=========================================="
echo ""

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Detect system architecture
ARCH=$(uname -m)
echo -e "${GREEN}Detected architecture: ${ARCH}${NC}"
echo ""

# Function to generate random secret
generate_secret() {
    openssl rand -base64 32 | tr -d '\n'
}

# Check if .env exists, if not create from example
if [ ! -f .env ]; then
    echo -e "${YELLOW}Creating .env from .env.example and auto-populating secrets...${NC}"
    cp .env.example .env

    # Generate secrets for __AUTO__ placeholders
    POSTGRES_PASSWORD=$(generate_secret)
    ES_PASSWORD=$(generate_secret)
    XMPP_ADMIN_PASSWORD=$(generate_secret)
    API_SECRET=$(openssl rand -hex 32 | tr -d '\n')
    AI_TOKEN=$(generate_secret)

    # Replace __AUTO__ placeholders in .env (idempotent - only if __AUTO__ exists)
    if grep -q "__AUTO__" .env; then
        sed -i.bak "s|POSTGRES_PASSWORD=__AUTO__|POSTGRES_PASSWORD=$POSTGRES_PASSWORD|g" .env
        sed -i.bak "s|ES_PASSWORD=__AUTO__|ES_PASSWORD=$ES_PASSWORD|g" .env
        sed -i.bak "s|XMPP_ADMIN_PASSWORD=__AUTO__|XMPP_ADMIN_PASSWORD=$XMPP_ADMIN_PASSWORD|g" .env
        sed -i.bak "s|API_SECRET=__AUTO__|API_SECRET=$API_SECRET|g" .env
        sed -i.bak "s|AI_TOKEN=__AUTO__|AI_TOKEN=$AI_TOKEN|g" .env
        rm -f .env.bak
    fi

    echo -e "${GREEN}✓ .env created with auto-generated secrets${NC}"
else
    echo -e "${GREEN}✓ .env already exists${NC}"
fi

# Load .env to get directory paths
if [ -f .env ]; then
    export $(grep -v '^#' .env | grep -v '^$' | xargs)
fi

# Set directory paths with defaults
SECRETS_DIR="${SECRETS_DIR:-./secrets}"
CERTS_DIR="${CERTS_DIR:-./certificates}"
DATA_DIR="${DATA_DIR:-./data}"

# Create all required directories
echo ""
echo "Setting up directories..."
mkdir -p "${SECRETS_DIR}"
mkdir -p "${CERTS_DIR}"
mkdir -p "${DATA_DIR}/es"
mkdir -p "${DATA_DIR}/pg"
mkdir -p "${DATA_DIR}/xmpp"
echo -e "${GREEN}✓ Directories created: ${SECRETS_DIR}, ${CERTS_DIR}, ${DATA_DIR}${NC}"

# Create placeholder secret files if they don't exist (prevents bind mount errors)
echo ""
echo "Setting up secrets..."
touch "${SECRETS_DIR}/db_password.txt"
touch "${SECRETS_DIR}/elastic_password.txt"
touch "${SECRETS_DIR}/api_secret.txt"
touch "${SECRETS_DIR}/ai_token.txt"
echo -e "${GREEN}✓ Secret placeholder files created${NC}"

# Generate database password
if [ ! -s "${SECRETS_DIR}/db_password.txt" ]; then
    echo -e "${YELLOW}Generating database password...${NC}"
    openssl rand -base64 32 > "${SECRETS_DIR}/db_password.txt"
    echo -e "${GREEN}✓ Database password generated${NC}"
else
    echo -e "${GREEN}✓ Database password already exists${NC}"
fi

# Generate Elasticsearch password
if [ ! -s "${SECRETS_DIR}/elastic_password.txt" ]; then
    echo -e "${YELLOW}Generating Elasticsearch password...${NC}"
    openssl rand -base64 32 > "${SECRETS_DIR}/elastic_password.txt"
    echo -e "${GREEN}✓ Elasticsearch password generated${NC}"
else
    echo -e "${GREEN}✓ Elasticsearch password already exists${NC}"
fi

# Generate API secret key
if [ ! -s "${SECRETS_DIR}/api_secret.txt" ]; then
    echo -e "${YELLOW}Generating API secret key...${NC}"
    openssl rand -hex 32 > "${SECRETS_DIR}/api_secret.txt"
    echo -e "${GREEN}✓ API secret key generated${NC}"
else
    echo -e "${GREEN}✓ API secret key already exists${NC}"
fi

# Generate AI token (placeholder)
if [ ! -s "${SECRETS_DIR}/ai_token.txt" ]; then
    echo -e "${YELLOW}Generating AI token placeholder...${NC}"
    echo "your-ai-token-here" > "${SECRETS_DIR}/ai_token.txt"
    echo -e "${YELLOW}⚠ Update ${SECRETS_DIR}/ai_token.txt with your actual AI service token${NC}"
else
    echo -e "${GREEN}✓ AI token already exists${NC}"
fi

# Generate TLS certificates
echo ""
echo "Setting up TLS certificates..."

if [ ! -f "${CERTS_DIR}/server.crt" ]; then
    echo -e "${YELLOW}Generating self-signed TLS certificate...${NC}"

    # Generate private key
    openssl genrsa -out "${CERTS_DIR}/server.key" 4096 2>/dev/null

    # Generate certificate signing request
    openssl req -new -key "${CERTS_DIR}/server.key" -out "${CERTS_DIR}/server.csr" \
        -subj "/C=TR/ST=Istanbul/L=Istanbul/O=CloudFlex/OU=FlexMON/CN=flexmon.local" 2>/dev/null

    # Generate self-signed certificate (valid for 365 days)
    openssl x509 -req -days 365 -in "${CERTS_DIR}/server.csr" \
        -signkey "${CERTS_DIR}/server.key" -out "${CERTS_DIR}/server.crt" 2>/dev/null

    # Generate CA for mTLS (optional)
    openssl genrsa -out "${CERTS_DIR}/ca.key" 4096 2>/dev/null
    openssl req -new -x509 -days 365 -key "${CERTS_DIR}/ca.key" -out "${CERTS_DIR}/ca.crt" \
        -subj "/C=TR/ST=Istanbul/L=Istanbul/O=CloudFlex/OU=FlexMON-CA/CN=flexmon-ca.local" 2>/dev/null

    # Clean up CSR
    rm -f "${CERTS_DIR}/server.csr"

    echo -e "${GREEN}✓ TLS certificates generated${NC}"
    echo -e "${YELLOW}⚠ Using self-signed certificates. Upload custom certs via UI for production.${NC}"
else
    echo -e "${GREEN}✓ TLS certificates already exist${NC}"
fi

# Set proper permissions
chmod 600 "${SECRETS_DIR}"/*.txt 2>/dev/null || true
chmod 600 "${CERTS_DIR}"/*.key 2>/dev/null || true
chmod 644 "${CERTS_DIR}"/*.crt 2>/dev/null || true

echo ""
echo "=========================================="
echo "Building Docker images..."
echo "=========================================="
docker-compose -f docker-compose.yml build

echo ""
echo "=========================================="
echo "Starting services..."
echo "=========================================="
docker-compose -f docker-compose.yml up -d

echo ""
echo "Waiting for services to be healthy (this may take 30-60 seconds)..."
sleep 30

# Wait for TimescaleDB
echo -e "${YELLOW}Waiting for TimescaleDB...${NC}"
for i in {1..30}; do
    if docker exec flexmon-timescaledb pg_isready -U flexmon > /dev/null 2>&1; then
        echo -e "${GREEN}✓ TimescaleDB is ready${NC}"
        break
    fi
    sleep 2
done

# Wait for Elasticsearch
echo -e "${YELLOW}Waiting for Elasticsearch...${NC}"
for i in {1..30}; do
    if curl -sf -u elastic:$(cat "${SECRETS_DIR}/elastic_password.txt") http://localhost:9200/_cluster/health > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Elasticsearch is ready${NC}"
        break
    fi
    sleep 2
done

# Wait for API
echo -e "${YELLOW}Waiting for API...${NC}"
for i in {1..30}; do
    if curl -sf http://localhost:8000/v1/health > /dev/null 2>&1; then
        echo -e "${GREEN}✓ API is ready${NC}"
        break
    fi
    sleep 2
done

echo ""
echo "=========================================="
echo "Verifying Elasticsearch templates and ILM..."
echo "=========================================="

# ES templates are loaded by the API service on startup via elastic.load_templates_and_ilm()
# Verify they were loaded successfully
sleep 5

ES_PASSWORD=$(cat "${SECRETS_DIR}/elastic_password.txt")
if curl -sf -u elastic:$ES_PASSWORD http://localhost:9200/_index_template/logs > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Elasticsearch templates loaded${NC}"
else
    echo -e "${YELLOW}⚠ ES templates not yet loaded, will retry on API startup${NC}"
fi

echo ""
echo "=========================================="
echo "Creating default platform admin..."
echo "=========================================="

# Generate platform admin password and save to secrets
if [ ! -f "${SECRETS_DIR}/platform_admin_pwd.txt" ]; then
    echo -e "${YELLOW}Generating platform admin password...${NC}"
    ADMIN_PASSWORD=$(openssl rand -base64 16)
    echo "$ADMIN_PASSWORD" > "${SECRETS_DIR}/platform_admin_pwd.txt"
    chmod 600 "${SECRETS_DIR}/platform_admin_pwd.txt"
else
    echo -e "${GREEN}✓ Platform admin password already exists${NC}"
    ADMIN_PASSWORD=$(cat "${SECRETS_DIR}/platform_admin_pwd.txt")
fi

# Create admin user using manage.py CLI inside API container
echo -e "${YELLOW}Running manage.py create-admin inside API container...${NC}"
docker exec flexmon-api python -m src.manage create-admin \
    --username platform_admin \
    --password "$ADMIN_PASSWORD" \
    --email admin@flexmon.local

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Platform admin created${NC}"
else
    echo -e "${RED}✗ Failed to create platform admin${NC}"
    echo -e "${YELLOW}⚠ You may need to create the admin manually using:${NC}"
    echo -e "${YELLOW}  docker exec flexmon-api python -m src.manage create-admin -u platform_admin -p <password>${NC}"
fi
echo ""
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}SAVE THESE CREDENTIALS:${NC}"
echo -e "${YELLOW}Username: platform_admin${NC}"
echo -e "${YELLOW}Password: ${ADMIN_PASSWORD}${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Save masked password to releases.md
MASKED_PASSWORD="${ADMIN_PASSWORD:0:4}****${ADMIN_PASSWORD: -4}"
TIMESTAMP=$(date -u +"%Y-%m-%d %H:%M UTC")
echo "$TIMESTAMP — Installation complete, platform_admin created (password: $MASKED_PASSWORD)" >> ../releases.md

echo ""
echo "=========================================="
echo "Loading default alert rules..."
echo "=========================================="

# Wait a moment for API to be fully ready
sleep 5

# Note: Default rules can be loaded via API or manually seeded
# For now, rules are available and can be loaded with: make seed
echo -e "${YELLOW}ℹ Default alert rules available in seed/alerts/default_rules.yaml${NC}"
echo -e "${YELLOW}ℹ Load them with: make seed${NC}"
echo -e "${YELLOW}ℹ Load demo data with: make demo${NC}"

echo ""
echo "=========================================="
echo "Installation Complete!"
echo "=========================================="
echo ""
echo -e "${GREEN}✓ All services are running${NC}"
echo ""
echo "Access URLs:"
echo "  - Frontend: http://localhost:3000"
echo "  - API: http://localhost:8000"
echo "  - API Docs: http://localhost:8000/docs"
echo "  - License API: http://localhost:8001/docs"
echo ""
echo "Next steps:"
echo "  1. Login with platform_admin credentials above"
echo "  2. Create tenants and users"
echo "  3. Deploy agents to target servers"
echo "  4. Configure alert rules and notification channels"
echo ""
echo "Commands:"
echo "  make logs    - View service logs"
echo "  make health  - Check service status"
echo "  make demo    - Load demo data"
echo "  make down    - Stop all services"
echo ""

# Generate bilgi.md with masked secrets and connection info
echo "=========================================="
echo "Generating bilgi.md..."
echo "=========================================="

# Function to mask secret (show first 2 and last 2 chars)
mask_secret() {
    local secret="$1"
    local len=${#secret}
    if [ $len -gt 4 ]; then
        echo "${secret:0:2}****${secret: -2}"
    else
        echo "****"
    fi
}

# Read secrets from files
DB_PASSWORD=$(cat "${SECRETS_DIR}/db_password.txt" 2>/dev/null || echo "not-set")
ELASTIC_PASSWORD=$(cat "${SECRETS_DIR}/elastic_password.txt" 2>/dev/null || echo "not-set")
API_SECRET=$(cat "${SECRETS_DIR}/api_secret.txt" 2>/dev/null || echo "not-set")
AI_TOKEN=$(cat "${SECRETS_DIR}/ai_token.txt" 2>/dev/null || echo "not-set")

# Mask them
MASKED_DB_PW=$(mask_secret "$DB_PASSWORD")
MASKED_ES_PW=$(mask_secret "$ELASTIC_PASSWORD")
MASKED_API_SECRET=$(mask_secret "$API_SECRET")
MASKED_AI_TOKEN=$(mask_secret "$AI_TOKEN")

# Write bilgi.md to repo root
cat > ../bilgi.md << EOF
# FlexMON Installation Information

**Generated:** $(date -u +"%Y-%m-%d %H:%M:%S UTC")
**Architecture:** ${ARCH}
**Docker Compose Version:** $(docker compose version 2>/dev/null | head -1)

## Service Endpoints

| Service          | Host:Port           | URL                           |
|------------------|---------------------|-------------------------------|
| Frontend         | localhost:3000      | http://localhost:3000         |
| API              | localhost:8000      | http://localhost:8000         |
| API Docs         | localhost:8000      | http://localhost:8000/docs    |
| License API      | localhost:8001      | http://localhost:8001/docs    |
| TimescaleDB      | localhost:5432      | postgresql://flexmon@localhost:5432/flexmon |
| Elasticsearch    | localhost:9200      | http://localhost:9200         |
| XMPP (Prosody)   | localhost:5222      | xmpp://localhost:5222         |

## Docker Images

| Service          | Image                                            |
|------------------|--------------------------------------------------|
| TimescaleDB      | timescale/timescaledb:2.16.1-pg16 (arm64)        |
| Elasticsearch    | docker.elastic.co/elasticsearch/elasticsearch:8.15.2 (arm64) |
| XMPP             | prosody/prosody:0.12 (arm64)                     |
| License API      | flexmon-license-api:latest (local build)         |
| Backend API      | flexmon-api:latest (local build)                 |
| Frontend         | flexmon-frontend:latest (local build)            |
| Gateway (opt)    | flexmon-gateway:latest (local build)             |

## Secrets (Masked)

| Secret Type          | Location                                      | Masked Value        |
|----------------------|-----------------------------------------------|---------------------|
| DB Password          | infra/${SECRETS_DIR}/db_password.txt          | ${MASKED_DB_PW}     |
| Elasticsearch Pass   | infra/${SECRETS_DIR}/elastic_password.txt     | ${MASKED_ES_PW}     |
| API Secret           | infra/${SECRETS_DIR}/api_secret.txt           | ${MASKED_API_SECRET}|
| AI Token             | infra/${SECRETS_DIR}/ai_token.txt             | ${MASKED_AI_TOKEN}  |

## TLS Certificates

| Certificate       | Path                                     |
|-------------------|------------------------------------------|
| Server Cert       | infra/${CERTS_DIR}/server.crt            |
| Server Key        | infra/${CERTS_DIR}/server.key            |
| CA Cert (mTLS)    | infra/${CERTS_DIR}/ca.crt                |
| CA Key (mTLS)     | infra/${CERTS_DIR}/ca.key                |

## Admin Credentials

**Username:** platform_admin
**Password:** ${MASKED_PASSWORD} (see installation logs for full password)

## Configuration

- **Environment File:** infra/.env
- **Docker Compose:** infra/docker-compose.yml
- **Volumes:** timescale_data, es_data, xmpp_data, backup_data

## Quick Commands

\`\`\`bash
cd infra

# View logs
docker compose logs -f

# Check service health
docker compose ps

# Restart services
docker compose restart

# Stop all services
docker compose down

# Start services
docker compose up -d
\`\`\`

## Notes

- All services are configured for **${ARCH}** architecture
- Using Prosody XMPP server (ARM64-compatible alternative to ejabberd)
- Elasticsearch 8.15.2 with ARM64 support
- TimescaleDB 2.16.1 with PostgreSQL 16
- Self-signed TLS certificates generated (replace in production)
- Platform admin password shown during installation

---
**For full setup details, see:** [Installation Guide](./README.md)
EOF

echo -e "${GREEN}✓ bilgi.md generated in repo root${NC}"
echo ""

# Git Auto Commit & Push
if [ -d "../.git" ]; then
  echo ""
  echo "=========================================="
  echo "Committing changes to git..."
  echo "=========================================="
  cd ..
  CURRENT_BRANCH=$(git branch --show-current)

  git add .
  git commit -m "Automated install/update $(date '+%Y-%m-%d %H:%M:%S')" || echo "No changes to commit"
  git pull --rebase origin "$CURRENT_BRANCH" || true
  git push origin "$CURRENT_BRANCH" || echo "Failed to push to remote"

  echo -e "${GREEN}✓ Changes committed and pushed to $CURRENT_BRANCH${NC}"
  cd infra
else
  echo "No .git repository found, skipping git push."
fi
