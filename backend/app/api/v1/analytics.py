from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, time, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Literal, Counter as TCounter
import json

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import func, select, or_, and_, text
from sqlalchemy import exists
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased, selectinload
from uuid import UUID

from backend.app.core.cache import cache_get, cache_set
from backend.app.db.deps import get_db_with_tenant
from backend.app.auth.deps import UserCtx, get_current_user
from backend.app.models.audit import ActivityLog
from backend.app.models.candidate import Candidate
from backend.app.models.candidate_handoff import CandidateHandoff
from backend.app.models.candidate_stage_history import CandidateStageHistory
from backend.app.models.company import Company
from backend.app.models.contact_attempt import ContactAttempt
from backend.app.models.document import Document
from backend.app.models.lead import Lead
from backend.app.models.reminder import Reminder
from backend.app.models.risk_intel import RiskIntelEntityShadow
from backend.app.models.additional_service import ServiceOrder
from backend.app.models.tenant import Tenant
from backend.app.models.user import User
from backend.app.models.vacancy import Vacancy
from backend.app.models.additional_service import ServiceOrderStatus
from backend.app.models.reminder import ReminderStatus
from backend.app.models.additional_service import Service, ServiceItem
from backend.app.models.invoice import Invoice
from backend.app.models.tenant import TenantLink
from backend.app.services.handoff import is_client_tenant_for_list
from backend.app.models.enums import CandidateStage
from backend.app.constants.stages import (
    LABELS as STAGE_LABELS,
    PIPELINE_COMPLETED_STAGE_CODES,
    STATUS_REASON_CHOICES,
    ORDER as STAGE_ORDER,
    STAGE_META as STAGE_META_CONST,
    code_for_label,
    is_stage_code,
)

_CANDIDATE_ACTIVE_FOR_NEXT_ACTION = or_(
    Candidate.stage.is_(None),
    Candidate.stage.notin_(tuple(PIPELINE_COMPLETED_STAGE_CODES)),
)
from backend.app.services.onboarding_demo_seed import onboarding_demo_still_active
from backend.app.services.tenant_visibility import TenantVisibility, get_tenant_visibility
from backend.app.services.source_labels import normalize_candidate_source
from backend.app.services.audit import log_activity
from backend.app.api.v1.utils.access import resolve_restricted_acl
from backend.app.api.v1.utils.own_company import resolve_active_own_company_id_optional
from backend.app.api.v1.candidates import repo as candidates_repo
from backend.app.api.v1.candidates.repo import _candidate_scope_clause as repo_scope_clause
from backend.app.services.additional_services import _service_order_scope_where
from backend.app.services.reminder_ops_counts import count_overdue_reminders_ops_scoped
from backend.app.services.risk_intel_v1 import (
    compute_candidate_risk_baseline,
    list_latest_shadow_snapshot,
    list_risk_intel_hourly_trends,
    list_shadow_digest_bucket_summaries,
    list_shadow_snapshot_for_bucket_iso,
    parse_shadow_bucket_iso,
    shadow_validation_summary,
)

router = APIRouter(tags=["analytics"], dependencies=[Depends(get_current_user)])

RISK_OPS_ROLES = frozenset({"superadmin", "administrator", "supervisor"})

# Canonical codes counted as «hired» in recruiter/manager aggregates (not employment_pending).
_CANONICAL_HIRED_STAGE_CODES = frozenset({"employed", "probation_ok"})


def _canonical_candidate_stage_token(stage_val: Any) -> Optional[str]:
    if stage_val is None:
        return None
    raw = stage_val.value if isinstance(stage_val, CandidateStage) else stage_val
    text = str(raw or "").strip()
    if not text:
        return None
    low = text.lower()
    if is_stage_code(low):
        return low
    mapped = code_for_label(text)
    return mapped


def _is_hired_stage_value(stage_val: Any) -> bool:
    code = _canonical_candidate_stage_token(stage_val)
    return bool(code) and code in _CANONICAL_HIRED_STAGE_CODES


def _normalize_stage_counter_key(raw: Any) -> Optional[str]:
    """Fold legacy enum / label values into canonical stage codes (matches DB `employed`, etc.)."""
    if raw is None:
        return None
    token = _canonical_candidate_stage_token(raw)
    if token:
        return token
    text = str(raw.value if isinstance(raw, CandidateStage) else raw).strip()
    if not text:
        return None
    low = text.lower()
    if is_stage_code(low):
        return low
    return text


MANAGER_DIGEST_ACK_ACTION = "risk_intel.manager_digest_ack"


async def _manager_digest_last_ack_bucket(db: AsyncSession, tenant_id: str, user_id: str) -> str | None:
    row = (
        await db.execute(
            select(ActivityLog.payload)
            .where(
                ActivityLog.tenant_id == tenant_id,
                ActivityLog.actor_id == user_id,
                ActivityLog.action == MANAGER_DIGEST_ACK_ACTION,
            )
            .order_by(ActivityLog.created_at.desc())
            .limit(1)
        )
    ).first()
    if not row:
        return None
    payload = row[0]
    p = payload if isinstance(payload, dict) else {}
    bs = p.get("bucket_start")
    return str(bs).strip() if bs else None


def _require_risk_ops_lead(ctx: UserCtx) -> None:
    role = (ctx.role or "").lower().strip()
    if role not in RISK_OPS_ROLES:
        raise HTTPException(
            status_code=403,
            detail="Risk intelligence requires supervisor, administrator, or superadmin role.",
        )

# Perf budgets: p95 thresholds (ms) by metric key.
# Keep small and actionable; these values are meant to be tuned after baseline stabilizes.
PERF_BUDGETS_P95_MS: dict[str, float] = {
    "leads.list.load": 1500.0,
    "candidates.list.load": 2500.0,
    "candidates.work_panel.load": 800.0,
    # Frontend-emitted via POST /analytics/events (perf); aligns with R1.5 Phase D SSOT.
    "candidate.card.open": 1200.0,
    # R3.4 — Overview risk intelligence (parallel analytics APIs).
    "dashboard.risk_intel.core.load": 12000.0,
    "dashboard.risk_intel.shadow_snapshot.load": 8000.0,
    # R3.4 — team settings risk_model_v1 GET.
    "settings.risk_intel.page.load": 4000.0,
}


class OpsCountersOut(BaseModel):
    no_next_action_candidates: int = 0
    overdue_reminders: int = 0
    # Active reminders assigned to current user without a resolvable CRM entity link.
    unlinked_tasks: int = 0
    # Onboarding / overview highlights (tenant-wide, complements assignee-scoped no_next_action_*)
    overview_pipeline_total: int = 0
    overview_stuck: int = 0
    overview_active_today: int = 0
    # Recruitment (open vacancies = status open, not archived; ACL-aligned with list_vacancies)
    open_vacancies: int = 0
    open_vacancies_candidates: int = 0
    # Service orders not completed/cancelled (tenant-wide; aligns with list_service_orders scope)
    open_service_orders: int = 0
    # Leads next action loop (processed leads only)
    leads_no_next_action: int = 0
    leads_overdue: int = 0
    leads_with_next_action: int = 0
    leads_total: int = 0
    # SLA nudge signals (best-effort, reminder-based)
    leads_sla_no_next_action_reminders: int = 0
    leads_sla_stuck_stage_reminders: int = 0
    leads_needs_routing: int = 0
    leads_failed: int = 0
    # New leads (status=new) created more than 24h ago — operational “no first touch” signal.
    leads_new_untouched_24h: int = 0
    draft_intake_stale: int = 0
    automation_rules_enabled: int = 0
    automation_events_24h: int = 0


@router.get("/analytics/ops-counters", response_model=OpsCountersOut)
async def ops_counters(
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    ctx: UserCtx = Depends(get_current_user),
):
    db, tenant_id = db_tenant
    tenant_id_str = str(tenant_id)

    # Candidate "no next action" = no active reminder for candidate assigned to current user.
    assignee = str(ctx.sub)
    active_statuses = (ReminderStatus.pending, ReminderStatus.new, ReminderStatus.overdue)
    reminder_exists = (
        exists()
        .where(
            Reminder.tenant_id == tenant_id_str,
            Reminder.entity_type == "candidate",
            Reminder.entity_id == Candidate.id,
            Reminder.assignee_id == assignee,
            Reminder.status.in_(active_statuses),
        )
        .correlate(Candidate)
    )
    no_next_action_candidates = (
        await db.execute(
            select(func.count())
            .select_from(Candidate)
            .where(
                Candidate.deleted_at.is_(None),
                Candidate.tenant_id == tenant_id_str,
                _CANDIDATE_ACTIVE_FOR_NEXT_ACTION,
                ~reminder_exists,
            )
        )
    ).scalar_one() or 0

    overdue_reminders = await count_overdue_reminders_ops_scoped(
        db, tenant_id=tenant_id_str, assignee_id=assignee
    )
    linkable_entity_types = ("candidate", "vacancy", "lead", "company", "communication_thread")
    entity_id_trimmed = func.trim(func.coalesce(Reminder.entity_id, ""))
    unlinked_tasks = (
        await db.execute(
            select(func.count())
            .select_from(Reminder)
            .where(
                Reminder.tenant_id == tenant_id_str,
                Reminder.assignee_id == assignee,
                Reminder.status.in_(active_statuses),
                or_(
                    entity_id_trimmed == "",
                    Reminder.entity_type.notin_(linkable_entity_types),
                ),
            )
        )
    ).scalar_one() or 0

    # Leads next action (processed leads only)
    # - no_next_action: processed leads with no active reminders
    # - overdue: processed leads with at least one active reminder overdue (status=overdue or due_at < now)
    # - with_next_action: processed leads with at least one active reminder
    now = datetime.now(timezone.utc)
    lead_active_statuses = (ReminderStatus.pending, ReminderStatus.new, ReminderStatus.overdue)

    lead_has_active_reminder = (
        exists()
        .where(
            Reminder.tenant_id == tenant_id_str,
            Reminder.entity_type == "lead",
            Reminder.entity_id == Lead.id,
            Reminder.status.in_(lead_active_statuses),
        )
        .correlate(Lead)
    )
    lead_has_overdue_reminder = (
        exists()
        .where(
            Reminder.tenant_id == tenant_id_str,
            Reminder.entity_type == "lead",
            Reminder.entity_id == Lead.id,
            Reminder.status.in_(lead_active_statuses),
            or_(Reminder.status == ReminderStatus.overdue, Reminder.due_at < now),
        )
        .correlate(Lead)
    )

    leads_total = (
        await db.execute(
            select(func.count()).select_from(Lead).where(
                Lead.tenant_id == tenant_id_str,
                Lead.status == "processed",
                Lead.candidate_id.is_(None),
            )
        )
    ).scalar_one() or 0
    leads_no_next_action = (
        await db.execute(
            select(func.count())
            .select_from(Lead)
            .where(
                Lead.tenant_id == tenant_id_str,
                Lead.status == "processed",
                Lead.candidate_id.is_(None),
                ~lead_has_active_reminder,
            )
        )
    ).scalar_one() or 0
    leads_with_next_action = (
        await db.execute(
            select(func.count())
            .select_from(Lead)
            .where(
                Lead.tenant_id == tenant_id_str,
                Lead.status == "processed",
                Lead.candidate_id.is_(None),
                lead_has_active_reminder,
            )
        )
    ).scalar_one() or 0
    leads_overdue = (
        await db.execute(
            select(func.count())
            .select_from(Lead)
            .where(
                Lead.tenant_id == tenant_id_str,
                Lead.status == "processed",
                Lead.candidate_id.is_(None),
                lead_has_overdue_reminder,
            )
        )
    ).scalar_one() or 0

    # Leads SLA: number of active "no next action" SLA reminders assigned to current user.
    leads_sla_no_next_action_reminders = (
        await db.execute(
            select(func.count())
            .select_from(Reminder)
            .where(
                Reminder.tenant_id == tenant_id_str,
                Reminder.assignee_id == assignee,
                Reminder.entity_type == "lead",
                Reminder.type == "leads_no_next_action",
                Reminder.status.in_(lead_active_statuses),
            )
        )
    ).scalar_one() or 0

    leads_sla_stuck_stage_reminders = (
        await db.execute(
            select(func.count())
            .select_from(Reminder)
            .where(
                Reminder.tenant_id == tenant_id_str,
                Reminder.assignee_id == assignee,
                Reminder.entity_type == "lead",
                Reminder.type == "leads_stuck_stage",
                Reminder.status.in_(lead_active_statuses),
            )
        )
    ).scalar_one() or 0

    leads_needs_routing = (
        await db.execute(
            select(func.count())
            .select_from(Lead)
            .where(Lead.tenant_id == tenant_id_str, Lead.status == "needs_routing")
        )
    ).scalar_one() or 0

    leads_failed = (
        await db.execute(
            select(func.count())
            .select_from(Lead)
            .where(Lead.tenant_id == tenant_id_str, Lead.status == "failed")
        )
    ).scalar_one() or 0

    _lead_stale_cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    leads_new_untouched_24h = (
        await db.execute(
            select(func.count())
            .select_from(Lead)
            .where(
                Lead.tenant_id == tenant_id_str,
                Lead.status == "new",
                Lead.created_at < _lead_stale_cutoff,
            )
        )
    ).scalar_one() or 0

    # Draft intake stale (24h+). Isolated: schema / tz drift must not fail the whole dashboard.
    draft_intake_stale = 0
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
        draft_intake_stale = (
            await db.execute(
                select(func.count())
                .select_from(Candidate)
                .where(
                    Candidate.tenant_id == tenant_id_str,
                    Candidate.deleted_at.is_(None),
                    Candidate.intake_status == "draft",
                    Candidate.updated_at < cutoff.replace(tzinfo=None),
                )
            )
        ).scalar_one() or 0
    except Exception:
        try:
            await db.rollback()
        except Exception:
            pass
        draft_intake_stale = 0

    # Automation rules enabled
    try:
        # Import from aggregated models to avoid app/backend import alias drift.
        from backend.app.models import AutomationRule
        automation_rules_enabled = (
            await db.execute(
                select(func.count())
                .select_from(AutomationRule)
                .where(AutomationRule.tenant_id == tenant_id_str, AutomationRule.enabled.is_(True))
            )
        ).scalar_one() or 0
    except Exception:
        # If a statement failed, the transaction is aborted in Postgres.
        # Roll back so subsequent counters can still execute.
        try:
            await db.rollback()
        except Exception:
            pass
        automation_rules_enabled = 0

    # Automation events last 24h (ActivityLog)
    since = datetime.now(timezone.utc) - timedelta(hours=24)
    try:
        automation_events_24h = (
            await db.execute(
                select(func.count())
                .select_from(ActivityLog)
                .where(
                    ActivityLog.tenant_id == tenant_id_str,
                    ActivityLog.action.like("automation.%"),
                    ActivityLog.created_at >= since,
                )
            )
        ).scalar_one() or 0
    except Exception:
        try:
            await db.rollback()
        except Exception:
            pass
        automation_events_24h = 0

    open_vacancies = 0
    open_vacancies_candidates = 0
    try:
        acl = await resolve_restricted_acl(db, tenant_id_str, ctx)
        vac_conds = [
            Vacancy.tenant_id == tenant_id_str,
            Vacancy.status == "open",
            Vacancy.is_archived.is_(False),
        ]
        if acl is not None:
            acl_filters = []
            if acl.company_ids:
                acl_filters.append(Vacancy.company_id.in_(list(acl.company_ids)))
            if acl.vacancy_ids:
                acl_filters.append(Vacancy.id.in_(list(acl.vacancy_ids)))
            if not acl_filters:
                vac_where = None
            else:
                vac_where = and_(*vac_conds, or_(*acl_filters))
        else:
            vac_where = and_(*vac_conds)

        if vac_where is not None:
            open_vacancies = int(
                (await db.execute(select(func.count()).select_from(Vacancy).where(vac_where))).scalar_one() or 0
            )
            vac_ids_subq = select(Vacancy.id).where(vac_where)
            open_vacancies_candidates = int(
                (
                    await db.execute(
                        select(func.count())
                        .select_from(Candidate)
                        .where(
                            Candidate.tenant_id == tenant_id_str,
                            Candidate.deleted_at.is_(None),
                            Candidate.vacancy_id.isnot(None),
                            Candidate.vacancy_id.in_(vac_ids_subq),
                        )
                    )
                ).scalar_one()
                or 0
            )
    except Exception:
        try:
            await db.rollback()
        except Exception:
            pass
        open_vacancies = 0
        open_vacancies_candidates = 0

    open_service_orders = 0
    try:
        terminal = (ServiceOrderStatus.completed.value, ServiceOrderStatus.cancelled.value)
        open_service_orders = int(
            (
                await db.execute(
                    select(func.count())
                    .select_from(ServiceOrder)
                    .where(
                        ServiceOrder.tenant_id == tenant_id_str,
                        ServiceOrder.status.notin_(list(terminal)),
                    )
                )
            ).scalar_one()
            or 0
        )
    except Exception:
        try:
            await db.rollback()
        except Exception:
            pass
        open_service_orders = 0

    overview_pipeline_total = 0
    overview_stuck = 0
    overview_active_today = 0
    try:
        tenant_row = (await db.execute(select(Tenant).where(Tenant.id == tenant_id_str).limit(1))).scalar_one_or_none()
        tsett = tenant_row.settings if tenant_row is not None and isinstance(tenant_row.settings, dict) else {}
        if onboarding_demo_still_active(tenant_row):
            bt_ov = str(tsett.get("business_type") or "agency").strip().lower()
            if bt_ov not in ("agency", "employer", "services"):
                bt_ov = "agency"
            today_d = datetime.now(timezone.utc).date()
            lead_terminal = ("won", "lost", "converted")
            if bt_ov == "services":
                overview_pipeline_total = int(
                    (
                        await db.execute(
                            select(func.count())
                            .select_from(Lead)
                            .where(
                                Lead.tenant_id == tenant_id_str,
                                Lead.status == "processed",
                                or_(Lead.stage.is_(None), Lead.stage.notin_(lead_terminal)),
                            )
                        )
                    ).scalar_one()
                    or 0
                )
                overview_stuck = int(
                    (
                        await db.execute(
                            select(func.count())
                            .select_from(Lead)
                            .where(Lead.tenant_id == tenant_id_str, Lead.status == "processed", Lead.stage == "negotiation")
                        )
                    ).scalar_one()
                    or 0
                )
                overview_active_today = int(
                    (
                        await db.execute(
                            select(func.count())
                            .select_from(Lead)
                            .where(
                                Lead.tenant_id == tenant_id_str,
                                Lead.status == "processed",
                                func.date(Lead.created_at) == today_d,
                            )
                        )
                    ).scalar_one()
                    or 0
                )
            else:
                overview_pipeline_total = int(
                    (
                        await db.execute(
                            select(func.count())
                            .select_from(Candidate)
                            .where(
                                Candidate.tenant_id == tenant_id_str,
                                Candidate.deleted_at.is_(None),
                                or_(Candidate.stage.is_(None), Candidate.stage.notin_(tuple(PIPELINE_COMPLETED_STAGE_CODES))),
                            )
                        )
                    ).scalar_one()
                    or 0
                )
                stuck_stage = "waiting_docs" if bt_ov == "agency" else "interview"
                overview_stuck = int(
                    (
                        await db.execute(
                            select(func.count())
                            .select_from(Candidate)
                            .where(
                                Candidate.tenant_id == tenant_id_str,
                                Candidate.deleted_at.is_(None),
                                Candidate.stage == stuck_stage,
                            )
                        )
                    ).scalar_one()
                    or 0
                )
                overview_active_today = int(
                    (
                        await db.execute(
                            select(func.count())
                            .select_from(Candidate)
                            .where(
                                Candidate.tenant_id == tenant_id_str,
                                Candidate.deleted_at.is_(None),
                                func.date(Candidate.updated_at) == today_d,
                                or_(
                                    Candidate.stage.is_(None),
                                    Candidate.stage.notin_(tuple(PIPELINE_COMPLETED_STAGE_CODES)),
                                ),
                            )
                        )
                    ).scalar_one()
                    or 0
                )
    except Exception:
        try:
            await db.rollback()
        except Exception:
            pass
        overview_pipeline_total = 0
        overview_stuck = 0
        overview_active_today = 0

    return OpsCountersOut(
        no_next_action_candidates=int(no_next_action_candidates),
        overdue_reminders=int(overdue_reminders),
        unlinked_tasks=int(unlinked_tasks),
        overview_pipeline_total=int(overview_pipeline_total),
        overview_stuck=int(overview_stuck),
        overview_active_today=int(overview_active_today),
        open_vacancies=int(open_vacancies),
        open_vacancies_candidates=int(open_vacancies_candidates),
        open_service_orders=int(open_service_orders),
        leads_no_next_action=int(leads_no_next_action),
        leads_overdue=int(leads_overdue),
        leads_with_next_action=int(leads_with_next_action),
        leads_total=int(leads_total),
        leads_sla_no_next_action_reminders=int(leads_sla_no_next_action_reminders),
        leads_sla_stuck_stage_reminders=int(leads_sla_stuck_stage_reminders),
        leads_needs_routing=int(leads_needs_routing),
        leads_failed=int(leads_failed),
        leads_new_untouched_24h=int(leads_new_untouched_24h),
        draft_intake_stale=int(draft_intake_stale),
        automation_rules_enabled=int(automation_rules_enabled),
        automation_events_24h=int(automation_events_24h),
    )


