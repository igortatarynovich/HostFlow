from __future__ import annotations

from datetime import datetime, timedelta, timezone
import re
import secrets
import string
import uuid
from typing import Any, Dict, Optional

import sqlalchemy as sa
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, select

from backend.app.auth.jwt_tools import encode as encode_jwt
from backend.app.core.config import settings
from backend.app.core.security import hash_password, verify_password
from backend.app.db.session import async_session_maker
from backend.app.models.tenant import Tenant, TenantLicense, TenantStatus, TenantType, user_memberships
from backend.app.models.user import Role as UserRole
from backend.app.models.user import User
from backend.app.schemas.user import UserDetailOut, UserInviteAccept
from backend.app.services.system_email import send_system_email
from backend.app.services import users as users_service
from backend.app.services.users import UserServiceError

router = APIRouter()

DEFAULT_TENANT_ID = "11111111-1111-1111-1111-111111111111"

_user_memberships = sa.table(
    "user_memberships",
    sa.column("user_id"),
    sa.column("tenant_id"),
    sa.column("role"),
)

_ROLE_MAP = {
    "owner": UserRole.administrator.value,
    "admin": UserRole.administrator.value,
    "administrator": UserRole.administrator.value,
    "manager": UserRole.supervisor.value,
    "supervisor": UserRole.supervisor.value,
    "recruiter": UserRole.recruiter.value,
    "viewer": UserRole.viewer.value,
    "client_manager": UserRole.client_manager.value,
    "client": UserRole.client_manager.value,
    "client_processor": UserRole.client_processor.value,
    "processor": UserRole.client_processor.value,
    "superadmin": UserRole.superadmin.value,
}

class LoginIn(BaseModel):
    email: EmailStr
    password: str


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    workspace_name: str = Field(..., min_length=2, max_length=128)
    full_name: str | None = Field(default=None, max_length=255)
    plan_code: str | None = Field(default=None, max_length=32)
    accept_terms: bool = False
    accept_privacy: bool = False


class RegisterOut(BaseModel):
    ok: bool = True
    user: Dict[str, Any]
    tenant: Dict[str, Any]


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: Dict[str, Any]
    session_id: str | None = None


def _normalize_role(
    user_role: Any,
    membership_role: Optional[str],
) -> str:
    raw_user_role = str(user_role or "").lower()
    if raw_user_role == UserRole.superadmin.value:
        return UserRole.superadmin.value
    if isinstance(user_role, UserRole) and user_role == UserRole.superadmin:
        return UserRole.superadmin.value
    if membership_role:
        mapped = _ROLE_MAP.get(str(membership_role).lower())
        if mapped:
            return mapped
    if isinstance(user_role, UserRole):
        return user_role.value
    raw = str(user_role or UserRole.viewer.value).lower()
    return _ROLE_MAP.get(raw, UserRole.viewer.value)


def _slugify_workspace(raw: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9]+", "-", (raw or "").strip().lower()).strip("-")
    if not value:
        return "workspace"
    return value[:50]


def _gen_api_key(length: int = 40) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


async def _unique_slug(session, base_slug: str) -> str:
    root = (base_slug or "workspace").strip("-") or "workspace"
    root = root[:40]
    for idx in range(0, 100):
        suffix = "" if idx == 0 else f"-{idx + 1}"
        candidate = f"{root}{suffix}"
        exists = await session.execute(select(Tenant.id).where(func.lower(Tenant.slug) == candidate.lower()).limit(1))
        if exists.scalar_one_or_none() is None:
            return candidate
    random_tail = secrets.token_hex(2)
    return f"{root[:35]}-{random_tail}"


async def _unique_tenant_name(session, desired: str) -> str:
    root = (desired or "").strip() or "Workspace"
    root = root[:110]
    for idx in range(0, 100):
        suffix = "" if idx == 0 else f" ({idx + 1})"
        candidate = f"{root}{suffix}"
        exists = await session.execute(select(Tenant.id).where(func.lower(Tenant.name) == candidate.lower()).limit(1))
        if exists.scalar_one_or_none() is None:
            return candidate
    return f"{root[:100]} {secrets.token_hex(2)}"


def _frontend_base_url() -> str:
    base = (settings.frontend_url or "").strip().rstrip("/")
    return base or "https://hostflow.cc"


