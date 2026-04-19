"""Manual thread-escalation cross-domain bridge.

When an Inbox operator manually escalates a thread, the API needs to:

1. resolve the human recipients (specific user, queue, or role);
2. fan out an in-app bell notification (with idempotent dedupe key);
3. create a HostFlow Activity reminder for each recipient (so the
   escalation lands on the assignee's task list, not just the bell);
4. write an audit log entry.

These two helpers do exactly that, importing the
``reminder_tasks`` / ``user_notifications`` services lazily because they
pull a heavy dependency graph that would otherwise slow startup.

Extracted from ``backend/app/api/v1/communications/__init__.py`` as part
of the Phase 1 god-module split (step 5/N).
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any, Dict, List, Optional

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.communication import CommunicationThread
from backend.app.models.reminder import Reminder, ReminderStatus
from backend.app.models.tenant import user_memberships
from backend.app.models.user import User
from backend.app.services.audit import log_activity

from .tenant_settings import _canonical_membership_role_for_escalation
from .utils import _as_dict, _now_utc

__all__ = [
    "_resolve_manual_escalation_recipient_user_ids",
    "_emit_manual_thread_escalation_bridge",
]


async def _resolve_manual_escalation_recipient_user_ids(
    db: AsyncSession,
    *,
    tenant_id: str,
    target: Dict[str, Any],
) -> List[str]:
    """Resolve inbox manual-escalation recipients for Tasks + bell notifications."""
    user_target = str(target.get("user_id") or "").strip()
    if user_target:
        return [user_target]
    queue_target = str(target.get("queue") or "").strip()
    role_target = str(target.get("role") or "").strip()
    roles_to_query: List[str] = []
    if queue_target:
        roles_to_query = ["supervisor", "administrator"]
    elif role_target:
        canon = _canonical_membership_role_for_escalation(role_target)
        if canon:
            roles_to_query = [canon]
    if not roles_to_query:
        return []
    stmt = (
        sa.select(User.id)
        .distinct()
        .join(user_memberships, user_memberships.c.user_id == User.id)
        .where(
            user_memberships.c.tenant_id == tenant_id,
            user_memberships.c.role.in_(roles_to_query),
            User.is_active.is_(True),
            User.deleted_at.is_(None),
        )
        .limit(25)
    )
    rows = (await db.execute(stmt)).scalars().all()
    return [str(r) for r in rows if r]


async def _emit_manual_thread_escalation_bridge(
    db: AsyncSession,
    *,
    tenant_id: str,
    thread: CommunicationThread,
    escalation: Dict[str, Any],
    actor_user_id: Optional[str],
) -> None:
    """Cross-domain bridge: Inbox ops escalation → Activity (reminder) +
    in-app notification + audit."""
    from backend.app.services.reminder_tasks import create_reminder
    from backend.app.services.user_notifications import create_notification

    esc_at = str(escalation.get("escalated_at") or "").strip()
    reason = str(escalation.get("reason") or "").strip()
    target = _as_dict(escalation.get("target"))
    actor = str(actor_user_id or "").strip() or "system"

    await log_activity(
        db,
        tenant_id=tenant_id,
        actor_id=actor if actor != "system" else None,
        action="communications.thread.ops_escalated",
        target_type="communication_thread",
        target_id=str(thread.id),
        payload={
            "thread_id": str(thread.id),
            "channel": thread.channel,
            "reason": reason[:2000],
            "target": target,
            "escalated_at": esc_at,
        },
    )

    recipient_ids = await _resolve_manual_escalation_recipient_user_ids(
        db, tenant_id=tenant_id, target=target
    )
    if not recipient_ids:
        return

    ch = str(thread.channel or "message").strip() or "message"
    subj = str(thread.subject or "").strip()
    preview = (thread.last_message_preview or subj or str(thread.id))[:400]
    title = f"Escalated {ch.upper()} thread"
    if subj:
        title = f"{title}: {subj[:80]}"

    due = _now_utc() + timedelta(hours=4)
    active_statuses = (
        ReminderStatus.new,
        ReminderStatus.pending,
        ReminderStatus.sent,
        ReminderStatus.overdue,
    )

    for uid in recipient_ids:
        dedupe_key = f"ops_escalation:{tenant_id}:{thread.id}:{esc_at}:{uid}"
        await create_notification(
            db,
            tenant_id=tenant_id,
            user_id=uid,
            event_type="communications_thread_escalated",
            entity_type="communication_thread",
            entity_id=str(thread.id),
            payload={
                "type": "communications_thread_escalated",
                "thread_id": str(thread.id),
                "channel": thread.channel,
                "reason": reason[:500],
                "escalation_target": target,
                "title": title,
                "description": preview,
                "severity": "high",
                "requires_action": True,
                "source": "communications.ops_escalation",
                "dedupe_key": dedupe_key,
            },
            dedupe_window_minutes=1440,
        )
        exists_stmt = (
            sa.select(Reminder.id)
            .where(
                Reminder.tenant_id == tenant_id,
                Reminder.entity_type == "communication_thread",
                Reminder.entity_id == str(thread.id),
                Reminder.assignee_id == uid,
                Reminder.type == "communications_thread_escalated",
                Reminder.status.in_(list(active_statuses)),
            )
            .limit(1)
        )
        row = (await db.execute(exists_stmt)).first()
        if row:
            continue
        await create_reminder(
            db,
            tenant_id=tenant_id,
            actor_id=actor,
            payload={
                "title": title,
                "description": f"{reason[:500]}\n\n{preview}".strip(),
                "type": "communications_thread_escalated",
                "entity_type": "communication_thread",
                "entity_id": str(thread.id),
                "due_at": due,
                "assignee_id": uid,
                "priority": "high",
                "channel": "internal",
                "source": "communications.ops_escalation",
                "message": reason[:500],
                "payload": {
                    "thread_id": str(thread.id),
                    "channel": thread.channel,
                    "escalation_target": target,
                    "reason": reason[:2000],
                },
            },
        )
