from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Iterable, List, Optional
from uuid import uuid4

from sqlalchemy import and_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.communication import CommunicationThread
from backend.app.models.reminder import Reminder, ReminderStatus
from backend.app.models.user_notification import UserNotification


def _infer_source(event_type: str) -> str:
    et = str(event_type or "").strip().lower()
    if et.startswith("communications_"):
        return "communications"
    if et.startswith("reminder_"):
        return "reminders"
    if et.startswith("handoff_"):
        return "handoff"
    if et.startswith("candidate_"):
        return "candidates"
    if et.startswith("lead_"):
        return "leads"
    return "system"


def _infer_severity(event_type: str) -> str:
    et = str(event_type or "").strip().lower()
    if "overdue" in et or "failed" in et:
        return "high"
    if "due" in et or "requested" in et:
        return "medium"
    return "low"


def _infer_requires_action(event_type: str) -> bool:
    et = str(event_type or "").strip().lower()
    return et in {
        "communications_sla_overdue",
        "communications_thread_escalated",
        "reminder_due",
        "reminder_overdue",
        "handoff_requested",
    }


def _normalize_payload(
    *,
    event_type: str,
    payload: Optional[dict],
    entity_type: Optional[str],
    entity_id: Optional[str],
) -> dict:
    data: dict[str, Any] = dict(payload or {})
    data["type"] = str(data.get("type") or event_type)
    data["source"] = str(data.get("source") or _infer_source(event_type))
    data["severity"] = str(data.get("severity") or _infer_severity(event_type))
    data["requires_action"] = bool(data.get("requires_action", _infer_requires_action(event_type)))
    if entity_type and "entity_type" not in data:
        data["entity_type"] = entity_type
    if entity_id and "entity_id" not in data:
        data["entity_id"] = entity_id
    if data.get("dedupe_key") is not None:
        data["dedupe_key"] = str(data.get("dedupe_key") or "").strip() or None
    return data


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
    dedupe_window_minutes: Optional[int] = None,
) -> UserNotification:
    normalized_payload = _normalize_payload(
        event_type=event_type,
        payload=payload,
        entity_type=entity_type,
        entity_id=entity_id,
    )
    dedupe_key = str(normalized_payload.get("dedupe_key") or "").strip() or None

    if dedupe_window_minutes is not None and int(dedupe_window_minutes) > 0:
        now = datetime.now(timezone.utc)
        since = now - timedelta(minutes=max(1, int(dedupe_window_minutes)))
        base_filters = [
            UserNotification.tenant_id == tenant_id,
            UserNotification.user_id == user_id,
            UserNotification.event_type == event_type,
            UserNotification.channel == channel,
            UserNotification.created_at >= since,
            UserNotification.is_read.is_(False),
        ]
        # Backward-compatible dedupe:
        # 1) exact dedupe_key match (preferred),
        # 2) fallback to entity-based match when no dedupe_key provided.
        recent = (
            await db.execute(
                select(UserNotification)
                .where(*base_filters)
                .order_by(UserNotification.created_at.desc())
                .limit(50)
            )
        ).scalars().all()
        for existing in recent:
            existing_payload = existing.payload if isinstance(existing.payload, dict) else {}
            existing_key = str(existing_payload.get("dedupe_key") or "").strip() or None
            if dedupe_key:
                if existing_key and existing_key == dedupe_key:
                    return existing
                continue
            if entity_type is None and existing.entity_type is not None:
                continue
            if entity_type is not None and existing.entity_type != entity_type:
                continue
            if entity_id is None and existing.entity_id is not None:
                continue
            if entity_id is not None and existing.entity_id != entity_id:
                continue
            return existing

    notification = UserNotification(
        id=str(uuid4()),
        tenant_id=tenant_id,
        user_id=user_id,
        event_type=event_type,
        entity_type=entity_type,
        entity_id=entity_id,
        payload=normalized_payload,
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
    scope: str = "direct",
) -> List[UserNotification]:
    # Current data model stores only user-bound notifications.
    # Keep `scope` parameter for API compatibility and future expansion.
    _ = scope
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


