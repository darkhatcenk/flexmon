"""
Authentication endpoints
"""
from fastapi import APIRouter, HTTPException, status, Depends
from datetime import datetime, timedelta
from ..models import UserLogin, Token, User
from ..deps.security import create_access_token, verify_password, get_platform_admin, get_tenant_admin
from ..services import timescale
from ..config import settings
import secrets

router = APIRouter()


@router.post("/auth/login", response_model=Token)
async def login(credentials: UserLogin):
    """
    Login endpoint - returns JWT token
    """
    # Get user from database
    query = """
        SELECT id, username, password_hash, role, tenant_id, enabled
        FROM users
        WHERE username = $1
    """
    user = await timescale.fetch_one(query, credentials.username)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )

    if not user["enabled"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )

    # Verify password
    if not verify_password(credentials.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )

    # Check if tenant is enabled (if not platform_admin)
    if user["role"] != "platform_admin" and user["tenant_id"]:
        tenant_query = "SELECT enabled FROM tenants WHERE id = $1"
        tenant = await timescale.fetch_one(tenant_query, user["tenant_id"])
        if not tenant or not tenant["enabled"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tenant account is disabled"
            )

    # Update last login
    await timescale.execute_query(
        "UPDATE users SET last_login = NOW() WHERE id = $1",
        user["id"]
    )

    # Create JWT token
    token_data = {
        "user_id": user["id"],
        "username": user["username"],
        "tenant_id": user["tenant_id"],
        "roles": [user["role"]]
    }

    access_token = create_access_token(token_data)

    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.jwt_expiration_minutes * 60
    )


@router.post("/auth/generate-otp")
async def generate_one_time_password(current_user: dict = Depends(get_platform_admin)):
    """
    Generate one-time password for platform admin (emergency access)
    Only platform_admin can call this
    """
    otp = secrets.token_urlsafe(16)

    # Store OTP in database with expiration
    query = """
        INSERT INTO one_time_passwords (user_id, otp_hash, expires_at)
        VALUES ($1, $2, NOW() + INTERVAL '1 hour')
    """

    from ..deps.security import hash_password
    await timescale.execute_query(
        query,
        current_user["user_id"],
        hash_password(otp)
    )

    return {
        "otp": otp,
        "expires_in_seconds": 3600,
        "message": "One-time password generated. Valid for 1 hour."
    }


@router.get("/auth/me", response_model=User)
async def get_current_user_info(current_user: dict = Depends(get_tenant_admin)):
    """
    Get current user information
    """
    query = """
        SELECT id, username, email, role, tenant_id, enabled, created_at, last_login
        FROM users
        WHERE id = $1
    """
    user = await timescale.fetch_one(query, current_user["user_id"])

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return User(**user)
