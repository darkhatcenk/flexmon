"""
Alert notification management
"""
from fastapi import APIRouter, HTTPException, status, Depends
from typing import List
from ..models import NotificationConfig, NotificationRequest
from ..deps.security import get_tenant_admin
from ..deps.tenancy import get_tenant_id
from ..services import timescale, notifications

router = APIRouter()


@router.get("/notifications/channels")
async def list_notification_channels(
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_tenant_admin)
):
    """List notification channels for tenant"""
    query = """
        SELECT * FROM notification_channels
        WHERE tenant_id = $1
        ORDER BY created_at DESC
    """
    channels = await timescale.fetch_all(query, tenant_id)
    return channels


@router.post("/notifications/channels", status_code=status.HTTP_201_CREATED)
async def create_notification_channel(
    config: NotificationConfig,
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_tenant_admin)
):
    """Create new notification channel"""
    query = """
        INSERT INTO notification_channels (tenant_id, channel_type, name, enabled, config)
        VALUES ($1, $2, $3, $4, $5)
        RETURNING *
    """

    channel = await timescale.fetch_one(
        query,
        tenant_id,
        config.channel,
        f"{config.channel}_channel",
        config.enabled,
        config.config
    )

    return channel


@router.post("/notifications/send")
async def send_notification(
    notification: NotificationRequest,
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_tenant_admin)
):
    """Send test notification"""
    result = await notifications.send_notification(
        channel=notification.channel,
        tenant_id=tenant_id,
        severity=notification.severity,
        subject=notification.subject,
        message=notification.message,
        metadata=notification.metadata
    )

    return {"message": "Notification sent", "result": result}
