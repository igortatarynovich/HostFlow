from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

import sqlalchemy as sa
from sqlalchemy import distinct, exists, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from backend.app.core.security import hash_password, verify_password
from backend.app.models.access import UserCompanyAccess
from backend.app.models.audit import UserAuditLog
from backend.app.models.catalogs import (
    user_full_name_expr,
    user_label_expr,
    user_short_expr,
)
from backend.app.models.invite import UserInvite
from backend.app.models.tenant import TenantLicense
from backend.app.models.session import UserSession
from backend.app.models.user import Role, User
from backend.app.models.own_company import OwnCompany
from backend.app.services.audit import log_activity
from backend.app.services.auth import generate_token, hash_token, revoke_refresh_tokens
from backend.app.services.tenant_limits import get_tenant_limits

user_memberships = sa.table(
    "user_memberships",
    sa.column("id"),
    sa.column("user_id"),
    sa.column("tenant_id"),
    sa.column("role"),
    sa.column("created_at"),
)

TENANT_ROLE_VALUES = {role.value for role in Role}
SUPERVISOR_ROLES = {
    Role.superadmin.value,
    Role.administrator.value,
    Role.supervisor.value,
}

ROLE_ALIAS = {
    "owner": Role.administrator.value,
    "admin": Role.administrator.value,
    "administrator": Role.administrator.value,
    "manager": Role.supervisor.value,
    "supervisor": Role.supervisor.value,
    "recruiter": Role.recruiter.value,
    "hr": Role.recruiter.value,
    "viewer": Role.viewer.value,
    "user": Role.viewer.value,
    "client": Role.client_manager.value,
    "client_manager": Role.client_manager.value,
    "client_processor": Role.client_processor.value,
    "processor": Role.client_processor.value,
    "superadmin": Role.superadmin.value,
}

DEFAULT_NOTIFICATION_EVENTS = {
    "candidate.new_assignment": {"enabled": True, "mode": "immediate"},
    "candidate.stage_changed": {"enabled": True, "mode": "immediate"},
    "documents.deadline": {"enabled": True, "mode": "immediate"},
    "mentions.direct": {"enabled": True, "mode": "immediate"},
    "lead.new.telegram": {"enabled": True, "mode": "immediate"},
    "lead.status_changed.telegram": {"enabled": True, "mode": "immediate"},
}

DEFAULT_UI_PREFERENCES = {
    "locale": "ru-RU",
    "timezone": "Europe/Warsaw",
    "date_format": "DD.MM.YYYY",
    "phone_format": "+CC (AAA) BBB-CC-DD",
    "theme": "system",
}

DEFAULT_SAVED_VIEWS = {
    "candidates": [],
    "vacancies": [],
}


class UserServiceError(Exception):
    def __init__(self, detail: Union[str, Dict[str, Any]], status_code: int = 400):
        super().__init__(detail if isinstance(detail, str) else str(detail))
        self.detail = detail
        self.status_code = status_code


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _normalize_role(role: str) -> str:
    value = ROLE_ALIAS.get(str(role or "").strip().lower())
    if not value:
        raise UserServiceError("Unsupported role", 422)
    return value


async def _tenant_row_has_license(db: AsyncSession, tenant_id: str) -> bool:
    stmt = select(TenantLicense.id).where(TenantLicense.tenant_id == tenant_id).limit(1)
    return (await db.execute(stmt)).scalar_one_or_none() is not None


def _quota_attr_for_tenant_role(role: str) -> Optional[str]:
    mapping = {
        Role.recruiter.value: "max_recruiters",
        Role.supervisor.value: "max_supervisors",
        Role.client_manager.value: "max_client_managers",
        Role.client_processor.value: "max_client_managers",
        Role.viewer.value: "max_viewers",
    }
    return mapping.get(role)


async def _get_membership_role_for_tenant(
    db: AsyncSession, tenant_id: str, user_id: str
) -> Optional[str]:
    stmt = (
        select(user_memberships.c.role)
        .where(user_memberships.c.tenant_id == tenant_id)
        .where(user_memberships.c.user_id == user_id)
        .limit(1)
    )
    return (await db.execute(stmt)).scalar_one_or_none()


async def _count_active_users_in_tenant_role(
    db: AsyncSession,
    tenant_id: str,
    role: str,
    *,
    exclude_user_id: Optional[str] = None,
) -> int:
    stmt = (
        select(func.count())
        .select_from(user_memberships)
        .join(User, User.id == user_memberships.c.user_id)
        .where(user_memberships.c.tenant_id == tenant_id)
        .where(user_memberships.c.role == role)
        .where(User.is_active.is_(True))
        .where(User.deleted_at.is_(None))
    )
    if exclude_user_id:
        stmt = stmt.where(User.id != exclude_user_id)
    return int((await db.execute(stmt)).scalar_one() or 0)


async def _count_pending_invites_for_role(
    db: AsyncSession,
    tenant_id: str,
    role: str,
    *,
    exclude_invite_email: Optional[str] = None,
) -> int:
    stmt = (
        select(func.count())
        .select_from(UserInvite)
        .where(UserInvite.tenant_id == tenant_id)
        .where(UserInvite.role == role)
        .where(UserInvite.revoked_at.is_(None))
        .where(UserInvite.accepted_at.is_(None))
    )
    if exclude_invite_email:
        em = exclude_invite_email.strip().lower()
        stmt = stmt.where(func.lower(UserInvite.email) != em)
    return int((await db.execute(stmt)).scalar_one() or 0)


async def _ensure_role_seat_available_for_invite_or_user_add(
    db: AsyncSession,
    tenant_id: str,
    role: str,
    *,
    exclude_invite_email: Optional[str] = None,
) -> None:
    """Hard seat gate when TenantLicense exists (§2.2 / §2.16)."""
    if not await _tenant_row_has_license(db, tenant_id):
        return
    attr = _quota_attr_for_tenant_role(role)
    if not attr:
        return
    limits = await get_tenant_limits(db, tenant_id)
    limit = int(getattr(limits, attr))
    if limit <= 0:
        raise UserServiceError(
            {
                "code": "seat_limit_reached",
                "role": role,
                "limit": limit,
                "current": 0,
            },
            403,
        )
    active = await _count_active_users_in_tenant_role(db, tenant_id, role)
    pending = await _count_pending_invites_for_role(
        db, tenant_id, role, exclude_invite_email=exclude_invite_email
    )
    total = active + pending
    if total >= limit:
        raise UserServiceError(
            {
                "code": "seat_limit_reached",
                "role": role,
                "limit": limit,
                "current": total,
            },
            403,
        )


async def _ensure_role_change_respects_seat_cap(
    db: AsyncSession,
    tenant_id: str,
    *,
    user_id: str,
    old_role: Optional[str],
    new_role: str,
) -> None:
    if old_role == new_role:
        return
    if not await _tenant_row_has_license(db, tenant_id):
        return
    attr = _quota_attr_for_tenant_role(new_role)
    if not attr:
        return
    limits = await get_tenant_limits(db, tenant_id)
    limit = int(getattr(limits, attr))
    if limit <= 0:
        raise UserServiceError(
            {
                "code": "seat_limit_reached",
                "role": new_role,
                "limit": limit,
                "current": 0,
            },
            403,
        )
    active = await _count_active_users_in_tenant_role(
        db, tenant_id, new_role, exclude_user_id=user_id
    )
    pending = await _count_pending_invites_for_role(db, tenant_id, new_role)
    if active + pending >= limit:
        raise UserServiceError(
            {
                "code": "seat_limit_reached",
                "role": new_role,
                "limit": limit,
                "current": active + pending,
            },
            403,
        )


async def _ensure_invite_accept_seat_still_valid(
    db: AsyncSession, tenant_id: str, role: str
) -> None:
    """Blocks accept if license was tightened below current commitments."""
    if not await _tenant_row_has_license(db, tenant_id):
        return
    attr = _quota_attr_for_tenant_role(role)
    if not attr:
        return
    limits = await get_tenant_limits(db, tenant_id)
    limit = int(getattr(limits, attr))
    if limit <= 0:
        raise UserServiceError(
            {
                "code": "seat_limit_reached",
                "role": role,
                "limit": limit,
                "current": 0,
            },
            403,
        )
    active = await _count_active_users_in_tenant_role(db, tenant_id, role)
    pending = await _count_pending_invites_for_role(db, tenant_id, role)
    if active + pending > limit:
        raise UserServiceError(
            {
                "code": "seat_limit_reached",
                "role": role,
                "limit": limit,
                "current": active + pending,
            },
            403,
        )


