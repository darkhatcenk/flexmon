.PHONY: help up down restart logs health seed demo clean build install

# Default target
help:
	@echo "FlexMON Infrastructure Commands"
	@echo "================================"
	@echo "make install    - First-time setup (generates secrets, certs, migrations)"
	@echo "make build      - Build all Docker images"
	@echo "make up         - Start all services"
	@echo "make down       - Stop all services"
	@echo "make restart    - Restart all services"
	@echo "make logs       - Tail all service logs"
	@echo "make health     - Check service health"
	@echo "make seed       - Load default alert rules"
	@echo "make demo       - Load demo data (metrics and logs)"
	@echo "make clean      - Remove all volumes and data (WARNING: destructive)"
	@echo "make gateway-up - Start with optional gateway service"

# First-time installation
install:
	@echo "Running FlexMON installation..."
	@bash install.sh

# Build all images
build:
	@echo "Building all Docker images..."
	@docker-compose -f docker-compose.yml build

# Start all services
up:
	@echo "Starting FlexMON services..."
	@docker-compose -f docker-compose.yml up -d
	@echo "Waiting for services to be healthy..."
	@sleep 10
	@make health

# Start with gateway
gateway-up:
	@echo "Starting FlexMON with gateway..."
	@docker-compose -f docker-compose.yml --profile gateway up -d

# Stop all services
down:
	@echo "Stopping FlexMON services..."
	@docker-compose -f docker-compose.yml down

# Restart all services
restart:
	@make down
	@make up

# View logs
logs:
	@docker-compose -f docker-compose.yml logs -f

# Check health of all services
health:
	@echo "Checking service health..."
	@echo ""
	@echo "TimescaleDB:"
	@docker exec flexmon-timescaledb pg_isready -U flexmon || echo "❌ TimescaleDB not ready"
	@echo ""
	@echo "Elasticsearch:"
	@curl -sf http://localhost:9200/_cluster/health?pretty || echo "❌ Elasticsearch not ready"
	@echo ""
	@echo "API:"
	@curl -sf http://localhost:8000/v1/health || echo "❌ API not ready"
	@echo ""
	@echo "License API:"
	@curl -sf http://localhost:8001/health || echo "❌ License API not ready"
	@echo ""
	@echo "Frontend:"
	@curl -sf http://localhost:3000 > /dev/null && echo "✅ Frontend ready" || echo "❌ Frontend not ready"

# Load default alert rules
seed:
	@echo "Loading default alert rules..."
	@bash -c 'curl -X POST http://localhost:8000/v1/alerts/rules/batch \
		-H "Content-Type: application/json" \
		-d @seed/alerts/default_rules.json'

# Load demo data
demo:
	@echo "Loading demo metrics..."
	@bash -c 'curl -X POST http://localhost:8000/v1/ingest/metrics/batch \
		-H "Content-Type: application/x-ndjson" \
		--data-binary @seed/demo/demo_metrics.ndjson'
	@echo ""
	@echo "Loading demo logs..."
	@bash -c 'curl -X POST http://localhost:8000/v1/logs/bulk \
		-H "Content-Type: application/x-ndjson" \
		--data-binary @seed/demo/demo_logs.ndjson'
	@echo ""
	@echo "Demo data loaded successfully!"

# Clean everything (WARNING: destroys all data)
clean:
	@echo "⚠️  WARNING: This will delete all data!"
	@read -p "Are you sure? (yes/no): " confirm && [ "$$confirm" = "yes" ] || exit 1
	@make down
	@docker-compose -f docker-compose.yml down -v
	@rm -rf secrets/
	@rm -rf certificates/*.crt certificates/*.key certificates/*.pem
	@echo "All data cleaned."

# Database backup
backup:
	@echo "Creating database backup..."
	@docker exec flexmon-timescaledb pg_dump -U flexmon flexmon > backup_$(shell date +%Y%m%d_%H%M%S).sql
	@echo "Backup created: backup_$(shell date +%Y%m%d_%H%M%S).sql"

# Database restore
restore:
	@if [ -z "$(file)" ]; then echo "Usage: make restore file=backup.sql"; exit 1; fi
	@echo "Restoring database from $(file)..."
	@docker exec -i flexmon-timescaledb psql -U flexmon flexmon < $(file)
	@echo "Database restored."
