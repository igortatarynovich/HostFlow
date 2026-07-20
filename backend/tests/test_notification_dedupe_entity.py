"""Regression: entity-bound notification dedupe must not scan only top-N rows."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from backend.app.models.user_notification import UserNotification
from backend.app.services import user_notifications as un


@pytest.mark.asyncio
async def test_create_notification_dedupes_by_entity_beyond_top50(db) -> None:
    tenant_id = str(uuid4())
    user_id = str(uuid4())
    now = datetime.now(timezone.utc)
    target_entity = str(uuid4())

    # Flood >50 newer unread of same type for other entities (old broken window).
    for i in range(60):
        db.add(
            UserNotification(
                id=str(uuid4()),
                tenant_id=tenant_id,
                user_id=user_id,
                event_type="lead_stuck_stage",
                priority="normal",
                channel="in_app",
                is_read=False,
                entity_type="lead",
                entity_id=str(uuid4()),
                payload={"dedupe_key": f"other:{i}"},
                created_at=now - timedelta(minutes=i),
                updated_at=now,
            )
        )
    # Older unread for the target entity — must still be found.
    existing_id = str(uuid4())
    db.add(
        UserNotification(
            id=existing_id,
            tenant_id=tenant_id,
            user_id=user_id,
            event_type="lead_stuck_stage",
            priority="normal",
            channel="in_app",
            is_read=False,
            entity_type="lead",
            entity_id=target_entity,
            payload={"dedupe_key": f"lead_stuck_stage:{target_entity}"},
            created_at=now - timedelta(hours=5),
            updated_at=now,
        )
    )
    await db.commit()

    again = await un.create_notification(
        db,
        tenant_id=tenant_id,
        user_id=user_id,
        event_type="lead_stuck_stage",
        entity_type="lead",
        entity_id=target_entity,
        payload={"dedupe_key": f"lead_stuck_stage:{target_entity}"},
        dedupe_window_minutes=60 * 24 * 30,
    )
    await db.commit()
    assert again is not None
    assert str(again.id) == existing_id
