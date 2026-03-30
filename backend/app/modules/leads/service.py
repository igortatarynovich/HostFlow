from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from typing import Any, Awaitable, Callable, Dict, List, Literal, Optional, Tuple
from uuid import UUID

from fastapi import HTTPException, status
import json

from sqlalchemy import Text, case, cast, func, literal, or_, select, exists, and_, inspect as sa_inspect
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.v1.candidates.service import create_candidate_full
from backend.app.constants.spa_paths import CANDIDATES_NO_NEXT_ACTION_PAGE, LEADS as SPA_LEADS, TASKS
from backend.app.constants.stages import PIPELINE_COMPLETED_STAGE_CODES
from backend.app.models import Candidate, Company, Lead, OwnCompany, Tenant, User, Vacancy, ActivityLog
from backend.app.models.funnel import Funnel, FunnelStage
from backend.app.models.custom_field import CustomFieldEntityType, CustomFieldValue
from backend.app.models.tenant import TenantLicense
from backend.app.models.user import Role
from backend.app.modules.leads import crud, lead_custom_fields, normalizer
from backend.app.modules.leads.recruiter_validation import validate_tenant_recruiter_id
from backend.app.modules.leads.lead_candidate_doc_loader import (
    batch_candidate_document_status_sets,
    vacancy_extra_requires_candidate_documents_module,
)
from backend.app.modules.leads.lead_criteria_eval import (
    evaluate_lead_criteria_v1,
    evaluate_vacancy_for_lead,
    ordered_vacancy_ids_from_tenant_settings,
)
from backend.app.modules.leads.lead_stage_contract import batch_lead_stage_contracts
from backend.app.modules.leads.schemas import (
    LeadConversionFunnelCohortWindow,
    LeadConversionFunnelEdge,
    LeadConversionFunnelLostFromStage,
    LeadConversionFunnelLostReasonRow,
    LeadConversionFunnelResponse,
    LeadConversionFunnelStage,
    LeadListResponse,
    LeadNextActionsResponse,
    LeadOut,
    LeadStageHealthResponse,
    LeadStageHealthRow,
    MetaLeadResponse,
    NextActionGroupOut,
    NextActionQueryParams,
    LeadTimelineResponse,
    LeadTimelineEventOut,
)
from backend.app.modules.leads import pipeline
from backend.app.services import events
from backend.app.services.events import EventAudience
from backend.app.services import reminder_tasks
from backend.app.services import billing_restrictions
from backend.app.services.automation_rules import run_rules as run_automation_rules
from backend.app.services.plan_feature_gates import (
    plan_allows_team_tier_features,
    plan_is_pro_tier,
    resolve_tenant_plan_code,
)
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


async def _load_tenant_business_type(db: AsyncSession, tenant_id: str, own_company_id: Optional[str] = None) -> str:
    # Source of truth should be the active OwnCompany business type (OwnCompany.extra),
    # so the whole scenario (agency/employer/services) follows the Topbar selection.
    #
    # Backward compatibility:
    # - if `own_company_id` is not provided or OwnCompany.extra does not contain business_type,
    #   we fall back to legacy operating profile (Company.extra) and then to Tenant.settings.
    operating_company_type: Optional[str] = None
    if own_company_id:
        try:
            row = await db.execute(
                select(OwnCompany.extra)
                .where(OwnCompany.tenant_id == tenant_id, OwnCompany.id == own_company_id, OwnCompany.is_archived.is_(False))
                .limit(1)
            )
            extra = row.scalar_one_or_none()
            if isinstance(extra, dict):
                ct = (
                    extra.get("business_type")
                    or extra.get("company_type")
                    or extra.get("company_kind")
                    or extra.get("kind")
                )
                if isinstance(ct, str) and ct.strip().lower() in {"agency", "employer", "services"}:
                    operating_company_type = ct.strip().lower()
        except Exception:
            operating_company_type = None

    # Legacy fallback: operating company type from Company.extra (company_role="operating").
    # tenant.settings/business_type may be stale after legacy migrations or incomplete updates,
    # which leads to wrong leads conversion (candidate vs service order).
    try:
        if operating_company_type is None:
            # We fetch a small window of companies and select the one marked as operating in `extra`.
            # (Avoids fragile JSON querying across DB dialects.)
            rows = await db.execute(
                select(Company.extra)
                .where(Company.tenant_id == tenant_id, Company.is_archived.is_(False))
                .order_by(Company.created_at.asc())
                .limit(50)
            )
            for (extra,) in rows.all():
                if not isinstance(extra, dict):
                    continue
                role = str(extra.get("company_role") or "").strip().lower()
                if role != "operating":
                    continue
                ct = extra.get("company_type") or extra.get("business_type") or extra.get("company_kind") or extra.get("kind")
                if isinstance(ct, str) and ct.strip().lower() in {"agency", "employer", "services"}:
                    operating_company_type = ct.strip().lower()
                    break
    except Exception:
        operating_company_type = None

    row = (await db.execute(select(Tenant.settings, Tenant.type).where(Tenant.id == tenant_id).limit(1))).first()
    if not row:
        return "agency"
    settings_payload, tenant_type = row
    settings_dict = settings_payload if isinstance(settings_payload, dict) else {}
    raw = operating_company_type if operating_company_type is not None else settings_dict.get("business_type")
    return _normalize_business_type(raw, tenant_type)


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
    normalized: Optional[Dict[str, Any]] = None,
    lead_id: Optional[str] = None,
) -> Optional[str]:
    """
    Actor for lead.processed automations and related side effects.

    Order:
    1) Automatic lead distribution (Tenant.settings.lead_distribution_v1, team/pro plan) when mode=automatic.
    2) preferred_user_id (vacancy recruiter, supervisor, meta fallback recruiter).
    3) Legacy: first active administrator/supervisor/manager on tenant.
    """
    from backend.app.services.lead_distribution import pick_assignee_user_id_for_ingest

    dist_id = await pick_assignee_user_id_for_ingest(
        db,
        tenant_id=tenant_id,
        normalized=normalized,
        lead_id=lead_id,
    )
    if dist_id:
        return dist_id
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