class StageTimeItemOut(BaseModel):
    stage: str
    count: int
    avg_days: float
    p50_days: float
    p90_days: float


class StageTransitionOut(BaseModel):
    from_stage: Optional[str] = None
    to_stage: str
    count: int


class StageMetricsOut(BaseModel):
    generated_at: datetime
    stage_time: List[StageTimeItemOut]
    transitions: List[StageTransitionOut]
    readiness: Dict[str, int]


def _safe_docs_progress(docs_progress: Any) -> Dict[str, Any]:
    if isinstance(docs_progress, dict):
        return docs_progress
    if isinstance(docs_progress, str):
        try:
            parsed = json.loads(docs_progress)
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            return {}
    return {}


def _readiness_key_from_docs_progress(progress: Dict[str, Any]) -> str:
    # Mirror frontend deriveDocsMeta() fallback order (minimal subset).
    raw = (
        str(progress.get("readiness_state") or progress.get("readinessState") or progress.get("state") or "")
        .strip()
        .lower()
    )
    if raw:
        return raw
    total = int(progress.get("total") or progress.get("count") or 0) if str(progress.get("total") or progress.get("count") or "0").isdigit() else 0
    ready = int(progress.get("ready") or progress.get("verified") or progress.get("approved") or 0) if str(progress.get("ready") or progress.get("verified") or progress.get("approved") or "0").isdigit() else 0
    problem = int(progress.get("problem") or progress.get("invalid") or progress.get("expired") or progress.get("overdue") or 0) if str(progress.get("problem") or progress.get("invalid") or progress.get("expired") or progress.get("overdue") or "0").isdigit() else 0
    in_progress = int(progress.get("in_progress") or progress.get("submitted") or progress.get("pending_validation") or 0) if str(progress.get("in_progress") or progress.get("submitted") or progress.get("pending_validation") or "0").isdigit() else 0
    ordered = int(progress.get("ordered") or progress.get("requested") or progress.get("pending") or progress.get("ordered_count") or 0) if str(progress.get("ordered") or progress.get("requested") or progress.get("pending") or progress.get("ordered_count") or "0").isdigit() else 0
    with_files = int(progress.get("with_files") or progress.get("uploaded") or progress.get("files") or progress.get("files_count") or 0) if str(progress.get("with_files") or progress.get("uploaded") or progress.get("files") or progress.get("files_count") or "0").isdigit() else 0
    if problem > 0:
        return "problem"
    if ready > 0 and (total == 0 or ready >= total):
        return "ready"
    if in_progress > 0:
        return "in_progress"
    if ordered > 0:
        return "ordered"
    if with_files > 0:
        return "awaiting_review"
    if total > 0:
        return "pending"
    return "pending"


def _percentile(sorted_values: List[float], p: float) -> float:
    if not sorted_values:
        return 0.0
    if p <= 0:
        return float(sorted_values[0])
    if p >= 1:
        return float(sorted_values[-1])
    idx = int(round((len(sorted_values) - 1) * p))
    idx = max(0, min(len(sorted_values) - 1, idx))
    return float(sorted_values[idx])


@router.get("/analytics/stage-metrics", response_model=StageMetricsOut)
async def stage_metrics(
    date_from: Optional[str] = Query(None, alias="from"),
    date_to: Optional[str] = Query(None, alias="to"),
    limit_transitions: int = Query(30, ge=5, le=200),
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
):
    db, tenant_id = db_tenant
    tenant_id_str = str(tenant_id)
    now = datetime.now(timezone.utc)

    dfrom = _parse_dt(date_from)
    dto = _parse_dt(date_to, end_of_day=True)

    # Stage entered_at per candidate for current stage: last history record to_code == candidate.stage.
    stage_entered_rows = await db.execute(
        select(CandidateStageHistory.candidate_id, func.max(CandidateStageHistory.at))
        .where(CandidateStageHistory.tenant_id == tenant_id_str)
        .group_by(CandidateStageHistory.candidate_id)
    )
    # Note: history is stored for every stage change; for "current stage since", we need last entry,
    # and it should correspond to current stage. We'll validate against candidate.stage below.
    last_stage_at_map = {cid: at for cid, at in stage_entered_rows.all() if cid and at}

    cand_rows = await db.execute(
        select(Candidate.id, Candidate.stage, Candidate.docs_progress, Candidate.created_at)
        .where(Candidate.tenant_id == tenant_id_str, Candidate.deleted_at.is_(None))
    )
    by_stage_days: Dict[str, List[float]] = defaultdict(list)
    readiness_counts: Dict[str, int] = defaultdict(int)

    for cid, stage, docs_progress, created_at in cand_rows.all():
        stage_code = str(stage or "unknown")
        entered_at = last_stage_at_map.get(str(cid)) or created_at
        if entered_at is None:
            continue
        # stage history uses tz-aware at; created_at might be naive
        if isinstance(entered_at, datetime) and entered_at.tzinfo is None:
            entered_at = entered_at.replace(tzinfo=timezone.utc)
        days = max(0.0, (now - entered_at).total_seconds() / 86400.0)
        by_stage_days[stage_code].append(days)

        progress = _safe_docs_progress(docs_progress)
        key = _readiness_key_from_docs_progress(progress)
        readiness_counts[key] += 1

    stage_time_items: List[StageTimeItemOut] = []
    for stage_code, vals in by_stage_days.items():
        vals_sorted = sorted(vals)
        avg = float(sum(vals_sorted) / max(1, len(vals_sorted)))
        stage_time_items.append(
            StageTimeItemOut(
                stage=stage_code,
                count=len(vals_sorted),
                avg_days=round(avg, 2),
                p50_days=round(_percentile(vals_sorted, 0.5), 2),
                p90_days=round(_percentile(vals_sorted, 0.9), 2),
            )
        )
    stage_time_items.sort(key=lambda x: (-x.avg_days, -x.count, x.stage))

    # Transitions over period (from/to within date range)
    trans_stmt = (
        select(CandidateStageHistory.from_code, CandidateStageHistory.to_code, func.count())
        .where(CandidateStageHistory.tenant_id == tenant_id_str)
    )
    if dfrom:
        trans_stmt = trans_stmt.where(CandidateStageHistory.at >= dfrom)
    if dto:
        trans_stmt = trans_stmt.where(CandidateStageHistory.at <= dto)
    trans_stmt = trans_stmt.group_by(CandidateStageHistory.from_code, CandidateStageHistory.to_code)
    trans_rows = await db.execute(trans_stmt)
    transitions = [
        StageTransitionOut(from_stage=fs, to_stage=ts, count=int(cnt or 0))
        for fs, ts, cnt in trans_rows.all()
        if ts
    ]
    transitions.sort(key=lambda x: x.count, reverse=True)
    transitions = transitions[:limit_transitions]

    return StageMetricsOut(
        generated_at=now,
        stage_time=stage_time_items[:50],
        transitions=transitions,
        readiness={k: int(v) for k, v in readiness_counts.items()},
    )


_REASON_LABELS = {
    stage: {item["code"]: item["label"] for item in items}
    for stage, items in STATUS_REASON_CHOICES.items()
}


_CLIENT_KIND_ALIASES = {
    "client",
    "customer",
    "заказчик",
    "клиент",
}

_COUNTERPARTY_KIND_ALIASES = {
    "counterparty",
    "vendor",
    "supplier",
    "contractor",
    "subcontractor",
    "partner",
    "исполнитель",
    "подрядчик",
    "контрагент",
}


def _safe_dict(value: Any) -> Dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            return {}
    return {}


def _tenant_business_type(tenant: Optional[Tenant]) -> str:
    if tenant is None:
        return "agency"
    settings_payload = tenant.settings if isinstance(tenant.settings, dict) else {}
    raw_business_type = settings_payload.get("business_type")
    normalized = str(raw_business_type or "").strip().lower()
    if normalized in {"agency", "employer", "services"}:
        return normalized
    tenant_type = str(getattr(getattr(tenant, "type", None), "value", getattr(tenant, "type", ""))).strip().lower()
    if tenant_type == "company":
        return "employer"
    return "agency"


