"""Ensure recruitment funnels + vacancy defaults for launch-search (подбор)."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.candidate_profile import CandidateProfile
from backend.app.models.company import Company
from backend.app.models.tenant import Tenant
from backend.app.models.vacancy import Vacancy
from backend.app.services.launch_search_role_defaults import (
    LAUNCH_SEARCH_ROLE_BY_CODE,
    ensure_launch_search_role_funnels_for_company,
)
from backend.app.services.recruitment_funnel_bootstrap import (
    bootstrap_recruitment_funnels_for_company,
    resolve_company_default_funnel_id,
)
from backend.app.services.recruitment_funnel_resolver import (
    RecruitmentFunnelNotFoundError,
    resolve_recruitment_funnel,
)

logger = logging.getLogger(__name__)

LaunchSearchRole = str


class LaunchSearchSetupError(Exception):
    """Launch-search provisioning failed."""


def _ensure_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _coalesce_industry(*values: str | None) -> str | None:
    for value in values:
        if value and str(value).strip():
            return str(value).strip()
    return None


def _tenant_industry_from_settings(settings: Any) -> str | None:
    if not isinstance(settings, dict):
        return None
    raw = settings.get("industry")
    return str(raw).strip() if isinstance(raw, str) and raw.strip() else None


async def _resolve_company_type_for_bootstrap(
    db: AsyncSession,
    *,
    tenant_id: str,
    tenant: Tenant,
    company: Company,
) -> tuple[str, str | None]:
    extra = _ensure_dict(getattr(company, "extra", None))
    company_type = str(extra.get("company_type") or "").strip().lower() or None
    industry = _coalesce_industry(
        str(extra.get("industry") or "").strip() or None,
        _tenant_industry_from_settings(tenant.settings),
    )

    if not company_type:
        from backend.app.services.recruitment_funnel_bootstrap import resolve_first_operating_company_id

        operating_id = await resolve_first_operating_company_id(db, tenant_id=tenant_id)
        if operating_id:
            operating = (
                await db.execute(
                    select(Company).where(Company.id == operating_id, Company.tenant_id == tenant_id).limit(1)
                )
            ).scalar_one_or_none()
            if operating is not None:
                op_extra = _ensure_dict(getattr(operating, "extra", None))
                company_type = str(op_extra.get("company_type") or "").strip().lower() or None
                industry = _coalesce_industry(
                    industry,
                    str(op_extra.get("industry") or "").strip() or None,
                )

    if not company_type and isinstance(tenant.settings, dict):
        company_type = str(tenant.settings.get("business_type") or "agency").strip().lower() or "agency"

    return company_type or "agency", industry


async def ensure_recruitment_funnels_for_company(
    db: AsyncSession,
    *,
    tenant_id: str,
    company_id: str,
    tenant: Tenant | None = None,
    company: Company | None = None,
) -> dict[str, str]:
    """Idempotently ensure default candidate + lead funnels and role funnels for a company."""
    tid = str(tenant_id).strip()
    cid = str(company_id).strip()

    tenant_obj = tenant
    if tenant_obj is None:
        tenant_obj = await db.get(Tenant, tid)
    if tenant_obj is None:
        raise LaunchSearchSetupError(f"tenant not found: {tid}")

    company_obj = company
    if company_obj is None:
        company_obj = (
            await db.execute(
                select(Company).where(Company.id == cid, Company.tenant_id == tid).limit(1)
            )
        ).scalar_one_or_none()
    if company_obj is None:
        raise LaunchSearchSetupError(f"company not found: {cid}")

    company_type, industry = await _resolve_company_type_for_bootstrap(
        db,
        tenant_id=tid,
        tenant=tenant_obj,
        company=company_obj,
    )
    tenant_modules = (
        _ensure_dict(tenant_obj.settings.get("modules")) if isinstance(tenant_obj.settings, dict) else {}
    )

    out = await bootstrap_recruitment_funnels_for_company(
        db,
        tenant=tenant_obj,
        company=company_obj,
        company_type=company_type,
        tenant_modules=tenant_modules,
        industry=industry,
    )

    try:
        role_funnels = await ensure_launch_search_role_funnels_for_company(
            db,
            tenant_id=tid,
            company_id=cid,
        )
        out.update({f"role_{role}": funnel_id for role, funnel_id in role_funnels.items()})
    except Exception:
        logger.warning(
            "launch_search role funnel bootstrap failed tenant=%s company=%s",
            tid,
            cid,
            exc_info=True,
        )

    await db.flush()
    return out


async def _pick_role_profile(
    db: AsyncSession,
    *,
    tenant_id: str,
    role: LaunchSearchRole,
) -> CandidateProfile | None:
    spec = LAUNCH_SEARCH_ROLE_BY_CODE.get(role) or LAUNCH_SEARCH_ROLE_BY_CODE.get("driver")
    if spec is None:
        return None

    codes = [spec.candidate_profile_code, "driver_ce_default"]
    rows = (
        await db.execute(
            select(CandidateProfile)
            .where(
                CandidateProfile.tenant_id == tenant_id,
                CandidateProfile.is_active.is_(True),
            )
            .order_by(CandidateProfile.created_at.asc())
        )
    ).scalars().all()

    for code in codes:
        match = next((p for p in rows if p.code == code), None)
        if match is not None:
            return match
    return next((p for p in rows if p.is_system), None) or (rows[0] if rows else None)


async def _pick_role_funnel_id(
    db: AsyncSession,
    *,
    tenant_id: str,
    company_id: str,
    role: LaunchSearchRole,
    profile: CandidateProfile | None,
    bootstrapped: dict[str, str],
) -> str | None:
    spec = LAUNCH_SEARCH_ROLE_BY_CODE.get(role) or LAUNCH_SEARCH_ROLE_BY_CODE.get("driver")
    if spec is None:
        return bootstrapped.get("candidate")

    role_key = f"role_{role}"
    if bootstrapped.get(role_key):
        return bootstrapped[role_key]

    from backend.app.models.funnel import Funnel

    rows = (
        await db.execute(
            select(Funnel).where(
                Funnel.tenant_id == tenant_id,
                Funnel.company_id == company_id,
                Funnel.type == "candidate",
                Funnel.name == spec.funnel_name,
            )
        )
    ).scalars().all()
    if rows:
        return str(rows[0].id)

    if profile is not None and profile.funnel_id:
        return str(profile.funnel_id)

    return bootstrapped.get("candidate") or await resolve_company_default_funnel_id(
        db,
        tenant_id=tenant_id,
        company_id=company_id,
        funnel_type="candidate",
    )


async def ensure_launch_search_vacancy_defaults(
    db: AsyncSession,
    *,
    tenant_id: str,
    vacancy_id: str,
    role: LaunchSearchRole = "driver",
) -> dict[str, str | None]:
    """Bootstrap company funnels and attach role funnel + profile to a launch-search vacancy."""
    tid = str(tenant_id).strip()
    vid = str(vacancy_id).strip()
    normalized_role = str(role or "driver").strip().lower()
    if normalized_role not in LAUNCH_SEARCH_ROLE_BY_CODE:
        normalized_role = "driver"

    vacancy = (
        await db.execute(
            select(Vacancy).where(Vacancy.id == vid, Vacancy.tenant_id == tid).limit(1)
        )
    ).scalar_one_or_none()
    if vacancy is None:
        raise LaunchSearchSetupError("vacancy not found")

    company_id = str(getattr(vacancy, "company_id", None) or "").strip()
    if not company_id:
        raise LaunchSearchSetupError("vacancy has no company_id")

    bootstrapped = await ensure_recruitment_funnels_for_company(
        db,
        tenant_id=tid,
        company_id=company_id,
    )

    profile = await _pick_role_profile(db, tenant_id=tid, role=normalized_role)
    funnel_id = await _pick_role_funnel_id(
        db,
        tenant_id=tid,
        company_id=company_id,
        role=normalized_role,
        profile=profile,
        bootstrapped=bootstrapped,
    )

    if not funnel_id:
        raise LaunchSearchSetupError("no candidate funnel available for launch search")

    vacancy.funnel_id = funnel_id
    if profile is not None:
        vacancy.candidate_profile_id = str(profile.id)

    await db.flush()

    try:
        await resolve_recruitment_funnel(
            db,
            tenant_id=tid,
            company_id=company_id,
            pipeline_type="lead",
        )
    except RecruitmentFunnelNotFoundError as exc:
        raise LaunchSearchSetupError(
            "lead funnel is missing; public candidate link cannot work"
        ) from exc

    funnel_name = None
    if funnel_id:
        from backend.app.models.funnel import Funnel

        funnel = await db.get(Funnel, funnel_id)
        funnel_name = getattr(funnel, "name", None)

    return {
        "vacancy_id": vid,
        "company_id": company_id,
        "funnel_id": funnel_id,
        "funnel_name": funnel_name,
        "profile_id": str(profile.id) if profile is not None else None,
        "profile_name": getattr(profile, "name", None) if profile is not None else None,
        "lead_funnel_id": bootstrapped.get("lead"),
    }
