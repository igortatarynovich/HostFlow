"""Candidate lifecycle hooks — zero-leak cleanup on terminal stages and deletion.

Closes G-1 from `docs/specs/operations-loop.md`:

When a candidate moves into a "completed pipeline" stage (`PIPELINE_COMPLETED_STAGE_CODES`,
i.e. `rejected` / `declined` / `probation_ok` / `employed`) or gets soft-deleted, the
operational signals tied to that candidate must be silenced:

1. Active deadline-only `Activity` rows (``starts_at IS NULL``) for
   ``related_entity_type='candidate', related_entity_id=<cand>`` are moved
   to ``cancelled`` (statuses ``new|pending|sent|overdue|planned|in_progress``
   → ``cancelled``).
2. Unread `UserNotification` rows for the same entity are marked read.
3. Future (``starts_at >= now``) time-bound `Activity` rows
   (``starts_at IS NOT NULL``) linked to the candidate that are still
   ``planned|in_progress`` are moved to ``cancelled``. Linkage is detected
   either via the canonical ``related_entity_*`` pair *or* via the legacy
   ``metadata.planner.linked_candidate_id`` marker preserved by Phase 2.1
   backfill (Alembic ``202607150004_pti``).
4. A `ReminderEvent` row of type `auto_cancelled_due_to_candidate_stage`
   is logged for each cancelled reminder so the operator can see *why*
   it disappeared (G-10 explainability).

Phase 2.1 (ADR-012, 2026-05-09): both halves now query the canonical
``activities`` table (``Reminder is Activity`` after the ``activity_layer_v1``
rename). The split between "reminder" and "planner" rows is on
``Activity.starts_at IS NULL`` vs ``IS NOT NULL`` — see
``docs/specs/architecture/phase-2-1-planner-tasks-into-activities.md``
§"What service rewire means concretely".

The cleanup is idempotent and best-effort: failures are isolated and do not
roll back the candidate stage transition itself. The caller is responsible
for committing.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import and_, not_, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.constants.stages import PIPELINE_COMPLETED_STAGE_CODES
from backend.app.models.candidate import Candidate
# Phase 2.1 (ADR-012, 2026-05-09): import ``Activity`` via the
# ``backend.app.models.reminder`` alias (``Reminder is Activity``
# post-Phase-1.3) to avoid the duplicate-package-path footgun under
# Docker — see ``models/user_notification.py`` docstring. We pull
# ``Activity`` and ``ActivityStatus`` as local aliases here so the
# rest of this module can keep using the canonical names.
from backend.app.models.reminder import (
    Reminder,
    Reminder as Activity,
    ReminderStatus,
    ReminderStatus as ActivityStatus,
)
from backend.app.models.reminder_event import ReminderEvent
from backend.app.models.user_notification import UserNotification

logger = logging.getLogger(__name__)


# Re-export for callers that want a single import point.
LIFECYCLE_TERMINATED_STAGE_CODES = PIPELINE_COMPLETED_STAGE_CODES


# "Active" reminder/activity statuses — closed Activity enum
# (planned / in_progress) plus the legacy transient values that the
# ``activity_layer_v1`` migration collapses to ``planned`` on read but
# may still exist on rows that were not yet touched.
_ACTIVE_REMINDER_STATUSES: tuple[str, ...] = (
    ReminderStatus.new,
    ReminderStatus.pending,
    ReminderStatus.sent,
    ReminderStatus.overdue,
    ActivityStatus.planned,
    ActivityStatus.in_progress,
)

_ACTIVE_PLANNER_STATUSES: tuple[str, ...] = (
    ActivityStatus.planned,
    ActivityStatus.in_progress,
)


def is_terminal_stage(stage_code: Optional[str]) -> bool:
    """True when `stage_code` is one of the canonical PIPELINE_COMPLETED stages."""
    s = (stage_code or "").strip().lower()
    return bool(s) and s in LIFECYCLE_TERMINATED_STAGE_CODES


@dataclass(frozen=True)
class CandidateLifecycleCleanupResult:
    reminders_cancelled: int
    notifications_marked_read: int
    planner_events_cancelled: int
    reason: str


async def apply_candidate_terminal_cleanup(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate_id: str,
    new_stage: Optional[str],
    actor_id: Optional[str],
    reason: str = "candidate_stage_terminal",
) -> CandidateLifecycleCleanupResult:
    """Cancel pending operational signals for `candidate_id` (Reminder + UserNotification + Planner).

    No-op when the candidate has nothing pending. Always safe to call multiple times.

    The caller MUST commit the session afterwards (we mutate ORM rows but do not commit
    so the change is part of the same transaction whenever practical).
    """
    now = datetime.now(timezone.utc)
    tenant_id_str = str(tenant_id or "").strip()
    candidate_id_str = str(candidate_id or "").strip()
    if not tenant_id_str or not candidate_id_str:
        return CandidateLifecycleCleanupResult(0, 0, 0, reason)

    reminders_cancelled = await _cancel_candidate_reminders(
        db,
        tenant_id=tenant_id_str,
        candidate_id=candidate_id_str,
        now=now,
        actor_id=actor_id,
        new_stage=new_stage,
        reason=reason,
    )
    notifications_marked = await _mark_candidate_notifications_read(
        db,
        tenant_id=tenant_id_str,
        candidate_id=candidate_id_str,
        now=now,
    )
    planner_cancelled = await _cancel_candidate_planner_events(
        db,
        tenant_id=tenant_id_str,
        candidate_id=candidate_id_str,
        now=now,
    )

    if reminders_cancelled or notifications_marked or planner_cancelled:
        logger.info(
            "candidate lifecycle cleanup tenant=%s candidate=%s stage=%s "
            "reminders=%d notifications=%d planner=%d reason=%s",
            tenant_id_str,
            candidate_id_str,
            new_stage,
            reminders_cancelled,
            notifications_marked,
            planner_cancelled,
            reason,
        )

    return CandidateLifecycleCleanupResult(
        reminders_cancelled=reminders_cancelled,
        notifications_marked_read=notifications_marked,
        planner_events_cancelled=planner_cancelled,
        reason=reason,
    )


async def maybe_apply_candidate_terminal_cleanup(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate_id: str,
    old_stage: Optional[str],
    new_stage: Optional[str],
    actor_id: Optional[str],
) -> Optional[CandidateLifecycleCleanupResult]:
    """Run cleanup only when the stage *transitioned into* a terminal code.

    Re-entering the same terminal stage is a no-op (we don't want to keep re-cancelling
    rows that were re-created manually after the first cleanup).
    """
    if not is_terminal_stage(new_stage):
        return None
    old = (old_stage or "").strip().lower()
    if old in LIFECYCLE_TERMINATED_STAGE_CODES:
        return None
    return await apply_candidate_terminal_cleanup(
        db,
        tenant_id=tenant_id,
        candidate_id=candidate_id,
        new_stage=new_stage,
        actor_id=actor_id,
        reason="candidate_stage_terminal",
    )


async def apply_candidate_deletion_cleanup(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate_id: str,
    actor_id: Optional[str],
) -> CandidateLifecycleCleanupResult:
    """Always-on cleanup invoked from `delete_candidate_full` (soft delete)."""
    return await apply_candidate_terminal_cleanup(
        db,
        tenant_id=tenant_id,
        candidate_id=candidate_id,
        new_stage=None,
        actor_id=actor_id,
        reason="candidate_deleted",
    )


async def _cancel_candidate_reminders(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate_id: str,
    now: datetime,
    actor_id: Optional[str],
    new_stage: Optional[str],
    reason: str,
) -> int:
    # Phase 2.1 (ADR-012, 2026-05-09): scoped to deadline-only rows
    # (``starts_at IS NULL``) so it doesn't double-process the
    # planner-style rows handled by ``_cancel_candidate_planner_events``.
    rows = await db.execute(
        select(Activity).where(
            Activity.tenant_id == tenant_id,
            Activity.related_entity_type == "candidate",
            Activity.related_entity_id == candidate_id,
            Activity.status.in_(_ACTIVE_REMINDER_STATUSES),
            Activity.starts_at.is_(None),
        )
    )
    reminders = list(rows.scalars().all())
    if not reminders:
        return 0

    cancelled = 0
    for reminder in reminders:
        previous_status = str(reminder.status)
        reminder.status = ActivityStatus.done
        reminder.completed_at = now
        # Best-effort audit row so /app/tasks "explainability" can show why this disappeared.
        db.add(
            ReminderEvent(
                reminder_id=reminder.id,
                tenant_id=tenant_id,
                event_type="auto_cancelled_due_to_candidate_stage",
                payload={
                    "actor_id": actor_id,
                    "candidate_id": candidate_id,
                    "new_stage": new_stage,
                    "reason": reason,
                    "previous_status": previous_status,
                },
            )
        )
        cancelled += 1
    return cancelled


async def _mark_candidate_notifications_read(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate_id: str,
    now: datetime,
) -> int:
    """Mark unread bell notifications attached to this candidate as read.

    Notifications are user-scoped (per-assignee), so this can affect rows for many users.
    The bell becomes silent for all of them — which is what we want when a candidate
    is rejected/employed.
    """
    result = await db.execute(
        update(UserNotification)
        .where(
            UserNotification.tenant_id == tenant_id,
            UserNotification.entity_type == "candidate",
            UserNotification.entity_id == candidate_id,
            UserNotification.is_read.is_(False),
        )
        .values(is_read=True, read_at=now, updated_at=now)
    )
    return int(result.rowcount or 0)


async def _cancel_candidate_planner_events(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate_id: str,
    now: datetime,
) -> int:
    """Cancel future time-bound (planner-style) activities linked to this candidate.

    A planner-source activity can be linked to a candidate either via:
      * the canonical ``related_entity_type='candidate', related_entity_id=<cand>``
        pair (set by the calendar UI / automation since Phase 1.3);
      * or via the legacy ``metadata.planner.linked_candidate_id`` marker
        preserved by Phase 2.1 backfill (Alembic ``202607150004_pti``) for
        rows whose original ``communication_planner_events.linked_candidate_id``
        differed from ``entity_id``.

    Phase 2.1 (ADR-012, 2026-05-09): scoped to ``Activity.starts_at IS NOT NULL``
    (time-bound) and ``starts_at >= now`` so it doesn't double-process the
    deadline-only rows handled by ``_cancel_candidate_reminders``. Past
    events are kept as historical record.
    """
    rows = await db.execute(
        select(Activity).where(
            Activity.tenant_id == tenant_id,
            Activity.status.in_(_ACTIVE_PLANNER_STATUSES),
            Activity.starts_at.is_not(None),
            Activity.starts_at >= now,
            or_(
                # Canonical linkage.
                (Activity.related_entity_type == "candidate")
                & (Activity.related_entity_id == candidate_id),
                # Legacy ``linked_candidate_id`` preserved by backfill in
                # ``metadata.planner.linked_candidate_id``. The JSON path
                # is portable across PG (JSON ``->>``) and SQLite (TEXT
                # JSON1) since both support the chained ``->>`` operator
                # via SQLAlchemy's ``Activity.metadata_["planner"]["linked_candidate_id"]``.
                Activity.metadata_["planner"]["linked_candidate_id"].as_string()
                == candidate_id,
            ),
        )
    )
    events = list(rows.scalars().all())
    if not events:
        return 0

    cancelled = 0
    for event in events:
        event.status = ActivityStatus.cancelled
        event.cancelled_at = now
        meta = dict(event.metadata_) if isinstance(event.metadata_, dict) else {}
        meta["auto_cancelled"] = {
            "reason": "candidate_lifecycle_terminal",
            "at": now.isoformat(),
        }
        event.metadata_ = meta
        cancelled += 1
    return cancelled


def silenced_candidate_ids_subquery(tenant_id: str):
    """Subquery: ids of candidates whose operational signals should be hidden.

    A candidate is "silenced" when:
      * `stage IN PIPELINE_COMPLETED_STAGE_CODES` (rejected / declined / employed / probation_ok),
      * OR `deleted_at IS NOT NULL` (soft-deleted).

    Used as `WHERE NOT (entity_type='candidate' AND entity_id IN <this subquery>)`
    in `GET /reminders`, `GET /notifications`, `GET /communications/planner/events`
    when `include_completed_entities=False` (the default).
    """
    return (
        select(Candidate.id)
        .where(
            Candidate.tenant_id == tenant_id,
            or_(
                Candidate.stage.in_(tuple(LIFECYCLE_TERMINATED_STAGE_CODES)),
                Candidate.deleted_at.is_not(None),
            ),
        )
        .scalar_subquery()
    )


def exclude_completed_candidate_entities_clause(
    tenant_id: str,
    *,
    entity_type_col,
    entity_id_col,
):
    """Build a SQLAlchemy WHERE clause that drops rows tied to silenced candidates.

    Use with any table that carries ``(entity_type, entity_id)`` columns
    (``UserNotification``, or the legacy ``Reminder`` / ``CommunicationPlannerEvent``
    aliases that now resolve to ``activities`` post-Phase-2.1). Rows that are
    not candidate-related pass through unchanged.

    Returns a clause suitable for `stmt = stmt.where(<clause>)`.
    """
    silenced = silenced_candidate_ids_subquery(tenant_id)
    return not_(
        and_(
            entity_type_col == "candidate",
            entity_id_col.in_(silenced),
        )
    )


__all__ = [
    "LIFECYCLE_TERMINATED_STAGE_CODES",
    "CandidateLifecycleCleanupResult",
    "apply_candidate_deletion_cleanup",
    "apply_candidate_terminal_cleanup",
    "exclude_completed_candidate_entities_clause",
    "is_terminal_stage",
    "maybe_apply_candidate_terminal_cleanup",
    "silenced_candidate_ids_subquery",
]
