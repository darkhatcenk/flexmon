"""
FlexMON License API
Handles license validation and management
"""
from fastapi import FastAPI, HTTPException, status
from .models import LicenseValidationRequest, LicenseValidationResponse, LicenseCreate
from .config import settings
from datetime import datetime, timedelta
import asyncpg

app = FastAPI(
    title="FlexMON License API",
    version="1.0.0",
    description="License validation and management service"
)

# Database connection pool
db_pool: asyncpg.Pool = None


@app.on_event("startup")
async def startup():
    """Initialize database connection"""
    global db_pool
    db_pool = await asyncpg.create_pool(settings.database_url, min_size=2, max_size=10)


@app.on_event("shutdown")
async def shutdown():
    """Close database connection"""
    if db_pool:
        await db_pool.close()


@app.get("/health")
async def health():
    """Health check"""
    return {"status": "healthy", "service": "license-api"}


@app.post("/validate", response_model=LicenseValidationResponse)
async def validate_license(request: LicenseValidationRequest):
    """Validate a license key"""
    # Get tenant from database
    query = """
        SELECT license_key, license_expires_at, license_agent_limit
        FROM tenants
        WHERE id = $1
    """

    async with db_pool.acquire() as conn:
        tenant = await conn.fetchrow(query, request.tenant_id)

    if not tenant:
        return LicenseValidationResponse(
            valid=False,
            message="Tenant not found"
        )

    if tenant["license_key"] != request.license_key:
        return LicenseValidationResponse(
            valid=False,
            message="Invalid license key"
        )

    # Check expiration
    expires_at = tenant["license_expires_at"]
    if expires_at and datetime.utcnow() > expires_at:
        return LicenseValidationResponse(
            valid=False,
            message="License expired",
            expires_at=expires_at
        )

    return LicenseValidationResponse(
        valid=True,
        message="License valid",
        expires_at=expires_at,
        agent_limit=tenant["license_agent_limit"]
    )


@app.post("/create")
async def create_license(license_data: LicenseCreate):
    """Create a new license (admin only)"""
    # Generate license key
    import secrets
    license_key = f"FLX-{secrets.token_urlsafe(24)}"

    # Calculate expiration
    expires_at = datetime.utcnow() + timedelta(days=license_data.duration_days)

    # Insert or update tenant
    query = """
        INSERT INTO tenants (id, name, license_key, license_expires_at, license_agent_limit, enabled)
        VALUES ($1, $2, $3, $4, $5, TRUE)
        ON CONFLICT (id) DO UPDATE
        SET license_key = $3, license_expires_at = $4, license_agent_limit = $5, enabled = TRUE
        RETURNING *
    """

    async with db_pool.acquire() as conn:
        tenant = await conn.fetchrow(
            query,
            license_data.tenant_id,
            license_data.tenant_name,
            license_key,
            expires_at,
            license_data.agent_limit
        )

    return {
        "tenant_id": tenant["id"],
        "license_key": license_key,
        "expires_at": expires_at,
        "agent_limit": tenant["license_agent_limit"]
    }


@app.get("/tenants/{tenant_id}")
async def get_tenant_license(tenant_id: str):
    """Get license information for a tenant"""
    query = """
        SELECT id, name, license_expires_at, license_agent_limit, licensed_agents, enabled
        FROM tenants
        WHERE id = $1
    """

    async with db_pool.acquire() as conn:
        tenant = await conn.fetchrow(query, tenant_id)

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )

    return {
        "tenant_id": tenant["id"],
        "name": tenant["name"],
        "expires_at": tenant["license_expires_at"],
        "agent_limit": tenant["license_agent_limit"],
        "licensed_agents": tenant["licensed_agents"],
        "enabled": tenant["enabled"]
    }
