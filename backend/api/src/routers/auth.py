"""
Authentication endpoints with robust error handling and structured logging
"""
import uuid
import logging
from fastapi import APIRouter, HTTPException, status, Depends, Request
from datetime import datetime, timedelta
from ..models import UserLogin, Token, User
from ..deps.security import create_access_token, verify_password, get_platform_admin, get_tenant_admin
from ..services import timescale
from ..config import settings

router = APIRouter()
logger = logging.getLogger(__name__)


def generate_request_id() -> str:
    """Generate unique request ID for tracking"""
    return str(uuid.uuid4())


@router.post("/auth/login", response_model=Token)
async def login(credentials: UserLogin, request: Request):
    """
    Login endpoint - returns JWT token

    Returns:
    - 200: Success with JWT token
    - 400: Invalid input (empty username/password)
    - 401: Invalid credentials
    - 503: Bootstrap required (no users in database)
    """
    request_id = generate_request_id()

    # Validate input
    username = credentials.username.strip() if credentials.username else ""
    password = credentials.password if credentials.password else ""

    if not username:
        logger.warning(f"[{request_id}] Login failed: empty username")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username is required"
        )

    if not password:
        logger.warning(f"[{request_id}] Login failed: empty password for user '{username}'")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password is required"
        )

    try:
        # Check if any users exist (bootstrap check)
        count_query = "SELECT COUNT(*) as count FROM users"
        count_result = await timescale.fetch_one(count_query)
        user_count = count_result["count"] if count_result else 0

        if user_count == 0:
            logger.error(f"[{request_id}] Bootstrap required: no users in database")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="bootstrap_required"
            )

        # Get user from database
        query = """
            SELECT id, username, password_hash, role, tenant_id, enabled
            FROM users
            WHERE username = $1
        """
        user = await timescale.fetch_one(query, username)

        if not user:
            logger.warning(f"[{request_id}] Login failed: user not found - username='{username}'")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="invalid_credentials"
            )

        if not user["enabled"]:
            logger.warning(f"[{request_id}] Login failed: user disabled - username='{username}', user_id={user['id']}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is disabled"
            )

        # Verify password
        try:
            password_valid = verify_password(password, user["password_hash"])
        except Exception as e:
            logger.error(f"[{request_id}] Password verification failed: {e}", exc_info=True)
            logger.warning(f"[{request_id}] Login failed: password verification error - username='{username}'")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="invalid_credentials"
            )

        if not password_valid:
            logger.warning(f"[{request_id}] Login failed: invalid password - username='{username}', password_length={len(password)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="invalid_credentials"
            )

        # Check if tenant is enabled (if not platform_admin)
        if user["role"] != "platform_admin" and user["tenant_id"]:
            tenant_query = "SELECT enabled FROM tenants WHERE id = $1"
            tenant = await timescale.fetch_one(tenant_query, user["tenant_id"])
            if not tenant or not tenant["enabled"]:
                logger.warning(f"[{request_id}] Login failed: tenant disabled - username='{username}', tenant_id='{user['tenant_id']}'")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Tenant account is disabled"
                )

        # Update last login
        try:
            await timescale.execute_query(
                "UPDATE users SET last_login = NOW() WHERE id = $1",
                user["id"]
            )
        except Exception as e:
            logger.warning(f"[{request_id}] Failed to update last_login: {e}")

        # Create JWT token
        token_data = {
            "user_id": user["id"],
            "username": user["username"],
            "tenant_id": user["tenant_id"],
            "roles": [user["role"]]
        }

        access_token = create_access_token(token_data)

        logger.info(f"[{request_id}] Login successful - username='{username}', user_id={user['id']}, role='{user['role']}'")

        return Token(
            access_token=access_token,
            token_type="bearer",
            expires_in=settings.jwt_expiration_minutes * 60
        )

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        # Catch any unexpected errors
        logger.error(f"[{request_id}] Unexpected error during login - username='{username}': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/_diag/auth")
async def auth_diagnostics():
    """
    Authentication diagnostics endpoint

    Checks:
    - Database connectivity
    - Users table exists and has required columns
    - Returns status and details
    """
    request_id = generate_request_id()
    checks = {}

    try:
        # Check database connectivity
        try:
            await timescale.fetch_one("SELECT 1 as test")
            checks["database_connectivity"] = "ok"
        except Exception as e:
            checks["database_connectivity"] = f"failed: {str(e)}"
            logger.error(f"[{request_id}] DB connectivity check failed: {e}")
            return {"ok": False, "checks": checks, "error": "Database connectivity failed"}

        # Check users table exists and has required columns
        try:
            query = """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'users'
                ORDER BY column_name
            """
            columns_result = await timescale.fetch_all(query)
            columns = [row["column_name"] for row in columns_result]

            required_columns = ["username", "password_hash", "role", "created_at", "updated_at"]
            missing_columns = [col for col in required_columns if col not in columns]

            if missing_columns:
                checks["users_table_schema"] = f"missing columns: {', '.join(missing_columns)}"
                return {"ok": False, "checks": checks, "error": f"Missing columns: {', '.join(missing_columns)}"}
            else:
                checks["users_table_schema"] = f"ok ({len(columns)} columns)"
        except Exception as e:
            checks["users_table_schema"] = f"failed: {str(e)}"
            logger.error(f"[{request_id}] Schema check failed: {e}")
            return {"ok": False, "checks": checks, "error": "Schema check failed"}

        # Check user count
        try:
            count_result = await timescale.fetch_one("SELECT COUNT(*) as count FROM users")
            user_count = count_result["count"] if count_result else 0
            checks["user_count"] = user_count

            if user_count == 0:
                checks["bootstrap_status"] = "required - no users found (run: docker exec api python -m src.manage reset-admin)"
        except Exception as e:
            checks["user_count"] = f"failed: {str(e)}"

        logger.info(f"[{request_id}] Diagnostics check passed")
        return {"ok": True, "checks": checks}

    except Exception as e:
        logger.error(f"[{request_id}] Diagnostics failed: {e}", exc_info=True)
        return {"ok": False, "checks": checks, "error": str(e)}


@router.get("/auth/me", response_model=User)
async def get_current_user_info(current_user: dict = Depends(get_tenant_admin)):
    """
    Get current user information
    """
    request_id = generate_request_id()

    try:
        query = """
            SELECT id, username, email, role, tenant_id, enabled, created_at, last_login
            FROM users
            WHERE id = $1
        """
        user = await timescale.fetch_one(query, current_user["user_id"])

        if not user:
            logger.warning(f"[{request_id}] User not found for /auth/me - user_id={current_user['user_id']}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        return User(**user)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[{request_id}] Error fetching user info - user_id={current_user.get('user_id')}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )
