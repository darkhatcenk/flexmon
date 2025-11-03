"""
Alert rules management
"""
from fastapi import APIRouter, HTTPException, status, Depends
from typing import List
from ..models import AlertRule
from ..deps.security import get_tenant_admin
from ..deps.tenancy import get_tenant_id_optional
from ..services import timescale

router = APIRouter()


@router.get("/alerts/rules", response_model=List[AlertRule])
async def list_alert_rules(
    tenant_id: str = Depends(get_tenant_id_optional),
    current_user: dict = Depends(get_tenant_admin)
):
    """List all alert rules"""
    if tenant_id:
        query = """
            SELECT * FROM alert_rules
            WHERE tenant_id = $1
            ORDER BY created_at DESC
        """
        rules = await timescale.fetch_all(query, tenant_id)
    else:
        query = "SELECT * FROM alert_rules ORDER BY created_at DESC"
        rules = await timescale.fetch_all(query)

    return [AlertRule(**rule) for rule in rules]


@router.post("/alerts/rules", response_model=AlertRule, status_code=status.HTTP_201_CREATED)
async def create_alert_rule(
    rule: AlertRule,
    tenant_id: str = Depends(get_tenant_id_optional),
    current_user: dict = Depends(get_tenant_admin)
):
    """Create new alert rule"""
    query = """
        INSERT INTO alert_rules (name, description, type, metric, condition, threshold, duration_minutes, severity, enabled, tenant_id, tags)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
        RETURNING *
    """

    created = await timescale.fetch_one(
        query,
        rule.name,
        rule.description,
        rule.type,
        rule.metric,
        rule.condition,
        rule.threshold,
        rule.duration_minutes,
        rule.severity,
        rule.enabled,
        rule.tenant_id or tenant_id,
        rule.tags
    )

    return AlertRule(**created)


@router.post("/alerts/rules/batch", status_code=status.HTTP_201_CREATED)
async def create_alert_rules_batch(
    rules_data: dict,
    tenant_id: str = Depends(get_tenant_id_optional)
):
    """
    Create multiple alert rules from batch (for seeding)
    No authentication required for initial seeding
    """
    rules = rules_data.get("rules", [])
    created_count = 0

    query = """
        INSERT INTO alert_rules (name, description, type, metric, condition, threshold, duration_minutes, severity, enabled, tenant_id, tags)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
        ON CONFLICT (name, tenant_id) DO NOTHING
    """

    for rule in rules:
        try:
            await timescale.execute_query(
                query,
                rule.get("name"),
                rule.get("description"),
                rule.get("type"),
                rule.get("metric"),
                rule.get("condition"),
                rule.get("threshold"),
                rule.get("duration_minutes", 5),
                rule.get("severity", "warning"),
                rule.get("enabled", True),
                rule.get("tenant_id"),
                rule.get("tags", [])
            )
            created_count += 1
        except Exception as e:
            # Skip rules that fail (e.g., duplicates)
            continue

    return {
        "message": f"Created {created_count} alert rules",
        "total": len(rules),
        "created": created_count
    }


@router.get("/alerts/rules/{rule_id}", response_model=AlertRule)
async def get_alert_rule(
    rule_id: int,
    tenant_id: str = Depends(get_tenant_id_optional),
    current_user: dict = Depends(get_tenant_admin)
):
    """Get alert rule by ID"""
    query = "SELECT * FROM alert_rules WHERE id = $1"
    rule = await timescale.fetch_one(query, rule_id)

    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert rule not found"
        )

    if tenant_id and rule["tenant_id"] != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    return AlertRule(**rule)


@router.patch("/alerts/rules/{rule_id}")
async def update_alert_rule(
    rule_id: int,
    enabled: bool,
    tenant_id: str = Depends(get_tenant_id_optional),
    current_user: dict = Depends(get_tenant_admin)
):
    """Enable/disable alert rule"""
    rule = await timescale.fetch_one(
        "SELECT tenant_id FROM alert_rules WHERE id = $1",
        rule_id
    )

    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert rule not found"
        )

    if tenant_id and rule["tenant_id"] != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    await timescale.execute_query(
        "UPDATE alert_rules SET enabled = $1, updated_at = NOW() WHERE id = $2",
        enabled,
        rule_id
    )

    return {"message": "Alert rule updated"}


@router.delete("/alerts/rules/{rule_id}")
async def delete_alert_rule(
    rule_id: int,
    tenant_id: str = Depends(get_tenant_id_optional),
    current_user: dict = Depends(get_tenant_admin)
):
    """Delete alert rule"""
    rule = await timescale.fetch_one(
        "SELECT tenant_id FROM alert_rules WHERE id = $1",
        rule_id
    )

    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert rule not found"
        )

    if tenant_id and rule["tenant_id"] != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    await timescale.execute_query(
        "DELETE FROM alert_rules WHERE id = $1",
        rule_id
    )

    return {"message": "Alert rule deleted"}


@router.get("/alerts")
async def list_alerts(
    tenant_id: str = Depends(get_tenant_id_optional),
    current_user: dict = Depends(get_tenant_admin),
    limit: int = 100
):
    """List recent alerts"""
    if tenant_id:
        query = """
            SELECT * FROM alerts
            WHERE tenant_id = $1
            ORDER BY triggered_at DESC
            LIMIT $2
        """
        alerts = await timescale.fetch_all(query, tenant_id, limit)
    else:
        query = "SELECT * FROM alerts ORDER BY triggered_at DESC LIMIT $1"
        alerts = await timescale.fetch_all(query, limit)

    return alerts


@router.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: int,
    current_user: dict = Depends(get_tenant_admin)
):
    """Acknowledge an alert"""
    await timescale.execute_query(
        """
        UPDATE alerts
        SET acknowledged_at = NOW(), acknowledged_by = $1
        WHERE id = $2
        """,
        current_user["username"],
        alert_id
    )

    return {"message": "Alert acknowledged"}
