"""Routers module"""
from . import (
    health,
    auth,
    users,
    metrics_ingest,
    alerts_rules,
    alerts_outbox,
    alerts_webhooks,
    discovery,
    ai_explain
)

__all__ = [
    "health",
    "auth",
    "users",
    "metrics_ingest",
    "alerts_rules",
    "alerts_outbox",
    "alerts_webhooks",
    "discovery",
    "ai_explain"
]
