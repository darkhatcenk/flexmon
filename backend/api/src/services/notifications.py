"""
Multi-channel notification service
"""
import httpx
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any
import logging
from ..models import NotificationChannel, Severity
from . import timescale

logger = logging.getLogger(__name__)


async def send_notification(
    channel: NotificationChannel,
    tenant_id: str,
    severity: Severity,
    subject: str,
    message: str,
    metadata: Dict[str, Any] = None
) -> Dict[str, Any]:
    """Send notification via specified channel"""

    # Get channel configuration
    config_query = """
        SELECT config FROM notification_channels
        WHERE tenant_id = $1 AND channel_type = $2 AND enabled = TRUE
        LIMIT 1
    """

    channel_config = await timescale.fetch_one(config_query, tenant_id, channel.value)

    if not channel_config:
        return {"success": False, "error": "Channel not configured"}

    config = channel_config["config"]

    try:
        if channel == NotificationChannel.EMAIL:
            return await _send_email(config, subject, message)
        elif channel == NotificationChannel.SLACK:
            return await _send_slack(config, severity, subject, message)
        elif channel == NotificationChannel.TEAMS:
            return await _send_teams(config, severity, subject, message)
        elif channel == NotificationChannel.TELEGRAM:
            return await _send_telegram(config, subject, message)
        elif channel == NotificationChannel.WHATSAPP:
            return await _send_whatsapp(config, message)
        else:
            return {"success": False, "error": "Unsupported channel"}
    except Exception as e:
        logger.error(f"Notification error ({channel}): {e}")
        return {"success": False, "error": str(e)}


async def _send_email(config: Dict, subject: str, message: str) -> Dict:
    """Send email via SMTP"""
    try:
        msg = MIMEMultipart()
        msg["From"] = config["from_address"]
        msg["To"] = config["to_address"]
        msg["Subject"] = subject
        msg.attach(MIMEText(message, "plain"))

        with smtplib.SMTP(config["smtp_host"], config.get("smtp_port", 587)) as server:
            if config.get("use_tls", True):
                server.starttls()
            if config.get("username"):
                server.login(config["username"], config["password"])
            server.send_message(msg)

        return {"success": True, "channel": "email"}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def _send_slack(config: Dict, severity: Severity, subject: str, message: str) -> Dict:
    """Send Slack message"""
    webhook_url = config.get("webhook_url")

    color_map = {
        "info": "#36a64f",
        "warning": "#ff9900",
        "error": "#ff0000",
        "critical": "#8b0000"
    }

    payload = {
        "attachments": [{
            "color": color_map.get(severity.value, "#cccccc"),
            "title": subject,
            "text": message,
            "footer": "FlexMON",
            "ts": int(datetime.utcnow().timestamp())
        }]
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(webhook_url, json=payload)
        return {"success": response.status_code == 200, "channel": "slack"}


async def _send_teams(config: Dict, severity: Severity, subject: str, message: str) -> Dict:
    """Send Microsoft Teams message"""
    webhook_url = config.get("webhook_url")

    payload = {
        "@type": "MessageCard",
        "@context": "http://schema.org/extensions",
        "themeColor": "FF0000" if severity in ["critical", "error"] else "FFA500",
        "summary": subject,
        "sections": [{
            "activityTitle": subject,
            "text": message,
            "markdown": True
        }]
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(webhook_url, json=payload)
        return {"success": response.status_code == 200, "channel": "teams"}


async def _send_telegram(config: Dict, subject: str, message: str) -> Dict:
    """Send Telegram message"""
    bot_token = config.get("bot_token")
    chat_id = config.get("chat_id")

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": f"*{subject}*\n\n{message}",
        "parse_mode": "Markdown"
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload)
        return {"success": response.status_code == 200, "channel": "telegram"}


async def _send_whatsapp(config: Dict, message: str) -> Dict:
    """Send WhatsApp message via Cloud API"""
    access_token = config.get("access_token")
    phone_number_id = config.get("phone_number_id")
    to_number = config.get("to_number")

    url = f"https://graph.facebook.com/v17.0/{phone_number_id}/messages"

    payload = {
        "messaging_product": "whatsapp",
        "to": to_number,
        "type": "text",
        "text": {"body": message}
    }

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload, headers=headers)
        return {"success": response.status_code == 200, "channel": "whatsapp"}


from datetime import datetime
