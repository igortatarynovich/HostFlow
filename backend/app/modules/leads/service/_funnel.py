"""Lead conversion funnel + stage health analytics.

Extracted from ``backend/app/modules/leads/service/__init__.py`` (Phase 1 #3
god-module split, step 4/N): lost-from-stage / lost-reason breakdowns,
``ConversionFunnelSliceParams`` filter dataclass, slice predicate builder,
per-root / per-stage count + dwell aggregations, ``_compute_lead_conversion_funnel``,
``lead_conversion_funnel_snapshot`` and ``lead_stage_health_snapshot``.

Re-exported via ``service/__init__.py`` so ``router`` and tests keep using the
historical ``service.<name>`` access pattern.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from typing import Any, List, Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy import exists, func, literal, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models import ActivityLog, Candidate, Lead
from backend.app.models.funnel import Funnel, FunnelStage
from backend.app.modules.leads.schemas import (
    LeadConversionFunnelCohortWindow,
    LeadConversionFunnelEdge,
    LeadConversionFunnelLostFromStage,
    LeadConversionFunnelLostReasonRow,
    LeadConversionFunnelResponse,
    LeadConversionFunnelStage,
    LeadStageHealthResponse,
    LeadStageHealthRow,
)

from ._listing import (
    CONVERSION_ROOTS_SET,
    CONVERSION_ROOT_ORDER,
    _LEAD_LEGACY_STAGE_TO_ROOT,
    _build_lead_list_filters,
    _sql_effective_lead_conversion_root,
    count_leads,
)


async def _lost_from_stage_breakdown(
    db: AsyncSession,
    *,
    tenant_id: str,
    own_company_id: str | None,
    slice_params: ConversionFunnelSliceParams,
) -> list[LeadConversionFunnelLostFromStage]:
    """
    Distinct leads per prior CRM stage when `lead.stage_changed` moved them into `lost`
    (payload.from_stage → payload.to_stage=lost). Respects conversion-funnel slice filters on Lead.
    """
    from_stage_txt = func.coalesce(
        func.nullif(ActivityLog.payload["from_stage"].as_string(), ""),
        literal("unknown"),
    )
    cnt = func.count(func.distinct(Lead.id))
    stmt = (
        select(from_stage_txt.label("fs"), cnt)
        .select_from(ActivityLog)
        .join(Lead, Lead.id == ActivityLog.target_id)
        .where(
            ActivityLog.tenant_id == tenant_id,
            ActivityLog.target_type == "lead",
            ActivityLog.action == "lead.stage_changed",
            ActivityLog.payload["to_stage"].as_string() == "lost",
            Lead.tenant_id == tenant_id,
        )
    )
    if own_company_id:
        stmt = stmt.where(Lead.own_company_id == own_company_id)
    for pred in _conversion_funnel_slice_predicates(tenant_id=tenant_id, sp=slice_params):
        stmt = stmt.where(pred)
    stmt = stmt.group_by(from_stage_txt).order_by(cnt.desc())
    rows = (await db.execute(stmt)).all()
    return [
        LeadConversionFunnelLostFromStage(from_stage=str(fs or "unknown"), lead_count=int(n or 0))
        for fs, n in rows
    ]


async def _lost_reason_code_breakdown(
    db: AsyncSession,
    *,
    tenant_id: str,
    own_company_id: str | None,
    slice_params: ConversionFunnelSliceParams,
) -> list[LeadConversionFunnelLostReasonRow]:
    reason_txt = func.coalesce(
        func.nullif(ActivityLog.payload["lost_reason_code"].as_string(), ""),
        literal("unknown"),
    )
    cnt = func.count(func.distinct(Lead.id))
    stmt = (
        select(reason_txt.label("rc"), cnt)
        .select_from(ActivityLog)
        .join(Lead, Lead.id == ActivityLog.target_id)
        .where(
            ActivityLog.tenant_id == tenant_id,
            ActivityLog.target_type == "lead",
            ActivityLog.action == "lead.stage_changed",
            ActivityLog.payload["to_stage"].as_string() == "lost",
            Lead.tenant_id == tenant_id,
        )
    )
    if own_company_id:
        stmt = stmt.where(Lead.own_company_id == own_company_id)
    for pred in _conversion_funnel_slice_predicates(tenant_id=tenant_id, sp=slice_params):
        stmt = stmt.where(pred)
    stmt = stmt.group_by(reason_txt).order_by(cnt.desc())
    rows = (await db.execute(stmt)).all()
    return [
        LeadConversionFunnelLostReasonRow(reason_code=str(rc or "unknown"), lead_count=int(n or 0))
        for rc, n in rows
    ]
LEAD_CRM_STAGES_FOR_HEALTH: tuple[str, ...] = ("new", "contacted", "qualified", "converted", "lost")

_DWELL_LOG_CHUNK = 800


@dataclass(frozen=True)
class ConversionFunnelSliceParams:
    """Optional TEAM-tier filters for conversion funnel counts + dwell (§2.12)."""

    source: Optional[str] = None
    vacancy_id: Optional[str] = None
    funnel_id: Optional[str] = None
    assignee_user_id: Optional[str] = None
    cohort_created_at_min: Optional[datetime] = None
    cohort_created_at_max_exclusive: Optional[datetime] = None

    @staticmethod
    def normalize(
        *,
        source: Optional[str] = None,
        vacancy_id: Optional[str] = None,
        funnel_id: Optional[str] = None,
        assignee_user_id: Optional[str] = None,
        cohort_created_at_min: Optional[datetime] = None,
        cohort_created_at_max_exclusive: Optional[datetime] = None,
    ) -> "ConversionFunnelSliceParams":
        def _s(v: Optional[str]) -> Optional[str]:
            if v is None:
                return None
            t = str(v).strip()
            return t or None

        return ConversionFunnelSliceParams(
            source=_s(source),
            vacancy_id=_s(vacancy_id),
            funnel_id=_s(funnel_id),
            assignee_user_id=_s(assignee_user_id),
            cohort_created_at_min=cohort_created_at_min,
            cohort_created_at_max_exclusive=cohort_created_at_max_exclusive,
        )

    def any_set(self) -> bool:
        return bool(
            self.source
            or self.vacancy_id
            or self.funnel_id
            or self.assignee_user_id
            or self.cohort_created_at_min is not None
            or self.cohort_created_at_max_exclusive is not None
        )

    def cohort_active(self) -> bool:
        return self.cohort_created_at_min is not None and self.cohort_created_at_max_exclusive is not None


def _conversion_funnel_slice_predicates(*, tenant_id: str, sp: ConversionFunnelSliceParams) -> List[Any]:
    extra: List[Any] = []
    if sp.source:
        extra.append(func.lower(Lead.source) == str(sp.source).lower())
    if sp.vacancy_id:
        extra.append(Lead.vacancy_id == sp.vacancy_id)
    if sp.funnel_id:
        extra.append(Lead.funnel_id == sp.funnel_id)
    if sp.assignee_user_id:
        extra.append(
            exists()
            .where(
                Candidate.id == Lead.candidate_id,
                Candidate.recruiter_id == sp.assignee_user_id,
                Candidate.tenant_id == tenant_id,
                Candidate.deleted_at.is_(None),
            )
            .correlate(Lead)
        )
    if sp.cohort_created_at_min is not None:
        extra.append(Lead.created_at >= sp.cohort_created_at_min)
    if sp.cohort_created_at_max_exclusive is not None:
        extra.append(Lead.created_at < sp.cohort_created_at_max_exclusive)
    return extra


async def _count_leads_for_conversion_funnel(
    db: AsyncSession,
    *,
    tenant_id: str,
    own_company_id: str | None,
    status: Optional[str],
    stage: Optional[str],
    slice_params: ConversionFunnelSliceParams,
) -> int:
    filters, stuck_subq, stuck_join, _n = await _build_lead_list_filters(
        db,
        tenant_id=tenant_id,
        own_company_id=own_company_id,
        status=status,
        stage=stage,
        next_action=None,
    )
    filters.extend(_conversion_funnel_slice_predicates(tenant_id=tenant_id, sp=slice_params))
    total_stmt = select(func.count()).select_from(Lead)
    if stuck_subq is not None and stuck_join is not None:
        total_stmt = total_stmt.outerjoin(stuck_subq, stuck_join)
    total_stmt = total_stmt.where(*filters)
    return int((await db.execute(total_stmt)).scalar_one() or 0)


async def _count_leads_for_conversion_root(
    db: AsyncSession,
    *,
    tenant_id: str,
    own_company_id: str | None,
    root: str,
    slice_params: ConversionFunnelSliceParams,
) -> int:
    filters, stuck_subq, stuck_join, _n = await _build_lead_list_filters(
        db,
        tenant_id=tenant_id,
        own_company_id=own_company_id,
        status="processed",
        stage=None,
        next_action=None,
    )
    filters.extend(_conversion_funnel_slice_predicates(tenant_id=tenant_id, sp=slice_params))
    filters.append(func.lower(func.coalesce(Lead.stage, "")) != "lost")
    filters.append(_sql_effective_lead_conversion_root() == root)
    total_stmt = select(func.count()).select_from(Lead)
    if stuck_subq is not None and stuck_join is not None:
        total_stmt = total_stmt.outerjoin(stuck_subq, stuck_join)
    total_stmt = total_stmt.where(*filters)
    return int((await db.execute(total_stmt)).scalar_one() or 0)


def _percentile_sorted(sorted_vals: List[float], p: float) -> float:
    if not sorted_vals:
        return 0.0
    if p <= 0:
        return float(sorted_vals[0])
    if p >= 1:
        return float(sorted_vals[-1])
    idx = int(round((len(sorted_vals) - 1) * p))
    idx = max(0, min(len(sorted_vals) - 1, idx))
    return float(sorted_vals[idx])


def _as_utc(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _dwell_avg_p50(days: List[float]) -> tuple[Optional[float], Optional[float], int]:
    if not days:
        return None, None, 0
    s = sorted(days)
    n = len(s)
    avg = round(float(sum(s)) / float(n), 2)
    p50 = round(_percentile_sorted(s, 0.5), 2)
    return avg, p50, n


async def _lead_conversion_funnel_dwell_by_stage(
    db: AsyncSession,
    *,
    tenant_id: str,
    own_company_id: str | None,
    stages: tuple[str, ...],
    slice_params: ConversionFunnelSliceParams,
) -> dict[str, tuple[Optional[float], Optional[float], int]]:
    """
    Per CRM stage: avg/median days since entering that stage (last ActivityLog lead.stage_changed with
    payload.to_stage == current stage), else Lead.created_at. Only processed leads in `stages`.
    """
    if not stages:
        return {}
    filt: List[Any] = [
        Lead.tenant_id == tenant_id,
        Lead.status == "processed",
        Lead.stage.in_(stages),
    ]
    if own_company_id:
        filt.append(Lead.own_company_id == own_company_id)
    filt.extend(_conversion_funnel_slice_predicates(tenant_id=tenant_id, sp=slice_params))
    lead_rows = (await db.execute(select(Lead.id, Lead.stage, Lead.created_at).where(*filt))).all()
    if not lead_rows:
        return {s: (None, None, 0) for s in stages}

    lead_stage_created: dict[str, tuple[str, datetime]] = {}
    for lid, st, cat in lead_rows:
        sid = str(lid)
        stage_code = str(st or "").strip() or "new"
        lead_stage_created[sid] = (stage_code, cat)

    ids = list(lead_stage_created.keys())
    by_lead_logs: dict[str, List[Tuple[datetime, str]]] = defaultdict(list)
    for i in range(0, len(ids), _DWELL_LOG_CHUNK):
        chunk = ids[i : i + _DWELL_LOG_CHUNK]
        log_stmt = (
            select(ActivityLog.target_id, ActivityLog.created_at, ActivityLog.payload)
            .where(
                ActivityLog.tenant_id == tenant_id,
                ActivityLog.target_type == "lead",
                ActivityLog.action == "lead.stage_changed",
                ActivityLog.target_id.in_(chunk),
            )
            .order_by(ActivityLog.created_at.asc())
        )
        for tid, cat, payload in (await db.execute(log_stmt)).all():
            pl = payload if isinstance(payload, dict) else {}
            to_st = str(pl.get("to_stage") or "").strip()
            if not to_st:
                continue
            by_lead_logs[str(tid)].append((_as_utc(cat) or cat, to_st))

    now = datetime.now(timezone.utc)
    by_stage_days: dict[str, List[float]] = defaultdict(list)

    for lid, (st, created_at) in lead_stage_created.items():
        entered: Optional[datetime] = None
        for at, to_st in by_lead_logs.get(lid, []):
            if to_st == st:
                if entered is None or at > entered:
                    entered = at
        base = _as_utc(created_at)
        ref = entered if entered is not None else base
        if ref is None:
            continue
        days = max(0.0, (now - ref).total_seconds() / 86400.0)
        by_stage_days[st].append(days)

    out: dict[str, tuple[Optional[float], Optional[float], int]] = {}
    for s in stages:
        avg, p50, n = _dwell_avg_p50(by_stage_days.get(s, []))
        out[s] = (avg, p50, n)
    return out


async def _load_lead_funnel_root_lookup(
    db: AsyncSession, *, tenant_id: str
) -> tuple[set[tuple[str, str]], dict[tuple[str, str], str]]:
    stmt = (
        select(FunnelStage.funnel_id, FunnelStage.code, FunnelStage.conversion_root_v1)
        .join(Funnel, Funnel.id == FunnelStage.funnel_id)
        .where(Funnel.type == "lead", Funnel.tenant_id.in_([tenant_id, "default"]))
    )
    existing: set[tuple[str, str]] = set()
    override: dict[tuple[str, str], str] = {}
    for fid, code, root in (await db.execute(stmt)).all():
        key = (str(fid), str(code or "").strip().lower())
        existing.add(key)
        if root:
            r = str(root).strip().lower()
            if r in CONVERSION_ROOTS_SET:
                override[key] = r
    return existing, override


def _python_effective_conversion_root(
    funnel_id: Optional[str],
    stage: Optional[str],
    existing: set[tuple[str, str]],
    override: dict[tuple[str, str], str],
) -> Optional[str]:
    st = (stage or "").strip().lower() or "new"
    fid = (funnel_id or "").strip()
    if fid:
        key = (fid, st)
        if key in override:
            return override[key]
        if key in existing:
            return _LEAD_LEGACY_STAGE_TO_ROOT.get(st)
    return _LEAD_LEGACY_STAGE_TO_ROOT.get(st)


async def _lead_conversion_funnel_dwell_by_root(
    db: AsyncSession,
    *,
    tenant_id: str,
    own_company_id: str | None,
    roots: tuple[str, ...],
    slice_params: ConversionFunnelSliceParams,
) -> dict[str, tuple[Optional[float], Optional[float], int]]:
    """Dwell aggregated by §2.12 conversion root (time in current CRM stage, bucketed by mapped root)."""
    if not roots:
        return {}
    existing, override = await _load_lead_funnel_root_lookup(db, tenant_id=tenant_id)
    filt: List[Any] = [
        Lead.tenant_id == tenant_id,
        Lead.status == "processed",
        func.lower(func.coalesce(Lead.stage, "")) != "lost",
    ]
    if own_company_id:
        filt.append(Lead.own_company_id == own_company_id)
    filt.extend(_conversion_funnel_slice_predicates(tenant_id=tenant_id, sp=slice_params))
    lead_rows = (
        await db.execute(select(Lead.id, Lead.stage, Lead.funnel_id, Lead.created_at).where(*filt))
    ).all()
    if not lead_rows:
        return {r: (None, None, 0) for r in roots}

    lead_stage_created: dict[str, tuple[str, str, Optional[str], datetime]] = {}
    for lid, st, fid, cat in lead_rows:
        sid = str(lid)
        stage_code = str(st or "").strip() or "new"
        fid_s = str(fid).strip() if fid else ""
        root = _python_effective_conversion_root(fid_s or None, stage_code, existing, override)
        if root not in roots:
            continue
        lead_stage_created[sid] = (stage_code, fid_s, root, cat)

    ids = list(lead_stage_created.keys())
    if not ids:
        return {r: (None, None, 0) for r in roots}

    by_lead_logs: dict[str, List[Tuple[datetime, str]]] = defaultdict(list)
    for i in range(0, len(ids), _DWELL_LOG_CHUNK):
        chunk = ids[i : i + _DWELL_LOG_CHUNK]
        log_stmt = (
            select(ActivityLog.target_id, ActivityLog.created_at, ActivityLog.payload)
            .where(
                ActivityLog.tenant_id == tenant_id,
                ActivityLog.target_type == "lead",
                ActivityLog.action == "lead.stage_changed",
                ActivityLog.target_id.in_(chunk),
            )
            .order_by(ActivityLog.created_at.asc())
        )
        for tid, cat, payload in (await db.execute(log_stmt)).all():
            pl = payload if isinstance(payload, dict) else {}
            to_st = str(pl.get("to_stage") or "").strip()
            if not to_st:
                continue
            by_lead_logs[str(tid)].append((_as_utc(cat) or cat, to_st))

    now = datetime.now(timezone.utc)
    by_root_days: dict[str, List[float]] = defaultdict(list)

    for lid, (st, _fid, _root, created_at) in lead_stage_created.items():
        entered: Optional[datetime] = None
        for at, to_st in by_lead_logs.get(lid, []):
            if to_st == st:
                if entered is None or at > entered:
                    entered = at
        base = _as_utc(created_at)
        ref = entered if entered is not None else base
        if ref is None:
            continue
        days = max(0.0, (now - ref).total_seconds() / 86400.0)
        by_root_days[_root].append(days)

    out: dict[str, tuple[Optional[float], Optional[float], int]] = {}
    for r in roots:
        avg, p50, n = _dwell_avg_p50(by_root_days.get(r, []))
        out[r] = (avg, p50, n)
    return out


async def _compute_lead_conversion_funnel(
    db: AsyncSession,
    *,
    tenant_id: str,
    own_company_id: str | None,
    sp: ConversionFunnelSliceParams,
) -> LeadConversionFunnelResponse:
    """Core conversion funnel snapshot for one slice + optional cohort (§2.12)."""
    win = CONVERSION_ROOT_ORDER
    counts: dict[str, int] = {}
    for s in win:
        counts[s] = await _count_leads_for_conversion_root(
            db,
            tenant_id=tenant_id,
            own_company_id=own_company_id,
            root=s,
            slice_params=sp,
        )
    lost_processed = await _count_leads_for_conversion_funnel(
        db,
        tenant_id=tenant_id,
        own_company_id=own_company_id,
        status="processed",
        stage="lost",
        slice_params=sp,
    )
    status_new = await _count_leads_for_conversion_funnel(
        db,
        tenant_id=tenant_id,
        own_company_id=own_company_id,
        status="new",
        stage=None,
        slice_params=sp,
    )
    total_win = int(sum(counts[s] for s in win))
    dwell_map = await _lead_conversion_funnel_dwell_by_root(
        db,
        tenant_id=tenant_id,
        own_company_id=own_company_id,
        roots=win,
        slice_params=sp,
    )
    dwell_lost = await _lead_conversion_funnel_dwell_by_stage(
        db,
        tenant_id=tenant_id,
        own_company_id=own_company_id,
        stages=("lost",),
        slice_params=sp,
    )
    steps: list[LeadConversionFunnelStage] = []
    for i, s in enumerate(win):
        at_or_beyond = int(sum(counts[x] for x in win[i:]))
        da, dp, dn = dwell_map.get(s, (None, None, 0))
        steps.append(
            LeadConversionFunnelStage(
                stage=s,
                count=counts[s],
                at_or_beyond=at_or_beyond,
                dwell_avg_days=da,
                dwell_p50_days=dp,
                dwell_sample_size=dn,
            )
        )
    edges: list[LeadConversionFunnelEdge] = []
    for i in range(len(win) - 1):
        den = steps[i].at_or_beyond
        num = steps[i + 1].at_or_beyond
        share = round(float(num) / float(den), 4) if den else None
        edges.append(
            LeadConversionFunnelEdge(from_stage=win[i], to_stage=win[i + 1], progressed_share=share)
        )
    l_avg, l_p50, l_n = dwell_lost.get("lost", (None, None, 0))
    lost_from = await _lost_from_stage_breakdown(
        db, tenant_id=tenant_id, own_company_id=own_company_id, slice_params=sp
    )
    lost_reason_rows = await _lost_reason_code_breakdown(
        db, tenant_id=tenant_id, own_company_id=own_company_id, slice_params=sp
    )
    return LeadConversionFunnelResponse(
        generated_at=datetime.now(timezone.utc),
        own_company_id=own_company_id,
        filter_source=sp.source,
        filter_vacancy_id=sp.vacancy_id,
        filter_funnel_id=sp.funnel_id,
        filter_assignee_user_id=sp.assignee_user_id,
        status_new_count=status_new,
        lost_processed_count=lost_processed,
        lost_dwell_avg_days=l_avg,
        lost_dwell_p50_days=l_p50,
        lost_dwell_sample_size=l_n,
        total_win_path_processed=total_win,
        lost_from_stage=lost_from,
        lost_reason_breakdown=lost_reason_rows,
        stages=steps,
        edges=edges,
    )


async def lead_conversion_funnel_snapshot(
    db: AsyncSession,
    *,
    tenant_id: str,
    own_company_id: str | None = None,
    slice_params: ConversionFunnelSliceParams | None = None,
    cohort_compare_prior: bool = False,
) -> LeadConversionFunnelResponse:
    """
    Snapshot counts by §2.12 conversion root (funnel_stages.conversion_root_v1 + legacy CRM mapping),
    plus progression shares between adjacent roots. Optional cohort on Lead.created_at + prior window compare.
    """
    sp = slice_params or ConversionFunnelSliceParams()
    main = await _compute_lead_conversion_funnel(db, tenant_id=tenant_id, own_company_id=own_company_id, sp=sp)
    cmin = sp.cohort_created_at_min
    cmax = sp.cohort_created_at_max_exclusive
    if cohort_compare_prior:
        if cmin is None or cmax is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="cohort_compare_prior requires an active cohort window (cohort_window_days or cohort bounds)",
            )
        span = cmax - cmin
        if span.total_seconds() <= 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="cohort window must have positive duration",
            )
        prior_sp = replace(
            sp,
            cohort_created_at_max_exclusive=cmin,
            cohort_created_at_min=cmin - span,
        )
        prior = await _compute_lead_conversion_funnel(
            db, tenant_id=tenant_id, own_company_id=own_company_id, sp=prior_sp
        )
        pcm = prior_sp.cohort_created_at_min
        pcx = prior_sp.cohort_created_at_max_exclusive
        if pcm is None or pcx is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="cohort prior window computation failed",
            )
        pw = LeadConversionFunnelCohortWindow(
            cohort_created_at_min=pcm,
            cohort_created_at_max_exclusive=pcx,
            total_win_path_processed=prior.total_win_path_processed,
            lost_processed_count=prior.lost_processed_count,
            status_new_count=prior.status_new_count,
            stages=prior.stages,
            edges=prior.edges,
        )
        return main.model_copy(
            update={
                "cohort_created_after": cmin,
                "cohort_created_before_exclusive": cmax,
                "cohort_prior_window": pw,
            }
        )
    if sp.cohort_active():
        return main.model_copy(
            update={
                "cohort_created_after": cmin,
                "cohort_created_before_exclusive": cmax,
            }
        )
    return main


async def lead_stage_health_snapshot(
    db: AsyncSession,
    *,
    tenant_id: str,
    own_company_id: str | None = None,
) -> LeadStageHealthResponse:
    """
    Per-stage counts for processed pipeline + next-action health (same semantics as GET /leads filters).
    Sequential queries (safe for one AsyncSession).
    """
    rows: list[LeadStageHealthRow] = []
    for s in LEAD_CRM_STAGES_FOR_HEALTH:
        proc_total = await count_leads(
            db,
            tenant_id=tenant_id,
            own_company_id=own_company_id,
            status="processed",
            stage=s,
        )
        nna = await count_leads(
            db,
            tenant_id=tenant_id,
            own_company_id=own_company_id,
            status="processed",
            stage=s,
            next_action="no_next_action",
        )
        ovd = await count_leads(
            db,
            tenant_id=tenant_id,
            own_company_id=own_company_id,
            status="processed",
            stage=s,
            next_action="overdue",
        )
        stk = await count_leads(
            db,
            tenant_id=tenant_id,
            own_company_id=own_company_id,
            stage=s,
            next_action="stuck",
        )
        rows.append(
            LeadStageHealthRow(
                stage=s,
                processed_total=proc_total,
                no_next_action=nna,
                overdue=ovd,
                stuck=stk,
            )
        )
    return LeadStageHealthResponse(
        generated_at=datetime.now(timezone.utc),
        own_company_id=own_company_id,
        stages=rows,
    )
