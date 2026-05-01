from __future__ import annotations

from typing import Any, Dict, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models import Lead, Reminder
from backend.app.models.reminder import ReminderStatus
from backend.app.models.user import Role
from backend.app.modules.leads import lead_custom_fields, service as lead_service
from backend.app.services import events
from backend.app.services.audit import log_activity
from backend.app.services.automation_rules import run_rules as run_automation_rules
from backend.app.services.events import EventAudience
from backend.app.services.plan_feature_gates import (
    TRIAL_CONVERSION_ACTIONS_METRIC,
    enforce_trial_usage_cap_and_increment,
)


async def _lead_reminder_assignee_id(
    db: AsyncSession,
    *,
    tenant_id: str,
    lead_id: str,
) -> Optional[str]:
    active_statuses = (ReminderStatus.pending, ReminderStatus.new, ReminderStatus.overdue)
    row = await db.execute(
        select(Reminder.assignee_id)
        .where(
            Reminder.tenant_id == tenant_id,
            Reminder.entity_type == "lead",
            Reminder.entity_id == lead_id,
            Reminder.status.in_(active_statuses),
        )
        .order_by(Reminder.updated_at.desc())
        .limit(1)
    )
    aid = row.scalar_one_or_none()
    if not aid:
        return None
    s = str(aid).strip()
    return s or None


async def record_lead_stage_change(
    db: AsyncSession,
    *,
    tenant_id: str,
    lead: Lead,
    from_stage: Optional[Any],
    to_stage: Any,
    actor_id: Optional[str],
    lost_reason_code: Optional[str] = None,
    lost_reason_note: Optional[str] = None,
) -> None:
    """Audit + in-app notification. Call in the same transaction as the stage update (before commit)."""
    fs = None if from_stage is None else str(from_stage)
    ts = str(to_stage)
    if fs != ts:
        await enforce_trial_usage_cap_and_increment(
            db,
            tenant_id=tenant_id,
            metric=TRIAL_CONVERSION_ACTIONS_METRIC,
            increment=1,
        )
    audit_payload: Dict[str, Any] = {
        "lead_id": str(lead.id),
        "from_stage": fs,
        "to_stage": ts,
    }
    if ts == "lost":
        if lost_reason_code:
            audit_payload["lost_reason_code"] = lost_reason_code
        if lost_reason_note:
            audit_payload["lost_reason_note"] = lost_reason_note
    try:
        await log_activity(
            db,
            tenant_id=tenant_id,
            actor_id=actor_id,
            action="lead.stage_changed",
            target_type="lead",
            target_id=str(lead.id),
            payload=audit_payload,
        )
    except Exception:
        pass
    business_type = await lead_service._load_tenant_business_type(db, tenant_id)
    outcome_entity_type, outcome_entity_id, outcome_entity_name = lead_service._build_lead_outcome(
        business_type=business_type,
        company_id=lead.company_id,
        company_name=None,
        candidate_id=lead.candidate_id,
        candidate_name=None,
    )
    payload: Dict[str, Any] = {
        "lead_id": lead.id,
        "status": lead.status,
        "business_type": business_type,
        "company_id": lead.company_id,
        "vacancy_id": lead.vacancy_id,
        "from_stage": fs,
        "to_stage": ts,
        "outcome_entity_type": outcome_entity_type,
        "outcome_entity_id": outcome_entity_id,
        "outcome_entity_name": outcome_entity_name,
    }
    if ts == "lost":
        if lost_reason_code:
            payload["lost_reason_code"] = lost_reason_code
        if lost_reason_note:
            payload["lost_reason_note"] = lost_reason_note
    try:
        await events.emit_event(
            db,
            tenant_id=tenant_id,
            event_type="lead.pipeline.stage_changed",
            payload=payload,
            entity_type="lead",
            entity_id=str(lead.id),
            audience=EventAudience(roles=[Role.administrator, Role.supervisor]),
        )
    except Exception:
        pass


async def run_lead_stage_change_automations(
    db: AsyncSession,
    *,
    tenant_id: str,
    lead: Lead,
    from_stage: Optional[Any],
    to_stage: Any,
    actor_id: Optional[str],
) -> None:
    """
    Fire automation rules for lead pipeline stage change.
    Must run after the stage update transaction has been committed so rule failures never undo the stage.
    """
    fs = "" if from_stage is None else str(from_stage)
    ts = str(to_stage)
    reminder_assignee = await _lead_reminder_assignee_id(db, tenant_id=tenant_id, lead_id=str(lead.id))
    preferred = str(actor_id or "").strip() or None
    pick = await lead_service._pick_lead_assignee_id(
        db,
        tenant_id=tenant_id,
        preferred_user_id=preferred,
        normalized=lead.normalized if isinstance(lead.normalized, dict) else None,
        lead_id=str(lead.id),
    )
    actor_for_rules = reminder_assignee or pick or preferred
    business_type = await lead_service._load_tenant_business_type(db, tenant_id)
    norm = lead.normalized if isinstance(lead.normalized, dict) else {}
    extras = await lead_custom_fields.automation_context_for_lead(
        db,
        tenant_id=tenant_id,
        lead_id=str(lead.id),
        normalized=norm,
    )
    ctx: Dict[str, Any] = {
        "entity_type": "lead",
        "entity_id": str(lead.id),
        "lead_id": str(lead.id),
        "from_stage": fs,
        "to_stage": ts,
        "status": lead.status,
        "business_type": business_type,
        "company_id": lead.company_id or "",
        "vacancy_id": lead.vacancy_id or "",
        "assignee_id": actor_for_rules or "",
        **extras,
    }
    try:
        await run_automation_rules(
            db,
            tenant_id=tenant_id,
            trigger="lead.pipeline.stage_changed",
            actor_id=actor_for_rules,
            context=ctx,
        )
        await db.commit()
    except Exception:
        await db.rollback()
