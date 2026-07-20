"""C1.2 — Workspace Commands: sole Thread mutation path for interactive Workspace.

Aligned with outbound Intent → Policy → Command pattern, but for workplace state
(not send). Each successful command returns a fresh ThreadContext.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.communications.thread_context import ThreadContext, build_thread_context
from backend.app.models.communication import (
    CommunicationCommandAudit,
    CommunicationMessage,
    CommunicationThread,
)
from backend.app.models.communication_thread_next_action import (
    NEXT_ACTION_SOURCE_AUTOMATION,
    NEXT_ACTION_SOURCE_MANUAL,
    NEXT_ACTION_STATUS_ACTIVE,
    NEXT_ACTION_STATUS_CANCELLED,
    NEXT_ACTION_STATUS_COMPLETED,
    CommunicationThreadNextAction,
)

AssignmentReason = Literal[
    "manual",
    "automation",
    "queue_balancing",
    "escalation",
    "workload_balancing",
]

ASSIGNMENT_REASONS: frozenset[str] = frozenset(
    {
        "manual",
        "automation",
        "queue_balancing",
        "escalation",
        "workload_balancing",
    }
)

WorkspaceCommandName = Literal[
    "AssignThread",
    "ReassignThread",
    "UnassignThread",
    "MarkThreadRead",
    "MarkThreadUnread",
    "SetNextAction",
    "CompleteNextAction",
    "CancelNextAction",
]

NEXT_ACTION_SOURCES: frozenset[str] = frozenset(
    {NEXT_ACTION_SOURCE_MANUAL, NEXT_ACTION_SOURCE_AUTOMATION}
)


@dataclass(frozen=True, slots=True)
class WorkspaceCommandResult:
    context: ThreadContext
    command: str
    applied: bool  # False = idempotent no-op
    audit_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "command": self.command,
            "applied": self.applied,
            "audit_id": self.audit_id,
            "context": self.context.to_dict(),
        }


class WorkspaceCommandError(Exception):
    def __init__(self, code: str, message: str, details: dict[str, Any] | None = None):
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(message)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _normalize_reason(reason: str | None) -> str:
    key = str(reason or "manual").strip().lower()
    if key not in ASSIGNMENT_REASONS:
        raise WorkspaceCommandError(
            "invalid_assignment_reason",
            f"Unknown AssignmentReason: {reason}",
            {"allowed": sorted(ASSIGNMENT_REASONS)},
        )
    return key


async def _write_audit(
    db: AsyncSession,
    *,
    tenant_id: str,
    thread: CommunicationThread,
    actor_user_id: str | None,
    command_id: str,
    actions: list[dict[str, Any]],
    payload: dict[str, Any] | None = None,
) -> str:
    audit_id = str(uuid4())
    db.add(
        CommunicationCommandAudit(
            id=audit_id,
            tenant_id=tenant_id,
            thread_id=str(thread.id),
            channel=str(thread.channel or ""),
            command_id=command_id,
            command_label=command_id,
            actor_user_id=actor_user_id,
            action_count=len(actions),
            actions_json=actions,
            payload=dict(payload or {}),
            executed_at=_now(),
        )
    )
    return audit_id


async def _finish(
    db: AsyncSession,
    *,
    tenant_id: str,
    thread: CommunicationThread,
    actor_user_id: str | None,
    command: str,
    applied: bool,
    audit_id: str | None,
) -> WorkspaceCommandResult:
    await db.commit()
    await db.refresh(thread)
    ctx = await build_thread_context(
        db,
        tenant_id=tenant_id,
        thread=thread,
        actor_user_id=actor_user_id,
    )
    return WorkspaceCommandResult(
        context=ctx,
        command=command,
        applied=applied,
        audit_id=audit_id,
    )


async def assign_thread(
    db: AsyncSession,
    *,
    tenant_id: str,
    thread: CommunicationThread,
    actor_user_id: str | None,
    assignee_id: str,
    reason: str | None = "manual",
    command_id: str = "AssignThread",
) -> WorkspaceCommandResult:
    assignee = str(assignee_id or "").strip()
    if not assignee:
        raise WorkspaceCommandError("assignee_required", "assignee_id is required")
    reason_key = _normalize_reason(reason)
    prev = thread.assignee_id
    if prev == assignee:
        return await _finish(
            db,
            tenant_id=tenant_id,
            thread=thread,
            actor_user_id=actor_user_id,
            command=command_id,
            applied=False,
            audit_id=None,
        )
    if command_id == "AssignThread" and prev:
        # Prefer ReassignThread when already assigned — still apply for convenience.
        command_id = "ReassignThread"
    now = _now()
    thread.assignee_id = assignee
    thread.queue_assigned_by = reason_key
    thread.updated_at = now
    audit_id = await _write_audit(
        db,
        tenant_id=tenant_id,
        thread=thread,
        actor_user_id=actor_user_id,
        command_id=command_id,
        actions=[
            {
                "field": "assignee_id",
                "from": prev,
                "to": assignee,
                "reason": reason_key,
            }
        ],
        payload={"assignment_reason": reason_key},
    )
    return await _finish(
        db,
        tenant_id=tenant_id,
        thread=thread,
        actor_user_id=actor_user_id,
        command=command_id,
        applied=True,
        audit_id=audit_id,
    )


async def unassign_thread(
    db: AsyncSession,
    *,
    tenant_id: str,
    thread: CommunicationThread,
    actor_user_id: str | None,
    reason: str | None = "manual",
) -> WorkspaceCommandResult:
    reason_key = _normalize_reason(reason)
    prev = thread.assignee_id
    if prev is None:
        return await _finish(
            db,
            tenant_id=tenant_id,
            thread=thread,
            actor_user_id=actor_user_id,
            command="UnassignThread",
            applied=False,
            audit_id=None,
        )
    now = _now()
    thread.assignee_id = None
    thread.queue_assigned_by = None
    thread.updated_at = now
    audit_id = await _write_audit(
        db,
        tenant_id=tenant_id,
        thread=thread,
        actor_user_id=actor_user_id,
        command_id="UnassignThread",
        actions=[
            {
                "field": "assignee_id",
                "from": prev,
                "to": None,
                "reason": reason_key,
            }
        ],
        payload={"assignment_reason": reason_key},
    )
    return await _finish(
        db,
        tenant_id=tenant_id,
        thread=thread,
        actor_user_id=actor_user_id,
        command="UnassignThread",
        applied=True,
        audit_id=audit_id,
    )


async def mark_thread_read(
    db: AsyncSession,
    *,
    tenant_id: str,
    thread: CommunicationThread,
    actor_user_id: str | None,
) -> WorkspaceCommandResult:
    """Thread-level read SoT: unread_count → 0 (also stamps inbound read_at)."""
    already = int(thread.unread_count or 0) == 0
    now = _now()
    await db.execute(
        sa.update(CommunicationMessage)
        .where(
            CommunicationMessage.tenant_id == tenant_id,
            CommunicationMessage.thread_id == str(thread.id),
            CommunicationMessage.direction == "inbound",
            CommunicationMessage.read_at.is_(None),
        )
        .values(
            read_at=now,
            delivery_status=sa.case(
                (CommunicationMessage.delivery_status == "delivered", "read"),
                else_=CommunicationMessage.delivery_status,
            ),
        )
    )
    if already:
        return await _finish(
            db,
            tenant_id=tenant_id,
            thread=thread,
            actor_user_id=actor_user_id,
            command="MarkThreadRead",
            applied=False,
            audit_id=None,
        )
    prev = int(thread.unread_count or 0)
    thread.unread_count = 0
    thread.updated_at = now
    audit_id = await _write_audit(
        db,
        tenant_id=tenant_id,
        thread=thread,
        actor_user_id=actor_user_id,
        command_id="MarkThreadRead",
        actions=[{"field": "unread_count", "from": prev, "to": 0}],
    )
    return await _finish(
        db,
        tenant_id=tenant_id,
        thread=thread,
        actor_user_id=actor_user_id,
        command="MarkThreadRead",
        applied=True,
        audit_id=audit_id,
    )


async def mark_thread_unread(
    db: AsyncSession,
    *,
    tenant_id: str,
    thread: CommunicationThread,
    actor_user_id: str | None,
) -> WorkspaceCommandResult:
    """Thread-level unread SoT — not a sum of messages."""
    prev = int(thread.unread_count or 0)
    if prev > 0:
        return await _finish(
            db,
            tenant_id=tenant_id,
            thread=thread,
            actor_user_id=actor_user_id,
            command="MarkThreadUnread",
            applied=False,
            audit_id=None,
        )
    now = _now()
    thread.unread_count = 1
    thread.updated_at = now
    audit_id = await _write_audit(
        db,
        tenant_id=tenant_id,
        thread=thread,
        actor_user_id=actor_user_id,
        command_id="MarkThreadUnread",
        actions=[{"field": "unread_count", "from": prev, "to": 1}],
    )
    return await _finish(
        db,
        tenant_id=tenant_id,
        thread=thread,
        actor_user_id=actor_user_id,
        command="MarkThreadUnread",
        applied=True,
        audit_id=audit_id,
    )


async def _get_active_next_action(
    db: AsyncSession, *, tenant_id: str, thread_id: str
) -> CommunicationThreadNextAction | None:
    row = await db.execute(
        sa.select(CommunicationThreadNextAction)
        .where(
            CommunicationThreadNextAction.tenant_id == tenant_id,
            CommunicationThreadNextAction.thread_id == thread_id,
            CommunicationThreadNextAction.status == NEXT_ACTION_STATUS_ACTIVE,
        )
        .limit(1)
    )
    return row.scalar_one_or_none()


async def set_next_action(
    db: AsyncSession,
    *,
    tenant_id: str,
    thread: CommunicationThread,
    actor_user_id: str | None,
    action_type: str,
    owner_id: str | None = None,
    due_at: datetime | None = None,
    source: str | None = NEXT_ACTION_SOURCE_MANUAL,
    note: str | None = None,
) -> WorkspaceCommandResult:
    """Create active ThreadNextAction; supersede any previous active (cancel + new)."""
    atype = str(action_type or "").strip()
    if not atype:
        raise WorkspaceCommandError("action_type_required", "action_type is required")
    src = str(source or NEXT_ACTION_SOURCE_MANUAL).strip().lower()
    if src not in NEXT_ACTION_SOURCES:
        raise WorkspaceCommandError(
            "invalid_next_action_source",
            f"Unknown source: {source}",
            {"allowed": sorted(NEXT_ACTION_SOURCES)},
        )

    now = _now()
    previous = await _get_active_next_action(
        db, tenant_id=tenant_id, thread_id=str(thread.id)
    )
    actions: list[dict[str, Any]] = []
    if previous is not None:
        # Immutable terminal history: cancel previous active, then create new.
        previous.status = NEXT_ACTION_STATUS_CANCELLED
        previous.completed_at = now
        previous.completed_by = actor_user_id
        previous.updated_at = now
        actions.append(
            {
                "field": "next_action",
                "op": "supersede_cancel",
                "from": previous.id,
                "to": None,
            }
        )

    new_id = str(uuid4())
    db.add(
        CommunicationThreadNextAction(
            id=new_id,
            tenant_id=tenant_id,
            thread_id=str(thread.id),
            action_type=atype,
            owner_id=(str(owner_id).strip() if owner_id else None) or None,
            due_at=due_at,
            status=NEXT_ACTION_STATUS_ACTIVE,
            source=src,
            note=note,
            payload={},
        )
    )
    thread.updated_at = now
    actions.append(
        {
            "field": "next_action",
            "op": "set",
            "from": previous.id if previous else None,
            "to": new_id,
            "action_type": atype,
            "source": src,
        }
    )
    audit_id = await _write_audit(
        db,
        tenant_id=tenant_id,
        thread=thread,
        actor_user_id=actor_user_id,
        command_id="SetNextAction",
        actions=actions,
        payload={"next_action_id": new_id, "action_type": atype, "source": src},
    )
    return await _finish(
        db,
        tenant_id=tenant_id,
        thread=thread,
        actor_user_id=actor_user_id,
        command="SetNextAction",
        applied=True,
        audit_id=audit_id,
    )


async def complete_next_action(
    db: AsyncSession,
    *,
    tenant_id: str,
    thread: CommunicationThread,
    actor_user_id: str | None,
    next_action_id: str | None = None,
) -> WorkspaceCommandResult:
    active = await _get_active_next_action(
        db, tenant_id=tenant_id, thread_id=str(thread.id)
    )
    if active is None:
        return await _finish(
            db,
            tenant_id=tenant_id,
            thread=thread,
            actor_user_id=actor_user_id,
            command="CompleteNextAction",
            applied=False,
            audit_id=None,
        )
    if next_action_id and str(next_action_id) != str(active.id):
        raise WorkspaceCommandError(
            "next_action_mismatch",
            "next_action_id is not the active next action",
            {"active_id": str(active.id), "requested_id": str(next_action_id)},
        )
    now = _now()
    active.status = NEXT_ACTION_STATUS_COMPLETED
    active.completed_at = now
    active.completed_by = actor_user_id
    active.updated_at = now
    thread.updated_at = now
    audit_id = await _write_audit(
        db,
        tenant_id=tenant_id,
        thread=thread,
        actor_user_id=actor_user_id,
        command_id="CompleteNextAction",
        actions=[
            {
                "field": "next_action",
                "op": "complete",
                "from": NEXT_ACTION_STATUS_ACTIVE,
                "to": NEXT_ACTION_STATUS_COMPLETED,
                "id": str(active.id),
            }
        ],
        payload={"next_action_id": str(active.id)},
    )
    return await _finish(
        db,
        tenant_id=tenant_id,
        thread=thread,
        actor_user_id=actor_user_id,
        command="CompleteNextAction",
        applied=True,
        audit_id=audit_id,
    )


async def cancel_next_action(
    db: AsyncSession,
    *,
    tenant_id: str,
    thread: CommunicationThread,
    actor_user_id: str | None,
    next_action_id: str | None = None,
) -> WorkspaceCommandResult:
    active = await _get_active_next_action(
        db, tenant_id=tenant_id, thread_id=str(thread.id)
    )
    if active is None:
        return await _finish(
            db,
            tenant_id=tenant_id,
            thread=thread,
            actor_user_id=actor_user_id,
            command="CancelNextAction",
            applied=False,
            audit_id=None,
        )
    if next_action_id and str(next_action_id) != str(active.id):
        raise WorkspaceCommandError(
            "next_action_mismatch",
            "next_action_id is not the active next action",
            {"active_id": str(active.id), "requested_id": str(next_action_id)},
        )
    now = _now()
    active.status = NEXT_ACTION_STATUS_CANCELLED
    active.completed_at = now
    active.completed_by = actor_user_id
    active.updated_at = now
    thread.updated_at = now
    audit_id = await _write_audit(
        db,
        tenant_id=tenant_id,
        thread=thread,
        actor_user_id=actor_user_id,
        command_id="CancelNextAction",
        actions=[
            {
                "field": "next_action",
                "op": "cancel",
                "from": NEXT_ACTION_STATUS_ACTIVE,
                "to": NEXT_ACTION_STATUS_CANCELLED,
                "id": str(active.id),
            }
        ],
        payload={"next_action_id": str(active.id)},
    )
    return await _finish(
        db,
        tenant_id=tenant_id,
        thread=thread,
        actor_user_id=actor_user_id,
        command="CancelNextAction",
        applied=True,
        audit_id=audit_id,
    )


__all__ = [
    "ASSIGNMENT_REASONS",
    "AssignmentReason",
    "WorkspaceCommandError",
    "WorkspaceCommandName",
    "WorkspaceCommandResult",
    "assign_thread",
    "cancel_next_action",
    "complete_next_action",
    "mark_thread_read",
    "mark_thread_unread",
    "set_next_action",
    "unassign_thread",
]
