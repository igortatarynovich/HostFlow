from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from threading import Lock
from typing import Any, Dict, Iterable, List, Literal, Optional, Tuple
from uuid import uuid4

from sqlalchemy import and_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.user import User
from backend.app.models.communication import CommunicationThread
from backend.app.models.reminder import Reminder, ReminderStatus
from backend.app.models.user_notification import UserNotification
from backend.app.services.notification_settings_v1 import (
    normalize_notification_settings_v1,
    should_skip_in_app_notification_v1,
)

NotificationPriority = Literal["critical", "high", "normal"]
_VALID_PRIORITIES = frozenset({"critical", "high", "normal"})

# Root cause fix: GET /notifications is polled frequently; running full SLA cleanup on every
# request loads unbounded rows from PostgreSQL and pegs CPU. Throttle per (tenant, user).
_SLA_POLL_CLEANUP_LOCK = Lock()
_SLA_POLL_CLEANUP_LAST: Dict[Tuple[str, str], float] = {}
_SLA_POLL_CLEANUP_INTERVAL_SEC = 60.0
_SLA_POLL_CLEANUP_MAX_TRACKED = 10_000
# Cap rows processed per cleanup pass (remaining backlog is handled on subsequent passes).
_SLA_CLEANUP_BATCH_LIMIT = 2000


