"""G-4 stage 4: cancel an assignee's reminders and planner-source
activities that fall within an approved time-off window.

Triggered from `decide_time_off_request` when the decision flips a
request to `approved`. The contract:

  * Only PENDING-equivalent reminder-style activities (deadline-only,
    `starts_at IS NULL`) are auto-completed — already-completed or
    already-cancelled rows stay as-is (no rewriting history).
  * Only ACTIVE planner-style activities (time-bound, `starts_at IS
    NOT NULL`, `status NOT IN {done, cancelled}`) are cancelled —
    same rationale.
  * Each row records `payload._cancelled_reason="timeoff_approved"`
    plus the time-off request id, so the audit trail explains why the
    operator suddenly has fewer items in their queue.
  * The date range is `[start_date 00:00, end_date 23:59:59]` in the
    REQUESTER's local timezone (from `User.extra.working_hours_v1.tz`,
    falling back to UTC). This matches user expectations — "I'm off
    Monday through Friday" means Monday 00:00 local through Friday
    24:00 local, not whatever UTC-bounded slice that maps to.

Phase 2.1 (ADR-012, 2026-05-09): both halves now query the canonical
``activities`` table (`Reminder is Activity`). The split between
"reminder" and "planner" rows is on ``Activity.starts_at IS NULL``
(deadline) vs ``IS NOT NULL`` (time-bound). The counter names
(``reminders_cancelled`` and ``planner_events_cancelled``) are
preserved verbatim for log/metric continuity through Phase 4 — see
``docs/specs/architecture/phase-2-1-planner-tasks-into-activities.md``
§"What service rewire means concretely".

Returns counts so callers can log / surface "12 reminders auto-closed".

Caller responsibility:
  * Wraps in the same DB transaction as the time-off decision so the
    cleanup is atomic with the approval (no half-state where the
    request is approved but the reminders are still firing).
  * Catches exceptions — best-effort cleanup must not block the
    decision path itself.
"""

from __future__ import annotations

from datetime import datetime, time, timedelta, timezone
from typing import Any, Dict
from zoneinfo import ZoneInfo

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

# Phase 2.1 (ADR-012, 2026-05-09): we want the canonical ``Activity``
# class, but importing it as ``backend.app.models.activity`` directly
# trips the duplicate-package-path footgun under Docker (where both
# ``app.models.activity`` and ``backend.app.models.activity`` resolve
# to the same file but as two distinct ``sys.modules`` entries — see
# ``models/user_notification.py`` docstring). Going through
# ``backend.app.models.reminder`` is the safe loader path that the
# rest of the service layer already uses (e.g. ``reminder_tasks``);
# ``Reminder is Activity`` and ``ReminderStatus is ActivityStatus``
# post-Phase-1.3, so the alias is a free identity rename.
from backend.app.models.reminder import Reminder as Activity, ReminderStatus as ActivityStatus
from backend.app.models.user import User


# Activity statuses that mean "no operator action expected" — closed
# enum from ADR-012 §6 plus the `cancelled` terminal. The legacy
# values (`new` / `pending` / `sent` / `overdue`) are normalised to
# `planned` by the activity_layer_v1 migration on read; we keep them
# out of the terminal set so they remain "active" candidates for
# cancellation here.
_PLANNER_TERMINAL_STATUSES = frozenset({"done", "cancelled"})

_CANCEL_REASON = "timeoff_approved"


def _parse_iso_date(value: str) -> datetime | None:
    """Parse "YYYY-MM-DD" to a naive datetime at 00:00. Returns None on
    malformed input so the caller can decide whether to bail loudly."""
    s = str(value or "").strip()
    if not s:
        return None
    try:
        # `datetime.fromisoformat` accepts "YYYY-MM-DD" since 3.7.
        return datetime.fromisoformat(s)
    except ValueError:
        return None


async def _resolve_user_tz(db: AsyncSession, user_id: str) -> ZoneInfo | timezone:
    """Look up the requester's working-hours tz. Falls back to UTC if
    the user has no schedule or the tz string is invalid. Centralised so
    the helper isn't sensitive to where exactly the tz lives."""
    user = await db.get(User, str(user_id))
    if user is None:
        return timezone.utc
    extra = user.extra if isinstance(user.extra, dict) else {}
    wh = extra.get("working_hours_v1") if isinstance(extra, dict) else None
    if not isinstance(wh, dict):
        return timezone.utc
    tz_name = wh.get("tz")
    tz_str = str(tz_name).strip() if isinstance(tz_name, str) else ""
    if not tz_str:
        return timezone.utc
    try:
        return ZoneInfo(tz_str)
    except Exception:
        return timezone.utc


