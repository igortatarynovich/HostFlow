from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any, Dict, List
from uuid import UUID

import sqlalchemy as sa
from datetime import timedelta
from sqlalchemy.exc import OperationalError

from backend.app.db.session import async_session_maker
from backend.app.models.tenant import Tenant
from backend.app.core.queue import enqueue_job
from backend.app.observability.metrics import (
    increment_calendar_maintenance_error,
    increment_calendar_maintenance_queued,
    set_calendar_sync_lag_seconds,
)


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


def _leads_next_action_sla_enabled() -> bool:
    return _env_bool("COMM_SCHEDULER_LEADS_NEXT_ACTION_SLA_ENABLED", True)


def _tenant_leads_sla_settings(tenant: Tenant) -> Dict[str, Any]:
    root = tenant.settings if isinstance(tenant.settings, dict) else {}
    raw = root.get("leads_next_action_sla_v1")
    return raw if isinstance(raw, dict) else {}


def _tenant_leads_next_action_sla_enabled(tenant: Tenant) -> bool:
    if not _leads_next_action_sla_enabled():
        return False
    cfg = _tenant_leads_sla_settings(tenant)
    return bool(cfg.get("enabled", True))


def _tenant_leads_no_next_action_after_hours(tenant: Tenant) -> int:
    cfg = _tenant_leads_sla_settings(tenant)
    try:
        return max(1, int(cfg.get("noNextActionAfterHours") or 24))
    except Exception:
        return 24


def _tenant_leads_sla_create_notifications(tenant: Tenant) -> bool:
    cfg = _tenant_leads_sla_settings(tenant)
    return bool(cfg.get("createNotifications", True))


def _tenant_leads_sla_create_reminders(tenant: Tenant) -> bool:
    cfg = _tenant_leads_sla_settings(tenant)
    return bool(cfg.get("createReminders", True))


def _tenant_leads_sla_limit(tenant: Tenant) -> int:
    cfg = _tenant_leads_sla_settings(tenant)
    try:
        return max(10, min(500, int(cfg.get("limit") or 200)))
    except Exception:
        return 200


def _tenant_leads_stuck_after_days(tenant: Tenant) -> int:
    cfg = _tenant_leads_sla_settings(tenant)
    try:
        return max(1, int(cfg.get("stuckAfterDays") or 7))
    except Exception:
        return 7


def _tenant_leads_stuck_stages(tenant: Tenant) -> set[str]:
    cfg = _tenant_leads_sla_settings(tenant)
    raw = cfg.get("stages")
    if isinstance(raw, list):
        out = {str(x).strip() for x in raw if str(x or "").strip()}
        if out:
            return out
    # Default: active lead stages (exclude converted/lost)
    return {"new", "contacted", "qualified"}


def _invoices_overdue_sla_enabled() -> bool:
    return _env_bool("COMM_SCHEDULER_INVOICES_OVERDUE_SLA_ENABLED", True)


def _calendar_scheduler_enabled() -> bool:
    return _env_bool("CALENDAR_SCHEDULER_ENABLED", True)


def _calendar_reconcile_max_lag_minutes() -> int:
    return _env_int("CALENDAR_RECONCILE_MAX_LAG_MINUTES", 15)


def _calendar_reconcile_min_interval_minutes() -> int:
    return _env_int("CALENDAR_RECONCILE_MIN_INTERVAL_MINUTES", 5)


def _calendar_renew_lookahead_minutes() -> int:
    return _env_int("CALENDAR_RENEW_LOOKAHEAD_MINUTES", 10)


def _converted_lead_sweep_enabled() -> bool:
    return _env_bool("COMM_SCHEDULER_CONVERTED_LEAD_SWEEP_ENABLED", True)


def _converted_lead_sweep_interval_seconds() -> int:
    return _env_int("COMM_SCHEDULER_CONVERTED_LEAD_SWEEP_INTERVAL_SECONDS", 3600)


def _converted_lead_sweep_batch() -> int:
    return _env_int("COMM_SCHEDULER_CONVERTED_LEAD_SWEEP_BATCH", 120)


