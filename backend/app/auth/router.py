from __future__ import annotations

from datetime import datetime, timedelta, timezone
import re
import secrets
import string
import uuid
from typing import Any, Dict, Optional

import sqlalchemy as sa
from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, select

from backend.app.auth.jwt_tools import decode as decode_jwt
from backend.app.auth.jwt_tools import encode as encode_jwt
from backend.app.auth.session_cookies import (
    clear_session_cookies,
    new_csrf_token,
    read_csrf_cookie,
    read_refresh_token,
    resolve_access_token,
    set_session_cookies,
)
from backend.app.constants.spa_paths import SETTINGS_BILLING
from backend.app.core.config import settings
from backend.app.core.rate_limit import enforce_rate_limit, rate_limits
from backend.app.core.security import hash_password, verify_password
from backend.app.core.turnstile import require_turnstile
from backend.app.db.session import async_session_maker
from backend.app.models.tenant import Tenant, TenantLicense, TenantStatus, TenantType, user_memberships
from backend.app.models.user import Role as UserRole
from backend.app.models.user import User
from backend.app.schemas.user import UserDetailOut, UserInviteAccept
from backend.app.services.system_email import send_system_email
from backend.app.services import users as users_service
from backend.app.services.auth import (
    issue_refresh_token,
    lookup_active_refresh_token,
    revoke_refresh_token_raw,
    revoke_refresh_tokens,
)
from backend.app.services.users import UserServiceError

router = APIRouter()

DEFAULT_TENANT_ID = "11111111-1111-1111-1111-111111111111"
TRIAL_DAYS = 30

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
    "employee": UserRole.employee.value,
    "manager": UserRole.employee.value,
    "supervisor": UserRole.employee.value,
    "recruiter": UserRole.employee.value,
    "viewer": UserRole.viewer.value,
    "client_manager": UserRole.viewer.value,
    "client": UserRole.viewer.value,
    "client_processor": UserRole.viewer.value,
    "processor": UserRole.viewer.value,
    "superadmin": UserRole.superadmin.value,
    "hr_officer": UserRole.employee.value,
    "people_ops": UserRole.employee.value,
    "hr": UserRole.employee.value,
    "compliance_officer": UserRole.employee.value,
    "compliance": UserRole.employee.value,
    "docs_officer": UserRole.employee.value,
    "lead": UserRole.employee.value,
    "user": UserRole.viewer.value,
}


def _access_context_for_user(user: User, role_value: str) -> str:
    from backend.app.auth.trust_roles import infer_access_context

    prefs = user.preferences if isinstance(user.preferences, dict) else {}
    explicit = prefs.get("access_context")
    return infer_access_context(role_value, explicit if isinstance(explicit, str) else None)


def _preset_id_for_user(user: User, role_value: str) -> str | None:
    from backend.app.auth.trust_roles import resolve_preset_id

    prefs = user.preferences if isinstance(user.preferences, dict) else {}
    return resolve_preset_id(role_value, preferences=prefs)

class LoginIn(BaseModel):
    email: str
    password: str


class RegisterIn(BaseModel):
    email: str
    password: str = Field(..., min_length=8, max_length=128)
    workspace_name: str = Field(..., min_length=2, max_length=128)
    full_name: str | None = Field(default=None, max_length=255)
    plan_code: str | None = Field(default=None, max_length=32)
    accept_terms: bool = False
    accept_privacy: bool = False
    turnstile_token: str | None = Field(default=None, max_length=2048)


class RegisterOut(BaseModel):
    ok: bool = True
    user: Dict[str, Any]
    tenant: Dict[str, Any]
    meta: Dict[str, Any] = Field(default_factory=dict)


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: Dict[str, Any]
    session_id: str | None = None


