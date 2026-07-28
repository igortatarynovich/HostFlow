"""Cover the notifications age-out sweep.

Without retention the bell table only grows; it reached ~1M rows for a handful of
real users in July 2026 and pinned a CPU core on polling.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
import sqlalchemy as sa

from backend.app.models.user_notification import UserNotification
from backend.app.services.notification_retention import purge_expired_notifications


async def _mk(
    db,
    *,
    tenant_id: str,
    user_id: str,
    age_days: int,
    is_read: bool,
    priority: str | None,
    marker: str,
) -> None:
    await db.execute(
        sa.insert(UserNotification.__table__).values(
            id=f"ret-{marker}",
            tenant_id=tenant_id,
            user_id=user_id,
            type="retention_probe",
            is_read=is_read,
            priority=priority,
            channel="in_app",
            created_at=datetime.now(timezone.utc) - timedelta(days=age_days),
            updated_at=datetime.now(timezone.utc),
        )
    )


async def _surviving(db, tenant_id: str) -> set[str]:
    rows = (
        await db.execute(
            sa.select(UserNotification.id).where(
                UserNotification.tenant_id == tenant_id,
                UserNotification.event_type == "retention_probe",
            )
        )
    ).scalars().all()
    return set(rows)


@pytest.mark.asyncio
async def test_retention_classes_have_separate_ttls(db, bootstrap) -> None:
    tenant_id = bootstrap["tenant_id"]
    user_id = bootstrap["admin_id"]

    # Defaults: read 30d, unread 90d, critical 180d.
    await _mk(db, tenant_id=tenant_id, user_id=user_id, age_days=40, is_read=True, priority="normal", marker="read-old")
    await _mk(db, tenant_id=tenant_id, user_id=user_id, age_days=10, is_read=True, priority="normal", marker="read-fresh")
    await _mk(db, tenant_id=tenant_id, user_id=user_id, age_days=100, is_read=False, priority="normal", marker="unread-old")
    await _mk(db, tenant_id=tenant_id, user_id=user_id, age_days=40, is_read=False, priority="normal", marker="unread-fresh")
    await _mk(db, tenant_id=tenant_id, user_id=user_id, age_days=200, is_read=False, priority="critical", marker="crit-old")
    await _mk(db, tenant_id=tenant_id, user_id=user_id, age_days=100, is_read=False, priority="critical", marker="crit-fresh")
    await db.flush()

    stats = await purge_expired_notifications(db, tenant_id=tenant_id)
    await db.flush()

    survivors = await _surviving(db, tenant_id)
    assert "ret-read-old" not in survivors
    assert "ret-unread-old" not in survivors
    assert "ret-crit-old" not in survivors

    # A read row younger than 30d, an unread one younger than 90d and a critical
    # one younger than 180d must all be kept.
    assert "ret-read-fresh" in survivors
    assert "ret-unread-fresh" in survivors
    assert "ret-crit-fresh" in survivors

    assert stats["total"] == 3


@pytest.mark.asyncio
async def test_retention_is_tenant_scoped(db, bootstrap) -> None:
    tenant_id = bootstrap["tenant_id"]
    user_id = bootstrap["admin_id"]

    await _mk(db, tenant_id=tenant_id, user_id=user_id, age_days=400, is_read=True, priority="normal", marker="mine")
    await _mk(db, tenant_id="other-tenant-xyz", user_id=user_id, age_days=400, is_read=True, priority="normal", marker="theirs")
    await db.flush()

    await purge_expired_notifications(db, tenant_id=tenant_id)
    await db.flush()

    assert "ret-mine" not in await _surviving(db, tenant_id)
    # Another tenant's row must be untouched by this tenant's sweep.
    assert "ret-theirs" in await _surviving(db, "other-tenant-xyz")


@pytest.mark.asyncio
async def test_retention_respects_batch_limit(db, bootstrap) -> None:
    tenant_id = bootstrap["tenant_id"]
    user_id = bootstrap["admin_id"]

    for i in range(10):
        await _mk(
            db, tenant_id=tenant_id, user_id=user_id, age_days=400,
            is_read=True, priority="normal", marker=f"batch-{i}",
        )
    await db.flush()

    stats = await purge_expired_notifications(db, tenant_id=tenant_id, batch_limit=4)
    await db.flush()

    # Bounded per run; the backlog drains across subsequent ticks.
    assert stats["read"] == 4
    assert len(await _surviving(db, tenant_id)) == 6