async def _run_calendar_maintenance_for_tenant(db, *, tenant: Tenant, now: datetime) -> Dict[str, int]:
    from backend.app.models.calendar_integration import (
        CalendarChannel,
        CalendarConnection,
        CalendarSyncCursor,
        CalendarSyncJob,
    )

    stats = {
        "connections": 0,
        "renew_queued": 0,
        "reconcile_queued": 0,
        "renew_failed": 0,
        "reconcile_failed": 0,
        "renew_skipped": 0,
        "reconcile_skipped": 0,
        "max_sync_lag_seconds": 0,
    }
    if not _calendar_scheduler_enabled():
        return stats

    tenant_id = str(tenant.id)
    connections = (
        await db.execute(
            sa.select(CalendarConnection)
            .where(
                CalendarConnection.tenant_id == tenant_id,
                CalendarConnection.status == "active",
            )
            .order_by(sa.asc(CalendarConnection.created_at))
        )
    ).scalars().all()
    stats["connections"] = len(connections)
    if not connections:
        return stats

    renew_lookahead = timedelta(minutes=_calendar_renew_lookahead_minutes())
    reconcile_max_lag = timedelta(minutes=_calendar_reconcile_max_lag_minutes())
    reconcile_min_interval = timedelta(minutes=_calendar_reconcile_min_interval_minutes())

    for conn in connections:
        conn_id = str(conn.id)
        provider = str(conn.provider or "").strip().lower()
        if provider not in {"google", "microsoft"}:
            continue

        channel = (
            await db.execute(
                sa.select(CalendarChannel)
                .where(CalendarChannel.connection_id == conn_id)
                .order_by(sa.desc(CalendarChannel.updated_at))
                .limit(1)
            )
        ).scalar_one_or_none()

        renew_due = False
        if channel is None:
            renew_due = True
        else:
            renew_after = channel.renew_after
            if renew_after is None:
                renew_due = True
            else:
                if renew_after.tzinfo is None:
                    renew_after = renew_after.replace(tzinfo=timezone.utc)
                renew_due = renew_after <= (now + renew_lookahead)

        if renew_due:
            dedupe_key = f"renew:{conn_id}"
            already = (
                await db.execute(
                    sa.select(CalendarSyncJob.id)
                    .where(
                        CalendarSyncJob.tenant_id == tenant_id,
                        CalendarSyncJob.dedupe_key == dedupe_key,
                        CalendarSyncJob.status.in_(["queued", "processing"]),
                    )
                    .limit(1)
                )
            ).scalar_one_or_none()
            if already:
                stats["renew_skipped"] += 1
            else:
                renew_job = CalendarSyncJob(
                    tenant_id=tenant_id,
                    source_kind=f"{provider}_subscription_renew",
                    operation="renew_subscription",
                    status="queued",
                    dedupe_key=dedupe_key,
                    payload={
                        "tenant_id": tenant_id,
                        "connection_id": conn_id,
                        "provider": provider,
                    },
                )
                db.add(renew_job)
                await db.flush()
                try:
                    await enqueue_job(
                        "calendar_sync_ingest",
                        sync_job_id=renew_job.id,
                        tenant_id=tenant_id,
                        job_id=f"calendar_sync_ingest:{renew_job.id}",
                    )
                    stats["renew_queued"] += 1
                    increment_calendar_maintenance_queued(tenant_id, "renew_subscription")
                except Exception:
                    stats["renew_failed"] += 1
                    increment_calendar_maintenance_error(tenant_id, "renew_enqueue_failed")

        cursor = (
            await db.execute(
                sa.select(CalendarSyncCursor)
                .where(CalendarSyncCursor.connection_id == conn_id)
                .order_by(sa.desc(CalendarSyncCursor.updated_at))
                .limit(1)
            )
        ).scalar_one_or_none()
        cursor_ts = cursor.last_synced_at if cursor is not None else None
        lag_seconds = None
        if cursor_ts is not None:
            if cursor_ts.tzinfo is None:
                cursor_ts = cursor_ts.replace(tzinfo=timezone.utc)
            lag_seconds = int((now - cursor_ts).total_seconds())
            stats["max_sync_lag_seconds"] = max(stats["max_sync_lag_seconds"], max(0, lag_seconds))

        reconcile_due = False
        if cursor_ts is None:
            reconcile_due = True
        else:
            reconcile_due = (now - cursor_ts) >= reconcile_max_lag

        if reconcile_due:
            dedupe_key = f"reconcile:{conn_id}:{str(getattr(cursor, 'cursor', '') or '')}"
            already = (
                await db.execute(
                    sa.select(CalendarSyncJob.id)
                    .where(
                        CalendarSyncJob.tenant_id == tenant_id,
                        CalendarSyncJob.dedupe_key == dedupe_key,
                        CalendarSyncJob.status.in_(["queued", "processing"]),
                    )
                    .limit(1)
                )
            ).scalar_one_or_none()
            too_soon = False
            if cursor_ts is not None:
                too_soon = (now - cursor_ts) < reconcile_min_interval
            if already or too_soon:
                stats["reconcile_skipped"] += 1
            else:
                reconcile_job = CalendarSyncJob(
                    tenant_id=tenant_id,
                    source_kind=f"{provider}_reconcile",
                    operation="reconcile",
                    status="queued",
                    dedupe_key=dedupe_key,
                    payload={
                        "tenant_id": tenant_id,
                        "connection_id": conn_id,
                        "provider": provider,
                        "cursor": str(getattr(cursor, "cursor", "") or "") or None,
                        "cursor_meta": dict(getattr(cursor, "cursor_meta_json", {}) or {}),
                    },
                )
                db.add(reconcile_job)
                await db.flush()
                try:
                    await enqueue_job(
                        "calendar_sync_ingest",
                        sync_job_id=reconcile_job.id,
                        tenant_id=tenant_id,
                        job_id=f"calendar_sync_ingest:{reconcile_job.id}",
                    )
                    stats["reconcile_queued"] += 1
                    increment_calendar_maintenance_queued(tenant_id, "reconcile")
                except Exception:
                    stats["reconcile_failed"] += 1
                    increment_calendar_maintenance_error(tenant_id, "reconcile_enqueue_failed")

    set_calendar_sync_lag_seconds(tenant_id, int(stats.get("max_sync_lag_seconds", 0) or 0))
    return stats


def _tenant_invoices_sla_settings(tenant: Tenant) -> Dict[str, Any]:
    root = tenant.settings if isinstance(tenant.settings, dict) else {}
    raw = root.get("invoice_overdue_sla_v1")
    return raw if isinstance(raw, dict) else {}


def _tenant_invoices_overdue_sla_enabled(tenant: Tenant) -> bool:
    if not _invoices_overdue_sla_enabled():
        return False
    cfg = _tenant_invoices_sla_settings(tenant)
    return bool(cfg.get("enabled", True))


def _tenant_invoices_sla_create_notifications(tenant: Tenant) -> bool:
    cfg = _tenant_invoices_sla_settings(tenant)
    return bool(cfg.get("createNotifications", True))


