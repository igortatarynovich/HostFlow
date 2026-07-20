"""C1.2 — ThreadNextAction entity + Commands."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import func, select

from backend.app.communications.workspace_commands import (
    cancel_next_action,
    complete_next_action,
    set_next_action,
)
from backend.app.models.communication import CommunicationThread
from backend.app.models.communication_thread_next_action import (
    NEXT_ACTION_STATUS_ACTIVE,
    NEXT_ACTION_STATUS_CANCELLED,
    NEXT_ACTION_STATUS_COMPLETED,
    CommunicationThreadNextAction,
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
        db.add(OwnCompany(id=oc, tenant_id=tenant_id, name="OC TNA"))
        await db.flush()
    return str(oc)


@pytest.mark.asyncio
async def test_set_complete_cancel_next_action(db, tenant_id: str, bootstrap: dict):
    oc = await _oc(db, tenant_id)
    me = str(bootstrap["recruiter_id"])
    thread = CommunicationThread(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        own_company_id=oc,
        channel="email",
        status="open",
        subject="na",
        unread_count=0,
    )
    db.add(thread)
    await db.flush()

    due = datetime.now(timezone.utc) + timedelta(hours=4)
    first = await set_next_action(
        db,
        tenant_id=tenant_id,
        thread=thread,
        actor_user_id=me,
        action_type="call_back",
        owner_id=me,
        due_at=due,
        source="manual",
    )
    assert first.applied is True
    na = first.context.work_state["next_action"]
    assert na is not None
    assert na["action_type"] == "call_back"
    assert na["status"] == NEXT_ACTION_STATUS_ACTIVE
    assert na["owner_id"] == me
    first_id = na["id"]

    second = await set_next_action(
        db,
        tenant_id=tenant_id,
        thread=thread,
        actor_user_id=me,
        action_type="send_docs",
        owner_id=me,
        source="manual",
    )
    second_id = second.context.work_state["next_action"]["id"]
    assert second.context.work_state["next_action"]["action_type"] == "send_docs"
    assert second_id != first_id

    active_count = await db.scalar(
        select(func.count())
        .select_from(CommunicationThreadNextAction)
        .where(
            CommunicationThreadNextAction.tenant_id == tenant_id,
            CommunicationThreadNextAction.thread_id == str(thread.id),
            CommunicationThreadNextAction.status == NEXT_ACTION_STATUS_ACTIVE,
        )
    )
    assert int(active_count or 0) == 1

    old = await db.get(CommunicationThreadNextAction, first_id)
    assert old is not None
    assert old.status == NEXT_ACTION_STATUS_CANCELLED

    done = await complete_next_action(
        db, tenant_id=tenant_id, thread=thread, actor_user_id=me
    )
    assert done.applied is True
    assert done.context.work_state["next_action"] is None

    completed_row = await db.get(CommunicationThreadNextAction, second_id)
    assert completed_row is not None
    assert completed_row.status == NEXT_ACTION_STATUS_COMPLETED
    assert completed_row.completed_by == me

    again = await complete_next_action(
        db, tenant_id=tenant_id, thread=thread, actor_user_id=me
    )
    assert again.applied is False

    await set_next_action(
        db,
        tenant_id=tenant_id,
        thread=thread,
        actor_user_id=me,
        action_type="follow_up",
        source="manual",
    )
    cancelled = await cancel_next_action(
        db, tenant_id=tenant_id, thread=thread, actor_user_id=me
    )
    assert cancelled.applied is True
    assert cancelled.context.work_state["next_action"] is None

    cancel_again = await cancel_next_action(
        db, tenant_id=tenant_id, thread=thread, actor_user_id=me
    )
    assert cancel_again.applied is False