def _normalize_company_kind(extra_payload: Any) -> str:
    extra = _safe_dict(extra_payload)
    raw_value = (
        extra.get("company_kind")
        or extra.get("company_type")
        or extra.get("kind")
        or extra.get("entity_type")
        or extra.get("segment")
        or extra.get("role")
    )
    normalized = str(raw_value or "").strip().lower()
    if normalized in _COUNTERPARTY_KIND_ALIASES:
        return "counterparty"
    if normalized in _CLIENT_KIND_ALIASES:
        return "client"
    return "unknown"


def _as_float(value: Any) -> float:
    if value is None:
        return 0.0
    if isinstance(value, Decimal):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _status_reason_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return []
        try:
            parsed = json.loads(s)
            if isinstance(parsed, list):
                return [str(v).strip() for v in parsed if str(v).strip()]
        except Exception:
            pass
        return [part.strip() for part in s.split(",") if part and part.strip()]
    return []


def _stage_label(code: Optional[str]) -> str:
    if not code:
        return "—"
    return STAGE_LABELS.get(code, str(code))


_ORDERED_STAGE_LABELS = [_stage_label(code) for code in STAGE_ORDER]

# Безопасный снимок метаданных стадий (если константа недоступна, используем пустой dict)
STAGE_META: Dict[str, Dict[str, Any]] = dict(STAGE_META_CONST or {})  # type: ignore[arg-type]


def _stage_visible_for_view(code: Optional[str], view: str) -> bool:
    """
    Определяет, должен ли этап участвовать в текущем режиме отображения пайплайна.

    view:
      - "all"    — все стадии без фильтрации
      - "agency" — только стадии, видимые агентству
      - "client" — только стадии, видимые клиенту
    """
    if not code or view == "all":
        return True
    meta = STAGE_META.get(code) or {}
    if view == "agency":
        return bool(meta.get("visible_for_agency", True))
    if view == "client":
        return bool(meta.get("visible_for_client", False))
    return True


# DEPRECATED: Use repo._candidate_scope_clause instead for client tenant support
# Keeping for backward compatibility in export endpoint
def _candidate_scope_clause_legacy(tenant_id: str, visibility: TenantVisibility | None):
    clauses = [Candidate.tenant_id == tenant_id]
    shared_vacancies = getattr(visibility, "shared_vacancy_ids", set()) or set()
    shared_companies = getattr(visibility, "shared_company_ids", set()) or set()
    extra = []
    if shared_vacancies:
        extra.append(Candidate.vacancy_id.in_(shared_vacancies))
    if shared_companies:
        extra.append(Candidate.company_id.in_(shared_companies))
    if extra:
        clauses.append(or_(*extra))
    return or_(*clauses)


# ------- helpers -------
def _parse_dt(value: Optional[str], *, end_of_day: bool = False) -> Optional[datetime]:
    if not value:
        return None
    # поддержим и YYYY-MM-DD, и полные ISO-датавремена
    try:
        # полные ISO, например 2025-08-14T10:25:00
        return _with_day_end(datetime.fromisoformat(value), end_of_day=end_of_day)
    except Exception:
        # только дата 2025-08-14
        try:
            return _with_day_end(datetime.fromisoformat(value + "T00:00:00"), end_of_day=end_of_day)
        except Exception:
            return None


def _with_day_end(dt: datetime, *, end_of_day: bool) -> datetime:
    if not end_of_day:
        return dt
    if (
        dt.hour == 0
        and dt.minute == 0
        and dt.second == 0
        and dt.microsecond == 0
    ):
        return dt.replace(hour=23, minute=59, second=59, microsecond=999_999)
    return dt


def _apply_period_filters(
    stmt, date_from: Optional[datetime], date_to: Optional[datetime], by: str
):
    # by=created|updated — выбираем по какому полю фильтровать
    col = Candidate.created_at if by == "created" else Candidate.updated_at
    if date_from:
        stmt = stmt.where(col >= date_from)
    if date_to:
        stmt = stmt.where(col <= date_to)
    return stmt


# ------- /overview (как было, оставим без изменений) -------
@router.get("/analytics/overview")
async def overview(
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    stage_view: Optional[str] = Query(
        None,
        description="all | agency | client — режим отображения пайплайна по стадиям",
    ),
):
    db, tenant_id = db_tenant
    tenant_id_str = str(tenant_id)
    visibility = get_tenant_visibility(db, tenant_id_str)
    is_client = await is_client_tenant_for_list(db, tenant_id_str)
    effective_stage_view = stage_view or ("client" if is_client else "all")
    scope_clause = repo_scope_clause(tenant_id_str, visibility, is_client_tenant=is_client)

    total_stmt = select(func.count()).select_from(Candidate).where(
        and_(Candidate.deleted_at.is_(None), scope_clause)
    )
    total = (await db.execute(total_stmt)).scalar_one()

    # по стадиям
    rows = (
        await db.execute(
            select(Candidate.stage, func.count())
            .where(and_(Candidate.deleted_at.is_(None), scope_clause))
            .group_by(Candidate.stage)
            .order_by(func.count().desc())
        )
    ).all()
    raw_by_stage = {
        (s.value if isinstance(s, CandidateStage) else str(s)): cnt for s, cnt in rows
    }
    by_stage = {
        code: cnt
        for code, cnt in raw_by_stage.items()
        if _stage_visible_for_view(code, effective_stage_view)
    }

    # считаем языки без БД-специфичных функций (кросс-БД)
    lang_counter: TCounter[str] = Counter()
    # забираем только колонку languages
    langs_rows = (await db.execute(select(Candidate.languages).where(and_(Candidate.deleted_at.is_(None), scope_clause)))).all()
    for (langs,) in langs_rows:
        if not langs:
            continue
        # поддержим как список строк, так и строку с запятыми
        if isinstance(langs, (list, tuple)):
            lang_counter.update([str(x or "") for x in langs])
        else:
            # если пришла строка, разбиваем по запятым
            parts = [p.strip() for p in str(langs).split(",")]
            lang_counter.update([p for p in parts if p])
    by_language = dict(sorted(((k, int(v)) for k, v in lang_counter.items()), key=lambda x: -x[1]))

    return {"total": total, "by_stage": by_stage, "by_language": by_language}


@router.get("/analytics/profile-summary")
async def profile_summary(
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
):
    db, tenant_id = db_tenant
    tenant_id_str = str(tenant_id)

    tenant_row = await db.execute(select(Tenant).where(Tenant.id == tenant_id_str).limit(1))
    tenant = tenant_row.scalar_one_or_none()
    business_type = _tenant_business_type(tenant)

    total_companies = int(
        (await db.execute(select(func.count()).select_from(Company).where(Company.tenant_id == tenant_id_str))).scalar_one() or 0
    )
    active_companies = int(
        (
            await db.execute(
                select(func.count()).select_from(Company).where(Company.tenant_id == tenant_id_str, Company.is_archived.is_(False))
            )
        ).scalar_one()
        or 0
    )
    total_candidates = int(
        (
            await db.execute(
                select(func.count()).select_from(Candidate).where(Candidate.tenant_id == tenant_id_str, Candidate.deleted_at.is_(None))
            )
        ).scalar_one()
        or 0
    )
    total_vacancies = int(
        (await db.execute(select(func.count()).select_from(Vacancy).where(Vacancy.tenant_id == tenant_id_str))).scalar_one() or 0
    )
    active_vacancies = int(
        (
            await db.execute(
                select(func.count()).select_from(Vacancy).where(
                    Vacancy.tenant_id == tenant_id_str,
                    Vacancy.is_archived.is_(False),
                )
            )
        ).scalar_one()
        or 0
    )
    total_leads = int(
        (await db.execute(select(func.count()).select_from(Lead).where(Lead.tenant_id == tenant_id_str))).scalar_one() or 0
    )

    service_orders_total = int(
        (
            await db.execute(
                select(func.count()).select_from(ServiceOrder).where(ServiceOrder.tenant_id == tenant_id_str)
            )
        ).scalar_one()
        or 0
    )
    service_orders_rows = (
        await db.execute(
            select(ServiceOrder.status, func.count(), func.coalesce(func.sum(ServiceOrder.total_amount), 0))
            .where(ServiceOrder.tenant_id == tenant_id_str)
            .group_by(ServiceOrder.status)
        )
    ).all()
    service_orders_by_status = {str(status): int(count or 0) for status, count, _sum in service_orders_rows}
    service_revenue_delivered = 0.0
    for status, _count, total_sum in service_orders_rows:
        if str(status) == "completed":
            service_revenue_delivered = _as_float(total_sum)

    company_rows = (
        await db.execute(select(Company.id, Company.extra).where(Company.tenant_id == tenant_id_str))
    ).all()
    service_owner_company_rows = (
        await db.execute(
            select(ServiceOrder.company_id)
            .where(ServiceOrder.tenant_id == tenant_id_str, ServiceOrder.company_id.is_not(None))
            .distinct()
        )
    ).all()
    client_company_ids = {str(row[0]) for row in service_owner_company_rows if row and row[0]}

    clients_count = 0
    counterparties_count = 0
    unknown_count = 0
    for company_id, extra_payload in company_rows:
        if company_id and str(company_id) in client_company_ids:
            clients_count += 1
            continue
        kind = _normalize_company_kind(extra_payload)
        if kind == "counterparty":
            counterparties_count += 1
        elif kind == "client":
            clients_count += 1
        else:
            unknown_count += 1
            # Для services неизвестный тип считаем клиентом по умолчанию.
            clients_count += 1

    service_in_progress = sum(
        int(service_orders_by_status.get(key, 0))
        for key in ("confirmed", "in_progress", "on_hold")
    )
    service_delivered = int(service_orders_by_status.get("completed", 0))

    profile = {
        "business_type": business_type,
        "generated_at": datetime.utcnow().isoformat(),
        "kpis": {},
        "datasets": {},
    }

    if business_type == "services":
        profile["kpis"] = {
            "companies_total": total_companies,
            "companies_active": active_companies,
            "clients_total": clients_count,
            "counterparties_total": counterparties_count,
            "service_orders_total": service_orders_total,
            "service_orders_in_progress": service_in_progress,
            "service_orders_delivered": service_delivered,
            "service_revenue_delivered": round(service_revenue_delivered, 2),
            "leads_total": total_leads,
        }
        profile["datasets"] = {
            "primary_entities": ["clients", "counterparties", "service_orders", "leads"],
            "unknown_company_classification": unknown_count,
        }
    elif business_type == "employer":
        profile["kpis"] = {
            "vacancies_total": total_vacancies,
            "vacancies_active": active_vacancies,
            "candidates_total": total_candidates,
            "leads_total": total_leads,
            "companies_total": total_companies,
        }
        profile["datasets"] = {
            "primary_entities": ["vacancies", "candidates", "team", "communications"],
        }
    else:
        profile["kpis"] = {
            "companies_total": total_companies,
            "vacancies_active": active_vacancies,
            "candidates_total": total_candidates,
            "leads_total": total_leads,
            "service_orders_total": service_orders_total,
        }
        profile["datasets"] = {
            "primary_entities": ["clients", "candidates", "vacancies", "leads", "communications"],
        }

    return profile


class ServicesAnalyticsStatusRowOut(BaseModel):
    status: str
    count: int


class ServicesAnalyticsTopItemOut(BaseModel):
    service_id: Optional[str] = None
    label: str
    total: int
    pending: int
    revenue: float
    profit: float


class ServicesAnalyticsTopClientOut(BaseModel):
    owner_kind: str
    owner_id: Optional[str] = None
    label: str
    revenue: float
    profit: float
    orders: int


class ServicesAnalyticsHotOrderOut(BaseModel):
    order_id: str
    label: str
    reason: str
    owner_kind: str
    status: str
    updated_at: Optional[str] = None


class ServicesAnalyticsOverviewOut(BaseModel):
    generated_at: str
    totals: dict[str, float | int]
    last30: dict[str, int]
    data_quality: dict[str, int]
    status_breakdown: list[ServicesAnalyticsStatusRowOut]
    top_items: list[ServicesAnalyticsTopItemOut]
    top_clients: list[ServicesAnalyticsTopClientOut]
    hot_orders: list[ServicesAnalyticsHotOrderOut]
    trends: list[dict[str, float | int | str]]
    slices: list[dict[str, float | int | str | None]]


