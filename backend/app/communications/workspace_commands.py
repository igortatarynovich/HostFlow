"""C1.2 — Workspace Commands: sole Thread mutation path for interactive Workspace.

Aligned with outbound Intent → Policy → Command pattern, but for workplace state
(not send). Each successful command returns a fresh ThreadContext.
"""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterator, Literal
from uuid import uuid4

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.communications.thread_context import ThreadContext, build_thread_context
from backend.app.models.communication import (
    CommunicationCommandAudit,
    CommunicationMessage,
    CommunicationThread,
)
from backend.app.communications.sla_clock import (
    append_sla_event,
    project_thread_sla,
)
from backend.app.models.communication_thread_next_action import (
    NEXT_ACTION_SOURCE_AUTOMATION,
    NEXT_ACTION_SOURCE_MANUAL,
    NEXT_ACTION_STATUS_ACTIVE,
    NEXT_ACTION_STATUS_CANCELLED,
    NEXT_ACTION_STATUS_COMPLETED,
    CommunicationThreadNextAction,
)
from backend.app.models.communication_thread_sla_event import (
    SLA_EVENT_PAUSE,
    SLA_EVENT_RESOLVE,
    SLA_EVENT_RESUME,
    SLA_EVENT_START,
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
    "PauseSLA",
    "ResumeSLA",
    "CloseThread",
    "ReopenThread",
    "SetThreadPriority",
    "SetThreadTags",
    "DeleteThread",
    "RestoreThread",
    "UpdateThreadWorkflow",
    "SetThreadLinks",
]

# Every Workspace-visible Thread field mutation must map to a Command name here.
THREAD_FIELD_COMMAND_COVERAGE: dict[str, tuple[str, ...]] = {
    "assignee_id": ("AssignThread", "ReassignThread", "UnassignThread"),
    "queue_assigned_by": ("AssignThread", "ReassignThread", "UnassignThread"),
    "unread_count": ("MarkThreadRead", "MarkThreadUnread"),
    "is_archived": ("CloseThread", "ReopenThread", "DeleteThread", "RestoreThread"),
    "status": ("CloseThread", "ReopenThread", "DeleteThread", "RestoreThread"),
    "sla_due_at": ("PauseSLA", "ResumeSLA", "CloseThread", "UpdateThreadWorkflow"),
    "priority": ("SetThreadPriority", "UpdateThreadWorkflow"),
    "tags_json": ("SetThreadTags",),
    "thread_meta": ("UpdateThreadWorkflow", "SetThreadLinks"),
    "linked_candidate_id": ("SetThreadLinks",),
    "linked_company_id": ("SetThreadLinks",),
    "work_version": tuple(),  # platform-managed concurrency token
}

_expected_work_version: ContextVar[int | None] = ContextVar(
    "workspace_cmd_expected_work_version", default=None
)


@contextmanager
def expect_work_version(version: int | None) -> Iterator[None]:
    """Optional optimistic concurrency envelope for a Command invocation."""
    token = _expected_work_version.set(version)
    try:
        yield
    finally:
        _expected_work_version.reset(token)


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


def _guard_work_version(thread: CommunicationThread) -> None:
    expected = _expected_work_version.get()
    if expected is None:
        return
    current = int(getattr(thread, "work_version", 1) or 1)
    if int(expected) != current:
        raise WorkspaceCommandError(
            "stale_work_version",
            "Thread was modified; refresh ThreadContext and retry",
            {"expected": int(expected), "current": current},
        )


def _bump_work_version(thread: CommunicationThread) -> None:
    thread.work_version = int(getattr(thread, "work_version", 1) or 1) + 1
    thread.updated_at = _now()


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
    _guard_work_version(thread)
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
    _bump_work_version(thread)
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
    _guard_work_version(thread)
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
    _bump_work_version(thread)
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
    _guard_work_version(thread)
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
    _bump_work_version(thread)
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
    _guard_work_version(thread)
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
    _bump_work_version(thread)
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
    _guard_work_version(thread)
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
    _bump_work_version(thread)
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
    _guard_work_version(thread)
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
    _bump_work_version(thread)
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
    _guard_work_version(thread)
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
    _bump_work_version(thread)
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