def _tenant_invoices_sla_create_reminders(tenant: Tenant) -> bool:
    cfg = _tenant_invoices_sla_settings(tenant)
    return bool(cfg.get("createReminders", True))


def _tenant_invoices_sla_limit(tenant: Tenant) -> int:
    cfg = _tenant_invoices_sla_settings(tenant)
    try:
        return max(10, min(500, int(cfg.get("limit") or 200)))
    except Exception:
        return 200


def _tenant_invoices_overdue_after_days(tenant: Tenant) -> int:
    cfg = _tenant_invoices_sla_settings(tenant)
    try:
        return max(0, int(cfg.get("overdueAfterDays") or 0))
    except Exception:
        return 0


async def _pick_ops_assignee_id(db, *, tenant_id: str) -> str | None:
    """Pick a stable ops recipient for SLA nudges (best-effort)."""
    from backend.app.models.user import Role, User

    row = await db.execute(
        sa.select(User.id)
        .where(
            User.is_active.is_(True),
            sa.or_(User.tenant_id == tenant_id, User.tenant_id.is_(None)),
            # IMPORTANT: keep only real DB enum values (no aliases like "owner").
            User.role.in_([Role.superadmin.value, Role.administrator.value, Role.employee.value]),
        )
        .order_by(sa.asc(User.created_at))
        .limit(1)
    )
    return row.scalar_one_or_none()


async def _latest_lead_stage_change_map(db, *, tenant_id: str, lead_ids: list[str]) -> Dict[str, datetime]:
    """Fetch last lead.stage_changed timestamps from ActivityLog for the given leads."""
    from backend.app.models.audit import ActivityLog

    if not lead_ids:
        return {}
    stmt = (
        sa.select(ActivityLog.target_id, sa.func.max(ActivityLog.created_at))
        .where(
            ActivityLog.tenant_id == tenant_id,
            ActivityLog.target_type == "lead",
            ActivityLog.action == "lead.stage_changed",
            ActivityLog.target_id.in_(lead_ids),
        )
        .group_by(ActivityLog.target_id)
    )
    rows = (await db.execute(stmt)).all()
    return {str(tid): ts for tid, ts in rows if tid and ts}


async def _run_leads_next_action_sla_for_tenant(db, *, tenant: Tenant, now: datetime) -> Dict[str, int]:
    """
    Leads SLA nudge: if a processed lead has no next action for N hours, create:
    - in-app notification (optional)
    - internal reminder assigned to ops recipient (optional)
    Idempotent via reminder existence check for type=leads_no_next_action.
    """
    from backend.app.models.lead import Lead
    from backend.app.models.reminder import Reminder, ReminderStatus
    from backend.app.services.user_notifications import create_notification

    stats = {"checked": 0, "due": 0, "notifications": 0, "reminders": 0, "skipped_unassigned": 0}
    if not _tenant_leads_next_action_sla_enabled(tenant):
        return stats

    tenant_id = str(tenant.id)
    limit = _tenant_leads_sla_limit(tenant)
    threshold_hours = _tenant_leads_no_next_action_after_hours(tenant)
    create_notifications = _tenant_leads_sla_create_notifications(tenant)
    create_reminders = _tenant_leads_sla_create_reminders(tenant)

    assignee_id = await _pick_ops_assignee_id(db, tenant_id=tenant_id)
    if not assignee_id:
        stats["skipped_unassigned"] += 1
        return stats

    active_statuses = (ReminderStatus.pending, ReminderStatus.new, ReminderStatus.overdue)
    # Cross-DB cutoff: compute in python and compare.
    cutoff_dt = now - timedelta(hours=int(threshold_hours))

    reminder_exists_active = (
        sa.exists()
        .where(
            Reminder.tenant_id == tenant_id,
            Reminder.entity_type == "lead",
            Reminder.entity_id == Lead.id,
            Reminder.status.in_(active_statuses),
        )
        .correlate(Lead)
    )

    # Candidates: processed leads with no active reminder and older than threshold.
    stmt = (
        sa.select(Lead.id, Lead.created_at, Lead.stage)
        .where(
            Lead.tenant_id == tenant_id,
            Lead.status == "processed",
            Lead.candidate_id.is_(None),
            Lead.created_at <= cutoff_dt,
            ~reminder_exists_active,
        )
        .order_by(sa.asc(Lead.created_at))
        .limit(limit)
    )
    rows = (await db.execute(stmt)).all()
    stats["checked"] = len(rows)
    if not rows:
        return stats

    for lead_id, created_at, stage in rows:
        lid = str(lead_id)
        stats["due"] += 1
        due_key = f"{tenant_id}:{lid}:{threshold_hours}"

        if create_notifications:
            created_n = await create_notification(
                db,
                tenant_id=tenant_id,
                user_id=str(assignee_id),
                event_type="lead_no_next_action",
                entity_type="lead",
                entity_id=lid,
                payload={
                    "type": "lead_no_next_action",
                    "source": "leads_next_action_sla",
                    "severity": "medium",
                    "requires_action": True,
                    "title": "Lead without next action",
                    "description": f"Processed lead has no next action for {threshold_hours}h+.",
                    "lead_id": lid,
                    "stage": str(stage or ""),
                    "created_at": created_at.isoformat() if hasattr(created_at, "isoformat") else None,
                    "threshold_hours": int(threshold_hours),
                    "dedupe_key": f"lead_no_next_action:{due_key}",
                },
                # Keep bell signal low-noise; reminders are the primary actionable queue.
                dedupe_window_minutes=60 * 24 * 30,
            )
            if created_n is not None:
                stats["notifications"] += 1

        if create_reminders:
            # Idempotency: avoid duplicate active reminders of this type.
            existing = (
                await db.execute(
                    sa.select(Reminder.id)
                    .where(
                        Reminder.tenant_id == tenant_id,
                        Reminder.entity_type == "lead",
                        Reminder.entity_id == lid,
                        Reminder.assignee_id == str(assignee_id),
                        Reminder.type == "leads_no_next_action",
                        Reminder.status.in_(list(active_statuses)),
                    )
                    .limit(1)
                )
            ).scalar_one_or_none()
            if not existing:
                reminder = Reminder(
                    tenant_id=tenant_id,
                    type="leads_no_next_action",
                    entity_type="lead",
                    entity_id=lid,
                    title="Lead: create next action",
                    description=f"No next action for {threshold_hours}h+ (processed lead).",
                    owner_id=str(assignee_id),
                    assignee_id=str(assignee_id),
                    priority="normal",
                    channel="internal",
                    due_at=now,
                    remind_at=now,
                    status=ReminderStatus.pending,
                    message="Lead requires next action",
                    payload={
                        "lead_id": lid,
                        "threshold_hours": int(threshold_hours),
                        "created_at": created_at.isoformat() if hasattr(created_at, "isoformat") else None,
                        "stage": str(stage or ""),
                        "source": "leads_next_action_sla",
                    },
                    created_by=None,
                )
                db.add(reminder)
                stats["reminders"] += 1

    return stats


