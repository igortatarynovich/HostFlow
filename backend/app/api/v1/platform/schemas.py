from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, Optional, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from backend.app.models.tenant import TenantStatus, TenantType
from backend.app.schemas.user import UserOut


class TenantLicenseBase(BaseModel):
    plan: str = Field(..., min_length=1, max_length=64)
    max_recruiters: int = Field(default=0, ge=0)
    max_supervisors: int = Field(default=0, ge=0)
    max_client_managers: int = Field(default=0, ge=0)
    max_viewers: int = Field(default=0, ge=0)
    max_storage_gb: int = Field(default=0, ge=0)
    max_companies: int = Field(default=0, ge=0)
    max_candidates_active: int = Field(default=0, ge=0)
    max_vacancies_active: int = Field(default=0, ge=0)
    max_documents: int = Field(default=0, ge=0)
    max_public_portal_links: int = Field(default=0, ge=0)
    expires_at: date | None = None
    auto_renew: bool = False
    notes: str | None = Field(default=None, max_length=4000)


class TenantLicenseIn(TenantLicenseBase):
    pass


class TenantLicensePatch(BaseModel):
    plan: str | None = Field(default=None, min_length=1, max_length=64)
    max_recruiters: int | None = Field(default=None, ge=0)
    max_supervisors: int | None = Field(default=None, ge=0)
    max_client_managers: int | None = Field(default=None, ge=0)
    max_viewers: int | None = Field(default=None, ge=0)
    max_storage_gb: int | None = Field(default=None, ge=0)
    max_companies: int | None = Field(default=None, ge=0)
    max_candidates_active: int | None = Field(default=None, ge=0)
    max_vacancies_active: int | None = Field(default=None, ge=0)
    max_documents: int | None = Field(default=None, ge=0)
    max_public_portal_links: int | None = Field(default=None, ge=0)
    expires_at: date | None = None
    auto_renew: bool | None = None
    notes: str | None = Field(default=None, max_length=4000)