@router.get("/analytics/services-overview", response_model=ServicesAnalyticsOverviewOut)
async def services_overview(
    days: int = Query(90, ge=7, le=365),
    trend_bucket: str = Query("month", pattern="^(week|month)$"),
    slice_by: str = Query("client", pattern="^(client|item|status|manager)$"),
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    active_own_company_id: Optional[str] = Depends(resolve_active_own_company_id_optional),
):
    db, tenant_id = db_tenant
    tenant_id_str = str(tenant_id)
    stmt = select(ServiceOrder).where(ServiceOrder.tenant_id == tenant_id_str)
    scope = _service_order_scope_where(active_own_company_id)
    if scope is not None:
        stmt = (
            stmt.outerjoin(Candidate, ServiceOrder.candidate_id == Candidate.id)
            .outerjoin(Vacancy, ServiceOrder.vacancy_id == Vacancy.id)
            .where(scope)
        )
    stmt = (
        stmt.options(
            selectinload(ServiceOrder.items).selectinload(ServiceItem.service),
            selectinload(ServiceOrder.items).selectinload(ServiceItem.schedules),
            selectinload(ServiceOrder.items).selectinload(ServiceItem.attachments),
        )
        .order_by(ServiceOrder.updated_at.desc())
    )
    rows = (await db.execute(stmt)).scalars().all()

    # Build label lookup maps (avoid placeholder labels in UI).
    company_ids = {str(o.company_id) for o in rows if getattr(o, "company_id", None)}
    candidate_ids = {str(o.candidate_id) for o in rows if getattr(o, "candidate_id", None)}
    vacancy_ids = {str(o.vacancy_id) for o in rows if getattr(o, "vacancy_id", None)}
    user_ids = {str(getattr(o, "assigned_to", "") or "").strip() for o in rows if str(getattr(o, "assigned_to", "") or "").strip()}

    company_map: dict[str, str] = {}
    candidate_map: dict[str, str] = {}
    vacancy_map: dict[str, str] = {}
    user_map: dict[str, str] = {}

    if company_ids:
        crows = await db.execute(select(Company.id, Company.name).where(Company.tenant_id == tenant_id_str, Company.id.in_(company_ids)))
        company_map = {str(cid): (str(name or "").strip() or str(cid)[:8]) for cid, name in crows.all()}
    if candidate_ids:
        crow = await db.execute(select(Candidate.id, Candidate.first_name, Candidate.last_name).where(Candidate.tenant_id == tenant_id_str, Candidate.id.in_(candidate_ids)))
        candidate_map = {
            str(cid): (f"{(fn or '').strip()} {(ln or '').strip()}".strip() or str(cid)[:8])
            for cid, fn, ln in crow.all()
        }
    if vacancy_ids:
        vrow = await db.execute(select(Vacancy.id, Vacancy.title).where(Vacancy.tenant_id == tenant_id_str, Vacancy.id.in_(vacancy_ids)))
        vacancy_map = {str(vid): (str(title or "").strip() or str(vid)[:8]) for vid, title in vrow.all()}
    if user_ids:
        urow = await db.execute(select(User.id, User.full_name, User.email).where(User.tenant_id == tenant_id_str, User.id.in_(user_ids)))
        user_map = {
            str(uid): (str(full or "").strip() or str(email or "").strip() or str(uid)[:8])
            for uid, full, email in urow.all()
        }

    now = datetime.now(timezone.utc)

    # Invoice aggregation for service_orders (sell → invoice → collect analytics).
    order_ids = [str(o.id) for o in rows]
    invoices_by_order: dict[str, list[Invoice]] = defaultdict(list)
    invoices_invoiced_total = 0.0
    invoices_paid_total = 0.0
    invoices_overdue_count = 0
    if order_ids:
        inv_rows = await db.execute(
            select(Invoice).where(
                Invoice.tenant_id == tenant_id_str,
                Invoice.service_order_id.in_(order_ids),
            )
        )
        for inv in inv_rows.scalars().all():
            invoices_by_order[str(inv.service_order_id)].append(inv)
            try:
                invoices_invoiced_total += _as_float(getattr(inv, "total_amount", 0))
            except Exception:
                pass
            try:
                invoices_paid_total += _as_float(getattr(inv, "paid_amount", 0))
            except Exception:
                pass
            try:
                due = getattr(inv, "due_date", None)
                st = str(getattr(inv, "status", "") or "").strip().lower()
                if due and hasattr(due, "toordinal") and st not in {"paid", "cancelled"} and due < now.date():
                    invoices_overdue_count += 1
            except Exception:
                pass

    cutoff = now - timedelta(days=30)
    trends_cutoff = now - timedelta(days=days)

    revenue = 0.0
    estimated_cost = 0.0
    actual_cost = 0.0
    delivered_orders = 0
    cancelled_orders = 0
    confirmed_items = 0
    estimated_items = 0
    missing_items = 0
    status_counter: TCounter[str] = Counter()
    top_items_map: dict[str, dict[str, float | int | str | None]] = {}
    top_clients_map: dict[str, dict[str, float | int | str | None]] = {}
    trend_map: dict[str, dict[str, float | int | str]] = {}
    slice_map: dict[str, dict[str, float | int | str]] = {}
    hot_orders: list[ServicesAnalyticsHotOrderOut] = []
    last30_total = 0
    last30_delivered = 0
    last30_cancelled = 0

    def owner_label_and_kind(order: ServiceOrder) -> tuple[str, str]:
        if order.company_id:
            cid = str(order.company_id)
            return (company_map.get(cid) or cid[:8], "company")
        if order.candidate_id:
            cid = str(order.candidate_id)
            return (candidate_map.get(cid) or cid[:8], "candidate")
        if order.vacancy_id:
            vid = str(order.vacancy_id)
            return (vacancy_map.get(vid) or vid[:8], "vacancy")
        return ("Unknown", "unknown")

    def manager_label(order: ServiceOrder) -> str:
        assigned = str(getattr(order, "assigned_to", "") or "").strip()
        if not assigned:
            return "Unassigned"
        return user_map.get(assigned) or f"Manager {assigned[:8]}"

    def trend_key(order: ServiceOrder) -> str:
        dt = order.created_at or now
        if trend_bucket == "week":
            iso_year, iso_week, _ = dt.isocalendar()
            return f"{iso_year}-W{iso_week:02d}"
        return dt.strftime("%Y-%m")

    for order in rows:
        status_value = str(order.status)
        status_counter[status_value] += 1
        order_revenue = _as_float(order.total_amount)
        revenue += order_revenue
        if status_value == "completed":
            delivered_orders += 1
        if status_value == "cancelled":
            cancelled_orders += 1
        if order.created_at and order.created_at >= cutoff:
            last30_total += 1
            if status_value == "completed":
                last30_delivered += 1
            if status_value == "cancelled":
                last30_cancelled += 1

        client_label, owner_kind = owner_label_and_kind(order)
        owner_id = str(order.company_id or order.candidate_id or order.vacancy_id or "") or None
        slice_label = (
            client_label
            if slice_by == "client"
            else manager_label(order)
            if slice_by == "manager"
            else status_value
            if slice_by == "status"
            else None
        )
        client_entry = top_clients_map.get(client_label) or {
            "label": client_label,
            "owner_kind": owner_kind,
            "owner_id": owner_id,
            "revenue": 0.0,
            "profit": 0.0,
            "orders": 0,
        }
        client_entry["revenue"] = float(client_entry["revenue"]) + order_revenue
        client_entry["orders"] = int(client_entry["orders"]) + 1

        has_schedule_issue = False
        has_docs_issue = False
        first_item_label = "Unknown"
        order_profit = 0.0
        order_invoiced = 0.0
        order_paid = 0.0
        order_overdue = 0
        for inv in invoices_by_order.get(str(order.id), []):
            try:
                total_amount = _as_float(getattr(inv, "total_amount", 0))
            except Exception:
                total_amount = 0.0
            try:
                paid_amount = _as_float(getattr(inv, "paid_amount", 0))
            except Exception:
                paid_amount = 0.0
            order_invoiced += total_amount
            order_paid += paid_amount
            due = getattr(inv, "due_date", None)
            st = str(getattr(inv, "status", "") or "").strip().lower()
            if due and st not in {"paid", "cancelled"} and isinstance(due, (datetime, )):
                # due_date is Date on model; keep safe
                pass
            try:
                # due_date is date; compare with now.date()
                if due and hasattr(due, "toordinal") and st not in {"paid", "cancelled"} and due < now.date():
                    order_overdue += 1
            except Exception:
                pass
        for item in order.items:
            item_revenue = _as_float(item.amount)
            item_estimated_cost = _as_float(getattr(item, "estimated_cost", 0))
            raw_actual_cost = getattr(item, "actual_cost", None)
            item_actual_cost = _as_float(raw_actual_cost) if raw_actual_cost is not None else 0.0
            estimated_cost += item_estimated_cost
            if raw_actual_cost is not None:
                actual_cost += item_actual_cost
                confirmed_items += 1
            elif str(getattr(item, "cost_status", "missing")) == "estimated" or item_estimated_cost > 0:
                estimated_items += 1
            else:
                missing_items += 1
            item_cost = item_actual_cost if raw_actual_cost is not None else item_estimated_cost
            item_profit = item_revenue - item_cost
            order_profit += item_profit
            client_entry["profit"] = float(client_entry["profit"]) + item_profit

            item_label = (
                str(getattr(getattr(item, "service", None), "name", None) or "")
                or str(getattr(getattr(item, "service", None), "code", None) or "")
                or "Unknown"
            )
            if first_item_label == "Unknown":
                first_item_label = item_label
            item_entry = top_items_map.get(item_label) or {
                "service_id": str(getattr(item, "service_id", "") or "") or None,
                "label": item_label,
                "total": 0,
                "pending": 0,
                "revenue": 0.0,
                "profit": 0.0,
            }
            item_entry["total"] = int(item_entry["total"]) + 1
            if str(item.status) != "delivered":
                item_entry["pending"] = int(item_entry["pending"]) + 1
            item_entry["revenue"] = float(item_entry["revenue"]) + item_revenue
            item_entry["profit"] = float(item_entry["profit"]) + item_profit
            top_items_map[item_label] = item_entry

            if slice_by == "item":
                slice_label = item_label

            has_schedule_issue = has_schedule_issue or len(getattr(item, "schedules", []) or []) == 0
            has_docs_issue = has_docs_issue or (
                bool(getattr(item, "required_documents", None)) and len(getattr(item, "attachments", []) or []) == 0
            )

        top_clients_map[client_label] = client_entry

        if order.created_at and order.created_at >= trends_cutoff:
            trend_entry = trend_map.get(trend_key(order)) or {
                "bucket": trend_key(order),
                "orders": 0,
                "revenue": 0.0,
                "profit": 0.0,
                "delivered": 0,
                "invoiced": 0.0,
                "paid": 0.0,
                "overdue_invoices": 0,
            }
            trend_entry["orders"] = int(trend_entry["orders"]) + 1
            trend_entry["revenue"] = float(trend_entry["revenue"]) + order_revenue
            trend_entry["profit"] = float(trend_entry["profit"]) + order_profit
            trend_entry["invoiced"] = float(trend_entry["invoiced"]) + order_invoiced
            trend_entry["paid"] = float(trend_entry["paid"]) + order_paid
            trend_entry["overdue_invoices"] = int(trend_entry["overdue_invoices"]) + int(order_overdue)
            if status_value == "completed":
                trend_entry["delivered"] = int(trend_entry["delivered"]) + 1
            trend_map[trend_key(order)] = trend_entry

        if slice_label:
            slice_entry = slice_map.get(slice_label) or {
                "label": slice_label,
                "slice_kind": slice_by,
                "slice_value": owner_id if slice_by == "client" else slice_label,
                "owner_kind": owner_kind if slice_by == "client" else None,
                "orders": 0,
                "revenue": 0.0,
                "profit": 0.0,
            }
            slice_entry["orders"] = int(slice_entry["orders"]) + 1
            slice_entry["revenue"] = float(slice_entry["revenue"]) + order_revenue
            slice_entry["profit"] = float(slice_entry["profit"]) + order_profit
            slice_map[slice_label] = slice_entry

        if status_value not in {"completed", "cancelled"} and order.items:
            hot_orders.append(
                ServicesAnalyticsHotOrderOut(
                    order_id=str(order.id),
                    label=first_item_label,
                    reason="documents" if has_docs_issue else "schedule" if has_schedule_issue else "status",
                    owner_kind=owner_kind,
                    status=status_value,
                    updated_at=order.updated_at.isoformat() if order.updated_at else None,
                )
            )

    cost_base = actual_cost or estimated_cost
    gross_profit = revenue - cost_base
    gross_margin = round((gross_profit / revenue) * 100) if revenue > 0 else 0
    total_cost_items = confirmed_items + estimated_items + missing_items
    coverage = round((confirmed_items / total_cost_items) * 100) if total_cost_items else 0
    last30_rate = round((last30_cancelled / last30_total) * 100) if last30_total else 0

    return ServicesAnalyticsOverviewOut(
        generated_at=now.isoformat(),
        totals={
            "orders_total": len(rows),
            "delivered_orders": delivered_orders,
            "cancelled_orders": cancelled_orders,
            "revenue": round(revenue, 2),
            "estimated_cost": round(estimated_cost, 2),
            "actual_cost": round(actual_cost, 2),
            "gross_profit": round(gross_profit, 2),
            "gross_margin": gross_margin,
            "cost_coverage": coverage,
            "invoices_invoiced": round(invoices_invoiced_total, 2),
            "invoices_paid": round(invoices_paid_total, 2),
            "invoices_outstanding": round(max(0.0, invoices_invoiced_total - invoices_paid_total), 2),
            "invoices_overdue_count": int(invoices_overdue_count),
        },
        last30={
            "total": last30_total,
            "delivered": last30_delivered,
            "cancelled": last30_cancelled,
            "cancellation_rate": last30_rate,
        },
        data_quality={
            "confirmed_items": confirmed_items,
            "estimated_items": estimated_items,
            "missing_items": missing_items,
        },
        status_breakdown=[
            ServicesAnalyticsStatusRowOut(status=status, count=count)
            for status, count in sorted(status_counter.items(), key=lambda item: item[1], reverse=True)
        ],
        top_items=[
            ServicesAnalyticsTopItemOut(
                service_id=str(entry["service_id"]) if entry.get("service_id") else None,
                label=str(entry["label"]),
                total=int(entry["total"]),
                pending=int(entry["pending"]),
                revenue=round(float(entry["revenue"]), 2),
                profit=round(float(entry["profit"]), 2),
            )
            for entry in sorted(top_items_map.values(), key=lambda item: (float(item["profit"]), float(item["revenue"])), reverse=True)[:5]
        ],
        top_clients=[
            ServicesAnalyticsTopClientOut(
                owner_kind=str(entry["owner_kind"]),
                owner_id=str(entry["owner_id"]) if entry.get("owner_id") else None,
                label=str(entry["label"]),
                revenue=round(float(entry["revenue"]), 2),
                profit=round(float(entry["profit"]), 2),
                orders=int(entry["orders"]),
            )
            for entry in sorted(top_clients_map.values(), key=lambda item: (float(item["profit"]), float(item["revenue"])), reverse=True)[:5]
        ],
        hot_orders=sorted(hot_orders, key=lambda item: item.updated_at or "", reverse=True)[:5],
        trends=[
            {
                "bucket": str(entry["bucket"]),
                "orders": int(entry["orders"]),
                "delivered": int(entry["delivered"]),
                "revenue": round(float(entry["revenue"]), 2),
                "profit": round(float(entry["profit"]), 2),
            }
            for entry in sorted(trend_map.values(), key=lambda item: str(item["bucket"]))
        ],
        slices=[
            {
                "label": str(entry["label"]),
                "slice_kind": entry.get("slice_kind"),
                "slice_value": entry.get("slice_value"),
                "owner_kind": entry.get("owner_kind"),
                "orders": int(entry["orders"]),
                "revenue": round(float(entry["revenue"]), 2),
                "profit": round(float(entry["profit"]), 2),
            }
            for entry in sorted(slice_map.values(), key=lambda item: (float(item["profit"]), float(item["revenue"])), reverse=True)[:10]
        ],
    )