def _normalize_role(
    user_role: Any,
    membership_role: Optional[str],
) -> str:
    from backend.app.auth.trust_roles import normalize_trust_role

    raw_user_role = str(user_role or "").lower()
    if raw_user_role == UserRole.superadmin.value:
        return UserRole.superadmin.value
    if isinstance(user_role, UserRole) and user_role == UserRole.superadmin:
        return UserRole.superadmin.value
    if membership_role:
        mapped = _ROLE_MAP.get(str(membership_role).lower())
        if mapped:
            return mapped
        return normalize_trust_role(membership_role)
    if isinstance(user_role, UserRole):
        return normalize_trust_role(user_role.value)
    raw = str(user_role or UserRole.viewer.value).lower()
    return _ROLE_MAP.get(raw, normalize_trust_role(raw))


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
    billing_url = f"{base}{SETTINGS_BILLING}"
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
async def auth_register(payload: RegisterIn, request: Request) -> RegisterOut:
    await enforce_rate_limit(request, rate_limits().signup, scope="auth:signup")
    await require_turnstile(request, token=payload.turnstile_token)
    email = payload.email.lower().strip()
    workspace_name = payload.workspace_name.strip()
    if len(workspace_name) < 2:
        raise HTTPException(status_code=422, detail="Workspace name is too short")
    if not payload.accept_terms or not payload.accept_privacy:
        raise HTTPException(status_code=422, detail="Terms and privacy acceptance is required")

    async with async_session_maker() as session:
        existing_user = await session.execute(
            select(User.id).where(func.lower(User.email) == email).limit(1)
        )
        if existing_user.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=409,
                detail="Account already exists. Trial can only be activated once per account.",
            )

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

        trial_expires_at = (datetime.now(timezone.utc) + timedelta(days=TRIAL_DAYS)).date()
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
                "trial_granted_at": datetime.now(timezone.utc).isoformat(),
                "trial_days": TRIAL_DAYS,
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

    welcome_email_sent = False
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
            "trial_days": TRIAL_DAYS,
        },
        meta={"welcome_email_sent": False},
    )
    try:
        welcome_email_sent = await send_system_email(
            to=email,
            subject="Welcome to HostFlow CRM: your trial is active",
            body=_signup_welcome_email_body(
                workspace_name=workspace_name,
                trial_expires_at=trial_expires_at.isoformat(),
            ),
        )
    except Exception:
        # Registration must not fail due to outbound email issues.
        welcome_email_sent = False
    response.meta = {"welcome_email_sent": bool(welcome_email_sent)}
    return response


@router.post(
    "/login", response_model=TokenOut, tags=["auth"], summary="Auth Login"
)
async def auth_login(payload: LoginIn, request: Request, response: Response) -> TokenOut:
    """
    Проверяет email/пароль по базе и выдаёт подписанный access-токен
    + shared session cookies (Stage 6B: Domain=.hostflow.cc).
    """
    await enforce_rate_limit(request, rate_limits().login, scope="auth:login")
    email = payload.email.lower().strip()
    password = payload.password

    async with async_session_maker() as session:
        row = await session.execute(
            select(User).where(func.lower(User.email) == email.lower())
        )
        user = row.scalar_one_or_none()
        if user is None or not verify_password(password, user.password_hash):
            raise HTTPException(status_code=401, detail="Invalid credentials")

        membership = None
        if user.tenant_id:
            membership_row = await session.execute(
                select(
                    _user_memberships.c.tenant_id,
                    _user_memberships.c.role,
                )
                .where(_user_memberships.c.user_id == user.id)
                .where(_user_memberships.c.tenant_id == user.tenant_id)
                .limit(1)
            )
            membership = membership_row.first()
        if not membership:
            membership_row = await session.execute(
                select(
                    _user_memberships.c.tenant_id,
                    _user_memberships.c.role,
                )
                .where(_user_memberships.c.user_id == user.id)
                .order_by(
                    sa.case(
                        (_user_memberships.c.tenant_id == DEFAULT_TENANT_ID, 1),
                        else_=0,
                    )
                )
                .limit(1)
            )
            membership = membership_row.first()

        # JWT tenant must match the membership we use for role (not stale users.tenant_id).
        if membership:
            tenant_id = str(membership.tenant_id)
        else:
            tenant_id = user.tenant_id or DEFAULT_TENANT_ID
        membership_role = membership.role if membership else None
        role_value = _normalize_role(user.role, membership_role)

        now = datetime.now(timezone.utc)
        ttl_minutes = max(5, int(getattr(settings, "auth_token_ttl_minutes", 720) or 720))
        refresh_days = max(1, int(getattr(settings, "auth_refresh_ttl_days", 30) or 30))
        exp = now + timedelta(minutes=ttl_minutes)
        refresh_exp = now + timedelta(days=refresh_days)

        token_payload: Dict[str, Any] = {
            "sub": user.id,
            "email": email,
            "role": role_value,
            "tenant_id": tenant_id,
            "access_context": _access_context_for_user(user, role_value),
            "preset_id": _preset_id_for_user(user, role_value),
            "type": "access",
            "jti": str(uuid.uuid4()),
            "iat": int(now.timestamp()),
            "exp": int(exp.timestamp()),
        }
        token = encode_jwt(token_payload)

        # One refresh family per login: revoke prior refresh rows for this user+tenant.
        await revoke_refresh_tokens(
            session,
            user_id=user.id,
            tenant_id=tenant_id,
            actor_id=user.id,
        )
        refresh_raw = await issue_refresh_token(
            session,
            user_id=user.id,
            tenant_id=tenant_id,
            expires_at=refresh_exp,
            payload={"session_kind": "web"},
        )

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

    csrf = new_csrf_token()
    set_session_cookies(
        response,
        request,
        access_token=token,
        refresh_token=refresh_raw,
        csrf_token=csrf,
        access_max_age=ttl_minutes * 60,
        refresh_max_age=refresh_days * 86400,
    )

    return TokenOut(
        access_token=token,
        user={"id": user.id, "email": email, "role": role_value, "tenant_id": tenant_id, "preset_id": _preset_id_for_user(user, role_value), "access_context": _access_context_for_user(user, role_value)},
        session_id=session_entry.id,
    )