def lead_processing_error_as_http(exc: LeadProcessingError) -> HTTPException:
    if exc.status == "billing_blocked":
        if exc.message == "BILLING_TRIAL_EXPIRED":
            return HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "billing_trial_expired",
                    "message": "Your trial has ended. Choose a plan in Billing to create new leads.",
                },
            )
        return HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "billing_past_due",
                "message": "New leads are paused until subscription payment succeeds. Open Billing to retry payment.",
            },
        )
    return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.message)


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


def _normalize_stored_leads_processing_mode_v1(raw: Any) -> str:
    s = str(raw or "").strip().lower()
    if s in ("manual", "assisted", "automatic"):
        return s
    return "assisted"


async def _apply_leads_processing_mode_v1_to_normalized(
    db: AsyncSession,
    *,
    tenant_id: str,
    normalized: Dict[str, Any],
    settings_row: Any,
) -> Dict[str, Any]:
    """
    Stamp configured + effective qualification mode on lead.normalized (§2.10 / §2.3).
    Automatic without Team-tier plan is downgraded to manual for this ingest only.
    """
    stored = _normalize_stored_leads_processing_mode_v1(
        getattr(settings_row, "leads_processing_mode_v1", None)
    )
    effective = stored
    downgrade: Optional[str] = None
    if stored == "automatic":
        plan = await resolve_tenant_plan_code(db, tenant_id)
        if not plan_allows_team_tier_features(plan):
            effective = "manual"
            downgrade = "team_plan_required"
    normalized["leads_processing_mode_configured_v1"] = stored
    normalized["leads_processing_mode_v1"] = effective
    if downgrade:
        normalized["leads_processing_mode_downgrade_v1"] = downgrade
    else:
        normalized.pop("leads_processing_mode_downgrade_v1", None)
    return normalized


async def _validate_recruiter_id(
    db: AsyncSession,
    tenant_id: str,
    recruiter_id: Optional[str],
) -> Optional[str]:
    return await validate_tenant_recruiter_id(db, tenant_id, recruiter_id)


def _rule_recruiter_id_from_normalized(normalized: Dict[str, Any]) -> Optional[str]:
    raw = normalized.get("lead_qualification_rule_match_v1")
    if not isinstance(raw, dict):
        return None
    rid = raw.get("recruiter_id")
    if rid is None:
        return None
    s = str(rid).strip()
    return s or None


def _vacancy_allows_auto_convert_on_fit(vacancy: Optional[Vacancy]) -> bool:
    """Vacancy.extra.leads_auto_convert_on_fit_v1 == False opts out of tenant automatic conversion (§2.4)."""
    if vacancy is None:
        return True
    raw = getattr(vacancy, "extra", None)
    if raw is None:
        return True
    if isinstance(raw, str):
        try:
            obj = json.loads(raw)
        except Exception:
            return True
        if not isinstance(obj, dict):
            return True
        data = obj
    elif isinstance(raw, dict):
        data = raw
    else:
        return True
    if data.get("leads_auto_convert_on_fit_v1") is False:
        return False
    return True


async def _resolve_vacancy(
    db: AsyncSession,
    tenant_id: str,
    normalized: Dict[str, Any],
    *,
    own_company_id: Optional[str] = None,
) -> Optional[Vacancy]:
    vacancy_id = normalized.get("vacancy_id")
    if vacancy_id:
        vacancy = await crud.resolve_vacancy_by_id(
            db, tenant_id, vacancy_id, scoped_own_company_id=own_company_id
        )
        if vacancy:
            return vacancy

    vacancy = await crud.resolve_vacancy_by_ad(
        db, tenant_id, normalized.get("ad_id"), scoped_own_company_id=own_company_id
    )
    if vacancy:
        return vacancy

    return None


async def resolve_vacancy_for_lead_processing(
    db: AsyncSession,
    *,
    tenant_id: str,
    normalized: Dict[str, Any],
    tenant_settings: Dict[str, Any],
    source: str = "",
    own_company_id: Optional[str] = None,
) -> Tuple[Optional[Vacancy], Optional[str], List[str]]:
    """
    Single routing path for ingest (§2.10):
    1) Explicit vacancy_id / Meta ad map — always wins; fit is evaluated for that vacancy only.
    2) Else: AutomationRule trigger `lead.qualification` (priority desc) — set_vacancy_id + fit eval;
       optional actions.set_recruiter_id (active user of tenant) stamped on match and applied at convert.
    3) Else: Tenant.settings.lead_fit_routing_v1.ordered_vacancy_ids — first vacancy with
       fit or no_criteria (criteria from Vacancy.extra.lead_criteria_v1).
    """
    primary = await _resolve_vacancy(
        db, tenant_id, normalized, own_company_id=own_company_id
    )
    if primary is not None:
        st, rs = evaluate_vacancy_for_lead(normalized, primary.extra)
        return primary, st, rs
    from backend.app.modules.leads.lead_qualification_rules import pick_vacancy_via_qualification_rules

    picked = await pick_vacancy_via_qualification_rules(
        db,
        tenant_id=tenant_id,
        source=source,
        normalized=normalized,
        own_company_id=own_company_id,
    )
    if picked is not None:
        v, st, rs = picked
        return v, st, rs
    for vid in ordered_vacancy_ids_from_tenant_settings(tenant_settings):
        v = await crud.resolve_vacancy_by_id(
            db, tenant_id, vid, scoped_own_company_id=own_company_id
        )
        if v is None:
            continue
        st, rs = evaluate_vacancy_for_lead(normalized, v.extra)
        if st in ("fit", "no_criteria"):
            return v, st, rs
    return None, None, []


