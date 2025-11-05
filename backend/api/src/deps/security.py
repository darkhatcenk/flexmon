"""
Security dependencies for JWT authentication and authorization
"""
from datetime import datetime, timedelta
from typing import Optional, Annotated
import jwt
from fastapi import Depends, HTTPException, status, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from passlib.hash import bcrypt_sha256

from ..config import settings

# JWT Configuration
security = HTTPBearer()


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.jwt_expiration_minutes)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.api_secret_key, algorithm=settings.jwt_algorithm)
    return encoded_jwt


def verify_token(token: str) -> dict:
    """Verify and decode JWT token"""
    try:
        payload = jwt.decode(token, settings.api_secret_key, algorithms=[settings.jwt_algorithm])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except jwt.JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )


def hash_password(password: str) -> str:
    """Hash password using bcrypt_sha256 (no 72-byte limit)"""
    return bcrypt_sha256.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash using bcrypt_sha256"""
    return bcrypt_sha256.verify(plain_password, hashed_password)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)]
) -> dict:
    """Get current authenticated user from JWT token"""
    token = credentials.credentials
    payload = verify_token(token)

    # Token should contain: user_id, tenant_id, roles
    if "user_id" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )

    return {
        "user_id": payload["user_id"],
        "tenant_id": payload.get("tenant_id"),
        "roles": payload.get("roles", []),
        "username": payload.get("username")
    }


async def require_role(required_role: str):
    """Dependency to require specific role"""
    async def role_checker(current_user: dict = Depends(get_current_user)) -> dict:
        if required_role not in current_user.get("roles", []):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{required_role}' required"
            )
        return current_user
    return role_checker


async def get_platform_admin(current_user: dict = Depends(get_current_user)) -> dict:
    """Require platform_admin role"""
    if "platform_admin" not in current_user.get("roles", []):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Platform admin access required"
        )
    return current_user


async def get_tenant_admin(current_user: dict = Depends(get_current_user)) -> dict:
    """Require tenant_admin or platform_admin role"""
    roles = current_user.get("roles", [])
    if not any(role in roles for role in ["tenant_admin", "platform_admin"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


def verify_webhook_hmac(
    signature: str,
    body: bytes,
    secret: str
) -> bool:
    """
    Verify HMAC signature for webhook requests
    Signature format: sha256=<hexdigest>
    """
    import hmac
    import hashlib

    if not signature:
        return False

    # Remove 'sha256=' prefix if present
    sig_value = signature.replace("sha256=", "").replace("SHA256=", "")

    expected_signature = hmac.new(
        secret.encode(),
        body,
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(sig_value, expected_signature)