@router.post("/logout", tags=["auth"], summary="Auth Logout")
async def auth_logout(request: Request, response: Response) -> dict[str, bool]:
    """Clear shared session cookies and revoke the refresh token (all subdomains)."""
    raw_refresh = read_refresh_token(request)
    if raw_refresh:
        async with async_session_maker() as session:
            await revoke_refresh_token_raw(session, raw_token=raw_refresh)
            await session.commit()
    clear_session_cookies(response, request)
    return {"ok": True}


@router.post(
    "/session/sync",
    response_model=TokenOut,
    tags=["auth"],
    summary="Sync cookie session for module hosts",
)
async def auth_session_sync(request: Request, response: Response) -> TokenOut:
    """
    Mint Domain=.hostflow.cc session cookies from a valid Bearer (or access cookie).

    Needed when the SPA still has a shell-only localStorage token from before shared
    cookies, or host-only cookies — otherwise module hosts bounce back to /login.
    """
    # Cookie mint is called on every shell/module mount; 10/min login bucket 429s
    # a recruiter who just signed in and is being handed across hosts.
    await enforce_rate_limit(request, "60/minute", scope="auth:session_sync")
    raw = resolve_access_token(request)
    if not raw:
        raise HTTPException(status_code=401, detail="Missing session")
    try:
        claims = decode_jwt(raw)
    except Exception as exc:
        raise HTTPException(status_code=401, detail=f"Invalid session: {exc}") from exc

    user_id = str(claims.get("sub") or "").strip()
    tenant_id = str(claims.get("tenant_id") or "").strip()
    if not user_id or not tenant_id:
        raise HTTPException(status_code=401, detail="Invalid session claims")

    existing_refresh_raw = read_refresh_token(request)
    reused_refresh = False
    session_entry_id: str | None = None

    async with async_session_maker() as session:
        user_row = await session.execute(select(User).where(User.id == user_id))
        user = user_row.scalar_one_or_none()
        if user is None:
            raise HTTPException(status_code=401, detail="Invalid session")

        membership_row = await session.execute(
            select(_user_memberships.c.role)
            .where(_user_memberships.c.user_id == user.id)
            .where(_user_memberships.c.tenant_id == tenant_id)
            .limit(1)
        )
        membership = membership_row.first()
        membership_role = membership.role if membership else None
        role_value = _normalize_role(user.role, membership_role)
        email = str(user.email or claims.get("email") or "").lower().strip()

        now = datetime.now(timezone.utc)
        ttl_minutes = max(5, int(getattr(settings, "auth_token_ttl_minutes", 720) or 720))
        refresh_days = max(1, int(getattr(settings, "auth_refresh_ttl_days", 30) or 30))
        exp = now + timedelta(minutes=ttl_minutes)
        refresh_exp = now + timedelta(days=refresh_days)

        token_payload: Dict[str, Any] = {
            "sub": user.id,
            "email": email,
            "role": role_value,
            "tenant_id": tenant_id,
            "access_context": _access_context_for_user(user, role_value),
            "preset_id": _preset_id_for_user(user, role_value),
            "type": "access",
            "jti": str(uuid.uuid4()),
            "iat": int(now.timestamp()),
            "exp": int(exp.timestamp()),
        }
        token = encode_jwt(token_payload)

        active_refresh = None
        if existing_refresh_raw:
            active_refresh = await lookup_active_refresh_token(
                session, raw_token=existing_refresh_raw
            )
            if (
                active_refresh is None
                or str(active_refresh.user_id) != str(user.id)
                or str(active_refresh.tenant_id) != str(tenant_id)
            ):
                active_refresh = None

        if active_refresh is not None and existing_refresh_raw:
            # Reuse the login refresh family. Revoking here races concurrent
            # POST /login + POST /session/sync and leaves the browser with a
            # revoked hf_refresh (user bounces back to /login with a valid password).
            refresh_raw = existing_refresh_raw
            reused_refresh = True
        else:
            # Bearer-only mint: do not revoke other families — login owns rotation.
            # Concurrent syncs must not invalidate a refresh cookie login just set.
            refresh_raw = await issue_refresh_token(
                session,
                user_id=user.id,
                tenant_id=tenant_id,
                expires_at=refresh_exp,
                payload={"session_kind": "web", "synced": True},
            )
            session_entry = await users_service.register_user_session(
                session,
                tenant_id=tenant_id,
                user_id=user.id,
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("User-Agent"),
                device_label=request.headers.get("X-Device-Name"),
                expires_at=exp,
            )
            session_entry_id = session_entry.id
            await session.commit()

    existing_csrf = read_csrf_cookie(request)
    csrf = existing_csrf if reused_refresh and existing_csrf else new_csrf_token()
    set_session_cookies(
        response,
        request,
        access_token=token,
        refresh_token=refresh_raw,
        csrf_token=csrf,
        access_max_age=ttl_minutes * 60,
        refresh_max_age=refresh_days * 86400,
    )
    return TokenOut(
        access_token=token,
        user={"id": user.id, "email": email, "role": role_value, "tenant_id": tenant_id, "preset_id": _preset_id_for_user(user, role_value), "access_context": _access_context_for_user(user, role_value)},
        session_id=session_entry_id,
    )


