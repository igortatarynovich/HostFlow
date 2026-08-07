from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Literal, Optional, Sequence

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserRole(str, Enum):
    administrator = "administrator"
    employee = "employee"
    supervisor = "supervisor"
    recruiter = "recruiter"
    client_manager = "client_manager"
    client_processor = "client_processor"
    compliance_officer = "compliance_officer"
    hr_officer = "hr_officer"
    viewer = "viewer"


class UserCreateInvite(BaseModel):
    email: EmailStr
    role: UserRole
    supervisor_id: str | None = Field(default=None)
    company_ids: Sequence[str] = Field(default_factory=list)
    expires_in_hours: int = Field(
        default=72,
        ge=1,
        le=720,
        description="Invite validity window (in hours).",
    )


class UserUpdateRole(BaseModel):
    role: UserRole


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: str | None = None
    invite_id: str | None = None
    email: EmailStr
    role: UserRole
    status: Literal["active", "inactive", "invited"]
    is_active: bool
    full_name: str | None = None
    short_id: str | None = None
    supervisor_id: str | None = None
    invited_at: datetime | None = None
    invite_expires_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    temporary_password: str | None = None
    company_ids: list[str] = Field(default_factory=list)


class UserDetailOut(UserOut):
    companies: list[dict[str, str | bool]] = Field(default_factory=list)
    recruiters: list[dict[str, str | None]] = Field(default_factory=list)
    allowed_own_company_ids: list[str] | None = Field(
        default=None,
        description="Subset of own-company UUIDs this user may use; null/omitted = no ACL.",
    )


class UserSupervisorUpdate(BaseModel):
    supervisor_id: str | None = Field(default=None)

class UserCompaniesUpdate(BaseModel):
    company_ids: Sequence[str] = Field(default_factory=list)


class UserOwnCompanyAccessUpdate(BaseModel):
    allowed_own_company_ids: list[str] = Field(
        default_factory=list,
        description="Empty list clears ACL (user may use any tenant own-company).",
    )


class UserInviteOut(BaseModel):
    id: str
    email: EmailStr
    role: UserRole
    token: str
    expires_at: datetime
    status: Literal["pending", "accepted", "revoked"]
    invited_user_id: str | None = None
    supervisor_id: str | None = None
    company_ids: list[str] = Field(default_factory=list)


class UserInviteAccept(BaseModel):
    token: str = Field(..., min_length=8, max_length=512)
    password: str = Field(..., min_length=8, max_length=128)
    full_name: str | None = Field(default=None, max_length=255)
    short_id: str | None = Field(default=None, max_length=50)


class UserAuditOut(BaseModel):
    id: str
    tenant_id: str
    user_id: str | None = None
    actor_id: str | None = None
    action: str
    payload: dict | None = None
    created_at: datetime


class RefreshRevokeOut(BaseModel):
    revoked: int


class UserCreate(BaseModel):
    email: EmailStr
    role: UserRole
    full_name: str | None = Field(default=None, max_length=255)
    short_id: str | None = Field(default=None, max_length=50)
    password: str | None = Field(default=None, min_length=8, max_length=128)
    supervisor_id: str | None = Field(default=None)
    company_ids: Sequence[str] = Field(default_factory=list)


class UserOutgoingSignature(BaseModel):
    first_name: str | None = Field(default=None, max_length=255)
    last_name: str | None = Field(default=None, max_length=255)
    position: str | None = Field(default=None, max_length=128)
    phone: str | None = Field(default=None, max_length=64)
    email: EmailStr | None = None
    company: str | None = Field(default=None, max_length=255)
    website: str | None = Field(default=None, max_length=255)
    logo_url: str | None = Field(default=None, max_length=1024)
    show_phone: bool = True
    show_email: bool = True
    show_website: bool = True


class UserProfileOut(BaseModel):
    user_id: str
    email: EmailStr
    tenant_id: str | None = None
    role: str | None = None
    first_name: str | None = Field(default=None, max_length=255)
    last_name: str | None = Field(default=None, max_length=255)
    birth_date: str | None = Field(default=None, min_length=8, max_length=32)
    country: str | None = Field(default=None, max_length=128)
    city: str | None = Field(default=None, max_length=128)
    position: str | None = Field(default=None, max_length=128)
    phone: str | None = Field(default=None, max_length=64)
    avatar_url: str | None = Field(default=None, max_length=1024)
    signature: UserOutgoingSignature = Field(default_factory=UserOutgoingSignature)


