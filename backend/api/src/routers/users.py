"""
User management endpoints
"""
from fastapi import APIRouter, HTTPException, status, Depends
from typing import List
from ..models import User, UserCreate
from ..deps.security import get_tenant_admin, hash_password
from ..deps.tenancy import get_tenant_id_optional
from ..services import timescale

router = APIRouter()


@router.get("/users", response_model=List[User])
async def list_users(
    tenant_id: str = Depends(get_tenant_id_optional),
    current_user: dict = Depends(get_tenant_admin)
):
    """
    List all users (filtered by tenant for tenant admins)
    """
    if tenant_id:
        query = """
            SELECT id, username, email, role, tenant_id, enabled, created_at, last_login
            FROM users
            WHERE tenant_id = $1 AND role != 'platform_admin'
            ORDER BY created_at DESC
        """
        users = await timescale.fetch_all(query, tenant_id)
    else:
        # Platform admin sees all users
        query = """
            SELECT id, username, email, role, tenant_id, enabled, created_at, last_login
            FROM users
            WHERE role != 'platform_admin'
            ORDER BY created_at DESC
        """
        users = await timescale.fetch_all(query)

    return [User(**user) for user in users]


@router.post("/users", response_model=User, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    tenant_id: str = Depends(get_tenant_id_optional),
    current_user: dict = Depends(get_tenant_admin)
):
    """
    Create a new user
    """
    # Tenant admins can only create users in their own tenant
    if tenant_id and user_data.tenant_id and user_data.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot create user in different tenant"
        )

    # Only platform admin can create platform_admin users
    if user_data.role == "platform_admin" and "platform_admin" not in current_user.get("roles", []):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only platform admins can create platform admin users"
        )

    # Check if username already exists
    existing = await timescale.fetch_one(
        "SELECT id FROM users WHERE username = $1",
        user_data.username
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists"
        )

    # Hash password
    password_hash = hash_password(user_data.password)

    # Insert user
    query = """
        INSERT INTO users (username, email, password_hash, role, tenant_id, enabled)
        VALUES ($1, $2, $3, $4, $5, TRUE)
        RETURNING id, username, email, role, tenant_id, enabled, created_at, last_login
    """

    user = await timescale.fetch_one(
        query,
        user_data.username,
        user_data.email,
        password_hash,
        user_data.role,
        user_data.tenant_id
    )

    return User(**user)


@router.get("/users/{user_id}", response_model=User)
async def get_user(
    user_id: int,
    tenant_id: str = Depends(get_tenant_id_optional),
    current_user: dict = Depends(get_tenant_admin)
):
    """
    Get user by ID
    """
    query = """
        SELECT id, username, email, role, tenant_id, enabled, created_at, last_login
        FROM users
        WHERE id = $1
    """
    user = await timescale.fetch_one(query, user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Tenant admins can only see users in their tenant
    if tenant_id and user["tenant_id"] != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    return User(**user)


@router.patch("/users/{user_id}")
async def update_user(
    user_id: int,
    enabled: bool,
    tenant_id: str = Depends(get_tenant_id_optional),
    current_user: dict = Depends(get_tenant_admin)
):
    """
    Update user (enable/disable)
    """
    # Get existing user
    user = await timescale.fetch_one(
        "SELECT tenant_id FROM users WHERE id = $1",
        user_id
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Tenant admins can only update users in their tenant
    if tenant_id and user["tenant_id"] != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    # Update user
    await timescale.execute_query(
        "UPDATE users SET enabled = $1, updated_at = NOW() WHERE id = $2",
        enabled,
        user_id
    )

    return {"message": "User updated successfully"}


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    tenant_id: str = Depends(get_tenant_id_optional),
    current_user: dict = Depends(get_tenant_admin)
):
    """
    Delete user
    """
    # Get existing user
    user = await timescale.fetch_one(
        "SELECT tenant_id FROM users WHERE id = $1",
        user_id
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Tenant admins can only delete users in their tenant
    if tenant_id and user["tenant_id"] != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    # Delete user
    await timescale.execute_query(
        "DELETE FROM users WHERE id = $1",
        user_id
    )

    return {"message": "User deleted successfully"}
