from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from fastapi import HTTPException, status
from sqlalchemy import and_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.reminder import Reminder, ReminderStatus
from backend.app.models.reminder_event import ReminderEvent
from backend.app.services.user_notifications import create_notification

DEFAULT_REMIND_OFFSET_MINUTES = 15
ALLOWED_CHANNELS = {"internal"}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _is_admin(role: Optional[str]) -> bool:
    if not role:
        return False
    return role in {"administrator", "superadmin", "supervisor", "admin", "manager"}


def _assert_acl(reminder: Reminder, actor_id: str, role: Optional[str]) -> None:
    if _is_admin(role):
        return
    if actor_id not in {reminder.owner_id, reminder.assignee_id}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")


def _log_event(
    db: AsyncSession,
    *,
    reminder_id: str,
    tenant_id: str,
    event_type: str,
    payload: Optional[dict] = None,
) -> ReminderEvent:
    event = ReminderEvent(
        reminder_id=reminder_id,
        tenant_id=tenant_id,
        event_type=event_type,
        payload=payload or {},
    )
    db.add(event)
    return event


def _normalize_remind_at(
    due_at: datetime, remind_at: Optional[datetime], default_offset_minutes: int
) -> datetime:
    if remind_at is None:
        remind_at = due_at - timedelta(minutes=default_offset_minutes)
    if remind_at.tzinfo is None:
        remind_at = remind_at.replace(tzinfo=timezone.utc)
    now = _now()
    if remind_at < now:
        return now
    return remind_at


async def create_reminder(
    db: AsyncSession,
    *,
    tenant_id: str,
    actor_id: str,
    payload: Dict[str, Any],
) -> Reminder:
    due_at_raw = payload.get("due_at")
    if not isinstance(due_at_raw, datetime):
        raise HTTPException(status_code=400, detail="due_at is required")
    due_at = due_at_raw if due_at_raw.tzinfo else due_at_raw.replace(tzinfo=timezone.utc)

    channel = payload.get("channel") or "internal"
    if channel not in ALLOWED_CHANNELS:
        raise HTTPException(status_code=400, detail="Unsupported channel")

    remind_at = payload.get("remind_at")
    if remind_at is not None and not isinstance(remind_at, datetime):
        raise HTTPException(status_code=400, detail="remind_at must be datetime or null")

    assignee_id = payload.get("assignee_id") or actor_id
    reminder = Reminder(
        tenant_id=tenant_id,
        type=payload.get("type") or "custom",
        entity_type=payload.get("entity_type") or "custom",
        entity_id=payload.get("entity_id") or "",
        title=payload.get("title") or payload.get("message"),
        description=payload.get("description"),
        owner_id=actor_id,
        assignee_id=assignee_id,
        priority=payload.get("priority") or "normal",
        channel=channel,
        due_at=due_at,
        remind_at=_normalize_remind_at(due_at, remind_at, DEFAULT_REMIND_OFFSET_MINUTES),
        snoozed_until=None,
        completed_at=None,
        recurrence_json=payload.get("recurrence_json"),
        status=ReminderStatus.pending,
        message=payload.get("message"),
        payload=payload.get("payload") or {},
        created_by=actor_id,
    )
    db.add(reminder)
    await db.flush()
    _log_event(
        db,
        reminder_id=reminder.id,
        tenant_id=tenant_id,
        event_type="created",
        payload={"actor_id": actor_id},
    )
    return reminder


async def list_reminders(
    db: AsyncSession,
    *,
    tenant_id: str,
    assignee_id: Optional[str] = None,
    entity: Optional[Tuple[str, str]] = None,
    status_in: Optional[Sequence[str]] = None,
    due_range: Optional[Tuple[datetime, datetime]] = None,
) -> List[Reminder]:
    stmt = select(Reminder).where(Reminder.tenant_id == tenant_id)
    if assignee_id:
        stmt = stmt.where(Reminder.assignee_id == assignee_id)
    if entity:
        entity_type, entity_id = entity
        stmt = stmt.where(
            Reminder.entity_type == entity_type,
            Reminder.entity_id == entity_id,
        )
    if status_in:
        stmt = stmt.where(Reminder.status.in_(list(status_in)))
    if due_range:
        start, end = due_range
        if start:
            stmt = stmt.where(Reminder.due_at >= start)
        if end:
            stmt = stmt.where(Reminder.due_at <= end)
    rows = await db.execute(stmt.order_by(Reminder.due_at.asc()))
    return list(rows.scalars().all())


