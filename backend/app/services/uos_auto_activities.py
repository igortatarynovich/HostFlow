"""
UOS: system-created activities (reminders) on lifecycle events.

Toggle per tenant via Tenant.settings["uos_auto_activities_v1"]:

  {
    "candidate_created_call": true,
    "service_order_confirm": true,
    "invoice_follow_payment": true,
    "inbound_message_reply": true
  }

Omitted keys default to True. Set a key to false to disable that automation.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any, Mapping, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.reminder import Reminder, ReminderStatus
from backend.app.models.tenant import Tenant
from backend.app.services.reminder_tasks import create_reminder, refresh_open_typed_reminder_due

_ACTIVE_STATUSES = (
    ReminderStatus.pending,
    ReminderStatus.new,
    ReminderStatus.sent,
    ReminderStatus.overdue,
)


def _as_dict(m: Optional[Mapping[str, Any]]) -> dict[str, Any]:
    return dict(m) if isinstance(m, Mapping) else {}


def _uos_auto_flag(settings: Optional[dict], key: str, default: bool = True) -> bool:
    raw = _as_dict(settings).get("uos_auto_activities_v1")
    if not isinstance(raw, dict):
        return default
    if key not in raw:
        return default
    return bool(raw[key])


async def _tenant_settings(db: AsyncSession, tenant_id: str) -> dict[str, Any]:
    row = await db.execute(select(Tenant.settings).where(Tenant.id == tenant_id))
    s = row.scalar_one_or_none()
    return _as_dict(s)


def _thread_skips_auto_reply(thread: Any) -> bool:
    """Respect Inbox \"no reply needed\" / SLA policy (same signals as SLA scheduler)."""
    meta = getattr(thread, "thread_meta", None)
    meta = meta if isinstance(meta, dict) else {}
    if bool(meta.get("no_reply_needed")):
        return True
    sla_policy = meta.get("sla_policy")
    sla_policy = sla_policy if isinstance(sla_policy, dict) else {}
    if bool(sla_policy.get("no_reply_needed")):
        return True
    return False


async def _has_active_typed_reminder(
    db: AsyncSession,
    *,
    tenant_id: str,
    entity_type: str,
    entity_id: str,
    rtype: str,
) -> bool:
    stmt = (
        select(Reminder.id)
        .where(
            Reminder.tenant_id == tenant_id,
            Reminder.entity_type == entity_type,
            Reminder.entity_id == entity_id,
            Reminder.type == rtype,
            Reminder.status.in_(list(_ACTIVE_STATUSES)),
        )
        .limit(1)
    )
    row = await db.execute(stmt)
    return row.scalar_one_or_none() is not None


async def ensure_candidate_created_call_task(
    db: AsyncSession,
    tenant_id: str,
    actor_id: str,
    candidate: Any,
) -> None:
    if not _uos_auto_flag(await _tenant_settings(db, tenant_id), "candidate_created_call", True):
        return
    cid = str(getattr(candidate, "id", "") or "").strip()
    if not cid:
        return
    if await _has_active_typed_reminder(
        db, tenant_id=tenant_id, entity_type="candidate", entity_id=cid, rtype="uos_candidate_call"
    ):
        return
    assignee = str(
        getattr(candidate, "recruiter_id", None)
        or getattr(candidate, "manager", None)
        or actor_id
        or ""
    ).strip() or actor_id
    due = datetime.now(timezone.utc) + timedelta(hours=24)
    await create_reminder(
        db,
        tenant_id=tenant_id,
        actor_id=actor_id,
        payload={
            "title": "Call candidate",
            "type": "uos_candidate_call",
            "entity_type": "candidate",
            "entity_id": cid,
            "due_at": due,
            "assignee_id": assignee,
            "source": "uos_auto",
            "priority": "normal",
            "channel": "internal",
            "payload": {"uos_trigger": "candidate.created"},
        },
    )