class TenantLicenseOut(TenantLicenseBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID | str
    created_at: datetime
    updated_at: datetime


class TenantUsageOut(BaseModel):
    recruiter_count: int = 0
    supervisor_count: int = 0
    client_manager_count: int = 0
    viewer_count: int = 0
    storage_used_gb: float = 0
    leads_created_this_month: int = 0
    candidates_active_count: int = 0
    documents_count: int = 0
    vacancies_open_count: int = 0
    portal_links_active_count: int = 0


class TenantModuleSettings(BaseModel):
    candidates: bool = True
    companies: bool = True
    vacancies: bool = True
    documents: bool = True
    leads: bool = True
    services: bool = True
    client_portal: bool = True
    hr: bool = True


class TenantModuleSettingsPatch(BaseModel):
    candidates: bool | None = None
    companies: bool | None = None
    vacancies: bool | None = None
    documents: bool | None = None
    leads: bool | None = None
    services: bool | None = None
    client_portal: bool | None = None
    hr: bool | None = None


class RoleModulePermissions(BaseModel):
    visible: bool = True
    editable: bool = False


class TenantRoleModuleMatrix(BaseModel):
    administrator: Dict[str, RoleModulePermissions] = Field(default_factory=dict)
    supervisor: Dict[str, RoleModulePermissions] = Field(default_factory=dict)
    recruiter: Dict[str, RoleModulePermissions] = Field(default_factory=dict)
    client_manager: Dict[str, RoleModulePermissions] = Field(default_factory=dict)
    client_processor: Dict[str, RoleModulePermissions] = Field(default_factory=dict)
    compliance_officer: Dict[str, RoleModulePermissions] = Field(default_factory=dict)
    hr_officer: Dict[str, RoleModulePermissions] = Field(default_factory=dict)
    viewer: Dict[str, RoleModulePermissions] = Field(default_factory=dict)


class TenantRoleModuleMatrixPatch(BaseModel):
    administrator: Dict[str, RoleModulePermissions] | None = None
    supervisor: Dict[str, RoleModulePermissions] | None = None
    recruiter: Dict[str, RoleModulePermissions] | None = None
    client_manager: Dict[str, RoleModulePermissions] | None = None
    client_processor: Dict[str, RoleModulePermissions] | None = None
    compliance_officer: Dict[str, RoleModulePermissions] | None = None
    hr_officer: Dict[str, RoleModulePermissions] | None = None
    viewer: Dict[str, RoleModulePermissions] | None = None


class EffectiveRoleModules(BaseModel):
    role: str
    modules: Dict[str, RoleModulePermissions] = Field(default_factory=dict)


class TenantUserModuleOverrides(BaseModel):
    users: Dict[str, Dict[str, RoleModulePermissions]] = Field(default_factory=dict)


class TenantUserModuleOverridesPatch(BaseModel):
    users: Dict[str, Dict[str, RoleModulePermissions] | None] = Field(default_factory=dict)


class TenantProvisionIn(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    name: str = Field(..., min_length=1, max_length=128)
    slug: str = Field(..., min_length=1, max_length=64)
    type: TenantType = TenantType.agency
    status: TenantStatus = TenantStatus.active
    parent_tenant_id: UUID | None = None
    client_portal_enabled: bool = True
    status_sharing_allowed: bool = False
    description: str | None = Field(default=None, max_length=2000)
    settings: Dict[str, Any] = Field(default_factory=dict)
    workspace_label: str | None = Field(default=None, max_length=128)
    logo_url: str | None = Field(default=None, max_length=512)
    logo_meta: Dict[str, Any] | None = None
    license: TenantLicenseIn
    initial_admin: TenantAdminCreate | None = None


class PlatformTenantOut(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    id: UUID
    name: str
    slug: str
    type: TenantType
    status: TenantStatus
    parent_tenant_id: UUID | None = None
    client_portal_enabled: bool
    status_sharing_allowed: bool
    description: str | None = None
    workspace_label: str | None = None
    logo_url: str | None = None
    logo_meta: Dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime
    license: TenantLicenseOut | None = None
    usage: TenantUsageOut
    public_domain: str | None = None
    custom_domain: str | None = None
    legal_domain: str | None = None
    public_hosts: list[str] = Field(default_factory=list)
    domains: list[str] = Field(default_factory=list)
    legal_hosts: list[str] = Field(default_factory=list)


class PlatformTenantPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    description: str | None = Field(default=None, max_length=2000)
    workspace_label: str | None = Field(default=None, max_length=128)
    logo_url: str | None = Field(default=None, max_length=512)
    logo_meta: Dict[str, Any] | None = None
    client_portal_enabled: bool | None = None
    status_sharing_allowed: bool | None = None


class TenantLegalHostSettingsOut(BaseModel):
    public_domain: str | None = None
    custom_domain: str | None = None
    legal_domain: str | None = None
    public_hosts: list[str] = Field(default_factory=list)
    domains: list[str] = Field(default_factory=list)
    legal_hosts: list[str] = Field(default_factory=list)


class TenantLegalHostSettingsPatch(BaseModel):
    public_domain: str | None = None
    custom_domain: str | None = None
    legal_domain: str | None = None
    public_hosts: list[str] | None = None
    domains: list[str] | None = None
    legal_hosts: list[str] | None = None


class PlatformTenantList(BaseModel):
    total: int
    items: list[PlatformTenantOut]


class PlatformFounderEnrollOut(BaseModel):
    enrolled: bool
    founder_slots_used: int
    founder_slots_max: int = 50


class TenantStatusChange(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    status: TenantStatus = TenantStatus.suspended
    client_portal_enabled: bool | None = None
    reason: str | None = Field(default=None, max_length=2000)


class TenantImpersonationIn(BaseModel):
    """Phase 5 — mandatory justification for platform impersonation (SSOT §6)."""

    reason: str = Field(..., min_length=3, max_length=2000)


class TenantImpersonationOut(BaseModel):
    token: str
    expires_at: datetime


class TenantSeatRequestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: str
    requested_by: str
    role: str
    requested_count: int
    message: str | None = None
    status: str
    resolution_notes: str | None = None
    resolved_by: str | None = None
    resolved_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class TenantSeatRequestDecision(BaseModel):
    status: Literal["approved", "rejected"]
    resolution_notes: str | None = Field(default=None, max_length=2000)


class TenantAdminCreate(BaseModel):
    email: EmailStr
    full_name: str | None = Field(default=None, max_length=255)
    password: str = Field(..., min_length=8, max_length=128)


class PlatformTenantAdminOut(BaseModel):
    user: UserOut
    temporary_password: str | None = None


class TenantVacancyAccessItem(BaseModel):
    vacancy_id: UUID
    title: str
    company_name: str | None = None
    status: str | None = None


class TenantVacancyAccessList(BaseModel):
    items: list[TenantVacancyAccessItem]


class TenantVacancyAccessUpdate(BaseModel):
    vacancy_ids: list[UUID] = Field(default_factory=list)


class TenantVacancyOption(BaseModel):
    vacancy_id: UUID
    title: str
    company_name: str | None = None
    tenant_id: UUID
    status: str | None = None
