"""Lead listing / filtering / count queries.

Extracted from ``backend/app/modules/leads/service/__init__.py`` (Phase 1 #3
god-module split, step 3/N): text-search predicate, conversion-root SQL
helpers + constants, ``_build_lead_list_filters``, ``count_leads``, candidate
no-next-action / overdue counts, and the public ``list_leads`` endpoint.

Re-exported via ``service/__init__.py`` so external consumers (router,
tests) keep using the historical ``service.<name>`` access pattern.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any, List, Optional, Tuple
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import (
    Text,
    and_,
    case,
    cast,
    exists,
    func,
    literal,
    or_,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.constants.stages import PIPELINE_COMPLETED_STAGE_CODES
from backend.app.models import (
    ActivityLog,
    Candidate,
    Company,
    Lead,
    Reminder,
    Tenant,
    Vacancy,
)
from backend.app.models.custom_field import CustomFieldEntityType, CustomFieldValue
from backend.app.models.funnel import FunnelStage
from backend.app.models.reminder import ReminderStatus
from backend.app.modules.leads import lead_custom_fields
from backend.app.modules.leads.lead_candidate_doc_loader import (
    batch_candidate_document_status_sets,
    vacancy_extra_requires_candidate_documents_module,
)
from backend.app.modules.leads.lead_criteria_eval import evaluate_vacancy_for_lead
from backend.app.modules.leads.lead_stage_contract import batch_lead_stage_contracts
from backend.app.modules.leads.schemas import LeadListResponse, LeadOut

from ._helpers import _build_lead_outcome, _load_tenant_business_type


def _lead_list_text_search_or(q_norm: str) -> Any:
    """
    Case-insensitive substring match on payload/normalized JSON text, id, source, stage, status,
    lead_type, linked company name (align with global_search_v1._search_leads_slice).
    `q_norm` must be lowercased, len >= 2.
    """
    like = f"%{q_norm}%"
    text_norm = cast(Lead.normalized, Text)
    text_payload = cast(Lead.payload, Text)
    company_l = func.lower(func.coalesce(Company.name, ""))
    return or_(
        func.lower(text_norm).like(like),
        func.lower(text_payload).like(like),
        func.lower(Lead.id).like(like),
        func.lower(Lead.source).like(like),
        func.lower(func.coalesce(Lead.stage, "")).like(like),
        func.lower(func.coalesce(Lead.status, "")).like(like),
        func.lower(func.coalesce(Lead.lead_type, "")).like(like),
        company_l.like(like),
    )


# §2.12 conversion funnel: root buckets (funnel_stages.conversion_root_v1 + legacy CRM codes).
CONVERSION_ROOT_ORDER: tuple[str, ...] = ("lead", "qualified", "active", "final")
CONVERSION_ROOTS_SET = frozenset(CONVERSION_ROOT_ORDER)

_LEAD_LEGACY_STAGE_TO_ROOT = {
    "new": "lead",
    "contacted": "qualified",
    "qualified": "active",
    "converted": "final",
}


# Allowed exact values for GET /leads ?pipeline_error= (NBA drill-down for fit pipeline).
LEAD_LIST_PIPELINE_ERROR_WHITELIST: frozenset[str] = frozenset({"LEAD_FIT_NO_MATCH", "LEAD_FIT_NEEDS_INFO"})


def _sql_effective_lead_conversion_root() -> Any:
    mapped = (
        select(FunnelStage.conversion_root_v1)
        .where(
            FunnelStage.funnel_id == Lead.funnel_id,
            func.lower(FunnelStage.code) == func.lower(func.coalesce(Lead.stage, literal(""))),
        )
        .limit(1)
        .scalar_subquery()
    )
    lc = func.lower(func.coalesce(Lead.stage, literal("")))
    legacy = case(
        (lc == "new", literal("lead")),
        (lc == "contacted", literal("qualified")),
        (lc == "qualified", literal("active")),
        (lc == "converted", literal("final")),
        else_=None,
    )
    return func.coalesce(mapped, legacy)


async def _build_lead_list_filters(
    db: AsyncSession,
    *,
    tenant_id: str,
    own_company_id: str | None,
    status: Optional[str],
    stage: Optional[str],
    next_action: Optional[str],
    custom_field_definition_id: Optional[str] = None,
    custom_field_match_value: Optional[str] = None,
    conversion_root: Optional[str] = None,
    lost_reason_code: Optional[str] = None,
    lost_from_crm_stage: Optional[str] = None,
    pipeline_error: Optional[str] = None,
    created_before_hours: Optional[int] = None,
) -> Tuple[List[Any], Any, Any, datetime]:
    filters: List[Any] = [Lead.tenant_id == tenant_id]
    if own_company_id:
        filters.append(Lead.own_company_id == own_company_id)
    lrc = (lost_reason_code or "").strip() or None
    lf_crm = (lost_from_crm_stage or "").strip().lower() or None
    lost_focus = bool(lrc or lf_crm)
    eff_status = "processed" if lost_focus else status
    eff_stage = "lost" if lost_focus else stage
    eff_cr = None if lost_focus else conversion_root
    if eff_status:
        filters.append(Lead.status == eff_status)
    if eff_stage:
        filters.append(Lead.stage == eff_stage)
    if eff_cr:
        cr = str(eff_cr).strip().lower()
        if cr not in CONVERSION_ROOTS_SET:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="conversion_root must be one of: lead, qualified, active, final",
            )
        filters.append(_sql_effective_lead_conversion_root() == cr)
    active_statuses = (ReminderStatus.pending, ReminderStatus.new, ReminderStatus.overdue)
    now = datetime.now(timezone.utc)
    stuck_stage_subq = None
    stuck_stage_join_on = None

    if created_before_hours is not None:
        try:
            hrs = max(1, int(created_before_hours))
        except Exception:
            hrs = 1
        filters.append(Lead.created_at < (now - timedelta(hours=hrs)))

    if next_action:
        normalized = str(next_action or "").strip().lower()
        # Converted leads are completed operationally; keep them out of lead
        # next-action queues/filters to avoid duplicate noise with candidates.
        filters.append(Lead.candidate_id.is_(None))
        reminder_exists_active = (
            exists()
            .where(
                Reminder.tenant_id == tenant_id,
                Reminder.entity_type == "lead",
                Reminder.entity_id == Lead.id,
                Reminder.status.in_(active_statuses),
            )
            .correlate(Lead)
        )
        reminder_exists_overdue = (
            exists()
            .where(
                Reminder.tenant_id == tenant_id,
                Reminder.entity_type == "lead",
                Reminder.entity_id == Lead.id,
                Reminder.status.in_(active_statuses),
                or_(Reminder.status == ReminderStatus.overdue, Reminder.due_at < now),
            )
            .correlate(Lead)
        )
        if normalized in {"no_next_action", "none"}:
            filters.append(~reminder_exists_active)
        elif normalized in {"overdue"}:
            filters.append(reminder_exists_overdue)
        elif normalized in {"scheduled", "has_next_action"}:
            filters.append(reminder_exists_active)
        elif normalized in {"stuck", "stuck_stage"}:
            tenant_row = (await db.execute(select(Tenant.settings).where(Tenant.id == tenant_id).limit(1))).first()
            settings_payload = tenant_row[0] if tenant_row else {}
            settings_dict = settings_payload if isinstance(settings_payload, dict) else {}
            sla_cfg = settings_dict.get("leads_next_action_sla_v1") if isinstance(settings_dict, dict) else None
            sla_cfg = sla_cfg if isinstance(sla_cfg, dict) else {}
            try:
                stuck_days = max(1, int(sla_cfg.get("stuckAfterDays") or 7))
            except Exception:
                stuck_days = 7
            stages_raw = sla_cfg.get("stages")
            if isinstance(stages_raw, list):
                active_stages = {str(x).strip() for x in stages_raw if str(x or "").strip()}
            else:
                active_stages = {"new", "contacted", "qualified"}
            cutoff = now - timedelta(days=int(stuck_days))

            last_change_subq = (
                select(
                    ActivityLog.target_id.label("lead_id"),
                    func.max(ActivityLog.created_at).label("last_changed_at"),
                )
                .where(
                    ActivityLog.tenant_id == tenant_id,
                    ActivityLog.target_type == "lead",
                    ActivityLog.action == "lead.stage_changed",
                )
                .group_by(ActivityLog.target_id)
                .subquery()
            )
            stuck_stage_subq = last_change_subq
            stuck_stage_join_on = last_change_subq.c.lead_id == Lead.id
            last_changed_at = func.coalesce(last_change_subq.c.last_changed_at, Lead.created_at)
            filters.append(Lead.status == "processed")
            # Global stuck bucket: only CRM stages configured for SLA tracking.
            # When `stage` is already pinned (e.g. per-stage health / ?stage=x&next_action=stuck), respect that stage.
            if not stage:
                filters.append(func.coalesce(Lead.stage, "new").in_(sorted(active_stages)))
            filters.append(last_changed_at <= cutoff)

    if lrc:
        lr_code_expr = Lead.normalized["lead_lost_reason_v1"]["code"].as_string()
        filters.append(lr_code_expr == lrc)

    if lf_crm:
        fs_log = ActivityLog.payload["from_stage"].as_string()
        to_lost = ActivityLog.payload["to_stage"].as_string() == "lost"
        if lf_crm == "unknown":
            prior_bucket = func.coalesce(func.nullif(fs_log, ""), literal("unknown")) == "unknown"
        else:
            prior_bucket = fs_log == lf_crm
        lost_from_exists = (
            exists()
            .where(
                ActivityLog.tenant_id == tenant_id,
                ActivityLog.target_type == "lead",
                ActivityLog.target_id == Lead.id,
                ActivityLog.action == "lead.stage_changed",
                to_lost,
                prior_bucket,
            )
            .correlate(Lead)
        )
        filters.append(lost_from_exists)

    if custom_field_definition_id and custom_field_match_value is not None:
        did = str(custom_field_definition_id).strip()
        if did:
            # Stored shape from custom field API / ingest: {"v": <scalar>}; v1 compares string form from query.
            cf_exists = (
                exists()
                .where(
                    CustomFieldValue.tenant_id == tenant_id,
                    CustomFieldValue.entity_type == CustomFieldEntityType.LEAD,
                    CustomFieldValue.definition_id == did,
                    CustomFieldValue.entity_id == Lead.id,
                    CustomFieldValue.value == {"v": custom_field_match_value},
                )
                .correlate(Lead)
            )
            filters.append(cf_exists)

    pe = (pipeline_error or "").strip() or None
    if pe:
        if pe not in LEAD_LIST_PIPELINE_ERROR_WHITELIST:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="pipeline_error must be one of: LEAD_FIT_NO_MATCH, LEAD_FIT_NEEDS_INFO",
            )
        filters.append(Lead.error == pe)

    return filters, stuck_stage_subq, stuck_stage_join_on, now


async def count_leads(
    db: AsyncSession,
    *,
    tenant_id: str,
    own_company_id: str | None = None,
    status: Optional[str] = None,
    stage: Optional[str] = None,
    next_action: Optional[str] = None,
    custom_field_definition_id: Optional[str] = None,
    custom_field_match_value: Optional[str] = None,
    conversion_root: Optional[str] = None,
    pipeline_error: Optional[str] = None,
) -> int:
    filters, stuck_stage_subq, stuck_stage_join_on, _now = await _build_lead_list_filters(
        db,
        tenant_id=tenant_id,
        own_company_id=own_company_id,
        status=status,
        stage=stage,
        next_action=next_action,
        custom_field_definition_id=custom_field_definition_id,
        custom_field_match_value=custom_field_match_value,
        conversion_root=conversion_root,
        lost_reason_code=None,
        lost_from_crm_stage=None,
        pipeline_error=pipeline_error,
    )
    total_stmt = select(func.count()).select_from(Lead)
    if stuck_stage_subq is not None and stuck_stage_join_on is not None:
        total_stmt = total_stmt.outerjoin(stuck_stage_subq, stuck_stage_join_on)
    total_stmt = total_stmt.where(*filters)
    return int((await db.execute(total_stmt)).scalar_one() or 0)



async def count_candidates_no_next_action_for_assignee(
    db: AsyncSession,
    *,
    tenant_id: str,
    assignee_id: str,
    own_company_id: str | None = None,
) -> int:
    """Same contract as GET /candidates/no-next-action (assignee-scoped)."""
    active_statuses = (ReminderStatus.pending, ReminderStatus.new, ReminderStatus.overdue)
    reminder_exists = (
        exists()
        .where(
            Reminder.tenant_id == tenant_id,
            Reminder.entity_type == "candidate",
            Reminder.entity_id == Candidate.id,
            Reminder.assignee_id == assignee_id,
            Reminder.status.in_(active_statuses),
        )
        .correlate(Candidate)
    )
    active_stage = or_(
        Candidate.stage.is_(None),
        Candidate.stage.notin_(tuple(PIPELINE_COMPLETED_STAGE_CODES)),
    )
    where = [
        Candidate.tenant_id == tenant_id,
        Candidate.deleted_at.is_(None),
        active_stage,
        ~reminder_exists,
    ]
    if own_company_id:
        where.append(Candidate.own_company_id == own_company_id)
    row = await db.execute(select(func.count()).select_from(Candidate).where(*where))
    return int(row.scalar_one() or 0)


async def count_candidate_overdue_reminders_for_assignee(
    db: AsyncSession,
    *,
    tenant_id: str,
    assignee_id: str,
    own_company_id: str | None = None,
) -> int:
    """Active candidate reminders for assignee that are overdue (status or due_at)."""
    now = datetime.now(timezone.utc)
    active_statuses = (ReminderStatus.pending, ReminderStatus.new, ReminderStatus.overdue)
    stmt = (
        select(func.count())
        .select_from(Reminder)
        .join(
            Candidate,
            and_(
                Reminder.entity_type == "candidate",
                Reminder.entity_id == Candidate.id,
            ),
        )
        .where(
            Reminder.tenant_id == tenant_id,
            Candidate.tenant_id == tenant_id,
            Candidate.deleted_at.is_(None),
            or_(
                Candidate.stage.is_(None),
                Candidate.stage.notin_(tuple(PIPELINE_COMPLETED_STAGE_CODES)),
            ),
            Reminder.assignee_id == assignee_id,
            Reminder.status.in_(active_statuses),
            or_(Reminder.status == ReminderStatus.overdue, Reminder.due_at < now),
        )
    )
    if own_company_id:
        stmt = stmt.where(Candidate.own_company_id == own_company_id)
    return int((await db.execute(stmt)).scalar_one() or 0)



async def list_leads(
    db: AsyncSession,
    *,
    tenant_id: str,
    own_company_id: str | None = None,
    status: Optional[str] = None,
    stage: Optional[str] = None,
    next_action: Optional[str] = None,
    custom_field_definition_id: Optional[str] = None,
    custom_field_match_value: Optional[str] = None,
    conversion_root: Optional[str] = None,
    lost_reason_code: Optional[str] = None,
    lost_from_crm_stage: Optional[str] = None,
    pipeline_error: Optional[str] = None,
    created_before_hours: Optional[int] = None,
    search: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    only_lead_id: Optional[str] = None,
) -> LeadListResponse:
    business_type = await _load_tenant_business_type(db, tenant_id, own_company_id)
    if only_lead_id:
        oid = str(only_lead_id or "").strip()
        filters = [Lead.tenant_id == tenant_id, Lead.id == oid]
        if own_company_id:
            filters.append(Lead.own_company_id == own_company_id)
        stuck_stage_subq = None
        stuck_stage_join_on = None
        now = datetime.now(timezone.utc)
        limit = 1
        offset = 0
        text_search_or = None
    else:
        filters, stuck_stage_subq, stuck_stage_join_on, now = await _build_lead_list_filters(
            db,
            tenant_id=tenant_id,
            own_company_id=own_company_id,
            status=status,
            stage=stage,
            next_action=next_action,
            custom_field_definition_id=custom_field_definition_id,
            custom_field_match_value=custom_field_match_value,
            conversion_root=conversion_root,
            lost_reason_code=lost_reason_code,
            lost_from_crm_stage=lost_from_crm_stage,
            pipeline_error=pipeline_error,
            created_before_hours=created_before_hours,
        )
        sq = (search or "").strip().lower()
        text_search_or = _lead_list_text_search_or(sq) if len(sq) >= 2 else None
        if text_search_or is not None:
            filters = [*filters, text_search_or]
    active_statuses = (ReminderStatus.pending, ReminderStatus.new, ReminderStatus.overdue)

    total_stmt = select(func.count()).select_from(Lead)
    if stuck_stage_subq is not None and stuck_stage_join_on is not None:
        total_stmt = total_stmt.outerjoin(stuck_stage_subq, stuck_stage_join_on)
    if only_lead_id is None and text_search_or is not None:
        total_stmt = total_stmt.outerjoin(Company, Company.id == Lead.company_id)
    total_stmt = total_stmt.where(*filters)
    total = (await db.execute(total_stmt)).scalar_one()

    vacancy_scope_join = and_(
        Vacancy.id == Lead.vacancy_id,
        or_(Vacancy.own_company_id.is_(None), Vacancy.own_company_id == Lead.own_company_id),
    )
    stmt = select(
        Lead,
        Company.name.label("company_name"),
        Vacancy.title.label("vacancy_title"),
        Vacancy.extra.label("vacancy_extra"),
        Candidate.first_name.label("candidate_first"),
        Candidate.last_name.label("candidate_last"),
        Candidate.id.label("candidate_id"),
        Candidate.recruiter_id.label("candidate_recruiter"),
    ).select_from(Lead)
    if stuck_stage_subq is not None and stuck_stage_join_on is not None:
        stmt = stmt.outerjoin(stuck_stage_subq, stuck_stage_join_on)
    stmt = (
        stmt.join(Company, Company.id == Lead.company_id, isouter=True)
        .join(Vacancy, vacancy_scope_join, isouter=True)
        .join(Candidate, Candidate.id == Lead.candidate_id, isouter=True)
        .where(*filters)
        .order_by(Lead.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    rows = await db.execute(stmt)
    raw_rows = rows.all()

    cand_ids_for_module_docs: set[str] = set()
    for row in raw_rows:
        _lead, _cn, _vt, vacancy_extra, _cf, _cl, cand_id, _cr = row
        if cand_id and vacancy_extra_requires_candidate_documents_module(vacancy_extra):
            cand_ids_for_module_docs.add(str(cand_id))
    doc_status_by_candidate: dict[str, dict[str, set[str]]] = {}
    if cand_ids_for_module_docs:
        doc_status_by_candidate = await batch_candidate_document_status_sets(
            db,
            tenant_id=tenant_id,
            candidate_ids=cand_ids_for_module_docs,
        )

    # Preload next action info in one query for current page items.
    # We compute:
    # - overdue_count: number of active reminders with due_at < now OR status overdue
    # - next_due_at/title/type: earliest due_at among active reminders
    lead_ids: list[str] = [str(lead.id) for lead, *_ in raw_rows]
    next_action_map: dict[str, dict[str, Any]] = {}
    if lead_ids:
        due_col = Reminder.due_at
        overdue_case = case(
            (
                or_(Reminder.status == ReminderStatus.overdue, due_col < now),
                1,
            ),
            else_=0,
        )
        agg_stmt = (
            select(
                Reminder.entity_id.label("lead_id"),
                func.min(due_col).label("next_due_at"),
                func.sum(overdue_case).label("overdue_count"),
            )
            .where(
                Reminder.tenant_id == tenant_id,
                Reminder.entity_type == "lead",
                Reminder.entity_id.in_(lead_ids),
                Reminder.status.in_(active_statuses),
            )
            .group_by(Reminder.entity_id)
        )
        agg_rows = (await db.execute(agg_stmt)).all()
        by_lead = {str(lid): {"next_due_at": nd, "overdue_count": int(oc or 0)} for lid, nd, oc in agg_rows}

        # Fetch the earliest reminder per lead (title/type) via a subquery on min(due_at).
        min_due_subq = (
            select(
                Reminder.entity_id.label("lead_id"),
                func.min(Reminder.due_at).label("min_due_at"),
            )
            .where(
                Reminder.tenant_id == tenant_id,
                Reminder.entity_type == "lead",
                Reminder.entity_id.in_(lead_ids),
                Reminder.status.in_(active_statuses),
            )
            .group_by(Reminder.entity_id)
            .subquery()
        )
        details_stmt = (
            select(Reminder.entity_id, Reminder.title, Reminder.type, Reminder.due_at)
            .join(
                min_due_subq,
                and_(
                    Reminder.entity_id == min_due_subq.c.lead_id,
                    Reminder.due_at == min_due_subq.c.min_due_at,
                ),
            )
            .where(
                Reminder.tenant_id == tenant_id,
                Reminder.entity_type == "lead",
                Reminder.entity_id.in_(lead_ids),
                Reminder.status.in_(active_statuses),
            )
        )
        det_rows = (await db.execute(details_stmt)).all()
        for lid, title, rtype, due_at in det_rows:
            entry = by_lead.get(str(lid)) or {"next_due_at": due_at, "overdue_count": 0}
            entry["next_title"] = str(title or "") or None
            entry["next_type"] = str(rtype or "") or None
            next_action_map[str(lid)] = entry

    lead_objects = [row[0] for row in raw_rows]
    contract_by_lead = await batch_lead_stage_contracts(db, tenant_id=tenant_id, leads=lead_objects)
    lead_id_strs = [str(row[0].id) for row in raw_rows]
    custom_field_maps = await lead_custom_fields.batch_lead_custom_field_maps(
        db, tenant_id=tenant_id, lead_ids=lead_id_strs
    )

    def _uuid_or_none(value: Optional[str]) -> Optional[UUID]:
        if not value:
            return None
        try:
            return UUID(str(value))
        except ValueError:
            return None

    def _loads_extra(extra: Any) -> dict[str, Any]:
        if not extra:
            return {}
        if isinstance(extra, dict):
            return extra
        try:
            return json.loads(str(extra))
        except Exception:
            return {}

    items: List[LeadOut] = []
    for lead, company_name, vacancy_title, vacancy_extra, cand_first, cand_last, cand_id, cand_recruiter in raw_rows:
        candidate_name = None
        if cand_first or cand_last:
            candidate_name = f"{cand_first or ''} {cand_last or ''}".strip()
        elif cand_id:
            candidate_name = str(cand_id)
        outcome_entity_type, outcome_entity_id, outcome_entity_name = _build_lead_outcome(
            business_type=business_type,
            company_id=lead.company_id,
            company_name=company_name,
            candidate_id=cand_id,
            candidate_name=candidate_name,
        )

        doc_status_payload: Optional[dict[str, set[str]]] = None
        if vacancy_extra_requires_candidate_documents_module(vacancy_extra):
            if cand_id:
                doc_status_payload = doc_status_by_candidate.get(str(cand_id), {})
            else:
                doc_status_payload = None
        fit_status, fit_reasons = evaluate_vacancy_for_lead(
            lead.normalized,
            vacancy_extra,
            candidate_document_statuses=doc_status_payload,
        )
        items.append(
            LeadOut(
                id=_uuid_or_none(lead.id) or UUID(lead.id),
                tenant_id=_uuid_or_none(lead.tenant_id) or UUID(lead.tenant_id),
                business_type=business_type,
                lead_type=(getattr(lead, "lead_type", None) or "candidate"),  # type: ignore[arg-type]
                company_id=_uuid_or_none(lead.company_id),
                company_name=company_name,
                vacancy_id=_uuid_or_none(lead.vacancy_id),
                vacancy_title=vacancy_title,
                source=lead.source,
                ad_id=lead.ad_id,
                external_id=getattr(lead, "external_id", None),
                status=lead.status,  # type: ignore[arg-type]
                stage=getattr(lead, "stage", None),
                funnel_id=_uuid_or_none(lead.funnel_id),
                stage_contract=contract_by_lead.get(str(lead.id)),
                candidate_id=_uuid_or_none(cand_id),
                candidate_name=candidate_name,
                outcome_entity_type=outcome_entity_type,
                outcome_entity_id=_uuid_or_none(outcome_entity_id),
                outcome_entity_name=outcome_entity_name,
                service_order_id=_uuid_or_none((lead.normalized or {}).get("service_order_id") if isinstance(lead.normalized, dict) else None),
                recruiter_id=_uuid_or_none(cand_recruiter),
                error=lead.error,
                payload=lead.payload or {},
                normalized=lead.normalized,
                created_at=lead.created_at,
                last_routed_at=lead.last_routed_at,
                next_action_status=(
                    None
                    if cand_id
                    else "overdue"
                    if (next_action_map.get(str(lead.id)) or {}).get("overdue_count", 0) > 0
                    else "scheduled"
                    if (next_action_map.get(str(lead.id)) or {}).get("next_due_at") is not None
                    else "no_next_action"
                ),
                next_action_due_at=(next_action_map.get(str(lead.id)) or {}).get("next_due_at"),
                next_action_type=(next_action_map.get(str(lead.id)) or {}).get("next_type"),
                next_action_title=(next_action_map.get(str(lead.id)) or {}).get("next_title"),
                fit_status=fit_status,
                fit_reasons=fit_reasons,
                custom_fields=custom_field_maps.get(str(lead.id), {}),
            )
        )

    return LeadListResponse(items=items, total=int(total or 0), limit=limit, offset=offset)
