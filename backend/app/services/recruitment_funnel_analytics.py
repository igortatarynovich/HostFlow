"""Company-scoped recruitment funnel analytics (M5)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Literal, Optional

from fastapi import HTTPException
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.v1.tenants import service as tenant_service
from backend.app.api.v1.utils.access import resolve_restricted_acl
from backend.app.auth.deps import UserCtx
from backend.app.models.candidate import Candidate
from backend.app.models.lead import Lead
from backend.app.services import company_module_settings_service as cms_svc
from backend.app.services.company_module_access import company_allows_module
from backend.app.services.recruitment_funnel_metrics import record_recruitment_funnel_analytics
from backend.app.services.recruitment_funnel_resolver import (
    RECRUITMENT_MODULE_KEY,
    RecruitmentFunnelNotFoundError,
    RecruitmentFunnelResolveResult,
    RecruitmentPipelineType,
    resolve_legacy_tenant_recruitment_funnel,
    resolve_recruitment_funnel,
)

RecruitmentAnalyticsScope = Literal["recruitment_company", "legacy_tenant"]


@dataclass(frozen=True)
class RecruitmentFunnelAnalyticsResult:
    pipeline_type: RecruitmentPipelineType
    module_key: str
    company_id: Optional[str]
    funnel: Any
    resolve_result: RecruitmentFunnelResolveResult
    analytics_scope: RecruitmentAnalyticsScope
    stages: list[dict[str, Any]]
    excluded_unbound: int


def _normalize_stage_code(raw: Any) -> Optional[str]:
    if raw is None:
        return None
    text = str(raw.value if hasattr(raw, "value") else raw).strip()
    return text.lower() if text else None


def _funnel_stage_index(funnel: Any) -> dict[str, dict[str, Any]]:
    ordered = sorted(
        list(getattr(funnel, "stages", None) or []),
        key=lambda s: (int(getattr(s, "order", 0) or 0), str(getattr(s, "code", ""))),
    )
    out: dict[str, dict[str, Any]] = {}
    for stage in ordered:
        code = _normalize_stage_code(getattr(stage, "code", None))
        if not code or code in out:
            continue
        out[code] = {
            "code": code,
            "label": str(getattr(stage, "label", code) or code),
            "order": int(getattr(stage, "order", 0) or 0),
            "count": 0,
        }
    return out


async def _enforce_company_recruitment_gate(
    db: AsyncSession,
    *,
    tenant_id: str,
    company_id: str,
    current_user: UserCtx,
) -> None:
    company = await cms_svc.get_company_for_tenant(db, tenant_id, company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="Company not found")

    acl = await resolve_restricted_acl(db, tenant_id, current_user)
    if acl is not None and acl.company_ids and company_id not in acl.company_ids:
        raise HTTPException(status_code=403, detail="Forbidden")

    tenant = await tenant_service.get_tenant(db, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")

    if not company_allows_module(tenant, company, RECRUITMENT_MODULE_KEY):
        raise HTTPException(
            status_code=403,
            detail="Recruitment module is not enabled for this company",
        )


async def _resolve_analytics_funnel(
    db: AsyncSession,
    *,
    tenant_id: str,
    company_id: Optional[str],
    legacy_tenant: bool,
    pipeline_type: RecruitmentPipelineType,
    explicit_funnel_id: Optional[str],
) -> tuple[RecruitmentFunnelResolveResult, RecruitmentAnalyticsScope]:
    if company_id:
        try:
            result = await resolve_recruitment_funnel(
                db,
                tenant_id=tenant_id,
                company_id=company_id,
                pipeline_type=pipeline_type,
                explicit_funnel_id=explicit_funnel_id,
            )
        except RecruitmentFunnelNotFoundError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return result, "recruitment_company"

    if not legacy_tenant:
        raise HTTPException(
            status_code=422,
            detail="company_id is required unless legacy_tenant=true",
        )

    try:
        result = await resolve_legacy_tenant_recruitment_funnel(
            db,
            tenant_id=tenant_id,
            pipeline_type=pipeline_type,
        )
    except RecruitmentFunnelNotFoundError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return result, "legacy_tenant"


def _apply_candidate_period(
    stmt,
    *,
    date_from: Optional[datetime],
    date_to: Optional[datetime],
    by: str,
):
    col = Candidate.created_at if by == "created" else Candidate.updated_at
    if date_from:
        stmt = stmt.where(col >= date_from)
    if date_to:
        stmt = stmt.where(col <= date_to)
    return stmt


def _apply_lead_period(
    stmt,
    *,
    date_from: Optional[datetime],
    date_to: Optional[datetime],
    by: str,
):
    if by == "updated":
        col = func.coalesce(Lead.last_routed_at, Lead.created_at)
    else:
        col = Lead.created_at
    if date_from:
        stmt = stmt.where(col >= date_from)
    if date_to:
        stmt = stmt.where(col <= date_to)
    return stmt


async def build_recruitment_funnel_analytics(
    db: AsyncSession,
    *,
    tenant_id: str,
    current_user: UserCtx,
    company_id: Optional[str],
    legacy_tenant: bool,
    pipeline_type: RecruitmentPipelineType,
    module_key: str,
    explicit_funnel_id: Optional[str],
    scope_clause: Any,
    date_from: Optional[datetime],
    date_to: Optional[datetime],
    by: str,
    stage_visible: Optional[Callable[[str], bool]] = None,
) -> RecruitmentFunnelAnalyticsResult:
    if company_id and legacy_tenant:
        raise HTTPException(
            status_code=422,
            detail="company_id and legacy_tenant are mutually exclusive",
        )
    if legacy_tenant and explicit_funnel_id:
        raise HTTPException(
            status_code=422,
            detail="funnel_id override is not supported with legacy_tenant analytics",
        )

    module = str(module_key or RECRUITMENT_MODULE_KEY).strip() or RECRUITMENT_MODULE_KEY
    if module != RECRUITMENT_MODULE_KEY:
        raise HTTPException(
            status_code=422,
            detail=f"unsupported module_key for funnel analytics: {module}",
        )

    company_str = str(company_id or "").strip() or None
    if company_str:
        await _enforce_company_recruitment_gate(
            db, tenant_id=tenant_id, company_id=company_str, current_user=current_user
        )

    resolve_result, analytics_scope = await _resolve_analytics_funnel(
        db,
        tenant_id=tenant_id,
        company_id=company_str,
        legacy_tenant=legacy_tenant,
        pipeline_type=pipeline_type,
        explicit_funnel_id=explicit_funnel_id,
    )
    funnel = resolve_result.funnel
    stage_index = _funnel_stage_index(funnel)
    allowed_codes = set(stage_index.keys())

    record_recruitment_funnel_analytics(
        pipeline_type=pipeline_type,
        scope=analytics_scope,
    )

    excluded_unbound = 0

    if pipeline_type == "candidate":
        funnel_match = (
            Candidate.funnel_id == funnel.id
            if analytics_scope == "recruitment_company"
            else or_(Candidate.funnel_id == funnel.id, Candidate.funnel_id.is_(None))
        )
        base = (
            select(Candidate.stage, func.count())
            .select_from(Candidate)
            .where(
                and_(
                    Candidate.deleted_at.is_(None),
                    scope_clause,
                    funnel_match,
                )
            )
        )
        if company_str:
            base = base.where(Candidate.company_id == company_str)
        base = _apply_candidate_period(base, date_from=date_from, date_to=date_to, by=by)
        base = base.group_by(Candidate.stage)
        rows = (await db.execute(base)).all()

        if analytics_scope == "legacy_tenant":
            unbound_stmt = select(func.count()).select_from(Candidate).where(
                and_(
                    Candidate.deleted_at.is_(None),
                    scope_clause,
                    Candidate.funnel_id.isnot(None),
                    Candidate.funnel_id != funnel.id,
                )
            )
            unbound_stmt = _apply_candidate_period(
                unbound_stmt, date_from=date_from, date_to=date_to, by=by
            )
            excluded_unbound = int((await db.execute(unbound_stmt)).scalar_one() or 0)
    else:
        funnel_match = (
            Lead.funnel_id == funnel.id
            if analytics_scope == "recruitment_company"
            else or_(Lead.funnel_id == funnel.id, Lead.funnel_id.is_(None))
        )
        base = (
            select(Lead.stage, func.count())
            .select_from(Lead)
            .where(
                and_(
                    Lead.tenant_id == tenant_id,
                    funnel_match,
                )
            )
        )
        if company_str:
            base = base.where(Lead.company_id == company_str)
        base = _apply_lead_period(base, date_from=date_from, date_to=date_to, by=by)
        base = base.group_by(Lead.stage)
        rows = (await db.execute(base)).all()

        if analytics_scope == "legacy_tenant":
            unbound_stmt = select(func.count()).select_from(Lead).where(
                and_(
                    Lead.tenant_id == tenant_id,
                    Lead.funnel_id.isnot(None),
                    Lead.funnel_id != funnel.id,
                )
            )
            unbound_stmt = _apply_lead_period(
                unbound_stmt, date_from=date_from, date_to=date_to, by=by
            )
            excluded_unbound = int((await db.execute(unbound_stmt)).scalar_one() or 0)

    for raw_stage, cnt in rows:
        code = _normalize_stage_code(raw_stage)
        if not code or code not in allowed_codes:
            excluded_unbound += int(cnt or 0)
            continue
        if stage_visible and not stage_visible(code):
            continue
        stage_index[code]["count"] += int(cnt or 0)

    stages_out = [
        {
            "name": row["code"],
            "code": row["code"],
            "label": row["label"],
            "order": row["order"],
            "count": row["count"],
        }
        for row in sorted(stage_index.values(), key=lambda r: (r["order"], r["code"]))
    ]
    stages_out = [s for s in stages_out if s["count"] > 0]

    return RecruitmentFunnelAnalyticsResult(
        pipeline_type=pipeline_type,
        module_key=module,
        company_id=company_str,
        funnel=funnel,
        resolve_result=resolve_result,
        analytics_scope=analytics_scope,
        stages=stages_out,
        excluded_unbound=excluded_unbound,
    )