def _stamp_lead_qualification_preview_v1(
    normalized: Dict[str, Any],
    *,
    vacancy: Optional[Vacancy],
    fit_status: Optional[str],
    fit_reasons: List[str],
    blocked_auto_convert: bool = False,
) -> None:
    normalized["lead_qualification_preview_v1"] = {
        "suggested_vacancy_id": str(vacancy.id) if vacancy else None,
        "fit_status": fit_status,
        "fit_reasons": list(fit_reasons or []),
        "blocked_auto_convert": bool(blocked_auto_convert),
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
    }


async def _audit_lead_qualification_rule_match(
    db: AsyncSession,
    *,
    tenant_id: str,
    lead_id: str,
    normalized: Dict[str, Any],
) -> None:
    raw = normalized.get("lead_qualification_rule_match_v1")
    if not isinstance(raw, dict) or not raw.get("rule_id"):
        return
    from backend.app.services.audit import log_activity

    await log_activity(
        db,
        tenant_id=tenant_id,
        action="lead.qualification_rule_matched",
        target_type="lead",
        target_id=str(lead_id),
        payload={k: v for k, v in raw.items() if v is not None},
    )


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
            Reminder.assignee_id == assignee_id,
            Reminder.status.in_(active_statuses),
            or_(Reminder.status == ReminderStatus.overdue, Reminder.due_at < now),
        )
    )
    if own_company_id:
        stmt = stmt.where(Candidate.own_company_id == own_company_id)
    return int((await db.execute(stmt)).scalar_one() or 0)


def _nba_lead_locked_and_required(
    min_plan: Optional[str],
    *,
    plan: str,
    team_ok: bool,
) -> tuple[bool, Optional[str]]:
    """If bucket requires a higher plan, return (locked, required_plan code for UI)."""
    if not min_plan:
        return False, None
    mp = str(min_plan).strip().lower()
    if mp == "team":
        if team_ok:
            return False, None
        return True, "team"
    if mp == "pro":
        if plan_is_pro_tier(plan):
            return False, None
        return True, "pro"
    return False, None


NBA_FUNNEL_MIN_TOTAL_WIN = 5
NBA_FUNNEL_MIN_AT_OR_BEYOND = 6
NBA_FUNNEL_WEAK_SHARE_MAX = 0.49
NBA_FUNNEL_SLOW_DWELL_DAYS = 5.0
NBA_FUNNEL_MIN_DWELL_SAMPLE = 3


async def nba_conversion_funnel_insight_groups(
    db: AsyncSession,
    *,
    tenant_id: str,
    own_company_id: str | None,
    plan: str,
    team_ok: bool,
) -> List[NextActionGroupOut]:
    """
    Deterministic §2.12 funnel signals merged into GET /next-actions (bridge toward NBA).
    No extra HTTP round-trip on the dashboard.
    Same paywall as conversion-funnel slices: Team-tier unlocks actionable insight chips (§2.12).
    """
    funnel = await lead_conversion_funnel_snapshot(
        db,
        tenant_id=tenant_id,
        own_company_id=own_company_id,
        slice_params=ConversionFunnelSliceParams(),
    )
    if not funnel.stages:
        return []
    total_win = int(sum(int(s.count) for s in funnel.stages))
    if total_win < NBA_FUNNEL_MIN_TOTAL_WIN:
        return []
    insight_locked, insight_required_plan = _nba_lead_locked_and_required(
        "team", plan=plan, team_ok=team_ok
    )
    out: List[NextActionGroupOut] = []

    worst_idx: Optional[int] = None
    worst_share: Optional[float] = None
    for i, edge in enumerate(funnel.edges):
        if edge.progressed_share is None:
            continue
        at_here = int(funnel.stages[i].at_or_beyond)
        if at_here < NBA_FUNNEL_MIN_AT_OR_BEYOND:
            continue
        sh = float(edge.progressed_share)
        if worst_share is None or sh < worst_share:
            worst_share = sh
            worst_idx = i

    if worst_idx is not None and worst_share is not None and worst_share <= NBA_FUNNEL_WEAK_SHARE_MAX:
        from_root = str(funnel.stages[worst_idx].stage)
        at_top = int(funnel.stages[worst_idx].at_or_beyond)
        at_next = (
            int(funnel.stages[worst_idx + 1].at_or_beyond) if worst_idx + 1 < len(funnel.stages) else 0
        )
        drop = max(0, at_top - at_next)
        if drop > 0:
            pct = max(0, min(100, int(round(worst_share * 100))))
            out.append(
                NextActionGroupOut(
                    id="leads_funnel_weak_step",
                    entity="lead",
                    reason="funnel_weak_conversion_step",
                    title="Lead funnel: weak handoff between stages",
                    count=drop,
                    priority=17,
                    query=NextActionQueryParams(status="processed", conversion_root=from_root),
                    path=SPA_LEADS,
                    locked=insight_locked,
                    required_plan=insight_required_plan,
                    nba_detail={"conversion_root": from_root, "pct": pct},
                )
            )

    slow_stage: Optional[str] = None
    slow_days = 0.0
    slow_bucket_count = 0
    for s in funnel.stages:
        n = int(s.dwell_sample_size or 0)
        if n < NBA_FUNNEL_MIN_DWELL_SAMPLE:
            continue
        if s.dwell_avg_days is None:
            continue
        d = float(s.dwell_avg_days)
        if d >= NBA_FUNNEL_SLOW_DWELL_DAYS and d > slow_days:
            slow_days = d
            slow_stage = str(s.stage)
            slow_bucket_count = int(s.count)

    if slow_stage and slow_bucket_count > 0:
        out.append(
            NextActionGroupOut(
                id="leads_funnel_slow_stage",
                entity="lead",
                reason="funnel_slow_stage_dwell",
                title="Lead funnel: slow stage dwell",
                count=slow_bucket_count,
                priority=16,
                query=NextActionQueryParams(status="processed", conversion_root=slow_stage),
                path=SPA_LEADS,
                locked=insight_locked,
                required_plan=insight_required_plan,
                nba_detail={"conversion_root": slow_stage, "days": round(slow_days, 1)},
            )
        )

    return out


