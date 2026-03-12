from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any, Dict
from uuid import UUID

import sqlalchemy as sa

from backend.app.db.session import async_session_maker
from backend.app.models.tenant import Tenant


logger = logging.getLogger(__name__)


_RUNTIME_STATUS: Dict[str, Any] = {
    "active": False,
    "started_at": None,
    "stopped_at": None,
    "tick_seconds": None,
    "last_tick_started_at": None,
    "last_tick_finished_at": None,
    "last_tick_duration_ms": None,
    "last_tick_error": None,
    "last_tick_summary": {},
    "tenants": {},
}


def _env_bool(name: str, default: bool) -> bool:
    raw = str(os.getenv(name, "")).strip().lower()
    if not raw:
        return default
    return raw in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    raw = str(os.getenv(name, "")).strip()
    if not raw:
        return default
    try:
        return max(1, int(raw))
    except Exception:
        return default


def scheduler_enabled() -> bool:
    return _env_bool("COMM_SCHEDULER_ENABLED", True)


def scheduler_tick_seconds() -> int:
    return _env_int("COMM_SCHEDULER_TICK_SECONDS", 60)


def _tenant_comm_settings(tenant: Tenant) -> Dict[str, Any]:
    root = tenant.settings if isinstance(tenant.settings, dict) else {}
    raw = root.get("communications")
    return raw if isinstance(raw, dict) else {}


def _tenant_email_cfg(tenant: Tenant) -> Dict[str, Any]:
    raw = _tenant_comm_settings(tenant).get("email")
    return raw if isinstance(raw, dict) else {}


def _tenant_entitlements(tenant: Tenant) -> Dict[str, Any]:
    raw = _tenant_comm_settings(tenant).get("entitlements")
    return raw if isinstance(raw, dict) else {}


def _tenant_sla_settings(tenant: Tenant) -> Dict[str, Any]:
    raw = _tenant_comm_settings(tenant).get("sla")
    return raw if isinstance(raw, dict) else {}


def _tenant_email_module_enabled(tenant: Tenant) -> bool:
    ent = _tenant_entitlements(tenant)
    modules = ent.get("modules")
    if isinstance(modules, dict):
        email_cfg = modules.get("email")
        if isinstance(email_cfg, dict) and email_cfg.get("enabled") is False:
            return False
    return True


def _tenant_email_incoming_enabled(tenant: Tenant) -> bool:
    cfg = _tenant_email_cfg(tenant)
    return bool(cfg.get("incomingEnabled", False))


def _tenant_email_sync_interval_minutes(tenant: Tenant) -> int:
    cfg = _tenant_email_cfg(tenant)
    try:
        return max(1, int(cfg.get("syncIntervalMinutes") or 5))
    except Exception:
        return 5


def _env_str(name: str, default: str) -> str:
    raw = str(os.getenv(name, "")).strip()
    return raw if raw else default


def _parse_iso_dt(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            return None
        try:
            parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=timezone.utc)
        except Exception:
            return None
    return None


def _sla_escalations_enabled() -> bool:
    return _env_bool("COMM_SCHEDULER_SLA_ESCALATIONS_ENABLED", True)


def _sla_escalation_cooldown_minutes() -> int:
    return _env_int("COMM_SCHEDULER_SLA_ESCALATION_COOLDOWN_MINUTES", 120)


def _tenant_sla_escalations_enabled(tenant: Tenant) -> bool:
    if not _sla_escalations_enabled():
        return False
    cfg = _tenant_sla_settings(tenant)
    return bool(cfg.get("enabled", True))


def _tenant_sla_create_notifications(tenant: Tenant) -> bool:
    cfg = _tenant_sla_settings(tenant)
    return bool(cfg.get("createNotifications", True))


def _tenant_sla_create_reminders(tenant: Tenant) -> bool:
    cfg = _tenant_sla_settings(tenant)
    return bool(cfg.get("createReminders", True))


def _tenant_sla_recipient_mode(tenant: Tenant) -> str:
    cfg = _tenant_sla_settings(tenant)
    mode = str(cfg.get("recipientMode") or "").strip().lower()
    if mode in {"assignee_only", "owner_only", "assignee_or_owner"}:
        return mode
    return "assignee_or_owner"


