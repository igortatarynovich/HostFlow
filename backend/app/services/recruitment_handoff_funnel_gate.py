"""Handoff-on companies may only use recruitment candidate funnels with ready_for_handoff."""

from __future__ import annotations

from typing import Any, Iterable

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.constants.funnel_types import RECRUITMENT_MODULE_KEY
from backend.app.models.candidate_profile import CandidateProfile
from backend.app.models.funnel import Funnel, FunnelStage
from backend.app.models.vacancy import Vacancy
from backend.app.services.stage_meta_recruitment_filter import handoff_lane_active_for_company
from backend.app.services.tenant_links import list_links_for_agency

READY_FOR_HANDOFF_STAGE_CODE = "ready_for_handoff"

_ASSIGN_DETAIL = (
    "Funnel must include stage ready_for_handoff (Готов к передаче) "
    "when handoff is enabled for this client"
)
_DELETE_DETAIL = (
    "Cannot remove stage ready_for_handoff (Готов к передаче) "
    "while handoff is enabled for this client"
)


class HandoffFunnelGateError(Exception):
    """409 conflict: handoff is on and the candidate funnel lacks ready_for_handoff."""

    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)

    def as_http_exception(self) -> HTTPException:
        return HTTPException(status_code=409, detail=self.detail)


def funnel_codes_include_ready_for_handoff(codes: Iterable[Any]) -> bool:
    return READY_FOR_HANDOFF_STAGE_CODE in {
        str(code or "").strip().lower() for code in codes if str(code or "").strip()
    }


def funnel_has_ready_for_handoff(stages: Iterable[Any]) -> bool:
    return funnel_codes_include_ready_for_handoff(
        getattr(stage, "code", None) for stage in stages
    )


def operating_company_ids_for_link(link: Any) -> set[str]:
    ids: set[str] = set()
    for attr in ("client_company_id", "handoff_include_company_id"):
        raw = str(getattr(link, attr, None) or "").strip()
        if raw:
            ids.add(raw)
    return ids


async def company_has_handoff_enabled(
    db: AsyncSession,
    *,
    tenant_id: str,
    company_id: str | None,
) -> bool:
    cid = str(company_id or "").strip()
    if not cid:
        return False
    links = await list_links_for_agency(db, str(tenant_id).strip())
    return handoff_lane_active_for_company(links, company_id=cid)


async def _stage_codes_for_funnel(db: AsyncSession, funnel_id: str) -> list[str]:
    rows = (
        await db.execute(select(FunnelStage.code).where(FunnelStage.funnel_id == funnel_id))
    ).scalars().all()
    return [str(code) for code in rows]


async def _load_recruitment_candidate_funnel(
    db: AsyncSession,
    *,
    tenant_id: str,
    funnel_id: str,
) -> Funnel | None:
    funnel = await db.get(Funnel, funnel_id)
    if funnel is None:
        return None
    if str(funnel.tenant_id or "") not in {str(tenant_id).strip(), "default"}:
        return None
    if str(funnel.type or "").strip() != "candidate":
        return None
    module_key = str(funnel.module_key or "").strip()
    if module_key and module_key != RECRUITMENT_MODULE_KEY:
        return None
    return funnel


async def ensure_candidate_funnel_allows_company_handoff(
    db: AsyncSession,
    *,
    tenant_id: str,
    company_id: str | None,
    funnel_id: str | None,
) -> None:
    """Block assigning a candidate funnel that lacks ready_for_handoff when handoff is on."""
    fid = str(funnel_id or "").strip()
    if not fid:
        return
    if not await company_has_handoff_enabled(db, tenant_id=tenant_id, company_id=company_id):
        return
    funnel = await _load_recruitment_candidate_funnel(db, tenant_id=tenant_id, funnel_id=fid)
    if funnel is None:
        return
    codes = await _stage_codes_for_funnel(db, funnel.id)
    if not funnel_codes_include_ready_for_handoff(codes):
        raise HandoffFunnelGateError(_ASSIGN_DETAIL)


async def ensure_vacancy_funnel_assignment_allowed(
    db: AsyncSession,
    *,
    tenant_id: str,
    company_id: str | None,
    funnel_id: str | None = None,
    candidate_profile_id: str | None = None,
) -> None:
    await ensure_candidate_funnel_allows_company_handoff(
        db,
        tenant_id=tenant_id,
        company_id=company_id,
        funnel_id=funnel_id,
    )
    pid = str(candidate_profile_id or "").strip()
    if not pid:
        return
    profile = await db.get(CandidateProfile, pid)
    if profile is None:
        return
    await ensure_candidate_funnel_allows_company_handoff(
        db,
        tenant_id=tenant_id,
        company_id=company_id or getattr(profile, "client_id", None),
        funnel_id=getattr(profile, "funnel_id", None),
    )