def _utc_bounds_for_local_date_range(
    start_date_local: datetime,
    end_date_local: datetime,
    tz: ZoneInfo | timezone,
) -> tuple[datetime, datetime]:
    """Return UTC `[start_inclusive, end_exclusive)` for the calendar
    range `[start_date 00:00, end_date 24:00)` interpreted in `tz`.

    Using an exclusive upper bound matches SQLAlchemy's idiomatic
    `between`-replacement (`>= start AND < end`) and avoids the
    "should I include 23:59:59?" edge case entirely."""
    start_local = start_date_local.replace(
        hour=0, minute=0, second=0, microsecond=0, tzinfo=tz
    )
    # End is exclusive: end_date + 1 day at 00:00.
    end_exclusive_local = end_date_local.replace(
        hour=0, minute=0, second=0, microsecond=0, tzinfo=tz
    ) + timedelta(days=1)
    return (
        start_local.astimezone(timezone.utc),
        end_exclusive_local.astimezone(timezone.utc),
    )


def _stash_reason(payload: Any, *, request_id: str | None) -> Dict[str, Any]:
    """Merge `_cancelled_reason` and `_timeoff_request_id` into the
    existing payload. Existing keys are preserved — defensive merge,
    not an overwrite."""
    new_payload = dict(payload) if isinstance(payload, dict) else {}
    new_payload["_cancelled_reason"] = _CANCEL_REASON
    if request_id:
        new_payload["_timeoff_request_id"] = str(request_id)
    return new_payload


async def cancel_assignee_schedule_during_timeoff(
    db: AsyncSession,
    *,
    tenant_id: str,
    assignee_id: str,
    start_date: str,
    end_date: str,
    request_id: str | None = None,
) -> Dict[str, int]:
    """Cancel pending reminders + active planner events for `assignee_id`
    that fall within the approved time-off window. See module docstring
    for the full contract.

    Returns:
        Dict with keys `reminders_cancelled` and `planner_events_cancelled`.
        Both are 0 on no-op (e.g. malformed dates, no matching rows).
    """
    counts = {"reminders_cancelled": 0, "planner_events_cancelled": 0}

    start_local = _parse_iso_date(start_date)
    end_local = _parse_iso_date(end_date)
    if start_local is None or end_local is None or end_local < start_local:
        # Defensive — `_validate_iso_date_range` upstream already
        # rejects this, but the cleanup helper shouldn't depend on
        # that. Returning empty counts is safer than raising.
        return counts

    tz = await _resolve_user_tz(db, assignee_id)
    window_start_utc, window_end_utc = _utc_bounds_for_local_date_range(
        start_local, end_local, tz
    )

    now_utc = datetime.now(timezone.utc)

    # --- Reminder-style activities (deadline-only, no time slot) ---
    # Reminder-style rows have ``starts_at IS NULL`` and we anchor the
    # window on ``due_at`` — same semantics as the legacy reminders
    # cleanup. ``ActivityStatus.planned`` covers the canonical
    # "active" status; the legacy ``pending`` value is collapsed to
    # ``planned`` by ``activity_layer_v1`` migration §3 on read but
    # may still exist on rows that were not yet touched, so we accept
    # both via ``status NOT IN terminal``.
    reminders_stmt = sa.select(Activity).where(
        Activity.tenant_id == str(tenant_id),
        Activity.assigned_to_user_id == str(assignee_id),
        sa.func.lower(Activity.status).notin_(_PLANNER_TERMINAL_STATUSES),
        Activity.starts_at.is_(None),
        Activity.due_at >= window_start_utc,
        Activity.due_at < window_end_utc,
    )
    reminders = (await db.execute(reminders_stmt)).scalars().all()
    for reminder in reminders:
        reminder.status = ActivityStatus.done
        reminder.completed_at = now_utc
        reminder.metadata_ = _stash_reason(reminder.metadata_, request_id=request_id)
    counts["reminders_cancelled"] = len(reminders)

    # --- Planner-style activities (time-bound, has start slot) ---
    # Time-bound rows have ``starts_at IS NOT NULL``. The legacy
    # ``communication_planner_events`` table is absorbed into
    # ``activities`` (Phase 2.1 backfill — see
    # ``alembic/versions/202607150004_planner_tasks_into_activities.py``);
    # we filter on ``starts_at`` rather than ``due_at`` because the
    # planner UI anchors visualisation on the slot start, not the
    # deadline.
    planner_stmt = sa.select(Activity).where(
        Activity.tenant_id == str(tenant_id),
        Activity.assigned_to_user_id == str(assignee_id),
        # Active only — exclude already-terminal rows.
        sa.func.lower(Activity.status).notin_(_PLANNER_TERMINAL_STATUSES),
        Activity.starts_at.is_not(None),
        Activity.starts_at >= window_start_utc,
        Activity.starts_at < window_end_utc,
    )
    planner_events = (await db.execute(planner_stmt)).scalars().all()
    for event in planner_events:
        event.status = ActivityStatus.cancelled
        event.cancelled_at = now_utc
        event.metadata_ = _stash_reason(event.metadata_, request_id=request_id)
    counts["planner_events_cancelled"] = len(planner_events)

    await db.flush()
    return counts


__all__ = ["cancel_assignee_schedule_during_timeoff"]
