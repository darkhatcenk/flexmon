"""
License API models
"""
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class LicenseValidationRequest(BaseModel):
    """License validation request"""
    license_key: str
    tenant_id: str


class LicenseValidationResponse(BaseModel):
    """License validation response"""
    valid: bool
    message: str
    expires_at: Optional[datetime] = None
    agent_limit: Optional[int] = None


class LicenseCreate(BaseModel):
    """License creation request"""
    tenant_id: str
    tenant_name: str
    agent_limit: int = 10
    duration_days: int = 365
