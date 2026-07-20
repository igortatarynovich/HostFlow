"""Episode-level notification idempotency (SLA breach, not lead lifetime)."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from backend.app.models.user_notification import UserNotification
from backend.app.services import user_notifications as un


@pytest.mark.asyncio
async def test_idempotent_create_100_times_one_row(db) -> None:
    tenant_id = str(uuid4())
    user_id = str(uuid4())
    lead_id = str(uuid4())
    entered = datetime(2026, 7, 1, 12, 0, 0, tzinfo=timezone.utc)
    source_event_id = f"lead_stuck_stage:v2:{lead_id}:new:{entered.strftime('%Y%m%dT%H%M%SZ')}"

    ids = set()
    created_flags = []
    for _ in range(100):
        row = await un.create_notification(
            db,
            tenant_id=tenant_id,
            user_id=user_id,
            event_type="lead_stuck_stage",
            entity_type="lead",
            entity_id=lead_id,
            source_event_id=source_event_id,
            require_idempotency_key=True,
            payload={"source_event_id": source_event_id, "title": "Lead stuck in stage"},
            dedupe_window_minutes=60 * 24 * 30,
        )
        assert row is not None
        ids.add(str(row.id))
        created_flags.append(bool(getattr(row, "_hf_notification_created", False)))
        await db.flush()

    await db.commit()
    assert len(ids) == 1
    assert created_flags[0] is True
    assert all(flag is False for flag in created_flags[1:])

    count = (
        await db.execute(
            select(func.count())
            .select_from(UserNotification)
            .where(
                UserNotification.tenant_id == tenant_id,
                UserNotification.user_id == user_id,
                UserNotification.event_type == "lead_stuck_stage",
                UserNotification.entity_id == lead_id,
            )
        )
    ).scalar_one()
    assert int(count) == 1

    # Survives is_read flip — still one row for the same episode.
    only = (
        await db.execute(
            select(UserNotification).where(UserNotification.id == next(iter(ids))).limit(1)
        )
    ).scalar_one()
    only.is_read = True
    await db.commit()

    again = await un.create_notification(
        db,
        tenant_id=tenant_id,
        user_id=user_id,
        event_type="lead_stuck_stage",
        entity_type="lead",
        entity_id=lead_id,
        source_event_id=source_event_id,
        require_idempotency_key=True,
        payload={"source_event_id": source_event_id},
    )
    await db.commit()
    assert again is not None
    assert str(again.id) == next(iter(ids))


@pytest.mark.asyncio
async def test_new_episode_after_read_creates_new_row(db) -> None:
    """Old stuck episode read + new stage stay → new notification row."""
    tenant_id = str(uuid4())
    user_id = str(uuid4())
    lead_id = str(uuid4())
    ep1 = f"lead_stuck_stage:v2:{lead_id}:new:20260701T120000Z"
    ep2 = f"lead_stuck_stage:v2:{lead_id}:contacted:20260710T090000Z"

    first = await un.create_notification(
        db,
        tenant_id=tenant_id,
        user_id=user_id,
        event_type="lead_stuck_stage",
        entity_type="lead",
        entity_id=lead_id,
        source_event_id=ep1,
        require_idempotency_key=True,
        payload={"source_event_id": ep1, "stage": "new"},
    )
    await db.commit()
    assert first is not None
    assert getattr(first, "_hf_notification_created", False) is True

    first.is_read = True
    await db.commit()

    second = await un.create_notification(
        db,
        tenant_id=tenant_id,
        user_id=user_id,
        event_type="lead_stuck_stage",
        entity_type="lead",
        entity_id=lead_id,
        source_event_id=ep2,
        require_idempotency_key=True,
        payload={"source_event_id": ep2, "stage": "contacted"},
    )
    await db.commit()
    assert second is not None
    assert getattr(second, "_hf_notification_created", False) is True
    assert str(second.id) != str(first.id)

    count = (
        await db.execute(
            select(func.count())
            .select_from(UserNotification)
            .where(
                UserNotification.tenant_id == tenant_id,
                UserNotification.event_type == "lead_stuck_stage",
                UserNotification.entity_id == lead_id,
            )
        )
    ).scalar_one()
    assert int(count) == 2


@pytest.mark.asyncio
async def test_scheduler_create_requires_idempotency_key(db) -> None:
    with pytest.raises(un.NotificationIdempotencyRequired):
        await un.create_notification(
            db,
            tenant_id=str(uuid4()),
            user_id=str(uuid4()),
            event_type="lead_stuck_stage",
            entity_type="lead",
            entity_id=str(uuid4()),
            require_idempotency_key=True,
            payload={"title": "missing key"},
        )