async def pause_sla(
    db: AsyncSession,
    *,
    tenant_id: str,
    thread: CommunicationThread,
    actor_user_id: str | None,
) -> WorkspaceCommandResult:
    _guard_work_version(thread)
    clock = await project_thread_sla(db, tenant_id=tenant_id, thread=thread)
    if clock.status == "none" and thread.sla_due_at is not None:
        # Bootstrap start from legacy column so Pause has a clock to freeze.
        await append_sla_event(
            db,
            tenant_id=tenant_id,
            thread_id=str(thread.id),
            event_type=SLA_EVENT_START,
            actor_user_id=actor_user_id,
            payload={"target_due_at": thread.sla_due_at.isoformat(), "source": "legacy_due"},
        )
        clock = await project_thread_sla(db, tenant_id=tenant_id, thread=thread)
    if clock.paused or clock.status in {"none", "resolved"}:
        return await _finish(
            db,
            tenant_id=tenant_id,
            thread=thread,
            actor_user_id=actor_user_id,
            command="PauseSLA",
            applied=False,
            audit_id=None,
        )
    now = _now()
    frozen_due = clock.target_due_at or (
        thread.sla_due_at.isoformat() if thread.sla_due_at else None
    )
    await append_sla_event(
        db,
        tenant_id=tenant_id,
        thread_id=str(thread.id),
        event_type=SLA_EVENT_PAUSE,
        actor_user_id=actor_user_id,
        at=now,
        payload={"frozen_target_due_at": frozen_due},
    )
    # Keep scheduler quiet while paused (projection still knows frozen due).
    thread.sla_due_at = None
    _bump_work_version(thread)
    audit_id = await _write_audit(
        db,
        tenant_id=tenant_id,
        thread=thread,
        actor_user_id=actor_user_id,
        command_id="PauseSLA",
        actions=[{"field": "sla", "op": "pause", "frozen_target_due_at": frozen_due}],
    )
    return await _finish(
        db,
        tenant_id=tenant_id,
        thread=thread,
        actor_user_id=actor_user_id,
        command="PauseSLA",
        applied=True,
        audit_id=audit_id,
    )


async def resume_sla(
    db: AsyncSession,
    *,
    tenant_id: str,
    thread: CommunicationThread,
    actor_user_id: str | None,
    target_due_at: datetime | None = None,
) -> WorkspaceCommandResult:
    _guard_work_version(thread)
    from backend.app.communications.sla_clock import list_sla_events

    clock = await project_thread_sla(db, tenant_id=tenant_id, thread=thread)
    if not clock.paused:
        return await _finish(
            db,
            tenant_id=tenant_id,
            thread=thread,
            actor_user_id=actor_user_id,
            command="ResumeSLA",
            applied=False,
            audit_id=None,
        )
    now = _now()
    due = target_due_at
    if due is None:
        evs = await list_sla_events(db, tenant_id=tenant_id, thread_id=str(thread.id))
        frozen = None
        for ev in reversed(evs):
            if str(ev.event_type) == SLA_EVENT_PAUSE:
                frozen = (ev.payload or {}).get("frozen_target_due_at")
                break
        if frozen:
            try:
                due = datetime.fromisoformat(str(frozen).replace("Z", "+00:00"))
            except Exception:
                due = None
        elif clock.target_due_at:
            try:
                due = datetime.fromisoformat(clock.target_due_at.replace("Z", "+00:00"))
            except Exception:
                due = None

    await append_sla_event(
        db,
        tenant_id=tenant_id,
        thread_id=str(thread.id),
        event_type=SLA_EVENT_RESUME,
        actor_user_id=actor_user_id,
        at=now,
        payload={"target_due_at": due.isoformat() if due else None},
    )
    thread.sla_due_at = due
    _bump_work_version(thread)
    audit_id = await _write_audit(
        db,
        tenant_id=tenant_id,
        thread=thread,
        actor_user_id=actor_user_id,
        command_id="ResumeSLA",
        actions=[
            {
                "field": "sla",
                "op": "resume",
                "target_due_at": due.isoformat() if due else None,
            }
        ],
    )
    return await _finish(
        db,
        tenant_id=tenant_id,
        thread=thread,
        actor_user_id=actor_user_id,
        command="ResumeSLA",
        applied=True,
        audit_id=audit_id,
    )