def _tenant_sla_muted_channels(tenant: Tenant) -> set[str]:
    cfg = _tenant_sla_settings(tenant)
    raw = cfg.get("mutedChannels")
    if not isinstance(raw, list):
        return set()
    return {str(x).strip().lower() for x in raw if str(x).strip()}


def _docs_deadline_reminders_enabled() -> bool:
    return _env_bool("COMM_SCHEDULER_DOCS_DEADLINE_REMINDERS_ENABLED", True)


def _docs_first_reminder_hours() -> int:
    return _env_int("COMM_SCHEDULER_DOCS_FIRST_REMINDER_HOURS", 24)


def _docs_second_reminder_hours() -> int:
    return _env_int("COMM_SCHEDULER_DOCS_SECOND_REMINDER_HOURS", 72)


def _docs_reminder_thresholds_hours() -> list[int]:
    values = {
        max(1, int(_docs_first_reminder_hours())),
        max(1, int(_docs_second_reminder_hours())),
    }
    return sorted(values)


async def _run_sla_escalations_for_tenant(db, *, tenant: Tenant, now: datetime) -> Dict[str, int]:
    from backend.app.models.communication import CommunicationThread
    from backend.app.models.reminder import Reminder, ReminderStatus
    from backend.app.services.user_notifications import create_notification

    tenant_id = str(tenant.id)
    stats = {"candidates": 0, "escalated": 0, "notifications": 0, "reminders": 0}
    if not _tenant_sla_escalations_enabled(tenant):
        return stats
    create_notifications = _tenant_sla_create_notifications(tenant)
    create_reminders = _tenant_sla_create_reminders(tenant)
    recipient_mode = _tenant_sla_recipient_mode(tenant)
    muted_channels = _tenant_sla_muted_channels(tenant)

    stmt = (
        sa.select(CommunicationThread)
        .where(
            CommunicationThread.tenant_id == tenant_id,
            CommunicationThread.is_archived.is_(False),
            CommunicationThread.sla_due_at.is_not(None),
            CommunicationThread.sla_due_at <= now,
            CommunicationThread.status.in_(["open", "pending", "active"]),
        )
        .order_by(sa.asc(CommunicationThread.sla_due_at))
        .limit(200)
    )
    threads = (await db.execute(stmt)).scalars().all()
    stats["candidates"] = len(threads)

    cooldown_min = _sla_escalation_cooldown_minutes()
    for thread in threads:
        if not thread.sla_due_at:
            continue
        thread_meta = thread.thread_meta if isinstance(thread.thread_meta, dict) else {}
        sla_policy = thread_meta.get("sla_policy")
        sla_policy = sla_policy if isinstance(sla_policy, dict) else {}
        if str(thread.channel or "").strip().lower() in muted_channels:
            continue
        if bool(sla_policy.get("muted") or thread_meta.get("sla_muted")):
            continue
        if bool(sla_policy.get("no_reply_needed") or thread_meta.get("no_reply_needed")):
            continue
        ops_meta = thread_meta.get("ops")
        ops_meta = ops_meta if isinstance(ops_meta, dict) else {}
        ops_mode = str(ops_meta.get("mode") or "").strip().lower()
        paused_until_raw = str(ops_meta.get("paused_until") or "").strip()
        paused_until = None
        if paused_until_raw:
            try:
                paused_until = datetime.fromisoformat(paused_until_raw.replace("Z", "+00:00"))
            except Exception:
                paused_until = None
        if paused_until is not None and paused_until.tzinfo is None:
            paused_until = paused_until.replace(tzinfo=timezone.utc)
        if ops_mode in ("later", "paused"):
            if paused_until is not None and paused_until > now:
                # Paused dialogs should not generate SLA escalations until resume time.
                continue
            # Auto-resume expired pauses to avoid stale "later" state forever.
            next_meta = dict(thread_meta)
            next_ops = dict(ops_meta)
            next_ops["mode"] = "in_work"
            next_ops.pop("paused_until", None)
            next_ops["resumed_at"] = now.isoformat()
            next_meta["ops"] = next_ops
            thread.thread_meta = next_meta
            thread.updated_at = now

        if int(thread.unread_count or 0) <= 0:
            # SLA escalation is only relevant when inbound messages are still unread.
            continue
        # If the thread already has an outbound reply after SLA due, skip escalation.
        if thread.last_outbound_at and thread.last_outbound_at >= thread.sla_due_at:
            continue

        sla_meta = thread_meta.get("sla_escalation")
        sla_meta = sla_meta if isinstance(sla_meta, dict) else {}
        due_key = thread.sla_due_at.isoformat()
        last_due_key = str(sla_meta.get("last_due_key") or "")
        last_escalated_at_raw = str(sla_meta.get("last_escalated_at") or "")
        last_escalated_at = None
        if last_escalated_at_raw:
            try:
                last_escalated_at = datetime.fromisoformat(last_escalated_at_raw.replace("Z", "+00:00"))
            except Exception:
                last_escalated_at = None

        # Do not create duplicate SLA notifications for the same due point.
        # Escalate again only when SLA due key changes (new inbound / new SLA cycle).
        if last_due_key == due_key:
            continue

        if recipient_mode == "assignee_only":
            recipient_user_id = str(thread.assignee_id or "").strip() or None
        elif recipient_mode == "owner_only":
            recipient_user_id = str(thread.owner_id or "").strip() or None
        else:
            recipient_user_id = str(thread.assignee_id or thread.owner_id or "").strip() or None
        if not recipient_user_id:
            # Mark that escalation was evaluated but unassigned to avoid tight loop spam.
            next_meta = dict(thread_meta)
            next_meta["sla_escalation"] = {
                **sla_meta,
                "last_due_key": due_key,
                "last_escalated_at": now.isoformat(),
                "last_result": "skipped_unassigned",
            }
            thread.thread_meta = next_meta
            thread.updated_at = now
            continue

        notif = None
        if create_notifications:
            event_type = "communications_sla_overdue"
            notif = await create_notification(
                db,
                tenant_id=tenant_id,
                user_id=recipient_user_id,
                event_type=event_type,
                entity_type="communication_thread",
                entity_id=str(thread.id),
                payload={
                    "type": event_type,
                    "thread_id": str(thread.id),
                    "channel": thread.channel,
                    "sla_due_at": due_key,
                    "unread_count": int(thread.unread_count or 0),
                    "subject": thread.subject,
                    "title": f"SLA overdue: {thread.channel.upper()}",
                    "description": (thread.subject or thread.last_message_preview or str(thread.id))[:500],
                    "severity": "high",
                    "requires_action": True,
                    "source": "communications_sla",
                    "dedupe_key": f"sla:{tenant_id}:{recipient_user_id}:{thread.id}:{due_key}",
                },
                dedupe_window_minutes=240,
            )
            stats["notifications"] += 1

        if create_reminders:
            reminder_exists = False
            reminder_check_stmt = sa.select(Reminder.id).where(
                Reminder.tenant_id == tenant_id,
                Reminder.entity_type == "communication_thread",
                Reminder.entity_id == str(thread.id),
                Reminder.assignee_id == recipient_user_id,
                Reminder.type == "communications_sla_overdue",
                Reminder.status.in_([ReminderStatus.new, ReminderStatus.pending, ReminderStatus.overdue]),
            ).limit(1)
            existing_reminder_id = (await db.execute(reminder_check_stmt)).scalar()
            if existing_reminder_id:
                reminder_exists = True
            if not reminder_exists:
                reminder = Reminder(
                    tenant_id=tenant_id,
                    type="communications_sla_overdue",
                    entity_type="communication_thread",
                    entity_id=str(thread.id),
                    title=f"SLA overdue: {thread.channel.upper()}",
                    description=(thread.subject or thread.last_message_preview or str(thread.id))[:500],
                    owner_id=recipient_user_id,
                    assignee_id=recipient_user_id,
                    priority="high",
                    channel="internal",
                    due_at=now,
                    remind_at=now,
                    status=ReminderStatus.overdue,
                    message="Communication thread SLA is overdue",
                    payload={
                        "thread_id": str(thread.id),
                        "channel": thread.channel,
                        "sla_due_at": due_key,
                    },
                    created_by=None,
                )
                db.add(reminder)
                stats["reminders"] += 1

        next_meta = dict(thread_meta)
        next_meta["sla_escalation"] = {
            **sla_meta,
            "last_due_key": due_key,
            "last_escalated_at": now.isoformat(),
            "last_result": "escalated",
            "recipient_user_id": recipient_user_id,
            "notification_id": str(getattr(notif, "id", "") or ""),
            "cooldown_minutes": cooldown_min,
            "recipient_mode": recipient_mode,
            "create_notifications": bool(create_notifications),
            "create_reminders": bool(create_reminders),
        }
        thread.thread_meta = next_meta
        thread.updated_at = now
        stats["escalated"] += 1

    return stats