async def cleanup_stale_sla_notifications(
    db: AsyncSession,
    *,
    tenant_id: str,
    user_id: str,
) -> int:
    """
    Mark stale unread SLA notifications as read when no action is required anymore.
    Conditions for stale:
    - thread no longer exists,
    - thread marked "no reply needed",
    - thread is no longer overdue by SLA policy,
    - or an outbound reply already happened after SLA due.
    Also closes active SLA reminders bound to the same thread for this assignee.
    """
    now = datetime.now(timezone.utc)
    notif_rows = await db.execute(
        select(UserNotification).where(
            UserNotification.tenant_id == tenant_id,
            UserNotification.user_id == user_id,
            UserNotification.event_type == "communications_sla_overdue",
            UserNotification.entity_type == "communication_thread",
            UserNotification.entity_id.is_not(None),
            UserNotification.is_read.is_(False),
        )
    )
    notifications = list(notif_rows.scalars().all())
    if not notifications:
        return 0

    thread_ids = sorted({str(n.entity_id or "").strip() for n in notifications if str(n.entity_id or "").strip()})
    if not thread_ids:
        return 0

    thread_rows = await db.execute(
        select(CommunicationThread).where(
            CommunicationThread.tenant_id == tenant_id,
            CommunicationThread.id.in_(thread_ids),
        )
    )
    thread_by_id = {str(t.id): t for t in thread_rows.scalars().all()}

    stale_thread_ids: List[str] = []
    for n in notifications:
        thread_id = str(n.entity_id or "").strip()
        if not thread_id:
            continue
        thread = thread_by_id.get(thread_id)
        if thread is None:
            stale_thread_ids.append(thread_id)
            continue
        thread_meta = thread.thread_meta if isinstance(thread.thread_meta, dict) else {}
        sla_policy = thread_meta.get("sla_policy")
        sla_policy = sla_policy if isinstance(sla_policy, dict) else {}
        no_reply_needed = bool(sla_policy.get("no_reply_needed") or thread_meta.get("no_reply_needed"))
        if no_reply_needed:
            stale_thread_ids.append(thread_id)
            continue
        if int(thread.unread_count or 0) <= 0:
            # No unread inbound left -> no pending SLA action for assignee.
            stale_thread_ids.append(thread_id)
            continue
        if thread.sla_due_at is None or thread.sla_due_at > now:
            stale_thread_ids.append(thread_id)
            continue
        if thread.last_outbound_at and thread.last_outbound_at >= thread.sla_due_at:
            stale_thread_ids.append(thread_id)
            continue
        if str(thread.status or "").lower() not in {"open", "pending", "active"}:
            stale_thread_ids.append(thread_id)
            continue

    stale_thread_ids = sorted(set(stale_thread_ids))
    if not stale_thread_ids:
        return 0

    notif_update = await db.execute(
        update(UserNotification)
        .where(
            UserNotification.tenant_id == tenant_id,
            UserNotification.user_id == user_id,
            UserNotification.event_type == "communications_sla_overdue",
            UserNotification.entity_type == "communication_thread",
            UserNotification.entity_id.in_(stale_thread_ids),
            UserNotification.is_read.is_(False),
        )
        .values(is_read=True, read_at=now, updated_at=now)
    )

    await db.execute(
        update(Reminder)
        .where(
            Reminder.tenant_id == tenant_id,
            Reminder.entity_type == "communication_thread",
            Reminder.entity_id.in_(stale_thread_ids),
            Reminder.type == "communications_sla_overdue",
            Reminder.assignee_id == user_id,
            Reminder.status.in_([ReminderStatus.new, ReminderStatus.pending, ReminderStatus.overdue]),
        )
        .values(status=ReminderStatus.done, completed_at=now, updated_at=now)
    )

    return int(notif_update.rowcount or 0)


async def cleanup_stale_sla_notifications_for_tenant(
    db: AsyncSession,
    *,
    tenant_id: str,
    max_users: int = 2000,
) -> dict:
    max_users = max(1, int(max_users or 1))
    user_rows = await db.execute(
        select(UserNotification.user_id)
        .where(
            UserNotification.tenant_id == tenant_id,
            UserNotification.event_type == "communications_sla_overdue",
            UserNotification.entity_type == "communication_thread",
            UserNotification.is_read.is_(False),
        )
        .distinct()
        .limit(max_users)
    )
    user_ids = [str(row[0]) for row in user_rows.all() if str(row[0] or "").strip()]
    if not user_ids:
        return {"users_processed": 0, "cleaned": 0}

    cleaned_total = 0
    processed = 0
    for user_id in user_ids:
        cleaned = await cleanup_stale_sla_notifications(
            db,
            tenant_id=tenant_id,
            user_id=user_id,
        )
        cleaned_total += int(cleaned or 0)
        processed += 1
    return {"users_processed": processed, "cleaned": cleaned_total}


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