async def close_thread(
    db: AsyncSession,
    *,
    tenant_id: str,
    thread: CommunicationThread,
    actor_user_id: str | None,
    cancel_active_next_action: bool = True,
) -> WorkspaceCommandResult:
    _guard_work_version(thread)
    already = bool(thread.is_archived) or str(thread.status or "").lower() in {
        "closed",
        "archived",
        "resolved",
        "done",
    }
    if already:
        return await _finish(
            db,
            tenant_id=tenant_id,
            thread=thread,
            actor_user_id=actor_user_id,
            command="CloseThread",
            applied=False,
            audit_id=None,
        )
    now = _now()
    actions: list[dict[str, Any]] = []
    if cancel_active_next_action:
        active = await _get_active_next_action(
            db, tenant_id=tenant_id, thread_id=str(thread.id)
        )
        if active is not None:
            active.status = NEXT_ACTION_STATUS_CANCELLED
            active.completed_at = now
            active.completed_by = actor_user_id
            active.updated_at = now
            actions.append(
                {
                    "field": "next_action",
                    "op": "cancel_on_close",
                    "id": str(active.id),
                }
            )
    clock = await project_thread_sla(db, tenant_id=tenant_id, thread=thread)
    if clock.status not in {"none", "resolved"}:
        await append_sla_event(
            db,
            tenant_id=tenant_id,
            thread_id=str(thread.id),
            event_type=SLA_EVENT_RESOLVE,
            actor_user_id=actor_user_id,
            at=now,
            payload={"reason": "thread_closed"},
        )
        actions.append({"field": "sla", "op": "resolve_on_close"})
    prev_status = thread.status
    thread.is_archived = True
    thread.status = "closed"
    thread.sla_due_at = None
    _bump_work_version(thread)
    actions.append(
        {
            "field": "status",
            "from": prev_status,
            "to": "closed",
            "is_archived": True,
        }
    )
    audit_id = await _write_audit(
        db,
        tenant_id=tenant_id,
        thread=thread,
        actor_user_id=actor_user_id,
        command_id="CloseThread",
        actions=actions,
    )
    return await _finish(
        db,
        tenant_id=tenant_id,
        thread=thread,
        actor_user_id=actor_user_id,
        command="CloseThread",
        applied=True,
        audit_id=audit_id,
    )


async def reopen_thread(
    db: AsyncSession,
    *,
    tenant_id: str,
    thread: CommunicationThread,
    actor_user_id: str | None,
) -> WorkspaceCommandResult:
    _guard_work_version(thread)
    closed = bool(thread.is_archived) or str(thread.status or "").lower() in {
        "closed",
        "archived",
        "resolved",
        "done",
        "deleted",
    }
    if not closed:
        return await _finish(
            db,
            tenant_id=tenant_id,
            thread=thread,
            actor_user_id=actor_user_id,
            command="ReopenThread",
            applied=False,
            audit_id=None,
        )
    now = _now()
    prev_status = thread.status
    thread.is_archived = False
    thread.status = "open"
    _bump_work_version(thread)
    audit_id = await _write_audit(
        db,
        tenant_id=tenant_id,
        thread=thread,
        actor_user_id=actor_user_id,
        command_id="ReopenThread",
        actions=[
            {
                "field": "status",
                "from": prev_status,
                "to": "open",
                "is_archived": False,
            }
        ],
    )
    return await _finish(
        db,
        tenant_id=tenant_id,
        thread=thread,
        actor_user_id=actor_user_id,
        command="ReopenThread",
        applied=True,
        audit_id=audit_id,
    )


async def set_thread_priority(
    db: AsyncSession,
    *,
    tenant_id: str,
    thread: CommunicationThread,
    actor_user_id: str | None,
    priority: str,
) -> WorkspaceCommandResult:
    _guard_work_version(thread)
    key = str(priority or "").strip().lower()
    if key not in {"low", "normal", "high", "urgent"}:
        raise WorkspaceCommandError(
            "invalid_priority",
            f"Unknown priority: {priority}",
            {"allowed": ["low", "normal", "high", "urgent"]},
        )
    prev = str(thread.priority or "normal")
    if prev == key:
        return await _finish(
            db,
            tenant_id=tenant_id,
            thread=thread,
            actor_user_id=actor_user_id,
            command="SetThreadPriority",
            applied=False,
            audit_id=None,
        )
    thread.priority = key
    _bump_work_version(thread)
    audit_id = await _write_audit(
        db,
        tenant_id=tenant_id,
        thread=thread,
        actor_user_id=actor_user_id,
        command_id="SetThreadPriority",
        actions=[{"field": "priority", "from": prev, "to": key}],
    )
    return await _finish(
        db,
        tenant_id=tenant_id,
        thread=thread,
        actor_user_id=actor_user_id,
        command="SetThreadPriority",
        applied=True,
        audit_id=audit_id,
    )