def _apply_global_role(user: User, tenant_role: str) -> None:
    mapping = {
        Role.viewer.value: Role.viewer,
        Role.recruiter.value: Role.recruiter,
        Role.supervisor.value: Role.supervisor,
        Role.administrator.value: Role.administrator,
        Role.client_manager.value: Role.client_manager,
        Role.client_processor.value: Role.client_processor,
        Role.superadmin.value: Role.superadmin,
    }
    user.role = mapping.get(tenant_role, Role.viewer)


async def record_user_audit(
    db: AsyncSession,
    *,
    tenant_id: str,
    actor_id: str | None,
    target_user_id: str | None,
    action: str,
    payload: Dict[str, Any] | None = None,
) -> UserAuditLog:
    entry = UserAuditLog(
        tenant_id=tenant_id,
        user_id=target_user_id,
        actor_id=actor_id,
        action=action,
        payload=payload or {},
    )
    db.add(entry)
    await db.flush()
    return entry


async def _load_user(
    db: AsyncSession,
    *,
    tenant_id: str,
    user_id: str,
) -> User:
    stmt = select(User).where(User.id == user_id)
    user = (await db.execute(stmt)).scalar_one_or_none()
    if not user:
        raise UserServiceError("User not found", 404)
    if user.tenant_id and user.tenant_id != tenant_id:
        raise UserServiceError("User belongs to another tenant", 403)
    return user


async def _ensure_supervisor(
    db: AsyncSession,
    *,
    tenant_id: str,
    supervisor_id: str,
) -> User:
    supervisor = await _load_user(db, tenant_id=tenant_id, user_id=supervisor_id)
    supervisor_role = supervisor.role.value
    if supervisor_role not in SUPERVISOR_ROLES:
        raise UserServiceError("Supervisor must have role supervisor or administrator", 422)
    if supervisor.tenant_id is None:
        supervisor.tenant_id = tenant_id
    return supervisor


async def _upsert_membership(
    db: AsyncSession,
    *,
    tenant_id: str,
    user_id: str,
    role: str,
) -> None:
    base_values = dict(
        id=str(uuid.uuid4()),
        user_id=user_id,
        tenant_id=tenant_id,
        role=role,
        created_at=_now(),
    )
    bind = getattr(db, "bind", None)
    dialect_name = getattr(getattr(bind, "dialect", None), "name", "sqlite")
    if dialect_name == "sqlite":
        stmt = sa.insert(user_memberships).values(**base_values).prefix_with("OR REPLACE")
    elif dialect_name == "postgresql":
        stmt = (
            pg_insert(user_memberships)
            .values(**base_values)
            .on_conflict_do_update(
                index_elements=[user_memberships.c.user_id, user_memberships.c.tenant_id],
                set_={"role": role, "created_at": _now()},
            )
        )
    else:
        await db.execute(
            sa.delete(user_memberships)
            .where(user_memberships.c.user_id == user_id)
            .where(user_memberships.c.tenant_id == tenant_id)
        )
        stmt = sa.insert(user_memberships).values(**base_values)
    await db.execute(stmt)


async def _replace_company_access(
    db: AsyncSession,
    *,
    tenant_id: str,
    user_id: str,
    company_ids: Sequence[str],
    can_edit: bool = False,
) -> None:
    await db.execute(
        sa.delete(UserCompanyAccess)
        .where(UserCompanyAccess.tenant_id == tenant_id)
        .where(UserCompanyAccess.user_id == user_id)
    )
    unique_ids = {str(cid) for cid in company_ids if cid}
    for company_id in unique_ids:
        db.add(
            UserCompanyAccess(
                tenant_id=tenant_id,
                user_id=user_id,
                company_id=company_id,
                can_edit=can_edit,
            )
        )
    await db.flush()


async def _load_company_access_map(
    db: AsyncSession,
    *,
    tenant_id: str,
    user_ids: Sequence[str],
) -> Dict[str, List[UserCompanyAccess]]:
    if not user_ids:
        return {}
    rows = await db.execute(
        select(UserCompanyAccess)
        .where(UserCompanyAccess.tenant_id == tenant_id)
        .where(UserCompanyAccess.user_id.in_(user_ids))
    )
    mapping: Dict[str, List[UserCompanyAccess]] = {}
    for access in rows.scalars():
        mapping.setdefault(access.user_id, []).append(access)
    return mapping


async def _load_recruiter_map(
    db: AsyncSession,
    *,
    tenant_id: str,
    supervisor_ids: Sequence[str],
) -> Dict[str, List[User]]:
    if not supervisor_ids:
        return {}
    rows = await db.execute(
        select(User)
        .where(User.tenant_id == tenant_id)
        .where(User.supervisor_id.in_(supervisor_ids))
    )
    mapping: Dict[str, List[User]] = {}
    for recruiter in rows.scalars():
        mapping.setdefault(recruiter.supervisor_id, []).append(recruiter)
    return mapping


def _status_for_user(user: User) -> str:
    return "active" if user.is_active and not user.deleted_at else "inactive"


def _compose_user_entry(
    *,
    user: User,
    supervisor_id: Optional[str],
    temporary_password: Optional[str] = None,
    invited_at: Optional[datetime] = None,
    invite_expires_at: Optional[datetime] = None,
    invite_id: Optional[str] = None,
    status: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "user_id": user.id,
        "invite_id": invite_id,
        "email": user.email,
        "role": user.role.value,
        "status": status or _status_for_user(user),
        "is_active": bool(user.is_active),
        "full_name": user.full_name,
        "short_id": user.short_id,
        "supervisor_id": supervisor_id,
        "invited_at": invited_at,
        "invite_expires_at": invite_expires_at,
        "created_at": user.created_at,
        "updated_at": user.updated_at,
        "temporary_password": temporary_password,
    }


async def list_users(
    db: AsyncSession,
    tenant_id: str,
    *,
    role: Optional[str] = None,
    supervisor_id: Optional[str] = None,
    company_id: Optional[str] = None,
    active: Optional[bool] = None,
) -> List[Dict[str, Any]]:
    membership = user_memberships.alias("um")

    stmt = (
        select(User, membership.c.role.label("membership_role"))
        .join(
            membership,
            sa.and_(
                membership.c.user_id == User.id,
                membership.c.tenant_id == tenant_id,
            ),
        )
        .where(sa.or_(User.tenant_id == tenant_id, User.tenant_id.is_(None)))
        .order_by(User.created_at.asc())
    )

    normalized_role: Optional[str] = None
    if role:
        normalized_role = _normalize_role(role)
        stmt = stmt.where(User.role == normalized_role)

    if supervisor_id:
        stmt = stmt.where(User.supervisor_id == supervisor_id)

    if active is not None:
        if active:
            stmt = stmt.where(User.is_active.is_(True)).where(User.deleted_at.is_(None))
        else:
            stmt = stmt.where(sa.or_(User.is_active.is_(False), User.deleted_at.is_not(None)))

    if company_id:
        stmt = stmt.where(
            exists(
                select(UserCompanyAccess.id)
                .where(UserCompanyAccess.tenant_id == tenant_id)
                .where(UserCompanyAccess.company_id == str(company_id))
                .where(UserCompanyAccess.user_id == User.id)
            )
        )

    result = await db.execute(stmt)
    rows = result.all()

    user_ids = [row[0].id for row in rows]
    companies_map = await _load_company_access_map(db, tenant_id=tenant_id, user_ids=user_ids)

    items: List[Dict[str, Any]] = []
    for user, membership_role in rows:
        tenant_role = user.role.value
        if membership_role:
            mapped_role = ROLE_ALIAS.get(str(membership_role).lower())
            if mapped_role:
                tenant_role = mapped_role
        user.role = Role(tenant_role)
        entry = _compose_user_entry(
            user=user,
            supervisor_id=user.supervisor_id,
        )
        if user.id in companies_map:
            entry["company_ids"] = [access.company_id for access in companies_map[user.id]]
        items.append(entry)

    # Include pending invites matching filters
    invite_stmt = (
        select(UserInvite)
        .where(UserInvite.tenant_id == tenant_id)
        .where(UserInvite.revoked_at.is_(None))
        .where(UserInvite.accepted_at.is_(None))
        .order_by(UserInvite.created_at.asc())
    )
    invites = (await db.execute(invite_stmt)).scalars().all()

    for invite in invites:
        invite_role = _normalize_role(invite.role)
        if normalized_role and invite_role != normalized_role:
            continue
        if supervisor_id and invite.supervisor_id and supervisor_id != invite.supervisor_id:
            continue
        if company_id and invite.companies and str(company_id) not in {str(cid) for cid in invite.companies}:
            continue
        items.append(
            {
                "user_id": invite.invited_user_id,
                "invite_id": invite.id,
                "email": invite.email,
                "role": invite_role,
                "status": "invited",
                "is_active": False,
                "full_name": None,
                "short_id": None,
                "supervisor_id": invite.supervisor_id,
                "invited_at": invite.created_at,
                "invite_expires_at": invite.expires_at,
                "created_at": invite.created_at,
                "updated_at": invite.updated_at,
                "company_ids": invite.companies or [],
            }
        )

    return items


