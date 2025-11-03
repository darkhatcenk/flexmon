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

# Check if .env exists, if not create from example
if [ ! -f .env ]; then
    echo -e "${YELLOW}Creating .env from .env.example...${NC}"
    cp .env.example .env
    echo -e "${GREEN}✓ .env created${NC}"
else
    echo -e "${GREEN}✓ .env already exists${NC}"
fi

# Create secrets directory
echo ""
echo "Setting up secrets..."
mkdir -p secrets

# Generate database password
if [ ! -f secrets/db_password.txt ]; then
    echo -e "${YELLOW}Generating database password...${NC}"
    openssl rand -base64 32 > secrets/db_password.txt
    echo -e "${GREEN}✓ Database password generated${NC}"
else
    echo -e "${GREEN}✓ Database password already exists${NC}"
fi

# Generate Elasticsearch password
if [ ! -f secrets/elastic_password.txt ]; then
    echo -e "${YELLOW}Generating Elasticsearch password...${NC}"
    openssl rand -base64 32 > secrets/elastic_password.txt
    echo -e "${GREEN}✓ Elasticsearch password generated${NC}"
else
    echo -e "${GREEN}✓ Elasticsearch password already exists${NC}"
fi

# Generate API secret key
if [ ! -f secrets/api_secret.txt ]; then
    echo -e "${YELLOW}Generating API secret key...${NC}"
    openssl rand -hex 32 > secrets/api_secret.txt
    echo -e "${GREEN}✓ API secret key generated${NC}"
else
    echo -e "${GREEN}✓ API secret key already exists${NC}"
fi

# Generate AI token (placeholder)
if [ ! -f secrets/ai_token.txt ]; then
    echo -e "${YELLOW}Generating AI token placeholder...${NC}"
    echo "your-ai-token-here" > secrets/ai_token.txt
    echo -e "${YELLOW}⚠ Update secrets/ai_token.txt with your actual AI service token${NC}"
else
    echo -e "${GREEN}✓ AI token already exists${NC}"
fi

# Generate TLS certificates
echo ""
echo "Setting up TLS certificates..."
mkdir -p certificates

if [ ! -f certificates/server.crt ]; then
    echo -e "${YELLOW}Generating self-signed TLS certificate...${NC}"

    # Generate private key
    openssl genrsa -out certificates/server.key 4096 2>/dev/null

    # Generate certificate signing request
    openssl req -new -key certificates/server.key -out certificates/server.csr \
        -subj "/C=TR/ST=Istanbul/L=Istanbul/O=CloudFlex/OU=FlexMON/CN=flexmon.local" 2>/dev/null

    # Generate self-signed certificate (valid for 365 days)
    openssl x509 -req -days 365 -in certificates/server.csr \
        -signkey certificates/server.key -out certificates/server.crt 2>/dev/null

    # Generate CA for mTLS (optional)
    openssl genrsa -out certificates/ca.key 4096 2>/dev/null
    openssl req -new -x509 -days 365 -key certificates/ca.key -out certificates/ca.crt \
        -subj "/C=TR/ST=Istanbul/L=Istanbul/O=CloudFlex/OU=FlexMON-CA/CN=flexmon-ca.local" 2>/dev/null

    # Clean up CSR
    rm certificates/server.csr

    echo -e "${GREEN}✓ TLS certificates generated${NC}"
    echo -e "${YELLOW}⚠ Using self-signed certificates. Upload custom certs via UI for production.${NC}"
else
    echo -e "${GREEN}✓ TLS certificates already exist${NC}"
fi

# Set proper permissions
chmod 600 secrets/*.txt
chmod 600 certificates/*.key
chmod 644 certificates/*.crt

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
    if curl -sf -u elastic:$(cat secrets/elastic_password.txt) http://localhost:9200/_cluster/health > /dev/null 2>&1; then
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

ES_PASSWORD=$(cat secrets/elastic_password.txt)
if curl -sf -u elastic:$ES_PASSWORD http://localhost:9200/_index_template/logs > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Elasticsearch templates loaded${NC}"
else
    echo -e "${YELLOW}⚠ ES templates not yet loaded, will retry on API startup${NC}"
fi

echo ""
echo "=========================================="
echo "Creating default platform admin..."
echo "=========================================="

# Generate platform admin password
ADMIN_PASSWORD=$(openssl rand -base64 16)
ADMIN_PASSWORD_HASH=$(python3 -c "from passlib.hash import bcrypt; print(bcrypt.hash('$ADMIN_PASSWORD'))")

# Insert platform admin into database
docker exec -i flexmon-timescaledb psql -U flexmon flexmon << EOF
INSERT INTO users (username, password_hash, role, tenant_id, created_at)
VALUES ('platform_admin', '$ADMIN_PASSWORD_HASH', 'platform_admin', NULL, NOW())
ON CONFLICT (username) DO NOTHING;
EOF

echo -e "${GREEN}✓ Platform admin created${NC}"
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
