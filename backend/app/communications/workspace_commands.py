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
]


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


__all__ = [
    "ASSIGNMENT_REASONS",
    "AssignmentReason",
    "WorkspaceCommandError",
    "WorkspaceCommandName",
    "WorkspaceCommandResult",
    "assign_thread",
    "mark_thread_read",
    "mark_thread_unread",
    "unassign_thread",
]
