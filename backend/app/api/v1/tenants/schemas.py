from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, Field, computed_field


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
    type: str = "agency"
    status: str = "active"
    client_portal_enabled: bool = True
    status_sharing_allowed: bool = False
    client_handoff_view: bool = False
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


class TenantLinkOut(BaseModel):
    id: str
    agency_tenant_id: str
    client_company_id: Optional[str] = None
    client_tenant_id: Optional[str] = None
    status: str
    features_json: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True

    @computed_field
    @property
    def handoff_enabled(self) -> bool:
        features = self.features_json or {}
        return bool(features.get("handoff_enabled", False))


class TenantLinkWithCompanyOut(BaseModel):
    """TenantLinkOut with company_name for display."""
    id: str
    agency_tenant_id: str
    client_company_id: Optional[str] = None
    client_tenant_id: Optional[str] = None
    handoff_include_company_id: Optional[str] = None
    status: str
    features_json: Optional[Dict[str, Any]] = None
    company_name: Optional[str] = None
    portal_token: Optional[str] = None
    portal_expires_at: Optional[datetime] = None

    @computed_field
    @property
    def handoff_enabled(self) -> bool:
        features = self.features_json or {}
        return bool(features.get("handoff_enabled", False))

    @computed_field
    @property
    def see_vacancies(self) -> bool:
        features = self.features_json or {}
        return bool(features.get("see_vacancies", False))

    @computed_field
    @property
    def see_reduced_profiles(self) -> bool:
        features = self.features_json or {}
        return bool(features.get("see_reduced_profiles", False))


class TenantLinkCreate(BaseModel):
    """Create client link. Either link to existing company/tenant or create by display_name."""
    display_name: Optional[str] = Field(default=None, max_length=255)
    client_company_id: Optional[UUID] = None
    client_tenant_id: Optional[UUID] = None
    handoff_include_company_id: Optional[UUID] = None
    handoff_enabled: bool = False
    see_vacancies: bool = False
    see_reduced_profiles: bool = False


class TenantLinkUpdate(BaseModel):
    handoff_enabled: Optional[bool] = None
    handoff_to_client: Optional[bool] = None
    handoff_to_internal_hr: Optional[bool] = None
    workforce_handoff_on_ready_for_handoff_stage: Optional[bool] = None
    contact_policy: Optional[Dict[str, Any]] = None
    see_vacancies: Optional[bool] = None
    see_reduced_profiles: Optional[bool] = None


class CompanySearchOut(BaseModel):
    """Company in another tenant (employer) for linking as client."""
    id: UUID
    name: str
    tenant_id: str
    website: Optional[str] = None


class PortalLinkOut(BaseModel):
    """Generated portal URL and token for client link."""
    url: str
    token: str
    expires_at: Optional[datetime] = None
