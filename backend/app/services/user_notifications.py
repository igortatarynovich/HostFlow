from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable, List, Optional
from uuid import uuid4

from sqlalchemy import and_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.user_notification import UserNotification


async def create_notification(
    db: AsyncSession,
    *,
    tenant_id: str,
    user_id: str,
    event_type: str,
    payload: Optional[dict] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    channel: str = "in_app",
    delivered_at: Optional[datetime] = None,
) -> UserNotification:
    notification = UserNotification(
        id=str(uuid4()),
        tenant_id=tenant_id,
        user_id=user_id,
        event_type=event_type,
        entity_type=entity_type,
        entity_id=entity_id,
        payload=payload or {},
        channel=channel,
        delivered_at=delivered_at,
    )
    db.add(notification)
    return notification


async def list_notifications(
    db: AsyncSession,
    *,
    tenant_id: str,
    user_id: str,
    limit: int = 50,
    include_read: bool = False,
) -> List[UserNotification]:
    stmt = (
        select(UserNotification)
        .where(
            UserNotification.tenant_id == tenant_id,
            UserNotification.user_id == user_id,
        )
        .order_by(UserNotification.created_at.desc())
        .limit(limit)
    )
    if not include_read:
        stmt = stmt.where(UserNotification.is_read.is_(False))
    rows = await db.execute(stmt)
    return list(rows.scalars().all())


async def mark_notifications_read(
    db: AsyncSession,
    *,
    tenant_id: str,
    user_id: str,
    notification_ids: Optional[Iterable[str]] = None,
    mark_all: bool = False,
) -> int:
    if not mark_all and not notification_ids:
        return 0

    now = datetime.now(timezone.utc)
    stmt = (
        update(UserNotification)
        .where(
            and_(
                UserNotification.tenant_id == tenant_id,
                UserNotification.user_id == user_id,
                UserNotification.is_read.is_(False),
            )
        )
        .values(is_read=True, read_at=now, updated_at=now)
    )
    if not mark_all and notification_ids:
        stmt = stmt.where(UserNotification.id.in_(list(notification_ids)))
    result = await db.execute(stmt)
    return result.rowcount or 0
