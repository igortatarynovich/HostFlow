"""G-9 — bell hygiene: reminder state changes silence the bell.

Covers `services/user_notifications.mark_reminder_bell_notifications_read`
and its wiring inside `services/reminder_tasks.complete_reminder` /
`services/reminder_tasks.snooze_reminder`. The contract:

* Completing or snoozing a reminder MUST mark the matching unread
  `reminder_due` / `reminder_overdue` `UserNotification` rows as read.
* Notifications that don't reference this reminder (different `reminder_id`
  in payload) MUST be left untouched — we silence only what we acted on.

If this test starts failing, /app/tasks actions stopped quieting the bell
(or something started over-clearing the bell across unrelated reminders).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from backend.app.models.reminder import Reminder, ReminderStatus
from backend.app.models.user import User
from backend.app.models.user_notification import UserNotification
from backend.app.services import reminder_tasks


pytestmark = pytest.mark.anyio


async def _any_user_id_in_tenant(db, tenant_id: str) -> str:
    uid = await db.scalar(select(User.id).where(User.tenant_id == tenant_id).limit(1))
    assert uid is not None, "No seeded user found in tenant"
    return uid


async def _seed_reminder_with_bell(
    db,
    *,
    tenant_id: str,
    candidate_id: str,
    user_id: str,
    title: str = "Schedule interview",
) -> tuple[Reminder, UserNotification]:
    rid = str(uuid.uuid4())
    reminder = Reminder(
        id=rid,
        tenant_id=tenant_id,
        type="custom",
        entity_type="candidate",
        entity_id=candidate_id,
        owner_id=user_id,
        assignee_id=user_id,
        title=title,
        due_at=datetime.now(timezone.utc) + timedelta(hours=2),
        status=ReminderStatus.pending,
        channel="internal",
    )
    notif = UserNotification(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        user_id=user_id,
        event_type="reminder_due",
        entity_type="candidate",
        entity_id=candidate_id,
        payload={
            "type": "reminder_due",
            "reminder_id": rid,
            "source": "reminders",
            "dedupe_key": f"reminder:reminder_due:{rid}:{user_id}",
        },
        channel="in_app",
    )
    db.add_all([reminder, notif])
    await db.commit()
    await db.refresh(reminder)
    await db.refresh(notif)
    return reminder, notif


async def test_complete_reminder_marks_bell_notification_read(
    db,
    tenant_id: str,
    candidate_id: str,
) -> None:
    user_id = await _any_user_id_in_tenant(db, tenant_id)
    reminder, notif = await _seed_reminder_with_bell(
        db, tenant_id=tenant_id, candidate_id=candidate_id, user_id=user_id
    )
    assert notif.is_read is False

    await reminder_tasks.complete_reminder(
        db,
        tenant_id=tenant_id,
        reminder_id=reminder.id,
        actor_id=user_id,
        role="administrator",
    )
    await db.commit()

    refreshed = await db.scalar(
        select(UserNotification).where(UserNotification.id == notif.id)
    )
    assert refreshed is not None
    assert refreshed.is_read is True
    assert refreshed.read_at is not None
    payload = refreshed.payload or {}
    assert payload.get("auto_closed", {}).get("reason") == "reminder_completed"


async def test_snooze_reminder_marks_bell_notification_read(
    db,
    tenant_id: str,
    candidate_id: str,
) -> None:
    user_id = await _any_user_id_in_tenant(db, tenant_id)
    reminder, notif = await _seed_reminder_with_bell(
        db, tenant_id=tenant_id, candidate_id=candidate_id, user_id=user_id
    )
    assert notif.is_read is False

    await reminder_tasks.snooze_reminder(
        db,
        tenant_id=tenant_id,
        reminder_id=reminder.id,
        actor_id=user_id,
        role="administrator",
        minutes=60,
    )
    await db.commit()

    refreshed = await db.scalar(
        select(UserNotification).where(UserNotification.id == notif.id)
    )
    assert refreshed is not None
    assert refreshed.is_read is True
    payload = refreshed.payload or {}
    assert payload.get("auto_closed", {}).get("reason") == "reminder_snoozed"


async def test_unrelated_reminder_notification_is_not_touched(
    db,
    tenant_id: str,
    candidate_id: str,
) -> None:
    """Two reminders on the same candidate with two bell rows — completing
    reminder #1 must leave reminder #2's bell row alone."""
    user_id = await _any_user_id_in_tenant(db, tenant_id)
    rem_a, notif_a = await _seed_reminder_with_bell(
        db, tenant_id=tenant_id, candidate_id=candidate_id, user_id=user_id, title="A"
    )
    rem_b, notif_b = await _seed_reminder_with_bell(
        db, tenant_id=tenant_id, candidate_id=candidate_id, user_id=user_id, title="B"
    )

    await reminder_tasks.complete_reminder(
        db,
        tenant_id=tenant_id,
        reminder_id=rem_a.id,
        actor_id=user_id,
        role="administrator",
    )
    await db.commit()

    a = await db.scalar(select(UserNotification).where(UserNotification.id == notif_a.id))
    b = await db.scalar(select(UserNotification).where(UserNotification.id == notif_b.id))
    assert a is not None and b is not None
    assert a.is_read is True, "reminder A's bell should be cleared"
    assert b.is_read is False, "reminder B's bell must NOT be cleared"