async def _run_leads_stuck_stage_sla_for_tenant(db, *, tenant: Tenant, now: datetime) -> Dict[str, int]:
    """
    Leads stuck-in-stage: for processed leads in selected stages, if no stage change for D days,
    create best-effort nudge (notification + reminder). Idempotent by reminder existence.
    """
    from backend.app.models.lead import Lead
    from backend.app.models.reminder import Reminder, ReminderStatus
    from backend.app.services.user_notifications import create_notification

    stats = {"checked": 0, "due": 0, "notifications": 0, "reminders": 0, "skipped_unassigned": 0}
    if not _tenant_leads_next_action_sla_enabled(tenant):
        return stats

    tenant_id = str(tenant.id)
    limit = _tenant_leads_sla_limit(tenant)
    stages = _tenant_leads_stuck_stages(tenant)
    stuck_days = _tenant_leads_stuck_after_days(tenant)
    create_notifications = _tenant_leads_sla_create_notifications(tenant)
    create_reminders = _tenant_leads_sla_create_reminders(tenant)
    cutoff_dt = now - timedelta(days=int(stuck_days))

    assignee_id = await _pick_ops_assignee_id(db, tenant_id=tenant_id)
    if not assignee_id:
        stats["skipped_unassigned"] += 1
        return stats

    # Consider only leads in configured stages; if stage is NULL, treat as "new".
    stmt = (
        sa.select(Lead.id, Lead.created_at, Lead.stage)
        .where(
            Lead.tenant_id == tenant_id,
            Lead.status == "processed",
            Lead.candidate_id.is_(None),
            sa.func.coalesce(Lead.stage, "new").in_(list(stages)),
        )
        .order_by(sa.asc(Lead.created_at))
        .limit(limit)
    )
    rows = (await db.execute(stmt)).all()
    stats["checked"] = len(rows)
    if not rows:
        return stats

    lead_ids = [str(lid) for lid, _c, _s in rows if lid]
    last_change_map = await _latest_lead_stage_change_map(db, tenant_id=tenant_id, lead_ids=lead_ids)

    active_statuses = (ReminderStatus.pending, ReminderStatus.new, ReminderStatus.overdue)
    for lead_id, created_at, stage in rows:
        lid = str(lead_id)
        last_change_at = last_change_map.get(lid) or (created_at if isinstance(created_at, datetime) else None) or now
        if last_change_at.tzinfo is None:
            last_change_at = last_change_at.replace(tzinfo=timezone.utc)
        if last_change_at > cutoff_dt:
            continue

        stats["due"] += 1
        due_key = f"{tenant_id}:{lid}:{stuck_days}:{str(stage or '')}"

        if create_notifications:
            created_n = await create_notification(
                db,
                tenant_id=tenant_id,
                user_id=str(assignee_id),
                event_type="lead_stuck_stage",
                entity_type="lead",
                entity_id=lid,
                payload={
                    "type": "lead_stuck_stage",
                    "source": "leads_next_action_sla",
                    "severity": "medium",
                    "requires_action": True,
                    "title": "Lead stuck in stage",
                    "description": f"No stage change for {stuck_days}d+.",
                    "lead_id": lid,
                    "stage": str(stage or "new"),
                    "last_stage_change_at": last_change_at.isoformat(),
                    "stuck_days": int(stuck_days),
                    "dedupe_key": f"lead_stuck_stage:{due_key}",
                },
                # Keep bell signal low-noise; reminders are the primary actionable queue.
                dedupe_window_minutes=60 * 24 * 30,
            )
            if created_n is not None:
                stats["notifications"] += 1

        if create_reminders:
            existing = (
                await db.execute(
                    sa.select(Reminder.id)
                    .where(
                        Reminder.tenant_id == tenant_id,
                        Reminder.entity_type == "lead",
                        Reminder.entity_id == lid,
                        Reminder.assignee_id == str(assignee_id),
                        Reminder.type == "leads_stuck_stage",
                        Reminder.status.in_(list(active_statuses)),
                    )
                    .limit(1)
                )
            ).scalar_one_or_none()
            if not existing:
                reminder = Reminder(
                    tenant_id=tenant_id,
                    type="leads_stuck_stage",
                    entity_type="lead",
                    entity_id=lid,
                    title="Lead: check stage progress",
                    description=f"No stage change for {stuck_days}d+ (processed lead).",
                    owner_id=str(assignee_id),
                    assignee_id=str(assignee_id),
                    priority="normal",
                    channel="internal",
                    due_at=now,
                    remind_at=now,
                    status=ReminderStatus.pending,
                    message="Lead stuck in stage",
                    payload={
                        "lead_id": lid,
                        "stuck_days": int(stuck_days),
                        "last_stage_change_at": last_change_at.isoformat(),
                        "stage": str(stage or "new"),
                        "source": "leads_next_action_sla",
                    },
                    created_by=None,
                )
                db.add(reminder)
                stats["reminders"] += 1

    return stats


