from __future__ import annotations

import re
import secrets
import string
from datetime import datetime, timezone
from typing import Dict, List, Optional, Sequence, Tuple

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.tenant import (
    Tenant,
    TenantLicense,
    TenantSeatRequest,
    TenantSeatRequestStatus,
    TenantStatus,
    TenantType,
    user_memberships,
    TenantVacancyAccess,
)
from backend.app.models.vacancy import Vacancy
from backend.app.models.company import Company
from backend.app.models.user import Role as UserRole, User
from backend.app.services.audit import log_activity


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _generate_api_key(length: int = 40) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


_SLUG_PATTERN = re.compile(r"^[a-z0-9\-]+$")


def normalize_slug(slug: str) -> str:
    return (slug or "").strip().lower()


def is_valid_slug(slug: str) -> bool:
    return bool(_SLUG_PATTERN.fullmatch(slug or ""))


async def ensure_slug_unique(db: AsyncSession, slug: str, exclude_id: str | None = None) -> None:
    stmt = sa.select(Tenant.id).where(sa.func.lower(Tenant.slug) == slug.lower())
    if exclude_id:
        stmt = stmt.where(Tenant.id != exclude_id)
    exists = await db.execute(stmt.limit(1))
    if exists.scalar_one_or_none():
        raise ValueError("slug_exists")


def _usage_subquery():
    membership = user_memberships.alias("membership")
    users = User.__table__
    role_lower = sa.func.lower(membership.c.role)

    def _count(*roles: str):
        normalized = [str(role or "").strip().lower() for role in roles if role]
        if not normalized:
            return sa.literal(0)
        condition = role_lower.in_(normalized) if len(normalized) > 1 else role_lower == normalized[0]
        return sa.func.coalesce(
            sa.func.sum(
                sa.case(
                    (condition, 1),
                    else_=0,
                )
            ),
            0,
        )

    return (
        sa.select(
            membership.c.tenant_id.label("tenant_id"),
            _count("recruiter").label("recruiter_count"),
            _count("supervisor", "administrator").label("supervisor_count"),
            _count("client_manager").label("client_manager_count"),
            _count("viewer").label("viewer_count"),
            sa.literal(0).label("storage_used_gb"),
        )
        .select_from(membership)
        .join(
            users,
            sa.and_(
                users.c.id == membership.c.user_id,
                users.c.tenant_id == membership.c.tenant_id,
                users.c.is_active.is_(True),
                users.c.deleted_at.is_(None),
            ),
        )
        .group_by(membership.c.tenant_id)
        .subquery()
    )


def _usage_from_row(
    recruiter: int | None,
    supervisor: int | None,
    client_manager: int | None,
    viewer: int | None,
    storage: int | float | None,
) -> Dict[str, float]:
    return {
        "recruiter_count": int(recruiter or 0),
        "supervisor_count": int(supervisor or 0),
        "client_manager_count": int(client_manager or 0),
        "viewer_count": int(viewer or 0),
        "storage_used_gb": float(storage or 0),
    }


def _normalize_enum_values(values: Sequence[object] | None) -> list[str]:
    if not values:
        return []
    normalized: list[str] = []
    for value in values:
        if isinstance(value, (TenantStatus, TenantType)):
            normalized.append(value.value)
        elif isinstance(value, str):
            normalized.append(value.strip().lower())
        else:
            normalized.append(str(value or "").strip().lower())
    return [entry for entry in normalized if entry]


_MODULE_DEFAULTS: Dict[str, bool] = {
    "candidates": True,
    "companies": True,
    "vacancies": True,
    "documents": True,
    "leads": True,
    "services": True,
    "client_portal": True,
}

_ALLOWED_SEAT_ROLES = {
    UserRole.administrator.value,
    UserRole.supervisor.value,
    UserRole.recruiter.value,
    UserRole.client_manager.value,
    UserRole.viewer.value,
}


async def get_tenant(db: AsyncSession, tenant_id: str) -> Optional[Tenant]:
    res = await db.execute(sa.select(Tenant).where(Tenant.id == tenant_id))
    return res.scalar_one_or_none()


