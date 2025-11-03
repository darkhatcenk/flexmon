"""
Agent discovery and management
"""
from fastapi import APIRouter, HTTPException, status, Depends
from typing import List
from ..models import AgentRegistration, AgentInfo
from ..deps.security import get_tenant_admin
from ..deps.tenancy import get_tenant_id_optional
from ..services import timescale
import hashlib

router = APIRouter()


@router.post("/discovery/register", status_code=status.HTTP_201_CREATED)
async def register_agent(
    registration: AgentRegistration,
    tenant_id: str = Depends(get_tenant_id_optional)
):
    """
    Register a new agent (auto-discovery)
    """
    # Generate fingerprint
    fp = registration.fingerprint
    fingerprint = hashlib.sha256(
        f"{fp.hostname}:{fp.uuid}:{fp.mac_address}:{fp.ip_address}".encode()
    ).hexdigest()

    # Check if agent already exists
    existing = await timescale.fetch_one(
        "SELECT * FROM agents WHERE fingerprint = $1",
        fingerprint
    )

    if existing:
        # Update last_seen
        await timescale.execute_query(
            "UPDATE agents SET last_seen = NOW() WHERE fingerprint = $1",
            fingerprint
        )
        return {
            "message": "Agent already registered",
            "agent_id": existing["id"],
            "licensed": existing["licensed"]
        }

    # Insert new agent
    query = """
        INSERT INTO agents (
            fingerprint, hostname, tenant_id, uuid, mac_address, ip_address,
            os, os_version, architecture, last_seen
        )
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, NOW())
        RETURNING *
    """

    agent = await timescale.fetch_one(
        query,
        fingerprint,
        fp.hostname,
        registration.tenant_id or tenant_id,
        fp.uuid,
        fp.mac_address,
        fp.ip_address,
        fp.os,
        fp.os_version,
        fp.architecture
    )

    return {
        "message": "Agent registered successfully",
        "agent_id": agent["id"],
        "licensed": False,
        "fingerprint": fingerprint
    }


@router.get("/discovery/agents", response_model=List[AgentInfo])
async def list_agents(
    tenant_id: str = Depends(get_tenant_id_optional),
    current_user: dict = Depends(get_tenant_admin)
):
    """
    List all discovered agents
    """
    if tenant_id:
        query = """
            SELECT * FROM agents
            WHERE tenant_id = $1
            ORDER BY last_seen DESC
        """
        agents = await timescale.fetch_all(query, tenant_id)
    else:
        query = "SELECT * FROM agents ORDER BY last_seen DESC"
        agents = await timescale.fetch_all(query)

    return [AgentInfo(**agent) for agent in agents]


@router.patch("/discovery/agents/{agent_id}/license")
async def bind_license(
    agent_id: int,
    licensed: bool,
    tenant_id: str = Depends(get_tenant_id_optional),
    current_user: dict = Depends(get_tenant_admin)
):
    """
    Bind/unbind license to agent
    """
    agent = await timescale.fetch_one(
        "SELECT * FROM agents WHERE id = $1",
        agent_id
    )

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )

    if tenant_id and agent["tenant_id"] != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    # Check license limits
    if licensed:
        tenant = await timescale.fetch_one(
            "SELECT license_agent_limit, licensed_agents FROM tenants WHERE id = $1",
            agent["tenant_id"]
        )

        if tenant["licensed_agents"] >= tenant["license_agent_limit"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="License limit reached"
            )

    # Update agent
    await timescale.execute_query(
        "UPDATE agents SET licensed = $1 WHERE id = $2",
        licensed,
        agent_id
    )

    # Update tenant licensed count
    if licensed:
        await timescale.execute_query(
            "UPDATE tenants SET licensed_agents = licensed_agents + 1 WHERE id = $1",
            agent["tenant_id"]
        )
    else:
        await timescale.execute_query(
            "UPDATE tenants SET licensed_agents = licensed_agents - 1 WHERE id = $1",
            agent["tenant_id"]
        )

    return {"message": "License updated successfully"}


@router.patch("/discovery/agents/{agent_id}/config")
async def update_agent_config(
    agent_id: int,
    ignore_logs: bool = None,
    ignore_alerts: bool = None,
    collection_interval_sec: int = None,
    tenant_id: str = Depends(get_tenant_id_optional),
    current_user: dict = Depends(get_tenant_admin)
):
    """
    Update agent configuration
    """
    agent = await timescale.fetch_one(
        "SELECT tenant_id FROM agents WHERE id = $1",
        agent_id
    )

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )

    if tenant_id and agent["tenant_id"] != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    # Build update query
    updates = []
    params = []
    param_count = 1

    if ignore_logs is not None:
        updates.append(f"ignore_logs = ${param_count}")
        params.append(ignore_logs)
        param_count += 1

    if ignore_alerts is not None:
        updates.append(f"ignore_alerts = ${param_count}")
        params.append(ignore_alerts)
        param_count += 1

    if collection_interval_sec is not None:
        updates.append(f"collection_interval_sec = ${param_count}")
        params.append(collection_interval_sec)
        param_count += 1

    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No updates provided"
        )

    params.append(agent_id)
    query = f"UPDATE agents SET {', '.join(updates)} WHERE id = ${param_count}"

    await timescale.execute_query(query, *params)

    return {"message": "Agent configuration updated"}