# ------- /funnel -------
@router.get("/analytics/funnel")
async def funnel(
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
    company_id: Optional[str] = Query(
        None,
        min_length=1,
        max_length=36,
        description="Operating company scope (required unless legacy_tenant=true)",
    ),
    legacy_tenant: bool = Query(
        False,
        description="Explicit legacy tenant-wide analytics (read-only strangler); requires company_id omitted",
    ),
    pipeline_type: str = Query(
        "candidate",
        pattern="^(candidate|lead)$",
        description="Recruitment pipeline kind — candidate and lead cannot be mixed in one report",
    ),
    module_key: str = Query(
        "recruitment",
        min_length=1,
        max_length=32,
        description="Module owner (P0: recruitment only)",
    ),
    funnel_id: Optional[str] = Query(
        None,
        max_length=36,
        description="Optional explicit funnel override (validated via resolver)",
    ),
    date_from: Optional[str] = Query(
        None, alias="from", description="ISO дата/время начала (включительно)"
    ),
    date_to: Optional[str] = Query(
        None, alias="to", description="ISO дата/время конца (включительно)"
    ),
    by: str = Query(
        "created",
        pattern="^(created|updated)$",
        description="created|updated — по какому полю фильтровать",
    ),
    stage_view: Optional[str] = Query(
        None,
        description="all | agency | client — candidate pipeline visibility only",
    ),
):
    from backend.app.services.recruitment_funnel_analytics import (
        build_recruitment_funnel_analytics,
    )

    db, tenant_id = db_tenant
    tenant_id_str = str(tenant_id)
    visibility = get_tenant_visibility(db, tenant_id_str)
    is_client = await is_client_tenant_for_list(db, tenant_id_str)
    scope_clause = repo_scope_clause(tenant_id_str, visibility, is_client_tenant=is_client)
    effective_stage_view = stage_view or ("client" if is_client else "all")
    dfrom = _parse_dt(date_from)
    dto = _parse_dt(date_to, end_of_day=True)

    pipe: Literal["candidate", "lead"] = "lead" if pipeline_type == "lead" else "candidate"

    stage_visible_fn = None
    if pipe == "candidate":

        def stage_visible_fn(code: str) -> bool:
            return _stage_visible_for_view(code, effective_stage_view)

    result = await build_recruitment_funnel_analytics(
        db,
        tenant_id=tenant_id_str,
        current_user=current_user,
        company_id=str(company_id).strip() if company_id else None,
        legacy_tenant=legacy_tenant,
        pipeline_type=pipe,
        module_key=str(module_key).strip(),
        explicit_funnel_id=str(funnel_id).strip() if funnel_id else None,
        scope_clause=scope_clause if pipe == "candidate" else None,
        date_from=dfrom,
        date_to=dto,
        by=by,
        stage_visible=stage_visible_fn,
    )

    resolve = result.resolve_result
    funnel_obj = result.funnel
    return {
        "period": {
            "from": dfrom.isoformat() if dfrom else None,
            "to": dto.isoformat() if dto else None,
        },
        "by": by,
        "pipeline_type": result.pipeline_type,
        "module_key": result.module_key,
        "company_id": result.company_id,
        "funnel_id": funnel_obj.id,
        "funnel_name": funnel_obj.name,
        "funnel_source": resolve.source,
        "analytics_scope": result.analytics_scope,
        "is_legacy_readonly": result.analytics_scope == "legacy_tenant",
        "excluded_unbound": result.excluded_unbound,
        "stages": result.stages,
    }


# ------- /by-manager -------
@router.get("/analytics/by-manager")
async def by_manager(
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    date_from: Optional[str] = Query(None, alias="from"),
    date_to: Optional[str] = Query(None, alias="to"),
    by: str = Query("created", pattern="^(created|updated)$"),
    stage_view: Optional[str] = Query(
        None,
        description="all | agency | client — режим отображения пайплайна по стадиям",
    ),
):
    db, tenant_id = db_tenant
    tenant_id_str = str(tenant_id)
    visibility = get_tenant_visibility(db, tenant_id_str)
    is_client = await is_client_tenant_for_list(db, tenant_id_str)
    scope_clause = repo_scope_clause(tenant_id_str, visibility, is_client_tenant=is_client)
    effective_stage_view = stage_view or ("client" if is_client else "all")
    dfrom = _parse_dt(date_from)
    dto = _parse_dt(date_to, end_of_day=True)

    # totals по менеджерам
    recruiter_alias = aliased(User)

    totals_stmt = (
        select(
            Candidate.manager,
            Candidate.recruiter_id,
            recruiter_alias.full_name.label("recruiter_name"),
            recruiter_alias.short_id.label("recruiter_short"),
            recruiter_alias.email.label("recruiter_email"),
            func.count(),
        )
        .select_from(Candidate)
        .join(recruiter_alias, recruiter_alias.id == Candidate.recruiter_id, isouter=True)
        .where(and_(Candidate.deleted_at.is_(None), scope_clause))
    )
    totals_stmt = _apply_period_filters(totals_stmt, dfrom, dto, by).group_by(
        Candidate.manager,
        Candidate.recruiter_id,
        recruiter_alias.full_name,
        recruiter_alias.short_id,
        recruiter_alias.email,
    )
    totals = (await db.execute(totals_stmt)).all()

    # распределение по стадиям на менеджера
    dist_stmt = (
        select(
            Candidate.manager,
            Candidate.recruiter_id,
            Candidate.stage,
            func.count(),
        )
        .select_from(Candidate)
        .where(and_(Candidate.deleted_at.is_(None), scope_clause))
    )
    dist_stmt = _apply_period_filters(dist_stmt, dfrom, dto, by).group_by(
        Candidate.manager, Candidate.recruiter_id, Candidate.stage
    )
    dist = (await db.execute(dist_stmt)).all()

    by_mgr: Dict[str, Dict[str, Any]] = {}

    by_mgr: Dict[str, Dict[str, Any]] = {}

    def _resolve_label(
        manager_raw: Optional[str],
        recruiter_full: Optional[str],
        recruiter_short: Optional[str],
        recruiter_email: Optional[str],
        recruiter_id: Optional[str],
    ) -> str:
        if manager_raw:
            return manager_raw
        for val in (recruiter_full, recruiter_short, recruiter_email, recruiter_id):
            if val and str(val).strip():
                return str(val).strip()
        return "—"

    def _key(manager_raw: Optional[str], recruiter_id: Optional[str]) -> str:
        return manager_raw or recruiter_id or "—"

    for mgr, recruiter_id, recruiter_name, recruiter_short, recruiter_email, cnt in totals:
        key = _key(mgr, recruiter_id)
        label = _resolve_label(mgr, recruiter_name, recruiter_short, recruiter_email, recruiter_id)
        # G-6 Stage 2c — surface the canonical ``users.id`` (when the row
        # already hit G-5's shadow-write) so UI drill-downs can build
        # ``/app/candidates?recruiter_id=<uuid>`` without a second lookup.
        # Legacy rows (only ``Candidate.manager`` string, no FK) still
        # show up with ``recruiter_id=null`` and drill-down via the
        # legacy ``?manager=<label>`` path.
        by_mgr[key] = {
            "manager": label,
            "recruiter_id": str(recruiter_id) if recruiter_id else None,
            "total": int(cnt),
            "by_stage": {},
            "hired": 0,
        }

    for mgr, recruiter_id, stage, cnt in dist:
        key = _key(mgr, recruiter_id)
        if key not in by_mgr:
            label = _resolve_label(mgr, None, None, None, recruiter_id)
            by_mgr[key] = {
                "manager": label,
                "recruiter_id": str(recruiter_id) if recruiter_id else None,
                "total": 0,
                "by_stage": {},
                "hired": 0,
            }
        stage_name = stage.value if isinstance(stage, CandidateStage) else str(stage)
        if not _stage_visible_for_view(stage_name, effective_stage_view):
            continue
        by_mgr[key]["by_stage"][stage_name] = int(cnt)
        if _is_hired_stage_value(stage):
            by_mgr[key]["hired"] += int(cnt)

    # чтобы были все стадии в словаре by_stage (с нулями)
    for v in by_mgr.values():
        for st in CandidateStage:
            if not _stage_visible_for_view(st.value, effective_stage_view):
                continue
            v["by_stage"].setdefault(st.value, 0)

    items = sorted(by_mgr.values(), key=lambda x: (-x["total"], x["manager"]))
    return {
        "period": {
            "from": dfrom.isoformat() if dfrom else None,
            "to": dto.isoformat() if dto else None,
        },
        "by": by,
        "items": items,
    }


# ------- /analytics/handoff-stats -------
@router.get("/analytics/handoff-stats")
async def handoff_stats(
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    date_from: Optional[str] = Query(None, alias="from"),
    date_to: Optional[str] = Query(None, alias="to"),
):
    """Aggregate handoff stats: for agency by agency_tenant_id, for client by client_tenant_id / client_company_id (requested_at in period)."""
    db, tenant_id = db_tenant
    tenant_id_str = str(tenant_id)
    dfrom = _parse_dt(date_from)
    dto = _parse_dt(date_to, end_of_day=True)

    is_client = await is_client_tenant_for_list(db, tenant_id_str)
    if is_client:
        client_company_subq = select(TenantLink.handoff_include_company_id).where(
            TenantLink.client_tenant_id == tenant_id_str,
            TenantLink.handoff_include_company_id.isnot(None),
        )
        base = select(CandidateHandoff).where(
            or_(
                CandidateHandoff.client_tenant_id == tenant_id_str,
                CandidateHandoff.client_company_id.in_(client_company_subq),
            )
        )
    else:
        base = select(CandidateHandoff).where(
            CandidateHandoff.agency_tenant_id == tenant_id_str,
        )
    if dfrom:
        base = base.where(CandidateHandoff.requested_at >= dfrom)
    if dto:
        base = base.where(CandidateHandoff.requested_at <= dto)

    rows = (await db.execute(base)).scalars().all()

    total_requested = len(rows)
    total_accepted = sum(1 for h in rows if h.status == "accepted")
    total_rejected = sum(1 for h in rows if h.status == "rejected")
    total_returned = sum(1 for h in rows if h.status == "returned")

    by_client: Dict[str, Dict[str, int]] = {}
    for h in rows:
        key = h.client_tenant_id or h.client_company_id or "unknown"
        if key not in by_client:
            by_client[key] = {"requested": 0, "accepted": 0, "rejected": 0, "returned": 0}
        by_client[key]["requested"] += 1
        if h.status == "accepted":
            by_client[key]["accepted"] += 1
        elif h.status == "rejected":
            by_client[key]["rejected"] += 1
        elif h.status == "returned":
            by_client[key]["returned"] += 1

    return {
        "total_requested": total_requested,
        "total_accepted": total_accepted,
        "total_rejected": total_rejected,
        "total_returned": total_returned,
        "by_client": [{"client_id": k, **v} for k, v in by_client.items()],
        "period": {
            "from": dfrom.isoformat() if dfrom else None,
            "to": dto.isoformat() if dto else None,
        },
    }


# ------- /analytics/contact-attempt-stats -------
@router.get("/analytics/contact-attempt-stats")
async def contact_attempt_stats(
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    date_from: Optional[str] = Query(None, alias="from"),
    date_to: Optional[str] = Query(None, alias="to"),
):
    """Aggregate contact attempt stats for candidates in tenant (filter by candidate created_at)."""
    db, tenant_id = db_tenant
    tenant_id_str = str(tenant_id)
    visibility = get_tenant_visibility(db, tenant_id_str)
    is_client = await is_client_tenant_for_list(db, tenant_id_str)
    scope_clause = repo_scope_clause(tenant_id_str, visibility, is_client_tenant=is_client)
    dfrom = _parse_dt(date_from)
    dto = _parse_dt(date_to, end_of_day=True)

    cand_subq = (
        select(Candidate.id)
        .where(and_(Candidate.deleted_at.is_(None), scope_clause))
    )
    if dfrom:
        cand_subq = cand_subq.where(Candidate.created_at >= dfrom)
    if dto:
        cand_subq = cand_subq.where(Candidate.created_at <= dto)

    attempts_stmt = (
        select(ContactAttempt.candidate_id, ContactAttempt.result, func.count())
        .where(ContactAttempt.candidate_id.in_(cand_subq.scalar_subquery()))
        .group_by(ContactAttempt.candidate_id, ContactAttempt.result)
    )
    attempt_rows = (await db.execute(attempts_stmt)).all()

    total_attempts = sum(cnt for _, _, cnt in attempt_rows)
    by_result: Dict[str, int] = {}
    cand_attempt_counts: Dict[str, int] = {}
    for cand_id, result, cnt in attempt_rows:
        by_result[result] = by_result.get(result, 0) + cnt
        cand_attempt_counts[cand_id] = cand_attempt_counts.get(cand_id, 0) + cnt

    candidates_with_attempts = len(cand_attempt_counts)
    avg_per_candidate = (
        total_attempts / candidates_with_attempts if candidates_with_attempts else 0
    )
    limit_reached_count = sum(1 for c in cand_attempt_counts.values() if c >= 3)

    return {
        "total_attempts": total_attempts,
        "candidates_with_attempts": candidates_with_attempts,
        "avg_per_candidate": round(avg_per_candidate, 2),
        "limit_reached_count": limit_reached_count,
        "by_result": by_result,
        "period": {
            "from": dfrom.isoformat() if dfrom else None,
            "to": dto.isoformat() if dto else None,
        },
    }


# ------- /analytics/document-stats -------
@router.get("/analytics/document-stats")
async def document_stats(
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    date_from: Optional[str] = Query(None, alias="from"),
    date_to: Optional[str] = Query(None, alias="to"),
    company_id: Optional[str] = Query(
        None,
        alias="company_id",
        description="Optional client/company filter (Candidate.company_id).",
    ),
    vacancy_id: Optional[str] = Query(
        None,
        alias="vacancy_id",
        description="Optional vacancy filter (Candidate.vacancy_id).",
    ),
):
    """Aggregate document stats for candidates in tenant (filter by candidate created_at)."""
    db, tenant_id = db_tenant
    tenant_id_str = str(tenant_id)
    visibility = get_tenant_visibility(db, tenant_id_str)
    is_client = await is_client_tenant_for_list(db, tenant_id_str)
    scope_clause = repo_scope_clause(tenant_id_str, visibility, is_client_tenant=is_client)
    dfrom = _parse_dt(date_from)
    dto = _parse_dt(date_to, end_of_day=True)
    company_filter = str(company_id).strip() if company_id else ""
    vacancy_filter = str(vacancy_id).strip() if vacancy_id else ""

    cand_subq = (
        select(Candidate.id)
        .where(and_(Candidate.deleted_at.is_(None), scope_clause))
    )
    if dfrom:
        cand_subq = cand_subq.where(Candidate.created_at >= dfrom)
    if dto:
        cand_subq = cand_subq.where(Candidate.created_at <= dto)
    if company_filter:
        cand_subq = cand_subq.where(Candidate.company_id == company_filter)
    if vacancy_filter:
        cand_subq = cand_subq.where(Candidate.vacancy_id == vacancy_filter)

    docs_stmt = (
        select(Document.status, Document.kind, Document.candidate_id)
        .where(Document.tenant_id == tenant_id_str)
        .where(Document.candidate_id.in_(cand_subq.scalar_subquery()))
        .where(Document.deleted_at.is_(None))
    )
    doc_rows = (await db.execute(docs_stmt)).all()

    by_status: Dict[str, int] = {}
    by_kind: Dict[str, int] = {}
    total_docs = 0
    ready_statuses = {"completed", "approved", "received", "delivered", "verified"}
    candidates_with_complete: set[str] = set()
    cand_doc_statuses: Dict[str, set[str]] = {}

    for status, kind, cand_id in doc_rows:
        s = str(status.value) if hasattr(status, "value") else str(status)
        k = str(kind.value) if hasattr(kind, "value") else str(kind)
        by_status[s] = by_status.get(s, 0) + 1
        by_kind[k] = by_kind.get(k, 0) + 1
        total_docs += 1
        if cand_id not in cand_doc_statuses:
            cand_doc_statuses[cand_id] = set()
        cand_doc_statuses[cand_id].add(s)

    for cand_id, statuses in cand_doc_statuses.items():
        if any(st in ready_statuses for st in statuses):
            candidates_with_complete.add(cand_id)

    return {
        "total_docs": total_docs,
        "by_status": by_status,
        "by_kind": by_kind,
        "candidates_with_complete_docs": len(candidates_with_complete),
        "period": {
            "from": dfrom.isoformat() if dfrom else None,
            "to": dto.isoformat() if dto else None,
        },
    }