def _signup_welcome_email_body(
    *,
    workspace_name: str,
    trial_expires_at: str,
) -> str:
    base = _frontend_base_url()
    billing_url = f"{base}/app/settings/billing"
    privacy_url = f"{base}/legal/privacy.html"
    terms_url = f"{base}/legal/terms.html"
    cookies_url = f"{base}/legal/cookies.html"
    return (
        f"Welcome to HostFlow CRM.\n\n"
        f"Workspace: {workspace_name}\n"
        f"Trial status: active\n"
        f"Trial ends: {trial_expires_at}\n\n"
        f"Next steps:\n"
        f"1) Create company and complete onboarding\n"
        f"2) Open billing settings to monitor trial and plan: {billing_url}\n"
        f"3) Review legal documents:\n"
        f"   - Privacy Policy: {privacy_url}\n"
        f"   - Terms of Service: {terms_url}\n"
        f"   - Cookie Policy: {cookies_url}\n\n"
        f"If you did not create this account, contact support immediately."
    )


@router.post("/register", response_model=RegisterOut, tags=["auth"], summary="Self-service registration")
async def auth_register(payload: RegisterIn) -> RegisterOut:
    email = payload.email.lower().strip()
    workspace_name = payload.workspace_name.strip()
    if len(workspace_name) < 2:
        raise HTTPException(status_code=422, detail="Workspace name is too short")
    if not payload.accept_terms or not payload.accept_privacy:
        raise HTTPException(status_code=422, detail="Terms and privacy acceptance is required")

    async with async_session_maker() as session:
        existing_user = await session.execute(select(User.id).where(func.lower(User.email) == email).limit(1))
        if existing_user.scalar_one_or_none() is not None:
            raise HTTPException(status_code=409, detail="Email already in use")

        tenant_name = await _unique_tenant_name(session, workspace_name)
        tenant_slug = await _unique_slug(session, _slugify_workspace(workspace_name))

        tenant = Tenant(
            id=str(uuid.uuid4()),
            name=tenant_name,
            slug=tenant_slug,
            api_key=_gen_api_key(),
            type=TenantType.agency,
            status=TenantStatus.trial,
            workspace_label=workspace_name,
            settings={"signup": {"source": "self_service"}},
        )
        session.add(tenant)
        await session.flush()

        trial_expires_at = (datetime.now(timezone.utc) + timedelta(days=14)).date()
        license_entry = TenantLicense(
            tenant_id=tenant.id,
            plan="trial",
            expires_at=trial_expires_at,
            max_recruiters=1,
            max_supervisors=1,
            max_client_managers=0,
            max_viewers=0,
            max_storage_gb=5,
            max_companies=1,
            max_candidates_active=100,
            max_vacancies_active=5,
            max_documents=500,
            max_public_portal_links=1,
            auto_renew=False,
        )
        session.add(license_entry)

        user = User(
            id=str(uuid.uuid4()),
            email=email,
            password_hash=hash_password(payload.password),
            role=UserRole.administrator,
            tenant_id=tenant.id,
            is_active=True,
            full_name=(payload.full_name or "").strip() or None,
            preferences={},
            extra={
                "signup_plan_code": (payload.plan_code or "").strip() or None,
                "signup_consents": {
                    "terms": bool(payload.accept_terms),
                    "privacy": bool(payload.accept_privacy),
                    "accepted_at": datetime.now(timezone.utc).isoformat(),
                    "terms_version": "2025-02-01",
                    "privacy_version": "2025-02-01",
                },
            },
        )
        session.add(user)
        await session.flush()

        await session.execute(
            sa.insert(user_memberships).values(
                id=str(uuid.uuid4()),
                user_id=user.id,
                tenant_id=tenant.id,
                role=UserRole.administrator.value,
                created_at=datetime.now(timezone.utc),
            )
        )

        await session.commit()

    response = RegisterOut(
        user={
            "id": user.id,
            "email": user.email,
            "role": UserRole.administrator.value,
            "tenant_id": tenant.id,
            "full_name": user.full_name,
        },
        tenant={
            "id": tenant.id,
            "name": tenant.name,
            "slug": tenant.slug,
            "workspace_label": tenant.workspace_label,
            "status": tenant.status.value if hasattr(tenant.status, "value") else str(tenant.status),
            "trial_ends_at": trial_expires_at.isoformat(),
            "trial_days": 14,
        },
    )
    try:
        await send_system_email(
            to=email,
            subject="Welcome to HostFlow CRM: your trial is active",
            body=_signup_welcome_email_body(
                workspace_name=workspace_name,
                trial_expires_at=trial_expires_at.isoformat(),
            ),
        )
    except Exception:
        # Registration must not fail due to outbound email issues.
        pass
    return response