async def _get_user_entry(
    db: AsyncSession,
    tenant_id: str,
    user_id: str,
) -> Dict[str, Any]:
    user = await _load_user(db, tenant_id=tenant_id, user_id=user_id)
    entry = _compose_user_entry(
        user=user,
        supervisor_id=user.supervisor_id,
    )
    return entry


def _generate_password(length: int = 16) -> str:
    alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*()"
    base_length = max(length, 12)
    required = [
        secrets.choice("abcdefghijklmnopqrstuvwxyz"),
        secrets.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ"),
        secrets.choice("0123456789"),
        secrets.choice("!@#$%^&*()"),
    ]
    remaining = [secrets.choice(alphabet) for _ in range(base_length - len(required))]
    chars = required + remaining
    secrets.SystemRandom().shuffle(chars)
    candidate = "".join(chars)
    _validate_password_complexity(candidate)
    return candidate


async def create_invite(
    db: AsyncSession,
    *,
    tenant_id: str,
    actor_id: str | None,
    email: str,
    role: str,
    supervisor_id: str | None = None,
    company_ids: Sequence[str] | None = None,
    expires_in_hours: int = 72,
) -> tuple[UserInvite, str]:
    normalized_role = _normalize_role(role)
    normalized_email = email.strip().lower()
    company_ids = company_ids or []

    await _ensure_role_seat_available_for_invite_or_user_add(db, tenant_id, normalized_role)

    existing_invite_stmt = (
        select(UserInvite)
        .where(UserInvite.tenant_id == tenant_id)
        .where(func.lower(UserInvite.email) == normalized_email)
        .where(UserInvite.revoked_at.is_(None))
        .where(UserInvite.accepted_at.is_(None))
        .order_by(UserInvite.created_at.desc())
        .limit(1)
    )
    existing_invite = (await db.execute(existing_invite_stmt)).scalar_one_or_none()
    if existing_invite:
        raise UserServiceError("Invite already exists", 409)

    user_stmt = select(User).where(func.lower(User.email) == normalized_email)
    user = (await db.execute(user_stmt)).scalar_one_or_none()
    invited_user_id: Optional[str] = None
    supervisor_ref: Optional[User] = None

    if normalized_role == Role.recruiter.value:
        if not supervisor_id:
            raise UserServiceError("Recruiter requires supervisor", 422)
        supervisor_ref = await _ensure_supervisor(
            db, tenant_id=tenant_id, supervisor_id=supervisor_id
        )
    elif supervisor_id:
        supervisor_ref = await _ensure_supervisor(
            db, tenant_id=tenant_id, supervisor_id=supervisor_id
        )

    if user:
        if user.tenant_id and user.tenant_id != tenant_id:
            raise UserServiceError("User belongs to another tenant", 409)
        membership_stmt = (
            select(user_memberships.c.role)
            .where(user_memberships.c.user_id == user.id)
            .where(user_memberships.c.tenant_id == tenant_id)
        )
        membership_role = (await db.execute(membership_stmt)).scalar_one_or_none()
        if membership_role and user.is_active:
            raise UserServiceError("User already active in tenant", 409)
        invited_user_id = user.id
        if user.tenant_id is None:
            user.tenant_id = tenant_id
        user.supervisor_id = supervisor_ref.id if supervisor_ref else None
        _apply_global_role(user, normalized_role)
        user.is_active = False
        await _replace_company_access(
            db,
            tenant_id=tenant_id,
            user_id=user.id,
            company_ids=company_ids,
        )
        await db.flush()

    raw_token, token_hash = generate_token("invite")
    expires_at = _now() + timedelta(hours=expires_in_hours)

    invite = UserInvite(
        tenant_id=tenant_id,
        email=normalized_email,
        role=normalized_role,
        supervisor_id=supervisor_ref.id if supervisor_ref else None,
        companies=list(company_ids),
        token_hash=token_hash,
        invited_user_id=invited_user_id,
        expires_at=expires_at,
        created_by=actor_id,
    )
    db.add(invite)
    await db.flush()

    await record_user_audit(
        db,
        tenant_id=tenant_id,
        actor_id=actor_id,
        target_user_id=invited_user_id,
        action="user.invited",
        payload={
            "invite_id": invite.id,
            "email": normalized_email,
            "role": normalized_role,
            "supervisor_id": invite.supervisor_id,
            "company_ids": list(company_ids),
        },
    )
    await log_activity(
        db,
        tenant_id=tenant_id,
        actor_id=actor_id,
        action="user.invited",
        target_type="user",
        target_id=invited_user_id,
        payload={"email": normalized_email, "invite_id": invite.id},
    )

    return invite, raw_token


async def create_user(
    db: AsyncSession,
    *,
    tenant_id: str,
    actor_id: str | None,
    email: str,
    role: str,
    full_name: str | None,
    short_id: str | None,
    password: str | None,
    supervisor_id: str | None = None,
    company_ids: Sequence[str] | None = None,
) -> tuple[Dict[str, Any], str | None]:
    normalized_role = _normalize_role(role)
    normalized_email = email.strip().lower()
    company_ids = company_ids or []

    stmt = select(User).where(func.lower(User.email) == normalized_email)
    user = (await db.execute(stmt)).scalar_one_or_none()

    prev_membership: Optional[str] = None
    if user:
        prev_membership = await _get_membership_role_for_tenant(db, tenant_id, user.id)
    idempotent_active = bool(
        user
        and user.tenant_id == tenant_id
        and user.is_active
        and prev_membership == normalized_role
    )
    if not idempotent_active:
        await _ensure_role_seat_available_for_invite_or_user_add(
            db,
            tenant_id,
            normalized_role,
            exclude_invite_email=normalized_email,
        )

    generated_password: Optional[str] = None
    supervisor_ref: Optional[User] = None

    if normalized_role == Role.recruiter.value:
        if not supervisor_id:
            raise UserServiceError("Recruiter requires supervisor", 422)
        supervisor_ref = await _ensure_supervisor(
            db, tenant_id=tenant_id, supervisor_id=supervisor_id
        )
    elif supervisor_id:
        supervisor_ref = await _ensure_supervisor(
            db, tenant_id=tenant_id, supervisor_id=supervisor_id
        )

    if user:
        if user.tenant_id and user.tenant_id != tenant_id:
            raise UserServiceError("User belongs to another tenant", 409)

        if password:
            user.password_hash = hash_password(password)
        elif not user.password_hash:
            generated_password = _generate_password()
            user.password_hash = hash_password(generated_password)

        user.full_name = full_name or user.full_name
        user.short_id = short_id or user.short_id
        user.tenant_id = tenant_id
        user.supervisor_id = supervisor_ref.id if supervisor_ref else None
        user.is_active = True
        user.revive()
    else:
        generated_password = password or _generate_password()
        hashed = hash_password(generated_password)
        user = User(
            id=str(uuid.uuid4()),
            email=normalized_email,
            password_hash=hashed,
            tenant_id=tenant_id,
            is_active=True,
            full_name=full_name,
            short_id=short_id,
            supervisor_id=supervisor_ref.id if supervisor_ref else None,
        )
        db.add(user)

    _apply_global_role(user, normalized_role)
    await db.flush()

    await _replace_company_access(
        db,
        tenant_id=tenant_id,
        user_id=user.id,
        company_ids=company_ids,
    )

    await _upsert_membership(
        db, tenant_id=tenant_id, user_id=user.id, role=normalized_role
    )

    await record_user_audit(
        db,
        tenant_id=tenant_id,
        actor_id=actor_id,
        target_user_id=user.id,
        action="user.created",
        payload={
            "role": normalized_role,
            "supervisor_id": supervisor_ref.id if supervisor_ref else None,
        },
    )

    await log_activity(
        db,
        tenant_id=tenant_id,
        actor_id=actor_id,
        action="user.created",
        target_type="user",
        target_id=user.id,
        payload={"role": normalized_role, "supervisor_id": supervisor_ref.id if supervisor_ref else None},
    )

    entry = await _get_user_entry(db, tenant_id, user.id)
    entry["company_ids"] = list(company_ids)

    return entry, (generated_password if password is None else None)