async def _run_invoices_overdue_sla_for_tenant(db, *, tenant: Tenant, now: datetime) -> Dict[str, int]:
    """
    Invoice overdue SLA: create best-effort notification + internal reminder for overdue invoices.
    Idempotency:
    - notification dedupe by due date key
    - reminder check by type/entity/assignee and active statuses
    """
    from backend.app.models.invoice import Invoice
    from backend.app.models.reminder import Reminder, ReminderStatus
    from backend.app.services.user_notifications import create_notification

    stats = {"checked": 0, "due": 0, "notifications": 0, "reminders": 0, "skipped_unassigned": 0}
    if not _tenant_invoices_overdue_sla_enabled(tenant):
        return stats

    tenant_id = str(tenant.id)
    limit = _tenant_invoices_sla_limit(tenant)
    overdue_after_days = _tenant_invoices_overdue_after_days(tenant)
    create_notifications = _tenant_invoices_sla_create_notifications(tenant)
    create_reminders = _tenant_invoices_sla_create_reminders(tenant)
    assignee_id = await _pick_ops_assignee_id(db, tenant_id=tenant_id)
    if not assignee_id:
        stats["skipped_unassigned"] += 1
        return stats

    due_cutoff = (now.date() - timedelta(days=int(overdue_after_days)))
    # Overdue candidates: invoice due date passed threshold and not fully settled/cancelled.
    stmt = (
        sa.select(
            Invoice.id,
            Invoice.invoice_number,
            Invoice.status,
            Invoice.due_date,
            Invoice.total_amount,
            Invoice.paid_amount,
            Invoice.service_order_id,
            Invoice.company_id,
            Invoice.candidate_id,
        )
        .where(
            Invoice.tenant_id == tenant_id,
            Invoice.due_date.is_not(None),
            Invoice.due_date <= due_cutoff,
            sa.func.coalesce(Invoice.status, "").notin_(["paid", "cancelled"]),
        )
        .order_by(sa.asc(Invoice.due_date))
        .limit(limit)
    )
    rows = (await db.execute(stmt)).all()
    stats["checked"] = len(rows)
    if not rows:
        return stats

    active_statuses = (ReminderStatus.pending, ReminderStatus.new, ReminderStatus.overdue)
    for inv_id, inv_number, inv_status, due_date, total_amount, paid_amount, service_order_id, company_id, candidate_id in rows:
        iid = str(inv_id)
        total = float(total_amount or 0)
        paid = float(paid_amount or 0)
        outstanding = max(0.0, total - paid)
        if outstanding <= 0:
            continue

        stats["due"] += 1
        due_key = f"{tenant_id}:{iid}:{str(due_date)}"
        title = "Invoice overdue"
        description = f"Invoice {str(inv_number or iid)[:32]} is overdue. Outstanding: {round(outstanding, 2)}."

        if create_notifications:
            created_n = await create_notification(
                db,
                tenant_id=tenant_id,
                user_id=str(assignee_id),
                event_type="invoice_overdue",
                entity_type="invoice",
                entity_id=iid,
                payload={
                    "type": "invoice_overdue",
                    "source": "invoice_overdue_sla",
                    "severity": "high",
                    "requires_action": True,
                    "title": title,
                    "description": description,
                    "invoice_id": iid,
                    "invoice_number": str(inv_number or ""),
                    "invoice_status": str(inv_status or ""),
                    "due_date": str(due_date) if due_date else None,
                    "outstanding_amount": round(outstanding, 2),
                    "service_order_id": str(service_order_id) if service_order_id else None,
                    "company_id": str(company_id) if company_id else None,
                    "candidate_id": str(candidate_id) if candidate_id else None,
                    "dedupe_key": f"invoice_overdue:{due_key}",
                },
                dedupe_window_minutes=60 * 24,
            )
            if created_n is not None:
                stats["notifications"] += 1

        if create_reminders:
            existing = (
                await db.execute(
                    sa.select(Reminder.id)
                    .where(
                        Reminder.tenant_id == tenant_id,
                        Reminder.entity_type == "invoice",
                        Reminder.entity_id == iid,
                        Reminder.assignee_id == str(assignee_id),
                        Reminder.type == "invoice_overdue_payment",
                        Reminder.status.in_(list(active_statuses)),
                    )
                    .limit(1)
                )
            ).scalar_one_or_none()
            if not existing:
                reminder = Reminder(
                    tenant_id=tenant_id,
                    type="invoice_overdue_payment",
                    entity_type="invoice",
                    entity_id=iid,
                    title=title,
                    description=description,
                    owner_id=str(assignee_id),
                    assignee_id=str(assignee_id),
                    priority="high",
                    channel="internal",
                    due_at=now,
                    remind_at=now,
                    status=ReminderStatus.overdue,
                    message="Overdue invoice requires payment follow-up",
                    payload={
                        "invoice_id": iid,
                        "invoice_number": str(inv_number or ""),
                        "invoice_status": str(inv_status or ""),
                        "due_date": str(due_date) if due_date else None,
                        "outstanding_amount": round(outstanding, 2),
                        "service_order_id": str(service_order_id) if service_order_id else None,
                        "source": "invoice_overdue_sla",
                    },
                    created_by=None,
                )
                db.add(reminder)
                stats["reminders"] += 1

    return stats


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
        notif = None
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
            if notif is not None:
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
                created_doc_n = await create_notification(
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
                if created_doc_n is not None:
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
        "leads_sla_runs": 0,
        "leads_sla_due": 0,
        "leads_sla_notifications": 0,
        "leads_sla_reminders": 0,
        "invoices_sla_runs": 0,
        "invoices_sla_due": 0,
        "invoices_sla_notifications": 0,
        "invoices_sla_reminders": 0,
        "calendar_runs": 0,
        "calendar_connections": 0,
        "calendar_renew_queued": 0,
        "calendar_reconcile_queued": 0,
        "calendar_renew_failed": 0,
        "calendar_reconcile_failed": 0,
        "calendar_sync_lag_max_seconds": 0,
        "invalid_tenants_skipped": 0,
    }

    for tenant in tenants:
        tenant_id = str(tenant.id)
        try:
            tenant_uuid = UUID(tenant_id)
        except ValueError:
            tick_summary["invalid_tenants_skipped"] = int(tick_summary["invalid_tenants_skipped"]) + 1
            continue

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

        from backend.app.db.deps import tenant_enforced_session

        async with tenant_enforced_session(
            tenant_uuid,
            actor_id="system:communications-scheduler",
        ) as db:
            db_tenant = (db, tenant_uuid)
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

            # Leads next-action SLA nudges: processed leads without next action for N hours.
            try:
                leads_stats = await _run_leads_next_action_sla_for_tenant(db, tenant=tenant, now=now)
                tenant_runtime["last_leads_sla_check_at"] = now.isoformat()
                tenant_runtime["last_leads_sla_stats"] = dict(leads_stats)
                tick_summary["leads_sla_runs"] = int(tick_summary["leads_sla_runs"]) + 1
                tick_summary["leads_sla_due"] = int(tick_summary["leads_sla_due"]) + int(leads_stats.get("due", 0) or 0)
                tick_summary["leads_sla_notifications"] = int(tick_summary["leads_sla_notifications"]) + int(
                    leads_stats.get("notifications", 0) or 0
                )
                tick_summary["leads_sla_reminders"] = int(tick_summary["leads_sla_reminders"]) + int(leads_stats.get("reminders", 0) or 0)
                if int(leads_stats.get("reminders", 0) or 0) > 0 or int(leads_stats.get("notifications", 0) or 0) > 0:
                    logger.info(
                        "[communications-scheduler] leads SLA tenant=%s due=%s notifications=%s reminders=%s",
                        tenant_id,
                        leads_stats.get("due", 0),
                        leads_stats.get("notifications", 0),
                        leads_stats.get("reminders", 0),
                    )
                await db.commit()
            except Exception as exc:
                try:
                    await db.rollback()
                except Exception:
                    pass
                tenant_runtime["last_leads_sla_error"] = str(exc)
                logger.warning("[communications-scheduler] leads SLA failed tenant=%s (%s)", tenant_id, exc)

            # Leads stuck-in-stage SLA nudges.
            try:
                stuck_stats = await _run_leads_stuck_stage_sla_for_tenant(db, tenant=tenant, now=now)
                tenant_runtime["last_leads_stuck_check_at"] = now.isoformat()
                tenant_runtime["last_leads_stuck_stats"] = dict(stuck_stats)
                tick_summary["leads_sla_runs"] = int(tick_summary["leads_sla_runs"]) + 1
                tick_summary["leads_sla_due"] = int(tick_summary["leads_sla_due"]) + int(stuck_stats.get("due", 0) or 0)
                tick_summary["leads_sla_notifications"] = int(tick_summary["leads_sla_notifications"]) + int(
                    stuck_stats.get("notifications", 0) or 0
                )
                tick_summary["leads_sla_reminders"] = int(tick_summary["leads_sla_reminders"]) + int(stuck_stats.get("reminders", 0) or 0)
                if int(stuck_stats.get("reminders", 0) or 0) > 0 or int(stuck_stats.get("notifications", 0) or 0) > 0:
                    logger.info(
                        "[communications-scheduler] leads stuck tenant=%s due=%s notifications=%s reminders=%s",
                        tenant_id,
                        stuck_stats.get("due", 0),
                        stuck_stats.get("notifications", 0),
                        stuck_stats.get("reminders", 0),
                    )
                await db.commit()
            except Exception as exc:
                try:
                    await db.rollback()
                except Exception:
                    pass
                tenant_runtime["last_leads_stuck_error"] = str(exc)
                logger.warning("[communications-scheduler] leads stuck failed tenant=%s (%s)", tenant_id, exc)

            # Invoice overdue SLA nudges.
            try:
                invoices_stats = await _run_invoices_overdue_sla_for_tenant(db, tenant=tenant, now=now)
                tenant_runtime["last_invoices_sla_check_at"] = now.isoformat()
                tenant_runtime["last_invoices_sla_stats"] = dict(invoices_stats)
                tick_summary["invoices_sla_runs"] = int(tick_summary["invoices_sla_runs"]) + 1
                tick_summary["invoices_sla_due"] = int(tick_summary["invoices_sla_due"]) + int(invoices_stats.get("due", 0) or 0)
                tick_summary["invoices_sla_notifications"] = int(tick_summary["invoices_sla_notifications"]) + int(
                    invoices_stats.get("notifications", 0) or 0
                )
                tick_summary["invoices_sla_reminders"] = int(tick_summary["invoices_sla_reminders"]) + int(
                    invoices_stats.get("reminders", 0) or 0
                )
                if int(invoices_stats.get("reminders", 0) or 0) > 0 or int(invoices_stats.get("notifications", 0) or 0) > 0:
                    logger.info(
                        "[communications-scheduler] invoices SLA tenant=%s due=%s notifications=%s reminders=%s",
                        tenant_id,
                        invoices_stats.get("due", 0),
                        invoices_stats.get("notifications", 0),
                        invoices_stats.get("reminders", 0),
                    )
                await db.commit()
            except Exception as exc:
                try:
                    await db.rollback()
                except Exception:
                    pass
                tenant_runtime["last_invoices_sla_error"] = str(exc)
                logger.warning("[communications-scheduler] invoices SLA failed tenant=%s (%s)", tenant_id, exc)

            # Calendar maintenance: keep provider subscriptions healthy and queue reconcile.
            try:
                calendar_stats = await _run_calendar_maintenance_for_tenant(db, tenant=tenant, now=now)
                tenant_runtime["last_calendar_maintenance_at"] = now.isoformat()
                tenant_runtime["last_calendar_maintenance_stats"] = dict(calendar_stats)
                tick_summary["calendar_runs"] = int(tick_summary["calendar_runs"]) + 1
                tick_summary["calendar_connections"] = int(tick_summary["calendar_connections"]) + int(
                    calendar_stats.get("connections", 0) or 0
                )
                tick_summary["calendar_renew_queued"] = int(tick_summary["calendar_renew_queued"]) + int(
                    calendar_stats.get("renew_queued", 0) or 0
                )
                tick_summary["calendar_reconcile_queued"] = int(tick_summary["calendar_reconcile_queued"]) + int(
                    calendar_stats.get("reconcile_queued", 0) or 0
                )
                tick_summary["calendar_sync_lag_max_seconds"] = max(
                    int(tick_summary.get("calendar_sync_lag_max_seconds") or 0),
                    int(calendar_stats.get("max_sync_lag_seconds", 0) or 0),
                )
                tick_summary["calendar_renew_failed"] = int(tick_summary["calendar_renew_failed"]) + int(
                    calendar_stats.get("renew_failed", 0) or 0
                )
                tick_summary["calendar_reconcile_failed"] = int(tick_summary["calendar_reconcile_failed"]) + int(
                    calendar_stats.get("reconcile_failed", 0) or 0
                )
                await db.commit()
            except Exception as exc:
                try:
                    await db.rollback()
                except Exception:
                    pass
                increment_calendar_maintenance_error(tenant_id, "maintenance_tick_failed")
                tenant_runtime["last_calendar_maintenance_error"] = str(exc)
                logger.warning("[communications-scheduler] calendar maintenance failed tenant=%s (%s)", tenant_id, exc)

    tick_summary.setdefault("risk_intel_runs", 0)
    tick_summary.setdefault("risk_intel_errors", 0)
    await _run_risk_intel_hourly_pass(state, tenants, now, tick_summary)

    await _run_converted_lead_sweep_pass(state, tenants, now, tick_summary)

    await _run_notification_retention_pass(state, tenants, now, tick_summary)

    _RUNTIME_STATUS["last_tick_summary"] = tick_summary