async def _get_reminder(db: AsyncSession, tenant_id: str, reminder_id: str) -> Reminder:
    row = await db.execute(
        select(Reminder).where(
            Reminder.id == reminder_id,
            Reminder.tenant_id == tenant_id,
        )
    )
    reminder = row.scalar_one_or_none()
    if reminder is None:
        raise HTTPException(status_code=404, detail="Reminder not found")
    return reminder


async def update_reminder(
    db: AsyncSession,
    *,
    tenant_id: str,
    reminder_id: str,
    actor_id: str,
    role: Optional[str],
    payload: Dict[str, Any],
) -> Reminder:
    reminder = await _get_reminder(db, tenant_id, reminder_id)
    _assert_acl(reminder, actor_id, role)

    for key in ("title", "description", "priority", "channel", "message"):
        if key in payload and payload[key] is not None:
            setattr(reminder, key, payload[key])

    if "assignee_id" in payload and payload["assignee_id"]:
        reminder.assignee_id = payload["assignee_id"]

    if "due_at" in payload and isinstance(payload["due_at"], datetime):
        due_at = payload["due_at"]
        if due_at.tzinfo is None:
            due_at = due_at.replace(tzinfo=timezone.utc)
        reminder.due_at = due_at

    if "remind_at" in payload:
        remind_at = payload["remind_at"]
        if remind_at is None:
            reminder.remind_at = _normalize_remind_at(
                reminder.due_at, None, DEFAULT_REMIND_OFFSET_MINUTES
            )
        elif isinstance(remind_at, datetime):
            reminder.remind_at = _normalize_remind_at(
                reminder.due_at, remind_at, DEFAULT_REMIND_OFFSET_MINUTES
            )
        else:
            raise HTTPException(status_code=400, detail="remind_at must be datetime or null")

    _log_event(
        db,
        reminder_id=reminder.id,
        tenant_id=tenant_id,
        event_type="updated",
        payload={"actor_id": actor_id},
    )
    return reminder


async def snooze_reminder(
    db: AsyncSession,
    *,
    tenant_id: str,
    reminder_id: str,
    actor_id: str,
    role: Optional[str],
    minutes: Optional[int] = None,
    new_remind_at: Optional[datetime] = None,
) -> Reminder:
    reminder = await _get_reminder(db, tenant_id, reminder_id)
    _assert_acl(reminder, actor_id, role)
    if minutes is None and new_remind_at is None:
        raise HTTPException(status_code=400, detail="minutes or new_remind_at required")
    if minutes is not None:
        new_remind_at = _now() + timedelta(minutes=int(minutes))
    elif new_remind_at and new_remind_at.tzinfo is None:
        new_remind_at = new_remind_at.replace(tzinfo=timezone.utc)
    reminder.remind_at = _normalize_remind_at(reminder.due_at, new_remind_at, DEFAULT_REMIND_OFFSET_MINUTES)
    reminder.snoozed_until = reminder.remind_at
    reminder.status = ReminderStatus.pending
    reminder.sent_at = None
    _log_event(
        db,
        reminder_id=reminder.id,
        tenant_id=tenant_id,
        event_type="snoozed",
        payload={"actor_id": actor_id, "remind_at": reminder.remind_at.isoformat()},
    )
    return reminder


