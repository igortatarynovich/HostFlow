"""Regression cover for the notifications runaway (2026-07).

The scheduler re-evaluates its SLA sweeps every ``COMM_SCHEDULER_TICK_SECONDS``
(60s) and calls ``create_notification`` with a stable ``dedupe_key`` per finding.
Dedupe used to probe "the 50 newest unread rows of this event_type" and scan them
in Python, so once a tenant carried more than 50 unread rows of one event_type the
row holding the wanted key fell outside the probe, dedupe missed, and every tick
appended another copy. It compounded to ~3.6k rows per key.
"""

from __future__ import annotations

import pytest
import sqlalchemy as sa

from backend.app.models.user_notification import UserNotification
from backend.app.services.user_notifications import create_notification


async def _count(db, *, tenant_id: str, event_type: str) -> int:
    return int(
        (
            await db.execute(
                sa.select(sa.func.count())
                .select_from(UserNotification)
                .where(
                    UserNotification.tenant_id == tenant_id,
                    UserNotification.event_type == event_type,
                )
            )
        ).scalar_one()
    )


@pytest.mark.asyncio
async def test_dedupe_holds_beyond_the_probe_window(db, bootstrap) -> None:
    """Many distinct entities must not push each other out of the dedupe probe."""
    tenant_id = bootstrap["tenant_id"]
    user_id = bootstrap["admin_id"]
    event_type = "lead_stuck_stage_dedupe_probe"

    # 120 distinct leads — comfortably past the old 50-row probe window.
    lead_ids = [f"lead-probe-{i:04d}" for i in range(120)]

    async def sweep() -> None:
        """One scheduler tick: report every stuck lead exactly once."""
        for lid in lead_ids:
            await create_notification(
                db,
                tenant_id=tenant_id,
                user_id=user_id,
                event_type=event_type,
                entity_type="lead",
                entity_id=lid,
                payload={
                    "type": event_type,
                    "dedupe_key": f"{event_type}:{tenant_id}:{lid}:3:new",
                },
                dedupe_window_minutes=60 * 24 * 30,
            )
        await db.flush()

    await sweep()
    assert await _count(db, tenant_id=tenant_id, event_type=event_type) == len(lead_ids)

    # Five more ticks with the condition unchanged must add nothing.
    for _ in range(5):
        await sweep()

    assert await _count(db, tenant_id=tenant_id, event_type=event_type) == len(lead_ids)


@pytest.mark.asyncio
async def test_changed_dedupe_key_still_notifies(db, bootstrap) -> None:
    """A genuinely new condition on the same entity must still raise a notification."""
    tenant_id = bootstrap["tenant_id"]
    user_id = bootstrap["admin_id"]
    event_type = "lead_stuck_stage_key_change"
    lid = "lead-key-change-1"

    async def emit(stuck_days: int) -> None:
        await create_notification(
            db,
            tenant_id=tenant_id,
            user_id=user_id,
            event_type=event_type,
            entity_type="lead",
            entity_id=lid,
            payload={
                "type": event_type,
                "dedupe_key": f"{event_type}:{tenant_id}:{lid}:{stuck_days}:new",
            },
            dedupe_window_minutes=60 * 24 * 30,
        )
        await db.flush()

    await emit(3)
    await emit(3)
    assert await _count(db, tenant_id=tenant_id, event_type=event_type) == 1

    # Lead crossed the next SLA threshold -> new key -> one more notification.
    await emit(7)
    assert await _count(db, tenant_id=tenant_id, event_type=event_type) == 2


@pytest.mark.asyncio
async def test_distinct_entities_are_not_collapsed(db, bootstrap) -> None:
    """Entity scoping must not over-dedupe across different entities."""
    tenant_id = bootstrap["tenant_id"]
    user_id = bootstrap["admin_id"]
    event_type = "lead_stuck_stage_distinct"

    for lid in ("lead-a", "lead-b", "lead-c"):
        await create_notification(
            db,
            tenant_id=tenant_id,
            user_id=user_id,
            event_type=event_type,
            entity_type="lead",
            entity_id=lid,
            payload={"type": event_type, "dedupe_key": f"{event_type}:{lid}"},
            dedupe_window_minutes=60 * 24 * 30,
        )
    await db.flush()

    assert await _count(db, tenant_id=tenant_id, event_type=event_type) == 3


@pytest.mark.asyncio
async def test_entity_dedupe_without_key(db, bootstrap) -> None:
    """Callers that pass no dedupe_key still collapse on entity identity."""
    tenant_id = bootstrap["tenant_id"]
    user_id = bootstrap["admin_id"]
    event_type = "lead_stuck_stage_no_key"

    # The session runs with autoflush=False, so the dedupe probe only sees rows
    # already flushed — mirror how the scheduler drives it (one flush per finding).
    for _ in range(4):
        await create_notification(
            db,
            tenant_id=tenant_id,
            user_id=user_id,
            event_type=event_type,
            entity_type="lead",
            entity_id="lead-no-key",
            payload={"type": event_type},
            dedupe_window_minutes=60 * 24 * 30,
        )
        await db.flush()

    assert await _count(db, tenant_id=tenant_id, event_type=event_type) == 1
