"""G-4 stage 4 — `cancel_assignee_schedule_during_timeoff` cancels
pending reminders and active planner events of an assignee whose
time-off was just approved.

Contract under test:
  * Pending reminders inside the window → status flipped to `cancelled`,
    payload records the reason and the time-off request id.
  * Active planner events inside the window → status flipped to
    `cancelled` with the same payload markers.
  * Already-completed/cancelled rows are NOT touched (no rewriting
    history).
  * Rows OUTSIDE the window are left alone — same assignee, but the
    window only spans Mon-Fri, so a reminder on Saturday survives.
  * Rows for OTHER assignees are left alone (cross-user safety).
  * Tz handling: dates are interpreted in the requester's local tz
    (working_hours_v1.tz), so a reminder at "Saturday 23:30 Warsaw"
    is inside a "Friday-Saturday" range when end_date=Saturday.
  * Malformed dates → no-op return, no crash.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import select

# Phase 2.1 (ADR-012, 2026-05-09): the legacy ``Reminder`` /
# ``CommunicationPlannerEvent`` writes are blocked by the
# ``activity_layer_v1`` views; tests now seed directly through
# ``Activity`` (the canonical ORM) — split between reminder-style
# (``starts_at IS NULL``) and planner-style (``starts_at IS NOT NULL``)
# rows. The legacy ``ReminderStatus`` constants stay because the
# values themselves (``"pending"``, ``"done"``) match what the service
# enforces.
# Phase 2.1 (ADR-012, 2026-05-09): use the ``backend.app.models.reminder``
# alias module to fetch ``Activity`` (``Reminder is Activity`` post-
# Phase-1.3) — going through ``backend.app.models.activity`` directly
# triggers the duplicate-package-path footgun under Docker.
from backend.app.models.reminder import (
    Reminder as Activity,
    ReminderStatus,
    ReminderStatus as ActivityStatus,
)
from backend.app.models.user import User
from backend.app.services.timeoff_cleanup import (
    cancel_assignee_schedule_during_timeoff,
)
from backend.app.services.working_hours_presets import preset_to_working_hours_v1


pytestmark = pytest.mark.anyio


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _first_user_id(db, tenant_id: str) -> str:
    uid = await db.scalar(select(User.id).where(User.tenant_id == tenant_id).limit(1))
    assert uid is not None
    return uid


async def _set_user_tz_warsaw(db, user_id: str) -> None:
    """Anchor the user's timezone to Europe/Warsaw via the canonical
    9-17 preset. The preset carries `tz: Europe/Warsaw`, which the
    cleanup helper reads to interpret date strings."""
    user = await db.get(User, user_id)
    assert user is not None
    extra = dict(user.extra or {}) if isinstance(user.extra, dict) else {}
    sched = preset_to_working_hours_v1("weekdays_9_17")
    assert sched is not None
    extra["working_hours_v1"] = sched
    user.extra = extra
    await db.commit()


def _next_target_monday() -> datetime:
    """Same convention as the other G-4 tests — anchor on a future
    Monday. Cleanup helper doesn't care about now-clamping (it's
    looking at due_at, not creating reminders), but using future
    anchors keeps the data clearly separated from anything seeded
    by other tests."""
    now = datetime.now(timezone.utc)
    days_ahead = (7 - now.weekday()) % 7 or 7
    days_ahead += 7
    target = now + timedelta(days=days_ahead)
    return target.replace(hour=0, minute=0, second=0, microsecond=0)


def _warsaw_at(monday_utc: datetime, weekday_offset: int, hour: int, minute: int = 0) -> datetime:
    """Return UTC instant for `hour:minute` Warsaw on `monday + offset`
    days. Uses zoneinfo so DST is correct year-round."""
    base = monday_utc + timedelta(days=weekday_offset)
    local = base.astimezone(ZoneInfo("Europe/Warsaw")).replace(
        hour=hour, minute=minute, second=0, microsecond=0
    )
    return local.astimezone(timezone.utc)


async def _seed_reminder(
    db,
    *,
    tenant_id: str,
    user_id: str,
    candidate_id: str,
    due_at: datetime,
    status: str = ReminderStatus.pending,
    title: str = "Call candidate",
) -> Activity:
    """Seed a deadline-only (``starts_at IS NULL``) Activity row that
    plays the role of a reminder under Phase 2.1."""
    rem = Activity(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        type="custom",
        related_entity_type="candidate",
        related_entity_id=candidate_id,
        owner_id=user_id,
        assigned_to_user_id=user_id,
        title=title,
        due_at=due_at,
        starts_at=None,
        status=status,
        channel="internal",
    )
    db.add(rem)
    await db.commit()
    await db.refresh(rem)
    return rem


async def _seed_planner_event(
    db,
    *,
    tenant_id: str,
    user_id: str,
    start_at: datetime,
    end_at: datetime | None = None,
    status: str = ActivityStatus.planned,
    title: str = "Interview",
) -> Activity:
    """Seed a time-bound (``starts_at IS NOT NULL``) Activity row that
    plays the role of a planner event under Phase 2.1. The legacy
    ``kind="meeting"`` semantics are preserved in
    ``metadata.planner.kind``."""
    rem_at = end_at or (start_at + timedelta(hours=1))
    ev = Activity(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        type="meeting",
        related_entity_type="user",
        related_entity_id=user_id,
        title=title,
        status=status,
        priority="normal",
        starts_at=start_at,
        due_at=rem_at,
        owner_id=user_id,
        assigned_to_user_id=user_id,
        source="manual",
        metadata_={"planner": {"kind": "meeting"}},
    )
    db.add(ev)
    await db.commit()
    await db.refresh(ev)
    return ev


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_cancels_pending_reminders_inside_window(
    db, tenant_id: str, candidate_id: str
) -> None:
    user_id = await _first_user_id(db, tenant_id)
    await _set_user_tz_warsaw(db, user_id)
    monday = _next_target_monday()
    # Reminder on Wednesday 10:00 Warsaw — inside the Mon-Fri window.
    inside_due = _warsaw_at(monday, weekday_offset=2, hour=10)
    rem = await _seed_reminder(
        db, tenant_id=tenant_id, user_id=user_id, candidate_id=candidate_id, due_at=inside_due
    )

    # Build date strings for Mon-Fri.
    monday_local = monday.astimezone(ZoneInfo("Europe/Warsaw")).date()
    friday_local = monday_local + timedelta(days=4)

    request_id = "req-abc-123"
    counts = await cancel_assignee_schedule_during_timeoff(
        db,
        tenant_id=tenant_id,
        assignee_id=user_id,
        start_date=monday_local.isoformat(),
        end_date=friday_local.isoformat(),
        request_id=request_id,
    )
    await db.commit()

    # Counts assertion is per-row to avoid cross-test pollution: other
    # G-4 tests seed reminders for the same user on the same future
    # Monday (test_reminder_working_hours_shift), and they too land
    # inside the Mon-Fri window — they're equally legitimate cancels,
    # but inflate the count from this test's POV.
    assert counts["reminders_cancelled"] >= 1
    refreshed = await db.scalar(select(Activity).where(Activity.id == rem.id))
    assert refreshed is not None
    assert refreshed.status == ActivityStatus.done
    payload = refreshed.metadata_ or {}
    assert payload.get("_cancelled_reason") == "timeoff_approved"
    assert payload.get("_timeoff_request_id") == request_id


async def test_does_not_cancel_completed_reminders(
    db, tenant_id: str, candidate_id: str
) -> None:
    """Already-completed reminders inside the window must stay
    `done`. Cleanup must not rewrite history — operators rely on
    completion timestamps for SLA reporting."""
    user_id = await _first_user_id(db, tenant_id)
    await _set_user_tz_warsaw(db, user_id)
    monday = _next_target_monday()
    inside_due = _warsaw_at(monday, weekday_offset=2, hour=10)
    rem = await _seed_reminder(
        db,
        tenant_id=tenant_id,
        user_id=user_id,
        candidate_id=candidate_id,
        due_at=inside_due,
        status=ReminderStatus.done,
    )

    monday_local = monday.astimezone(ZoneInfo("Europe/Warsaw")).date()
    friday_local = monday_local + timedelta(days=4)
    await cancel_assignee_schedule_during_timeoff(
        db,
        tenant_id=tenant_id,
        assignee_id=user_id,
        start_date=monday_local.isoformat(),
        end_date=friday_local.isoformat(),
    )
    await db.commit()

    # Per-row assertion — counts may be > 0 due to other tests seeding
    # pending reminders on the same future Monday for the same user.
    refreshed = await db.scalar(select(Activity).where(Activity.id == rem.id))
    assert refreshed is not None
    assert refreshed.status == ActivityStatus.done


async def test_does_not_cancel_reminder_outside_window(
    db, tenant_id: str, candidate_id: str
) -> None:
    """Reminder on the Saturday after the Mon-Fri window must survive."""
    user_id = await _first_user_id(db, tenant_id)
    await _set_user_tz_warsaw(db, user_id)
    monday = _next_target_monday()
    saturday_due = _warsaw_at(monday, weekday_offset=5, hour=10)
    rem = await _seed_reminder(
        db, tenant_id=tenant_id, user_id=user_id, candidate_id=candidate_id, due_at=saturday_due
    )

    monday_local = monday.astimezone(ZoneInfo("Europe/Warsaw")).date()
    friday_local = monday_local + timedelta(days=4)
    await cancel_assignee_schedule_during_timeoff(
        db,
        tenant_id=tenant_id,
        assignee_id=user_id,
        start_date=monday_local.isoformat(),
        end_date=friday_local.isoformat(),
    )
    await db.commit()

    # Per-row assertion — what matters is the Saturday reminder
    # survived. Counts may be non-zero from sibling tests.
    refreshed = await db.scalar(select(Activity).where(Activity.id == rem.id))
    assert refreshed is not None
    assert refreshed.status == ReminderStatus.pending


async def test_cancels_active_planner_events_inside_window(
    db, tenant_id: str
) -> None:
    user_id = await _first_user_id(db, tenant_id)
    await _set_user_tz_warsaw(db, user_id)
    monday = _next_target_monday()
    inside_start = _warsaw_at(monday, weekday_offset=2, hour=14)
    ev = await _seed_planner_event(
        db, tenant_id=tenant_id, user_id=user_id, start_at=inside_start
    )

    monday_local = monday.astimezone(ZoneInfo("Europe/Warsaw")).date()
    friday_local = monday_local + timedelta(days=4)
    counts = await cancel_assignee_schedule_during_timeoff(
        db,
        tenant_id=tenant_id,
        assignee_id=user_id,
        start_date=monday_local.isoformat(),
        end_date=friday_local.isoformat(),
        request_id="req-planner-1",
    )
    await db.commit()

    assert counts["planner_events_cancelled"] >= 1
    refreshed = await db.scalar(select(Activity).where(Activity.id == ev.id))
    assert refreshed is not None
    assert refreshed.status == ActivityStatus.cancelled
    payload = refreshed.metadata_ or {}
    assert payload.get("_cancelled_reason") == "timeoff_approved"
    assert payload.get("_timeoff_request_id") == "req-planner-1"


async def test_does_not_cancel_done_planner_events(db, tenant_id: str) -> None:
    user_id = await _first_user_id(db, tenant_id)
    await _set_user_tz_warsaw(db, user_id)
    monday = _next_target_monday()
    inside_start = _warsaw_at(monday, weekday_offset=2, hour=14)
    ev = await _seed_planner_event(
        db,
        tenant_id=tenant_id,
        user_id=user_id,
        start_at=inside_start,
        status="done",
    )

    monday_local = monday.astimezone(ZoneInfo("Europe/Warsaw")).date()
    friday_local = monday_local + timedelta(days=4)
    await cancel_assignee_schedule_during_timeoff(
        db,
        tenant_id=tenant_id,
        assignee_id=user_id,
        start_date=monday_local.isoformat(),
        end_date=friday_local.isoformat(),
    )
    await db.commit()

    refreshed = await db.scalar(select(Activity).where(Activity.id == ev.id))
    assert refreshed is not None
    assert refreshed.status == ActivityStatus.done


async def test_does_not_cancel_other_assignees_rows(
    db, tenant_id: str, candidate_id: str
) -> None:
    """Two users in the same tenant — cleanup for user A must not touch
    user B's reminder, even when both fall inside the same date window."""
    user_a = await _first_user_id(db, tenant_id)
    await _set_user_tz_warsaw(db, user_a)

    # Find a different user in the same tenant.
    other_users = (
        await db.execute(
            select(User.id).where(User.tenant_id == tenant_id, User.id != user_a).limit(1)
        )
    ).scalar_one_or_none()
    if not other_users:
        pytest.skip("Tenant has only one user; cross-user safety test needs two.")
    user_b = other_users

    monday = _next_target_monday()
    inside_due = _warsaw_at(monday, weekday_offset=2, hour=10)
    rem_a = await _seed_reminder(
        db, tenant_id=tenant_id, user_id=user_a, candidate_id=candidate_id, due_at=inside_due
    )
    # Seed a reminder for user_b at the same time.
    rem_b = Activity(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        type="custom",
        related_entity_type="candidate",
        related_entity_id=candidate_id,
        owner_id=user_b,
        assigned_to_user_id=user_b,
        title="B's reminder",
        due_at=inside_due,
        starts_at=None,
        status=ReminderStatus.pending,
        channel="internal",
    )
    db.add(rem_b)
    await db.commit()
    await db.refresh(rem_b)

    monday_local = monday.astimezone(ZoneInfo("Europe/Warsaw")).date()
    friday_local = monday_local + timedelta(days=4)
    await cancel_assignee_schedule_during_timeoff(
        db,
        tenant_id=tenant_id,
        assignee_id=user_a,
        start_date=monday_local.isoformat(),
        end_date=friday_local.isoformat(),
    )
    await db.commit()

    # Per-row assertion — what matters is the cross-user safety: A's
    # row was auto-completed, B's was not. Total counts may be > 1 due to
    # other tests' seeded reminders for user A.
    a = await db.scalar(select(Activity).where(Activity.id == rem_a.id))
    b = await db.scalar(select(Activity).where(Activity.id == rem_b.id))
    assert a is not None and b is not None
    assert a.status == ActivityStatus.done
    assert b.status == ReminderStatus.pending, "B's reminder must NOT be auto-completed"


async def test_malformed_dates_return_zero_counts(db, tenant_id: str) -> None:
    """Defensive: garbage-in returns empty counts, doesn't raise. The
    upstream `_validate_iso_date_range` should have caught it, but this
    helper is independently safe to call."""
    user_id = await _first_user_id(db, tenant_id)
    counts = await cancel_assignee_schedule_during_timeoff(
        db,
        tenant_id=tenant_id,
        assignee_id=user_id,
        start_date="not-a-date",
        end_date="2025-06-02",
    )
    assert counts["reminders_cancelled"] == 0
    assert counts["planner_events_cancelled"] == 0
    # End-before-start.
    counts = await cancel_assignee_schedule_during_timeoff(
        db,
        tenant_id=tenant_id,
        assignee_id=user_id,
        start_date="2025-06-10",
        end_date="2025-06-01",
    )
    assert counts == {"reminders_cancelled": 0, "planner_events_cancelled": 0}