async def _run_notification_retention_pass(
    state: Dict[str, Any],
    tenants: List[Any],
    now: datetime,
    tick_summary: Dict[str, Any],
) -> None:
    """Age out notifications past their retention class (hourly, batched per tenant)."""
    from backend.app.services.notification_retention import (
        purge_expired_notifications,
        retention_enabled,
        retention_interval_seconds,
    )

    if not retention_enabled():
        return
    interval = retention_interval_seconds()
    last = state.setdefault("notification_retention_last", {})
    tick_summary.setdefault("notification_retention_runs", 0)
    tick_summary.setdefault("notification_retention_deleted", 0)
    tick_summary.setdefault("notification_retention_errors", 0)

    for tenant in tenants:
        tid = str(getattr(tenant, "id", "") or "")
        if not tid:
            continue
        # Some legacy/test tenants carry non-UUID ids; tenant_enforced_session needs
        # a real UUID. Skip them quietly instead of warning once per tenant per run.
        try:
            tenant_uuid = UUID(tid)
        except (ValueError, AttributeError, TypeError):
            continue
        prev = last.get(tid)
        if prev is not None and (now - prev).total_seconds() < interval:
            continue
        try:
            from backend.app.db.deps import tenant_enforced_session

            async with tenant_enforced_session(
                tenant_uuid,
                actor_id="system:notification-retention",
            ) as db:
                stats = await purge_expired_notifications(db, tenant_id=tid, now=now)
                await db.commit()
            last[tid] = now
            tick_summary["notification_retention_runs"] = int(
                tick_summary.get("notification_retention_runs") or 0
            ) + 1
            tick_summary["notification_retention_deleted"] = int(
                tick_summary.get("notification_retention_deleted") or 0
            ) + int(stats.get("total", 0) or 0)
        except OperationalError as exc:
            tick_summary["notification_retention_errors"] = int(
                tick_summary.get("notification_retention_errors") or 0
            ) + 1
            logger.warning(
                "[communications-scheduler] notification retention skipped tenant=%s (schema/db: %s)",
                tid,
                exc,
            )
        except Exception as exc:
            tick_summary["notification_retention_errors"] = int(
                tick_summary.get("notification_retention_errors") or 0
            ) + 1
            logger.warning(
                "[communications-scheduler] notification retention failed tenant=%s (%s)", tid, exc
            )


