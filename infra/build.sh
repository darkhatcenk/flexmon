#!/bin/bash
set -e

echo "=========================================="
echo "FlexMON Build Script"
echo "=========================================="
echo ""

# Color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Build backend API
echo -e "${YELLOW}Building backend API...${NC}"
cd ../backend/api
docker build -t flexmon-api:latest .
echo -e "${GREEN}✓ Backend API built${NC}"
echo ""

# Build license API
echo -e "${YELLOW}Building license API...${NC}"
cd ../license-api
docker build -t flexmon-license-api:latest .
echo -e "${GREEN}✓ License API built${NC}"
echo ""

# Build agent
echo -e "${YELLOW}Building agent...${NC}"
cd ../../agent
docker build -t flexmon-agent:latest .
echo -e "${GREEN}✓ Agent built${NC}"
echo ""

# Build gateway
echo -e "${YELLOW}Building gateway...${NC}"
cd ../gateway
docker build -t flexmon-gateway:latest .
echo -e "${GREEN}✓ Gateway built${NC}"
echo ""

# Build frontend
echo -e "${YELLOW}Building frontend...${NC}"
cd ../frontend
docker build -t flexmon-frontend:latest .
echo -e "${GREEN}✓ Frontend built${NC}"
echo ""

cd ../infra

echo "=========================================="
echo "Build Complete!"
echo "=========================================="
echo ""
echo "All Docker images have been built successfully."
echo ""
echo "Run 'make up' to start all services."
echo ""
