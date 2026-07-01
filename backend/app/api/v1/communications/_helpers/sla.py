"""SLA-policy helpers for communication threads.

Encapsulates:

* reading the per-channel response SLA from tenant communication settings
  (``_channel_response_sla_minutes``);
* applying the SLA-due-at update on a thread when a new message lands
  (``_apply_thread_sla_policy_from_message``);
* the thread-side ``_touch_thread_from_message`` that updates last-message
  timestamps, unread counters, direction hints, and the SLA-due-at field
  in one go (kept here together because it is the single caller of the
  apply-policy helper);
* SLA-overdue reminder & user-notification cleanup
  (``_resolve_thread_sla_alerts``).

Extracted from ``backend/app/api/v1/communications/__init__.py`` as part of
the Phase 1 god-module split (step 4/N). All public symbols keep their
underscore-prefixed names so the parent package can re-export them and
existing route handlers do not need to change.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.communication import (
    CommunicationMessage,
    CommunicationThread,
)
from backend.app.models.tenant import Tenant

from .tenant_settings import _comm_settings_channels
from .utils import _as_dict, _now_utc

__all__ = [
    "_channel_response_sla_minutes",
    "_apply_thread_sla_policy_from_message",
    "_touch_thread_from_message",
    "_resolve_thread_sla_alerts",
]


def _channel_response_sla_minutes(tenant: Tenant | None, channel: str) -> int | None:
    channels_cfg = _comm_settings_channels(tenant)
    rows = channels_cfg.get("channels")
    if isinstance(rows, list):
        for row in rows:
            if not isinstance(row, dict):
                continue
            if str(row.get("key") or "").strip().lower() != str(channel or "").strip().lower():
                continue
            try:
                return max(1, int(row.get("responseSlaMinutes") or 0))
            except Exception:
                return None
    return None


def _apply_thread_sla_policy_from_message(
    thread: CommunicationThread,
    msg: CommunicationMessage,
    tenant: Tenant | None,
) -> None:
    if msg.is_internal_note:
        return
    thread_meta_current = _as_dict(thread.thread_meta)
    sla_policy_current = _as_dict(thread_meta_current.get("sla_policy"))
    muted = bool(sla_policy_current.get("muted") or thread_meta_current.get("sla_muted"))
    if muted:
        thread.sla_due_at = None
        return
    no_reply_needed = bool(
        sla_policy_current.get("no_reply_needed") or thread_meta_current.get("no_reply_needed")
    )
    if no_reply_needed:
        thread.sla_due_at = None
        return
    if msg.direction == "inbound":
        sla_minutes = _channel_response_sla_minutes(tenant, thread.channel)
        if sla_minutes and sla_minutes > 0:
            base_ts = msg.sent_at or msg.delivered_at or msg.created_at or _now_utc()
            thread.sla_due_at = base_ts + timedelta(minutes=sla_minutes)
            thread_meta = _as_dict(thread.thread_meta)
            thread_meta["sla_policy"] = {
                **_as_dict(thread_meta.get("sla_policy")),
                "response_sla_minutes": sla_minutes,
                "channel": thread.channel,
                "last_started_at": base_ts.isoformat(),
                "last_due_at": thread.sla_due_at.isoformat() if thread.sla_due_at else None,
            }
            thread.thread_meta = thread_meta
        return
    if msg.direction == "outbound":
        if thread.sla_due_at is not None:
            thread_meta = _as_dict(thread.thread_meta)
            thread_meta["sla_policy"] = {
                **_as_dict(thread_meta.get("sla_policy")),
                "last_replied_at": (msg.sent_at or msg.created_at or _now_utc()).isoformat(),
                "last_cleared_due_at": thread.sla_due_at.isoformat(),
            }
            thread.thread_meta = thread_meta
        thread.sla_due_at = None


def _touch_thread_from_message(
    thread: CommunicationThread,
    msg: CommunicationMessage,
    *,
    tenant: Tenant | None = None,
) -> None:
    now = _now_utc()
    ts = msg.sent_at or msg.delivered_at or msg.read_at or msg.created_at or now
    thread.last_message_at = ts
    preview = (msg.body_text or msg.subject or "").strip()
    if preview:
        thread.last_message_preview = preview[:500]
    if msg.direction == "inbound":
        thread.last_inbound_at = ts
        payload = _as_dict(msg.payload)
        is_telegram_command = bool(payload.get("telegram_command"))
        text = str(msg.body_text or "").strip()
        is_slash_command = (
            str(msg.channel or "").lower() == "telegram" and text.startswith("/")
        )
        if msg.read_at is None and not is_telegram_command and not is_slash_command:
            thread.unread_count = int(thread.unread_count or 0) + 1
    elif msg.direction == "outbound":
        thread.last_outbound_at = ts
        if thread.direction_hint in (None, "", "inbound"):
            thread.direction_hint = "mixed" if thread.direction_hint else "outbound"
    if msg.direction == "inbound" and thread.direction_hint in (None, "", "outbound"):
        thread.direction_hint = "mixed" if thread.direction_hint == "outbound" else "inbound"
    _apply_thread_sla_policy_from_message(thread, msg, tenant)
    thread.updated_at = now


async def _resolve_thread_sla_alerts(
    db: AsyncSession,
    *,
    tenant_id: str,
    thread_id: str,
    close_mode: str = "done",
    now: Optional[datetime] = None,
) -> None:
    from backend.app.models.reminder import Reminder, ReminderStatus
    from backend.app.models.user_notification import UserNotification

    ts = now or _now_utc()
    if close_mode == "cancelled":
        await db.execute(
            sa.update(Reminder)
            .where(
                Reminder.tenant_id == tenant_id,
                Reminder.entity_type == "communication_thread",
                Reminder.entity_id == str(thread_id),
                Reminder.type == "communications_sla_overdue",
                Reminder.status.in_(
                    [ReminderStatus.new, ReminderStatus.pending, ReminderStatus.overdue]
                ),
            )
            .values(
                status=ReminderStatus.cancelled,
                cancelled_at=ts,
                completed_at=ts,
                updated_at=ts,
            )
        )
    else:
        await db.execute(
            sa.update(Reminder)
            .where(
                Reminder.tenant_id == tenant_id,
                Reminder.entity_type == "communication_thread",
                Reminder.entity_id == str(thread_id),
                Reminder.type == "communications_sla_overdue",
                Reminder.status.in_(
                    [ReminderStatus.new, ReminderStatus.pending, ReminderStatus.overdue]
                ),
            )
            .values(
                status=ReminderStatus.done,
                completed_at=ts,
                updated_at=ts,
            )
        )

    await db.execute(
        sa.update(UserNotification)
        .where(
            UserNotification.tenant_id == tenant_id,
            UserNotification.event_type == "communications_sla_overdue",
            UserNotification.entity_type == "communication_thread",
            UserNotification.entity_id == str(thread_id),
            UserNotification.is_read.is_(False),
        )
        .values(is_read=True, read_at=ts, updated_at=ts)
    )