async def _run_converted_lead_sweep_pass(
    state: Dict[str, Any],
    tenants: List[Any],
    now: datetime,
    tick_summary: Dict[str, Any],
) -> None:
    """Clear lead-scoped reminders/planner rows that survived a lead→candidate link (hook missed or legacy data)."""
    if not _converted_lead_sweep_enabled():
        return
    interval = _converted_lead_sweep_interval_seconds()
    batch = _converted_lead_sweep_batch()
    last = state.setdefault("converted_lead_sweep_last", {})
    tick_summary.setdefault("converted_lead_sweep_runs", 0)
    tick_summary.setdefault("converted_lead_sweep_leads", 0)
    tick_summary.setdefault("converted_lead_sweep_reminders", 0)
    tick_summary.setdefault("converted_lead_sweep_notifications", 0)
    tick_summary.setdefault("converted_lead_sweep_planner", 0)
    tick_summary.setdefault("converted_lead_sweep_errors", 0)

    try:
        from backend.app.services.lead_lifecycle import sweep_converted_lead_operational_noise
    except Exception as exc:
        logger.warning("[communications-scheduler] converted_lead_sweep import failed: %s", exc)
        return

    for tenant in tenants:
        tid = str(getattr(tenant, "id", "") or "")
        if not tid:
            continue
        prev = last.get(tid)
        if prev is not None and (now - prev).total_seconds() < interval:
            continue
        try:
            from backend.app.db.deps import tenant_enforced_session

            async with tenant_enforced_session(
                UUID(tid),
                actor_id="system:converted-lead-sweep",
            ) as db:
                stats = await sweep_converted_lead_operational_noise(
                    db,
                    tenant_id=tid,
                    limit=batch,
                    now=now,
                    actor_id="system-scheduler",
                )
                await db.commit()
            last[tid] = now
            tick_summary["converted_lead_sweep_runs"] = int(tick_summary.get("converted_lead_sweep_runs") or 0) + 1
            tick_summary["converted_lead_sweep_leads"] = int(tick_summary.get("converted_lead_sweep_leads") or 0) + int(
                stats.get("leads_processed", 0) or 0
            )
            tick_summary["converted_lead_sweep_reminders"] = int(tick_summary.get("converted_lead_sweep_reminders") or 0) + int(
                stats.get("reminders_cancelled", 0) or 0
            )
            tick_summary["converted_lead_sweep_notifications"] = int(
                tick_summary.get("converted_lead_sweep_notifications") or 0
            ) + int(stats.get("notifications_marked_read", 0) or 0)
            tick_summary["converted_lead_sweep_planner"] = int(tick_summary.get("converted_lead_sweep_planner") or 0) + int(
                stats.get("planner_events_cancelled", 0) or 0
            )
        except Exception as exc:
            tick_summary["converted_lead_sweep_errors"] = int(tick_summary.get("converted_lead_sweep_errors") or 0) + 1
            logger.warning("[communications-scheduler] converted_lead_sweep failed tenant=%s (%s)", tid, exc)


