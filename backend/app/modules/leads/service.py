from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Awaitable, Callable, Dict, List, Optional
from uuid import UUID

from fastapi import HTTPException
import json

from sqlalchemy import case, func, or_, select, exists, and_
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.v1.candidates.service import create_candidate_full
from backend.app.models import Candidate, Company, Lead, OwnCompany, Tenant, User, Vacancy, ActivityLog
from backend.app.models.user import Role
from backend.app.modules.leads import crud, normalizer
from backend.app.modules.leads.schemas import LeadListResponse, LeadOut, MetaLeadResponse, LeadTimelineResponse, LeadTimelineEventOut
from backend.app.modules.leads import pipeline
from backend.app.services import events
from backend.app.services.events import EventAudience
from backend.app.services import reminder_tasks
from backend.app.services.automation_rules import run_rules as run_automation_rules
from backend.app.models import Reminder
from backend.app.models.reminder import ReminderStatus


@dataclass
class MetaLeadRetryOutcome:
    lead_id: str
    status_before: str
    status_after: str
    candidate_id: Optional[str]
    error_before: Optional[str]
    error_after: Optional[str]
    processed: bool
    message: Optional[str] = None


@dataclass
class MetaLeadResult:
    lead_id: str
    status: str
    vacancy_id: Optional[str]
    candidate_id: Optional[str]
    recruiter_id: Optional[str]
    business_type: Optional[str] = None
    outcome_entity_type: Optional[str] = None
    outcome_entity_id: Optional[str] = None
    outcome_entity_name: Optional[str] = None
    error: Optional[str] = None
    is_new: bool = False

    def to_schema(self) -> MetaLeadResponse:
        return MetaLeadResponse(
            lead_id=UUID(self.lead_id),
            status=self.status,  # type: ignore[arg-type]
            vacancy_id=UUID(self.vacancy_id) if self.vacancy_id else None,
            candidate_id=UUID(self.candidate_id) if self.candidate_id else None,
            recruiter_id=UUID(self.recruiter_id) if self.recruiter_id else None,
            business_type=self.business_type,
            outcome_entity_type=self.outcome_entity_type,
            outcome_entity_id=UUID(self.outcome_entity_id) if self.outcome_entity_id else None,
            outcome_entity_name=self.outcome_entity_name,
            error=self.error,
        )


def _normalize_business_type(raw_business_type: Any, tenant_type: Any) -> str:
    normalized = str(raw_business_type or "").strip().lower()
    if normalized in {"agency", "employer", "services"}:
        return normalized
    tenant_type_value = str(getattr(tenant_type, "value", tenant_type or "")).strip().lower()
    return "employer" if tenant_type_value == "company" else "agency"


async def _load_tenant_business_type(db: AsyncSession, tenant_id: str) -> str:
    row = (await db.execute(select(Tenant.settings, Tenant.type).where(Tenant.id == tenant_id).limit(1))).first()
    if not row:
        return "agency"
    settings_payload, tenant_type = row
    settings_dict = settings_payload if isinstance(settings_payload, dict) else {}
    return _normalize_business_type(settings_dict.get("business_type"), tenant_type)


def _build_lead_outcome(
    *,
    business_type: str,
    company_id: Optional[str],
    company_name: Optional[str],
    candidate_id: Optional[str],
    candidate_name: Optional[str],
) -> tuple[Optional[str], Optional[str], Optional[str]]:
    if business_type == "services":
        return ("company", company_id, company_name or company_id)
    if candidate_id:
        return ("candidate", candidate_id, candidate_name or candidate_id)
    return ("company", company_id, company_name or company_id)


async def _emit_lead_event(
    db: AsyncSession,
    *,
    tenant_id: str,
    lead: Lead,
    event_type: str,
    candidate_id: Optional[str] = None,
    recruiter_id: Optional[str] = None,
    roles: Optional[List[Role | str]] = None,
    user_ids: Optional[List[str]] = None,
    error: Optional[str] = None,
    business_type: Optional[str] = None,
    outcome_entity_type: Optional[str] = None,
    outcome_entity_id: Optional[str] = None,
    outcome_entity_name: Optional[str] = None,
) -> None:
    payload = {
        "lead_id": lead.id,
        "status": lead.status,
        "business_type": business_type,
        "company_id": lead.company_id,
        "vacancy_id": lead.vacancy_id,
        "candidate_id": candidate_id,
        "recruiter_id": recruiter_id,
        "outcome_entity_type": outcome_entity_type,
        "outcome_entity_id": outcome_entity_id,
        "outcome_entity_name": outcome_entity_name,
        "error": error,
    }
    audience = EventAudience(
        user_ids=[uid for uid in (user_ids or []) if uid],
        roles=roles,
    )
    await events.emit_event(
        db,
        tenant_id=tenant_id,
        event_type=event_type,
        payload=payload,
        entity_type="lead",
        entity_id=lead.id,
        audience=audience,
    )


async def _load_supervisor_id(
    db: AsyncSession,
    recruiter_id: Optional[str],
) -> Optional[str]:
    if not recruiter_id:
        return None
    row = await db.execute(select(User.supervisor_id).where(User.id == recruiter_id))
    value = row.scalar_one_or_none()
    return value if value else None


async def _pick_lead_assignee_id(
    db: AsyncSession,
    *,
    tenant_id: str,
    preferred_user_id: Optional[str] = None,
) -> Optional[str]:
    if preferred_user_id:
        return preferred_user_id
    row = await db.execute(
        select(User.id)
        .where(
            User.is_active.is_(True),
            or_(User.tenant_id == tenant_id, User.tenant_id.is_(None)),
            User.role.in_(["administrator", "supervisor", "manager", "admin", "owner"]),
        )
        .order_by(User.created_at.asc())
        .limit(1)
    )
    return row.scalar_one_or_none()


async def _create_lead_followup_reminder(
    db: AsyncSession,
    *,
    tenant_id: str,
    lead: Lead,
    assignee_id: str,
    title: str,
    payload: Dict[str, Any],
) -> None:
    try:
        await reminder_tasks.create_reminder(
            db,
            tenant_id=tenant_id,
            actor_id=assignee_id,
            payload={
                "title": title,
                "type": "custom",
                "entity_type": "lead",
                "entity_id": str(lead.id),
                "assignee_id": assignee_id,
                "priority": "normal",
                "channel": "internal",
                "due_at": datetime.now(timezone.utc) + timedelta(hours=1),
                "payload": payload,
            },
        )
    except Exception:
        # best-effort: lead processing must not fail due to reminder creation
        return


