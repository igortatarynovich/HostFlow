"""Slice 4 Guard 1 — suppress default UOS \"Call candidate\" after Lead→Candidate when lead already has operational touch.

Lives under ``services/`` (not ``modules.leads``) so ``uos_auto_activities`` can import without loading the leads API package (import-cycle safe).
"""

from __future__ import annotations

from typing import Any, List, Sequence, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.audit import ActivityLog
from backend.app.models.reminder import ReminderStatus
from backend.app.services.lead_context_carry import resolve_lead_note

# Logged when default first-contact reminder is intentionally not created.
FIRST_CONTACT_SUPPRESSED_ACTION = "lead_to_candidate.first_contact_suppressed"

_INTAKE_STATUSES_SUPPRESS: frozenset[str] = frozenset(
    {
        "qualified",
        "rejected",
        "pooled",
        "info_requested",
        "duplicate_review_requested",
    }
)

# CRM stages on the lead that imply the lead is past \"cold\" first outreach.
_LEAD_STAGES_POST_TOUCH: frozenset[str] = frozenset({"contacted", "qualified"})

# From ``lead.stage_changed`` audit payloads — reached a post-touch CRM stage at least once.
_ACTIVITY_TO_STAGES_TOUCH: frozenset[str] = frozenset({"contacted", "qualified"})

# ActivityLog actions that prove operator engagement before candidate materialization.
_ACTIVITY_LOG_TOUCH_ACTIONS: frozenset[str] = frozenset(
    {
        "lead.manual_process",
        "lead.manual_process.done",
        "lead.vacancy_confirmed",
        "lead.intake_decision.qualify",
    }
)

# Lead-scoped activity types that imply outreach already happened or was scheduled.
_LEAD_ACTIVITY_TOUCH_TYPES: frozenset[str] = frozenset(
    {
        "call",
        "meeting",
        "phone",
        "contact",
    }
)


def lead_first_contact_suppression_reasons_sync(lead: Any) -> List[str]:
    """Signals available without extra DB reads (normalized + lead columns)."""
    reasons: List[str] = []
    norm = getattr(lead, "normalized", None)
    if not isinstance(norm, dict):
        norm = {}

    ir = norm.get("intake_resolution_v1")
    if isinstance(ir, dict):
        st = str(ir.get("status") or "").strip().lower()
        if st in _INTAKE_STATUSES_SUPPRESS:
            reasons.append(f"intake_resolution:{st}")

    stage = str(getattr(lead, "stage", None) or "").strip().lower()
    if stage in _LEAD_STAGES_POST_TOUCH:
        reasons.append(f"lead_stage:{stage}")

    note = resolve_lead_note(lead)
    if note:
        reasons.append("lead_note:present")

    return reasons


async def _activity_log_lead_touched_via_stage_audit(
    db: AsyncSession,
    *,
    tenant_id: str,
    lead_id: str,
) -> bool:
    stmt = select(ActivityLog.payload).where(
        ActivityLog.tenant_id == tenant_id,
        ActivityLog.target_type == "lead",
        ActivityLog.target_id == str(lead_id),
        ActivityLog.action == "lead.stage_changed",
    )
    res = await db.execute(stmt)
    for (payload,) in res.all():
        if not isinstance(payload, dict):
            continue
        ts = str(payload.get("to_stage") or "").strip().lower()
        if ts in _ACTIVITY_TO_STAGES_TOUCH:
            return True
    return False


async def _activity_log_lead_operational_touch(
    db: AsyncSession,
    *,
    tenant_id: str,
    lead_id: str,
) -> bool:
    stmt = (
        select(ActivityLog.id)
        .where(
            ActivityLog.tenant_id == tenant_id,
            ActivityLog.target_type == "lead",
            ActivityLog.target_id == str(lead_id),
            ActivityLog.action.in_(_ACTIVITY_LOG_TOUCH_ACTIONS),
        )
        .limit(1)
    )
    row = (await db.execute(stmt)).scalar_one_or_none()
    return row is not None


async def _lead_has_active_open_reminder(
    db: AsyncSession,
    *,
    tenant_id: str,
    lead_id: str,
) -> bool:
    """Any active lead-scoped reminder — avoid stacking uos_candidate_call on convert (Guard 3)."""
    from backend.app.models import Reminder

    active_statuses = (ReminderStatus.pending, ReminderStatus.new, ReminderStatus.overdue)
    row = (
        await db.execute(
            select(Reminder.id)
            .where(
                Reminder.tenant_id == tenant_id,
                Reminder.entity_type == "lead",
                Reminder.entity_id == str(lead_id),
                Reminder.status.in_(active_statuses),
            )
            .limit(1)
        )
    ).scalar_one_or_none()
    return row is not None


async def _lead_has_call_or_contact_activity(
    db: AsyncSession,
    *,
    tenant_id: str,
    lead_id: str,
) -> bool:
    from backend.app.models import Reminder

    stmt = (
        select(Reminder.id)
        .where(
            Reminder.tenant_id == tenant_id,
            Reminder.related_entity_type == "lead",
            Reminder.related_entity_id == str(lead_id),
            Reminder.type.in_(_LEAD_ACTIVITY_TOUCH_TYPES),
        )
        .limit(1)
    )
    row = (await db.execute(stmt)).scalar_one_or_none()
    return row is not None


async def lead_first_contact_suppression_reasons(
    db: AsyncSession,
    *,
    tenant_id: str,
    lead: Any,
) -> List[str]:
    """Merge sync signals with ActivityLog and lead-scoped activities."""
    reasons = list(lead_first_contact_suppression_reasons_sync(lead))
    if reasons:
        return _uniq_preserve(reasons)

    lead_id = str(getattr(lead, "id", "") or "").strip()
    if not lead_id:
        return []

    if await _activity_log_lead_touched_via_stage_audit(db, tenant_id=tenant_id, lead_id=lead_id):
        reasons.append("activity_log:lead.stage_changed→contacted|qualified")
    if await _activity_log_lead_operational_touch(db, tenant_id=tenant_id, lead_id=lead_id):
        reasons.append("activity_log:lead.operational_touch")
    if await _lead_has_call_or_contact_activity(db, tenant_id=tenant_id, lead_id=lead_id):
        reasons.append("activity:lead.call_or_contact")
    if await _lead_has_active_open_reminder(db, tenant_id=tenant_id, lead_id=lead_id):
        reasons.append("lead_reminder:active_next_action")

    return _uniq_preserve(reasons)


def _uniq_preserve(seq: Sequence[str]) -> List[str]:
    seen: set[str] = set()
    out: List[str] = []
    for x in seq:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out


async def should_skip_default_first_contact_after_lead_conversion(
    db: AsyncSession,
    *,
    tenant_id: str,
    lead: Any,
) -> Tuple[bool, List[str]]:
    reasons = await lead_first_contact_suppression_reasons(db, tenant_id=tenant_id, lead=lead)
    return (bool(reasons), reasons)