# ------- /analytics/document-runtime-kpis (Track B) -------
@router.get("/analytics/document-runtime-kpis")
async def document_runtime_kpis(
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    date_from: Optional[str] = Query(None, alias="from"),
    date_to: Optional[str] = Query(None, alias="to"),
):
    """Aggregate document_runtime_v1 checklist KPIs for dashboard tiles."""
    from backend.app.document_runtime.dashboard_projection import (
        aggregate_runtime_items_to_kpis,
        build_dashboard_kpi_payload,
        extract_runtime_items_from_hub_section,
    )
    from backend.app.document_runtime.kpi_predicates import empty_dashboard_kpi_counts
    from backend.app.services.document_hub_delivery_contract import (
        evaluate_document_hub_requirements_via_contract,
    )

    db, tenant_id = db_tenant
    tenant_id_str = str(tenant_id)
    visibility = get_tenant_visibility(db, tenant_id_str)
    is_client = await is_client_tenant_for_list(db, tenant_id_str)
    scope_clause = repo_scope_clause(tenant_id_str, visibility, is_client_tenant=is_client)
    dfrom = _parse_dt(date_from)
    dto = _parse_dt(date_to, end_of_day=True)

    cand_stmt = select(Candidate).where(and_(Candidate.deleted_at.is_(None), scope_clause))
    if dfrom:
        cand_stmt = cand_stmt.where(Candidate.created_at >= dfrom)
    if dto:
        cand_stmt = cand_stmt.where(Candidate.created_at <= dto)

    candidates = (await db.execute(cand_stmt)).scalars().all()
    kpis = empty_dashboard_kpi_counts()
    runtime_candidates = 0
    runtime_items_scanned = 0
    all_items: list[dict[str, Any]] = []

    for candidate in candidates:
        hub = await evaluate_document_hub_requirements_via_contract(
            db,
            tenant_id=tenant_id_str,
            candidate=candidate,
        )
        if not hub or not hub.get("applied"):
            continue
        runtime_candidates += 1
        items = extract_runtime_items_from_hub_section(hub)
        all_items.extend(items)
        runtime_items_scanned += len(items)

    if all_items:
        kpis = aggregate_runtime_items_to_kpis(all_items)

    source = "runtime" if runtime_items_scanned > 0 else "no_runtime"
    period = {
        "from": dfrom.isoformat() if dfrom else None,
        "to": dto.isoformat() if dto else None,
    }
    return build_dashboard_kpi_payload(
        kpis=kpis,
        candidates_scanned=len(candidates),
        runtime_candidates=runtime_candidates,
        runtime_items_scanned=runtime_items_scanned,
        source=source,
        period=period,
    )


# ------- /analytics/export (оставим простой CSV-дашьборд) -------
@router.get("/analytics/export")
async def analytics_export(
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    stage_view: Optional[str] = Query(
        None,
        description="all | agency | client — режим отображения пайплайна по стадиям",
    ),
):
    db, tenant_id = db_tenant
    import csv
    import io

    tenant_id_str = str(tenant_id)
    visibility = get_tenant_visibility(db, tenant_id_str)
    is_client = await is_client_tenant_for_list(db, tenant_id_str)
    scope_clause = repo_scope_clause(tenant_id_str, visibility, is_client_tenant=is_client)
    effective_stage_view = stage_view or ("client" if is_client else "all")

    total = (await db.execute(select(func.count()).select_from(Candidate).where(and_(Candidate.deleted_at.is_(None), scope_clause)))).scalar_one()
    stage_rows = (
        await db.execute(
            select(Candidate.stage, func.count()).where(and_(Candidate.deleted_at.is_(None), scope_clause)).group_by(Candidate.stage)
        )
    ).all()

    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["total", total])
    w.writerow([])
    w.writerow(["stage", "count"])
    for s, cnt in stage_rows:
        name = s.value if isinstance(s, CandidateStage) else str(s)
        if not _stage_visible_for_view(name, effective_stage_view):
            continue
        w.writerow([name, int(cnt)])

    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=analytics.csv"},
    )


# ------- /analytics/candidate-slices -------
@router.get("/analytics/candidate-slices")
async def candidate_slices(
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    date_from: Optional[str] = Query(None, alias="from"),
    date_to: Optional[str] = Query(None, alias="to"),
    by: str = Query(
        "created",
        pattern="^(created|updated)$",
        description="created|updated — по какому полю фильтровать",
    ),
    stages: Optional[List[str]] = Query(
        None,
        description="Список стадий через запятую/повтор параметра (codes).",
    ),
    vacancy_id: Optional[List[str]] = Query(
        None,
        alias="vacancy_id",
        description="ID вакансии (можно несколько: повторить параметр или передать через запятую).",
    ),
    company_id: Optional[List[str]] = Query(
        None,
        alias="company_id",
        description="ID компании (можно несколько).",
    ),
    manager_id: Optional[List[str]] = Query(
        None,
        alias="manager_id",
        description="ID менеджера (user_id или manager field, можно несколько).",
    ),
    candidate_id: Optional[str] = Query(
        None,
        alias="candidate_id",
        description="Один UUID кандидата — сузить срез до этой записи.",
    ),
    limit: int = Query(
        20,
        ge=5,
        le=200,
        description="Максимальное число строк в агрегированных таблицах.",
    ),
    scope_tenant_id: Optional[UUID] = Query(
        None,
        description="Scope to this tenant (same as list); uses X-Tenant-Id if not set.",
    ),
    stage_view: Optional[str] = Query(
        None,
        description="all | agency | client — режим отображения пайплайна по стадиям",
    ),
):
    db, tenant_id = db_tenant
    tenant_id_str = str(tenant_id)
    scope_tenant = str(scope_tenant_id) if scope_tenant_id else tenant_id_str

    stage_filters: list[str] = []
    if stages:
        for value in stages:
            if not value:
                continue
            parts = [p.strip() for p in value.split(",") if p and p.strip()]
            stage_filters.extend(parts)
    vacancy_filters: list[str] = []
    if vacancy_id:
        for value in vacancy_id:
            if not value:
                continue
            parts = [p.strip() for p in value.split(",") if p and p.strip()]
            vacancy_filters.extend(parts)
    company_filters: list[str] = []
    if company_id:
        for value in company_id:
            if not value:
                continue
            parts = [p.strip() for p in value.split(",") if p and p.strip()]
            company_filters.extend(parts)
    manager_filters: list[str] = []
    if manager_id:
        for value in manager_id:
            if not value:
                continue
            parts = [p.strip() for p in value.split(",") if p and p.strip()]
            manager_filters.extend(parts)

    cand_one = (candidate_id or "").strip()
    if cand_one:
        try:
            UUID(cand_one)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="invalid candidate_id") from exc

    cache_params = {
        "from": date_from,
        "to": date_to,
        "by": by,
        "scope_tenant": scope_tenant,
        "stages": ",".join(sorted(stage_filters)) if stage_filters else "",
        "vacancy_id": ",".join(sorted(vacancy_filters)) if vacancy_filters else "",
        "company_id": ",".join(sorted(company_filters)) if company_filters else "",
        "manager_id": ",".join(sorted(manager_filters)) if manager_filters else "",
        "candidate_id": cand_one,
        "limit": limit,
    }
    cached = await cache_get("candidate-slices", scope_tenant, cache_params)
    if cached is not None:
        return cached

    try:
        await db.execute(
            text("SELECT set_config('app.tenant_id', :tid, true)"),
            {"tid": scope_tenant},
        )
    except Exception:
        pass
    visibility = get_tenant_visibility(db, scope_tenant)
    client_tenant = await is_client_tenant_for_list(db, scope_tenant)
    scope_clause = repo_scope_clause(scope_tenant, visibility, is_client_tenant=client_tenant)
    effective_stage_view = stage_view or ("client" if client_tenant else "all")
    dfrom = _parse_dt(date_from)
    dto = _parse_dt(date_to, end_of_day=True)

    manager_alias = aliased(User)
    recruiter_alias = aliased(User)

    stmt = (
        select(
            Candidate.id,
            Candidate.stage,
            Candidate.status_reason,
            Candidate.source,
            Candidate.extra,
            Candidate.personal_data,
            Candidate.origin,
            Candidate.manager,
            Candidate.recruiter_id,
            Candidate.created_at,
            Candidate.updated_at,
            Candidate.company_id,
            Company.name.label("company_name"),
            Candidate.vacancy_id,
            Vacancy.title.label("vacancy_title"),
            recruiter_alias.full_name.label("recruiter_name"),
            recruiter_alias.short_id.label("recruiter_short"),
            recruiter_alias.email.label("recruiter_email"),
            manager_alias.full_name.label("manager_full"),
            manager_alias.short_id.label("manager_short"),
            manager_alias.email.label("manager_email"),
        )
        .select_from(Candidate)
        .outerjoin(Company, Candidate.company_id == Company.id)
        .outerjoin(Vacancy, Candidate.vacancy_id == Vacancy.id)
        .outerjoin(recruiter_alias, recruiter_alias.id == Candidate.recruiter_id)
        .outerjoin(manager_alias, manager_alias.id == Candidate.manager)
        .where(and_(Candidate.deleted_at.is_(None), scope_clause))
    )
    
    # Фильтрация тестовых данных: исключаем компании и вакансии с "test", "тест", "demo" в названии
    test_patterns = ["test", "тест", "demo", "демо"]
    test_filters = []
    for pattern in test_patterns:
        test_filters.append(func.lower(Company.name).like(f"%{pattern}%"))
        test_filters.append(func.lower(Vacancy.title).like(f"%{pattern}%"))
    if test_filters:
        from sqlalchemy import not_ as sql_not
        test_condition = sql_not(or_(*test_filters))
        stmt = stmt.where(test_condition)
    
    stmt = _apply_period_filters(stmt, dfrom, dto, by)

    if stage_filters:
        stmt = stmt.where(Candidate.stage.in_(stage_filters))
    if vacancy_filters:
        stmt = stmt.where(Candidate.vacancy_id.in_(vacancy_filters))
    if company_filters:
        stmt = stmt.where(Candidate.company_id.in_(company_filters))
    if manager_filters:
        stmt = stmt.where(
            or_(
                Candidate.manager.in_(manager_filters),
                Candidate.recruiter_id.in_(manager_filters),
            )
        )
    if cand_one:
        stmt = stmt.where(Candidate.id == cand_one)

    rows = (await db.execute(stmt)).all()

    # Счётчики стадий считаем по коду, а не по русской метке,
    # чтобы фронтенд мог тянуть переводы из i18n (app.candidates.stage_labels).
    stage_counter: Counter[str] = Counter()
    company_counter: Counter[str] = Counter()
    vacancy_counter: Counter[str] = Counter()
    company_labels: Dict[str, str] = {}
    vacancy_labels: Dict[str, str] = {}
    source_counter: Counter[str] = Counter()
    citizenship_counter: Counter[str] = Counter()
    country_counter: Counter[str] = Counter()
    company_stage_breakdown: Dict[str, Counter[str]] = defaultdict(Counter)
    vacancy_stage_breakdown: Dict[str, Counter[str]] = defaultdict(Counter)
    reason_counters: Dict[str, Counter[str]] = {
        "rejected": Counter(),
        "declined": Counter(),
    }

    snapshot: List[Dict[str, Any]] = []

    def _label(value: Optional[str]) -> str:
        return str(value).strip() if value else "—"

    def _source_label(value: Optional[str]) -> str:
        normalized = normalize_candidate_source(value)
        if normalized:
            return normalized
        return _label(value)

    def _maybe(value: Optional[str]) -> Optional[str]:
        lbl = _label(value)
        return lbl if lbl != "—" else None

    allowed_reason_stages = {"rejected", "declined"}

    for row in rows:
        (
            candidate_id,
            stage_code,
            status_reason_raw,
            source,
            extra_raw,
            personal_data_raw,
            origin_raw,
            manager_raw,
            recruiter_id,
            created_at,
            updated_at,
            company_id,
            company_name,
            vacancy_id,
            vacancy_title,
            recruiter_name,
            recruiter_short,
            recruiter_email,
            manager_full,
            manager_short,
            manager_email,
        ) = row

        stage_code_raw = stage_code or None
        stage_norm = _normalize_stage_counter_key(stage_code_raw) or stage_code_raw
        stage_label = _stage_label(stage_norm)

        origin_payload = _safe_dict(origin_raw)
        origin_hint = None
        if isinstance(origin_payload.get("source"), str):
            origin_hint = origin_payload["source"]
        elif origin_payload:
            origin_hint = next(iter(origin_payload.keys()), None)
        normalized_source = normalize_candidate_source(source or origin_hint)
        source_label = normalized_source or (_label(source) if source else "—")

        extra_payload = _safe_dict(extra_raw)
        personal_data = _safe_dict(personal_data_raw)
        citizenship = personal_data.get("citizenship") or extra_payload.get("citizenship")
        country = (
            personal_data.get("country")
            or personal_data.get("country_code")
            or extra_payload.get("country")
            or extra_payload.get("country_code")
        )

        reason_codes = _status_reason_list(status_reason_raw)
        reason_stage = stage_norm if stage_norm in allowed_reason_stages else None
        reason_labels: list[str] = []
        if reason_stage:
            label_map = _REASON_LABELS.get(reason_stage, {})
            dedup: list[tuple[str, str]] = []
            seen_codes: set[str] = set()
            for rcode in reason_codes:
                if rcode in seen_codes:
                    continue
                seen_codes.add(rcode)
                label = label_map.get(rcode, rcode)
                dedup.append((rcode, label))
            if dedup:
                reason_labels = [lbl for _, lbl in dedup]
            else:
                reason_labels = ["Без причины"]

        manager_preferred = manager_full or manager_short or manager_email or manager_raw
        final_manager_label = manager_preferred or None

        stage_visible = _stage_visible_for_view(stage_norm, effective_stage_view)
        if not stage_visible:
            snapshot.append(
                {
                    "id": str(candidate_id),
                    "stage": stage_code_raw,
                    "stage_label": stage_label,
                    "company": _maybe(company_name),
                    "company_id": str(company_id) if company_id else None,
                    "vacancy": _maybe(vacancy_title or company_name),
                    "vacancy_id": str(vacancy_id) if vacancy_id else None,
                    "source": source_label if source_label != "—" else None,
                    "manager": final_manager_label or None,
                    "manager_name": manager_full or None,
                    "manager_short": manager_short or None,
                    "manager_email": manager_email or None,
                    "manager_id": manager_raw,
                    "recruiter_id": recruiter_id,
                    "recruiter_name": recruiter_name or None,
                    "recruiter_short": recruiter_short or None,
                    "recruiter_email": recruiter_email or None,
                    "citizenship": _maybe(citizenship),
                    "country": _maybe(country),
                    "status_reason_codes": reason_codes,
                    "status_reason_labels": reason_labels,
                    "reason_stage": reason_stage,
                    "reason_stage_label": _stage_label(reason_stage) if reason_stage else None,
                    "created_at": created_at.isoformat() if hasattr(created_at, "isoformat") else created_at,
                    "updated_at": updated_at.isoformat() if hasattr(updated_at, "isoformat") else updated_at,
                }
            )
            continue

        # Считаем по каноническому коду (employed / employment_pending / …), не по legacy-меткам.
        counter_key = str(stage_norm) if stage_norm else stage_label
        stage_counter[counter_key] += 1

        company_label = _label(company_name)
        company_key = str(company_id) if company_id else f"label::{company_label}"
        vacancy_label = _label(vacancy_title or company_name)
        vacancy_key = str(vacancy_id) if vacancy_id else f"label::{vacancy_label}"

        company_counter[company_key] += 1
        vacancy_counter[vacancy_key] += 1
        company_labels[company_key] = company_label
        vacancy_labels[vacancy_key] = vacancy_label
        source_counter[source_label] += 1

        company_stage_breakdown[company_key][counter_key] += 1
        vacancy_stage_breakdown[vacancy_key][counter_key] += 1

        citizenship_counter[_label(citizenship)] += 1
        country_counter[_label(country)] += 1

        if reason_stage:
            label_map = _REASON_LABELS.get(reason_stage, {})
            dedup = []
            seen_codes = set()
            for rcode in reason_codes:
                if rcode in seen_codes:
                    continue
                seen_codes.add(rcode)
                label = label_map.get(rcode, rcode)
                dedup.append((rcode, label))
            if dedup:
                for _, label in dedup:
                    reason_counters[reason_stage][label] += 1
            else:
                reason_counters[reason_stage]["Без причины"] += 1

        snapshot.append(
            {
                "id": str(candidate_id),
                "stage": stage_code_raw,
                "stage_label": stage_label,
                "company": _maybe(company_name),
                "company_id": str(company_id) if company_id else None,
                "vacancy": _maybe(vacancy_title or company_name),
                "vacancy_id": str(vacancy_id) if vacancy_id else None,
                "source": source_label if source_label != "—" else None,
                "manager": final_manager_label or None,
                "manager_name": manager_full or None,
                "manager_short": manager_short or None,
                "manager_email": manager_email or None,
                "manager_id": manager_raw,
                "recruiter_id": recruiter_id,
                "recruiter_name": recruiter_name or None,
                "recruiter_short": recruiter_short or None,
                "recruiter_email": recruiter_email or None,
                "citizenship": _maybe(citizenship),
                "country": _maybe(country),
                "status_reason_codes": reason_codes,
                "status_reason_labels": reason_labels,
                "reason_stage": reason_stage,
                "reason_stage_label": _stage_label(reason_stage) if reason_stage else None,
                "created_at": created_at.isoformat() if hasattr(created_at, "isoformat") else created_at,
                "updated_at": updated_at.isoformat() if hasattr(updated_at, "isoformat") else updated_at,
            }
        )

    def _top(counter: Counter[str], top_limit: int) -> List[Dict[str, Any]]:
        items = sorted(counter.items(), key=lambda kv: (-kv[1], kv[0]))
        return [
            {"key": key, "label": key, "count": int(count)}
            for key, count in items[:top_limit]
        ]

    def _grouped(
        counter: Counter[str],
        breakdowns: Dict[str, Counter[str]],
        labels: Dict[str, str],
        top_limit: int,
    ):
        items = sorted(counter.items(), key=lambda kv: (-kv[1], kv[0]))[:top_limit]
        result: List[Dict[str, Any]] = []
        for key, total in items:
            stage_counts = breakdowns.get(key, {})
            breakdown = {
                _stage_label(stage_code): int(stage_counts.get(stage_code, 0))
                for stage_code in STAGE_ORDER
                if stage_counts.get(stage_code)
            }
            result.append(
                {
                    "key": key,
                    "label": labels.get(key, key),
                    "count": int(total),
                    "by_stage": breakdown,
                }
            )
        return result

    top_limit = max(5, min(limit, 200))
    list_limit = max(10, min(limit * 2, 200))

    ordered_stage_set = set(STAGE_ORDER)
    stage_rows: List[Dict[str, Any]] = []
    for code in STAGE_ORDER:
        if not _stage_visible_for_view(code, effective_stage_view):
            continue
        count = int(stage_counter.get(code, 0))
        if count:
            stage_rows.append({"key": code, "label": _stage_label(code), "count": count})
    extra_stages = [
        (code, count)
        for code, count in stage_counter.items()
        if code not in ordered_stage_set
    ]
    stage_rows.extend(
        {"key": code, "label": _stage_label(code), "count": int(count)}
        for code, count in sorted(extra_stages, key=lambda kv: (-kv[1], kv[0]))
    )

    result = {
        "period": {
            "from": dfrom.isoformat() if dfrom else None,
            "to": dto.isoformat() if dto else None,
        },
        "by": by,
        "total": len(snapshot),
        "stages": stage_rows,
        "companies_total": len(company_counter),
        "vacancies_total": len(vacancy_counter),
        "companies": _grouped(company_counter, company_stage_breakdown, company_labels, top_limit),
        "vacancies": _grouped(vacancy_counter, vacancy_stage_breakdown, vacancy_labels, top_limit),
        "sources": _top(source_counter, list_limit),
        "citizenships": _top(citizenship_counter, list_limit),
        "countries": _top(country_counter, list_limit),
        "reasons": {
            key: _top(counter, list_limit)
            for key, counter in reason_counters.items()
        },
        "snapshot": snapshot,
    }
    await cache_set("candidate-slices", scope_tenant, cache_params, result, ttl_sec=300)
    return result