class UserProfileUpdate(BaseModel):
    first_name: str | None = Field(default=None, max_length=255)
    last_name: str | None = Field(default=None, max_length=255)
    birth_date: str | None = Field(default=None, min_length=4, max_length=32)
    country: str | None = Field(default=None, max_length=128)
    city: str | None = Field(default=None, max_length=128)
    position: str | None = Field(default=None, max_length=128)
    phone: str | None = Field(default=None, max_length=64)
    email: EmailStr | None = None
    signature: UserOutgoingSignature | None = None


class UserPasswordChange(BaseModel):
    current_password: str = Field(..., min_length=1, max_length=128)
    new_password: str = Field(..., min_length=8, max_length=128)


class AdminPasswordChange(BaseModel):
    new_password: str = Field(..., min_length=12, max_length=128)
    revoke_sessions: bool = Field(default=True)


class UserPasswordResetOut(BaseModel):
    temporary_password: str = Field(default="", max_length=256)
    revoked_sessions: int = Field(default=0, ge=0)


class UserDeleteOut(BaseModel):
    deleted: bool = True
    revoked_sessions: int = Field(default=0, ge=0)


class InviteRevokeOut(BaseModel):
    revoked: bool = True
    invite_id: str


class UIPreferences(BaseModel):
    locale: str | None = None
    timezone: str | None = None
    date_format: str | None = None
    phone_format: str | None = None
    theme: Literal["light", "dark", "system"] | None = None


class NotificationsPreference(BaseModel):
    enabled: bool
    mode: Literal["immediate", "daily_digest"] = Field(default="immediate")


class DefaultsPreferences(BaseModel):
    company_id: str | None = None


class SavedView(BaseModel):
    id: str = Field(..., min_length=1, max_length=64)
    name: str = Field(..., min_length=1, max_length=128)
    filters: Dict[str, Any] = Field(default_factory=dict)
    is_default: bool | None = False


class SavedViews(BaseModel):
    candidates: list[SavedView] = Field(default_factory=list)
    vacancies: list[SavedView] = Field(default_factory=list)


class SavedViewsPatch(BaseModel):
    candidates: Optional[list[SavedView]] = None
    vacancies: Optional[list[SavedView]] = None


class UserPreferencesOut(BaseModel):
    ui: UIPreferences = Field(default_factory=UIPreferences)
    notifications: Dict[str, NotificationsPreference] = Field(default_factory=dict)
    defaults: DefaultsPreferences = Field(default_factory=DefaultsPreferences)
    saved_views: SavedViews = Field(default_factory=SavedViews)


class UserPreferencesPatch(BaseModel):
    ui: UIPreferences | None = None
    notifications: Dict[str, NotificationsPreference] | None = None
    defaults: DefaultsPreferences | None = None
    saved_views: SavedViewsPatch | None = None


class UserSecurityCompany(BaseModel):
    id: str
    name: str
    can_edit: bool = False


class UserSecuritySupervisor(BaseModel):
    id: str
    name: str | None = None
    email: EmailStr | None = None


class UserSecuritySummary(BaseModel):
    role: str
    companies: list[UserSecurityCompany] = Field(default_factory=list)
    supervisor: UserSecuritySupervisor | None = None
    last_login_at: datetime | None = None
    sessions_count: int = 0


class UserSessionOut(BaseModel):
    id: str
    created_at: datetime
    last_seen_at: datetime
    ip_address: str | None = None
    user_agent: str | None = None
    device_label: str | None = None
    expires_at: datetime | None = None
    revoked_at: datetime | None = None


class UserAvatarOut(BaseModel):
    avatar_url: str | None = None


class UserMeOut(BaseModel):
    profile: UserProfileOut
    preferences: UserPreferencesOut
    security: UserSecuritySummary
    # G-6 Stage 2e — Work Hub `admin_solo` vs `admin_team`: true when this user
    # is an owner-class role and the tenant has exactly one active, non-deleted
    # member (computed server-side; see `users_service.get_user_me`).
    is_solo_admin: bool = False


class UserMePatch(BaseModel):
    profile: UserProfileUpdate | None = None
    preferences: UserPreferencesPatch | None = None
