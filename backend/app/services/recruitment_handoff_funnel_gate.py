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


# Operator lane shown while handoff is on, removed when it is turned off.
# Codes stay in the recruitment stage catalog; labels are the operator words.
HANDOFF_LANE_READY = ("ready_for_handoff", "Готов к передаче")
HANDOFF_LANE_RETURNED = ("handoff_returned", "Возвращён")
HANDOFF_LANE_TRANSFERRED_CLIENT = ("processing_by_client", "Передан")
HANDOFF_LANE_TRANSFERRED_HR = ("processing_by_hr", "Передан")
_HANDOFF_LANE_REMOVABLE_CODES = frozenset(
    {
        HANDOFF_LANE_READY[0],
        HANDOFF_LANE_RETURNED[0],
        HANDOFF_LANE_TRANSFERRED_CLIENT[0],
        HANDOFF_LANE_TRANSFERRED_HR[0],
    }
)
_HANDOFF_LANE_TERMINAL_CODES = frozenset({"rejected", "declined", "employed", "hired"})
_DISABLE_OCCUPIED_DETAIL = (
    "Нельзя отключить передачу: на этапах «Готов к передаче», «Передан» или «Возвращён» "
    "ещё есть кандидаты. Сначала переведите их на другой этап."
)


def handoff_lane_stage_specs(*, to_client: bool, to_hr: bool) -> list[tuple[str, str]]:
    """Stages the operator sees while transfer is on: ready, transferred, returned."""
    specs = [HANDOFF_LANE_READY]
    if to_hr and not to_client:
        specs.append(HANDOFF_LANE_TRANSFERRED_HR)
    elif to_hr and to_client:
        specs.append(HANDOFF_LANE_TRANSFERRED_CLIENT)
        specs.append(HANDOFF_LANE_TRANSFERRED_HR)
    else:
        specs.append(HANDOFF_LANE_TRANSFERRED_CLIENT)
    specs.append(HANDOFF_LANE_RETURNED)
    return specs


async def _company_candidate_funnels(
    db: AsyncSession,
    *,
    tenant_id: str,
    company_id: str,
    allow_bootstrap: bool = True,
) -> list[Funnel]:
    """Recruitment funnels this company owns or assigns on a vacancy or profile.

    A vacancy may point at another company's funnel (shared agency pipeline).
    That funnel is the one the candidate card shows, so the transfer lane
    belongs there too.
    """
    from backend.app.services.recruitment_funnel_resolver import RECRUITMENT_MODULE_KEY

    ids: set[str] = set()
    from backend.app.services import company_module_settings_service as cms_svc

    row = await cms_svc.get_row(db, tenant_id, company_id, RECRUITMENT_MODULE_KEY)
    settings = row.settings_json if row is not None and isinstance(row.settings_json, dict) else {}
    default_fid = str(settings.get("default_candidate_funnel_id") or "").strip()
    if default_fid:
        ids.add(default_fid)

    vacancy_rows = (
        await db.execute(
            select(Vacancy.funnel_id, Vacancy.candidate_profile_id).where(
                Vacancy.tenant_id == tenant_id,
                Vacancy.company_id == company_id,
            )
        )
    ).all()
    profile_ids: set[str] = set()
    for vac_funnel_id, profile_id in vacancy_rows:
        fid = str(vac_funnel_id or "").strip()
        if fid:
            ids.add(fid)
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
            ids.add(fid)
    if profile_ids:
        extra = (
            await db.execute(
                select(CandidateProfile.funnel_id).where(CandidateProfile.id.in_(profile_ids))
            )
        ).scalars().all()
        for funnel_id in extra:
            fid = str(funnel_id or "").strip()
            if fid:
                ids.add(fid)

    company_rows = (
        await db.execute(
            select(Funnel.id).where(
                Funnel.tenant_id == tenant_id,
                Funnel.company_id == company_id,
                Funnel.type == "candidate",
                Funnel.module_key == RECRUITMENT_MODULE_KEY,
            )
        )
    ).scalars().all()
    for fid in company_rows:
        raw = str(fid or "").strip()
        if raw:
            ids.add(raw)

    funnels: list[Funnel] = []
    seen: set[str] = set()
    for fid in ids:
        funnel = await _load_recruitment_candidate_funnel(
            db, tenant_id=tenant_id, funnel_id=fid
        )
        if funnel is None or funnel.id in seen:
            continue
        if str(funnel.tenant_id or "") == "default":
            continue
        seen.add(funnel.id)
        funnels.append(funnel)

    if funnels or not allow_bootstrap:
        return funnels

    from backend.app.models.company import Company
    from backend.app.models.tenant import Tenant
    from backend.app.services.recruitment_funnel_bootstrap import (
        bootstrap_recruitment_funnels_for_company,
    )

    tenant = await db.get(Tenant, tenant_id)
    company = await db.get(Company, company_id)
    if tenant is None or company is None:
        return []
    created = await bootstrap_recruitment_funnels_for_company(
        db,
        tenant=tenant,
        company=company,
        company_type=None,
    )
    created_id = str(created.get("candidate") or "").strip()
    if not created_id:
        return []
    funnel = await _load_recruitment_candidate_funnel(
        db, tenant_id=tenant_id, funnel_id=created_id
    )
    return [funnel] if funnel is not None else []


