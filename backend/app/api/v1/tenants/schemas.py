from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class TenantBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    slug: str = Field(..., min_length=1, max_length=64, pattern=r"^[a-z0-9\-]+$")
    description: Optional[str] = Field(default=None, max_length=2000)
    settings: Dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True
    workspace_label: Optional[str] = Field(default=None, max_length=128)
    logo_url: Optional[str] = Field(default=None, max_length=512)
    logo_meta: Optional[Dict[str, Any]] = None


class TenantCreate(TenantBase):
    pass


class TenantUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=128)
    description: Optional[str] = Field(default=None, max_length=2000)
    settings: Optional[Dict[str, Any]] = Field(default=None)
    is_active: Optional[bool] = None
    workspace_label: Optional[str] = Field(default=None, max_length=128)
    logo_url: Optional[str] = Field(default=None, max_length=512)
    logo_meta: Optional[Dict[str, Any]] = None


class TenantOut(TenantBase):
    id: UUID
    api_key: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TenantMeOut(BaseModel):
    tenant: TenantOut


class TenantUsersOut(BaseModel):
    id: str
    email: str
    role: str
    joined_at: Optional[datetime] = None


class ApiKeyResetOut(BaseModel):
    api_key: str
    tenant_id: UUID
    rotated_at: datetime
