"""G-4 stage 2 — `create_reminder` shifts `due_at` to the assignee's
next working window when the tenant opts in.

Contract under test:
  * Default (no tenant setting): no shift, behaviour unchanged.
  * `tenant.settings.reminders.shift_due_at_outside_hours = True`:
      - Assignee with `working_hours_v1` AND `due_at` outside it →
        due_at is moved to the next opening; `payload._working_hours_shift`
        records the original time and the delta.
      - Assignee with no schedule → no shift (callers shouldn't see
        different behaviour just because someone never set their hours).
      - due_at already inside a window → no shift.
      - remind_at delta is preserved (lead-time invariant).

These tests directly exercise the service function (no HTTP) so they
don't depend on the reminder-create endpoint's request schema.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from backend.app.models.reminder import Reminder
from backend.app.models.tenant import Tenant
from backend.app.models.user import User
from backend.app.services import reminder_tasks
from backend.app.services.working_hours_presets import preset_to_working_hours_v1


pytestmark = pytest.mark.anyio


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _enable_shift_on_tenant(db, tenant_id: str) -> None:
    """Toggle `tenant.settings.reminders.shift_due_at_outside_hours = True`.
    Has to merge into existing settings dict — overwriting would clobber
    other operations / billing keys."""
    tenant = await db.get(Tenant, tenant_id)
    assert tenant is not None
    settings = dict(tenant.settings or {}) if isinstance(tenant.settings, dict) else {}
    reminders = dict(settings.get("reminders") or {})
    reminders["shift_due_at_outside_hours"] = True
    settings["reminders"] = reminders
    tenant.settings = settings
    await db.commit()


async def _set_user_working_hours(db, user_id: str, preset: str = "weekdays_9_17") -> None:
    """Seed the assignee with a weekly schedule. Uses the canonical
    Warsaw 9-17 preset so the test math matches `test_working_hours_window`.
    """
    user = await db.get(User, user_id)
    assert user is not None
    extra = dict(user.extra or {}) if isinstance(user.extra, dict) else {}
    sched = preset_to_working_hours_v1(preset)
    assert sched is not None
    extra["working_hours_v1"] = sched
    user.extra = extra
    await db.commit()


async def _clear_user_working_hours(db, user_id: str) -> None:
    """Strip `working_hours_v1` from the user's extra. Required because
    `_init_data` is session-idempotent and previous tests mutate the
    same user. Without this, the "no schedule" test sees leftover state."""
    user = await db.get(User, user_id)
    assert user is not None
    extra = dict(user.extra or {}) if isinstance(user.extra, dict) else {}
    extra.pop("working_hours_v1", None)
    user.extra = extra
    await db.commit()


async def _clear_tenant_shift_setting(db, tenant_id: str) -> None:
    """Disable the shift policy. Same reason: tenant.settings persists
    across tests; explicit reset keeps each test's preconditions
    independent of execution order."""
    tenant = await db.get(Tenant, tenant_id)
    assert tenant is not None
    settings = dict(tenant.settings or {}) if isinstance(tenant.settings, dict) else {}
    reminders = dict(settings.get("reminders") or {})
    reminders.pop("shift_due_at_outside_hours", None)
    if reminders:
        settings["reminders"] = reminders
    else:
        settings.pop("reminders", None)
    tenant.settings = settings
    await db.commit()


async def _first_user_id(db, tenant_id: str) -> str:
    uid = await db.scalar(select(User.id).where(User.tenant_id == tenant_id).limit(1))
    assert uid is not None
    return uid


def _next_target_monday() -> datetime:
    """Return a Monday safely in the future (≥ 7 days from now) at
    01:00 UTC. Hard-coding a 2025 anchor became stale by 2026 — the
    `_normalize_remind_at` clamp pushed remind_at to `now`. Computing
    "next Monday + 7" relative to now keeps the test future-proof
    without mocking time."""
    now = datetime.now(timezone.utc)
    # Days until next Monday (weekday=0). +7 to ensure ≥ 7 days ahead
    # so even on Monday we land on the *next* Monday.
    days_ahead = (7 - now.weekday()) % 7 or 7
    days_ahead += 7
    target = now + timedelta(days=days_ahead)
    return target.replace(hour=1, minute=0, second=0, microsecond=0)


def _outside_hours_anchor() -> datetime:
    """Monday at 01:00 UTC = 03:00 Warsaw (CEST) or 02:00 Warsaw (CET).
    Either way, well before the 09:00 working-hours opening — guaranteed
    outside the schedule."""
    return _next_target_monday()


def _expected_shift_target(anchor: datetime) -> datetime:
    """09:00 Warsaw on the same Monday. We can't hard-code "07:00 UTC"
    because DST shifts the offset (CEST=+2 in summer, CET=+1 in winter).
    Compute via zoneinfo to stay correct year-round."""
    from zoneinfo import ZoneInfo

    local = anchor.astimezone(ZoneInfo("Europe/Warsaw")).replace(
        hour=9, minute=0, second=0, microsecond=0
    )
    return local.astimezone(timezone.utc)


def _inside_hours_anchor(anchor: datetime) -> datetime:
    """12:00 Warsaw on the same Monday — squarely inside 09:00–17:00."""
    from zoneinfo import ZoneInfo

    local = anchor.astimezone(ZoneInfo("Europe/Warsaw")).replace(
        hour=12, minute=0, second=0, microsecond=0
    )
    return local.astimezone(timezone.utc)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_no_shift_when_tenant_setting_off(
    db, tenant_id: str, candidate_id: str
) -> None:
    """Default tenant config: shift policy is OFF. due_at must be
    persisted exactly as provided, even when assignee has hours and
    the time falls outside them."""
    user_id = await _first_user_id(db, tenant_id)
    await _set_user_working_hours(db, user_id)
    await _clear_tenant_shift_setting(db, tenant_id)

    outside = _outside_hours_anchor()
    reminder = await reminder_tasks.create_reminder(
        db,
        tenant_id=tenant_id,
        actor_id=user_id,
        payload={
            "due_at": outside,
            "title": "Call candidate",
            "entity_type": "candidate",
            "entity_id": candidate_id,
            "assignee_id": user_id,
        },
    )
    assert reminder.due_at == outside
    payload = reminder.payload or {}
    assert "_working_hours_shift" not in payload, "shift diag must be absent when policy off"


async def test_shift_applied_when_setting_on_and_outside_hours(
    db, tenant_id: str, candidate_id: str
) -> None:
    """Tenant opted in + assignee has hours + due_at outside → shift to
    next window; payload records the original time."""
    user_id = await _first_user_id(db, tenant_id)
    await _set_user_working_hours(db, user_id)
    await _enable_shift_on_tenant(db, tenant_id)

    outside = _outside_hours_anchor()
    expected = _expected_shift_target(outside)
    reminder = await reminder_tasks.create_reminder(
        db,
        tenant_id=tenant_id,
        actor_id=user_id,
        payload={
            "due_at": outside,
            "title": "Call candidate",
            "entity_type": "candidate",
            "entity_id": candidate_id,
            "assignee_id": user_id,
        },
    )
    assert reminder.due_at == expected
    diag = (reminder.payload or {}).get("_working_hours_shift")
    assert isinstance(diag, dict), "shift diag MUST be stashed in payload for explainability"
    assert diag["original_due_at"] == outside.isoformat()
    assert diag["shifted_due_at"] == expected.isoformat()
    assert diag["reason"] == "outside_assignee_working_hours"
    # Delta is whatever it takes to reach 09:00 Warsaw from 01:00 UTC —
    # 6 h in summer (CEST), 7 h in winter (CET). Either way, positive.
    assert diag["delta_seconds"] > 0
    assert diag["delta_seconds"] == int((expected - outside).total_seconds())


async def test_no_shift_when_due_at_already_inside_window(
    db, tenant_id: str, candidate_id: str
) -> None:
    """Even with policy on + assignee schedule, an in-window due_at
    must not be touched."""
    user_id = await _first_user_id(db, tenant_id)
    await _set_user_working_hours(db, user_id)
    await _enable_shift_on_tenant(db, tenant_id)

    inside = _inside_hours_anchor(_outside_hours_anchor())
    reminder = await reminder_tasks.create_reminder(
        db,
        tenant_id=tenant_id,
        actor_id=user_id,
        payload={
            "due_at": inside,
            "title": "Call candidate",
            "entity_type": "candidate",
            "entity_id": candidate_id,
            "assignee_id": user_id,
        },
    )
    assert reminder.due_at == inside
    payload = reminder.payload or {}
    assert "_working_hours_shift" not in payload


async def test_no_shift_when_assignee_has_no_schedule(
    db, tenant_id: str, candidate_id: str
) -> None:
    """Policy on, no schedule on assignee → silent no-op. Operators
    should not be punished by behaviour change just because somebody on
    the team has not configured their hours."""
    user_id = await _first_user_id(db, tenant_id)
    await _clear_user_working_hours(db, user_id)
    await _enable_shift_on_tenant(db, tenant_id)

    outside = _outside_hours_anchor()
    reminder = await reminder_tasks.create_reminder(
        db,
        tenant_id=tenant_id,
        actor_id=user_id,
        payload={
            "due_at": outside,
            "title": "Call candidate",
            "entity_type": "candidate",
            "entity_id": candidate_id,
            "assignee_id": user_id,
        },
    )
    assert reminder.due_at == outside
    payload = reminder.payload or {}
    assert "_working_hours_shift" not in payload


async def test_remind_at_lead_time_preserved_after_shift(
    db, tenant_id: str, candidate_id: str
) -> None:
    """If caller passes an explicit remind_at, the same delta must be
    applied so the lead-time (e.g. 'remind 30 min before') survives the
    shift. Otherwise the alert window collapses or inverts."""
    user_id = await _first_user_id(db, tenant_id)
    await _set_user_working_hours(db, user_id)
    await _enable_shift_on_tenant(db, tenant_id)

    outside = _outside_hours_anchor()
    expected = _expected_shift_target(outside)
    explicit_remind = outside - timedelta(minutes=30)

    reminder = await reminder_tasks.create_reminder(
        db,
        tenant_id=tenant_id,
        actor_id=user_id,
        payload={
            "due_at": outside,
            "remind_at": explicit_remind,
            "title": "Call candidate",
            "entity_type": "candidate",
            "entity_id": candidate_id,
            "assignee_id": user_id,
        },
    )
    assert reminder.due_at == expected
    # remind_at must be exactly 30 min before the *shifted* due_at —
    # the lead-time invariant is preserved. (Both timestamps are in
    # the future, so `_normalize_remind_at`'s now-clamp doesn't fire.)
    expected_remind = expected - timedelta(minutes=30)
    assert reminder.remind_at == expected_remind