async def ensure_service_order_confirm_task(
    db: AsyncSession,
    tenant_id: str,
    actor_id: str,
    order: Any,
) -> None:
    if not _uos_auto_flag(await _tenant_settings(db, tenant_id), "service_order_confirm", True):
        return
    oid = str(getattr(order, "id", "") or "").strip()
    if not oid:
        return
    if await _has_active_typed_reminder(
        db,
        tenant_id=tenant_id,
        entity_type="service_order",
        entity_id=oid,
        rtype="uos_order_confirm",
    ):
        return
    assignee = str(getattr(order, "assigned_to", None) or getattr(order, "requested_by", None) or actor_id).strip() or actor_id
    due = datetime.now(timezone.utc) + timedelta(hours=48)
    await create_reminder(
        db,
        tenant_id=tenant_id,
        actor_id=actor_id,
        payload={
            "title": "Confirm service order",
            "type": "uos_order_confirm",
            "entity_type": "service_order",
            "entity_id": oid,
            "due_at": due,
            "assignee_id": assignee,
            "source": "uos_auto",
            "priority": "normal",
            "channel": "internal",
            "payload": {"uos_trigger": "service_order.created"},
        },
    )


def _invoice_due_datetime(inv: Any) -> datetime:
    dd = getattr(inv, "due_date", None)
    if isinstance(dd, datetime):
        dt = dd
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    if isinstance(dd, date):
        return datetime(dd.year, dd.month, dd.day, tzinfo=timezone.utc)
    return datetime.now(timezone.utc) + timedelta(days=7)


async def ensure_invoice_follow_payment_task(
    db: AsyncSession,
    tenant_id: str,
    actor_id: str,
    invoice: Any,
) -> None:
    if not _uos_auto_flag(await _tenant_settings(db, tenant_id), "invoice_follow_payment", True):
        return
    iid = str(getattr(invoice, "id", "") or "").strip()
    if not iid:
        return
    if await _has_active_typed_reminder(
        db, tenant_id=tenant_id, entity_type="invoice", entity_id=iid, rtype="uos_invoice_follow_payment"
    ):
        return
    assignee = str(getattr(invoice, "created_by", None) or actor_id).strip() or actor_id
    due = _invoice_due_datetime(invoice)
    await create_reminder(
        db,
        tenant_id=tenant_id,
        actor_id=actor_id,
        payload={
            "title": "Follow up payment",
            "type": "uos_invoice_follow_payment",
            "entity_type": "invoice",
            "entity_id": iid,
            "due_at": due,
            "assignee_id": assignee,
            "source": "uos_auto",
            "priority": "high",
            "channel": "internal",
            "payload": {"uos_trigger": "invoice.created"},
        },
    )


async def ensure_inbound_thread_reply_task(
    db: AsyncSession,
    tenant_id: str,
    actor_id: Optional[str],
    thread: Any,
) -> None:
    """At most one open \"reply in dialog\" task per thread; new inbound refreshes due/remind (+24h). Skipped if no-reply-needed."""
    if not _uos_auto_flag(await _tenant_settings(db, tenant_id), "inbound_message_reply", True):
        return
    tid = str(getattr(thread, "id", "") or "").strip()
    if not tid:
        return
    if _thread_skips_auto_reply(thread):
        return
    due = datetime.now(timezone.utc) + timedelta(hours=24)
    if await _has_active_typed_reminder(
        db,
        tenant_id=tenant_id,
        entity_type="communication_thread",
        entity_id=tid,
        rtype="uos_inbound_reply",
    ):
        await refresh_open_typed_reminder_due(
            db,
            tenant_id=tenant_id,
            entity_type="communication_thread",
            entity_id=tid,
            reminder_type="uos_inbound_reply",
            new_due_at=due,
        )
        return
    act = (
        str(actor_id or "").strip()
        or str(getattr(thread, "assignee_id", None) or "").strip()
        or str(getattr(thread, "owner_id", None) or "").strip()
        or "uos-auto"
    )
    assignee = (
        str(getattr(thread, "assignee_id", None) or getattr(thread, "owner_id", None) or act or "").strip() or act
    )
    ch = str(getattr(thread, "channel", "") or "message").strip() or "message"
    subj = str(getattr(thread, "subject", "") or "").strip()
    title = f"Reply in {ch.upper()} thread"
    if subj:
        title = f"{title}: {subj[:80]}"
    await create_reminder(
        db,
        tenant_id=tenant_id,
        actor_id=act,
        payload={
            "title": title,
            "type": "uos_inbound_reply",
            "entity_type": "communication_thread",
            "entity_id": tid,
            "due_at": due,
            "assignee_id": assignee,
            "source": "uos_auto",
            "priority": "normal",
            "channel": "internal",
            "payload": {
                "uos_trigger": "communication.inbound",
                "thread_id": tid,
                "thread_channel": ch,
            },
        },
    )
