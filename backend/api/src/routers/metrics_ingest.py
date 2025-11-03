"""
Metrics ingestion endpoint
Handles batch metrics from agents (JSON Lines format)
"""
from fastapi import APIRouter, HTTPException, status, Depends, Request
from typing import List
import json
from datetime import datetime
from ..deps.security import get_current_user
from ..deps.tenancy import get_tenant_id
from ..services import timescale
from ..config import settings

router = APIRouter()


@router.post("/ingest/metrics/batch")
async def ingest_metrics_batch(
    request: Request,
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """
    Ingest batch of metrics in JSON Lines format
    Max size: 15 MB / 3000 records
    Enforces license validation - blocks unlicensed tenants
    """
    # Check tenant license status
    tenant_check = await timescale.fetch_one(
        """
        SELECT enabled, license_expires_at, grace_period_until
        FROM tenants WHERE id = $1
        """,
        tenant_id
    )

    if not tenant_check:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant not found"
        )

    if not tenant_check["enabled"]:
        # Check if grace period is still valid
        from datetime import datetime as dt
        grace_until = tenant_check.get("grace_period_until")
        if not grace_until or dt.utcnow() > grace_until:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail="Tenant license expired. Metrics ingestion blocked."
            )

    # Check content type
    if request.headers.get("content-type") != "application/x-ndjson":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Content-Type must be application/x-ndjson"
        )

    # Read body
    body = await request.body()

    # Check size limit
    size_mb = len(body) / (1024 * 1024)
    if size_mb > settings.metrics_batch_max_size_mb:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Batch size exceeds {settings.metrics_batch_max_size_mb} MB"
        )

    # Parse NDJSON
    lines = body.decode("utf-8").strip().split("\n")

    if len(lines) > settings.metrics_batch_max_records:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Batch exceeds {settings.metrics_batch_max_records} records"
        )

    # Separate metrics by type
    cpu_metrics = []
    memory_metrics = []
    disk_metrics = []
    network_metrics = []
    process_metrics = []

    for line in lines:
        if not line.strip():
            continue

        try:
            record = json.loads(line)
        except json.JSONDecodeError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid JSON: {str(e)}"
            )

        # Validate tenant_id matches
        if record.get("tenant_id") != tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tenant ID mismatch"
            )

        # Route by metric type
        metric_type = record.get("metric_type")

        if metric_type == "cpu":
            cpu_metrics.append(record)
        elif metric_type == "memory":
            memory_metrics.append(record)
        elif metric_type == "disk":
            disk_metrics.append(record)
        elif metric_type == "network":
            network_metrics.append(record)
        elif metric_type == "process":
            process_metrics.append(record)

    # Insert metrics in batches
    inserted_count = 0

    if cpu_metrics:
        await _insert_cpu_metrics(cpu_metrics)
        inserted_count += len(cpu_metrics)

    if memory_metrics:
        await _insert_memory_metrics(memory_metrics)
        inserted_count += len(memory_metrics)

    if disk_metrics:
        await _insert_disk_metrics(disk_metrics)
        inserted_count += len(disk_metrics)

    if network_metrics:
        await _insert_network_metrics(network_metrics)
        inserted_count += len(network_metrics)

    if process_metrics:
        await _insert_process_metrics(process_metrics)
        inserted_count += len(process_metrics)

    # Update agent last_seen timestamp for all unique hosts
    unique_hosts = set()
    for metrics_list in [cpu_metrics, memory_metrics, disk_metrics, network_metrics, process_metrics]:
        for m in metrics_list:
            unique_hosts.add(m.get("host"))

    for host in unique_hosts:
        await timescale.execute_query(
            """
            UPDATE agents
            SET last_seen = NOW()
            WHERE tenant_id = $1 AND hostname = $2
            """,
            tenant_id,
            host
        )

    return {
        "message": "Metrics ingested successfully",
        "count": inserted_count,
        "breakdown": {
            "cpu": len(cpu_metrics),
            "memory": len(memory_metrics),
            "disk": len(disk_metrics),
            "network": len(network_metrics),
            "process": len(process_metrics)
        }
    }


