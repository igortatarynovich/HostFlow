from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional, Sequence, Set

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models import User
from backend.app.models.user_notification import UserNotification
from backend.app.services import notifications as outbound
from backend.app.services import user_notifications
from backend.app.models.user import Role


@dataclass
class EventAudience:
    user_ids: Sequence[str] | None = None
    roles: Sequence[Role | str] | None = None


def _notifications_enabled(preferences: dict | None, event_type: str, channel: str) -> bool:
    if not isinstance(preferences, dict):
        return True
    notifications_pref = preferences.get("notifications")
    if not isinstance(notifications_pref, dict):
        return True
    event_pref = notifications_pref.get(event_type)
    if event_pref is None:
        return True
    if isinstance(event_pref, bool):
        return event_pref
    if not isinstance(event_pref, dict):
        return True
    enabled = event_pref.get("enabled", True)
    channels_pref = event_pref.get("channels")
    channel_enabled = True
    if isinstance(channels_pref, dict):
        value = channels_pref.get(channel)
        if isinstance(value, bool):
            channel_enabled = value
    return bool(enabled) and bool(channel_enabled)


async def _resolve_user_ids(
    db: AsyncSession,
    *,
    tenant_id: str,
    audience: EventAudience,
) -> Set[str]:
    user_ids: Set[str] = set()
    if audience.user_ids:
        user_ids.update(str(uid) for uid in audience.user_ids if uid)
    if audience.roles:
        normalized_roles = {
            (role if isinstance(role, str) else role.value)
            for role in audience.roles
        }
        if normalized_roles:
            stmt = select(User.id).where(
                User.is_active.is_(True),
                User.tenant_id == tenant_id,
                User.role.in_(normalized_roles),  # type: ignore[arg-type]
            )
            rows = await db.execute(stmt)
            user_ids.update(rows.scalars().all())
    return {uid for uid in user_ids if uid}


async def emit_event(
    db: AsyncSession,
    *,
    tenant_id: str,
    event_type: str,
    payload: dict,
    audience: EventAudience,
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    channel: str = "in_app",
    send_webhook: bool = False,
) -> Sequence[UserNotification]:
    """
    Persist notifications for recipients and optionally emit webhook.
    """
    recipients = await _resolve_user_ids(db, tenant_id=tenant_id, audience=audience)
    if not recipients:
        return []

    stmt = select(User).where(
        User.id.in_(recipients),
        User.is_active.is_(True),
    )
    rows = await db.execute(stmt)
    users = rows.scalars().all()

    created: list[UserNotification] = []
    for user in users:
        if not _notifications_enabled(user.preferences or {}, event_type, channel):
            continue
        notification = await user_notifications.create_notification(
            db,
            tenant_id=tenant_id,
            user_id=user.id,
            event_type=event_type,
            payload=payload,
            entity_type=entity_type,
            entity_id=entity_id,
            channel=channel,
        )
        created.append(notification)
        if send_webhook:
            await outbound.send_webhook(
                event_type,
                {
                    **payload,
                    "user_id": user.id,
                    "tenant_id": tenant_id,
                    "entity_type": entity_type,
                    "entity_id": entity_id,
                },
            )
    return created