@router.post(
    "/login", response_model=TokenOut, tags=["auth"], summary="Auth Login"
)
async def auth_login(payload: LoginIn, request: Request) -> TokenOut:
    """
    Проверяет email/пароль по базе и выдаёт подписанный access-токен.
    """
    email = payload.email.lower().strip()
    password = payload.password

    async with async_session_maker() as session:
        row = await session.execute(
            select(User).where(func.lower(User.email) == email.lower())
        )
        user = row.scalar_one_or_none()
        if user is None or not verify_password(password, user.password_hash):
            raise HTTPException(status_code=401, detail="Invalid credentials")

        membership_row = await session.execute(
            select(
                _user_memberships.c.tenant_id,
                _user_memberships.c.role,
            )
            .where(_user_memberships.c.user_id == user.id)
            .limit(1)
        )
        membership = membership_row.first()

        tenant_id = user.tenant_id or (membership.tenant_id if membership else DEFAULT_TENANT_ID)
        membership_role = membership.role if membership else None
        role_value = _normalize_role(user.role, membership_role)

        now = datetime.now(timezone.utc)
        ttl_minutes = max(5, int(getattr(settings, "auth_token_ttl_minutes", 720) or 720))
        exp = now + timedelta(minutes=ttl_minutes)

        token_payload: Dict[str, Any] = {
            "sub": user.id,
            "email": email,
            "role": role_value,
            "tenant_id": tenant_id,
            "type": "access",
            "iat": int(now.timestamp()),
            "exp": int(exp.timestamp()),
        }
        token = encode_jwt(token_payload)

        client_host = request.client.host if request.client else None
        user_agent = request.headers.get("User-Agent")
        device_label = request.headers.get("X-Device-Name")
        session_entry = await users_service.register_user_session(
            session,
            tenant_id=tenant_id,
            user_id=user.id,
            ip_address=client_host,
            user_agent=user_agent,
            device_label=device_label,
            expires_at=exp,
        )
        await session.commit()

    return TokenOut(
        access_token=token,
        user={"id": user.id, "email": email, "role": role_value, "tenant_id": tenant_id},
        session_id=session_entry.id,
    )


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8, max_length=128)


@router.post("/password/request-reset", tags=["auth"])
async def request_password_reset(payload: PasswordResetRequest):
    """Request password reset link (self-service). Always returns 200 to prevent email enumeration."""
    async with async_session_maker() as session:
        ok = await users_service.request_password_reset(
            db=session, email=payload.email
        )
        await session.commit()
    return {"ok": True, "message": "If the email exists, a reset link was sent."}


@router.post("/password/reset-with-token", tags=["auth"])
async def reset_password_with_token(payload: PasswordResetConfirm):
    """Set new password using reset token from email link."""
    async with async_session_maker() as session:
        ok = await users_service.reset_password_with_token(
            db=session,
            token=payload.token,
            new_password=payload.new_password,
        )
        await session.commit()
    if not ok:
        raise HTTPException(
            status_code=400,
            detail="Invalid or expired token",
        )
    return {"ok": True, "message": "Password updated. You can now log in."}


@router.post("/invite/accept", response_model=UserDetailOut, tags=["auth"])
async def auth_invite_accept(payload: UserInviteAccept) -> UserDetailOut:
    async with async_session_maker() as session:
        try:
            detail = await users_service.accept_invite(
                session,
                token=payload.token,
                password=payload.password,
                full_name=payload.full_name,
                short_id=payload.short_id,
            )
            await session.commit()
        except UserServiceError as exc:
            await session.rollback()
            raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
        except Exception:
            await session.rollback()
            raise
    return UserDetailOut(**detail)