async def change_user_role(
    db: AsyncSession,
    *,
    tenant_id: str,
    actor_id: str | None,
    user_id: str,
    role: str,
) -> Dict[str, Any]:
    normalized_role = _normalize_role(role)
    user = await _load_user(db, tenant_id=tenant_id, user_id=user_id)
    prev_membership = await _get_membership_role_for_tenant(db, tenant_id, user_id)
    await _ensure_role_change_respects_seat_cap(
        db,
        tenant_id,
        user_id=user_id,
        old_role=prev_membership,
        new_role=normalized_role,
    )

    _apply_global_role(user, normalized_role)
    user.updated_at = _now()
    await db.flush()

    await _upsert_membership(
        db, tenant_id=tenant_id, user_id=user.id, role=normalized_role
    )

    await record_user_audit(
        db,
        tenant_id=tenant_id,
        actor_id=actor_id,
        target_user_id=user.id,
        action="user.role_changed",
        payload={"role": normalized_role},
    )
    await log_activity(
        db,
        tenant_id=tenant_id,
        actor_id=actor_id,
        action="user.role_changed",
        target_type="user",
        target_id=user.id,
        payload={"role": normalized_role},
    )
    await db.flush()
    return await _get_user_entry(db, tenant_id, user.id)


async def update_user_supervisor(
    db: AsyncSession,
    *,
    tenant_id: str,
    actor_id: str | None,
    user_id: str,
    supervisor_id: str | None,
) -> Dict[str, Any]:
    user = await _load_user(db, tenant_id=tenant_id, user_id=user_id)
    supervisor_ref: Optional[User] = None

    if supervisor_id:
        if supervisor_id == user_id:
            raise UserServiceError("User cannot supervise self", 422)
        supervisor_ref = await _ensure_supervisor(
            db, tenant_id=tenant_id, supervisor_id=supervisor_id
        )
        user.supervisor_id = supervisor_ref.id
    else:
        user.supervisor_id = None

    await record_user_audit(
        db,
        tenant_id=tenant_id,
        actor_id=actor_id,
        target_user_id=user.id,
        action="user.supervisor_assigned",
        payload={"supervisor_id": supervisor_ref.id if supervisor_ref else None},
    )
    await log_activity(
        db,
        tenant_id=tenant_id,
        actor_id=actor_id,
        action="user.supervisor_assigned",
        target_type="user",
        target_id=user.id,
        payload={"supervisor_id": supervisor_ref.id if supervisor_ref else None},
    )
    await db.flush()
    return await _get_user_entry(db, tenant_id, user.id)


async def update_user_companies(
    db: AsyncSession,
    *,
    tenant_id: str,
    actor_id: str | None,
    user_id: str,
    company_ids: Sequence[str] | None = None,
) -> Dict[str, Any]:
    normalized_ids = [str(cid) for cid in (company_ids or []) if cid]
    await _load_user(db, tenant_id=tenant_id, user_id=user_id)

    await _replace_company_access(
        db,
        tenant_id=tenant_id,
        user_id=user_id,
        company_ids=normalized_ids,
    )

    await record_user_audit(
        db,
        tenant_id=tenant_id,
        actor_id=actor_id,
        target_user_id=user_id,
        action="user.company_access_updated",
        payload={"company_ids": normalized_ids},
    )
    await log_activity(
        db,
        tenant_id=tenant_id,
        actor_id=actor_id,
        action="user.company_access_updated",
        target_type="user",
        target_id=user_id,
        payload={"company_ids": normalized_ids},
    )
    return await get_user_detail(db, tenant_id=tenant_id, user_id=user_id)


async def update_user_own_company_access(
    db: AsyncSession,
    *,
    tenant_id: str,
    actor_id: str | None,
    user_id: str,
    allowed_own_company_ids: Sequence[str],
) -> Dict[str, Any]:
    """Restrict user to a subset of tenant own-companies (empty list clears ACL)."""
    user = await _load_user(db, tenant_id=tenant_id, user_id=user_id)
    normalized = sorted({str(x).strip() for x in allowed_own_company_ids if x and str(x).strip()})

    prefs = dict(user.preferences or {})
    prev_allowed = prefs.get("allowed_own_company_ids")
    prev_active = str(prefs.get("active_own_company_id") or "").strip() or None

    if not normalized:
        prefs.pop("allowed_own_company_ids", None)
        allowed_set: set[str] | None = None
    else:
        cnt_row = await db.execute(
            select(func.count())
            .select_from(OwnCompany)
            .where(
                OwnCompany.tenant_id == tenant_id,
                OwnCompany.is_archived.is_(False),
                OwnCompany.id.in_(normalized),
            )
        )
        found = int(cnt_row.scalar_one() or 0)
        if found != len(normalized):
            raise UserServiceError("One or more own company ids are invalid or archived", 422)
        prefs["allowed_own_company_ids"] = list(normalized)
        allowed_set = set(normalized)

    if allowed_set:
        active = str(prefs.get("active_own_company_id") or "").strip()
        if active and active not in allowed_set:
            first_row = await db.execute(
                select(OwnCompany.id)
                .where(
                    OwnCompany.tenant_id == tenant_id,
                    OwnCompany.is_archived.is_(False),
                    OwnCompany.id.in_(allowed_set),
                )
                .order_by(OwnCompany.created_at.asc())
                .limit(1)
            )
            first = first_row.scalar_one_or_none()
            if first:
                prefs["active_own_company_id"] = str(first)
            else:
                prefs.pop("active_own_company_id", None)

    user.preferences = prefs
    user.updated_at = _now()
    await db.flush()

    await record_user_audit(
        db,
        tenant_id=tenant_id,
        actor_id=actor_id,
        target_user_id=user_id,
        action="user.own_company_access_updated",
        payload={
            "allowed_own_company_ids": normalized if normalized else None,
            "previous_allowed": prev_allowed,
            "active_own_company_id": prefs.get("active_own_company_id"),
            "previous_active": prev_active,
        },
    )
    await log_activity(
        db,
        tenant_id=tenant_id,
        actor_id=actor_id,
        action="user.own_company_access_updated",
        target_type="user",
        target_id=user_id,
        payload={
            "allowed_own_company_ids": normalized if normalized else None,
            "previous_active": prev_active,
        },
    )
    return await get_user_detail(db, tenant_id=tenant_id, user_id=user_id)


async def set_user_active(
    db: AsyncSession,
    *,
    tenant_id: str,
    actor_id: str | None,
    user_id: str,
    is_active: bool,
) -> Dict[str, Any]:
    user = await _load_user(db, tenant_id=tenant_id, user_id=user_id)
    if is_active:
        user.revive()
        action = "user.activated"
    else:
        user.mark_deleted()
        action = "user.deactivated"
    user.updated_at = _now()
    await db.flush()

    await record_user_audit(
        db,
        tenant_id=tenant_id,
        actor_id=actor_id,
        target_user_id=user.id,
        action=action,
        payload={"is_active": is_active},
    )
    await log_activity(
        db,
        tenant_id=tenant_id,
        actor_id=actor_id,
        action=action,
        target_type="user",
        target_id=user.id,
        payload={"is_active": is_active},
    )
    return await _get_user_entry(db, tenant_id, user.id)


async def change_user_password(
    db: AsyncSession,
    *,
    tenant_id: str,
    actor_id: str | None,
    user_id: str,
    new_password: str,
    revoke_sessions: bool = True,
) -> int:
    password_value = (new_password or "").strip()
    _validate_password_complexity(password_value)
    user = await _load_user(db, tenant_id=tenant_id, user_id=user_id)
    user.password_hash = hash_password(password_value)
    user.updated_at = _now()
    await db.flush()

    revoked = 0
    if revoke_sessions:
        revoked = await revoke_user_sessions(
            db,
            tenant_id=tenant_id,
            user_id=user.id,
            actor_id=actor_id,
        )

    await record_user_audit(
        db,
        tenant_id=tenant_id,
        actor_id=actor_id,
        target_user_id=user.id,
        action="user.password_changed_by_admin",
        payload={"revoked_sessions": revoked},
    )
    await log_activity(
        db,
        tenant_id=tenant_id,
        actor_id=actor_id,
        action="user.password_changed_by_admin",
        target_type="user",
        target_id=user.id,
        payload={"revoked_sessions": revoked},
    )
    return revoked