async def _spawn_next_recurrence(
    db: AsyncSession,
    *,
    tenant_id: str,
    actor_id: str,
    reminder: Reminder,
) -> Optional[Reminder]:
    rec = reminder.recurrence_json or {}
    if not isinstance(rec, dict) or not rec:
        return None

    freq = (rec.get("freq") or "").lower()
    interval = int(rec.get("interval") or 1)
    if interval <= 0:
        interval = 1

    if freq == "daily":
        delta = timedelta(days=interval)
    elif freq == "weekly":
        delta = timedelta(weeks=interval)
    else:
        # simple custom: treat interval as days
        delta = timedelta(days=interval)

    next_due = reminder.due_at + delta
    next_remind = _normalize_remind_at(next_due, None, DEFAULT_REMIND_OFFSET_MINUTES)
    clone = Reminder(
        tenant_id=tenant_id,
        type=reminder.type,
        entity_type=reminder.entity_type,
        entity_id=reminder.entity_id,
        title=reminder.title,
        description=reminder.description,
        owner_id=reminder.owner_id,
        assignee_id=reminder.assignee_id,
        priority=reminder.priority,
        channel=reminder.channel,
        due_at=next_due,
        remind_at=next_remind,
        recurrence_json=reminder.recurrence_json,
        status=ReminderStatus.pending,
        message=reminder.message,
        payload=reminder.payload,
        created_by=actor_id,
    )
    db.add(clone)
    _log_event(
        db,
        reminder_id=clone.id,
        tenant_id=tenant_id,
        event_type="created",
        payload={"actor_id": actor_id, "source": reminder.id, "reason": "recurrence"},
    )
    return clone


async def complete_reminder(
    db: AsyncSession,
    *,
    tenant_id: str,
    reminder_id: str,
    actor_id: str,
    role: Optional[str],
    completed_at: Optional[datetime] = None,
) -> Reminder:
    reminder = await _get_reminder(db, tenant_id, reminder_id)
    _assert_acl(reminder, actor_id, role)
    ts = completed_at or _now()
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    reminder.completed_at = ts
    reminder.status = ReminderStatus.done
    _log_event(
        db,
        reminder_id=reminder.id,
        tenant_id=tenant_id,
        event_type="completed",
        payload={"actor_id": actor_id, "completed_at": ts.isoformat()},
    )
    await _spawn_next_recurrence(db, tenant_id=tenant_id, actor_id=actor_id, reminder=reminder)
    return reminder


async def mark_overdue_reminders(db: AsyncSession, *, tenant_id: str) -> int:
    now = _now()
    stmt = (
        update(Reminder)
        .where(
            Reminder.tenant_id == tenant_id,
            Reminder.status.in_([ReminderStatus.pending, ReminderStatus.new]),
            Reminder.due_at < now,
        )
        .values(status=ReminderStatus.overdue)
    )
    result = await db.execute(stmt)
    return result.rowcount or 0


async def deliver_due_reminders(db: AsyncSession, *, tenant_id: str) -> int:
    now = _now()
    rows = await db.execute(
        select(Reminder).where(
            Reminder.tenant_id == tenant_id,
            Reminder.status.in_([ReminderStatus.pending, ReminderStatus.new, ReminderStatus.overdue]),
            Reminder.remind_at.isnot(None),
            Reminder.remind_at <= now,
            Reminder.channel == "internal",
            Reminder.sent_at.is_(None),
        )
    )
    reminders = list(rows.scalars().all())
    delivered = 0
    for reminder in reminders:
        target_user = reminder.assignee_id or reminder.owner_id
        if not target_user:
            continue
        event_type = "reminder_overdue" if reminder.status == ReminderStatus.overdue else "reminder_due"
        payload = {
            "title": reminder.title,
            "description": reminder.description,
            "type": event_type,
            "entity_type": reminder.entity_type,
            "entity_id": reminder.entity_id,
            "due_at": reminder.due_at.isoformat() if reminder.due_at else None,
            "remind_at": reminder.remind_at.isoformat() if reminder.remind_at else None,
            "priority": reminder.priority,
            "status": reminder.status,
            "severity": "high" if reminder.status == ReminderStatus.overdue else "medium",
            "requires_action": True,
            "source": "reminders",
            "dedupe_key": f"reminder:{event_type}:{reminder.id}:{str(target_user)}",
        }
        await create_notification(
            db,
            tenant_id=tenant_id,
            user_id=str(target_user),
            event_type=event_type,
            entity_type=reminder.entity_type,
            entity_id=reminder.entity_id,
            payload=payload,
            channel="in_app",
            delivered_at=now,
            dedupe_window_minutes=240,
        )
        _log_event(
            db,
            reminder_id=reminder.id,
            tenant_id=tenant_id,
            event_type="sent",
            payload={"to": target_user, "event_type": event_type},
        )
        reminder.sent_at = now
        if reminder.status in {ReminderStatus.new, ReminderStatus.pending}:
            reminder.status = ReminderStatus.sent
        delivered += 1
    return delivered
