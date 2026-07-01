"""Active lead-form slots per tenant (§2.16): base cap by plan + pack_addons_v1.lead_forms_active_cap."""

from __future__ import annotations

import re
from typing import Any

from fastapi import HTTPException
from sqlalchemy import func, select, text
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.tenant import Tenant, TenantLicense
from backend.app.models.tenant_lead_form import TenantLeadForm
from backend.app.services.billing_pack_addons import LEAD_FORMS_ACTIVE_CAP, pack_addon_int


_PLAN_CODES: tuple[str, ...] = ("starter", "team", "pro", "enterprise")


async def _plan_code_for_usage_caps(db: AsyncSession, tenant_id: str) -> str:
    """Same rules as ``billing._plan_code_for_usage_caps`` (subscription.plan_code wins over license row)."""
    tenant = await db.get(Tenant, tenant_id)
    sub: dict[str, Any] = {}
    if tenant is not None and isinstance(tenant.settings, dict):
        bill = tenant.settings.get("billing")
        if isinstance(bill, dict):
            raw_sub = bill.get("subscription")
            if isinstance(raw_sub, dict):
                sub = raw_sub
    license_row = (
        await db.execute(select(TenantLicense).where(TenantLicense.tenant_id == tenant_id).limit(1))
    ).scalar_one_or_none()
    status = str(sub.get("status") or "").strip().lower()
    if status == "trial":
        return "starter"
    raw = str(sub.get("plan_code") or "").strip().lower()
    if raw in _PLAN_CODES:
        return raw
    if license_row is not None:
        lic = str(getattr(license_row, "plan", None) or "").strip().lower()
        if lic in _PLAN_CODES:
            return lic
    return "starter"


def lead_forms_base_cap(plan_code: str) -> int:
    """Included active forms: Solo/starter 1, Team 3, Business (pro) 20."""
    p = (plan_code or "").strip().lower() or "starter"
    if p in {"pro", "enterprise"}:
        return 20
    if p == "team":
        return 3
    return 1


async def count_active_tenant_lead_forms(db: AsyncSession, tenant_id: str) -> int:
    stmt = (
        select(func.count())
        .select_from(TenantLeadForm)
        .where(TenantLeadForm.tenant_id == tenant_id)
        .where(TenantLeadForm.is_active.is_(True))
    )
    return int((await db.execute(stmt)).scalar_one() or 0)


async def resolve_effective_lead_forms_cap(db: AsyncSession, tenant_id: str) -> tuple[int, str]:
    plan = await _plan_code_for_usage_caps(db, tenant_id)
    base = lead_forms_base_cap(plan)
    tenant = await db.get(Tenant, tenant_id)
    st = tenant.settings if tenant is not None and isinstance(tenant.settings, dict) else None
    extra = pack_addon_int(st, LEAD_FORMS_ACTIVE_CAP)
    return base + extra, plan


async def ensure_tenant_lead_form_active_count_allows_transition(
    db: AsyncSession,
    tenant_id: str,
    *,
    was_active: bool,
    will_be_active: bool,
) -> None:
    """402 when enabling a form would exceed cap (create or re-activate)."""
    if not will_be_active or was_active:
        return
    cap, plan = await resolve_effective_lead_forms_cap(db, tenant_id)
    n = await count_active_tenant_lead_forms(db, tenant_id)
    if n >= cap:
        raise HTTPException(
            status_code=402,
            detail={
                "code": "lead_forms_limit_reached",
                "message": (
                    f"Active lead form limit reached ({cap} on this plan, including add-ons). "
                    "Deactivate a form, buy a pack, or upgrade in Billing."
                ),
                "plan": plan,
                "limit": cap,
                "current": n,
            },
        )


_SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_PUBLIC_SLUG_MIN_LEN = 2
_PUBLIC_SLUG_MAX_LEN = 64


