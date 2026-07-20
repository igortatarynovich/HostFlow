"""C1.2 — Workspace Commands mutate Thread and return ThreadContext."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import func, select

from backend.app.communications.workspace_commands import (
    assign_thread,
    mark_thread_read,
    mark_thread_unread,
    unassign_thread,
)
from backend.app.models.communication import (
    CommunicationCommandAudit,
    CommunicationThread,
)
from backend.app.models.own_company import OwnCompany


async def _oc(db, tenant_id: str) -> str:
    row = await db.execute(
        select(OwnCompany.id)
        .where(OwnCompany.tenant_id == tenant_id, OwnCompany.is_archived.is_(False))
        .limit(1)
    )
    oc = row.scalar_one_or_none()
    if oc is None:
        oc = str(uuid.uuid4())
        db.add(OwnCompany(id=oc, tenant_id=tenant_id, name="OC C1.2"))
        await db.flush()
    return str(oc)


async def _audit_count(db, tenant_id: str, thread_id: str, command_id: str) -> int:
    n = await db.scalar(
        select(func.count())
        .select_from(CommunicationCommandAudit)
        .where(
            CommunicationCommandAudit.tenant_id == tenant_id,
            CommunicationCommandAudit.thread_id == thread_id,
            CommunicationCommandAudit.command_id == command_id,
        )
    )
    return int(n or 0)


@pytest.mark.asyncio
async def test_assign_thread_returns_context_and_audits(db, tenant_id: str, bootstrap: dict):
    oc = await _oc(db, tenant_id)
    me = str(bootstrap["recruiter_id"])
    thread = CommunicationThread(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        own_company_id=oc,
        channel="email",
        status="open",
        subject="assign",
        unread_count=1,
        assignee_id=None,
    )
    db.add(thread)
    await db.flush()

    result = await assign_thread(
        db,
        tenant_id=tenant_id,
        thread=thread,
        actor_user_id=me,
        assignee_id=me,
        reason="manual",
    )
    assert result.applied is True
    assert result.audit_id
    ctx = result.context.to_dict()
    assert ctx["work_state"]["assignee_id"] == me
    assert "assigned_to_me" in ctx["work_state"]["active_queues"]
    assert ctx["context_version"]
    assert ctx["generated_at"]
    assert await _audit_count(db, tenant_id, str(thread.id), "AssignThread") == 1

    # Idempotent: same assignee → no new audit
    again = await assign_thread(
        db,
        tenant_id=tenant_id,
        thread=thread,
        actor_user_id=me,
        assignee_id=me,
        reason="manual",
    )
    assert again.applied is False
    assert again.audit_id is None
    assert await _audit_count(db, tenant_id, str(thread.id), "AssignThread") == 1
    assert again.context.work_state["assignee_id"] == me


@pytest.mark.asyncio
async def test_unassign_and_mark_read_unread(db, tenant_id: str, bootstrap: dict):
    oc = await _oc(db, tenant_id)
    me = str(bootstrap["recruiter_id"])
    thread = CommunicationThread(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        own_company_id=oc,
        channel="email",
        status="open",
        subject="read",
        unread_count=3,
        assignee_id=me,
        last_inbound_at=datetime.now(timezone.utc),
    )
    db.add(thread)
    await db.flush()

    read = await mark_thread_read(
        db, tenant_id=tenant_id, thread=thread, actor_user_id=me
    )
    assert read.applied is True
    assert read.context.work_state["unread_count"] == 0
    assert "new_inbound" not in read.context.work_state["active_queues"]

    read_again = await mark_thread_read(
        db, tenant_id=tenant_id, thread=thread, actor_user_id=me
    )
    assert read_again.applied is False

    unread = await mark_thread_unread(
        db, tenant_id=tenant_id, thread=thread, actor_user_id=me
    )
    assert unread.applied is True
    assert unread.context.work_state["unread_count"] == 1
    assert "new_inbound" in unread.context.work_state["active_queues"]

    un = await unassign_thread(
        db, tenant_id=tenant_id, thread=thread, actor_user_id=me, reason="manual"
    )
    assert un.applied is True
    assert un.context.work_state["assignee_id"] is None
    assert "unassigned" in un.context.work_state["active_queues"]


def test_no_queue_mutation_api_in_workspace_commands_route():
    from pathlib import Path

    text = (
        Path(__file__).resolve().parents[2]
        / "app/api/v1/communications/routes/workspace_commands.py"
    ).read_text(encoding="utf-8")
    for banned in ("MoveThreadToQueue", "move_to_queue", "queue_id", "PATCH"):
        assert banned not in text
