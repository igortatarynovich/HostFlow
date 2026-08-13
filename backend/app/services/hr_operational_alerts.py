"""HR operational alerts — react layer on top of ``hr_operational_risk`` (v1).

* Reads risk rows only (via ``list_operational_risk_items``); does **not** re-scan ``Candidate``.
* When ``dry_run=False``, may create **in-app notifications** (throttled / deduped) and **audit** rows.
* Intended for **cron / worker** — **do not** invoke from ``GET /hr/dashboard/*`` (avoids spam on refresh).

Throttling / idempotency: stable ``related_entity_id`` per risk fingerprint **plus** a direct
pre-check query (``create_notification``'s built-in dedupe only scans the latest 50 rows per user).
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.user import User, Role as UserRole
from backend.app.models.user_notification import UserNotification
from backend.app.services.audit import log_activity
from backend.app.services.hr_operational_risk import list_operational_risk_items
from backend.app.services.user_notifications import create_notification

_DEDUPE_MINUTES_BY_SEVERITY: dict[str, int] = {
    "critical": 360,
    "high": 180,
    "medium": 90,
    "low": 45,
}

_RISK_EVENT_TYPE: dict[str, str] = {
    "missing_high_risk_document": "hr_compliance_risk_alert",
    "document_expired": "hr_compliance_risk_alert",
    "document_expiring_soon": "hr_compliance_risk_reminder",
    "handoff_unaccepted_over_sla": "hr_handoff_sla_alert",
    "onboarding_task_overdue": "hr_onboarding_task_reminder",
    "hr_inactivity": "hr_workforce_inactivity_alert",
}


def risk_alert_fingerprint(risk: dict[str, Any]) -> str:
    """Stable idempotency key for (risk_code × handoff × doc × task)."""
    return ":".join(
        [
            "hr_alert_v1",
            str(risk.get("risk_code") or ""),
            str(risk.get("handoff_id") or "-"),
            str(risk.get("document_type") or "-"),
            str(risk.get("task_id") or "-"),
        ]
    )


def alert_notification_entity_id(*, tenant_id: str, fingerprint: str) -> str:
    """Stable 36-char id for notification dedupe (entity_type + entity_id fallback)."""
    return hashlib.sha256(f"{tenant_id}:{fingerprint}".encode()).hexdigest()[:36]


_ALERT_ENTITY_TYPE = "hr_operational_alert"


def _dedupe_minutes(severity: str) -> int:
    return int(_DEDUPE_MINUTES_BY_SEVERITY.get(str(severity or "").strip().lower(), 90))


async def _exists_recent_dispatch(
    db: AsyncSession,
    *,
    tenant_id: str,
    user_id: str,
    event_type: str,
    entity_type: str,
    entity_id: str,
    window_minutes: int,
) -> bool:
    """Service-level idempotency (not limited to the last 50 rows)."""
    since = datetime.now(timezone.utc) - timedelta(minutes=max(1, int(window_minutes)))
    row = await db.execute(
        select(func.count())
        .select_from(UserNotification)
        .where(
            UserNotification.tenant_id == str(tenant_id).strip(),
            UserNotification.user_id == str(user_id).strip(),
            UserNotification.event_type == str(event_type).strip(),
            UserNotification.entity_type == str(entity_type).strip(),
            UserNotification.entity_id == str(entity_id).strip(),
            UserNotification.created_at >= since,
        )
    )
    return int(row.scalar_one() or 0) > 0


async def _user_ids_for_roles(
    db: AsyncSession,
    *,
    tenant_id: str,
    roles: Iterable[UserRole],
) -> list[str]:
    role_vals = [r.value for r in roles]
    rows = await db.execute(
        select(User.id).where(
            User.tenant_id == str(tenant_id).strip(),
            User.role.in_(role_vals),
            User.is_active.is_(True),
        )
    )
    return [str(x) for x in rows.scalars().all() if x]


async def _user_ids_for_preset_lane(
    db: AsyncSession,
    *,
    tenant_id: str,
    preset: str,
) -> list[str]:
    """Employees (and admins) whose preferences.preset_id or legacy role matches lane."""
    from backend.app.auth.trust_roles import is_hr_workspace_actor, is_team_lead_org_actor

    rows = await db.execute(
        select(User).where(
            User.tenant_id == str(tenant_id).strip(),
            User.role.in_(
                (
                    UserRole.employee.value,
                    UserRole.administrator.value,
                    UserRole.superadmin.value,
                )
            ),
            User.is_active.is_(True),
        )
    )
    out: list[str] = []
    for user in rows.scalars().all():
        role = str(getattr(user.role, "value", user.role) or "")
        prefs = user.preferences if isinstance(user.preferences, dict) else {}
        if preset == "hr" and is_hr_workspace_actor(role, preferences=prefs):
            out.append(str(user.id))
        elif preset == "team_lead" and is_team_lead_org_actor(role, preferences=prefs):
            out.append(str(user.id))
    return out


def _unique_user_ids(*parts: Iterable[str | None]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for group in parts:
        for raw in group:
            uid = str(raw or "").strip()
            if not uid or uid in seen:
                continue
            seen.add(uid)
            out.append(uid)
    return out


async def resolve_alert_recipients(
    db: AsyncSession,
    *,
    tenant_id: str,
    risk: dict[str, Any],
) -> list[str]:
    """Who should receive an in-app alert for this risk row (v1 heuristics)."""
    tid = str(tenant_id).strip()
    code = str(risk.get("risk_code") or "")
    sev = str(risk.get("severity") or "low").strip().lower()
    assignee = risk.get("assignee_user_id")
    assignee_s = str(assignee).strip() if assignee else None

    hr_ids = await _user_ids_for_preset_lane(db, tenant_id=tid, preset="hr")
    sup_ids = await _user_ids_for_preset_lane(db, tenant_id=tid, preset="team_lead")
    if not sup_ids:
        # Fall back to administrators when no team_lead preset is present.
        sup_ids = await _user_ids_for_roles(
            db, tenant_id=tid, roles=(UserRole.administrator,)
        )

    if code in ("missing_high_risk_document", "document_expired"):
        return _unique_user_ids(hr_ids, sup_ids, [assignee_s])

    if code == "document_expiring_soon":
        base = _unique_user_ids([assignee_s])
        if sev in ("high", "critical"):
            return _unique_user_ids(base, hr_ids)
        return base if base else list(hr_ids)

    if code == "handoff_unaccepted_over_sla":
        if sev in ("critical", "high"):
            return _unique_user_ids(sup_ids, [assignee_s], hr_ids)
        return _unique_user_ids([assignee_s], hr_ids)

    if code == "onboarding_task_overdue":
        if assignee_s:
            return [assignee_s]
        return list(hr_ids)

    if code == "hr_inactivity":
        return _unique_user_ids(hr_ids, sup_ids, [assignee_s])

    return _unique_user_ids(hr_ids)


def build_alert_intents(
    risks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Pure read: one intent row per risk (recipients resolved later)."""
    out: list[dict[str, Any]] = []
    for risk in risks:
        out.append(
            {
                "event_type": _RISK_EVENT_TYPE.get(
                    str(risk.get("risk_code") or ""), "hr_operational_risk_alert"
                ),
                "fingerprint": risk_alert_fingerprint(risk),
                "dedupe_window_minutes": _dedupe_minutes(str(risk.get("severity") or "medium")),
                "risk": risk,
            }
        )
    return out


