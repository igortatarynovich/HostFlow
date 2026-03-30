from __future__ import annotations

import asyncio
import re
import secrets
import string
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence, Tuple

import sqlalchemy as sa
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.tenant import (
    Tenant,
    TenantLicense,
    TenantLink,
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
from backend.app.models.lead import Lead
from backend.app.models.candidate import Candidate
from backend.app.models.document import Document
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


async def _count_leads_created_this_month(db: AsyncSession, tenant_id: str) -> int:
    now = datetime.now(timezone.utc)
    month_start = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
    stmt = select(func.count()).select_from(Lead).where(
        Lead.tenant_id == tenant_id,
        Lead.created_at >= month_start,
    )
    return int((await db.execute(stmt)).scalar_one() or 0)


async def _count_candidates_active(db: AsyncSession, tenant_id: str) -> int:
    stmt = select(func.count()).select_from(Candidate).where(
        Candidate.tenant_id == tenant_id,
        Candidate.deleted_at.is_(None),
    )
    return int((await db.execute(stmt)).scalar_one() or 0)


async def _count_documents_for_tenant(db: AsyncSession, tenant_id: str) -> int:
    stmt = select(func.count()).select_from(Document).where(Document.tenant_id == tenant_id)
    return int((await db.execute(stmt)).scalar_one() or 0)


async def _count_open_vacancies(db: AsyncSession, tenant_id: str) -> int:
    stmt = select(func.count()).select_from(Vacancy).where(
        Vacancy.tenant_id == tenant_id,
        Vacancy.status == "open",
    )
    return int((await db.execute(stmt)).scalar_one() or 0)


async def _count_portal_links_active(db: AsyncSession, tenant_id: str) -> int:
    stmt = select(func.count()).select_from(TenantLink).where(
        TenantLink.agency_tenant_id == tenant_id,
        TenantLink.portal_token.is_not(None),
    )
    return int((await db.execute(stmt)).scalar_one() or 0)


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

_ROLE_MATRIX_ROLES: tuple[str, ...] = (
    UserRole.administrator.value,
    UserRole.supervisor.value,
    UserRole.recruiter.value,
    UserRole.client_manager.value,
    UserRole.client_processor.value,
    UserRole.viewer.value,
)

_ROLE_MODULE_DEFAULTS: Dict[str, Dict[str, Dict[str, bool]]] = {
    UserRole.administrator.value: {
        module: {"visible": True, "editable": True} for module in _MODULE_DEFAULTS
    },
    UserRole.supervisor.value: {
        "candidates": {"visible": True, "editable": True},
        "companies": {"visible": True, "editable": True},
        "vacancies": {"visible": True, "editable": True},
        "documents": {"visible": True, "editable": True},
        "leads": {"visible": True, "editable": True},
        "services": {"visible": True, "editable": True},
        "client_portal": {"visible": True, "editable": False},
    },
    UserRole.recruiter.value: {
        "candidates": {"visible": True, "editable": True},
        "companies": {"visible": True, "editable": False},
        "vacancies": {"visible": True, "editable": False},
        "documents": {"visible": True, "editable": True},
        "leads": {"visible": True, "editable": False},
        "services": {"visible": True, "editable": True},
        "client_portal": {"visible": False, "editable": False},
    },
    UserRole.client_manager.value: {
        "candidates": {"visible": True, "editable": True},
        "companies": {"visible": True, "editable": False},
        "vacancies": {"visible": True, "editable": False},
        "documents": {"visible": True, "editable": True},
        "leads": {"visible": False, "editable": False},
        "services": {"visible": False, "editable": False},
        "client_portal": {"visible": True, "editable": False},
    },
    UserRole.client_processor.value: {
        "candidates": {"visible": True, "editable": True},
        "companies": {"visible": True, "editable": False},
        "vacancies": {"visible": True, "editable": False},
        "documents": {"visible": True, "editable": True},
        "leads": {"visible": False, "editable": False},
        "services": {"visible": False, "editable": False},
        "client_portal": {"visible": True, "editable": False},
    },
    UserRole.viewer.value: {
        "candidates": {"visible": True, "editable": False},
        "companies": {"visible": True, "editable": False},
        "vacancies": {"visible": True, "editable": False},
        "documents": {"visible": False, "editable": False},
        "leads": {"visible": False, "editable": False},
        "services": {"visible": False, "editable": False},
        "client_portal": {"visible": False, "editable": False},
    },
}

_ALLOWED_SEAT_ROLES = {
    UserRole.administrator.value,
    UserRole.supervisor.value,
    UserRole.recruiter.value,
    UserRole.client_manager.value,
    UserRole.viewer.value,
}


def _business_type_for_tenant(tenant: Tenant) -> str:
    settings_payload = tenant.settings if isinstance(tenant.settings, dict) else {}
    raw_business_type = settings_payload.get("business_type")
    normalized = str(raw_business_type or "").strip().lower()
    if normalized in {"agency", "employer", "services"}:
        return normalized
    tenant_type = str(getattr(getattr(tenant, "type", None), "value", getattr(tenant, "type", ""))).strip().lower()
    if tenant_type == TenantType.company.value:
        return "employer"
    return "agency"


def _role_defaults_for_tenant(tenant: Tenant) -> Dict[str, Dict[str, Dict[str, bool]]]:
    business_type = _business_type_for_tenant(tenant)
    defaults = deepcopy(_ROLE_MODULE_DEFAULTS)

    if business_type == "employer":
        # Employer teams usually run vacancy+candidate loop directly.
        # Recruiter should be able to operate vacancies, not only view them.
        defaults[UserRole.recruiter.value]["vacancies"] = {"visible": True, "editable": True}
    elif business_type == "services":
        # Services mode shifts recruiter-like role to leads/services operations.
        defaults[UserRole.recruiter.value]["companies"] = {"visible": True, "editable": True}
        defaults[UserRole.recruiter.value]["leads"] = {"visible": True, "editable": True}
        defaults[UserRole.recruiter.value]["services"] = {"visible": True, "editable": True}
        defaults[UserRole.recruiter.value]["candidates"] = {"visible": False, "editable": False}
        defaults[UserRole.recruiter.value]["vacancies"] = {"visible": False, "editable": False}
        defaults[UserRole.client_manager.value]["leads"] = {"visible": True, "editable": True}
        defaults[UserRole.client_manager.value]["services"] = {"visible": True, "editable": True}
        defaults[UserRole.client_processor.value]["leads"] = {"visible": True, "editable": True}
        defaults[UserRole.client_processor.value]["services"] = {"visible": True, "editable": True}

    return defaults


def _normalize_permissions_cell(
    *,
    visible: bool,
    editable: bool,
    module_enabled: bool,
) -> Dict[str, bool]:
    next_visible = bool(visible)
    next_editable = bool(editable)
    if not module_enabled:
        next_visible = False
        next_editable = False
    if not next_visible:
        next_editable = False
    return {"visible": next_visible, "editable": next_editable}


def get_user_module_overrides_snapshot(
    tenant: Tenant,
    *,
    allowed_user_ids: set[str] | None = None,
) -> Dict[str, Dict[str, Dict[str, bool]]]:
    modules = get_module_settings_snapshot(tenant)
    settings_payload = dict(tenant.settings or {})
    raw_modules = settings_payload.get("modules") if isinstance(settings_payload, dict) else None
    raw_overrides = raw_modules.get("user_overrides") if isinstance(raw_modules, dict) else None
    if not isinstance(raw_overrides, dict):
        return {}

    snapshot: Dict[str, Dict[str, Dict[str, bool]]] = {}
    for user_key, user_payload in raw_overrides.items():
        user_id = str(user_key or "").strip()
        if not user_id:
            continue
        if allowed_user_ids is not None and user_id not in allowed_user_ids:
            continue
        if not isinstance(user_payload, dict):
            continue
        user_matrix: Dict[str, Dict[str, bool]] = {}
        for module_key, cell_payload in user_payload.items():
            module = str(module_key or "").strip()
            if module not in _MODULE_DEFAULTS or not isinstance(cell_payload, dict):
                continue
            user_matrix[module] = _normalize_permissions_cell(
                visible=bool(cell_payload.get("visible")),
                editable=bool(cell_payload.get("editable")),
                module_enabled=bool(modules.get(module, True)),
            )
        if user_matrix:
            snapshot[user_id] = user_matrix
    return snapshot


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


def _deep_merge_settings_fragment(base: dict, patch: dict) -> dict:
    out = dict(base)
    for k, v in patch.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge_settings_fragment(out[k], v)
        else:
            out[k] = v
    return out


async def get_risk_model_v1_settings_view(db: AsyncSession, tenant: Tenant) -> dict[str, Any]:
    from backend.app.services.risk_intel_v1 import resolve_risk_config

    settings_obj = tenant.settings if isinstance(tenant.settings, dict) else {}
    effective = resolve_risk_config(settings_obj)
    raw = settings_obj.get("risk_model_v1")
    overrides = dict(raw) if isinstance(raw, dict) else {}
    return {"effective": effective, "overrides": overrides}


async def patch_risk_model_v1_settings(db: AsyncSession, tenant: Tenant, fragment: dict) -> dict[str, Any]:
    from backend.app.services.risk_intel_v1 import resolve_risk_config

    if not isinstance(fragment, dict):
        raise ValueError("Body must be a JSON object")
    settings_obj = dict(tenant.settings or {}) if isinstance(tenant.settings, dict) else {}
    current = settings_obj.get("risk_model_v1")
    current = dict(current) if isinstance(current, dict) else {}
    merged = _deep_merge_settings_fragment(current, fragment)
    settings_obj["risk_model_v1"] = merged
    await update_tenant(db, tenant, {"settings": settings_obj})
    effective = resolve_risk_config(settings_obj)
    return {"effective": effective, "overrides": merged}


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
        base = _usage_from_row(0, 0, 0, 0, 0)
    else:
        recruiter, supervisor, client_manager, viewer, storage = row
        base = _usage_from_row(recruiter, supervisor, client_manager, viewer, storage)
    leads_m, cand, docs, vac_open, portals = await asyncio.gather(
        _count_leads_created_this_month(db, tenant_id),
        _count_candidates_active(db, tenant_id),
        _count_documents_for_tenant(db, tenant_id),
        _count_open_vacancies(db, tenant_id),
        _count_portal_links_active(db, tenant_id),
    )
    base["leads_created_this_month"] = leads_m
    base["candidates_active_count"] = cand
    base["documents_count"] = docs
    base["vacancies_open_count"] = vac_open
    base["portal_links_active_count"] = portals
    return base


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


def get_role_module_matrix_snapshot(tenant: Tenant) -> Dict[str, Dict[str, Dict[str, bool]]]:
    """Return normalized role->module->(visible, editable) matrix from tenant settings."""
    modules = get_module_settings_snapshot(tenant)
    role_defaults_map = _role_defaults_for_tenant(tenant)
    settings_payload = dict(tenant.settings or {})
    raw_modules = settings_payload.get("modules") if isinstance(settings_payload, dict) else None
    raw_matrix = raw_modules.get("role_matrix") if isinstance(raw_modules, dict) else None

    snapshot: Dict[str, Dict[str, Dict[str, bool]]] = {}
    for role in _ROLE_MATRIX_ROLES:
        role_defaults = role_defaults_map.get(role, {})
        role_raw = raw_matrix.get(role) if isinstance(raw_matrix, dict) else None
        role_matrix: Dict[str, Dict[str, bool]] = {}
        for module, module_enabled in modules.items():
            cell_default = role_defaults.get(module, {"visible": bool(module_enabled), "editable": False})
            raw_cell = role_raw.get(module) if isinstance(role_raw, dict) else None
            visible = cell_default["visible"]
            editable = cell_default["editable"]
            if isinstance(raw_cell, dict):
                if "visible" in raw_cell:
                    visible = bool(raw_cell["visible"])
                if "editable" in raw_cell:
                    editable = bool(raw_cell["editable"])
            role_matrix[module] = _normalize_permissions_cell(
                visible=visible,
                editable=editable,
                module_enabled=bool(module_enabled),
            )
        snapshot[role] = role_matrix
    return snapshot


def get_effective_role_module_permissions(
    tenant: Tenant,
    *,
    role: str,
    user_id: str | None = None,
) -> Dict[str, Dict[str, bool]]:
    normalized_role = str(role or UserRole.viewer.value).strip().lower()
    matrix = get_role_module_matrix_snapshot(tenant)
    role_matrix = matrix.get(normalized_role) or matrix.get(UserRole.viewer.value) or {}
    effective = {
        key: {"visible": bool(val.get("visible")), "editable": bool(val.get("editable"))}
        for key, val in role_matrix.items()
    }
    normalized_user_id = str(user_id or "").strip()
    if not normalized_user_id:
        return effective
    overrides = get_user_module_overrides_snapshot(tenant)
    user_override = overrides.get(normalized_user_id) or {}
    for module, cell in user_override.items():
        if module in effective:
            effective[module] = {
                "visible": bool(cell.get("visible")),
                "editable": bool(cell.get("editable")),
            }
    return effective


def get_vacancy_requirements_presets_snapshot(tenant: Tenant) -> list[dict]:
    """
    Presets are stored in tenant.settings['vacancy_requirements_presets_v1'] as a list of dicts.
    Each preset: { id: str, label: str, criteria: dict, updated_at?: str }
    """
    settings_payload = tenant.settings if isinstance(tenant.settings, dict) else {}
    raw = settings_payload.get("vacancy_requirements_presets_v1") if isinstance(settings_payload, dict) else None
    if not isinstance(raw, list):
        return []
    out: list[dict] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        pid = str(item.get("id") or "").strip()
        label = str(item.get("label") or "").strip()
        criteria = item.get("criteria")
        if not pid or not label or not isinstance(criteria, dict):
            continue
        out.append(
            {
                "id": pid,
                "label": label,
                "criteria": criteria,
                "updated_at": item.get("updated_at"),
            }
        )
    return out


async def upsert_vacancy_requirements_preset(
    db: AsyncSession,
    tenant: Tenant,
    *,
    preset_id: str,
    label: str,
    criteria: dict,
    actor_id: str | None = None,
) -> list[dict]:
    preset_id = str(preset_id or "").strip()
    if not preset_id:
        raise ValueError("invalid_preset_id")
    label = str(label or "").strip()
    if not label:
        raise ValueError("invalid_label")
    if not isinstance(criteria, dict):
        raise ValueError("invalid_criteria")

    current = get_vacancy_requirements_presets_snapshot(tenant)
    now = _now_utc().isoformat()
    next_item = {"id": preset_id, "label": label, "criteria": criteria, "updated_at": now}
    replaced = False
    next_list: list[dict] = []
    for item in current:
        if str(item.get("id") or "") == preset_id:
            next_list.append(next_item)
            replaced = True
        else:
            next_list.append(item)
    if not replaced:
        next_list.append(next_item)

    settings_payload = dict(tenant.settings or {})
    settings_payload["vacancy_requirements_presets_v1"] = next_list
    tenant.settings = settings_payload
    tenant.updated_at = _now_utc()
    await db.commit()
    await db.refresh(tenant)
    try:
        await log_activity(
            db,
            tenant_id=tenant.id,
            actor_id=actor_id,
            action="tenant.vacancy_requirements_presets.upsert",
            target_type="tenant",
            target_id=tenant.id,
            payload={"preset_id": preset_id, "label": label},
        )
    except Exception:
        pass
    return get_vacancy_requirements_presets_snapshot(tenant)


async def delete_vacancy_requirements_preset(
    db: AsyncSession,
    tenant: Tenant,
    *,
    preset_id: str,
    actor_id: str | None = None,
) -> list[dict]:
    preset_id = str(preset_id or "").strip()
    if not preset_id:
        raise ValueError("invalid_preset_id")
    current = get_vacancy_requirements_presets_snapshot(tenant)
    next_list = [item for item in current if str(item.get("id") or "") != preset_id]
    settings_payload = dict(tenant.settings or {})
    settings_payload["vacancy_requirements_presets_v1"] = next_list
    tenant.settings = settings_payload
    tenant.updated_at = _now_utc()
    await db.commit()
    await db.refresh(tenant)
    try:
        await log_activity(
            db,
            tenant_id=tenant.id,
            actor_id=actor_id,
            action="tenant.vacancy_requirements_presets.delete",
            target_type="tenant",
            target_id=tenant.id,
            payload={"preset_id": preset_id},
        )
    except Exception:
        pass
    return get_vacancy_requirements_presets_snapshot(tenant)

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
    modules_payload = dict(settings_payload.get("modules") or {})
    for key, value in modules.items():
        modules_payload[key] = value
    settings_payload["modules"] = modules_payload
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


async def update_role_module_matrix(
    db: AsyncSession,
    tenant: Tenant,
    updates: Dict[str, Dict[str, Dict[str, bool]]],
    *,
    actor_id: str | None = None,
) -> Dict[str, Dict[str, Dict[str, bool]]]:
    if not updates:
        return get_role_module_matrix_snapshot(tenant)

    modules = get_module_settings_snapshot(tenant)
    current = get_role_module_matrix_snapshot(tenant)
    changed = False

    for role_key, role_payload in updates.items():
        role = str(role_key or "").strip().lower()
        if role not in _ROLE_MATRIX_ROLES:
            raise ValueError(f"unknown_role:{role}")
        if not isinstance(role_payload, dict):
            raise ValueError(f"invalid_role_payload:{role}")
        for module_key, cell_payload in role_payload.items():
            module = str(module_key or "").strip()
            if module not in _MODULE_DEFAULTS:
                raise ValueError(f"unknown_module:{module}")
            if not isinstance(cell_payload, dict):
                raise ValueError(f"invalid_module_payload:{role}:{module}")
            next_visible = current[role][module]["visible"]
            next_editable = current[role][module]["editable"]
            if "visible" in cell_payload:
                next_visible = bool(cell_payload["visible"])
            if "editable" in cell_payload:
                next_editable = bool(cell_payload["editable"])
            if not modules.get(module, True):
                next_visible = False
                next_editable = False
            if not next_visible:
                next_editable = False
            if (
                current[role][module]["visible"] != next_visible
                or current[role][module]["editable"] != next_editable
            ):
                current[role][module] = {"visible": next_visible, "editable": next_editable}
                changed = True

    if not changed:
        return current

    settings_payload = dict(tenant.settings or {})
    modules_payload = dict(settings_payload.get("modules") or {})
    modules_payload["role_matrix"] = current
    settings_payload["modules"] = modules_payload
    tenant.settings = settings_payload
    tenant.updated_at = _now_utc()
    await db.commit()
    await db.refresh(tenant)
    await log_activity(
        db,
        tenant_id=tenant.id,
        actor_id=actor_id,
        action="tenant.role_modules_update",
        target_type="tenant",
        target_id=tenant.id,
        payload={"role_matrix": current},
    )
    return current


async def update_user_module_overrides(
    db: AsyncSession,
    tenant: Tenant,
    updates: Dict[str, Dict[str, Dict[str, bool]] | None],
    *,
    actor_id: str | None = None,
    allowed_user_ids: set[str] | None = None,
) -> Dict[str, Dict[str, Dict[str, bool]]]:
    if not updates:
        return get_user_module_overrides_snapshot(tenant, allowed_user_ids=allowed_user_ids)

    modules = get_module_settings_snapshot(tenant)
    current = get_user_module_overrides_snapshot(tenant, allowed_user_ids=allowed_user_ids)
    changed = False

    for user_key, user_payload in updates.items():
        user_id = str(user_key or "").strip()
        if not user_id:
            raise ValueError("invalid_user_id")
        if allowed_user_ids is not None and user_id not in allowed_user_ids:
            raise ValueError(f"unknown_user:{user_id}")
        if user_payload is None:
            if user_id in current:
                current.pop(user_id, None)
                changed = True
            continue
        if not isinstance(user_payload, dict):
            raise ValueError(f"invalid_user_payload:{user_id}")

        user_matrix = dict(current.get(user_id) or {})
        for module_key, cell_payload in user_payload.items():
            module = str(module_key or "").strip()
            if module not in _MODULE_DEFAULTS:
                raise ValueError(f"unknown_module:{module}")
            if not isinstance(cell_payload, dict):
                raise ValueError(f"invalid_module_payload:{user_id}:{module}")
            if "visible" not in cell_payload or "editable" not in cell_payload:
                raise ValueError(f"invalid_module_payload:{user_id}:{module}")
            normalized_cell = _normalize_permissions_cell(
                visible=bool(cell_payload["visible"]),
                editable=bool(cell_payload["editable"]),
                module_enabled=bool(modules.get(module, True)),
            )
            prev_cell = user_matrix.get(module)
            if prev_cell != normalized_cell:
                user_matrix[module] = normalized_cell
                changed = True
        if user_matrix:
            current[user_id] = user_matrix
        elif user_id in current:
            current.pop(user_id, None)
            changed = True

    if not changed:
        return current

    settings_payload = dict(tenant.settings or {})
    modules_payload = dict(settings_payload.get("modules") or {})
    modules_payload["user_overrides"] = current
    settings_payload["modules"] = modules_payload
    tenant.settings = settings_payload
    tenant.updated_at = _now_utc()
    await db.commit()
    await db.refresh(tenant)
    await log_activity(
        db,
        tenant_id=tenant.id,
        actor_id=actor_id,
        action="tenant.user_modules_update",
        target_type="tenant",
        target_id=tenant.id,
        payload={"user_overrides": updates},
    )
    return current


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