async def _run_risk_intel_hourly_pass(
    state: Dict[str, Any],
    tenants: List[Any],
    now: datetime,
    tick_summary: Dict[str, Any],
) -> None:
    """Phase B: persist hourly risk aggregate + shadow rows (all active tenants, throttled)."""
    if not _env_bool("RISK_INTEL_HOURLY_ENABLED", True):
        return
    interval = _env_int("RISK_INTEL_HOURLY_SECONDS", 3600)
    last = state.setdefault("risk_intel_hourly_last", {})
    try:
        from backend.app.services.risk_intel_v1 import run_risk_intel_hourly_job
    except Exception as exc:
        logger.warning("[communications-scheduler] risk_intel import failed: %s", exc)
        return

    for tenant in tenants:
        tid = str(getattr(tenant, "id", "") or "")
        if not tid:
            continue
        prev = last.get(tid)
        if prev is not None and (now - prev).total_seconds() < interval:
            continue
        try:
            from backend.app.db.deps import tenant_enforced_session

            async with tenant_enforced_session(
                UUID(tid),
                actor_id="system:risk-intel-hourly",
            ) as db:
                await run_risk_intel_hourly_job(db, tenant, now)
                await db.commit()
            last[tid] = now
            tick_summary["risk_intel_runs"] = int(tick_summary.get("risk_intel_runs") or 0) + 1
        except OperationalError as exc:
            tick_summary["risk_intel_errors"] = int(tick_summary.get("risk_intel_errors") or 0) + 1
            logger.warning(
                "[communications-scheduler] risk_intel hourly skipped tenant=%s (schema/db: %s)",
                tid,
                exc,
            )
        except Exception as exc:
            tick_summary["risk_intel_errors"] = int(tick_summary.get("risk_intel_errors") or 0) + 1
            logger.warning("[communications-scheduler] risk_intel hourly failed tenant=%s (%s)", tid, exc)


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
