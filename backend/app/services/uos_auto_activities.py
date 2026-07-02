"""
UOS: system-created activities (reminders) on lifecycle events.

Toggle per tenant via Tenant.settings["uos_auto_activities_v1"]:

  {
    "candidate_created_call": true,
    "candidate_stage_follow_up": true,
    "service_order_confirm": true,
    "invoice_follow_payment": true,
    "inbound_message_reply": true,
    "client_company_intro": true,
    "client_stage_follow_up": true,
    "vacancy_recruiting_follow_up": true
  }

Omitted keys default to True. Set a key to false to disable that automation.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any, Mapping, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.funnel import Funnel, FunnelStage
from backend.app.models.reminder import Reminder, ReminderStatus
from backend.app.models.tenant import Tenant
from backend.app.services.audit import log_activity
from backend.app.services.lead_first_contact_continuity import (
    FIRST_CONTACT_SUPPRESSED_ACTION,
    candidate_past_cold_first_contact_sync,
    should_skip_default_first_contact_after_lead_conversion,
)
from backend.app.services.recruiter_assignment import resolve_vacancy_primary_recruiter
from backend.app.services.reminder_tasks import create_reminder, refresh_open_typed_reminder_due

_ACTIVE_STATUSES = (
    ReminderStatus.pending,
    ReminderStatus.new,
    ReminderStatus.sent,
    ReminderStatus.overdue,
)
_PRE_CONTACT_CANDIDATE_STAGES = frozenset({"", "new", "no_answer", "to_call", "to_contact"})


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


def _company_is_client_party(company: Any) -> bool:
    extra = getattr(company, "extra", None)
    extra = extra if isinstance(extra, dict) else {}
    return str(extra.get("company_role") or "").strip() == "client"


def vacancy_is_recruiting(v: Any) -> bool:
    """True when the vacancy is an active recruiting container (open, not archived/closed)."""
    if bool(getattr(v, "is_archived", False)):
        return False
    st = str(getattr(v, "status", "") or "").strip().lower()
    if st in ("closed", "archived", "cancelled", "filled", "draft", "on_hold"):
        return False
    if st == "open":
        return True
    return bool(getattr(v, "is_active", True))


async def _tenant_funnel_stage_code_is_terminal(db: AsyncSession, tenant_id: str, code: str) -> bool:
    """True if any tenant funnel marks the code terminal, or a small heuristic when no row exists."""
    c = str(code or "").strip()
    if not c:
        return True
    stmt = (
        select(FunnelStage.id)
        .join(Funnel, Funnel.id == FunnelStage.funnel_id)
        .where(
            Funnel.tenant_id == tenant_id,
            FunnelStage.code == c,
            FunnelStage.is_terminal.is_(True),
        )
        .limit(1)
    )
    row = await db.execute(stmt)
    if row.scalar_one_or_none() is not None:
        return True
    lowered = c.lower()
    if lowered in {"rejected", "declined", "employed", "lost", "won", "archived", "closed"}:
        return True
    return False


async def _client_stage_code_is_terminal(db: AsyncSession, tenant_id: str, code: str) -> bool:
    return await _tenant_funnel_stage_code_is_terminal(db, tenant_id, code)


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


async def _cancel_open_typed_reminder(
    db: AsyncSession,
    *,
    tenant_id: str,
    entity_type: str,
    entity_id: str,
    rtype: str,
) -> int:
    rows = await db.execute(
        select(Reminder).where(
            Reminder.tenant_id == tenant_id,
            Reminder.entity_type == entity_type,
            Reminder.entity_id == entity_id,
            Reminder.type == rtype,
            Reminder.status.in_(list(_ACTIVE_STATUSES)),
        )
    )
    reminders = list(rows.scalars().all())
    if not reminders:
        return 0
    now = datetime.now(timezone.utc)
    for reminder in reminders:
        reminder.status = ReminderStatus.done
        reminder.completed_at = now
        reminder.updated_at = now
    return len(reminders)


async def ensure_candidate_created_call_task(
    db: AsyncSession,
    tenant_id: str,
    actor_id: str,
    candidate: Any,
    *,
    source_lead: Optional[Any] = None,
) -> None:
    if not _uos_auto_flag(await _tenant_settings(db, tenant_id), "candidate_created_call", True):
        return
    cid = str(getattr(candidate, "id", "") or "").strip()
    if not cid:
        return
    if source_lead is not None:
        skip, reasons = await should_skip_default_first_contact_after_lead_conversion(
            db, tenant_id=tenant_id, lead=source_lead
        )
        if skip:
            await log_activity(
                db,
                tenant_id=tenant_id,
                actor_id=None,
                action=FIRST_CONTACT_SUPPRESSED_ACTION,
                target_type="candidate",
                target_id=cid,
                payload={
                    "lead_id": str(getattr(source_lead, "id", "") or ""),
                    "reasons": reasons,
                },
            )
            await db.flush()
            return
    if candidate_past_cold_first_contact_sync(candidate):
        await log_activity(
            db,
            tenant_id=tenant_id,
            actor_id=None,
            action=FIRST_CONTACT_SUPPRESSED_ACTION,
            target_type="candidate",
            target_id=cid,
            payload={
                "lead_id": str(getattr(source_lead, "id", "") or "") or None,
                "reasons": ["candidate:existing_active_stage"],
                "candidate_stage": str(getattr(candidate, "stage", "") or ""),
            },
        )
        await db.flush()
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


async def ensure_client_company_intro_task(
    db: AsyncSession,
    tenant_id: str,
    actor_id: str,
    company: Any,
) -> None:
    """First-touch task for **client** companies (party role client); deduped per company."""
    if not _company_is_client_party(company):
        return
    if not _uos_auto_flag(await _tenant_settings(db, tenant_id), "client_company_intro", True):
        return
    cid = str(getattr(company, "id", "") or "").strip()
    if not cid:
        return
    if await _has_active_typed_reminder(
        db, tenant_id=tenant_id, entity_type="company", entity_id=cid, rtype="uos_client_intro"
    ):
        return
    assignee = str(
        getattr(company, "owner_user_id", None)
        or getattr(company, "manager_user_id", None)
        or actor_id
        or ""
    ).strip() or actor_id
    due = datetime.now(timezone.utc) + timedelta(hours=48)
    await create_reminder(
        db,
        tenant_id=tenant_id,
        actor_id=actor_id,
        payload={
            "title": "Qualify client relationship",
            "type": "uos_client_intro",
            "entity_type": "company",
            "entity_id": cid,
            "due_at": due,
            "assignee_id": assignee,
            "source": "uos_auto",
            "priority": "normal",
            "channel": "internal",
            "payload": {"uos_trigger": "company.client.created", "company_id": cid},
        },
    )


async def ensure_client_stage_follow_up_task(
    db: AsyncSession,
    tenant_id: str,
    actor_id: str,
    company: Any,
    old_stage: Optional[str],
    new_stage: Optional[str],
) -> None:
    """On client pipeline stage change: one open follow-up task per company (refresh due/title when re-advancing)."""
    if not _company_is_client_party(company):
        return
    if not _uos_auto_flag(await _tenant_settings(db, tenant_id), "client_stage_follow_up", True):
        return
    cid = str(getattr(company, "id", "") or "").strip()
    if not cid:
        return
    new_s = str(new_stage or "").strip() or None
    old_s = str(old_stage or "").strip() or None
    if not new_s or new_s == old_s:
        return
    if await _client_stage_code_is_terminal(db, tenant_id, new_s):
        return
    assignee = str(
        getattr(company, "owner_user_id", None)
        or getattr(company, "manager_user_id", None)
        or actor_id
        or ""
    ).strip() or actor_id
    due = datetime.now(timezone.utc) + timedelta(hours=72)
    title = f"Client pipeline: {new_s}"
    pmerge = {
        "uos_trigger": "company.client_stage.changed",
        "company_id": cid,
        "client_stage": new_s,
        "previous_client_stage": old_s,
    }
    refreshed = await refresh_open_typed_reminder_due(
        db,
        tenant_id=tenant_id,
        entity_type="company",
        entity_id=cid,
        reminder_type="uos_client_stage_follow_up",
        new_due_at=due,
        new_title=title,
        payload_merge=pmerge,
    )
    if refreshed:
        return
    await create_reminder(
        db,
        tenant_id=tenant_id,
        actor_id=actor_id,
        payload={
            "title": title,
            "type": "uos_client_stage_follow_up",
            "entity_type": "company",
            "entity_id": cid,
            "due_at": due,
            "assignee_id": assignee,
            "source": "uos_auto",
            "priority": "normal",
            "channel": "internal",
            "payload": pmerge,
        },
    )


async def ensure_candidate_stage_follow_up_task(
    db: AsyncSession,
    tenant_id: str,
    actor_id: str,
    candidate: Any,
    old_stage: Optional[str],
    new_stage: Optional[str],
) -> None:
    """On hiring pipeline stage change: one open follow-up task per candidate (refresh due/title when re-advancing)."""
    if not _uos_auto_flag(await _tenant_settings(db, tenant_id), "candidate_stage_follow_up", True):
        return
    cid = str(getattr(candidate, "id", "") or "").strip()
    if not cid:
        return
    new_s = str(new_stage or "").strip() or None
    old_s = str(old_stage or "").strip() or None
    if not new_s or new_s == old_s:
        return
    # Once contact is established (or candidate moved further), the initial
    # "call candidate" reminder is no longer relevant and must disappear.
    if str(new_s).strip().lower() not in _PRE_CONTACT_CANDIDATE_STAGES:
        await _cancel_open_typed_reminder(
            db,
            tenant_id=tenant_id,
            entity_type="candidate",
            entity_id=cid,
            rtype="uos_candidate_call",
        )
    if await _tenant_funnel_stage_code_is_terminal(db, tenant_id, new_s):
        return
    assignee = str(
        getattr(candidate, "recruiter_id", None)
        or getattr(candidate, "manager", None)
        or actor_id
        or ""
    ).strip() or actor_id
    due = datetime.now(timezone.utc) + timedelta(hours=72)
    title = f"Candidate pipeline: {new_s}"
    pmerge = {
        "uos_trigger": "candidate.stage.changed",
        "candidate_id": cid,
        "stage": new_s,
        "previous_stage": old_s,
    }
    refreshed = await refresh_open_typed_reminder_due(
        db,
        tenant_id=tenant_id,
        entity_type="candidate",
        entity_id=cid,
        reminder_type="uos_candidate_stage_follow_up",
        new_due_at=due,
        new_title=title,
        payload_merge=pmerge,
    )
    if refreshed:
        return
    await create_reminder(
        db,
        tenant_id=tenant_id,
        actor_id=actor_id,
        payload={
            "title": title,
            "type": "uos_candidate_stage_follow_up",
            "entity_type": "candidate",
            "entity_id": cid,
            "due_at": due,
            "assignee_id": assignee,
            "source": "uos_auto",
            "priority": "normal",
            "channel": "internal",
            "payload": pmerge,
        },
    )


async def ensure_vacancy_recruiting_follow_up_task(
    db: AsyncSession,
    tenant_id: str,
    actor_id: str,
    vacancy: Any,
    *,
    was_recruiting_before: bool,
) -> None:
    """When a vacancy **enters** recruiting (new open vacancy or reopen): one follow-up task; refresh if reopen reuses open row."""
    if not _uos_auto_flag(await _tenant_settings(db, tenant_id), "vacancy_recruiting_follow_up", True):
        return
    vid = str(getattr(vacancy, "id", "") or "").strip()
    if not vid:
        return
    if not vacancy_is_recruiting(vacancy):
        return
    if was_recruiting_before:
        return
    act = str(actor_id or "").strip() or "uos-auto"
    # Phase 2.6.G-5 Stage B — resolve the vacancy's primary recruiter through
    # the canonical helper instead of reading ``vacancy.manager`` directly.
    # Rationale: the old read silently ignored the ``VacancyRecruiter`` m2m
    # pool, so a vacancy with an active recruiter pool but ``manager=NULL``
    # would have its auto-generated follow-up assigned to ``actor_id`` (often
    # the admin who flipped the stage) instead of the pool member who owns
    # sourcing. Resolver cascade: m2m least-load pick → vacancy.manager →
    # None (fall back to ``act``).
    resolved_assignee = await resolve_vacancy_primary_recruiter(db, tenant_id, vacancy)
    assignee = (resolved_assignee or "").strip() or act
    due = datetime.now(timezone.utc) + timedelta(hours=72)
    title_part = str(getattr(vacancy, "title", "") or "").strip() or vid
    title = f"Vacancy pipeline: {title_part[:80]}"
    pmerge = {
        "uos_trigger": "vacancy.recruiting.entered",
        "vacancy_id": vid,
    }
    refreshed = await refresh_open_typed_reminder_due(
        db,
        tenant_id=tenant_id,
        entity_type="vacancy",
        entity_id=vid,
        reminder_type="uos_vacancy_recruiting_follow_up",
        new_due_at=due,
        new_title=title,
        payload_merge=pmerge,
    )
    if refreshed:
        return
    await create_reminder(
        db,
        tenant_id=tenant_id,
        actor_id=act,
        payload={
            "title": title,
            "type": "uos_vacancy_recruiting_follow_up",
            "entity_type": "vacancy",
            "entity_id": vid,
            "due_at": due,
            "assignee_id": assignee,
            "source": "uos_auto",
            "priority": "normal",
            "channel": "internal",
            "payload": pmerge,
        },
    )