async def reset_user_password(
    db: AsyncSession,
    *,
    tenant_id: str,
    actor_id: str | None,
    user_id: str,
    revoke_sessions: bool = True,
    send_email: bool = True,
) -> Tuple[str, int]:
    user = await _load_user(db, tenant_id=tenant_id, user_id=user_id)
    user.password_hash = hash_password(secrets.token_urlsafe(32))
    user.updated_at = _now()
    await db.flush()
    revoked = 0
    if revoke_sessions:
        revoked = await revoke_user_sessions(
            db,
            tenant_id=tenant_id,
            user_id=user.id,
            actor_id=actor_id,
        )

    if send_email and user.email:
        try:
            from backend.app.core.settings import settings
            from backend.app.services.system_email import send_system_email

            raw_token, token_hash = generate_token("pwreset")
            expires_at = _now() + timedelta(hours=24)
            from backend.app.models.password_reset_token import PasswordResetToken

            prt = PasswordResetToken(
                user_id=user.id,
                token_hash=token_hash,
                expires_at=expires_at,
            )
            db.add(prt)
            await db.flush()

            base = (settings.frontend_url or "").strip()
            link = f"{base}/reset-password?token={raw_token}" if base else ""
            body = (
                f"Dzień dobry,\n\n"
                f"Administrator zresetował Twoje hasło do HostFlow.\n\n"
                f"Kliknij link, aby ustawić nowe hasło (ważny 24h):\n{link}\n\n"
                if link
                else f"Token do ustawienia hasła (ważny 24h): {raw_token}\n\n"
            )
            body += "Pozdrawiamy,\nZespół HostFlow"
            await send_system_email(
                to=user.email,
                subject="HostFlow – ustaw nowe hasło",
                body=body,
            )
        except Exception:
            pass

    await record_user_audit(
        db,
        tenant_id=tenant_id,
        actor_id=actor_id,
        target_user_id=user.id,
        action="user.password_reset",
        payload={"revoked_sessions": revoked},
    )
    await log_activity(
        db,
        tenant_id=tenant_id,
        actor_id=actor_id,
        action="user.password_reset",
        target_type="user",
        target_id=user.id,
        payload={"revoked_sessions": revoked},
    )
    return "", revoked


async def request_password_reset(db: AsyncSession, *, email: str) -> bool:
    """Create password reset token and send email. Returns True if email sent (user exists)."""
    from backend.app.models.password_reset_token import PasswordResetToken

    email = (email or "").strip().lower()
    if not email or "@" not in email:
        return False
    stmt = select(User).where(func.lower(User.email) == email)
    user = (await db.execute(stmt)).scalar_one_or_none()
    if not user or user.deleted_at:
        return True

    raw_token, token_hash = generate_token("pwreset")
    expires_at = _now() + timedelta(hours=24)
    prt = PasswordResetToken(user_id=user.id, token_hash=token_hash, expires_at=expires_at)
    db.add(prt)
    await db.flush()

    try:
        from backend.app.core.settings import settings
        from backend.app.services.system_email import send_system_email

        base = (settings.frontend_url or "").strip()
        link = f"{base}/reset-password?token={raw_token}" if base else ""
        body = (
            f"Dzień dobry,\n\n"
            f"Otrzymałeś prośbę o zresetowanie hasła do HostFlow.\n\n"
            f"Kliknij link, aby ustawić nowe hasło (ważny 24h):\n{link}\n\n"
            if link
            else f"Token (ważny 24h): {raw_token}\n\n"
        )
        body += "Jeśli to nie Ty, zignoruj tę wiadomość.\n\nPozdrawiamy,\nZespół HostFlow"
        await send_system_email(
            to=user.email,
            subject="HostFlow – reset hasła",
            body=body,
        )
        return True
    except Exception:
        return False


async def reset_password_with_token(
    db: AsyncSession, *, token: str, new_password: str
) -> bool:
    """Verify token and set new password. Returns True on success."""
    from backend.app.models.password_reset_token import PasswordResetToken

    raw = (token or "").strip()
    if not raw or len(raw) < 16:
        return False
    token_hash = hash_token(raw)
    now = _now()

    stmt = (
        select(PasswordResetToken)
        .where(PasswordResetToken.token_hash == token_hash)
        .where(PasswordResetToken.used_at.is_(None))
    )
    prt = (await db.execute(stmt)).scalar_one_or_none()
    if not prt:
        return False
    exp = prt.expires_at
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)
    if exp < now:
        return False

    user = await db.get(User, prt.user_id)
    if not user or user.deleted_at:
        return False

    user.password_hash = hash_password(new_password)
    user.updated_at = now
    prt.used_at = now
    await db.flush()
    return True


async def delete_user(
    db: AsyncSession,
    *,
    tenant_id: str,
    actor_id: str | None,
    user_id: str,
) -> Dict[str, int]:
    if actor_id and actor_id == user_id:
        raise UserServiceError("Cannot delete self", 400)
    user = await _load_user(db, tenant_id=tenant_id, user_id=user_id)
    user.mark_deleted()
    user.updated_at = _now()

    await db.execute(
        sa.delete(user_memberships)
        .where(user_memberships.c.user_id == user.id)
        .where(user_memberships.c.tenant_id == tenant_id)
    )
    await db.execute(
        sa.delete(UserCompanyAccess)
        .where(UserCompanyAccess.tenant_id == tenant_id)
        .where(UserCompanyAccess.user_id == user.id)
    )
    revoked = await revoke_user_sessions(
        db,
        tenant_id=tenant_id,
        user_id=user.id,
        actor_id=actor_id,
    )
    await db.flush()

    await record_user_audit(
        db,
        tenant_id=tenant_id,
        actor_id=actor_id,
        target_user_id=user.id,
        action="user.deleted",
        payload={"revoked_sessions": revoked},
    )
    await log_activity(
        db,
        tenant_id=tenant_id,
        actor_id=actor_id,
        action="user.deleted",
        target_type="user",
        target_id=user.id,
        payload={"revoked_sessions": revoked},
    )
    return {"revoked_sessions": revoked}


async def revoke_user_refresh_tokens(
    db: AsyncSession,
    *,
    tenant_id: str,
    actor_id: str | None,
    user_id: str,
) -> int:
    await _load_user(db, tenant_id=tenant_id, user_id=user_id)
    revoked = await revoke_refresh_tokens(
        db, user_id=user_id, tenant_id=tenant_id, actor_id=actor_id
    )
    await record_user_audit(
        db,
        tenant_id=tenant_id,
        actor_id=actor_id,
        target_user_id=user_id,
        action="user.refresh_revoked",
        payload={"revoked": revoked},
    )
    await log_activity(
        db,
        tenant_id=tenant_id,
        actor_id=actor_id,
        action="user.refresh_revoked",
        target_type="user",
        target_id=user_id,
        payload={"revoked": revoked},
    )
    return revoked


