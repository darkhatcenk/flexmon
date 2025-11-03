"""
Multi-tenancy dependencies and utilities
"""
from typing import Optional
from fastapi import Depends, HTTPException, status

from .security import get_current_user


async def get_tenant_id(current_user: dict = Depends(get_current_user)) -> str:
    """Get tenant_id from current user context"""
    tenant_id = current_user.get("tenant_id")

    # Platform admins can access all tenants
    if "platform_admin" in current_user.get("roles", []):
        return None  # None means access to all tenants

    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No tenant context available"
        )

    return tenant_id


async def get_tenant_id_optional(
    current_user: dict = Depends(get_current_user)
) -> Optional[str]:
    """Get tenant_id from current user, returns None for platform admins"""
    return current_user.get("tenant_id")


def tenant_filter(tenant_id: Optional[str]) -> dict:
    """
    Generate tenant filter for database queries
    Returns empty dict if tenant_id is None (platform admin)
    """
    if tenant_id is None:
        return {}
    return {"tenant_id": tenant_id}


def build_tenant_query(base_query: str, tenant_id: Optional[str]) -> tuple[str, list]:
    """
    Build SQL query with tenant filtering
    Returns (query, params)
    """
    if tenant_id is None:
        return base_query, []

    if "WHERE" in base_query.upper():
        query = f"{base_query} AND tenant_id = $1"
    else:
        query = f"{base_query} WHERE tenant_id = $1"

    return query, [tenant_id]


def get_es_index_pattern(tenant_id: Optional[str], index_prefix: str = "logs") -> str:
    """
    Get Elasticsearch index pattern for tenant
    Format: {prefix}-{tenant_id}-* or {prefix}-* for platform admin
    """
    if tenant_id is None:
        return f"{index_prefix}-*"
    return f"{index_prefix}-{tenant_id}-*"


def get_es_index_name(tenant_id: str, index_prefix: str = "logs") -> str:
    """
    Get Elasticsearch index name for current date
    Format: {prefix}-{tenant_id}-YYYY.MM.DD
    """
    from datetime import datetime
    date_suffix = datetime.utcnow().strftime("%Y.%m.%d")
    return f"{index_prefix}-{tenant_id}-{date_suffix}"
