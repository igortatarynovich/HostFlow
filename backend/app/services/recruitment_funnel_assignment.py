"""Canonical assignment helpers — single entry point for runtime funnel binding."""

from __future__ import annotations

from typing import Optional

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.candidate import Candidate
from backend.app.models.candidate_profile import CandidateProfile
from backend.app.models.lead import Lead
from backend.app.models.vacancy import Vacancy
from backend.app.services.recruitment_funnel_resolver import (
    RecruitmentFunnelForbiddenError,
    RecruitmentFunnelNotFoundError,
    RecruitmentFunnelResolveResult,
    RecruitmentModuleNotEnabledError,
    RecruitmentPipelineType,
    first_funnel_stage_code,
    resolve_recruitment_funnel,
)


def _http_from_resolve_error(exc: Exception) -> HTTPException:
    if isinstance(exc, RecruitmentModuleNotEnabledError):
        return HTTPException(status_code=403, detail=str(exc))
    if isinstance(exc, RecruitmentFunnelForbiddenError):
        return HTTPException(status_code=403, detail=str(exc))
    if isinstance(exc, RecruitmentFunnelNotFoundError):
        return HTTPException(status_code=422, detail=str(exc))
    return HTTPException(status_code=422, detail=str(exc))


async def _vacancy_profile_funnel_hint(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate: Candidate,
) -> Optional[str]:
    """Vacancy assignment first (ADR-035 §12); Candidate Profile funnel_id is legacy only."""
    vacancy_id = str(getattr(candidate, "vacancy_id", None) or "").strip()
    if not vacancy_id:
        return None
    vacancy = (
        await db.execute(
            select(Vacancy).where(
                Vacancy.id == vacancy_id,
                Vacancy.tenant_id == str(tenant_id),
            )
        )
    ).scalar_one_or_none()
    if vacancy is None:
        return None
    vac_funnel = str(getattr(vacancy, "funnel_id", None) or "").strip()
    if vac_funnel:
        return vac_funnel
    # Legacy strangler: profile.funnel_id until vacancy assignment is universal.
    profile_id = str(getattr(vacancy, "candidate_profile_id", None) or "").strip()
    if not profile_id:
        return None
    profile = (
        await db.execute(
            select(CandidateProfile).where(
                CandidateProfile.id == profile_id,
                CandidateProfile.tenant_id == str(tenant_id),
            )
        )
    ).scalar_one_or_none()
    if profile is None:
        return None
    prof_funnel = str(getattr(profile, "funnel_id", None) or "").strip()
    return prof_funnel or None


async def resolve_funnel_id_for_vacancy(
    db: AsyncSession,
    *,
    tenant_id: str,
    vacancy: Vacancy,
) -> Optional[str]:
    """Operational pipeline for a vacancy: Vacancy.funnel_id, else legacy profile.funnel_id."""
    vac_funnel = str(getattr(vacancy, "funnel_id", None) or "").strip()
    if vac_funnel:
        return vac_funnel
    profile_id = str(getattr(vacancy, "candidate_profile_id", None) or "").strip()
    if not profile_id:
        return None
    profile = (
        await db.execute(
            select(CandidateProfile).where(
                CandidateProfile.id == profile_id,
                CandidateProfile.tenant_id == str(tenant_id),
            )
        )
    ).scalar_one_or_none()
    if profile is None:
        return None
    return str(getattr(profile, "funnel_id", None) or "").strip() or None


async def assign_recruitment_funnel_to_lead(
    db: AsyncSession,
    *,
    tenant_id: str,
    lead: Lead,
    explicit_funnel_id: Optional[str] = None,
    pipeline_type: RecruitmentPipelineType = "lead",
) -> Optional[RecruitmentFunnelResolveResult]:
    """Bind ``lead.funnel_id`` via resolver. Returns None when company_id missing."""
    company_id = str(getattr(lead, "company_id", None) or "").strip()
    if not company_id:
        return None
    try:
        result = await resolve_recruitment_funnel(
            db,
            tenant_id=tenant_id,
            company_id=company_id,
            pipeline_type=pipeline_type,
            explicit_funnel_id=explicit_funnel_id,
        )
    except (
        RecruitmentModuleNotEnabledError,
        RecruitmentFunnelForbiddenError,
        RecruitmentFunnelNotFoundError,
    ) as exc:
        raise _http_from_resolve_error(exc) from exc
    lead.funnel_id = result.funnel.id
    return result