async def set_thread_tags(
    db: AsyncSession,
    *,
    tenant_id: str,
    thread: CommunicationThread,
    actor_user_id: str | None,
    tags: list[Any],
) -> WorkspaceCommandResult:
    _guard_work_version(thread)
    next_tags = [str(x).strip() for x in (tags or []) if str(x).strip()]
    prev = list(thread.tags_json or [])
    if prev == next_tags:
        return await _finish(
            db,
            tenant_id=tenant_id,
            thread=thread,
            actor_user_id=actor_user_id,
            command="SetThreadTags",
            applied=False,
            audit_id=None,
        )
    thread.tags_json = next_tags
    _bump_work_version(thread)
    audit_id = await _write_audit(
        db,
        tenant_id=tenant_id,
        thread=thread,
        actor_user_id=actor_user_id,
        command_id="SetThreadTags",
        actions=[{"field": "tags_json", "from": prev, "to": next_tags}],
    )
    return await _finish(
        db,
        tenant_id=tenant_id,
        thread=thread,
        actor_user_id=actor_user_id,
        command="SetThreadTags",
        applied=True,
        audit_id=audit_id,
    )


async def delete_thread(
    db: AsyncSession,
    *,
    tenant_id: str,
    thread: CommunicationThread,
    actor_user_id: str | None,
) -> WorkspaceCommandResult:
    _guard_work_version(thread)
    if str(thread.status or "").lower() == "deleted":
        return await _finish(
            db,
            tenant_id=tenant_id,
            thread=thread,
            actor_user_id=actor_user_id,
            command="DeleteThread",
            applied=False,
            audit_id=None,
        )
    prev_status = thread.status
    prev_archived = bool(thread.is_archived)
    thread.status = "deleted"
    thread.is_archived = True
    _bump_work_version(thread)
    audit_id = await _write_audit(
        db,
        tenant_id=tenant_id,
        thread=thread,
        actor_user_id=actor_user_id,
        command_id="DeleteThread",
        actions=[
            {
                "field": "status",
                "from": prev_status,
                "to": "deleted",
                "is_archived": {"from": prev_archived, "to": True},
            }
        ],
    )
    return await _finish(
        db,
        tenant_id=tenant_id,
        thread=thread,
        actor_user_id=actor_user_id,
        command="DeleteThread",
        applied=True,
        audit_id=audit_id,
    )


async def restore_thread(
    db: AsyncSession,
    *,
    tenant_id: str,
    thread: CommunicationThread,
    actor_user_id: str | None,
) -> WorkspaceCommandResult:
    _guard_work_version(thread)
    if str(thread.status or "").lower() != "deleted":
        return await _finish(
            db,
            tenant_id=tenant_id,
            thread=thread,
            actor_user_id=actor_user_id,
            command="RestoreThread",
            applied=False,
            audit_id=None,
        )
    prev_status = thread.status
    thread.status = "open"
    thread.is_archived = False
    _bump_work_version(thread)
    audit_id = await _write_audit(
        db,
        tenant_id=tenant_id,
        thread=thread,
        actor_user_id=actor_user_id,
        command_id="RestoreThread",
        actions=[
            {
                "field": "status",
                "from": prev_status,
                "to": "open",
                "is_archived": False,
            }
        ],
    )
    return await _finish(
        db,
        tenant_id=tenant_id,
        thread=thread,
        actor_user_id=actor_user_id,
        command="RestoreThread",
        applied=True,
        audit_id=audit_id,
    )