async def lead_next_actions_snapshot(
    db: AsyncSession,
    *,
    tenant_id: str,
    own_company_id: str | None = None,
    actor_user_id: str | None = None,
) -> LeadNextActionsResponse:
    """
    NBA: lead buckets (tenant / own_company) + assignee-scoped candidate buckets (§2.3).
    Plan gating: some lead buckets locked on solo/starter — counts still returned; sort: unlocked first.
    """
    plan = await resolve_tenant_plan_code(db, tenant_id)
    team_ok = plan_allows_team_tier_features(plan)
    nba_tier: Literal["solo", "team"] = "team" if team_ok else "solo"

    # (id, reason, title, priority, status, stage, next_action, min_plan)
    specs: List[tuple[str, str, str, int, Optional[str], Optional[str], Optional[str], Optional[str]]] = [
        (
            "leads_no_next_action",
            "no_next_action_on_processed",
            "Processed leads without a next action",
            30,
            "processed",
            None,
            "no_next_action",
            None,
        ),
        (
            "leads_next_overdue",
            "lead_reminder_overdue",
            "Leads with an overdue next action",
            25,
            "processed",
            None,
            "overdue",
            None,
        ),
        (
            "leads_stuck_in_stage",
            "lead_stuck_in_stage",
            "Leads stuck in stage (SLA)",
            20,
            None,
            None,
            "stuck",
            "team",
        ),
        (
            "leads_needs_routing",
            "needs_routing",
            "Leads waiting for routing",
            90,
            "needs_routing",
            None,
            None,
            None,
        ),
        (
            "leads_failed",
            "lead_failed",
            "Failed leads",
            80,
            "failed",
            None,
            None,
            None,
        ),
        (
            "leads_new_unprocessed",
            "lead_new_unprocessed",
            "New leads (not yet processed)",
            15,
            "new",
            None,
            None,
            None,
        ),
    ]
    groups: List[NextActionGroupOut] = []
    for gid, reason, title, priority, st, stg, na, min_plan in specs:
        cnt = await count_leads(
            db,
            tenant_id=tenant_id,
            own_company_id=own_company_id,
            status=st,
            stage=stg,
            next_action=na,
        )
        locked, req = _nba_lead_locked_and_required(min_plan, plan=plan, team_ok=team_ok)
        groups.append(
            NextActionGroupOut(
                id=gid,
                entity="lead",
                reason=reason,
                title=title,
                count=cnt,
                priority=priority,
                query=NextActionQueryParams(status=st, stage=stg, next_action=na),
                locked=locked,
                required_plan=req,
            )
        )

    # §2.10: NBA drill-down for Meta fit gate errors (exact Lead.error, needs_routing).
    for gid, reason, title, priority, pe in (
        ("leads_fit_no_match", "lead_fit_no_match", "Leads: no vacancy fit (pipeline)", 92, "LEAD_FIT_NO_MATCH"),
        ("leads_fit_needs_info", "lead_fit_needs_info", "Leads: need more info (pipeline)", 91, "LEAD_FIT_NEEDS_INFO"),
    ):
        cnt_fit = await count_leads(
            db,
            tenant_id=tenant_id,
            own_company_id=own_company_id,
            status="needs_routing",
            pipeline_error=pe,
        )
        locked_fit, req_fit = _nba_lead_locked_and_required(None, plan=plan, team_ok=team_ok)
        groups.append(
            NextActionGroupOut(
                id=gid,
                entity="lead",
                reason=reason,
                title=title,
                count=cnt_fit,
                priority=priority,
                query=NextActionQueryParams(status="needs_routing", pipeline_error=pe),
                locked=locked_fit,
                required_plan=req_fit,
            )
        )

    aid = (actor_user_id or "").strip()
    if aid:
        c_nna = await count_candidates_no_next_action_for_assignee(
            db,
            tenant_id=tenant_id,
            assignee_id=aid,
            own_company_id=own_company_id,
        )
        groups.append(
            NextActionGroupOut(
                id="candidates_no_next_action",
                entity="candidate",
                reason="candidate_no_next_action",
                title="Candidates without a next action (you)",
                count=c_nna,
                priority=28,
                query=NextActionQueryParams(),
                path=CANDIDATES_NO_NEXT_ACTION_PAGE,
                locked=False,
                required_plan=None,
            )
        )
        c_ov = await count_candidate_overdue_reminders_for_assignee(
            db,
            tenant_id=tenant_id,
            assignee_id=aid,
            own_company_id=own_company_id,
        )
        groups.append(
            NextActionGroupOut(
                id="candidates_next_overdue",
                entity="candidate",
                reason="candidate_reminder_overdue",
                title="Candidate reminders overdue (you)",
                count=c_ov,
                priority=23,
                query=NextActionQueryParams(
                    tab="tasks",
                    t_status="active",
                    t_entity="candidate",
                    t_due_bucket="overdue",
                ),
                path=TASKS,
                locked=False,
                required_plan=None,
            )
        )

    funnel_groups = await nba_conversion_funnel_insight_groups(
        db,
        tenant_id=tenant_id,
        own_company_id=own_company_id,
        plan=plan,
        team_ok=team_ok,
    )
    groups.extend(funnel_groups)

    groups.sort(key=lambda g: (g.locked, -g.priority, -g.count, g.id))
    return LeadNextActionsResponse(
        generated_at=datetime.now(timezone.utc),
        own_company_id=own_company_id,
        plan_code=plan,
        nba_tier=nba_tier,
        groups=groups,
    )


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

        extra_obj = _loads_extra(vacancy_extra)
        criteria = (extra_obj or {}).get("lead_criteria_v1")
        doc_status_payload: Optional[dict[str, set[str]]] = None
        if vacancy_extra_requires_candidate_documents_module(vacancy_extra):
            if cand_id:
                doc_status_payload = doc_status_by_candidate.get(str(cand_id), {})
            else:
                doc_status_payload = None
        fit_status, fit_reasons = evaluate_lead_criteria_v1(
            lead.normalized,
            criteria,
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
                custom_fields=custom_field_maps.get(str(lead.id), {}),
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
    own_company_id: Optional[str] = None,
    payload: Dict[str, Any],
    normalized: Dict[str, Any],
    source: str,
    external_id: Optional[str] = None,
    on_lead_created: Optional[Callable[[Lead], Awaitable[None]]] = None,
    force_existing: bool = False,
) -> MetaLeadResult:
    normalized = dict(normalized or {})
    business_type: Optional[str] = None
    settings_row = await _load_settings(db, tenant_id)
    tenant_entity_for_settings = await db.get(Tenant, tenant_id)
    tenant_settings_for_routing: Dict[str, Any] = {}
    if tenant_entity_for_settings is not None:
        ts = getattr(tenant_entity_for_settings, "settings", None)
        if isinstance(ts, dict):
            tenant_settings_for_routing = ts
    fallback_company_hint = settings_row.default_company_id
    fallback_recruiter_hint = settings_row.fallback_recruiter_id
    auto_create_enabled = bool(settings_row.auto_create_enabled)
    await _apply_leads_processing_mode_v1_to_normalized(
        db,
        tenant_id=tenant_id,
        normalized=normalized,
        settings_row=settings_row,
    )
    effective_processing_mode = str(normalized.get("leads_processing_mode_v1") or "assisted").strip().lower()
    # §2.10: only Automatic + auto_create may create candidates without operator (§2.4 tightens below).
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
        # If lead was already processed successfully we normally skip the whole pipeline.
        # However, when a lead is inconsistent (e.g. status=processed but candidate_id is missing)
        # we need to force re-processing.
        #
        # IMPORTANT:
        # - `status="new"` must NOT be treated as "already processed"; otherwise manual `POST /process`
        #   will never attach `candidate_id` nor update lead status.
        if not force_existing and lead.status in {"processed", "duplicated"}:
            effective_own_company_id = own_company_id or getattr(lead, "own_company_id", None)
            business_type = await _load_tenant_business_type(db, tenant_id, effective_own_company_id)
            recruiter_id: Optional[str] = None
            candidate_id = lead.candidate_id
            if candidate_id:
                candidate = await db.get(Candidate, candidate_id)
                if candidate:
                    recruiter_id = getattr(candidate, "recruiter_id", None)
                    # Candidates list is filtered by own_company_id (active OwnCompany in Topbar).
                    # Some lead->candidate flows can create candidates with own_company_id=None
                    # (e.g. when no vacancy was resolved). Fix it here so the candidate is visible.
                    lead_own_company_id = getattr(lead, "own_company_id", None)
                    candidate_own_company_id = getattr(candidate, "own_company_id", None)
                    if lead_own_company_id and not candidate_own_company_id:
                        candidate.own_company_id = str(lead_own_company_id)
                        await db.flush()
                    if recruiter_id and not getattr(candidate, "manager", None):
                        candidate.manager = recruiter_id
                        await db.flush()
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

            await lead_custom_fields.sync_lead_custom_fields_from_normalized(
                db,
                tenant_id=tenant_id,
                lead_id=str(lead.id),
                normalized=normalized,
            )
            await db.flush()

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

    req_oc = str(own_company_id or "").strip() or None
    lead_oc = (
        str(getattr(lead, "own_company_id", None) or "").strip() or None
        if lead is not None
        else None
    )
    scope_for_vacancy_routing = req_oc or lead_oc
    vacancy, routing_fit_status, routing_fit_reasons = await resolve_vacancy_for_lead_processing(
        db,
        tenant_id=tenant_id,
        normalized=normalized,
        tenant_settings=tenant_settings_for_routing,
        source=source,
        own_company_id=scope_for_vacancy_routing,
    )

    tenant_autoconv = bool(getattr(settings_row, "leads_auto_convert_on_fit_v1", True))
    may_auto_convert = (
        bool(auto_create_enabled)
        and effective_processing_mode == "automatic"
        and tenant_autoconv
        and _vacancy_allows_auto_convert_on_fit(vacancy)
    )
    normalized["leads_auto_convert_on_fit_effective_v1"] = bool(may_auto_convert)

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
        tenant_row = await db.get(Tenant, tenant_id)
        lic_row = (
            await db.execute(select(TenantLicense).where(TenantLicense.tenant_id == tenant_id).limit(1))
        ).scalar_one_or_none()
        if tenant_row and billing_restrictions.tenant_billing_blocks_new_leads(tenant_row, lic_row):
            reason = billing_restrictions.billing_write_block_reason(tenant_row, lic_row)
            code = "BILLING_TRIAL_EXPIRED" if reason == "trial_expired" else "BILLING_PAST_DUE"
            raise LeadProcessingError("billing_blocked", code)
        # Always prefer the active OwnCompany (Topbar) so that:
        # - lead.own_company_id matches current scope
        # - candidates/clients remain visible in the UI after conversion
        own_company_id_for_lead = own_company_id
        if not own_company_id_for_lead:
            own_company_id_for_lead = getattr(vacancy, "own_company_id", None) if vacancy else None
        if not own_company_id_for_lead:
            row = await db.execute(
                select(OwnCompany.id)
                .where(OwnCompany.tenant_id == tenant_id, OwnCompany.is_archived.is_(False))
                .order_by(OwnCompany.created_at.asc())
                .limit(1)
            )
            own_company_id_for_lead = row.scalar_one_or_none()
        if not own_company_id_for_lead:
            raise LeadProcessingError("needs_routing", "OWN_COMPANY_REQUIRED")
        lead = await crud.create_lead(
            db,
            tenant_id=tenant_id,
            own_company_id=str(own_company_id_for_lead),
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
            # Prefer active OwnCompany if provided; otherwise fall back to vacancy.
            lead.own_company_id = own_company_id or (getattr(vacancy, "own_company_id", None) if vacancy else None)
        lead.payload = payload
        lead.normalized = normalized
        lead.ad_id = normalized.get("ad_id")
        await db.flush()

    await lead_custom_fields.sync_lead_custom_fields_from_normalized(
        db,
        tenant_id=tenant_id,
        lead_id=str(lead.id),
        normalized=normalized,
    )
    await db.flush()

    # At this point `lead.own_company_id` is known (from vacancy or OwnCompany fallback),
    # so we can determine the scenario using OwnCompany settings.
    effective_own_company_id = own_company_id or getattr(lead, "own_company_id", None)
    business_type = await _load_tenant_business_type(db, tenant_id, effective_own_company_id)

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
        await lead_custom_fields.sync_lead_custom_fields_from_normalized(
            db,
            tenant_id=tenant_id,
            lead_id=str(lead.id),
            normalized=normalized,
        )
        await db.flush()
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

    if (
        may_auto_convert
        and business_type not in (None, "services")
        and vacancy is not None
        and routing_fit_status in ("no_fit", "needs_info")
    ):
        err_code = "LEAD_FIT_NO_MATCH" if routing_fit_status == "no_fit" else "LEAD_FIT_NEEDS_INFO"
        _stamp_lead_qualification_preview_v1(
            normalized,
            vacancy=vacancy,
            fit_status=routing_fit_status,
            fit_reasons=list(routing_fit_reasons or []),
            blocked_auto_convert=True,
        )
        now_marker = datetime.now(timezone.utc)
        await crud.update_lead(
            db,
            lead,
            status="needs_routing",
            vacancy_id=lead.vacancy_id,
            normalized=normalized,
            error=err_code,
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
        await lead_custom_fields.sync_lead_custom_fields_from_normalized(
            db,
            tenant_id=tenant_id,
            lead_id=str(lead.id),
            normalized=normalized,
        )
        await db.flush()
        await _audit_lead_qualification_rule_match(
            db, tenant_id=tenant_id, lead_id=str(lead.id), normalized=normalized
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
            error=err_code,
            is_new=created_new,
        )

    if not may_auto_convert:
        if business_type not in (None, "services"):
            if effective_processing_mode == "assisted":
                _stamp_lead_qualification_preview_v1(
                    normalized,
                    vacancy=vacancy,
                    fit_status=routing_fit_status,
                    fit_reasons=list(routing_fit_reasons or []),
                    blocked_auto_convert=False,
                )
            elif effective_processing_mode == "automatic" and bool(auto_create_enabled):
                _stamp_lead_qualification_preview_v1(
                    normalized,
                    vacancy=vacancy,
                    fit_status=routing_fit_status,
                    fit_reasons=list(routing_fit_reasons or []),
                    blocked_auto_convert=True,
                )
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
        await lead_custom_fields.sync_lead_custom_fields_from_normalized(
            db,
            tenant_id=tenant_id,
            lead_id=str(lead.id),
            normalized=normalized,
        )
        await db.flush()
        await _audit_lead_qualification_rule_match(
            db, tenant_id=tenant_id, lead_id=str(lead.id), normalized=normalized
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
        # After commits SQLAlchemy may expire ORM instances, so avoid accessing `lead.*`
        # after `await db.commit()` by capturing values upfront.
        services_lead_id = str(lead.id)
        services_lead_source = lead.source
        services_lead_vacancy_id = lead.vacancy_id
        await crud.update_lead(
            db,
            lead,
            status="processed",
            candidate_id=None,
            vacancy_id=lead.vacancy_id,
            normalized=normalized,
            error=None,
        )
        await lead_custom_fields.sync_lead_custom_fields_from_normalized(
            db,
            tenant_id=tenant_id,
            lead_id=str(lead.id),
            normalized=normalized,
        )
        await db.flush()
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
        # Important: commit lead status update before running automation rules.
        # Automation failures previously caused `db.rollback()` to undo the lead update,
        # leaving the UI with stale status/error even though processing returned success.
        await _audit_lead_qualification_rule_match(
            db, tenant_id=tenant_id, lead_id=services_lead_id, normalized=normalized
        )
        await db.commit()
        # Minimal rules builder (R2.2): trigger lead.processed automation rules
        try:
            assignee_id = await _pick_lead_assignee_id(
                db,
                tenant_id=tenant_id,
                preferred_user_id=fallback_recruiter_hint,
                normalized=normalized,
                lead_id=str(services_lead_id),
            )
            rule_ctx_extras = await lead_custom_fields.automation_context_for_lead(
                db,
                tenant_id=tenant_id,
                lead_id=services_lead_id,
                normalized=normalized if isinstance(normalized, dict) else {},
            )
            await run_automation_rules(
                db,
                tenant_id=tenant_id,
                trigger="lead.processed",
                actor_id=assignee_id,
                context={
                    "entity_type": "lead",
                    "entity_id": services_lead_id,
                    "lead_id": services_lead_id,
                    "source": services_lead_source,
                    "status": "processed",
                    "business_type": business_type,
                    "company_id": resolved_company_id,
                    "vacancy_id": services_lead_vacancy_id,
                    "assignee_id": assignee_id,
                    **rule_ctx_extras,
                },
            )
            await db.commit()
        except Exception:
            await db.rollback()
        await db.commit()
        return MetaLeadResult(
            lead_id=services_lead_id,
            status="processed",
            vacancy_id=services_lead_vacancy_id,
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
        needs_routing_lead_id = str(lead.id)
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
        await lead_custom_fields.sync_lead_custom_fields_from_normalized(
            db,
            tenant_id=tenant_id,
            lead_id=needs_routing_lead_id,
            normalized=normalized,
        )
        await db.flush()
        await _audit_lead_qualification_rule_match(
            db, tenant_id=tenant_id, lead_id=needs_routing_lead_id, normalized=normalized
        )
        await db.commit()
        return MetaLeadResult(
            lead_id=needs_routing_lead_id,
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
        "own_company_id": getattr(lead, "own_company_id", None),
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

    stamp_rid = _rule_recruiter_id_from_normalized(normalized)
    rule_rid = await validate_tenant_recruiter_id(db, tenant_id, stamp_rid) if stamp_rid else None
    recruiter_id = getattr(candidate, "recruiter_id", None)
    vacancy_recruiter_id = getattr(vacancy, "recruiter_id", None) if vacancy else None
    if rule_rid:
        candidate.recruiter_id = rule_rid
        recruiter_id = rule_rid
        await db.flush()
    elif not recruiter_id and vacancy_recruiter_id:
        candidate.recruiter_id = vacancy_recruiter_id
        recruiter_id = vacancy_recruiter_id
        await db.flush()
    if not recruiter_id:
        fallback_recruiter = await _validate_recruiter_id(db, tenant_id, fallback_recruiter_hint)
        if fallback_recruiter:
            candidate.recruiter_id = fallback_recruiter
            recruiter_id = fallback_recruiter
            await db.flush()

    # Filtering/UX can use candidate.manager (separate from recruiter_id).
    # For meta lead conversions we keep them aligned to avoid candidates disappearing
    # when user has "Менеджер" filter applied.
    if recruiter_id and not getattr(candidate, "manager", None):
        candidate.manager = recruiter_id
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
    await lead_custom_fields.sync_lead_custom_fields_from_normalized(
        db,
        tenant_id=tenant_id,
        lead_id=str(lead.id),
        normalized=normalized,
    )
    await db.flush()
    # Commit lead status update before automation to avoid losing it on rollback.
    agency_lead_id = str(lead.id)
    await _audit_lead_qualification_rule_match(
        db, tenant_id=tenant_id, lead_id=agency_lead_id, normalized=normalized
    )
    await db.commit()
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
        normalized=normalized,
        lead_id=agency_lead_id,
    )
    # Minimal rules builder (R2.2): trigger lead.processed automation rules (agency/employer path).
    try:
        rule_ctx_extras = await lead_custom_fields.automation_context_for_lead(
            db,
            tenant_id=tenant_id,
            lead_id=agency_lead_id,
            normalized=normalized if isinstance(normalized, dict) else {},
        )
        await run_automation_rules(
            db,
            tenant_id=tenant_id,
            trigger="lead.processed",
            actor_id=assignee_id,
            context={
                "entity_type": "lead",
                "entity_id": agency_lead_id,
                "lead_id": agency_lead_id,
                "source": lead.source,
                "status": "processed",
                "business_type": business_type,
                "company_id": resolved_company_id,
                "vacancy_id": str(vacancy.id) if vacancy else None,
                "candidate_id": str(candidate.id),
                "recruiter_id": recruiter_id,
                "assignee_id": assignee_id,
                **rule_ctx_extras,
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


async def bulk_auto_process_meta_lead_queue(
    db: AsyncSession,
    *,
    tenant_id: str,
    own_company_id: Optional[str],
    max_items: int = 25,
    statuses: tuple[str, ...] = ("needs_routing", "failed"),
    prefer_oldest_first: bool = False,
) -> Dict[str, Any]:
    """
    Process up to `max_items` Meta leads (same pipeline as POST .../process).
    Default: needs_routing / failed (auto-fix). Optional: status=new (NBA «unprocessed» batch).
    Each successful item commits inside `process_meta_lead`; failures roll back the session before continuing.
    """
    max_items = max(1, min(int(max_items or 25), 50))
    st_tuple = tuple(str(s).strip() for s in statuses if str(s or "").strip()) or ("needs_routing", "failed")
    filters = [
        Lead.tenant_id == tenant_id,
        func.lower(Lead.source) == "meta",
        Lead.status.in_(st_tuple),
    ]
    if own_company_id:
        filters.append(Lead.own_company_id == own_company_id)

    order = Lead.created_at.asc() if prefer_oldest_first else Lead.updated_at.desc()
    stmt = select(Lead).where(*filters).order_by(order).limit(max_items)
    rows = (await db.execute(stmt)).scalars().all()

    results: List[Dict[str, Any]] = []
    for lead in rows:
        lid = str(lead.id)
        if not getattr(lead, "payload", None):
            results.append(
                {
                    "lead_id": lid,
                    "ok": False,
                    "status_after": lead.status,
                    "error": "Lead payload is missing",
                }
            )
            continue
        force_existing = bool(getattr(lead, "candidate_id", None) is None) and getattr(lead, "status", None) in {
            "processed",
            "duplicated",
        }
        try:
            out = await process_meta_lead(
                db,
                tenant_id=tenant_id,
                own_company_id=own_company_id,
                payload=lead.payload,
                force_existing=force_existing,
            )
            results.append(
                {
                    "lead_id": lid,
                    "ok": True,
                    "status_after": out.status,
                    "error": None,
                }
            )
        except LeadProcessingError as exc:
            try:
                await db.rollback()
            except Exception:
                pass
            results.append(
                {
                    "lead_id": lid,
                    "ok": False,
                    "status_after": getattr(lead, "status", None),
                    "error": str(exc.message or exc),
                }
            )
        except Exception as exc:
            try:
                await db.rollback()
            except Exception:
                pass
            results.append(
                {
                    "lead_id": lid,
                    "ok": False,
                    "status_after": getattr(lead, "status", None),
                    "error": str(exc),
                }
            )

    succeeded = sum(1 for r in results if r.get("ok"))
    failed = len(results) - succeeded
    return {"results": results, "attempted": len(results), "succeeded": succeeded, "failed": failed}


async def process_meta_lead(
    db: AsyncSession,
    *,
    tenant_id: str,
    own_company_id: Optional[str] = None,
    payload: Dict[str, Any],
    force_existing: bool = False,
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
        own_company_id=own_company_id,
        payload=payload,
        normalized=normalized,
        source="meta",
        external_id=external_id,
        force_existing=force_existing,
    )


async def process_generic_inbound_webhook_lead(
    db: AsyncSession,
    *,
    tenant_id: str,
    own_company_id: Optional[str] = None,
    body: Dict[str, Any],
) -> MetaLeadResult:
    """
    §2.11: arbitrary JSON POST → same field_mapping + process_normalized_lead as Meta; source=webhook.
    """
    settings_row = await _load_settings(db, tenant_id)
    coerced = normalizer.coerce_generic_json_to_meta_normalizer_payload(body)
    normalized = normalizer.normalize_meta_payload(
        coerced,
        field_mapping=getattr(settings_row, "field_mapping", None),
    )
    raw_lead_id = normalized.get("raw_lead_id")
    external_id = str(raw_lead_id).strip() if raw_lead_id else None
    return await process_normalized_lead(
        db,
        tenant_id=tenant_id,
        own_company_id=own_company_id,
        payload=body,
        normalized=normalized,
        source="webhook",
        external_id=external_id,
        force_existing=False,
    )


async def retry_meta_leads(
    db: AsyncSession,
    *,
    tenant_id: str,
    own_company_id: Optional[str] = None,
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
                own_company_id=own_company_id,
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
        target_vacancy = await crud.resolve_vacancy_by_id(
            db,
            tenant_id,
            str(vacancy_candidate),
            scoped_own_company_id=str(getattr(lead, "own_company_id", None) or "").strip()
            or None,
        )

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
        duplicate_recruiter_id = getattr(duplicate, "recruiter_id", None)
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
            recruiter_id=duplicate_recruiter_id,
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

    # Capture values BEFORE create_candidate_full().
    # That function may internally commit/flush which can expire ORM instances.
    # Accessing expired attributes later can cause MissingGreenlet in async SQLAlchemy.
    vacancy_id_for_lead: Optional[str] = str(target_vacancy.id) if target_vacancy else None
    vacancy_recruiter_id: Optional[str] = getattr(target_vacancy, "recruiter_id", None) if target_vacancy else None
    own_company_id_for_lead: Optional[str] = getattr(lead, "own_company_id", None)

    candidate_payload: Dict[str, Any] = {
        "first_name": (normalized.get("first_name") or "Meta").strip() or "Meta",
        "last_name": (normalized.get("last_name") or normalized.get("full_name") or "Lead").strip() or "Lead",
        "email": email,
        "phone": phone,
        "phone_country_code": normalized.get("phone_country_code"),
        "own_company_id": own_company_id_for_lead,
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

    candidate_id_for_lead: Optional[str] = None
    identity = sa_inspect(candidate).identity
    if identity and identity[0]:
        candidate_id_for_lead = str(identity[0])
    if not candidate_id_for_lead:
        # Defensive fallback: candidate primary key must exist.
        raise LeadProcessingError("candidate_id_missing", "CANDIDATE_ID_MISSING_AFTER_CREATE")

    stamp_rid = _rule_recruiter_id_from_normalized(normalized)
    rule_rid = await validate_tenant_recruiter_id(db, tenant_id, stamp_rid) if stamp_rid else None
    recruiter_id = vacancy_recruiter_id
    if rule_rid:
        candidate.recruiter_id = rule_rid
        recruiter_id = rule_rid
        await db.flush()
    if not recruiter_id:
        # If we don't have vacancy/recruiter from vacancy, fall back to the tenant-level hint.
        # Avoid reading candidate.recruiter_id here: create_candidate_full() may have expired it.
        fallback_recruiter = await _validate_recruiter_id(db, tenant_id, fallback_recruiter_hint)
        if fallback_recruiter:
            candidate.recruiter_id = fallback_recruiter
            recruiter_id = fallback_recruiter
            await db.flush()

    if recruiter_id and not getattr(candidate, "manager", None):
        candidate.manager = recruiter_id
        await db.flush()

    await crud.update_lead(
        db,
        lead,
        status="processed",
        candidate_id=candidate_id_for_lead,
        vacancy_id=vacancy_id_for_lead,
        normalized=normalized,
        error=None,
        last_routed_at=now_marker,
    )
    await db.commit()

    return MetaLeadResult(
        lead_id=lead.id,
        status="processed",
        vacancy_id=vacancy_id_for_lead,
        candidate_id=candidate_id_for_lead,
        recruiter_id=recruiter_id,
        error=None,
    )