async def _ensure_lane_stages_on_funnel(
    db: AsyncSession,
    *,
    tenant_id: str,
    funnel: Funnel,
    specs: list[tuple[str, str]],
) -> None:
    from uuid import uuid4

    from backend.app.process_engine.pipeline_mapping import ensure_funnel_stage_pe_mapping

    rows = list(
        (
            await db.execute(
                select(FunnelStage)
                .where(FunnelStage.funnel_id == funnel.id)
                .order_by(FunnelStage.order, FunnelStage.code)
            )
        ).scalars().all()
    )
    by_code = {str(row.code or "").strip().lower(): row for row in rows}
    missing = [spec for spec in specs if spec[0] not in by_code]
    codes = [str(row.code) for row in rows]
    if missing:
        insert_at = len(codes)
        for index, code in enumerate(codes):
            if code.strip().lower() in _HANDOFF_LANE_TERMINAL_CODES:
                insert_at = index
                break
        for offset, (code, _label) in enumerate(missing):
            codes.insert(insert_at + offset, code)
            stage = FunnelStage(
                id=str(uuid4()),
                funnel_id=funnel.id,
                code=code,
                label=_label,
                system_stage="in_progress",
                order=insert_at + offset,
                is_terminal=False,
            )
            db.add(stage)
            by_code[code] = stage
        await db.flush()
        order_of = {code: index for index, code in enumerate(codes)}
        fresh = list(
            (
                await db.execute(
                    select(FunnelStage).where(FunnelStage.funnel_id == funnel.id)
                )
            ).scalars().all()
        )
        for stage in fresh:
            key = str(stage.code or "")
            if key in order_of:
                stage.order = order_of[key]

    for code, label in specs:
        stage = by_code.get(code)
        if stage is None:
            continue
        if str(stage.label or "") != label:
            stage.label = label
        await ensure_funnel_stage_pe_mapping(db, stage, tenant_id=tenant_id)
    await db.flush()


async def _candidates_on_handoff_lane(
    db: AsyncSession,
    *,
    tenant_id: str,
    company_id: str,
) -> int:
    from sqlalchemy import func

    from backend.app.models.candidate import Candidate

    codes = list(_HANDOFF_LANE_REMOVABLE_CODES)
    count = await db.scalar(
        select(func.count())
        .select_from(Candidate)
        .where(
            Candidate.tenant_id == tenant_id,
            Candidate.company_id == company_id,
            func.lower(Candidate.stage).in_(codes),
        )
    )
    return int(count or 0)


async def _funnel_ids_kept_by_other_handoff(
    db: AsyncSession,
    *,
    tenant_id: str,
    company_id: str,
) -> set[str]:
    """Funnels another handoff-on company still assigns. Do not strip those."""
    links = await list_links_for_agency(db, tenant_id)
    others: set[str] = set()
    for link in links:
        if not link.get_handoff_enabled():
            continue
        others.update(operating_company_ids_for_link(link))
    others.discard(company_id)
    kept: set[str] = set()
    for other_id in others:
        for funnel in await _company_candidate_funnels(
            db,
            tenant_id=tenant_id,
            company_id=other_id,
            allow_bootstrap=False,
        ):
            kept.add(funnel.id)
    return kept


async def apply_company_handoff_funnel_stages(
    db: AsyncSession,
    *,
    tenant_id: str,
    company_id: str | None,
    enabled: bool,
    to_client: bool = True,
    to_hr: bool = False,
) -> None:
    """Add the transfer lane when handoff turns on, and remove it when handoff turns off."""
    cid = str(company_id or "").strip()
    tid = str(tenant_id or "").strip()
    if not cid or not tid:
        return
    funnels = await _company_candidate_funnels(db, tenant_id=tid, company_id=cid)
    if not funnels:
        return
    if not enabled:
        occupied = await _candidates_on_handoff_lane(db, tenant_id=tid, company_id=cid)
        if occupied:
            raise HandoffFunnelGateError(_DISABLE_OCCUPIED_DETAIL)
        kept = await _funnel_ids_kept_by_other_handoff(
            db, tenant_id=tid, company_id=cid
        )
        for funnel in funnels:
            if funnel.id in kept:
                continue
            rows = list(
                (
                    await db.execute(
                        select(FunnelStage).where(FunnelStage.funnel_id == funnel.id)
                    )
                ).scalars().all()
            )
            for stage in rows:
                if str(stage.code or "").strip().lower() in _HANDOFF_LANE_REMOVABLE_CODES:
                    await db.delete(stage)
        await db.flush()
        return

    specs = handoff_lane_stage_specs(to_client=to_client, to_hr=to_hr)
    for funnel in funnels:
        await _ensure_lane_stages_on_funnel(
            db, tenant_id=tid, funnel=funnel, specs=specs
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