async def get_tenant_with_details(
    db: AsyncSession,
    tenant_id: str,
) -> Optional[Tuple[Tenant, Optional[TenantLicense], Dict[str, float]]]:
    usage_subq = _usage_subquery()
    stmt = (
        sa.select(
            Tenant,
            TenantLicense,
            usage_subq.c.recruiter_count,
            usage_subq.c.supervisor_count,
            usage_subq.c.client_manager_count,
            usage_subq.c.viewer_count,
            usage_subq.c.storage_used_gb,
        )
        .outerjoin(TenantLicense, TenantLicense.tenant_id == Tenant.id)
        .outerjoin(usage_subq, usage_subq.c.tenant_id == Tenant.id)
        .where(Tenant.id == tenant_id)
        .limit(1)
    )
    row = (await db.execute(stmt)).first()
    if not row:
        return None
    tenant, license_entry, recruiter, supervisor, client_manager, viewer, storage = row
    usage = _usage_from_row(recruiter, supervisor, client_manager, viewer, storage)
    return tenant, license_entry, usage


async def list_tenants_with_licenses(
    db: AsyncSession,
    *,
    statuses: Sequence[object] | None = None,
    tenant_types: Sequence[object] | None = None,
    plans: Sequence[str] | None = None,
    search: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> Tuple[list[Tuple[Tenant, Optional[TenantLicense], Dict[str, float]]], int]:
    usage_subq = _usage_subquery()
    stmt = (
        sa.select(
            Tenant,
            TenantLicense,
            usage_subq.c.recruiter_count,
            usage_subq.c.supervisor_count,
            usage_subq.c.client_manager_count,
            usage_subq.c.viewer_count,
            usage_subq.c.storage_used_gb,
        )
        .outerjoin(TenantLicense, TenantLicense.tenant_id == Tenant.id)
        .outerjoin(usage_subq, usage_subq.c.tenant_id == Tenant.id)
    )
    count_stmt = sa.select(sa.func.count()).select_from(Tenant)

    normalized_statuses = _normalize_enum_values(statuses)
    normalized_types = _normalize_enum_values(tenant_types)
    normalized_plans = [p.strip() for p in plans or [] if p and p.strip()]

    if normalized_plans:
        stmt = stmt.where(TenantLicense.plan.in_(normalized_plans))
        count_stmt = count_stmt.join(
            TenantLicense, TenantLicense.tenant_id == Tenant.id, isouter=True
        ).where(TenantLicense.plan.in_(normalized_plans))

    if normalized_statuses:
        condition = Tenant.status.in_(normalized_statuses)
        stmt = stmt.where(condition)
        count_stmt = count_stmt.where(condition)

    if normalized_types:
        condition = Tenant.type.in_(normalized_types)
        stmt = stmt.where(condition)
        count_stmt = count_stmt.where(condition)

    if search:
        pattern = f"%{search.lower().strip()}%"
        condition = sa.or_(
            sa.func.lower(Tenant.name).like(pattern),
            sa.func.lower(Tenant.slug).like(pattern),
        )
        stmt = stmt.where(condition)
        count_stmt = count_stmt.where(condition)

    safe_limit = max(1, min(limit or 50, 200))
    safe_offset = max(0, offset or 0)

    stmt = stmt.order_by(Tenant.created_at.desc()).limit(safe_limit).offset(safe_offset)

    total = (await db.execute(count_stmt)).scalar_one()
    rows = await db.execute(stmt)
    items: list[Tuple[Tenant, Optional[TenantLicense], Dict[str, float]]] = []
    for tenant, license_entry, recruiter, supervisor, client_manager, viewer, storage in rows:
        usage = _usage_from_row(recruiter, supervisor, client_manager, viewer, storage)
        items.append((tenant, license_entry, usage))
    return items, int(total)


async def create_tenant(
    db: AsyncSession,
    data: dict,
    *,
    api_key: Optional[str] = None,
) -> Tenant:
    values = data.copy()
    values.setdefault("api_key", api_key or _generate_api_key())
    tenant = Tenant(**values)
    db.add(tenant)
    await db.commit()
    await db.refresh(tenant)
    return tenant


async def update_tenant(
    db: AsyncSession,
    tenant: Tenant,
    payload: dict,
) -> Tenant:
    for key, value in payload.items():
        setattr(tenant, key, value)
    setattr(tenant, "updated_at", _now_utc())
    await db.commit()
    await db.refresh(tenant)
    return tenant


async def rotate_api_key(
    db: AsyncSession,
    tenant: Tenant,
    *,
    length: int = 40,
) -> Tenant:
    tenant.api_key = _generate_api_key(length)
    tenant.updated_at = _now_utc()
    await db.commit()
    await db.refresh(tenant)
    return tenant


async def list_tenant_users(
    db: AsyncSession,
    tenant_id: str,
) -> List[Tuple[User, str, Optional[datetime]]]:
    stmt = (
        sa.select(
            User,
            user_memberships.c.role,
            user_memberships.c.created_at,
        )
        .join(user_memberships, user_memberships.c.user_id == User.id)
        .where(user_memberships.c.tenant_id == tenant_id)
    )
    res = await db.execute(stmt)
    return res.all()


async def create_tenant_with_license(
    db: AsyncSession,
    *,
    tenant_payload: Dict[str, object],
    license_payload: Dict[str, object],
) -> Tuple[Tenant, TenantLicense]:
    values = tenant_payload.copy()
    slug = normalize_slug(str(values.get("slug", "")))
    if not slug or not _SLUG_PATTERN.fullmatch(slug):
        raise ValueError("invalid_slug")
    await ensure_slug_unique(db, slug)
    values["slug"] = slug
    values.setdefault("api_key", _generate_api_key())
    tenant = Tenant(**values)
    db.add(tenant)
    await db.flush()

    license_values = license_payload.copy()
    license_values["tenant_id"] = tenant.id
    license_entry = TenantLicense(**license_values)
    db.add(license_entry)
    await db.commit()
    await db.refresh(tenant)
    await db.refresh(license_entry)
    return tenant, license_entry


async def get_tenant_license(db: AsyncSession, tenant_id: str) -> Optional[TenantLicense]:
    row = await db.execute(
        sa.select(TenantLicense).where(TenantLicense.tenant_id == tenant_id).limit(1)
    )
    return row.scalar_one_or_none()


async def upsert_license(
    db: AsyncSession,
    tenant_id: str,
    payload: Dict[str, object],
    *,
    actor_id: str | None = None,
) -> TenantLicense:
    license_entry = await get_tenant_license(db, tenant_id)
    created = False
    if license_entry is None:
        license_entry = TenantLicense(
            tenant_id=tenant_id,
            plan=str(payload.get("plan") or "manual"),
        )
        db.add(license_entry)
        created = True
    for key, value in payload.items():
        setattr(license_entry, key, value)
    license_entry.updated_at = _now_utc()
    await db.commit()
    await db.refresh(license_entry)
    await log_activity(
        db,
        tenant_id=tenant_id,
        actor_id=actor_id,
        action="tenant.license_update",
        target_type="tenant",
        target_id=tenant_id,
        payload={"created": created, "changes": payload},
    )
    return license_entry


async def get_usage_snapshot(db: AsyncSession, tenant_id: str) -> Dict[str, float]:
    usage_subq = _usage_subquery()
    stmt = (
        sa.select(
            usage_subq.c.recruiter_count,
            usage_subq.c.supervisor_count,
            usage_subq.c.client_manager_count,
            usage_subq.c.viewer_count,
            usage_subq.c.storage_used_gb,
        )
        .where(usage_subq.c.tenant_id == tenant_id)
        .limit(1)
    )
    row = (await db.execute(stmt)).first()
    if not row:
        return _usage_from_row(0, 0, 0, 0, 0)
    recruiter, supervisor, client_manager, viewer, storage = row
    return _usage_from_row(recruiter, supervisor, client_manager, viewer, storage)


async def set_tenant_status(
    db: AsyncSession,
    tenant: Tenant,
    *,
    status: TenantStatus,
    actor_id: str | None = None,
    client_portal_enabled: bool | None = None,
    reason: str | None = None,
) -> Tenant:
    tenant.status = status
    if client_portal_enabled is not None:
        tenant.client_portal_enabled = client_portal_enabled
    tenant.updated_at = _now_utc()
    await db.commit()
    await db.refresh(tenant)
    await log_activity(
        db,
        tenant_id=tenant.id,
        actor_id=actor_id,
        action="tenant.status_change",
        target_type="tenant",
        target_id=tenant.id,
        payload={"status": status.value, "reason": reason},
    )
    return tenant


def get_module_settings_snapshot(tenant: Tenant) -> Dict[str, bool]:
    modules = dict(_MODULE_DEFAULTS)
    raw_settings = tenant.settings or {}
    raw_modules = raw_settings.get("modules") if isinstance(raw_settings, dict) else None
    if isinstance(raw_modules, dict):
        for key in modules:
            if key in raw_modules:
                modules[key] = bool(raw_modules[key])
    return modules


async def update_module_settings(
    db: AsyncSession,
    tenant: Tenant,
    updates: Dict[str, bool],
    *,
    actor_id: str | None = None,
) -> Dict[str, bool]:
    if not updates:
        return get_module_settings_snapshot(tenant)

    modules = get_module_settings_snapshot(tenant)
    unknown = [key for key in updates if key not in modules]
    if unknown:
        raise ValueError(f"unknown_module:{','.join(unknown)}")

    changed = False
    for key, value in updates.items():
        normalized = bool(value)
        if modules[key] != normalized:
            modules[key] = normalized
            changed = True

    if not changed:
        return modules

    settings_payload = dict(tenant.settings or {})
    settings_payload["modules"] = modules
    tenant.settings = settings_payload
    tenant.updated_at = _now_utc()
    await db.commit()
    await db.refresh(tenant)
    await log_activity(
        db,
        tenant_id=tenant.id,
        actor_id=actor_id,
        action="tenant.modules_update",
        target_type="tenant",
        target_id=tenant.id,
        payload={"modules": modules},
    )
    return modules


async def list_seat_requests(
    db: AsyncSession,
    tenant_id: str,
    *,
    status: TenantSeatRequestStatus | None = None,
    limit: int = 50,
) -> List[TenantSeatRequest]:
    safe_limit = max(1, min(limit or 50, 200))
    stmt = sa.select(TenantSeatRequest).where(TenantSeatRequest.tenant_id == tenant_id)
    if status:
        stmt = stmt.where(TenantSeatRequest.status == status)
    stmt = stmt.order_by(TenantSeatRequest.created_at.desc()).limit(safe_limit)
    rows = await db.execute(stmt)
    return list(rows.scalars().all())


async def get_seat_request(
    db: AsyncSession,
    tenant_id: str,
    request_id: str,
) -> TenantSeatRequest | None:
    stmt = (
        sa.select(TenantSeatRequest)
        .where(
            TenantSeatRequest.tenant_id == tenant_id,
            TenantSeatRequest.id == request_id,
        )
        .limit(1)
    )
    row = await db.execute(stmt)
    return row.scalar_one_or_none()


async def create_seat_request(
    db: AsyncSession,
    tenant_id: str,
    *,
    requested_by: str,
    role: str,
    requested_count: int,
    message: str | None = None,
) -> TenantSeatRequest:
    normalized_role = (role or "").strip().lower()
    if normalized_role not in _ALLOWED_SEAT_ROLES:
        raise ValueError("invalid_role")
    if requested_count <= 0:
        raise ValueError("invalid_requested_count")
    entry = TenantSeatRequest(
        tenant_id=tenant_id,
        requested_by=requested_by,
        role=normalized_role,
        requested_count=requested_count,
        message=message,
        status=TenantSeatRequestStatus.pending,
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    await log_activity(
        db,
        tenant_id=tenant_id,
        actor_id=requested_by,
        action="tenant.seat_request",
        target_type="tenant",
        target_id=tenant_id,
        payload={
            "role": normalized_role,
            "requested_count": requested_count,
        },
    )
    return entry


async def resolve_seat_request(
    db: AsyncSession,
    seat_request: TenantSeatRequest,
    *,
    status: TenantSeatRequestStatus,
    actor_id: str | None,
    resolution_notes: str | None = None,
) -> TenantSeatRequest:
    if seat_request.status != TenantSeatRequestStatus.pending:
        raise ValueError("seat_request_already_resolved")
    seat_request.status = status
    seat_request.resolution_notes = (resolution_notes or "").strip() or None
    seat_request.resolved_by = actor_id
    seat_request.resolved_at = _now_utc()
    await db.commit()
    await db.refresh(seat_request)
    await log_activity(
        db,
        tenant_id=seat_request.tenant_id,
        actor_id=actor_id,
        action="tenant.seat_request_resolve",
        target_type="tenant",
        target_id=seat_request.tenant_id,
        payload={
            "request_id": seat_request.id,
            "status": seat_request.status.value,
        },
    )
    return seat_request


async def list_tenant_vacancy_access(db: AsyncSession, tenant_id: str) -> list[dict]:
    stmt = (
        sa.select(
            TenantVacancyAccess.vacancy_id,
            Vacancy.title,
            Company.name.label("company_name"),
            Vacancy.status,
        )
        .join(Vacancy, Vacancy.id == TenantVacancyAccess.vacancy_id, isouter=True)
        .join(Company, Company.id == Vacancy.company_id, isouter=True)
        .where(TenantVacancyAccess.tenant_id == tenant_id)
        .order_by(Vacancy.title.asc())
    )
    rows = await db.execute(stmt)
    items: list[dict] = []
    for row in rows:
        items.append(
            {
                "vacancy_id": row.vacancy_id,
                "title": row.title or row.vacancy_id,
                "company_name": row.company_name,
                "status": row.status,
            }
        )
    return items


async def set_tenant_vacancy_access(
    db: AsyncSession,
    tenant_id: str,
    vacancy_ids: Sequence[str],
) -> list[str]:
    unique_ids: list[str] = []
    seen: set[str] = set()
    for vid in vacancy_ids:
        if not vid:
            continue
        if vid in seen:
            continue
        seen.add(vid)
        unique_ids.append(vid)

    if unique_ids:
        rows = await db.execute(
            sa.select(Vacancy.id).where(Vacancy.id.in_(unique_ids))
        )
        found = {row.id for row in rows if row.id}
        missing = [vid for vid in unique_ids if vid not in found]
        if missing:
            raise ValueError(f"vacancy_not_found:{','.join(missing)}")

    await db.execute(
        sa.delete(TenantVacancyAccess).where(TenantVacancyAccess.tenant_id == tenant_id)
    )
    if unique_ids:
        payload = [{"tenant_id": tenant_id, "vacancy_id": vid} for vid in unique_ids]
        await db.execute(sa.insert(TenantVacancyAccess), payload)
    await db.commit()
    return unique_ids


async def list_shareable_vacancies(
    db: AsyncSession,
    tenant_id: str,
    *,
    search: str | None = None,
    limit: int = 50,
) -> list[dict]:
    stmt = (
        sa.select(
            Vacancy.id,
            Vacancy.title,
            Company.name.label("company_name"),
            Vacancy.status,
            Vacancy.tenant_id,
        )
        .join(Company, Company.id == Vacancy.company_id, isouter=True)
        .order_by(Vacancy.created_at.desc())
        .limit(limit)
    )
    if search:
        stmt = stmt.where(Vacancy.title.ilike(f"%{search}%"))
    rows = await db.execute(stmt)
    items: list[dict] = []
    for row in rows:
        items.append(
            {
                "vacancy_id": row.id,
                "title": row.title or row.id,
                "company_name": row.company_name,
                "status": row.status,
                "tenant_id": row.tenant_id,
            }
        )
    return items