class AnalyticsEventIn(BaseModel):
    # Тип события:
    # - trial_retention_nudge: существующий трек для D1/D2/D3/D7 подсказок
    # - ttv_step: новый трек для замеров Time To Value (ключевые шаги онбординга)
    event: Literal["trial_retention_nudge", "ttv_step", "perf"]
    # Действие над событием:
    # - impression/cta_click/dismiss — как раньше
    # - completed — новый action для фиксации завершения шага TTV
    action: Literal["impression", "cta_click", "dismiss", "completed", "measured"]
    # Для trial_retention_nudge:
    day_bucket: Optional[Literal["d1", "d2", "d3", "d7"]] = None
    # Для ttv_step:
    #   signup, plan_selected, company_created, first_client_created,
    #   first_candidate_created, email_connected, first_email_sent
    step_key: Optional[str] = None
    target_href: Optional[str] = None
    activation_done: Optional[bool] = None
    # For perf:
    metric_key: Optional[str] = None
    duration_ms: Optional[float] = None
    route: Optional[str] = None
    meta: Optional[dict[str, Any]] = None


class TrialRetentionBucketOut(BaseModel):
    day_bucket: str
    impression: int
    cta_click: int
    dismiss: int
    ctr_percent: float
    dismiss_percent: float


class TrialRetentionReportOut(BaseModel):
    period: dict[str, Optional[str]]
    totals: dict[str, float | int]
    buckets: list[TrialRetentionBucketOut]


class TtvStepDurationsOut(BaseModel):
    step_key: str
    samples: int
    p50_seconds: float
    p90_seconds: float
    min_seconds: float
    max_seconds: float


class TtvReportOut(BaseModel):
    period: dict[str, Optional[str]]
    actors: int
    steps: list[TtvStepDurationsOut]


class PerfBaselineRowOut(BaseModel):
    metric_key: str
    samples: int
    p50_ms: float
    p95_ms: float
    min_ms: float
    max_ms: float


class PerfBaselineOut(BaseModel):
    period: dict[str, Optional[str]]
    rows: list[PerfBaselineRowOut]


class PerfBudgetsOut(BaseModel):
    budgets_p95_ms: dict[str, float]


@router.post("/analytics/events")
async def post_analytics_event(
    payload: AnalyticsEventIn,
    user: UserCtx = Depends(get_current_user),
    db_tenant=Depends(get_db_with_tenant),
):
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    if str(user.tenant_id or "").strip() != tenant_id:
        return {"ok": False, "reason": "tenant_mismatch"}

    # Унифицированный action для ActivityLog
    action = f"analytics.{payload.event}.{payload.action}"
    event_payload: dict[str, Any] = {
        "event": payload.event,
        "action": payload.action,
        "day_bucket": payload.day_bucket,
        "step_key": payload.step_key,
        "target_href": payload.target_href,
        "activation_done": payload.activation_done,
        "metric_key": payload.metric_key,
        "duration_ms": payload.duration_ms,
        "route": payload.route,
        "meta": payload.meta,
    }

    await log_activity(
        db,
        tenant_id=tenant_id,
        actor_id=str(user.sub or "").strip() or None,
        action=action,
        target_type="analytics",
        payload={
            **event_payload,
        },
    )

    # Perf budgets: log an extra signal when a measurement breaches p95 budget.
    if payload.event == "perf" and payload.action == "measured":
        key = str(payload.metric_key or "").strip()
        if key and payload.duration_ms is not None:
            try:
                dms = float(payload.duration_ms)
            except Exception:
                dms = -1.0
            budget = PERF_BUDGETS_P95_MS.get(key)
            if budget is not None and dms >= 0 and dms > float(budget):
                await log_activity(
                    db,
                    tenant_id=tenant_id,
                    actor_id=str(user.sub or "").strip() or None,
                    action="analytics.perf.budget_breached",
                    target_type="analytics",
                    payload={
                        "metric_key": key,
                        "duration_ms": dms,
                        "budget_p95_ms": float(budget),
                        "route": payload.route,
                    },
                )
    await db.commit()
    return {"ok": True}


@router.get("/analytics/trial-retention", response_model=TrialRetentionReportOut)
async def get_trial_retention_report(
    days: int = Query(30, ge=1, le=180),
    db_tenant=Depends(get_db_with_tenant),
):
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    now = datetime.utcnow()
    since = now - timedelta(days=days)
    actions = [
        "analytics.trial_retention_nudge.impression",
        "analytics.trial_retention_nudge.cta_click",
        "analytics.trial_retention_nudge.dismiss",
    ]
    rows = (
        await db.execute(
            select(ActivityLog.action, ActivityLog.payload, ActivityLog.created_at)
            .where(
                ActivityLog.tenant_id == tenant_id,
                ActivityLog.action.in_(actions),
                ActivityLog.created_at >= since,
            )
            .order_by(ActivityLog.created_at.desc())
        )
    ).all()

    counters: dict[str, Counter[str]] = {
        "d1": Counter(),
        "d2": Counter(),
        "d3": Counter(),
        "d7": Counter(),
    }
    valid_days = set(counters.keys())
    for action, raw_payload, _created_at in rows:
        payload_dict = _safe_dict(raw_payload)
        day_bucket = str(payload_dict.get("day_bucket") or "").strip().lower()
        if day_bucket not in valid_days:
            continue
        event_action = str(payload_dict.get("action") or "").strip().lower()
        if event_action not in {"impression", "cta_click", "dismiss"}:
            action_str = str(action or "").strip().lower()
            if action_str.endswith(".impression"):
                event_action = "impression"
            elif action_str.endswith(".cta_click"):
                event_action = "cta_click"
            elif action_str.endswith(".dismiss"):
                event_action = "dismiss"
        if event_action not in {"impression", "cta_click", "dismiss"}:
            continue
        counters[day_bucket][event_action] += 1

    buckets: list[TrialRetentionBucketOut] = []
    total_impression = 0
    total_cta = 0
    total_dismiss = 0
    for day_bucket in ("d1", "d2", "d3", "d7"):
        row = counters[day_bucket]
        impression = int(row.get("impression", 0))
        cta_click = int(row.get("cta_click", 0))
        dismiss = int(row.get("dismiss", 0))
        total_impression += impression
        total_cta += cta_click
        total_dismiss += dismiss
        ctr_percent = round((cta_click / impression) * 100.0, 2) if impression > 0 else 0.0
        dismiss_percent = round((dismiss / impression) * 100.0, 2) if impression > 0 else 0.0
        buckets.append(
            TrialRetentionBucketOut(
                day_bucket=day_bucket,
                impression=impression,
                cta_click=cta_click,
                dismiss=dismiss,
                ctr_percent=ctr_percent,
                dismiss_percent=dismiss_percent,
            )
        )

    totals_ctr = round((total_cta / total_impression) * 100.0, 2) if total_impression > 0 else 0.0
    return TrialRetentionReportOut(
        period={
            "from": since.isoformat(),
            "to": now.isoformat(),
        },
        totals={
            "impression": total_impression,
            "cta_click": total_cta,
            "dismiss": total_dismiss,
            "ctr_percent": totals_ctr,
        },
        buckets=buckets,
    )


@router.get("/analytics/perf-baseline", response_model=PerfBaselineOut)
async def get_perf_baseline(
    days: int = Query(14, ge=1, le=180),
    limit: int = Query(50, ge=5, le=500),
    db_tenant=Depends(get_db_with_tenant),
):
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    now = datetime.utcnow()
    since = now - timedelta(days=days)

    rows = (
        await db.execute(
            select(ActivityLog.payload)
            .where(
                ActivityLog.tenant_id == tenant_id,
                ActivityLog.action == "analytics.perf.measured",
                ActivityLog.created_at >= since,
            )
        )
    ).all()

    by_key: dict[str, list[float]] = defaultdict(list)
    for (raw_payload,) in rows:
        payload = _safe_dict(raw_payload)
        key = str(payload.get("metric_key") or "").strip()
        if not key:
            continue
        dur = payload.get("duration_ms")
        try:
            d = float(dur)
        except Exception:
            continue
        if d < 0:
            continue
        by_key[key].append(d)

    out_rows: list[PerfBaselineRowOut] = []
    for key, vals in by_key.items():
        if not vals:
            continue
        vals_sorted = sorted(vals)
        out_rows.append(
            PerfBaselineRowOut(
                metric_key=key,
                samples=len(vals_sorted),
                p50_ms=round(_percentile(vals_sorted, 0.5), 1),
                p95_ms=round(_percentile(vals_sorted, 0.95), 1),
                min_ms=round(float(vals_sorted[0]), 1),
                max_ms=round(float(vals_sorted[-1]), 1),
            )
        )
    out_rows.sort(key=lambda r: (-r.p95_ms, -r.samples, r.metric_key))
    out_rows = out_rows[:limit]
    return PerfBaselineOut(
        period={
            "from": since.isoformat(),
            "to": now.isoformat(),
        },
        rows=out_rows,
    )


