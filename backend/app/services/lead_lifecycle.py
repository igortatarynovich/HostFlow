"""Lead lifecycle cleanup and visibility helpers.

Keeps lead-linked operational signals clean:
- when a lead enters a terminal stage/status, open reminders are cancelled,
  unread notifications are marked read, and future planner events are cancelled;
- list surfaces can hide rows tied to terminal leads by default.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import and_, not_, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.communication import CommunicationPlannerEvent
from backend.app.models.lead import Lead
from backend.app.models.reminder import Reminder, ReminderStatus
from backend.app.models.reminder_event import ReminderEvent
from backend.app.models.user_notification import UserNotification

logger = logging.getLogger(__name__)

LEAD_TERMINAL_STAGE_CODES: frozenset[str] = frozenset({"converted", "lost"})
LEAD_TERMINAL_STATUS_CODES: frozenset[str] = frozenset({"failed", "duplicated"})

_ACTIVE_REMINDER_STATUSES: tuple[str, ...] = (
    ReminderStatus.new,
    ReminderStatus.pending,
    ReminderStatus.sent,
    ReminderStatus.overdue,
)
_ACTIVE_PLANNER_STATUSES: tuple[str, ...] = ("planned", "in_progress")


def _norm(raw: Optional[str]) -> str:
    return str(raw or "").strip().lower()


def is_terminal_stage(stage_code: Optional[str]) -> bool:
    return _norm(stage_code) in LEAD_TERMINAL_STAGE_CODES


def is_terminal_status(status_code: Optional[str]) -> bool:
    return _norm(status_code) in LEAD_TERMINAL_STATUS_CODES


@dataclass(frozen=True)
class LeadLifecycleCleanupResult:
    reminders_cancelled: int
    notifications_marked_read: int
    planner_events_cancelled: int
    reason: str


async def apply_lead_terminal_cleanup(
    db: AsyncSession,
    *,
    tenant_id: str,
    lead_id: str,
    new_stage: Optional[str],
    new_status: Optional[str],
    actor_id: Optional[str],
    reason: str = "lead_terminal",
) -> LeadLifecycleCleanupResult:
    now = datetime.now(timezone.utc)
    tenant_id_str = str(tenant_id or "").strip()
    lead_id_str = str(lead_id or "").strip()
    if not tenant_id_str or not lead_id_str:
        return LeadLifecycleCleanupResult(0, 0, 0, reason)

    reminders_cancelled = await _cancel_lead_reminders(
        db,
        tenant_id=tenant_id_str,
        lead_id=lead_id_str,
        now=now,
        actor_id=actor_id,
        new_stage=new_stage,
        new_status=new_status,
        reason=reason,
    )
    notifications_marked = await _mark_lead_notifications_read(
        db,
        tenant_id=tenant_id_str,
        lead_id=lead_id_str,
        now=now,
    )
    planner_cancelled = await _cancel_lead_planner_events(
        db,
        tenant_id=tenant_id_str,
        lead_id=lead_id_str,
        now=now,
    )
    if reminders_cancelled or notifications_marked or planner_cancelled:
        logger.info(
            "lead lifecycle cleanup tenant=%s lead=%s stage=%s status=%s reminders=%d notifications=%d planner=%d reason=%s",
            tenant_id_str,
            lead_id_str,
            new_stage,
            new_status,
            reminders_cancelled,
            notifications_marked,
            planner_cancelled,
            reason,
        )
    return LeadLifecycleCleanupResult(
        reminders_cancelled=reminders_cancelled,
        notifications_marked_read=notifications_marked,
        planner_events_cancelled=planner_cancelled,
        reason=reason,
    )


async def maybe_apply_lead_terminal_cleanup(
    db: AsyncSession,
    *,
    tenant_id: str,
    lead_id: str,
    old_stage: Optional[str],
    new_stage: Optional[str],
    old_status: Optional[str],
    new_status: Optional[str],
    actor_id: Optional[str],
) -> Optional[LeadLifecycleCleanupResult]:
    entered_terminal_stage = is_terminal_stage(new_stage) and not is_terminal_stage(old_stage)
    entered_terminal_status = is_terminal_status(new_status) and not is_terminal_status(old_status)
    if not entered_terminal_stage and not entered_terminal_status:
        return None
    return await apply_lead_terminal_cleanup(
        db,
        tenant_id=tenant_id,
        lead_id=lead_id,
        new_stage=new_stage,
        new_status=new_status,
        actor_id=actor_id,
        reason="lead_terminal_transition",
    )


async def maybe_apply_lead_silence_cleanup(
    db: AsyncSession,
    *,
    tenant_id: str,
    lead_id: str,
    old_stage: Optional[str],
    new_stage: Optional[str],
    old_status: Optional[str],
    new_status: Optional[str],
    old_candidate_id: Optional[str],
    new_candidate_id: Optional[str],
    actor_id: Optional[str],
) -> Optional[LeadLifecycleCleanupResult]:
    entered_terminal_stage = is_terminal_stage(new_stage) and not is_terminal_stage(old_stage)
    entered_terminal_status = is_terminal_status(new_status) and not is_terminal_status(old_status)
    linked_candidate_now = bool(str(new_candidate_id or "").strip())
    linked_candidate_before = bool(str(old_candidate_id or "").strip())
    entered_candidate_linked = linked_candidate_now and not linked_candidate_before
    if not entered_terminal_stage and not entered_terminal_status and not entered_candidate_linked:
        return None
    reason = "lead_converted_to_candidate" if entered_candidate_linked else "lead_terminal_transition"
    return await apply_lead_terminal_cleanup(
        db,
        tenant_id=tenant_id,
        lead_id=lead_id,
        new_stage=new_stage,
        new_status=new_status,
        actor_id=actor_id,
        reason=reason,
    )


async def sweep_converted_lead_operational_noise(
    db: AsyncSession,
    *,
    tenant_id: str,
    limit: int = 150,
    now: Optional[datetime] = None,
    actor_id: Optional[str] = None,
) -> dict[str, int]:
    """
    Repair backlog: a lead linked to a candidate must not keep active lead-scoped
    reminders or future planner rows. Runs the same cleanup as conversion hooks,
    but only for leads that still have dangling operational signals.
    """
    tenant_id_str = str(tenant_id or "").strip()
    if not tenant_id_str:
        return {"leads_processed": 0, "reminders_cancelled": 0, "notifications_marked_read": 0, "planner_events_cancelled": 0}
    cap = min(max(1, int(limit or 150)), 500)
    ts = now or datetime.now(timezone.utc)

    reminder_lead_ids = (
        select(Reminder.entity_id)
        .where(
            Reminder.tenant_id == tenant_id_str,
            Reminder.entity_type == "lead",
            Reminder.status.in_(_ACTIVE_REMINDER_STATUSES),
        )
        .distinct()
    )
    stmt_rem = (
        select(Lead.id)
        .where(
            Lead.tenant_id == tenant_id_str,
            Lead.candidate_id.is_not(None),
            Lead.id.in_(reminder_lead_ids),
        )
    )
    planner_lead_ids = (
        select(CommunicationPlannerEvent.entity_id)
        .where(
            CommunicationPlannerEvent.tenant_id == tenant_id_str,
            CommunicationPlannerEvent.entity_type == "lead",
            CommunicationPlannerEvent.status.in_(_ACTIVE_PLANNER_STATUSES),
            CommunicationPlannerEvent.start_at >= ts,
        )
        .distinct()
    )
    stmt_plan = (
        select(Lead.id)
        .where(
            Lead.tenant_id == tenant_id_str,
            Lead.candidate_id.is_not(None),
            Lead.id.in_(planner_lead_ids),
        )
    )

    rows_rem = await db.execute(stmt_rem)
    rows_plan = await db.execute(stmt_plan)
    merged: list[str] = []
    seen: set[str] = set()
    for row in list(rows_rem.all()) + list(rows_plan.all()):
        lid = str(row[0] or "").strip()
        if not lid or lid in seen:
            continue
        seen.add(lid)
        merged.append(lid)
        if len(merged) >= cap:
            break

    totals = {"leads_processed": 0, "reminders_cancelled": 0, "notifications_marked_read": 0, "planner_events_cancelled": 0}
    actor = str(actor_id or "").strip() or "system"
    for lead_id in merged:
        res = await apply_lead_terminal_cleanup(
            db,
            tenant_id=tenant_id_str,
            lead_id=lead_id,
            new_stage=None,
            new_status=None,
            actor_id=actor,
            reason="sweep_converted_lead_backlog",
        )
        totals["leads_processed"] += 1
        totals["reminders_cancelled"] += int(res.reminders_cancelled or 0)
        totals["notifications_marked_read"] += int(res.notifications_marked_read or 0)
        totals["planner_events_cancelled"] += int(res.planner_events_cancelled or 0)

    if totals["leads_processed"]:
        logger.info(
            "converted lead operational sweep tenant=%s leads=%s reminders=%s notifications=%s planner=%s",
            tenant_id_str,
            totals["leads_processed"],
            totals["reminders_cancelled"],
            totals["notifications_marked_read"],
            totals["planner_events_cancelled"],
        )
    return totals


async def apply_lead_deletion_cleanup(
    db: AsyncSession,
    *,
    tenant_id: str,
    lead_id: str,
    actor_id: Optional[str],
) -> LeadLifecycleCleanupResult:
    return await apply_lead_terminal_cleanup(
        db,
        tenant_id=tenant_id,
        lead_id=lead_id,
        new_stage=None,
        new_status=None,
        actor_id=actor_id,
        reason="lead_deleted",
    )


async def _cancel_lead_reminders(
    db: AsyncSession,
    *,
    tenant_id: str,
    lead_id: str,
    now: datetime,
    actor_id: Optional[str],
    new_stage: Optional[str],
    new_status: Optional[str],
    reason: str,
) -> int:
    rows = await db.execute(
        select(Reminder).where(
            Reminder.tenant_id == tenant_id,
            Reminder.entity_type == "lead",
            Reminder.entity_id == lead_id,
            Reminder.status.in_(_ACTIVE_REMINDER_STATUSES),
        )
    )
    reminders = list(rows.scalars().all())
    if not reminders:
        return 0
    cancelled = 0
    for reminder in reminders:
        previous_status = str(reminder.status)
        reminder.status = ReminderStatus.done
        reminder.completed_at = now
        db.add(
            ReminderEvent(
                reminder_id=reminder.id,
                tenant_id=tenant_id,
                event_type="auto_cancelled_due_to_lead_terminal",
                payload={
                    "actor_id": actor_id,
                    "lead_id": lead_id,
                    "new_stage": new_stage,
                    "new_status": new_status,
                    "reason": reason,
                    "previous_status": previous_status,
                },
            )
        )
        cancelled += 1
    return cancelled


async def _mark_lead_notifications_read(
    db: AsyncSession,
    *,
    tenant_id: str,
    lead_id: str,
    now: datetime,
) -> int:
    result = await db.execute(
        update(UserNotification)
        .where(
            UserNotification.tenant_id == tenant_id,
            UserNotification.entity_type == "lead",
            UserNotification.entity_id == lead_id,
            UserNotification.is_read.is_(False),
        )
        .values(is_read=True, read_at=now, updated_at=now)
    )
    return int(result.rowcount or 0)


async def _cancel_lead_planner_events(
    db: AsyncSession,
    *,
    tenant_id: str,
    lead_id: str,
    now: datetime,
) -> int:
    rows = await db.execute(
        select(CommunicationPlannerEvent).where(
            CommunicationPlannerEvent.tenant_id == tenant_id,
            CommunicationPlannerEvent.status.in_(_ACTIVE_PLANNER_STATUSES),
            CommunicationPlannerEvent.start_at >= now,
            CommunicationPlannerEvent.entity_type == "lead",
            CommunicationPlannerEvent.entity_id == lead_id,
        )
    )
    events = list(rows.scalars().all())
    if not events:
        return 0
    cancelled = 0
    for event in events:
        event.status = "cancelled"
        event.updated_at = now
        meta = dict(event.payload) if isinstance(event.payload, dict) else {}
        meta["auto_cancelled"] = {
            "reason": "lead_lifecycle_terminal",
            "at": now.isoformat(),
        }
        event.payload = meta
        cancelled += 1
    return cancelled


def silenced_lead_ids_subquery(tenant_id: str):
    return (
        select(Lead.id)
        .where(
            Lead.tenant_id == tenant_id,
            or_(
                Lead.candidate_id.is_not(None),
                Lead.stage.in_(tuple(LEAD_TERMINAL_STAGE_CODES)),
                Lead.status.in_(tuple(LEAD_TERMINAL_STATUS_CODES)),
            ),
        )
        .scalar_subquery()
    )


def exclude_completed_lead_entities_clause(
    tenant_id: str,
    *,
    entity_type_col,
    entity_id_col,
):
    silenced = silenced_lead_ids_subquery(tenant_id)
    return not_(
        and_(
            entity_type_col == "lead",
            entity_id_col.in_(silenced),
        )
    )


__all__ = [
    "LEAD_TERMINAL_STAGE_CODES",
    "LEAD_TERMINAL_STATUS_CODES",
    "LeadLifecycleCleanupResult",
    "apply_lead_deletion_cleanup",
    "apply_lead_terminal_cleanup",
    "exclude_completed_lead_entities_clause",
    "is_terminal_stage",
    "is_terminal_status",
    "maybe_apply_lead_silence_cleanup",
    "maybe_apply_lead_terminal_cleanup",
    "silenced_lead_ids_subquery",
    "sweep_converted_lead_operational_noise",
]