async def resolve_recruitment_funnel_for_candidate(
    db: AsyncSession,
    *,
    tenant_id: str,
    company_id: str,
    explicit_funnel_id: Optional[str] = None,
) -> RecruitmentFunnelResolveResult:
    """Resolve candidate pipeline funnel; raises HTTPException on failure."""
    try:
        return await resolve_recruitment_funnel(
            db,
            tenant_id=tenant_id,
            company_id=company_id,
            pipeline_type="candidate",
            explicit_funnel_id=explicit_funnel_id,
        )
    except (
        RecruitmentModuleNotEnabledError,
        RecruitmentFunnelForbiddenError,
        RecruitmentFunnelNotFoundError,
    ) as exc:
        raise _http_from_resolve_error(exc) from exc


async def reconcile_candidate_funnel_on_company_change(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate: Candidate,
    new_company_id: Optional[str],
    changes: dict,
) -> None:
    """When company/vacancy scope changes, rebind funnel via Vacancy assignment first."""
    old_company = str(getattr(candidate, "company_id", None) or "").strip() or None
    new_company = str(new_company_id or "").strip() or None if new_company_id is not None else old_company

    if "company_id" not in changes and "vacancy_id" not in changes:
        return

    # Vacancy change within same company still rebinds from Vacancy.funnel_id.
    vacancy_changed = "vacancy_id" in changes
    company_changed = str(old_company or "") != str(new_company or "")
    if not vacancy_changed and not company_changed:
        return

    if not new_company:
        changes["funnel_id"] = None
        return

    vacancy_id = changes.get("vacancy_id", getattr(candidate, "vacancy_id", None))
    explicit: Optional[str] = None
    if vacancy_id:
        vacancy = (
            await db.execute(
                select(Vacancy).where(
                    Vacancy.id == str(vacancy_id),
                    Vacancy.tenant_id == str(tenant_id),
                )
            )
        ).scalar_one_or_none()
        if vacancy is not None:
            explicit = await resolve_funnel_id_for_vacancy(
                db, tenant_id=tenant_id, vacancy=vacancy
            )

    result = await resolve_recruitment_funnel_for_candidate(
        db,
        tenant_id=tenant_id,
        company_id=new_company,
        explicit_funnel_id=explicit,
    )
    changes["funnel_id"] = result.funnel.id


async def reconcile_lead_funnel_on_company_change(
    db: AsyncSession,
    *,
    tenant_id: str,
    lead: Lead,
    old_company_id: Optional[str],
    new_company_id: Optional[str],
) -> None:
    """Rebind lead funnel when company scope changes."""
    old_company = str(old_company_id or "").strip() or None
    new_company = str(new_company_id or "").strip() or None
    if str(old_company or "") == str(new_company or ""):
        return
    if not new_company:
        lead.funnel_id = None
        return
    await assign_recruitment_funnel_to_lead(
        db,
        tenant_id=tenant_id,
        lead=lead,
        pipeline_type="lead",
    )


async def resolve_lead_funnel_id_for_display(
    db: AsyncSession,
    *,
    tenant_id: str,
    lead: Lead,
) -> Optional[str]:
    """Resolve lead funnel for stage-contract display; falls back to stored id on failure."""
    company_id = str(getattr(lead, "company_id", None) or "").strip()
    explicit = str(getattr(lead, "funnel_id", None) or "").strip() or None
    if not company_id:
        return explicit
    try:
        result = await resolve_recruitment_funnel(
            db,
            tenant_id=tenant_id,
            company_id=company_id,
            pipeline_type="lead",
            explicit_funnel_id=explicit,
        )
        return result.funnel.id
    except (
        RecruitmentModuleNotEnabledError,
        RecruitmentFunnelForbiddenError,
        RecruitmentFunnelNotFoundError,
    ):
        return explicit


async def resolve_candidate_funnel_id_for_runtime(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate: Candidate,
) -> Optional[str]:
    """Runtime funnel id for PE mapping — resolver only, no direct tenant default queries."""
    company_id = str(getattr(candidate, "company_id", None) or "").strip()
    explicit = str(getattr(candidate, "funnel_id", None) or "").strip() or None

    if not explicit:
        explicit = await _vacancy_profile_funnel_hint(
            db, tenant_id=tenant_id, candidate=candidate
        )

    if company_id:
        try:
            result = await resolve_recruitment_funnel(
                db,
                tenant_id=tenant_id,
                company_id=company_id,
                pipeline_type="candidate",
                explicit_funnel_id=explicit,
            )
            return result.funnel.id
        except RecruitmentFunnelForbiddenError:
            if explicit:
                raise
        except (RecruitmentModuleNotEnabledError, RecruitmentFunnelNotFoundError):
            return explicit

    return explicit


def default_stage_from_funnel_result(
    result: RecruitmentFunnelResolveResult,
    *,
    stage_explicit: bool,
    current_stage_code: str,
) -> str:
    if stage_explicit:
        return current_stage_code
    first = first_funnel_stage_code(result.funnel)
    return first or current_stage_code