async def _run_candidate_docs_deadlines_for_tenant(db, *, tenant: Tenant, now: datetime) -> Dict[str, int]:
    from backend.app.models.candidate import Candidate
    from backend.app.services.user_notifications import create_notification
    from backend.app.services.candidate_telegram_notifications import (
        get_candidate_required_docs_snapshot,
        send_candidate_documents_deadline_nudge_telegram,
        sync_candidate_ready_for_handoff_gate,
    )

    stats = {
        "candidates": 0,
        "checked": 0,
        "due": 0,
        "candidate_telegram": 0,
        "manager_notifications": 0,
    }
    if not _docs_deadline_reminders_enabled():
        return stats

    tenant_id = str(tenant.id)
    thresholds = _docs_reminder_thresholds_hours()
    if not thresholds:
        return stats

    rows = (
        await db.execute(
            sa.select(Candidate)
            .where(
                Candidate.tenant_id == tenant_id,
                Candidate.deleted_at.is_(None),
            )
            .order_by(sa.desc(Candidate.updated_at))
            .limit(500)
        )
    ).scalars().all()
    stats["candidates"] = len(rows)

    for cand in rows:
        intake_state = cand.intake_state if isinstance(cand.intake_state, dict) else {}
        runtime = intake_state.get("telegram_intake")
        runtime = runtime if isinstance(runtime, dict) else {}
        completed_at = _parse_iso_dt(runtime.get("completed_at"))
        if completed_at is None:
            continue
        hours_since_ready = max(0, int((now - completed_at).total_seconds() // 3600))
        reminders_state = runtime.get("docs_wait_reminders")
        reminders_state = reminders_state if isinstance(reminders_state, dict) else {}
        due_thresholds: list[int] = []
        for h in thresholds:
            marker = reminders_state.get(str(h))
            marker = marker if isinstance(marker, dict) else {}
            manager_sent = bool(str(marker.get("manager_notification_at") or "").strip())
            candidate_sent = bool(str(marker.get("candidate_telegram_at") or "").strip())
            if hours_since_ready >= h and (not manager_sent or not candidate_sent):
                due_thresholds.append(h)
        if not due_thresholds:
            continue

        stats["checked"] = int(stats["checked"]) + 1
        snapshot = await get_candidate_required_docs_snapshot(
            db,
            tenant_id=tenant_id,
            candidate=cand,
        )
        total = int(snapshot.get("total") or 0)
        ready = int(snapshot.get("ready") or 0)
        missing = [str(x) for x in (snapshot.get("missing") or []) if str(x or "").strip()]
        if total > 0 and ready >= total:
            try:
                await sync_candidate_ready_for_handoff_gate(
                    db,
                    tenant_id=tenant_id,
                    candidate=cand,
                    source="docs_deadline_scheduler",
                )
            except Exception:
                logger.exception(
                    "[communications-scheduler] auto-ready-for-handoff sync failed tenant=%s candidate=%s",
                    tenant_id,
                    getattr(cand, "id", None),
                )
            continue
        if total <= 0 or ready >= total or not missing:
            continue

        stats["due"] = int(stats["due"]) + 1
        manager_id = str(getattr(cand, "manager", "") or "").strip() or None
        for h in due_thresholds:
            key = str(h)
            marker = reminders_state.get(key)
            marker = marker if isinstance(marker, dict) else {}

            if not str(marker.get("candidate_telegram_at") or "").strip():
                sent = await send_candidate_documents_deadline_nudge_telegram(
                    db,
                    tenant_id=tenant_id,
                    candidate=cand,
                    hours_since_ready=hours_since_ready,
                )
                if sent:
                    marker["candidate_telegram_at"] = now.isoformat()
                    stats["candidate_telegram"] = int(stats["candidate_telegram"]) + 1

            if manager_id and not str(marker.get("manager_notification_at") or "").strip():
                await create_notification(
                    db,
                    tenant_id=tenant_id,
                    user_id=manager_id,
                    event_type="candidate_docs_pending_upload",
                    entity_type="candidate",
                    entity_id=str(cand.id),
                    payload={
                        "type": "candidate_docs_pending_upload",
                        "source": "candidate_docs",
                        "severity": "medium",
                        "requires_action": True,
                        "title": "Ожидаются документы кандидата",
                        "description": (
                            f"Кандидат {str(getattr(cand, 'first_name', '') or '').strip()} "
                            f"{str(getattr(cand, 'last_name', '') or '').strip()}: "
                            f"прогресс {ready}/{total}, не хватает {len(missing)}."
                        ).strip(),
                        "candidate_id": str(cand.id),
                        "missing_count": len(missing),
                        "hours_since_ready": hours_since_ready,
                        "dedupe_key": f"candidate_docs_pending:{tenant_id}:{manager_id}:{cand.id}:{h}",
                    },
                    dedupe_window_minutes=60 * 24 * 30,
                )
                marker["manager_notification_at"] = now.isoformat()
                stats["manager_notifications"] = int(stats["manager_notifications"]) + 1

            if marker:
                reminders_state[key] = marker

        runtime["docs_wait_reminders"] = reminders_state
        runtime["docs_wait_last_checked_at"] = now.isoformat()
        intake_state["telegram_intake"] = runtime
        cand.intake_state = intake_state

    return stats


async def _run_scheduler_tick(state: Dict[str, Any]) -> None:
    from backend.app.api.v1 import communications as comm_api

    now = datetime.now(timezone.utc)
    _RUNTIME_STATUS["last_tick_started_at"] = now.isoformat()
    _RUNTIME_STATUS["last_tick_error"] = None
    fake_user = SimpleNamespace(
        sub=None,
        role="superadmin",
        tenant_id=None,
        email="",
        raw={},
    )
    poll_last_run: Dict[str, datetime] = state.setdefault("poll_last_run", {})
    dispatch_last_run: Dict[str, datetime] = state.setdefault("dispatch_last_run", {})
    dispatch_every_seconds = _env_int("COMM_SCHEDULER_EMAIL_DISPATCH_EVERY_SECONDS", scheduler_tick_seconds())

    async with async_session_maker() as db:
        tenants = (
            await db.execute(
                sa.select(Tenant).where(Tenant.is_active.is_(True)).order_by(sa.asc(Tenant.name))
            )
        ).scalars().all()

    tick_summary: Dict[str, Any] = {
        "tenants_total": len(tenants),
        "tenants_processed": 0,
        "poll_runs": 0,
        "dispatch_runs": 0,
        "sla_runs": 0,
        "sla_escalated": 0,
        "sla_notifications": 0,
        "sla_reminders": 0,
        "docs_deadline_runs": 0,
        "docs_deadline_due": 0,
        "docs_deadline_manager_notifications": 0,
        "docs_deadline_candidate_telegram": 0,
    }

    for tenant in tenants:
        tenant_id = str(tenant.id)
        if not _tenant_email_module_enabled(tenant):
            continue

        do_poll = False
        if _tenant_email_incoming_enabled(tenant):
            interval_min = _tenant_email_sync_interval_minutes(tenant)
            prev = poll_last_run.get(tenant_id)
            if prev is None or (now - prev).total_seconds() >= interval_min * 60:
                do_poll = True

        prev_dispatch = dispatch_last_run.get(tenant_id)
        do_dispatch = prev_dispatch is None or (now - prev_dispatch).total_seconds() >= dispatch_every_seconds

        if not do_poll and not do_dispatch:
            continue
        tick_summary["tenants_processed"] = int(tick_summary["tenants_processed"]) + 1

        tenant_runtime = _RUNTIME_STATUS.setdefault("tenants", {}).setdefault(tenant_id, {})
        tenant_runtime.update(
            {
                "tenant_id": tenant_id,
                "tenant_name": getattr(tenant, "name", None) or tenant_id,
                "email_module_enabled": True,
                "email_incoming_enabled": bool(_tenant_email_incoming_enabled(tenant)),
                "last_seen_at": now.isoformat(),
            }
        )

        async with async_session_maker() as db:
            db_tenant = (db, UUID(tenant_id))
            if do_poll:
                try:
                    result = await comm_api.run_email_poll_worker(
                        comm_api.CommunicationEmailWorkerPollRequest(limit_per_account=25),
                        db_tenant=db_tenant,
                        current_user=fake_user,
                    )
                    poll_last_run[tenant_id] = now
                    tick_summary["poll_runs"] = int(tick_summary["poll_runs"]) + 1
                    tenant_runtime["last_poll_at"] = now.isoformat()
                    tenant_runtime["last_poll_result"] = {
                        "ingested_messages": int(getattr(result, "ingested_messages", 0) or 0),
                        "created_threads": int(getattr(result, "created_threads", 0) or 0),
                        "updated_threads": int(getattr(result, "updated_threads", 0) or 0),
                        "duplicate_messages": int(getattr(result, "duplicate_messages", 0) or 0),
                        "processed_accounts": int(getattr(result, "processed_accounts", 0) or 0),
                    }
                    if int(getattr(result, "ingested_messages", 0) or 0) > 0:
                        logger.info(
                            "[communications-scheduler] email poll tenant=%s ingested=%s created_threads=%s",
                            tenant_id,
                            getattr(result, "ingested_messages", 0),
                            getattr(result, "created_threads", 0),
                        )
                except Exception as exc:
                    try:
                        await db.rollback()
                    except Exception:
                        pass
                    logger.warning("[communications-scheduler] email poll failed tenant=%s (%s)", tenant_id, exc)
                    tenant_runtime["last_poll_error"] = str(exc)

            if do_dispatch:
                try:
                    result = await comm_api.run_email_dispatch_worker(
                        comm_api.CommunicationEmailWorkerDispatchRequest(limit=100, mark_delivered=True),
                        db_tenant=db_tenant,
                        current_user=fake_user,
                    )
                    dispatch_last_run[tenant_id] = now
                    tick_summary["dispatch_runs"] = int(tick_summary["dispatch_runs"]) + 1
                    tenant_runtime["last_dispatch_at"] = now.isoformat()
                    tenant_runtime["last_dispatch_result"] = {
                        "processed": int(getattr(result, "processed", 0) or 0),
                        "dispatched": int(getattr(result, "dispatched", 0) or 0),
                        "failed": int(getattr(result, "failed", 0) or 0),
                    }
                    if int(getattr(result, "processed", 0) or 0) > 0:
                        logger.info(
                            "[communications-scheduler] email dispatch tenant=%s processed=%s dispatched=%s failed=%s",
                            tenant_id,
                            getattr(result, "processed", 0),
                            getattr(result, "dispatched", 0),
                            getattr(result, "failed", 0),
                        )
                except Exception as exc:
                    try:
                        await db.rollback()
                    except Exception:
                        pass
                    logger.warning("[communications-scheduler] email dispatch failed tenant=%s (%s)", tenant_id, exc)
                    tenant_runtime["last_dispatch_error"] = str(exc)

            # SLA escalations run every scheduler tick (lightweight query, tenant-scoped)
            try:
                sla_stats = await _run_sla_escalations_for_tenant(db, tenant=tenant, now=now)
                tenant_runtime["last_sla_check_at"] = now.isoformat()
                tenant_runtime["last_sla_stats"] = dict(sla_stats)
                tick_summary["sla_runs"] = int(tick_summary["sla_runs"]) + 1
                tick_summary["sla_escalated"] = int(tick_summary["sla_escalated"]) + int(sla_stats.get("escalated", 0) or 0)
                tick_summary["sla_notifications"] = int(tick_summary["sla_notifications"]) + int(sla_stats.get("notifications", 0) or 0)
                tick_summary["sla_reminders"] = int(tick_summary["sla_reminders"]) + int(sla_stats.get("reminders", 0) or 0)
                if int(sla_stats.get("escalated", 0) or 0) > 0:
                    logger.info(
                        "[communications-scheduler] sla tenant=%s escalated=%s notifications=%s reminders=%s",
                        tenant_id,
                        sla_stats.get("escalated", 0),
                        sla_stats.get("notifications", 0),
                        sla_stats.get("reminders", 0),
                    )
                await db.commit()
            except Exception as exc:
                try:
                    await db.rollback()
                except Exception:
                    pass
                tenant_runtime["last_sla_error"] = str(exc)
                logger.warning("[communications-scheduler] sla escalation failed tenant=%s (%s)", tenant_id, exc)

            # Candidate docs deadlines: remind candidate + manager after intake completion if required docs are still missing.
            try:
                docs_stats = await _run_candidate_docs_deadlines_for_tenant(db, tenant=tenant, now=now)
                tenant_runtime["last_docs_deadline_check_at"] = now.isoformat()
                tenant_runtime["last_docs_deadline_stats"] = dict(docs_stats)
                tick_summary["docs_deadline_runs"] = int(tick_summary["docs_deadline_runs"]) + 1
                tick_summary["docs_deadline_due"] = int(tick_summary["docs_deadline_due"]) + int(docs_stats.get("due", 0) or 0)
                tick_summary["docs_deadline_manager_notifications"] = int(tick_summary["docs_deadline_manager_notifications"]) + int(
                    docs_stats.get("manager_notifications", 0) or 0
                )
                tick_summary["docs_deadline_candidate_telegram"] = int(tick_summary["docs_deadline_candidate_telegram"]) + int(
                    docs_stats.get("candidate_telegram", 0) or 0
                )
                if int(docs_stats.get("manager_notifications", 0) or 0) > 0 or int(docs_stats.get("candidate_telegram", 0) or 0) > 0:
                    logger.info(
                        "[communications-scheduler] docs deadlines tenant=%s manager_notifications=%s candidate_telegram=%s due=%s",
                        tenant_id,
                        docs_stats.get("manager_notifications", 0),
                        docs_stats.get("candidate_telegram", 0),
                        docs_stats.get("due", 0),
                    )
                await db.commit()
            except Exception as exc:
                try:
                    await db.rollback()
                except Exception:
                    pass
                tenant_runtime["last_docs_deadline_error"] = str(exc)
                logger.warning("[communications-scheduler] docs deadlines failed tenant=%s (%s)", tenant_id, exc)

    _RUNTIME_STATUS["last_tick_summary"] = tick_summary


async def communications_scheduler_loop(stop_event: asyncio.Event) -> None:
    state: Dict[str, Any] = {}
    tick = scheduler_tick_seconds()
    _RUNTIME_STATUS["active"] = True
    _RUNTIME_STATUS["started_at"] = datetime.now(timezone.utc).isoformat()
    _RUNTIME_STATUS["stopped_at"] = None
    _RUNTIME_STATUS["tick_seconds"] = tick
    logger.info("[communications-scheduler] started tick=%ss", tick)
    while not stop_event.is_set():
        started = datetime.now(timezone.utc)
        try:
            await _run_scheduler_tick(state)
        except Exception as exc:
            _RUNTIME_STATUS["last_tick_error"] = str(exc)
            logger.exception("[communications-scheduler] tick failed: %s", exc)
        finally:
            finished = datetime.now(timezone.utc)
            _RUNTIME_STATUS["last_tick_finished_at"] = finished.isoformat()
            _RUNTIME_STATUS["last_tick_duration_ms"] = int((finished - started).total_seconds() * 1000)
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=tick)
        except asyncio.TimeoutError:
            pass
    _RUNTIME_STATUS["active"] = False
    _RUNTIME_STATUS["stopped_at"] = datetime.now(timezone.utc).isoformat()
    logger.info("[communications-scheduler] stopped")


async def run_scheduler_tick_once() -> Dict[str, Any]:
    state: Dict[str, Any] = {}
    started = datetime.now(timezone.utc)
    try:
        await _run_scheduler_tick(state)
    except Exception as exc:
        _RUNTIME_STATUS["last_tick_error"] = str(exc)
        raise
    finally:
        finished = datetime.now(timezone.utc)
        _RUNTIME_STATUS["last_tick_finished_at"] = finished.isoformat()
        _RUNTIME_STATUS["last_tick_duration_ms"] = int((finished - started).total_seconds() * 1000)
    return scheduler_runtime_status()


def scheduler_runtime_status() -> Dict[str, Any]:
    return {
        "enabled": bool(scheduler_enabled()),
        "tick_seconds": int(scheduler_tick_seconds()),
        **_RUNTIME_STATUS,
        "tenants": dict(_RUNTIME_STATUS.get("tenants") or {}),
        "last_tick_summary": dict(_RUNTIME_STATUS.get("last_tick_summary") or {}),
    }