@router.post(
    "/refresh",
    response_model=TokenOut,
    tags=["auth"],
    summary="Auth Refresh",
)
async def auth_refresh(request: Request, response: Response) -> TokenOut:
    """Rotate access (and refresh) cookies from the HttpOnly refresh cookie."""
    await enforce_rate_limit(request, rate_limits().login, scope="auth:refresh")
    raw_refresh = read_refresh_token(request)
    if not raw_refresh:
        raise HTTPException(status_code=401, detail="Missing refresh session")

    async with async_session_maker() as session:
        entry = await lookup_active_refresh_token(session, raw_token=raw_refresh)
        if entry is None:
            clear_session_cookies(response, request)
            raise HTTPException(status_code=401, detail="Invalid refresh session")

        user_row = await session.execute(select(User).where(User.id == entry.user_id))
        user = user_row.scalar_one_or_none()
        if user is None:
            await revoke_refresh_token_raw(session, raw_token=raw_refresh)
            await session.commit()
            clear_session_cookies(response, request)
            raise HTTPException(status_code=401, detail="Invalid refresh session")

        tenant_id = str(entry.tenant_id)
        membership_row = await session.execute(
            select(_user_memberships.c.role)
            .where(_user_memberships.c.user_id == user.id)
            .where(_user_memberships.c.tenant_id == tenant_id)
            .limit(1)
        )
        membership = membership_row.first()
        membership_role = membership.role if membership else None
        role_value = _normalize_role(user.role, membership_role)
        email = str(user.email or "").lower().strip()

        now = datetime.now(timezone.utc)
        ttl_minutes = max(5, int(getattr(settings, "auth_token_ttl_minutes", 720) or 720))
        refresh_days = max(1, int(getattr(settings, "auth_refresh_ttl_days", 30) or 30))
        exp = now + timedelta(minutes=ttl_minutes)
        refresh_exp = now + timedelta(days=refresh_days)

        token_payload: Dict[str, Any] = {
            "sub": user.id,
            "email": email,
            "role": role_value,
            "tenant_id": tenant_id,
            "access_context": _access_context_for_user(user, role_value),
            "preset_id": _preset_id_for_user(user, role_value),
            "type": "access",
            "jti": str(uuid.uuid4()),
            "iat": int(now.timestamp()),
            "exp": int(exp.timestamp()),
        }
        token = encode_jwt(token_payload)

        await revoke_refresh_token_raw(session, raw_token=raw_refresh, actor_id=user.id)
        new_refresh = await issue_refresh_token(
            session,
            user_id=user.id,
            tenant_id=tenant_id,
            expires_at=refresh_exp,
            payload={"session_kind": "web", "rotated": True},
        )
        session_entry = await users_service.register_user_session(
            session,
            tenant_id=tenant_id,
            user_id=user.id,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("User-Agent"),
            device_label=request.headers.get("X-Device-Name"),
            expires_at=exp,
        )
        await session.commit()

    csrf = new_csrf_token()
    set_session_cookies(
        response,
        request,
        access_token=token,
        refresh_token=new_refresh,
        csrf_token=csrf,
        access_max_age=ttl_minutes * 60,
        refresh_max_age=refresh_days * 86400,
    )
    return TokenOut(
        access_token=token,
        user={"id": user.id, "email": email, "role": role_value, "tenant_id": tenant_id, "preset_id": _preset_id_for_user(user, role_value), "access_context": _access_context_for_user(user, role_value)},
        session_id=session_entry.id,
    )


