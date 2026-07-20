"""C1.2 — SLA event clock + Close/Reopen Commands."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from backend.app.communications.sla_clock import append_sla_event, project_sla_clock
from backend.app.communications.workspace_commands import (
    close_thread,
    pause_sla,
    reopen_thread,
    resume_sla,
    set_next_action,
)
from backend.app.models.communication import CommunicationThread
from backend.app.models.communication_thread_sla_event import (
    SLA_EVENT_START,
    CommunicationThreadSlaEvent,
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
        db.add(OwnCompany(id=oc, tenant_id=tenant_id, name="OC SLA"))
        await db.flush()
    return str(oc)


def test_project_sla_clock_breached_derived():
    now = datetime.now(timezone.utc)
    start = CommunicationThreadSlaEvent(
        id=str(uuid.uuid4()),
        tenant_id="t",
        thread_id="th",
        event_type=SLA_EVENT_START,
        at=now - timedelta(hours=2),
        payload={"target_due_at": (now - timedelta(minutes=5)).isoformat()},
    )
    proj = project_sla_clock([start], now=now)
    assert proj.breached is True
    assert proj.status == "breached"
    assert "breached" not in (start.payload or {})  # never stored as SoT on event


@pytest.mark.asyncio
async def test_pause_resume_close_reopen(db, tenant_id: str, bootstrap: dict):
    oc = await _oc(db, tenant_id)
    me = str(bootstrap["recruiter_id"])
    due = datetime.now(timezone.utc) + timedelta(hours=1)
    thread = CommunicationThread(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        own_company_id=oc,
        channel="email",
        status="open",
        subject="sla",
        unread_count=1,
        sla_due_at=due,
    )
    db.add(thread)
    await db.flush()
    await append_sla_event(
        db,
        tenant_id=tenant_id,
        thread_id=str(thread.id),
        event_type=SLA_EVENT_START,
        actor_user_id=me,
        payload={"target_due_at": due.isoformat()},
    )
    await db.flush()

    paused = await pause_sla(
        db, tenant_id=tenant_id, thread=thread, actor_user_id=me
    )
    assert paused.applied is True
    assert paused.context.work_state["sla"]["paused"] is True
    assert paused.context.work_state["sla"]["status"] == "paused"
    assert thread.sla_due_at is None

    pause_again = await pause_sla(
        db, tenant_id=tenant_id, thread=thread, actor_user_id=me
    )
    assert pause_again.applied is False

    resumed = await resume_sla(
        db, tenant_id=tenant_id, thread=thread, actor_user_id=me
    )
    assert resumed.applied is True
    assert resumed.context.work_state["sla"]["paused"] is False
    assert resumed.context.work_state["sla"]["status"] == "running"

    await set_next_action(
        db,
        tenant_id=tenant_id,
        thread=thread,
        actor_user_id=me,
        action_type="wrap_up",
        source="manual",
    )
    closed = await close_thread(
        db, tenant_id=tenant_id, thread=thread, actor_user_id=me
    )
    assert closed.applied is True
    assert closed.context.work_state["is_archived"] is True
    assert closed.context.identity["thread"]["status"] == "closed"
    assert closed.context.work_state["next_action"] is None
    assert closed.context.work_state["sla"]["status"] == "resolved"
    assert "closed" in closed.context.work_state["active_queues"]

    close_again = await close_thread(
        db, tenant_id=tenant_id, thread=thread, actor_user_id=me
    )
    assert close_again.applied is False

    opened = await reopen_thread(
        db, tenant_id=tenant_id, thread=thread, actor_user_id=me
    )
    assert opened.applied is True
    assert opened.context.work_state["is_archived"] is False
    assert opened.context.identity["thread"]["status"] == "open"
