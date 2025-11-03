"""
External webhook endpoints for Zabbix, Alertmanager, etc.
"""
from fastapi import APIRouter, HTTPException, status, Request, Header
from typing import Optional
import json
import hashlib
from ..services import timescale
from ..deps.security import verify_webhook_hmac
from ..config import settings

router = APIRouter()


@router.post("/webhooks/zabbix")
async def zabbix_webhook(
    request: Request,
    x_webhook_signature: Optional[str] = Header(None)
):
    """
    Zabbix webhook endpoint (with HMAC validation)
    """
    body = await request.body()

    # Verify HMAC if signature provided
    if x_webhook_signature:
        if not verify_webhook_hmac(x_webhook_signature, body, settings.api_secret_key):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid webhook signature"
            )

    # Parse Zabbix payload
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload"
        )

    # Extract alert information
    tenant_id = payload.get("tenant_id", "default")
    host = payload.get("host", "unknown")
    severity = payload.get("severity", "warning")
    message = payload.get("message", "Alert from Zabbix")

    # Generate fingerprint for deduplication
    fingerprint = hashlib.sha256(
        f"zabbix:{tenant_id}:{host}:{message}".encode()
    ).hexdigest()

    # Insert into alerts_external
    query = """
        INSERT INTO alerts_external (source, tenant_id, host, severity, message, raw_payload, fingerprint)
        VALUES ($1, $2, $3, $4, $5, $6, $7)
        ON CONFLICT (fingerprint) DO UPDATE
        SET received_at = NOW()
        RETURNING id
    """

    result = await timescale.fetch_one(
        query,
        "zabbix",
        tenant_id,
        host,
        severity,
        message,
        payload,
        fingerprint
    )

    return {
        "message": "Webhook received",
        "alert_id": result["id"],
        "source": "zabbix"
    }


@router.post("/webhooks/alertmanager")
async def alertmanager_webhook(request: Request):
    """
    Prometheus Alertmanager webhook endpoint
    """
    body = await request.body()

    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload"
        )

    # Process Alertmanager alerts
    alerts = payload.get("alerts", [])
    inserted_ids = []

    for alert in alerts:
        labels = alert.get("labels", {})
        annotations = alert.get("annotations", {})

        tenant_id = labels.get("tenant_id", "default")
        host = labels.get("instance", "unknown")
        severity = labels.get("severity", "warning")
        message = annotations.get("summary", alert.get("status", "Alert"))

        fingerprint = hashlib.sha256(
            f"alertmanager:{tenant_id}:{host}:{message}".encode()
        ).hexdigest()

        query = """
            INSERT INTO alerts_external (source, tenant_id, host, severity, message, raw_payload, fingerprint)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            ON CONFLICT (fingerprint) DO UPDATE
            SET received_at = NOW()
            RETURNING id
        """

        result = await timescale.fetch_one(
            query,
            "alertmanager",
            tenant_id,
            host,
            severity,
            message,
            alert,
            fingerprint
        )

        inserted_ids.append(result["id"])

    return {
        "message": "Webhooks received",
        "count": len(inserted_ids),
        "alert_ids": inserted_ids,
        "source": "alertmanager"
    }


@router.post("/webhooks/generic")
async def generic_webhook(request: Request):
    """
    Generic webhook endpoint for custom integrations
    """
    body = await request.body()

    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload"
        )

    # Extract required fields
    tenant_id = payload.get("tenant_id")
    host = payload.get("host")
    severity = payload.get("severity", "info")
    message = payload.get("message")

    if not all([tenant_id, host, message]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing required fields: tenant_id, host, message"
        )

    fingerprint = hashlib.sha256(
        f"generic:{tenant_id}:{host}:{message}".encode()
    ).hexdigest()

    query = """
        INSERT INTO alerts_external (source, tenant_id, host, severity, message, raw_payload, fingerprint)
        VALUES ($1, $2, $3, $4, $5, $6, $7)
        ON CONFLICT (fingerprint) DO UPDATE
        SET received_at = NOW()
        RETURNING id
    """

    result = await timescale.fetch_one(
        query,
        "generic",
        tenant_id,
        host,
        severity,
        message,
        payload,
        fingerprint
    )

    return {
        "message": "Webhook received",
        "alert_id": result["id"],
        "source": "generic"
    }
