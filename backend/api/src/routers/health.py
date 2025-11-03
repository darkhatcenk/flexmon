"""
Health check endpoint
"""
from fastapi import APIRouter
from datetime import datetime
from ..models import HealthCheck
from ..version import VERSION_INFO
from ..services import timescale, elastic

router = APIRouter()


@router.get("/health", response_model=HealthCheck)
async def health_check():
    """
    Health check endpoint - returns status of all services
    """
    services = {}

    # Check TimescaleDB
    try:
        await timescale.execute_query("SELECT 1")
        services["timescaledb"] = "healthy"
    except Exception as e:
        services["timescaledb"] = f"unhealthy: {str(e)}"

    # Check Elasticsearch
    try:
        es_health = await elastic.get_cluster_health()
        services["elasticsearch"] = es_health.get("status", "unknown")
    except Exception as e:
        services["elasticsearch"] = f"unhealthy: {str(e)}"

    # Overall status
    all_healthy = all("unhealthy" not in str(v) for v in services.values())
    status = "healthy" if all_healthy else "degraded"

    return HealthCheck(
        status=status,
        version=VERSION_INFO["version"],
        timestamp=datetime.utcnow(),
        services=services
    )