@router.get("/analytics/perf-budgets", response_model=PerfBudgetsOut)
async def get_perf_budgets():
    return PerfBudgetsOut(budgets_p95_ms={k: float(v) for k, v in PERF_BUDGETS_P95_MS.items()})


@router.get("/analytics/ttv-report", response_model=TtvReportOut)
async def get_ttv_report(
    days: int = Query(30, ge=1, le=180),
    db_tenant=Depends(get_db_with_tenant),
):
    """
    Отчет по Time To Value на основе событий analytics.ttv_step.completed.

    Для каждого пользователя (actor_id) ищем времена завершения шагов TTV (step_key),
    затем считаем дельты в секундах от момента signup до каждого шага и агрегируем
    по всему tenant: p50/p90/min/max и количество сэмплов.
    """
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    now = datetime.utcnow()
    since = now - timedelta(days=days)

    rows = (
        await db.execute(
            select(
                ActivityLog.actor_id,
                ActivityLog.action,
                ActivityLog.payload,
                ActivityLog.created_at,
            )
            .where(
                ActivityLog.tenant_id == tenant_id,
                ActivityLog.action == "analytics.ttv_step.completed",
                ActivityLog.created_at >= since,
            )
            .order_by(ActivityLog.created_at.asc())
        )
    ).all()

    # actor_id -> step_key -> first completed timestamp
    per_actor_steps: dict[str, dict[str, datetime]] = {}
    for actor_id, _action, raw_payload, created_at in rows:
        if not actor_id:
            continue
        payload_dict = _safe_dict(raw_payload)
        step_key = str(payload_dict.get("step_key") or "").strip()
        if not step_key:
            continue
        actor_key = str(actor_id)
        actor_map = per_actor_steps.setdefault(actor_key, {})
        # сохраняем самое раннее время завершения шага
        if step_key not in actor_map or created_at < actor_map[step_key]:
            actor_map[step_key] = created_at

    # считаем дельты от signup до каждого шага
    durations_by_step: dict[str, list[float]] = {}
    for _actor, steps in per_actor_steps.items():
        signup_at = steps.get("signup")
        if not signup_at:
            continue
        for step_key, ts in steps.items():
            if step_key == "signup":
                continue
            delta = max((ts - signup_at).total_seconds(), 0.0)
            durations_by_step.setdefault(step_key, []).append(delta)

    def _percentile(values: list[float], p: float) -> float:
        if not values:
            return 0.0
        sorted_vals = sorted(values)
        if len(sorted_vals) == 1:
            return float(sorted_vals[0])
        k = (len(sorted_vals) - 1) * p
        f = int(k)
        c = min(f + 1, len(sorted_vals) - 1)
        if f == c:
            return float(sorted_vals[f])
        d0 = sorted_vals[f] * (c - k)
        d1 = sorted_vals[c] * (k - f)
        return float(d0 + d1)

    steps_out: list[TtvStepDurationsOut] = []
    for step_key, values in sorted(durations_by_step.items()):
        if not values:
            continue
        steps_out.append(
            TtvStepDurationsOut(
                step_key=step_key,
                samples=len(values),
                p50_seconds=round(_percentile(values, 0.5), 2),
                p90_seconds=round(_percentile(values, 0.9), 2),
                min_seconds=round(min(values), 2),
                max_seconds=round(max(values), 2),
            )
        )

    return TtvReportOut(
        period={
            "from": since.isoformat(),
            "to": now.isoformat(),
        },
        actors=len(per_actor_steps),
        steps=steps_out,
    )


# --- Risk intelligence v1 (Phase A: read-only baseline / SSOT R3.4) ---


class RiskIntelStageAggOut(BaseModel):
    count: int
    avg_risk_score: float
    high_plus_count: int


class RiskIntelligenceOut(BaseModel):
    generated_at: datetime
    risk_version: str
    candidates_evaluated: int
    high_risk_volume: int
    avg_risk_score: float
    band_distribution: dict[str, int]
    risk_distribution_by_stage: dict[str, RiskIntelStageAggOut]
    first_response_hours_histogram: dict[str, int]
    effective_weights: dict[str, float]


@router.get("/analytics/risk-intelligence", response_model=RiskIntelligenceOut)
async def risk_intelligence(
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    ctx: UserCtx = Depends(get_current_user),
    limit: int = Query(5000, ge=50, le=15000, description="Max candidates scored (most recently updated first)"),
):
    """
    Read-only aggregate risk baseline for candidates (transparent weighted v1 model).
    Uses Tenant.settings.risk_model_v1 when present. Phase B: hourly rows via scheduler (ops roles only).
    """
    _require_risk_ops_lead(ctx)
    db, tenant_id = db_tenant
    tenant_id_str = str(tenant_id)
    visibility = get_tenant_visibility(db, tenant_id_str)
    is_client = await is_client_tenant_for_list(db, tenant_id_str)
    scope_clause = repo_scope_clause(tenant_id_str, visibility, is_client_tenant=is_client)

    raw = await compute_candidate_risk_baseline(
        db,
        tenant_id_str,
        scope_clause,
        limit=limit,
    )
    by_stage = {
        k: RiskIntelStageAggOut(**v) for k, v in (raw.get("risk_distribution_by_stage") or {}).items()
    }
    return RiskIntelligenceOut(
        generated_at=raw["generated_at"],
        risk_version=str(raw.get("risk_version") or "risk_model_v1"),
        candidates_evaluated=int(raw.get("candidates_evaluated") or 0),
        high_risk_volume=int(raw.get("high_risk_volume") or 0),
        avg_risk_score=float(raw.get("avg_risk_score") or 0.0),
        band_distribution=dict(raw.get("band_distribution") or {}),
        risk_distribution_by_stage=by_stage,
        first_response_hours_histogram=dict(raw.get("first_response_hours_histogram") or {}),
        effective_weights={str(k): float(v) for k, v in (raw.get("effective_weights") or {}).items()},
    )


class RiskIntelTrendPointOut(BaseModel):
    bucket_start: str | None
    avg_risk_score: float
    high_risk_volume: int
    candidates_evaluated: int
    band_low: int
    band_medium: int
    band_high: int
    band_critical: int


class RiskIntelTrendsOut(BaseModel):
    generated_at: datetime
    days: int
    points: list[RiskIntelTrendPointOut]


class RiskIntelValidationOut(BaseModel):
    generated_at: str
    cohort_window: dict[str, str]
    lag_days_after_cohort: int
    samples: int
    forward_stage_progression_count: int
    forward_stage_progression_rate: float | None = None
    interpretation: str | None = None
    note: str | None = None


class RiskIntelShadowItemOut(BaseModel):
    entity_id: str
    score: float
    band: str
    stage_at_score: str | None = None
    drivers: list[str] = Field(default_factory=list)
    scored_at: str | None = None
    short_id: str | None = None
    display_name: str | None = None
    recruiter_id: str | None = None


class RiskIntelShadowSnapshotOut(BaseModel):
    bucket_start: str | None = None
    scored_at: str | None = None
    risk_version: str = "risk_model_v1"
    min_band: str = "high"
    total_matching: int = 0
    items: list[RiskIntelShadowItemOut] = Field(default_factory=list)
    note: str | None = None


@router.get("/analytics/risk-intelligence/trends", response_model=RiskIntelTrendsOut)
async def risk_intelligence_trends(
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    ctx: UserCtx = Depends(get_current_user),
    days: int = Query(30, ge=1, le=90),
):
    """Phase B: hourly aggregate time series (persisted by communications scheduler)."""
    _require_risk_ops_lead(ctx)
    db, tenant_id = db_tenant
    tenant_id_str = str(tenant_id)
    now = datetime.now(timezone.utc)
    raw_points = await list_risk_intel_hourly_trends(db, tenant_id_str, days=days, now=now)
    points = [RiskIntelTrendPointOut(**p) for p in raw_points]
    return RiskIntelTrendsOut(generated_at=now, days=days, points=points)


@router.get("/analytics/risk-intelligence/validation", response_model=RiskIntelValidationOut)
async def risk_intelligence_validation(
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    ctx: UserCtx = Depends(get_current_user),
    cohort_days: int = Query(14, ge=8, le=120),
    lag_days: int = Query(7, ge=1, le=60),
):
    """Phase B: proxy validation — forward stage movement after high/critical shadow cohort."""
    _require_risk_ops_lead(ctx)
    db, tenant_id = db_tenant
    tenant_id_str = str(tenant_id)
    raw = await shadow_validation_summary(
        db,
        tenant_id_str,
        cohort_days=cohort_days,
        lag_days=lag_days,
    )
    return RiskIntelValidationOut(**raw)


@router.get("/analytics/risk-intelligence/shadow-snapshot", response_model=RiskIntelShadowSnapshotOut)
async def risk_intelligence_shadow_snapshot(
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    ctx: UserCtx = Depends(get_current_user),
    limit: int = Query(40, ge=1, le=200),
    min_band: str = Query("high", description="low|medium|high|critical — include rows at or above this band"),
    bucket_start: str | None = Query(
        None,
        description="Hourly bucket (ISO-8601). Omit for latest bucket.",
    ),
):
    """Hourly shadow bucket: at-risk candidates (digest for ops leads). Default = latest row."""
    _require_risk_ops_lead(ctx)
    db, tenant_id = db_tenant
    tenant_id_str = str(tenant_id)
    if bucket_start and str(bucket_start).strip():
        raw = await list_shadow_snapshot_for_bucket_iso(
            db,
            tenant_id_str,
            bucket_start_iso=str(bucket_start).strip(),
            limit=limit,
            min_band=min_band,
        )
    else:
        raw = await list_latest_shadow_snapshot(db, tenant_id_str, limit=limit, min_band=min_band)
    items = [RiskIntelShadowItemOut(**x) for x in (raw.get("items") or [])]
    return RiskIntelShadowSnapshotOut(
        bucket_start=raw.get("bucket_start"),
        scored_at=raw.get("scored_at"),
        risk_version=str(raw.get("risk_version") or "risk_model_v1"),
        min_band=str(raw.get("min_band") or "high"),
        total_matching=int(raw.get("total_matching") or 0),
        items=items,
        note=raw.get("note"),
    )


class RiskIntelDigestQueueItemOut(BaseModel):
    bucket_start: str
    total_matching: int
    scored_at: str | None = None
    unread: bool = False


class RiskIntelDigestQueueOut(BaseModel):
    generated_at: datetime
    min_band: str
    last_ack_bucket_start: str | None = None
    unread_count: int = 0
    buckets: list[RiskIntelDigestQueueItemOut]


class ManagerDigestAckIn(BaseModel):
    bucket_start: str = Field(..., min_length=4, description="Hourly bucket ISO-8601 (same as queue row)")


@router.get("/analytics/risk-intelligence/manager-digest-queue", response_model=RiskIntelDigestQueueOut)
async def risk_intelligence_manager_digest_queue(
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    ctx: UserCtx = Depends(get_current_user),
    min_band: str = Query("high", description="Band floor for row counts (same as shadow snapshot)"),
    limit_buckets: int = Query(21, ge=1, le=168, description="Max hourly buckets to return (newest first)"),
):
    """
    In-product manager digest queue: recent hourly shadow buckets + per-user unread (vs last ack).
    Ack via POST .../manager-digest-queue/ack.
    """
    _require_risk_ops_lead(ctx)
    db, tenant_id = db_tenant
    tenant_id_str = str(tenant_id)
    uid = str(ctx.sub or "").strip()
    now = datetime.now(timezone.utc)
    summaries = await list_shadow_digest_bucket_summaries(
        db,
        tenant_id_str,
        min_band=min_band,
        limit_buckets=limit_buckets,
    )
    last_ack: str | None = None
    if uid:
        last_ack = await _manager_digest_last_ack_bucket(db, tenant_id_str, uid)
    last_ack_dt = parse_shadow_bucket_iso(last_ack) if last_ack else None
    buckets_out: list[RiskIntelDigestQueueItemOut] = []
    unread_count = 0
    for idx, s in enumerate(summaries):
        bs_iso = str(s.get("bucket_start") or "")
        bs_dt = parse_shadow_bucket_iso(bs_iso)
        if bs_dt is None:
            unread = False
        elif last_ack_dt is None:
            unread = idx == 0
        else:
            unread = bs_dt > last_ack_dt
        if unread:
            unread_count += 1
        buckets_out.append(
            RiskIntelDigestQueueItemOut(
                bucket_start=bs_iso,
                total_matching=int(s.get("total_matching") or 0),
                scored_at=s.get("scored_at"),
                unread=unread,
            )
        )
    return RiskIntelDigestQueueOut(
        generated_at=now,
        min_band=str(min_band).strip().lower(),
        last_ack_bucket_start=last_ack,
        unread_count=unread_count,
        buckets=buckets_out,
    )


@router.post("/analytics/risk-intelligence/manager-digest-queue/ack")
async def risk_intelligence_manager_digest_ack(
    body: ManagerDigestAckIn,
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    ctx: UserCtx = Depends(get_current_user),
):
    """Record that this ops user reviewed digest through the given hourly bucket (ActivityLog)."""
    _require_risk_ops_lead(ctx)
    db, tenant_id = db_tenant
    tenant_id_str = str(tenant_id)
    uid = str(ctx.sub or "").strip()
    if not uid:
        raise HTTPException(status_code=401, detail="Missing user context")
    buck = parse_shadow_bucket_iso(body.bucket_start)
    if buck is None:
        raise HTTPException(status_code=422, detail="Invalid bucket_start")
    chk = await db.execute(
        select(func.count())
        .select_from(RiskIntelEntityShadow)
        .where(
            RiskIntelEntityShadow.tenant_id == tenant_id_str,
            RiskIntelEntityShadow.entity_type == "candidate",
            RiskIntelEntityShadow.bucket_start == buck,
        )
    )
    if int(chk.scalar_one() or 0) == 0:
        raise HTTPException(status_code=404, detail="Unknown digest bucket for tenant")
    await log_activity(
        db,
        tenant_id=tenant_id_str,
        actor_id=uid,
        action=MANAGER_DIGEST_ACK_ACTION,
        target_type="tenant",
        target_id=tenant_id_str,
        payload={"bucket_start": buck.isoformat()},
    )
    await db.commit()
    return {"ok": True, "bucket_start": buck.isoformat()}