async def find_handoff_ready_candidate_funnel_id(
    db: AsyncSession,
    *,
    tenant_id: str,
    company_id: str,
) -> str | None:
    """Prefer a company copy; fall back to any tenant operational catalog funnel."""
    stmt = select(Funnel).where(
        Funnel.tenant_id == tenant_id,
        Funnel.company_id.isnot(None),
        Funnel.type == "candidate",
        Funnel.module_key == RECRUITMENT_MODULE_KEY,
    )
    funnels = list((await db.execute(stmt)).scalars().all())
    cid = str(company_id or "").strip()
    ordered = [funnel for funnel in funnels if str(funnel.company_id or "").strip() == cid]
    ordered.extend(funnel for funnel in funnels if str(funnel.company_id or "").strip() != cid)
    for funnel in ordered:
        codes = await _stage_codes_for_funnel(db, funnel.id)
        if funnel_codes_include_ready_for_handoff(codes):
            return funnel.id
    return None


async def _assigned_candidate_funnels_missing_ready(
    db: AsyncSession,
    *,
    tenant_id: str,
    company_id: str,
) -> list[str]:
    from backend.app.services import company_module_settings_service as cms_svc

    funnel_ids: set[str] = set()
    row = await cms_svc.get_row(db, tenant_id, company_id, RECRUITMENT_MODULE_KEY)
    settings = row.settings_json if row is not None and isinstance(row.settings_json, dict) else {}
    default_fid = str(settings.get("default_candidate_funnel_id") or "").strip()
    if default_fid:
        funnel_ids.add(default_fid)

    vacancies = (
        await db.execute(
            select(Vacancy.funnel_id, Vacancy.candidate_profile_id).where(
                Vacancy.tenant_id == tenant_id,
                Vacancy.company_id == company_id,
            )
        )
    ).all()
    profile_ids: set[str] = set()
    for vac_funnel_id, profile_id in vacancies:
        fid = str(vac_funnel_id or "").strip()
        if fid:
            funnel_ids.add(fid)
        pid = str(profile_id or "").strip()
        if pid:
            profile_ids.add(pid)

    scoped_profiles = (
        await db.execute(
            select(CandidateProfile.id, CandidateProfile.funnel_id).where(
                CandidateProfile.tenant_id == tenant_id,
                CandidateProfile.client_id == company_id,
            )
        )
    ).all()
    for pid, funnel_id in scoped_profiles:
        if str(pid or "").strip():
            profile_ids.add(str(pid).strip())
        fid = str(funnel_id or "").strip()
        if fid:
            funnel_ids.add(fid)

    if profile_ids:
        extra = (
            await db.execute(
                select(CandidateProfile.funnel_id).where(CandidateProfile.id.in_(profile_ids))
            )
        ).scalars().all()
        for funnel_id in extra:
            fid = str(funnel_id or "").strip()
            if fid:
                funnel_ids.add(fid)

    missing_names: list[str] = []
    seen: set[str] = set()
    for fid in funnel_ids:
        funnel = await _load_recruitment_candidate_funnel(
            db, tenant_id=tenant_id, funnel_id=fid
        )
        if funnel is None or funnel.id in seen:
            continue
        seen.add(funnel.id)
        codes = await _stage_codes_for_funnel(db, funnel.id)
        if not funnel_codes_include_ready_for_handoff(codes):
            missing_names.append(str(funnel.name or funnel.id))
    return missing_names


async def ensure_can_enable_handoff_for_company(
    db: AsyncSession,
    *,
    tenant_id: str,
    company_id: str | None,
) -> None:
    """Block turning handoff on when assigned candidate funnels lack ready_for_handoff."""
    cid = str(company_id or "").strip()
    if not cid:
        return
    missing = await _assigned_candidate_funnels_missing_ready(
        db, tenant_id=str(tenant_id).strip(), company_id=cid
    )
    if not missing:
        return
    names = ", ".join(missing)
    raise HandoffFunnelGateError(
        "Cannot enable handoff: assigned recruitment funnel(s) lack stage "
        f"ready_for_handoff (Готов к передаче): {names}. "
        "Add this stage or pick a funnel that includes it."
    )


async def ensure_can_drop_ready_for_handoff_from_funnel(
    db: AsyncSession,
    *,
    tenant_id: str,
    funnel: Funnel,
    remaining_codes: Iterable[Any],
) -> None:
    if str(getattr(funnel, "type", "") or "").strip() != "candidate":
        return
    if funnel_codes_include_ready_for_handoff(remaining_codes):
        return
    company_id = str(getattr(funnel, "company_id", None) or "").strip() or None
    if not await company_has_handoff_enabled(db, tenant_id=tenant_id, company_id=company_id):
        return
    raise HandoffFunnelGateError(_DELETE_DETAIL)