def _allow_sla_poll_cleanup(tenant_id: str, user_id: str) -> bool:
    key = (str(tenant_id), str(user_id))
    now = time.monotonic()
    with _SLA_POLL_CLEANUP_LOCK:
        last = _SLA_POLL_CLEANUP_LAST.get(key)
        if last is not None and (now - last) < _SLA_POLL_CLEANUP_INTERVAL_SEC:
            return False
        _SLA_POLL_CLEANUP_LAST[key] = now
        if len(_SLA_POLL_CLEANUP_LAST) > _SLA_POLL_CLEANUP_MAX_TRACKED:
            cutoff = now - _SLA_POLL_CLEANUP_INTERVAL_SEC
            stale_keys = [k for k, t in _SLA_POLL_CLEANUP_LAST.items() if t < cutoff]
            for k in stale_keys[: _SLA_POLL_CLEANUP_MAX_TRACKED // 2]:
                _SLA_POLL_CLEANUP_LAST.pop(k, None)
        return True


async def maybe_cleanup_stale_sla_notifications_for_poll(
    db: AsyncSession,
    *,
    tenant_id: str,
    user_id: str,
) -> int:
    """
    Run cleanup_stale_sla_notifications at most once per _SLA_POLL_CLEANUP_INTERVAL_SEC
    per (tenant_id, user_id). Used from notification list/reconcile HTTP handlers.
    """
    if not _allow_sla_poll_cleanup(tenant_id, user_id):
        return 0
    return await cleanup_stale_sla_notifications(db, tenant_id=tenant_id, user_id=user_id)


def _notification_uos_group(event_type: str, payload: dict[str, Any]) -> str:
    """Mirror of frontend getNotificationUosGroup (UOS attention center)."""
    et = str(event_type or "").strip().lower()
    source = str(payload.get("source") or "").lower()

    if et in ("communications_sla_overdue", "communications_thread_escalated"):
        return "sla"
    # Lead nudges are actionable work items, not comms SLA breaches — keep below "critical" tier
    # so quiet hours and drawer grouping behave like tasks.
    if et in ("lead_no_next_action", "lead_stuck_stage"):
        return "tasks"
    if et == "invoice_overdue" or "invoice_overdue" in source:
        return "sla"
    if source in ("leads_next_action_sla", "leads_stuck_stage_sla", "invoice_overdue_sla"):
        return "sla"

    if et in ("reminder_due", "reminder_overdue"):
        return "tasks"
    if source == "reminders":
        return "tasks"

    thread_id = payload.get("thread_id")
    if thread_id is not None and str(thread_id).strip():
        return "messages"
    if "communication" in et:
        return "messages"
    if "inbound" in et and ("email" in et or "message" in et):
        return "messages"
    return "system"


def resolve_notification_priority(
    event_type: str,
    payload: Optional[dict],
) -> NotificationPriority:
    """
    Canonical UOS priority for bell / drawer tiers (critical | high | normal).
    Used at write time and as fallback for legacy rows with NULL DB column.
    """
    p = payload if isinstance(payload, dict) else {}
    raw = str(p.get("priority") or "").strip().lower()
    if raw in _VALID_PRIORITIES:
        return raw  # type: ignore[return-value]

    group = _notification_uos_group(event_type, p)
    if group == "sla":
        return "critical"

    et = str(event_type or "").strip().lower()
    if et == "reminder_overdue":
        return "high"
    if et == "handoff_requested":
        return "high"
    return "normal"


def _coerce_priority(value: Optional[str]) -> Optional[NotificationPriority]:
    if value is None:
        return None
    v = str(value).strip().lower()
    if v in _VALID_PRIORITIES:
        return v  # type: ignore[return-value]
    return None


def notification_out_priority(row: UserNotification) -> NotificationPriority:
    stored = _coerce_priority(getattr(row, "priority", None))
    if stored is not None:
        return stored
    return resolve_notification_priority(row.event_type, row.payload if isinstance(row.payload, dict) else {})


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
    priority: Optional[str] = None,
) -> Optional[UserNotification]:
    """Add a notification, collapsing it onto an existing one when it repeats.

    Dedupe (when ``dedupe_window_minutes`` is set) matches on
    tenant/user/event_type/channel/entity plus, if supplied, ``payload["dedupe_key"]``.
    The session runs with ``autoflush=False``, so the probe only sees rows already
    flushed: callers emitting several findings inside one transaction must flush
    between them for dedupe to hold.
    """
    normalized_payload = _normalize_payload(
        event_type=event_type,
        payload=payload,
        entity_type=entity_type,
        entity_id=entity_id,
    )
    rp = normalized_payload.get("priority")
    explicit_payload = _coerce_priority(str(rp).strip()) if rp not in (None, "") else None
    resolved_priority = (
        _coerce_priority(priority)
        or explicit_payload
        or resolve_notification_priority(event_type, normalized_payload)
    )
    normalized_payload["priority"] = resolved_priority
    dedupe_key = str(normalized_payload.get("dedupe_key") or "").strip() or None

    now_utc = datetime.now(timezone.utc)
    user_row = (
        await db.execute(select(User).where(User.id == user_id, User.tenant_id == tenant_id).limit(1))
    ).scalar_one_or_none()
    if user_row is None:
        user_row = (await db.execute(select(User).where(User.id == user_id).limit(1))).scalar_one_or_none()
    extra = user_row.extra if user_row is not None and isinstance(user_row.extra, dict) else {}
    settings_v1 = normalize_notification_settings_v1(extra.get("notification_settings_v1"))
    if should_skip_in_app_notification_v1(
        settings_v1,
        now_utc=now_utc,
        resolved_priority=str(resolved_priority),
        channel=str(channel or "in_app"),
    ):
        return None

    if dedupe_window_minutes is not None and int(dedupe_window_minutes) > 0:
        now = now_utc
        since = now - timedelta(minutes=max(1, int(dedupe_window_minutes)))
        base_filters = [
            UserNotification.tenant_id == tenant_id,
            UserNotification.user_id == user_id,
            UserNotification.event_type == event_type,
            UserNotification.channel == channel,
            UserNotification.created_at >= since,
            UserNotification.is_read.is_(False),
        ]
        # Scope the probe to the target entity instead of "the 50 newest rows of
        # this event_type". The old global window silently stopped matching once a
        # tenant held more than 50 unread rows of one event_type: the row carrying
        # the dedupe_key we were looking for fell outside the window, dedupe missed,
        # and every scheduler tick inserted another duplicate. That is self-feeding —
        # it produced ~3.6k copies per dedupe_key and 920k rows for 3 users before it
        # was caught (2026-07). Entity scoping keeps the probe on the well-indexed
        # (tenant_id, related_entity_type, related_entity_id) path and bounds it to
        # the handful of rows that can legitimately match.
        if entity_type is None:
            base_filters.append(UserNotification.entity_type.is_(None))
        else:
            base_filters.append(UserNotification.entity_type == entity_type)
        if entity_id is None:
            base_filters.append(UserNotification.entity_id.is_(None))
        else:
            base_filters.append(UserNotification.entity_id == entity_id)

        recent = (
            await db.execute(
                select(UserNotification)
                .where(*base_filters)
                .order_by(UserNotification.created_at.desc())
                .limit(50)
            )
        ).scalars().all()
        for existing in recent:
            # Entity identity is already enforced in SQL above; only the optional
            # dedupe_key still has to be compared here (it lives inside the JSON
            # payload and is not indexable on this table).
            if not dedupe_key:
                return existing
            existing_payload = existing.payload if isinstance(existing.payload, dict) else {}
            existing_key = str(existing_payload.get("dedupe_key") or "").strip() or None
            if existing_key == dedupe_key:
                return existing

    notification = UserNotification(
        id=str(uuid4()),
        tenant_id=tenant_id,
        user_id=user_id,
        event_type=event_type,
        priority=resolved_priority,
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
    include_completed_entities: bool = False,
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
    # G-2: hide bell rows for candidates in terminal stages or soft-deleted.
    if not include_completed_entities:
        # Late import keeps user_notifications.py free of cyclic imports
        # (candidate_lifecycle imports UserNotification).
        from backend.app.services.candidate_lifecycle import (
            exclude_completed_candidate_entities_clause,
        )
        from backend.app.services.lead_lifecycle import (
            exclude_completed_lead_entities_clause,
        )

        stmt = stmt.where(
            and_(
                exclude_completed_candidate_entities_clause(
                    tenant_id,
                    entity_type_col=UserNotification.entity_type,
                    entity_id_col=UserNotification.entity_id,
                ),
                exclude_completed_lead_entities_clause(
                    tenant_id,
                    entity_type_col=UserNotification.entity_type,
                    entity_id_col=UserNotification.entity_id,
                ),
            )
        )
    rows = await db.execute(stmt)
    out = list(rows.scalars().all())

    def _ts(n: UserNotification) -> float:
        ca = n.created_at
        if ca.tzinfo is None:
            return ca.replace(tzinfo=timezone.utc).timestamp()
        return ca.timestamp()

    tier_rank = {"critical": 0, "high": 1, "normal": 2}
    out.sort(
        key=lambda n: (
            tier_rank.get(notification_out_priority(n), 2),
            -_ts(n),
        )
    )
    return out


async def cleanup_stale_communications_sla_notifications(
    db: AsyncSession,
    *,
    tenant_id: str,
    user_id: str,
) -> int:
    """Mark stale unread communications SLA notifications as read."""
    now = datetime.now(timezone.utc)
    notif_rows = await db.execute(
        select(UserNotification)
        .where(
            UserNotification.tenant_id == tenant_id,
            UserNotification.user_id == user_id,
            UserNotification.event_type == "communications_sla_overdue",
            UserNotification.entity_type == "communication_thread",
            UserNotification.entity_id.is_not(None),
            UserNotification.is_read.is_(False),
        )
        .order_by(UserNotification.created_at.asc())
        .limit(_SLA_CLEANUP_BATCH_LIMIT)
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


async def cleanup_stale_lead_sla_notifications(
    db: AsyncSession,
    *,
    tenant_id: str,
    user_id: str,
) -> int:
    """
    Mark lead SLA notifications as read when there is no active lead SLA reminder anymore.
    Reminder queue is the actionable source of truth; stale bell rows should not accumulate.
    """
    active_statuses = (ReminderStatus.new, ReminderStatus.pending, ReminderStatus.overdue)
    event_to_reminder_type = {
        "lead_no_next_action": "leads_no_next_action",
        "lead_stuck_stage": "leads_stuck_stage",
    }
    events = tuple(event_to_reminder_type.keys())

    notif_rows = await db.execute(
        select(UserNotification)
        .where(
            UserNotification.tenant_id == tenant_id,
            UserNotification.user_id == user_id,
            UserNotification.event_type.in_(events),
            UserNotification.entity_type == "lead",
            UserNotification.entity_id.is_not(None),
            UserNotification.is_read.is_(False),
        )
        .order_by(UserNotification.created_at.asc())
        .limit(_SLA_CLEANUP_BATCH_LIMIT)
    )
    notifications = list(notif_rows.scalars().all())
    if not notifications:
        return 0

    lead_ids = sorted({str(n.entity_id or "").strip() for n in notifications if str(n.entity_id or "").strip()})
    if not lead_ids:
        return 0

    reminder_rows = await db.execute(
        select(Reminder.entity_id, Reminder.type).where(
            Reminder.tenant_id == tenant_id,
            Reminder.assignee_id == user_id,
            Reminder.entity_type == "lead",
            Reminder.entity_id.in_(lead_ids),
            Reminder.type.in_(tuple(event_to_reminder_type.values())),
            Reminder.status.in_(active_statuses),
        )
    )
    active_pairs = {(str(entity_id or "").strip(), str(rtype or "").strip()) for entity_id, rtype in reminder_rows.all()}

    stale_ids: list[str] = []
    for n in notifications:
        lead_id = str(n.entity_id or "").strip()
        reminder_type = event_to_reminder_type.get(str(n.event_type or "").strip().lower())
        if not lead_id or not reminder_type:
            continue
        if (lead_id, reminder_type) not in active_pairs:
            stale_ids.append(str(n.id))
    if not stale_ids:
        return 0

    now = datetime.now(timezone.utc)
    notif_update = await db.execute(
        update(UserNotification)
        .where(
            UserNotification.tenant_id == tenant_id,
            UserNotification.user_id == user_id,
            UserNotification.id.in_(stale_ids),
            UserNotification.is_read.is_(False),
        )
        .values(is_read=True, read_at=now, updated_at=now)
    )
    return int(notif_update.rowcount or 0)


async def cleanup_stale_sla_notifications(
    db: AsyncSession,
    *,
    tenant_id: str,
    user_id: str,
) -> int:
    """Mark stale SLA notifications as read (communications + lead SLA)."""
    cleaned_comm = await cleanup_stale_communications_sla_notifications(
        db,
        tenant_id=tenant_id,
        user_id=user_id,
    )
    cleaned_leads = await cleanup_stale_lead_sla_notifications(
        db,
        tenant_id=tenant_id,
        user_id=user_id,
    )
    return int(cleaned_comm or 0) + int(cleaned_leads or 0)


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
            UserNotification.is_read.is_(False),
            (
                (
                    (UserNotification.event_type == "communications_sla_overdue")
                    & (UserNotification.entity_type == "communication_thread")
                )
                | (
                    UserNotification.event_type.in_(("lead_no_next_action", "lead_stuck_stage"))
                    & (UserNotification.entity_type == "lead")
                )
            ),
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


_REMINDER_BELL_EVENT_TYPES: tuple[str, ...] = ("reminder_due", "reminder_overdue")


async def mark_reminder_bell_notifications_read(
    db: AsyncSession,
    *,
    tenant_id: str,
    reminder: Reminder,
    reason: str = "reminder_state_changed",
) -> int:
    """G-9: silence the bell once a reminder is acted on (complete / snooze / cancel).

    Resolves all unread `reminder_due / reminder_overdue` notifications whose
    payload pointed at this reminder (by `reminder.id`) — across recipients —
    and marks them as read.

    Bell + tasks page are two surfaces for the same task; the moment the user
    acts on one of them the other should stop nagging.
    """
    if reminder is None:
        return 0
    reminder_id = str(getattr(reminder, "id", "") or "").strip()
    tenant_id_str = str(tenant_id or "").strip()
    if not reminder_id or not tenant_id_str:
        return 0

    entity_type = (reminder.entity_type or "").strip() or None
    entity_id = (reminder.entity_id or "").strip() or None

    stmt = select(UserNotification).where(
        UserNotification.tenant_id == tenant_id_str,
        UserNotification.event_type.in_(_REMINDER_BELL_EVENT_TYPES),
        UserNotification.is_read.is_(False),
    )
    # Narrow by entity when we have one; falls back to event_type-only otherwise.
    if entity_type and entity_id:
        stmt = stmt.where(
            UserNotification.entity_type == entity_type,
            UserNotification.entity_id == entity_id,
        )

    rows = await db.execute(stmt)
    candidates = list(rows.scalars().all())
    if not candidates:
        return 0

    ids_to_close: list[str] = []
    for n in candidates:
        payload = n.payload if isinstance(n.payload, dict) else {}
        # Match either via canonical reminder_id field or via dedupe_key suffix.
        rid = str(payload.get("reminder_id") or "").strip()
        dedupe_key = str(payload.get("dedupe_key") or "").strip()
        if rid == reminder_id or (dedupe_key and reminder_id in dedupe_key):
            ids_to_close.append(str(n.id))

    if not ids_to_close:
        return 0

    now = datetime.now(timezone.utc)
    result = await db.execute(
        update(UserNotification)
        .where(
            UserNotification.tenant_id == tenant_id_str,
            UserNotification.id.in_(ids_to_close),
            UserNotification.is_read.is_(False),
        )
        .values(is_read=True, read_at=now, updated_at=now)
    )
    closed = int(result.rowcount or 0)
    if closed:
        # Stash a reason on the row so /app/tasks explainability can show "auto-closed because reminder snoozed".
        # Best-effort: ignore failures, this is purely diagnostic.
        for n in candidates:
            if str(n.id) not in ids_to_close:
                continue
            payload = dict(n.payload) if isinstance(n.payload, dict) else {}
            meta = dict(payload.get("auto_closed") or {}) if isinstance(payload.get("auto_closed"), dict) else {}
            meta["reason"] = reason
            meta["at"] = now.isoformat()
            payload["auto_closed"] = meta
            n.payload = payload
    return closed


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
