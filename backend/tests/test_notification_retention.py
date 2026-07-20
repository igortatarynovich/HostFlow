"""Retention + unread-cap policy for in-app notifications."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from backend.app.core.settings import settings
from backend.app.models.user_notification import UserNotification
from backend.app.services.notification_retention import (
    enforce_unread_cap_for_user,
    purge_expired_notifications,
)
from backend.app.services import user_notifications as un


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


@pytest.mark.asyncio
async def test_purge_deletes_read_unread_and_critical_by_ttl(db) -> None:
    tenant_id = str(uuid4())
    user_id = str(uuid4())
    now = datetime.now(timezone.utc)

    rows = [
        UserNotification(
            id=str(uuid4()),
            tenant_id=tenant_id,
            user_id=user_id,
            event_type="reminder_due",
            priority="normal",
            channel="in_app",
            is_read=True,
            created_at=now - timedelta(hours=settings.notifications_retention_read_hours + 1),
            updated_at=now,
        ),
        UserNotification(
            id=str(uuid4()),
            tenant_id=tenant_id,
            user_id=user_id,
            event_type="reminder_due",
            priority="normal",
            channel="in_app",
            is_read=False,
            created_at=now - timedelta(days=settings.notifications_retention_unread_days + 1),
            updated_at=now,
        ),
        UserNotification(
            id=str(uuid4()),
            tenant_id=tenant_id,
            user_id=user_id,
            event_type="communications_sla_overdue",
            priority="critical",
            channel="in_app",
            is_read=False,
            created_at=now - timedelta(days=settings.notifications_retention_critical_days + 1),
            updated_at=now,
        ),
        # still fresh — must survive
        UserNotification(
            id=str(uuid4()),
            tenant_id=tenant_id,
            user_id=user_id,
            event_type="reminder_due",
            priority="normal",
            channel="in_app",
            is_read=False,
            created_at=now - timedelta(hours=1),
            updated_at=now,
        ),
    ]
    for row in rows:
        db.add(row)
    await db.commit()

    stats = await purge_expired_notifications(db, now=now, tenant_id=tenant_id, max_batches=10)
    await db.commit()

    assert stats["read"] >= 1
    assert stats["unread"] >= 1
    assert stats["critical"] >= 1

    left = (
        await db.execute(
            select(func.count())
            .select_from(UserNotification)
            .where(UserNotification.tenant_id == tenant_id)
        )
    ).scalar_one()
    assert int(left) == 1


@pytest.mark.asyncio
async def test_unread_cap_keeps_critical_and_newest(db) -> None:
    tenant_id = str(uuid4())
    user_id = str(uuid4())
    now = datetime.now(timezone.utc)
    # 5 normal + 2 critical; cap=5 should delete 2 oldest normal, keep critical.
    for i in range(5):
        db.add(
            UserNotification(
                id=str(uuid4()),
                tenant_id=tenant_id,
                user_id=user_id,
                event_type="reminder_due",
                priority="normal",
                channel="in_app",
                is_read=False,
                created_at=_aware(now - timedelta(minutes=10 - i)),
                updated_at=now,
            )
        )
    for _ in range(2):
        db.add(
            UserNotification(
                id=str(uuid4()),
                tenant_id=tenant_id,
                user_id=user_id,
                event_type="communications_sla_overdue",
                priority="critical",
                channel="in_app",
                is_read=False,
                created_at=_aware(now - timedelta(minutes=30)),
                updated_at=now,
            )
        )
    await db.commit()

    deleted = await enforce_unread_cap_for_user(
        db, tenant_id=tenant_id, user_id=user_id, max_unread=5
    )
    await db.commit()
    assert deleted == 2

    remaining = (
        await db.execute(
            select(UserNotification).where(
                UserNotification.tenant_id == tenant_id,
                UserNotification.user_id == user_id,
                UserNotification.is_read.is_(False),
            )
        )
    ).scalars().all()
    assert len(remaining) == 5
    assert sum(1 for r in remaining if r.priority == "critical") == 2


@pytest.mark.asyncio
async def test_list_notifications_hard_caps_limit(db) -> None:
    tenant_id = str(uuid4())
    user_id = str(uuid4())
    now = datetime.now(timezone.utc)
    for i in range(5):
        db.add(
            UserNotification(
                id=str(uuid4()),
                tenant_id=tenant_id,
                user_id=user_id,
                event_type="reminder_due",
                priority="normal",
                channel="in_app",
                is_read=False,
                created_at=now - timedelta(minutes=i),
                updated_at=now,
            )
        )
    await db.commit()

    prev = settings.notifications_list_max_limit
    try:
        settings.notifications_list_max_limit = 3
        rows = await un.list_notifications(
            db, tenant_id=tenant_id, user_id=user_id, limit=200, include_completed_entities=True
        )
        assert len(rows) == 3
    finally:
        settings.notifications_list_max_limit = prev