def normalize_and_validate_public_slug(raw: str | None) -> str | None:
    """Return normalized slug or None to clear; raises ValueError if non-empty but invalid."""
    if raw is None:
        return None
    s = raw.strip().lower()
    if not s:
        return None
    if len(s) < _PUBLIC_SLUG_MIN_LEN or len(s) > _PUBLIC_SLUG_MAX_LEN:
        raise ValueError(
            f"public_slug must be {_PUBLIC_SLUG_MIN_LEN}-{_PUBLIC_SLUG_MAX_LEN} characters after normalization"
        )
    if not _SLUG_PATTERN.match(s):
        raise ValueError("public_slug must be lowercase letters, digits, and hyphens (no leading/trailing hyphen)")
    return s


async def load_active_lead_form_for_public_intake(
    db: AsyncSession,
    tenant_id: str,
    *,
    lead_form_id: str | None,
    lead_form_slug: str | None,
) -> TenantLeadForm | None:
    """Resolve an active form for POST /public/intake; raises HTTPException if both id and slug are set."""
    fid = (lead_form_id or "").strip()
    slug_raw = (lead_form_slug or "").strip()
    if fid and slug_raw:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "lead_form_reference_ambiguous",
                "message": "Send only one of lead_form_id or lead_form_slug.",
            },
        )
    if not fid and not slug_raw:
        return None
    if fid:
        return (
            await db.execute(
                select(TenantLeadForm).where(
                    TenantLeadForm.tenant_id == tenant_id,
                    TenantLeadForm.id == fid,
                    TenantLeadForm.is_active.is_(True),
                )
            )
        ).scalar_one_or_none()
    try:
        slug = normalize_and_validate_public_slug(slug_raw)
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail={"code": "lead_form_slug_invalid", "message": str(exc)},
        ) from exc
    if not slug:
        return None
    return (
        await db.execute(
            select(TenantLeadForm).where(
                TenantLeadForm.tenant_id == tenant_id,
                TenantLeadForm.public_slug == slug,
                TenantLeadForm.is_active.is_(True),
            )
        )
    ).scalar_one_or_none()


async def list_active_lead_forms_with_public_slug(db: AsyncSession, tenant_id: str) -> list[TenantLeadForm]:
    rows = (
        await db.execute(
            select(TenantLeadForm)
            .where(TenantLeadForm.tenant_id == tenant_id)
            .where(TenantLeadForm.is_active.is_(True))
            .where(TenantLeadForm.public_slug.isnot(None))
            .where(TenantLeadForm.public_slug != "")
            .order_by(TenantLeadForm.title.asc())
        )
    ).scalars().all()
    return list(rows)


async def _public_slug_taken_globally_pg(db: AsyncSession, slug: str, exclude_form_id: str) -> bool | None:
    try:
        ex = (exclude_form_id or "").strip()
        r = await db.execute(
            text("SELECT public.hf_lead_form_public_slug_taken(:s, :e) AS taken").bindparams(s=slug, e=ex)
        )
        row = r.first()
        if row is None:
            return None
        return bool(row[0])
    except ProgrammingError:
        await db.rollback()
        return None


async def ensure_public_slug_unique_globally(
    db: AsyncSession,
    *,
    slug: str | None,
    exclude_form_id: str,
) -> None:
    """409 if any workspace already published this public_slug (public intake URLs are global)."""
    if not slug:
        return
    bind = db.get_bind()
    taken: bool | None = None
    if bind.dialect.name == "postgresql":
        taken = await _public_slug_taken_globally_pg(db, slug, exclude_form_id)
    if taken is None:
        other = (
            await db.execute(
                select(TenantLeadForm).where(
                    TenantLeadForm.public_slug == slug,
                    TenantLeadForm.id != exclude_form_id,
                )
            )
        ).scalar_one_or_none()
        taken = other is not None
    if taken:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "lead_form_public_slug_taken",
                "message": "Another workspace already uses this public slug. Choose a different slug.",
            },
        )


async def ensure_public_slug_unique_for_tenant(
    db: AsyncSession,
    tenant_id: str,
    *,
    slug: str | None,
    exclude_form_id: str,
) -> None:
    """Backward-compatible name; tenant_id is ignored (slug is globally unique)."""
    await ensure_public_slug_unique_globally(db, slug=slug, exclude_form_id=exclude_form_id)


def lead_form_meta_for_intake_state(row: TenantLeadForm) -> dict[str, Any]:
    return {
        "id": row.id,
        "title": row.title or "",
        "public_slug": row.public_slug or None,
    }