async def _insert_cpu_metrics(metrics: List[dict]):
    """Insert CPU metrics"""
    query = """
        INSERT INTO metrics_cpu (timestamp, tenant_id, host, cpu_percent, cpu_user, cpu_system, cpu_idle, cpu_iowait)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
    """

    for m in metrics:
        await timescale.execute_query(
            query,
            m.get("timestamp", datetime.utcnow()),
            m["tenant_id"],
            m["host"],
            m.get("cpu_percent"),
            m.get("cpu_user"),
            m.get("cpu_system"),
            m.get("cpu_idle"),
            m.get("cpu_iowait", 0.0)
        )


async def _insert_memory_metrics(metrics: List[dict]):
    """Insert memory metrics"""
    query = """
        INSERT INTO metrics_memory (timestamp, tenant_id, host, memory_total, memory_used, memory_free, memory_percent, swap_total, swap_used, swap_free, swap_percent)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
    """

    for m in metrics:
        await timescale.execute_query(
            query,
            m.get("timestamp", datetime.utcnow()),
            m["tenant_id"],
            m["host"],
            m.get("memory_total"),
            m.get("memory_used"),
            m.get("memory_free"),
            m.get("memory_percent"),
            m.get("swap_total"),
            m.get("swap_used"),
            m.get("swap_free"),
            m.get("swap_percent")
        )


async def _insert_disk_metrics(metrics: List[dict]):
    """Insert disk metrics"""
    query = """
        INSERT INTO metrics_disk (timestamp, tenant_id, host, device, mountpoint, total_bytes, used_bytes, free_bytes, percent)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
    """

    for m in metrics:
        await timescale.execute_query(
            query,
            m.get("timestamp", datetime.utcnow()),
            m["tenant_id"],
            m["host"],
            m.get("device"),
            m.get("mountpoint"),
            m.get("total"),
            m.get("used"),
            m.get("free"),
            m.get("percent")
        )


async def _insert_network_metrics(metrics: List[dict]):
    """Insert network metrics"""
    query = """
        INSERT INTO metrics_network (timestamp, tenant_id, host, interface, bytes_sent, bytes_recv, packets_sent, packets_recv, errors_in, errors_out, drops_in, drops_out)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
    """

    for m in metrics:
        await timescale.execute_query(
            query,
            m.get("timestamp", datetime.utcnow()),
            m["tenant_id"],
            m["host"],
            m.get("interface"),
            m.get("bytes_sent"),
            m.get("bytes_recv"),
            m.get("packets_sent"),
            m.get("packets_recv"),
            m.get("errors_in", 0),
            m.get("errors_out", 0),
            m.get("drops_in", 0),
            m.get("drops_out", 0)
        )


async def _insert_process_metrics(metrics: List[dict]):
    """Insert process metrics"""
    query = """
        INSERT INTO metrics_process (timestamp, tenant_id, host, pid, name, cpu_percent, memory_percent, status, username)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
    """

    for m in metrics:
        await timescale.execute_query(
            query,
            m.get("timestamp", datetime.utcnow()),
            m["tenant_id"],
            m["host"],
            m.get("pid"),
            m.get("name"),
            m.get("cpu_percent"),
            m.get("memory_percent"),
            m.get("status"),
            m.get("username")
        )


@router.get("/metrics/{metric_type}/query")
async def query_metrics(
    metric_type: str,
    host: str,
    start_time: datetime,
    end_time: datetime,
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """
    Query metrics for a specific host and time range
    """
    table_map = {
        "cpu": "metrics_cpu",
        "memory": "metrics_memory",
        "disk": "metrics_disk",
        "network": "metrics_network",
        "process": "metrics_process"
    }

    if metric_type not in table_map:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid metric type. Must be one of: {', '.join(table_map.keys())}"
        )

    table = table_map[metric_type]

    query = f"""
        SELECT *
        FROM {table}
        WHERE tenant_id = $1
        AND host = $2
        AND timestamp BETWEEN $3 AND $4
        ORDER BY timestamp DESC
        LIMIT 10000
    """

    results = await timescale.fetch_all(query, tenant_id, host, start_time, end_time)

    return {
        "metric_type": metric_type,
        "host": host,
        "start_time": start_time,
        "end_time": end_time,
        "count": len(results),
        "data": results
    }