class PasswordResetRequest(BaseModel):
    email: EmailStr
    turnstile_token: str | None = Field(default=None, max_length=2048)


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8, max_length=128)


@router.post("/password/request-reset", tags=["auth"])
async def request_password_reset(payload: PasswordResetRequest, request: Request):
    """Request password reset link (self-service). Always returns 200 to prevent email enumeration."""
    await enforce_rate_limit(request, rate_limits().password_reset, scope="auth:password_reset_request")
    await require_turnstile(request, token=payload.turnstile_token)
    async with async_session_maker() as session:
        ok = await users_service.request_password_reset(
            db=session, email=payload.email
        )
        await session.commit()
    return {"ok": True, "message": "If the email exists, a reset link was sent."}


@router.post("/password/reset-with-token", tags=["auth"])
async def reset_password_with_token(payload: PasswordResetConfirm, request: Request):
    """Set new password using reset token from email link."""
    await enforce_rate_limit(request, rate_limits().password_reset, scope="auth:password_reset_confirm")
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


class PublicAuthConfigOut(BaseModel):
    """
    Unauthenticated runtime configuration for login/signup/public intake pages.

    Lets the frontend decide whether to render the Turnstile widget and which
    sitekey to use — without bundling secrets or requiring a separate rebuild
    per environment.
    """
    turnstile_enabled: bool = False
    turnstile_sitekey: str | None = None


@router.get(
    "/public-config",
    response_model=PublicAuthConfigOut,
    tags=["auth"],
    summary="Public runtime config (captcha, feature flags)",
)
async def auth_public_config() -> PublicAuthConfigOut:
    from backend.app.core.turnstile import get_turnstile_sitekey, is_turnstile_enabled

    return PublicAuthConfigOut(
        turnstile_enabled=is_turnstile_enabled(),
        turnstile_sitekey=get_turnstile_sitekey(),
    )