class LeadProcessingError(Exception):
    def __init__(self, status: str, message: str):
        self.status = status
        self.message = message
        super().__init__(message)


async def _validate_company_id(
    db: AsyncSession,
    tenant_id: str,
    company_id: Optional[str],
) -> Optional[str]:
    if not company_id:
        return None
    stmt = select(Company.id).where(
        Company.id == company_id,
        Company.tenant_id == tenant_id,
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def _load_settings(
    db: AsyncSession,
    tenant_id: str,
):
    entry = await crud.get_meta_settings(db, tenant_id=tenant_id)
    if entry:
        return entry
    return await crud.create_meta_settings(
        db,
        tenant_id=tenant_id,
        auto_create_enabled=True,
        mask_pii_in_logs=True,
    )


async def _validate_recruiter_id(
    db: AsyncSession,
    tenant_id: str,
    recruiter_id: Optional[str],
) -> Optional[str]:
    if not recruiter_id:
        return None
    stmt = select(User.id).where(
        User.id == recruiter_id,
        User.is_active.is_(True),
        or_(User.tenant_id == tenant_id, User.tenant_id.is_(None)),
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def _resolve_vacancy(
    db: AsyncSession,
    tenant_id: str,
    normalized: Dict[str, Any],
) -> Optional[Vacancy]:
    vacancy_id = normalized.get("vacancy_id")
    if vacancy_id:
        vacancy = await crud.resolve_vacancy_by_id(db, tenant_id, vacancy_id)
        if vacancy:
            return vacancy

    vacancy = await crud.resolve_vacancy_by_ad(db, tenant_id, normalized.get("ad_id"))
    if vacancy:
        return vacancy

    return None


async def list_leads(
    db: AsyncSession,
    *,
    tenant_id: str,
    own_company_id: str | None = None,
    status: Optional[str] = None,
    stage: Optional[str] = None,
    next_action: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> LeadListResponse:
    business_type = await _load_tenant_business_type(db, tenant_id)
    filters = [Lead.tenant_id == tenant_id]
    if own_company_id:
        filters.append(Lead.own_company_id == own_company_id)
    if status:
        filters.append(Lead.status == status)
    if stage:
        filters.append(Lead.stage == stage)
    active_statuses = (ReminderStatus.pending, ReminderStatus.new, ReminderStatus.overdue)
    now = datetime.now(timezone.utc)
    stuck_stage_subq = None
    stuck_stage_join_on = None

    # Next action filters (entity-level, not assignee-level)
    if next_action:
        normalized = str(next_action or "").strip().lower()
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
            # "Stuck" = processed lead in active stages with no stage change for D days.
            # Uses ActivityLog lead.stage_changed; falls back to Lead.created_at if no events.
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
            filters.append(func.coalesce(Lead.stage, "new").in_(sorted(active_stages)))
            filters.append(last_changed_at <= cutoff)

    total_stmt = select(func.count()).select_from(Lead)
    if stuck_stage_subq is not None and stuck_stage_join_on is not None:
        total_stmt = total_stmt.outerjoin(stuck_stage_subq, stuck_stage_join_on)
    total_stmt = total_stmt.where(*filters)
    total = (await db.execute(total_stmt)).scalar_one()

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
        .join(Vacancy, Vacancy.id == Lead.vacancy_id, isouter=True)
        .join(Candidate, Candidate.id == Lead.candidate_id, isouter=True)
        .where(*filters)
        .order_by(Lead.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    rows = await db.execute(stmt)
    raw_rows = rows.all()

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

    def _evaluate_fit(criteria: Any, normalized: Any) -> tuple[str, list[str]]:
        """
        MVP vacancy fit evaluator.

        criteria schema (lead_criteria_v1):
          - min_experience_eu_years: int
          - requires_fields: [string]            # normalized keys required to be present (truthy)
          - in_poland: bool                      # requires normalized.in_poland == True/False
          - requires_documents: [string]         # requires normalized.documents includes each code
        """
        if not isinstance(criteria, dict) or not criteria:
            return ("no_criteria", [])
        norm = normalized if isinstance(normalized, dict) else {}
        reasons: list[str] = []
        missing_info = False
        hard_fail = False

        min_years = criteria.get("min_experience_eu_years")
        if min_years is not None:
            try:
                min_years_i = int(min_years)
            except Exception:
                min_years_i = 0
            if min_years_i > 0:
                value = norm.get("experience_eu_years")
                if value is None:
                    missing_info = True
                    reasons.append("missing_experience_eu_years")
                else:
                    try:
                        years_i = int(value)
                    except Exception:
                        years_i = -1
                    if years_i < min_years_i:
                        reasons.append(f"experience_eu_years<{min_years_i}")
                        hard_fail = True

        req_fields = criteria.get("requires_fields")
        if isinstance(req_fields, list):
            for key in req_fields:
                k = str(key or "").strip()
                if not k:
                    continue
                if not norm.get(k):
                    missing_info = True
                    reasons.append(f"missing:{k}")

        in_poland_req = criteria.get("in_poland")
        if isinstance(in_poland_req, bool):
            value = norm.get("in_poland")
            if value is None:
                missing_info = True
                reasons.append("missing_in_poland")
            else:
                if bool(value) is not in_poland_req:
                    reasons.append(f"in_poland!={str(in_poland_req).lower()}")
                    hard_fail = True

        req_docs = criteria.get("requires_documents")
        if isinstance(req_docs, list):
            docs = norm.get("documents")
            docs_set = set()
            if isinstance(docs, list):
                docs_set = {str(x).strip().lower() for x in docs if str(x or "").strip()}
            for code in req_docs:
                c = str(code or "").strip().lower()
                if not c:
                    continue
                if not docs_set:
                    missing_info = True
                    reasons.append("missing_documents")
                    break
                if c not in docs_set:
                    reasons.append(f"missing_doc:{c}")
                    hard_fail = True

        if reasons:
            if hard_fail:
                return ("no_fit", reasons)
            if missing_info:
                return ("needs_info", reasons)
            return ("no_fit", reasons)
        return ("fit", [])

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

        extra_obj = _loads_extra(vacancy_extra)
        criteria = (extra_obj or {}).get("lead_criteria_v1")
        fit_status, fit_reasons = _evaluate_fit(criteria, lead.normalized)
        items.append(
            LeadOut(
                id=_uuid_or_none(lead.id) or UUID(lead.id),
                tenant_id=_uuid_or_none(lead.tenant_id) or UUID(lead.tenant_id),
                business_type=business_type,
                company_id=_uuid_or_none(lead.company_id) or UUID(lead.company_id),
                company_name=company_name,
                vacancy_id=_uuid_or_none(lead.vacancy_id),
                vacancy_title=vacancy_title,
                source=lead.source,
                ad_id=lead.ad_id,
                status=lead.status,  # type: ignore[arg-type]
                stage=getattr(lead, "stage", None),
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
                    "overdue"
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
            )
        )

    return LeadListResponse(items=items, total=int(total or 0), limit=limit, offset=offset)


async def get_lead_timeline(
    db: AsyncSession,
    *,
    tenant_id: str,
    lead_id: str,
    limit: int = 200,
) -> LeadTimelineResponse:
    # Ensure lead exists and belongs to tenant.
    lead_row = await db.execute(select(Lead).where(Lead.id == lead_id, Lead.tenant_id == tenant_id).limit(1))
    lead = lead_row.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    # ActivityLog events for this lead.
    log_rows = (
        await db.execute(
            select(ActivityLog.action, ActivityLog.created_at, ActivityLog.payload)
            .where(
                ActivityLog.tenant_id == tenant_id,
                ActivityLog.target_type == "lead",
                ActivityLog.target_id == lead_id,
            )
            .order_by(ActivityLog.created_at.desc())
            .limit(limit)
        )
    ).all()

    # Reminder events for this lead.
    rem_rows = (
        await db.execute(
            select(
                Reminder.id,
                Reminder.type,
                Reminder.status,
                Reminder.title,
                Reminder.description,
                Reminder.created_at,
                Reminder.due_at,
                Reminder.completed_at,
            )
            .where(
                Reminder.tenant_id == tenant_id,
                Reminder.entity_type == "lead",
                Reminder.entity_id == lead_id,
            )
            .order_by(Reminder.created_at.desc())
            .limit(limit)
        )
    ).all()

    events: list[LeadTimelineEventOut] = []

    for action, created_at, payload in log_rows:
        kind = "activity"
        source = "activity_log"
        title = str(action or "").strip() or "event"
        descr = None
        if action == "lead.stage_changed":
            kind = "stage_changed"
            from_stage = (payload or {}).get("from_stage") if isinstance(payload, dict) else None
            to_stage = (payload or {}).get("to_stage") if isinstance(payload, dict) else None
            descr = f"{from_stage or '—'} → {to_stage or '—'}"
        elif str(action or "").startswith("analytics.next_action."):
            kind = "next_action_warning"
        elif str(action or "").startswith("analytics.perf."):
            kind = "analytics"
        events.append(
            LeadTimelineEventOut(
                at=created_at,
                kind=kind,
                source=source,
                title=title,
                description=descr,
                payload=payload if isinstance(payload, dict) else {},
            )
        )

    for (
        rem_id,
        r_type,
        status,
        title,
        description,
        created_at,
        due_at,
        completed_at,
    ) in rem_rows:
        base_payload: Dict[str, Any] = {
            "reminder_id": rem_id,
            "type": r_type,
            "status": status,
            "due_at": due_at.isoformat() if isinstance(due_at, datetime) else None,
            "completed_at": completed_at.isoformat() if isinstance(completed_at, datetime) else None,
        }
        # Created event
        events.append(
            LeadTimelineEventOut(
                at=created_at,
                kind="reminder_created",
                source="reminder",
                title=title or "Reminder created",
                description=description,
                payload=base_payload,
            )
        )
        # Completed event (if any)
        if completed_at:
            events.append(
                LeadTimelineEventOut(
                    at=completed_at,
                    kind="reminder_completed",
                    source="reminder",
                    title=title or "Reminder completed",
                    description=description,
                    payload=base_payload,
                )
            )

    # Sort all events by time desc and trim.
    events.sort(key=lambda e: e.at, reverse=True)
    if len(events) > limit:
        events = events[:limit]

    return LeadTimelineResponse(items=events)


async def process_normalized_lead(
    db: AsyncSession,
    *,
    tenant_id: str,
    payload: Dict[str, Any],
    normalized: Dict[str, Any],
    source: str,
    external_id: Optional[str] = None,
    on_lead_created: Optional[Callable[[Lead], Awaitable[None]]] = None,
) -> MetaLeadResult:
    normalized = dict(normalized or {})
    business_type = await _load_tenant_business_type(db, tenant_id)
    settings_row = await _load_settings(db, tenant_id)
    fallback_company_hint = settings_row.default_company_id
    fallback_recruiter_hint = settings_row.fallback_recruiter_id
    auto_create_enabled = bool(settings_row.auto_create_enabled)

    normalized_external_id: Optional[str] = None
    if external_id is not None:
        text = str(external_id).strip()
        normalized_external_id = text or None

    existing_lead: Optional[Lead] = None
    if normalized_external_id:
        existing_lead = await crud.get_lead_by_external_id(
            db,
            tenant_id=tenant_id,
            source=source,
            external_id=normalized_external_id,
        )

    lead: Optional[Lead] = existing_lead
    created_new = False
    if lead:
        lead.payload = payload
        lead.normalized = normalized
        lead.ad_id = normalized.get("ad_id")
        if lead.status not in {"failed", "needs_routing"}:
            recruiter_id: Optional[str] = None
            candidate_id = lead.candidate_id
            if candidate_id:
                candidate = await db.get(Candidate, candidate_id)
                if candidate:
                    recruiter_id = getattr(candidate, "recruiter_id", None)
                    # Обновляем extra поля из normalized данных, если они есть
                    import json
                    extra = candidate._get_extra()
                    updated = False
                    
                    # Обновляем preferred_contact
                    preferred_contact = normalized.get("preferred_contact")
                    if isinstance(preferred_contact, str) and preferred_contact.strip():
                        if extra.get("preferred_contact") != preferred_contact.strip():
                            extra["preferred_contact"] = preferred_contact.strip()
                            updated = True
                    
                    # Обновляем in_poland
                    in_poland_value = normalized.get("in_poland")
                    if isinstance(in_poland_value, bool):
                        if extra.get("in_poland") != in_poland_value:
                            extra["in_poland"] = in_poland_value
                            updated = True
                    elif isinstance(in_poland_value, str):
                        lowered = in_poland_value.strip().lower()
                        if lowered in {"true", "yes", "1"}:
                            if extra.get("in_poland") is not True:
                                extra["in_poland"] = True
                                updated = True
                        elif lowered in {"false", "no", "0"}:
                            if extra.get("in_poland") is not False:
                                extra["in_poland"] = False
                                updated = True
                    
                    # Обновляем poland_stay_basis
                    poland_basis = normalized.get("poland_stay_basis")
                    if isinstance(poland_basis, str) and poland_basis.strip():
                        if extra.get("poland_stay_basis") != poland_basis.strip():
                            extra["poland_stay_basis"] = poland_basis.strip()
                            updated = True
                    
                    # Обновляем driving_experience_in_europe
                    driving_experience = normalized.get("driving_experience_in_europe")
                    if isinstance(driving_experience, str) and driving_experience.strip():
                        if extra.get("driving_experience_in_europe") != driving_experience.strip():
                            extra["driving_experience_in_europe"] = driving_experience.strip()
                            updated = True
                    
                    # Обновляем experience_eu_years (опыт по ЕС)
                    experience_eu_years = normalized.get("experience_eu_years")
                    if isinstance(experience_eu_years, int) and experience_eu_years >= 0:
                        if extra.get("experience_eu_years") != experience_eu_years:
                            extra["experience_eu_years"] = experience_eu_years
                            updated = True
                    
                    if updated:
                        candidate.extra = json.dumps(extra, ensure_ascii=False, separators=(",", ":"))
                        await db.flush()
            outcome_entity_type, outcome_entity_id, outcome_entity_name = _build_lead_outcome(
                business_type=business_type,
                company_id=lead.company_id,
                company_name=None,
                candidate_id=candidate_id,
                candidate_name=None,
            )
            
            return MetaLeadResult(
                lead_id=lead.id,
                status=lead.status,
                vacancy_id=lead.vacancy_id,
                candidate_id=candidate_id,
                recruiter_id=recruiter_id,
                business_type=business_type,
                outcome_entity_type=outcome_entity_type,
                outcome_entity_id=outcome_entity_id,
                outcome_entity_name=outcome_entity_name,
                error=lead.error,
                is_new=False,
            )

    vacancy = await _resolve_vacancy(db, tenant_id, normalized)

    resolved_company_id: Optional[str] = None
    if vacancy:
        resolved_company_id = vacancy.company_id
        normalized["resolved_vacancy_id"] = vacancy.id
    else:
        normalized["resolved_vacancy_id"] = None

    hinted_company_id = normalized.get("company_id")
    if hinted_company_id and not resolved_company_id:
        resolved_company_id = await _validate_company_id(db, tenant_id, hinted_company_id)

    company_name_hint = normalized.get("company_name_hint")
    company_hints: List[str] = []

    def _add_company_hint(value: Any) -> None:
        if not value:
            return
        text = str(value).strip()
        if not text:
            return
        if text not in company_hints:
            company_hints.append(text)

    _add_company_hint(company_name_hint)
    raw_company_hints = normalized.get("company_hints")
    if isinstance(raw_company_hints, list):
        for item in raw_company_hints:
            _add_company_hint(item)

    if not resolved_company_id and company_hints:
        for hint in company_hints:
            resolved = await crud.resolve_company_by_name(db, tenant_id, hint)
            if resolved:
                resolved_company_id = resolved
                break

    if not resolved_company_id:
        resolved_company_id = await _validate_company_id(db, tenant_id, fallback_company_hint)

    if not resolved_company_id:
        resolved_company_id = await crud.get_default_company_id(db, tenant_id)

    if not resolved_company_id:
        raise LeadProcessingError("needs_routing", "COMPANY_NOT_RESOLVED")

    normalized["resolved_company_id"] = resolved_company_id
    resolved_company_name = next((hint for hint in company_hints if hint), None)

    if lead is None:
        own_company_id = getattr(vacancy, "own_company_id", None) if vacancy else None
        if not own_company_id:
            row = await db.execute(
                select(OwnCompany.id)
                .where(OwnCompany.tenant_id == tenant_id, OwnCompany.is_archived.is_(False))
                .order_by(OwnCompany.created_at.asc())
                .limit(1)
            )
            own_company_id = row.scalar_one_or_none()
        if not own_company_id:
            raise LeadProcessingError("needs_routing", "OWN_COMPANY_REQUIRED")
        lead = await crud.create_lead(
            db,
            tenant_id=tenant_id,
            own_company_id=str(own_company_id),
            company_id=resolved_company_id,
            vacancy_id=vacancy.id if vacancy else None,
            payload=payload,
            normalized=normalized,
            ad_id=normalized.get("ad_id"),
            source=source,
            external_id=normalized_external_id,
        )
        created_new = True
        if on_lead_created is not None:
            try:
                await on_lead_created(lead)
            except Exception:  # pragma: no cover - best effort
                pass
    else:
        lead.company_id = resolved_company_id
        lead.vacancy_id = vacancy.id if vacancy else None
        if getattr(lead, "own_company_id", None) in (None, ""):
            lead.own_company_id = getattr(vacancy, "own_company_id", None) if vacancy else None
        lead.payload = payload
        lead.normalized = normalized
        lead.ad_id = normalized.get("ad_id")
        await db.flush()

    email = normalized.get("email")
    phone = normalized.get("phone")
    if not email and not phone:
        fields = normalized.get("raw_field_names") or []
        graph_error = normalized.get("graph_error")
        diagnostic_base = graph_error or "NO_CONTACTS"
        if fields:
            suffix = f"(fields={'/'.join(fields)})"
            diagnostic = f"{diagnostic_base} {suffix}"
        else:
            diagnostic = diagnostic_base
        await crud.update_lead(
            db,
            lead,
            status="failed",
            vacancy_id=lead.vacancy_id,
            normalized=normalized,
            error=diagnostic,
        )
        await _emit_lead_event(
            db,
            tenant_id=tenant_id,
            lead=lead,
            event_type="lead.failed",
            roles=[Role.administrator, Role.supervisor],
            business_type=business_type,
            outcome_entity_type="company",
            outcome_entity_id=resolved_company_id,
            outcome_entity_name=resolved_company_name,
            error=diagnostic,
        )
        await db.commit()
        return MetaLeadResult(
            lead_id=lead.id,
            status="failed",
            vacancy_id=lead.vacancy_id,
            candidate_id=None,
            recruiter_id=None,
            business_type=business_type,
            outcome_entity_type="company",
            outcome_entity_id=resolved_company_id,
            outcome_entity_name=resolved_company_name,
            error=diagnostic,
            is_new=created_new,
        )

    duplicate = await crud.find_duplicate_candidate(
        db,
        tenant_id=tenant_id,
        company_id=resolved_company_id,
        email=email,
        phone=phone,
    )
    if duplicate:
        await crud.update_lead(
            db,
            lead,
            status="duplicated",
            candidate_id=str(duplicate.id),
            vacancy_id=lead.vacancy_id or duplicate.vacancy_id,
            normalized=normalized,
            error=None,
        )
        await db.commit()
        return MetaLeadResult(
            lead_id=lead.id,
            status="duplicated",
            vacancy_id=lead.vacancy_id or duplicate.vacancy_id,
            candidate_id=str(duplicate.id),
            recruiter_id=getattr(duplicate, "recruiter_id", None),
            business_type=business_type,
            outcome_entity_type="company" if business_type == "services" else "candidate",
            outcome_entity_id=resolved_company_id if business_type == "services" else str(duplicate.id),
            outcome_entity_name=resolved_company_name if business_type == "services" else None,
            error=None,
            is_new=created_new,
        )

    if not auto_create_enabled:
        now_marker = datetime.now(timezone.utc)
        await crud.update_lead(
            db,
            lead,
            status="needs_routing",
            vacancy_id=lead.vacancy_id,
            normalized=normalized,
            error=None,
            last_routed_at=now_marker,
        )
        await _emit_lead_event(
            db,
            tenant_id=tenant_id,
            lead=lead,
            event_type="lead.needs_routing",
            roles=[Role.administrator, Role.supervisor],
            business_type=business_type,
            outcome_entity_type="company",
            outcome_entity_id=resolved_company_id,
            outcome_entity_name=resolved_company_name,
        )
        await db.commit()
        return MetaLeadResult(
            lead_id=lead.id,
            status="needs_routing",
            vacancy_id=lead.vacancy_id,
            candidate_id=None,
            recruiter_id=None,
            business_type=business_type,
            outcome_entity_type="company",
            outcome_entity_id=resolved_company_id,
            outcome_entity_name=resolved_company_name,
            error=None,
            is_new=created_new,
        )

    # --- Services mode semantics: lead = potential client (no candidate creation) ---
    # For services tenants, vacancy/candidate is not the default conversion path.
    # We still accept vacancy_id in payload for compatibility, but the outcome is company-centric.
    if business_type == "services":
        await crud.update_lead(
            db,
            lead,
            status="processed",
            candidate_id=None,
            vacancy_id=lead.vacancy_id,
            normalized=normalized,
            error=None,
        )
        await _emit_lead_event(
            db,
            tenant_id=tenant_id,
            lead=lead,
            event_type="lead.processed",
            roles=[Role.administrator, Role.supervisor],
            business_type=business_type,
            outcome_entity_type="company",
            outcome_entity_id=resolved_company_id,
            outcome_entity_name=resolved_company_name,
        )
        if created_new:
            await _emit_lead_event(
                db,
                tenant_id=tenant_id,
                lead=lead,
                event_type="lead.new.telegram",
                roles=[Role.administrator, Role.supervisor],
                business_type=business_type,
                outcome_entity_type="company",
                outcome_entity_id=resolved_company_id,
                outcome_entity_name=resolved_company_name,
            )
        # Minimal rules builder (R2.2): trigger lead.processed automation rules
        try:
            assignee_id = await _pick_lead_assignee_id(
                db,
                tenant_id=tenant_id,
                preferred_user_id=fallback_recruiter_hint,
            )
            await run_automation_rules(
                db,
                tenant_id=tenant_id,
                trigger="lead.processed",
                actor_id=assignee_id,
                context={
                    "entity_type": "lead",
                    "entity_id": lead.id,
                    "lead_id": lead.id,
                    "source": lead.source,
                    "status": "processed",
                    "business_type": business_type,
                    "company_id": resolved_company_id,
                    "vacancy_id": lead.vacancy_id,
                    "assignee_id": assignee_id,
                },
            )
            await db.commit()
        except Exception:
            await db.rollback()
        await db.commit()
        return MetaLeadResult(
            lead_id=lead.id,
            status="processed",
            vacancy_id=lead.vacancy_id,
            candidate_id=None,
            recruiter_id=None,
            business_type=business_type,
            outcome_entity_type="company",
            outcome_entity_id=resolved_company_id,
            outcome_entity_name=resolved_company_name,
            error=None,
            is_new=created_new,
        )

    if not vacancy:
        await crud.update_lead(
            db,
            lead,
            status="needs_routing",
            vacancy_id=None,
            normalized=normalized,
            error="VACANCY_NOT_RESOLVED",
            last_routed_at=datetime.now(timezone.utc),
        )
        await _emit_lead_event(
            db,
            tenant_id=tenant_id,
            lead=lead,
            event_type="lead.needs_routing",
            roles=[Role.administrator, Role.supervisor],
            business_type=business_type,
            outcome_entity_type="company",
            outcome_entity_id=resolved_company_id,
            outcome_entity_name=resolved_company_name,
            error="VACANCY_NOT_RESOLVED",
        )
        await db.commit()
        return MetaLeadResult(
            lead_id=lead.id,
            status="needs_routing",
            vacancy_id=None,
            candidate_id=None,
            recruiter_id=None,
            business_type=business_type,
            outcome_entity_type="company",
            outcome_entity_id=resolved_company_id,
            outcome_entity_name=resolved_company_name,
            error="VACANCY_NOT_RESOLVED",
            is_new=created_new,
        )

    first_name = normalized.get("first_name") or "Meta"
    last_name = normalized.get("last_name") or normalized.get("full_name") or "Lead"
    if not last_name.strip():
        last_name = "Lead"

    extra_fields: Dict[str, Any] = {}
    preferred_contact = normalized.get("preferred_contact")
    if isinstance(preferred_contact, str) and preferred_contact.strip():
        extra_fields["preferred_contact"] = preferred_contact.strip()
    in_poland_value = normalized.get("in_poland")
    if isinstance(in_poland_value, bool):
        extra_fields["in_poland"] = in_poland_value
    elif isinstance(in_poland_value, str):
        lowered = in_poland_value.strip().lower()
        if lowered in {"true", "yes", "1"}:
            extra_fields["in_poland"] = True
        elif lowered in {"false", "no", "0"}:
            extra_fields["in_poland"] = False
    poland_basis = normalized.get("poland_stay_basis")
    if isinstance(poland_basis, str) and poland_basis.strip():
        extra_fields["poland_stay_basis"] = poland_basis.strip()
    # Handle driving experience - save both raw string and normalized number
    driving_experience = normalized.get("driving_experience_in_europe")
    if isinstance(driving_experience, str) and driving_experience.strip():
        extra_fields["driving_experience_in_europe"] = driving_experience.strip()
    # Also save normalized number of years if available (опыт по ЕС)
    experience_eu_years = normalized.get("experience_eu_years")
    if isinstance(experience_eu_years, int) and experience_eu_years >= 0:
        extra_fields["experience_eu_years"] = experience_eu_years

    candidate_payload: Dict[str, Any] = {
        "first_name": first_name.strip() or "Meta",
        "last_name": last_name.strip() or "Lead",
        "email": email,
        "phone": phone,
        "phone_country_code": normalized.get("phone_country_code"),
        "company_id": resolved_company_id,
        "vacancy_id": vacancy.id,
        "contacts": {
            key: value
            for key, value in {
                "email": email,
                "phone": phone,
                "phone_country_code": normalized.get("phone_country_code"),
            }.items()
            if value
        },
        "source": source,
        "origin": {source: normalized},
    }
    if extra_fields:
        candidate_payload["extra"] = extra_fields

    try:
        candidate = await create_candidate_full(
            db=db,
            tenant_id=tenant_id,
            payload=candidate_payload,
            actor_id=None,
            acl=None,
        )
    except HTTPException as exc:
        await crud.update_lead(
            db,
            lead,
            status="failed",
            candidate_id=None,
            vacancy_id=lead.vacancy_id,
            normalized=normalized,
            error=str(exc.detail),
        )
        await db.commit()
        raise
    except Exception as exc:  # pragma: no cover - defensive
        await crud.update_lead(
            db,
            lead,
            status="failed",
            candidate_id=None,
            vacancy_id=lead.vacancy_id,
            normalized=normalized,
            error=str(exc),
        )
        await db.commit()
        raise

    recruiter_id = getattr(candidate, "recruiter_id", None)
    vacancy_recruiter_id = getattr(vacancy, "recruiter_id", None) if vacancy else None
    if not recruiter_id and vacancy_recruiter_id:
        candidate.recruiter_id = vacancy_recruiter_id
        recruiter_id = vacancy_recruiter_id
        await db.flush()
    if not recruiter_id:
        fallback_recruiter = await _validate_recruiter_id(db, tenant_id, fallback_recruiter_hint)
        if fallback_recruiter:
            candidate.recruiter_id = fallback_recruiter
            recruiter_id = fallback_recruiter
            await db.flush()
    await crud.update_lead(
        db,
        lead,
        status="processed",
        candidate_id=str(candidate.id),
        vacancy_id=candidate.vacancy_id,
        normalized=normalized,
        error=None,
    )
    supervisor_id = await _load_supervisor_id(db, recruiter_id)
    recipient_ids: List[str] = []
    if recruiter_id:
        recipient_ids.append(recruiter_id)
    if supervisor_id:
        recipient_ids.append(supervisor_id)
    assignee_id = await _pick_lead_assignee_id(
        db,
        tenant_id=tenant_id,
        preferred_user_id=recruiter_id or supervisor_id,
    )
    # Minimal rules builder (R2.2): trigger lead.processed automation rules (agency/employer path).
    try:
        await run_automation_rules(
            db,
            tenant_id=tenant_id,
            trigger="lead.processed",
            actor_id=assignee_id,
            context={
                "entity_type": "lead",
                "entity_id": lead.id,
                "lead_id": lead.id,
                "source": lead.source,
                "status": "processed",
                "business_type": business_type,
                "company_id": resolved_company_id,
                "vacancy_id": str(vacancy.id) if vacancy else None,
                "candidate_id": str(candidate.id),
                "recruiter_id": recruiter_id,
                "assignee_id": assignee_id,
            },
        )
        await db.commit()
    except Exception:
        await db.rollback()
    await _emit_lead_event(
        db,
        tenant_id=tenant_id,
        lead=lead,
        event_type="lead.processed",
        candidate_id=str(candidate.id),
        recruiter_id=recruiter_id,
        user_ids=recipient_ids,
        business_type=business_type,
        outcome_entity_type="company" if business_type == "services" else "candidate",
        outcome_entity_id=resolved_company_id if business_type == "services" else str(candidate.id),
        outcome_entity_name=resolved_company_name if business_type == "services" else None,
    )
    await db.commit()

    return MetaLeadResult(
        lead_id=lead.id,
        status="processed",
        vacancy_id=candidate.vacancy_id,
        candidate_id=str(candidate.id),
        recruiter_id=recruiter_id,
        business_type=business_type,
        outcome_entity_type="company" if business_type == "services" else "candidate",
        outcome_entity_id=resolved_company_id if business_type == "services" else str(candidate.id),
        outcome_entity_name=resolved_company_name if business_type == "services" else None,
        error=None,
        is_new=created_new,
    )


async def process_meta_lead(
    db: AsyncSession,
    *,
    tenant_id: str,
    payload: Dict[str, Any],
) -> MetaLeadResult:
    settings_row = await _load_settings(db, tenant_id)
    normalized = normalizer.normalize_meta_payload(
        payload,
        field_mapping=getattr(settings_row, "field_mapping", None),
    )
    raw_lead_id = normalized.get("raw_lead_id")
    external_id = str(raw_lead_id).strip() if raw_lead_id else None
    return await process_normalized_lead(
        db,
        tenant_id=tenant_id,
        payload=payload,
        normalized=normalized,
        source="meta",
        external_id=external_id,
    )


async def retry_meta_leads(
    db: AsyncSession,
    *,
    tenant_id: str,
    lead_ids: Optional[List[str]] = None,
    statuses: Optional[List[str]] = None,
    limit: Optional[int] = None,
    refresh_graph: bool = True,
) -> List[MetaLeadRetryOutcome]:
    settings_row = await _load_settings(db, tenant_id)
    min_hours = getattr(settings_row, "reroute_after_hours", None)
    now_marker = datetime.now(timezone.utc)
    targets = await crud.list_leads_for_retry(
        db,
        tenant_id=tenant_id,
        statuses=statuses,
        lead_ids=lead_ids,
        limit=limit,
    )
    if not targets:
        return []

    outcomes: List[MetaLeadRetryOutcome] = []
    import json

    existing_map = {
        lead.external_id: lead
        for lead in targets
        if getattr(lead, "external_id", None)
    }

    for lead in targets:
        if isinstance(min_hours, int) and min_hours > 0 and lead.last_routed_at:
            # Rate-limit retries to avoid thrashing integrations.
            delta = now_marker - (lead.last_routed_at if lead.last_routed_at.tzinfo else lead.last_routed_at.replace(tzinfo=timezone.utc))
            if delta.total_seconds() < min_hours * 3600:
                outcomes.append(
                    MetaLeadRetryOutcome(
                        lead_id=lead.id,
                        status_before=lead.status,
                        status_after=lead.status,
                        candidate_id=lead.candidate_id,
                        error_before=lead.error,
                        error_after=lead.error,
                        processed=False,
                        message=f"Retry skipped: reroute_after_hours={min_hours}",
                    )
                )
                continue
        status_before = lead.status
        error_before = lead.error
        payload_raw = lead.payload
        if not payload_raw:
            outcomes.append(
                MetaLeadRetryOutcome(
                    lead_id=lead.id,
                    status_before=status_before,
                    status_after=status_before,
                    candidate_id=lead.candidate_id,
                    error_before=error_before,
                    error_after=error_before,
                    processed=False,
                    message="Lead payload is empty",
                )
            )
            continue

        if isinstance(payload_raw, str):
            try:
                payload_dict = json.loads(payload_raw)
            except json.JSONDecodeError as exc:
                outcomes.append(
                    MetaLeadRetryOutcome(
                        lead_id=lead.id,
                        status_before=status_before,
                        status_after=status_before,
                        candidate_id=lead.candidate_id,
                        error_before=error_before,
                        error_after=error_before,
                        processed=False,
                        message=f"Stored payload decode error: {exc}",
                    )
                )
                continue
        else:
            payload_dict = dict(payload_raw)

        try:
            hydrated = await pipeline.hydrate_webhook_payload(
                db,
                tenant_id,
                payload_dict,
                existing_leads=existing_map,
                refresh_graph=refresh_graph,
            )
        except ValueError as exc:
            outcomes.append(
                MetaLeadRetryOutcome(
                    lead_id=lead.id,
                    status_before=status_before,
                    status_after=status_before,
                    candidate_id=lead.candidate_id,
                    error_before=error_before,
                    error_after=error_before,
                    processed=False,
                    message=str(exc),
                )
            )
            continue

        try:
            result = await process_meta_lead(
                db=db,
                tenant_id=tenant_id,
                payload=hydrated,
            )
            status_after = result.status
            candidate_id = result.candidate_id
            error_after = result.error
            processed_flag = status_after in {"processed", "duplicated"}
        except LeadProcessingError as exc:
            status_after = status_before
            candidate_id = lead.candidate_id
            error_after = error_before
            processed_flag = False
            outcomes.append(
                MetaLeadRetryOutcome(
                    lead_id=lead.id,
                    status_before=status_before,
                    status_after=status_after,
                    candidate_id=candidate_id,
                    error_before=error_before,
                    error_after=error_after,
                    processed=processed_flag,
                    message=exc.message,
                )
            )
            continue

        try:
            await db.refresh(lead)
            status_after = lead.status
            candidate_id = lead.candidate_id
            error_after = lead.error
        except Exception:
            pass

        outcomes.append(
            MetaLeadRetryOutcome(
                lead_id=lead.id,
                status_before=status_before,
                status_after=status_after,
                candidate_id=candidate_id,
                error_before=error_before,
                error_after=error_after,
                processed=processed_flag,
                message=None,
            )
        )

    return outcomes


async def reroute_lead_manual(
    db: AsyncSession,
    *,
    tenant_id: str,
    lead_id: str,
    vacancy_id: Optional[str],
    company_id: Optional[str],
    force_process: bool,
) -> MetaLeadResult:
    lead = await crud.get_lead(db, tenant_id=tenant_id, lead_id=lead_id)
    if not lead:
        raise LeadProcessingError("not_found", "LEAD_NOT_FOUND")

    settings_row = await _load_settings(db, tenant_id)
    fallback_recruiter_hint = settings_row.fallback_recruiter_id

    target_company_id = company_id or lead.company_id
    target_company_id = await _validate_company_id(db, tenant_id, target_company_id)
    if not target_company_id:
        raise LeadProcessingError("needs_routing", "COMPANY_NOT_RESOLVED")

    target_vacancy: Optional[Vacancy] = None
    vacancy_candidate = vacancy_id or lead.vacancy_id
    if vacancy_candidate:
        target_vacancy = await crud.resolve_vacancy_by_id(db, tenant_id, str(vacancy_candidate))

    normalized = dict(lead.normalized or {})
    normalized["company_id"] = target_company_id
    if target_vacancy:
        normalized["vacancy_id"] = str(target_vacancy.id)
        normalized["resolved_vacancy_id"] = target_vacancy.id
    else:
        normalized["resolved_vacancy_id"] = None

    lead.company_id = target_company_id
    lead.vacancy_id = str(target_vacancy.id) if target_vacancy else None
    lead.normalized = normalized

    email = normalized.get("email")
    phone = normalized.get("phone")
    now_marker = datetime.now(timezone.utc)

    if not email and not phone:
        fields = normalized.get("raw_field_names") or []
        diagnostic = "NO_CONTACTS"
        if fields:
            diagnostic = f"NO_CONTACTS (fields={'/'.join(fields)})"
        await crud.update_lead(
            db,
            lead,
            status="failed",
            candidate_id=None,
            vacancy_id=lead.vacancy_id,
            normalized=normalized,
            error=diagnostic,
            last_routed_at=now_marker,
        )
        await db.commit()
        return MetaLeadResult(
            lead_id=lead.id,
            status="failed",
            vacancy_id=lead.vacancy_id,
            candidate_id=None,
            recruiter_id=None,
            error=diagnostic,
        )

    if not target_vacancy and not force_process:
        await crud.update_lead(
            db,
            lead,
            status="needs_routing",
            vacancy_id=None,
            normalized=normalized,
            error="VACANCY_NOT_RESOLVED",
            last_routed_at=now_marker,
        )
        await db.commit()
        return MetaLeadResult(
            lead_id=lead.id,
            status="needs_routing",
            vacancy_id=None,
            candidate_id=None,
            recruiter_id=None,
            error="VACANCY_NOT_RESOLVED",
        )

    duplicate = await crud.find_duplicate_candidate(
        db,
        tenant_id=tenant_id,
        company_id=target_company_id,
        email=email,
        phone=phone,
    )
    if duplicate:
        await crud.update_lead(
            db,
            lead,
            status="duplicated",
            candidate_id=str(duplicate.id),
            vacancy_id=lead.vacancy_id or duplicate.vacancy_id,
            normalized=normalized,
            error=None,
            last_routed_at=now_marker,
        )
        await db.commit()
        return MetaLeadResult(
            lead_id=lead.id,
            status="duplicated",
            vacancy_id=lead.vacancy_id or duplicate.vacancy_id,
            candidate_id=str(duplicate.id),
            recruiter_id=getattr(duplicate, "recruiter_id", None),
            error=None,
        )

    if not force_process:
        await crud.update_lead(
            db,
            lead,
            status="needs_routing",
            vacancy_id=lead.vacancy_id,
            normalized=normalized,
            error=None,
            last_routed_at=now_marker,
        )
        await db.commit()
        return MetaLeadResult(
            lead_id=lead.id,
            status="needs_routing",
            vacancy_id=lead.vacancy_id,
            candidate_id=None,
            recruiter_id=None,
            error=None,
        )

    extra_fields: Dict[str, Any] = {}
    preferred_contact = normalized.get("preferred_contact")
    if isinstance(preferred_contact, str) and preferred_contact.strip():
        extra_fields["preferred_contact"] = preferred_contact.strip()
    in_poland_value = normalized.get("in_poland")
    if isinstance(in_poland_value, bool):
        extra_fields["in_poland"] = in_poland_value
    elif isinstance(in_poland_value, str):
        lowered = in_poland_value.strip().lower()
        if lowered in {"true", "yes", "1"}:
            extra_fields["in_poland"] = True
        elif lowered in {"false", "no", "0"}:
            extra_fields["in_poland"] = False
    poland_basis = normalized.get("poland_stay_basis")
    if isinstance(poland_basis, str) and poland_basis.strip():
        extra_fields["poland_stay_basis"] = poland_basis.strip()
    # Handle driving experience - save both raw string and normalized number
    driving_experience = normalized.get("driving_experience_in_europe")
    if isinstance(driving_experience, str) and driving_experience.strip():
        extra_fields["driving_experience_in_europe"] = driving_experience.strip()
    # Also save normalized number of years if available (опыт по ЕС)
    experience_eu_years = normalized.get("experience_eu_years")
    if isinstance(experience_eu_years, int) and experience_eu_years >= 0:
        extra_fields["experience_eu_years"] = experience_eu_years

    candidate_payload: Dict[str, Any] = {
        "first_name": (normalized.get("first_name") or "Meta").strip() or "Meta",
        "last_name": (normalized.get("last_name") or normalized.get("full_name") or "Lead").strip() or "Lead",
        "email": email,
        "phone": phone,
        "phone_country_code": normalized.get("phone_country_code"),
        "company_id": target_company_id,
        "vacancy_id": str(target_vacancy.id) if target_vacancy else None,
        "contacts": {
            key: value
            for key, value in {
                "email": email,
                "phone": phone,
                "phone_country_code": normalized.get("phone_country_code"),
            }.items()
            if value
        },
        "source": "meta",
        "origin": {
            "meta": normalized,
        },
    }
    if extra_fields:
        candidate_payload["extra"] = extra_fields

    try:
        candidate = await create_candidate_full(
            db=db,
            tenant_id=tenant_id,
            payload=candidate_payload,
            actor_id=None,
            acl=None,
        )
    except HTTPException as exc:
        await crud.update_lead(
            db,
            lead,
            status="failed",
            candidate_id=None,
            vacancy_id=lead.vacancy_id,
            normalized=normalized,
            error=str(exc.detail),
            last_routed_at=now_marker,
        )
        await db.commit()
        raise
    except Exception as exc:  # pragma: no cover
        await crud.update_lead(
            db,
            lead,
            status="failed",
            candidate_id=None,
            vacancy_id=lead.vacancy_id,
            normalized=normalized,
            error=str(exc),
            last_routed_at=now_marker,
        )
        await db.commit()
        raise

    recruiter_id = getattr(candidate, "recruiter_id", None)
    if not recruiter_id:
        fallback_recruiter = await _validate_recruiter_id(db, tenant_id, fallback_recruiter_hint)
        if fallback_recruiter:
            candidate.recruiter_id = fallback_recruiter
            recruiter_id = fallback_recruiter
            await db.flush()

    await crud.update_lead(
        db,
        lead,
        status="processed",
        candidate_id=str(candidate.id),
        vacancy_id=candidate.vacancy_id,
        normalized=normalized,
        error=None,
        last_routed_at=now_marker,
    )
    await db.commit()

    return MetaLeadResult(
        lead_id=lead.id,
        status="processed",
        vacancy_id=candidate.vacancy_id,
        candidate_id=str(candidate.id),
        recruiter_id=recruiter_id,
        error=None,
    )