async def dispatch_hr_operational_alerts(
    db: AsyncSession,
    *,
    tenant_id: str,
    viewer_id: str,
    viewer_role: str,
    assignee_scope: str = "team",
    horizon_days: int = 90,
    dry_run: bool = False,
    actor_id: str | None = None,
    preset_id: str | None = None,
) -> dict[str, Any]:
    """Evaluate HR operational risks and optionally emit throttled notifications + audit trail."""
    tid = str(tenant_id).strip()
    risks = await list_operational_risk_items(
        db,
        tenant_id=tid,
        viewer_id=viewer_id,
        viewer_role=viewer_role,
        assignee_scope=assignee_scope,
        horizon_days=horizon_days,
        handoff_id=None,
        candidate_id=None,
        preset_id=preset_id,
    )

    examined = len(risks)
    notification_attempts = 0
    notifications_returned = 0
    would_notify_slots = 0

    if dry_run:
        for risk in risks:
            would_notify_slots += len(await resolve_alert_recipients(db, tenant_id=tid, risk=risk))
        await log_activity(
            db,
            tenant_id=tid,
            action="hr_operational_alert_dry_run",
            actor_id=actor_id,
            target_type="tenant",
            target_id=tid[:36],
            payload={
                "risk_items_examined": examined,
                "would_notify_slots": would_notify_slots,
            },
        )
        await db.flush()
        return {
            "dry_run": True,
            "risk_items_examined": examined,
            "notification_attempts": 0,
            "notifications_returned": 0,
            "would_notify_slots": would_notify_slots,
            "audit_rows_written": 1,
        }

    audit_rows = 0
    suppressed_pre_check = 0
    for risk in risks:
        fp = risk_alert_fingerprint(risk)
        event_type = _RISK_EVENT_TYPE.get(str(risk.get("risk_code") or ""), "hr_operational_risk_alert")
        recipients = await resolve_alert_recipients(db, tenant_id=tid, risk=risk)
        dedupe_min = _dedupe_minutes(str(risk.get("severity") or "medium"))
        title = str(risk.get("reason") or "HR operational alert")[:512]
        body = str(risk.get("recommended_action") or "").strip() or title

        payload_base: dict[str, Any] = {
            "title": title,
            "body": body,
            "risk_code": risk.get("risk_code"),
            "severity": risk.get("severity"),
            "handoff_id": risk.get("handoff_id"),
            "document_type": risk.get("document_type"),
            "task_id": risk.get("task_id"),
            "dedupe_key": fp,
            "source": "hr_operational_alerts",
            "requires_action": True,
        }

        hid = str(risk.get("handoff_id") or "").strip()
        eid = alert_notification_entity_id(tenant_id=tid, fingerprint=fp)

        for user_id in recipients:
            notification_attempts += 1
            if await _exists_recent_dispatch(
                db,
                tenant_id=tid,
                user_id=user_id,
                event_type=event_type,
                entity_type=_ALERT_ENTITY_TYPE,
                entity_id=eid,
                window_minutes=dedupe_min,
            ):
                suppressed_pre_check += 1
                await log_activity(
                    db,
                    tenant_id=tid,
                    action="hr_operational_alert_suppressed",
                    actor_id=actor_id,
                    target_type="user",
                    target_id=str(user_id)[:36],
                    payload={
                        "fingerprint": fp,
                        "event_type": event_type,
                        "user_id": user_id,
                        "reason": "recent_dispatch_exists",
                    },
                )
                audit_rows += 1
                continue

            notif = await create_notification(
                db,
                tenant_id=tid,
                user_id=user_id,
                event_type=event_type,
                payload={
                    **payload_base,
                    "handoff_id": hid or None,
                    "risk": {
                        "risk_code": risk.get("risk_code"),
                        "severity": risk.get("severity"),
                        "handoff_id": risk.get("handoff_id"),
                        "reason": risk.get("reason"),
                    },
                },
                entity_type=_ALERT_ENTITY_TYPE,
                entity_id=eid,
                channel="in_app",
                dedupe_window_minutes=dedupe_min,
                priority=str(risk.get("severity") or "medium"),
            )
            await db.flush()
            if notif is not None:
                notifications_returned += 1

            await log_activity(
                db,
                tenant_id=tid,
                action="hr_operational_alert_dispatch",
                actor_id=actor_id,
                target_type="user",
                target_id=str(user_id)[:36],
                payload={
                    "fingerprint": fp,
                    "event_type": event_type,
                    "user_id": user_id,
                    "notification_id": str(notif.id) if notif is not None else None,
                },
            )
            audit_rows += 1

    return {
        "dry_run": False,
        "risk_items_examined": examined,
        "notification_attempts": notification_attempts,
        "notifications_returned": notifications_returned,
        "suppressed_pre_check": suppressed_pre_check,
        "would_notify_slots": would_notify_slots,
        "audit_rows_written": audit_rows,
    }