async def update_thread_workflow(
    db: AsyncSession,
    *,
    tenant_id: str,
    tenant: Any,
    thread: CommunicationThread,
    actor_user_id: str | None,
    thread_meta: dict[str, Any],
) -> WorkspaceCommandResult:
    _guard_work_version(thread)
    from backend.app.communications.workspace_workflow import apply_thread_workflow_meta

    before = dict(thread.thread_meta or {})
    actions = await apply_thread_workflow_meta(
        db,
        tenant_id=tenant_id,
        tenant=tenant,
        thread=thread,
        actor_user_id=actor_user_id,
        meta_patch=dict(thread_meta or {}),
    )
    after = dict(thread.thread_meta or {})
    if before == after and not any(
        a.get("field") == "priority" for a in actions
    ):
        # Side-effects may still change sla_due_at/priority — treat as applied if dirty.
        pass
    _bump_work_version(thread)
    audit_id = await _write_audit(
        db,
        tenant_id=tenant_id,
        thread=thread,
        actor_user_id=actor_user_id,
        command_id="UpdateThreadWorkflow",
        actions=actions,
        payload={"thread_meta_keys": sorted(str(k) for k in (thread_meta or {}).keys())},
    )
    return await _finish(
        db,
        tenant_id=tenant_id,
        thread=thread,
        actor_user_id=actor_user_id,
        command="UpdateThreadWorkflow",
        applied=True,
        audit_id=audit_id,
    )


_UNSET: Any = object()


async def set_thread_links(
    db: AsyncSession,
    *,
    tenant_id: str,
    thread: CommunicationThread,
    actor_user_id: str | None,
    linked_candidate_id: Any = _UNSET,
    linked_company_id: Any = _UNSET,
    thread_meta: dict[str, Any] | None = None,
) -> WorkspaceCommandResult:
    """Set CRM entity links on the Thread (+ optional meta name/uos projection)."""
    _guard_work_version(thread)
    actions: list[dict[str, Any]] = []
    if linked_candidate_id is not _UNSET:
        prev = thread.linked_candidate_id
        nxt = str(linked_candidate_id).strip() if linked_candidate_id else None
        if prev != nxt:
            thread.linked_candidate_id = nxt
            actions.append(
                {"field": "linked_candidate_id", "from": prev, "to": nxt}
            )
    if linked_company_id is not _UNSET:
        prev = thread.linked_company_id
        nxt = str(linked_company_id).strip() if linked_company_id else None
        if prev != nxt:
            thread.linked_company_id = nxt
            actions.append(
                {"field": "linked_company_id", "from": prev, "to": nxt}
            )
    if thread_meta is not None:
        from backend.app.api.v1.communications._helpers.utils import (
            _as_dict,
            _deep_merge_dict,
        )

        before = _as_dict(thread.thread_meta)
        merged = _deep_merge_dict(before, _as_dict(thread_meta))
        if merged != before:
            thread.thread_meta = merged
            actions.append({"field": "thread_meta", "op": "merge_links"})

    from backend.app.communications.entity_link import ensure_links_for_known_thread_origin

    await ensure_links_for_known_thread_origin(db, tenant_id=tenant_id, thread=thread)

    if not actions:
        return await _finish(
            db,
            tenant_id=tenant_id,
            thread=thread,
            actor_user_id=actor_user_id,
            command="SetThreadLinks",
            applied=False,
            audit_id=None,
        )
    _bump_work_version(thread)
    audit_id = await _write_audit(
        db,
        tenant_id=tenant_id,
        thread=thread,
        actor_user_id=actor_user_id,
        command_id="SetThreadLinks",
        actions=actions,
    )
    return await _finish(
        db,
        tenant_id=tenant_id,
        thread=thread,
        actor_user_id=actor_user_id,
        command="SetThreadLinks",
        applied=True,
        audit_id=audit_id,
    )


__all__ = [
    "ASSIGNMENT_REASONS",
    "AssignmentReason",
    "THREAD_FIELD_COMMAND_COVERAGE",
    "WorkspaceCommandError",
    "WorkspaceCommandName",
    "WorkspaceCommandResult",
    "assign_thread",
    "cancel_next_action",
    "close_thread",
    "complete_next_action",
    "delete_thread",
    "expect_work_version",
    "mark_thread_read",
    "mark_thread_unread",
    "pause_sla",
    "reopen_thread",
    "restore_thread",
    "resume_sla",
    "set_next_action",
    "set_thread_links",
    "set_thread_priority",
    "set_thread_tags",
    "unassign_thread",
    "update_thread_workflow",
]