async def list_user_audit(
    db: AsyncSession,
    *,
    tenant_id: str,
    user_id: str,
    limit: int = 100,
) -> List[UserAuditLog]:
    stmt = (
        select(UserAuditLog)
        .where(UserAuditLog.tenant_id == tenant_id)
        .where(UserAuditLog.user_id == user_id)
        .order_by(UserAuditLog.created_at.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def list_tenant_audit(
    db: AsyncSession,
    *,
    tenant_id: str,
    user_id: Optional[str] = None,
    action: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    limit: int = 200,
    offset: int = 0,
) -> Tuple[List[Dict[str, Any]], int]:
    """List audit entries for the tenant with optional filters. Returns (items, total)."""
    stmt = (
        select(UserAuditLog)
        .where(UserAuditLog.tenant_id == tenant_id)
        .order_by(UserAuditLog.created_at.desc())
    )
    count_stmt = (
        select(func.count())
        .select_from(UserAuditLog)
        .where(UserAuditLog.tenant_id == tenant_id)
    )
    if user_id:
        stmt = stmt.where(UserAuditLog.user_id == user_id)
        count_stmt = count_stmt.where(UserAuditLog.user_id == user_id)
    if action:
        stmt = stmt.where(UserAuditLog.action == action)
        count_stmt = count_stmt.where(UserAuditLog.action == action)
    if date_from:
        stmt = stmt.where(UserAuditLog.created_at >= date_from)
        count_stmt = count_stmt.where(UserAuditLog.created_at >= date_from)
    if date_to:
        stmt = stmt.where(UserAuditLog.created_at <= date_to)
        count_stmt = count_stmt.where(UserAuditLog.created_at <= date_to)

    total = (await db.execute(count_stmt)).scalar() or 0
    stmt = stmt.offset(offset).limit(limit)
    result = await db.execute(stmt)
    logs = list(result.scalars().all())

    user_ids = {log.actor_id for log in logs if log.actor_id}
    user_ids.update({log.user_id for log in logs if log.user_id})
    user_ids.discard(None)
    users_map: Dict[str, Dict] = {}
    if user_ids:
        users_rows = await db.execute(
            select(User.id, User.full_name, User.email, User.short_id)
            .where(User.id.in_(user_ids))
        )
        for row in users_rows.all():
            users_map[row.id] = {
                "full_name": row.full_name,
                "email": row.email,
                "short_id": row.short_id,
            }

    items = []
    for log in logs:
        actor = users_map.get(log.actor_id or "", {}) if log.actor_id else {}
        user = users_map.get(log.user_id or "", {}) if log.user_id else {}
        items.append({
            "id": log.id,
            "tenant_id": log.tenant_id,
            "user_id": log.user_id,
            "user_label": (user.get("full_name") or user.get("email") or log.user_id or ""),
            "actor_id": log.actor_id,
            "actor_label": (actor.get("full_name") or actor.get("email") or log.actor_id or "—"),
            "action": log.action,
            "payload": log.payload,
            "created_at": log.created_at,
        })
    return items, int(total)


async def get_user_detail(
    db: AsyncSession,
    *,
    tenant_id: str,
    user_id: str,
) -> Dict[str, Any]:
    user = await _load_user(db, tenant_id=tenant_id, user_id=user_id)
    entry = _compose_user_entry(
        user=user,
        supervisor_id=user.supervisor_id,
    )
    companies_map = await _load_company_access_map(
        db, tenant_id=tenant_id, user_ids=[user.id]
    )
    entry["companies"] = [
        {"company_id": access.company_id, "can_edit": bool(access.can_edit)}
        for access in companies_map.get(user.id, [])
    ]
    entry["recruiters"] = []

    if user.role == Role.supervisor:
        recruiter_map = await _load_recruiter_map(
            db, tenant_id=tenant_id, supervisor_ids=[user.id]
        )
        for recruiter in recruiter_map.get(user.id, []):
            entry["recruiters"].append(
                {
                    "user_id": recruiter.id,
                    "email": recruiter.email,
                    "full_name": recruiter.full_name,
                    "short_id": recruiter.short_id,
                    "status": _status_for_user(recruiter),
                }
            )

    raw_prefs = user.preferences or {}
    raw_al = raw_prefs.get("allowed_own_company_ids") if isinstance(raw_prefs, dict) else None
    if isinstance(raw_al, (list, tuple)):
        ids = [str(x).strip() for x in raw_al if x is not None and str(x).strip()]
        entry["allowed_own_company_ids"] = ids if ids else None
    else:
        entry["allowed_own_company_ids"] = None
    return entry


async def accept_invite(
    db: AsyncSession,
    *,
    token: str,
    password: str,
    full_name: str | None = None,
    short_id: str | None = None,
) -> Dict[str, Any]:
    raw_token = (token or "").strip()
    if not raw_token:
        raise UserServiceError("Invite token is required", 422)
    password_value = (password or "").strip()
    if len(password_value) < 8:
        raise UserServiceError("Password must be at least 8 characters", 422)

    token_hash = hash_token(raw_token)
    now = _now()

    invite_stmt = (
        select(UserInvite)
        .where(UserInvite.token_hash == token_hash)
        .where(UserInvite.revoked_at.is_(None))
    )
    invite = (await db.execute(invite_stmt)).scalar_one_or_none()
    if invite is None:
        raise UserServiceError("Invite not found", 404)
    if invite.accepted_at is not None:
        raise UserServiceError("Invite already used", 409)
    if invite.expires_at:
        expires_at = invite.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at < now:
            raise UserServiceError("Invite expired", 410)

    tenant_id = invite.tenant_id
    await _ensure_invite_accept_seat_still_valid(db, tenant_id, invite.role)
    supervisor_candidate_id = invite.supervisor_id

    user: User | None = None
    if invite.invited_user_id:
        user = await _load_user(db, tenant_id=tenant_id, user_id=invite.invited_user_id)
    else:
        existing_stmt = select(User).where(func.lower(User.email) == invite.email.lower())
        user = (await db.execute(existing_stmt)).scalar_one_or_none()
        if user and user.tenant_id and user.tenant_id != tenant_id:
            raise UserServiceError("User belongs to another tenant", 409)
        if user is None:
            user = User(
                email=invite.email,
                tenant_id=tenant_id,
                is_active=True,
                password_hash=hash_password(password_value),
            )
            db.add(user)
            await db.flush()

    # Determine supervisor
    if supervisor_candidate_id is None and user.supervisor_id:
        supervisor_candidate_id = user.supervisor_id

    supervisor_ref: User | None = None
    if supervisor_candidate_id:
        supervisor_ref = await _ensure_supervisor(
            db,
            tenant_id=tenant_id,
            supervisor_id=supervisor_candidate_id,
        )
    elif invite.role == Role.recruiter.value:
        raise UserServiceError("Recruiter invite requires supervisor", 422)

    # Update user profile
    user.email = invite.email
    user.tenant_id = tenant_id
    user.is_active = True
    user.deleted_at = None
    user.password_hash = hash_password(password_value)
    if full_name is not None:
        full_value = full_name.strip()
        user.full_name = full_value or None
    if short_id is not None:
        short_value = short_id.strip()
        user.short_id = short_value or None
    user.supervisor_id = supervisor_ref.id if supervisor_ref else None
    _apply_global_role(user, invite.role)
    user.updated_at = now
    await db.flush()

    await _upsert_membership(
        db,
        tenant_id=tenant_id,
        user_id=user.id,
        role=invite.role,
    )

    company_ids = [str(cid) for cid in (invite.companies or []) if cid]
    await _replace_company_access(
        db,
        tenant_id=tenant_id,
        user_id=user.id,
        company_ids=company_ids,
    )

    invite.invited_user_id = user.id
    invite.accepted_at = now
    invite.used_at = now

    await record_user_audit(
        db,
        tenant_id=tenant_id,
        actor_id=user.id,
        target_user_id=user.id,
        action="user.invite_accepted",
        payload={
            "invite_id": invite.id,
            "role": invite.role,
            "company_ids": company_ids,
        },
    )
    await log_activity(
        db,
        tenant_id=tenant_id,
        actor_id=user.id,
        action="user.invite_accepted",
        target_type="user",
        target_id=user.id,
        payload={
            "invite_id": invite.id,
            "role": invite.role,
            "company_ids": company_ids,
        },
    )

    detail = await get_user_detail(db, tenant_id=tenant_id, user_id=user.id)
    detail["invite_id"] = invite.id
    detail["status"] = _status_for_user(user)
    detail["company_ids"] = [c["company_id"] for c in detail.get("companies", [])]
    return detail


async def get_tenant_managers(db: AsyncSession, tenant_id: str) -> List[Dict]:
    label_expr = user_label_expr()
    full_expr = user_full_name_expr()
    short_expr = user_short_expr()

    stmt = (
        select(
            distinct(User.id).label("id"),
            label_expr.label("label"),
            short_expr.label("short_id"),
            full_expr.label("full_name"),
            User.email.label("email"),
        )
        .select_from(User)
        .join(user_memberships, user_memberships.c.user_id == User.id)
        .where(user_memberships.c.tenant_id == tenant_id)
        .where(
            user_memberships.c.role.in_(
                [Role.supervisor.value, Role.administrator.value, Role.recruiter.value]
            )
        )
        .order_by(full_expr.asc())
    )

    rows = (await db.execute(stmt)).all()
    return [
        {
            "id": r.id,
            "short_id": r.short_id,
            "full_name": r.full_name,
            "email": r.email,
            "label": r.label or r.full_name or r.email,
        }
        for r in rows
    ]


def _ensure_profile_extra(extra: dict[str, Any] | None) -> dict[str, Any]:
    base = dict(extra or {})
    profile = base.get("profile")
    if not isinstance(profile, dict):
        profile = {}
    avatar = profile.get("avatar_url")
    if isinstance(avatar, str):
        avatar = avatar.strip() or None
    else:
        avatar = None
    profile["avatar_url"] = avatar
    base["profile"] = profile
    return base


def _sanitize_optional_str(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        trimmed = value.strip()
        return trimmed or None
    return str(value)


def _validate_birth_date(value: str | None) -> str | None:
    if value is None:
        return None
    trimmed = value.strip()
    if not trimmed:
        return None
    try:
        datetime.strptime(trimmed, "%Y-%m-%d")
    except ValueError as exc:
        raise UserServiceError("birth_date must be YYYY-MM-DD", 422) from exc
    return trimmed


def _ensure_preferences_structure(preferences: dict[str, Any] | None) -> dict[str, Any]:
    base = dict(preferences or {})

    ui_source = base.get("ui") if isinstance(base.get("ui"), dict) else {}
    ui_prefs = dict(DEFAULT_UI_PREFERENCES)
    for key, default_val in DEFAULT_UI_PREFERENCES.items():
        value = ui_source.get(key)
        if value is None:
            ui_prefs[key] = default_val
        elif isinstance(value, str):
            ui_prefs[key] = value.strip() or default_val
        else:
            ui_prefs[key] = value

    notifications_source = base.get("notifications")
    notifications: dict[str, dict[str, Any]] = {
        key: {"enabled": cfg["enabled"], "mode": cfg["mode"]}
        for key, cfg in DEFAULT_NOTIFICATION_EVENTS.items()
    }
    if isinstance(notifications_source, dict):
        for key, cfg in notifications_source.items():
            if not isinstance(cfg, dict):
                continue
            enabled = bool(cfg.get("enabled", True))
            mode = str(cfg.get("mode", "immediate")).strip().lower()
            if mode not in {"immediate", "daily_digest"}:
                mode = "immediate"
            notifications[key] = {"enabled": enabled, "mode": mode}

    defaults_src = base.get("defaults") if isinstance(base.get("defaults"), dict) else {}
    defaults = {
        "company_id": _sanitize_optional_str(defaults_src.get("company_id")),
    }

    saved_src = base.get("saved_views") if isinstance(base.get("saved_views"), dict) else {}
    saved_views: dict[str, list[dict[str, Any]]] = {key: [] for key in ("candidates", "vacancies")}
    for module in saved_views.keys():
        entries = saved_src.get(module)
        if not isinstance(entries, list):
            continue
        cleaned: list[dict[str, Any]] = []
        for entry in entries[:20]:
            if not isinstance(entry, dict):
                continue
            vid = _sanitize_optional_str(entry.get("id"))
            name = _sanitize_optional_str(entry.get("name"))
            if not vid or not name:
                continue
            filters = entry.get("filters") if isinstance(entry.get("filters"), dict) else {}
            cleaned.append(
                {
                    "id": vid,
                    "name": name,
                    "filters": filters,
                    "is_default": bool(entry.get("is_default", False)),
                }
            )
        saved_views[module] = cleaned

    result: dict[str, Any] = {
        "ui": ui_prefs,
        "notifications": notifications,
        "defaults": defaults,
        "saved_views": saved_views,
    }
    # Preserve multi-workspace keys not managed by structured UI blocks (§2.4 ACL / switcher).
    for key in ("active_own_company_id", "allowed_own_company_ids"):
        if key in base:
            result[key] = base[key]
    return result


def _extract_profile_dict(user: User) -> Dict[str, Any]:
    extra = _ensure_profile_extra(user.extra)
    profile = extra["profile"]
    return {
        "user_id": user.id,
        "email": user.email,
        "tenant_id": user.tenant_id,
        "role": user.role.value,
        "first_name": profile.get("first_name"),
        "last_name": profile.get("last_name"),
        "birth_date": profile.get("birth_date"),
        "country": profile.get("country"),
        "city": profile.get("city"),
        "position": profile.get("position"),
        "phone": profile.get("phone"),
        "avatar_url": profile.get("avatar_url"),
    }


async def _build_security_summary(
    db: AsyncSession,
    *,
    tenant_id: str,
    user: User,
) -> Dict[str, Any]:
    companies_map = await _load_company_access_map(db, tenant_id=tenant_id, user_ids=[user.id])
    companies = [
        {
            "id": access.company_id,
            "name": access.company_id,
            "can_edit": bool(access.can_edit),
        }
        for access in companies_map.get(user.id, [])
    ]

    supervisor_info = None
    if user.supervisor_id:
        stmt = select(User.id, User.full_name, User.email).where(User.id == user.supervisor_id)
        sup = (await db.execute(stmt)).first()
        if sup:
            supervisor_info = {
                "id": sup.id,
                "name": sup.full_name,
                "email": sup.email,
            }

    sessions_stmt = (
        select(UserSession)
        .where(UserSession.user_id == user.id)
        .where(UserSession.tenant_id == tenant_id)
        .where(UserSession.revoked_at.is_(None))
        .order_by(UserSession.last_seen_at.desc())
    )
    sessions = (await db.execute(sessions_stmt)).scalars().all()
    last_login = sessions[0].last_seen_at if sessions else None

    return {
        "role": user.role.value,
        "companies": companies,
        "supervisor": supervisor_info,
        "last_login_at": last_login,
        "sessions_count": len(sessions),
    }


async def get_user_me(
    db: AsyncSession,
    *,
    tenant_id: str,
    user_id: str,
) -> Dict[str, Any]:
    user = await _load_user(db, tenant_id=tenant_id, user_id=user_id)
    preferences = _ensure_preferences_structure(user.preferences)
    profile = _extract_profile_dict(user)
    security = await _build_security_summary(db, tenant_id=tenant_id, user=user)
    return {"profile": profile, "preferences": preferences, "security": security}


async def patch_user_me(
    db: AsyncSession,
    *,
    tenant_id: str,
    user_id: str,
    profile_payload: Dict[str, Any] | None,
    preferences_payload: Dict[str, Any] | None,
) -> Dict[str, Any]:
    user = await _load_user(db, tenant_id=tenant_id, user_id=user_id)
    extra = _ensure_profile_extra(user.extra)
    profile = extra["profile"]
    preferences = _ensure_preferences_structure(user.preferences)

    changed_profile_fields: list[str] = []
    email_changed = False

    if profile_payload:
        email_value = profile_payload.get("email")
        if email_value is not None:
            sanitized_email = email_value.strip()
            if not sanitized_email:
                raise UserServiceError("Email cannot be empty", 422)
            if sanitized_email.lower() != user.email.lower():
                existing_stmt = (
                    select(User.id)
                    .where(func.lower(User.email) == sanitized_email.lower())
                    .where(User.id != user.id)
                )
                existing = (await db.execute(existing_stmt)).scalar_one_or_none()
                if existing:
                    raise UserServiceError("Email already in use", 409)
                user.email = sanitized_email
                email_changed = True

        for key in ("first_name", "last_name", "country", "city", "position", "phone"):
            if key in profile_payload:
                new_value = _sanitize_optional_str(profile_payload.get(key))
                if profile.get(key) != new_value:
                    profile[key] = new_value
                    changed_profile_fields.append(key)

        if "birth_date" in profile_payload:
            new_birth_date = _validate_birth_date(profile_payload.get("birth_date"))
            if profile.get("birth_date") != new_birth_date:
                profile["birth_date"] = new_birth_date
                changed_profile_fields.append("birth_date")

    preferences_changed = False
    if preferences_payload:
        ui_payload = preferences_payload.get("ui")
        if isinstance(ui_payload, dict):
            for key in DEFAULT_UI_PREFERENCES.keys():
                if key in ui_payload:
                    value = ui_payload.get(key)
                    sanitized = _sanitize_optional_str(value)
                    if value is None:
                        sanitized = DEFAULT_UI_PREFERENCES[key]
                    if preferences["ui"].get(key) != sanitized:
                        preferences["ui"][key] = sanitized
                        preferences_changed = True

        defaults_payload = preferences_payload.get("defaults")
        if isinstance(defaults_payload, dict) and "company_id" in defaults_payload:
            company_id = _sanitize_optional_str(defaults_payload.get("company_id"))
            if preferences["defaults"].get("company_id") != company_id:
                preferences["defaults"]["company_id"] = company_id
                preferences_changed = True

        notifications_payload = preferences_payload.get("notifications")
        if isinstance(notifications_payload, dict):
            for key, cfg in notifications_payload.items():
                if not isinstance(cfg, dict):
                    continue
                enabled = bool(cfg.get("enabled", True))
                mode = str(cfg.get("mode", "immediate")).strip().lower()
                if mode not in {"immediate", "daily_digest"}:
                    mode = "immediate"
                current = preferences["notifications"].get(key)
                if not current or current.get("enabled") != enabled or current.get("mode") != mode:
                    preferences["notifications"][key] = {"enabled": enabled, "mode": mode}
                    preferences_changed = True

        saved_views_payload = preferences_payload.get("saved_views")
        if isinstance(saved_views_payload, dict):
            for module in ("candidates", "vacancies"):
                if module in saved_views_payload:
                    entries = saved_views_payload.get(module)
                    if entries is None:
                        continue
                    cleaned: list[dict[str, Any]] = []
                    if isinstance(entries, list):
                        for view in entries[:20]:
                            if not isinstance(view, dict):
                                continue
                            vid = _sanitize_optional_str(view.get("id"))
                            name = _sanitize_optional_str(view.get("name"))
                            if not vid or not name:
                                continue
                            filters = view.get("filters") if isinstance(view.get("filters"), dict) else {}
                            cleaned.append(
                                {
                                    "id": vid,
                                    "name": name,
                                    "filters": filters,
                                    "is_default": bool(view.get("is_default", False)),
                                }
                            )
                    if preferences["saved_views"].get(module) != cleaned:
                        preferences["saved_views"][module] = cleaned
                        preferences_changed = True

    if email_changed or changed_profile_fields:
        extra["profile"] = profile
        user.full_name = (
            f"{profile.get('first_name') or ''} {profile.get('last_name') or ''}".strip()
            or None
        )

    now = _now()
    columns_to_update: dict[str, Any] = {"updated_at": now}
    if email_changed or changed_profile_fields:
        columns_to_update["email"] = user.email
        columns_to_update["extra"] = extra
        columns_to_update["full_name"] = user.full_name
        user.extra = extra
    if preferences_changed:
        columns_to_update["preferences"] = preferences
        user.preferences = preferences

    if columns_to_update:
        await db.execute(
            sa.update(User)
            .where(User.id == user.id)
            .values(**columns_to_update)
        )
        await db.flush()

        await record_user_audit(
            db,
            tenant_id=tenant_id,
            actor_id=user.id,
            target_user_id=user.id,
            action="user.self_update",
            payload={
                "profile_fields": changed_profile_fields,
                "email_changed": email_changed,
                "preferences_changed": preferences_changed,
            },
        )
        await log_activity(
            db,
            tenant_id=tenant_id,
            actor_id=user.id,
            action="user.self_update",
            target_type="user",
            target_id=user.id,
        )

    return await get_user_me(db, tenant_id=tenant_id, user_id=user_id)


async def update_user_avatar(
    db: AsyncSession,
    *,
    tenant_id: str,
    user_id: str,
    avatar_url: str | None,
) -> Dict[str, Any]:
    user = await _load_user(db, tenant_id=tenant_id, user_id=user_id)
    extra = _ensure_profile_extra(user.extra)
    profile = extra["profile"]
    profile["avatar_url"] = avatar_url
    extra["profile"] = profile
    now = _now()
    await db.execute(
        sa.update(User)
        .where(User.id == user.id)
        .values(extra=extra, updated_at=now)
    )
    await db.flush()

    await record_user_audit(
        db,
        tenant_id=tenant_id,
        actor_id=user.id,
        target_user_id=user.id,
        action="user.avatar_updated",
        payload={"avatar_url": avatar_url},
    )

    return {"avatar_url": avatar_url}


async def get_notification_preferences(
    db: AsyncSession,
    *,
    tenant_id: str,
    user_id: str,
) -> Dict[str, Dict[str, Any]]:
    user = await _load_user(db, tenant_id=tenant_id, user_id=user_id)
    preferences = _ensure_preferences_structure(user.preferences)
    return preferences["notifications"]


async def update_notification_preferences(
    db: AsyncSession,
    *,
    tenant_id: str,
    user_id: str,
    updates: Dict[str, Dict[str, Any]],
) -> Dict[str, Dict[str, Any]]:
    user = await _load_user(db, tenant_id=tenant_id, user_id=user_id)
    preferences = _ensure_preferences_structure(user.preferences)
    changed = False
    for key, cfg in updates.items():
        if not isinstance(cfg, dict):
            continue
        enabled = bool(cfg.get("enabled", True))
        mode = str(cfg.get("mode", "immediate")).strip().lower()
        if mode not in {"immediate", "daily_digest"}:
            mode = "immediate"
        current = preferences["notifications"].get(key)
        if not current or current.get("enabled") != enabled or current.get("mode") != mode:
            preferences["notifications"][key] = {"enabled": enabled, "mode": mode}
            changed = True

    if changed:
        now = _now()
        await db.execute(
            sa.update(User)
            .where(User.id == user.id)
            .values(preferences=preferences, updated_at=now)
        )
        await db.flush()
        await record_user_audit(
            db,
            tenant_id=tenant_id,
            actor_id=user.id,
            target_user_id=user.id,
            action="user.notifications_update",
            payload={"events": list(updates.keys())},
        )

    return preferences["notifications"]


async def list_user_sessions(
    db: AsyncSession,
    *,
    tenant_id: str,
    user_id: str,
) -> List[Dict[str, Any]]:
    await _load_user(db, tenant_id=tenant_id, user_id=user_id)
    stmt = (
        select(UserSession)
        .where(UserSession.user_id == user_id)
        .where(UserSession.tenant_id == tenant_id)
        .order_by(UserSession.last_seen_at.desc())
    )
    sessions = (await db.execute(stmt)).scalars().all()
    result = []
    for session in sessions:
        result.append(
            {
                "id": session.id,
                "created_at": session.created_at,
                "last_seen_at": session.last_seen_at,
                "ip_address": session.ip_address,
                "user_agent": session.user_agent,
                "device_label": session.device_label,
                "expires_at": session.expires_at,
                "revoked_at": session.revoked_at,
            }
        )
    return result


async def revoke_user_sessions(
    db: AsyncSession,
    *,
    tenant_id: str,
    user_id: str,
    actor_id: str | None = None,
) -> int:
    await _load_user(db, tenant_id=tenant_id, user_id=user_id)
    now = _now()
    stmt = (
        sa.update(UserSession)
        .where(UserSession.user_id == user_id)
        .where(UserSession.tenant_id == tenant_id)
        .where(UserSession.revoked_at.is_(None))
        .values(revoked_at=now)
    )
    result = await db.execute(stmt)
    await db.flush()
    revoked_sessions = int(result.rowcount or 0)
    if revoked_sessions:
        await revoke_refresh_tokens(
            db,
            user_id=user_id,
            tenant_id=tenant_id,
            actor_id=actor_id or user_id,
        )
        await record_user_audit(
            db,
            tenant_id=tenant_id,
            actor_id=actor_id or user_id,
            target_user_id=user_id,
            action="user.sessions_revoked",
            payload={"revoked": revoked_sessions},
        )
    return revoked_sessions


async def register_user_session(
    db: AsyncSession,
    *,
    tenant_id: str,
    user_id: str,
    ip_address: str | None,
    user_agent: str | None,
    device_label: str | None,
    expires_at: datetime | None = None,
) -> UserSession:
    session = UserSession(
        user_id=user_id,
        tenant_id=tenant_id,
        ip_address=ip_address,
        user_agent=user_agent,
        device_label=device_label,
        expires_at=expires_at,
    )
    db.add(session)
    await db.flush()
    return session


def _validate_password_complexity(password: str) -> None:
    if len(password) < 12:
        raise UserServiceError("Password must be at least 12 characters", 422)
    if not any(c.islower() for c in password):
        raise UserServiceError("Password must contain a lowercase letter", 422)
    if not any(c.isupper() for c in password):
        raise UserServiceError("Password must contain an uppercase letter", 422)
    if not any(c.isdigit() for c in password):
        raise UserServiceError("Password must contain a digit", 422)
    if not any(not c.isalnum() for c in password):
        raise UserServiceError("Password must contain a special character", 422)


async def change_self_password(
    db: AsyncSession,
    *,
    tenant_id: str,
    user_id: str,
    current_password: str,
    new_password: str,
) -> None:
    current = (current_password or "").strip()
    new = (new_password or "").strip()

    _validate_password_complexity(new)

    user = await _load_user(db, tenant_id=tenant_id, user_id=user_id)
    if not verify_password(current, user.password_hash):
        raise UserServiceError("Current password is invalid", 401)

    user.password_hash = hash_password(new)
    user.updated_at = _now()
    await db.flush()

    await record_user_audit(
        db,
        tenant_id=tenant_id,
        actor_id=user.id,
        target_user_id=user.id,
        action="user.self_password_change",
        payload={"at": _now().isoformat()},
    )

    await log_activity(
        db,
        tenant_id=tenant_id,
        actor_id=user.id,
        action="user.self_password_change",
        target_type="user",
        target_id=user.id,
    )
