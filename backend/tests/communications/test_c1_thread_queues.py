"""C1 — Thread working queues (Thread is the work object)."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from backend.app.communications.thread_queues import (
    QUEUE_ASSIGNED_TO_ME,
    QUEUE_NEW_INBOUND,
    QUEUE_REQUIRES_REPLY,
    QUEUE_UNASSIGNED,
    QUEUE_WAITING_FOR_REPLY,
    THREAD_QUEUES,
    normalize_thread_queue,
    thread_queue_clause,
)
from backend.app.models.communication import CommunicationThread
from backend.app.models.own_company import OwnCompany


def test_queue_keys_normalize():
    assert normalize_thread_queue("Requires_Reply") == QUEUE_REQUIRES_REPLY
    with pytest.raises(ValueError):
        normalize_thread_queue("messages")
    assert THREAD_QUEUES >= {
        QUEUE_REQUIRES_REPLY,
        QUEUE_NEW_INBOUND,
        QUEUE_ASSIGNED_TO_ME,
        QUEUE_UNASSIGNED,
        QUEUE_WAITING_FOR_REPLY,
    }


@pytest.mark.asyncio
async def test_queue_filters_threads_not_messages(db, tenant_id: str, bootstrap: dict):
    oc_row = await db.execute(
        select(OwnCompany.id)
        .where(OwnCompany.tenant_id == tenant_id, OwnCompany.is_archived.is_(False))
        .limit(1)
    )
    oc = oc_row.scalar_one_or_none()
    if oc is None:
        oc = str(uuid.uuid4())
        db.add(OwnCompany(id=oc, tenant_id=tenant_id, name="OC C1"))
        await db.flush()

    now = datetime.now(timezone.utc)
    me = str(bootstrap["recruiter_id"])
    needs_reply = CommunicationThread(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        own_company_id=str(oc),
        channel="email",
        status="open",
        subject="needs reply",
        last_inbound_at=now,
        last_outbound_at=now - timedelta(hours=2),
        unread_count=1,
        assignee_id=me,
    )
    waiting = CommunicationThread(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        own_company_id=str(oc),
        channel="email",
        status="open",
        subject="waiting",
        last_inbound_at=now - timedelta(hours=3),
        last_outbound_at=now,
        unread_count=0,
        assignee_id=None,
    )
    db.add_all([needs_reply, waiting])
    await db.flush()

    q_needs = await db.execute(
        select(CommunicationThread.id).where(
            CommunicationThread.tenant_id == tenant_id,
            thread_queue_clause(
                QUEUE_REQUIRES_REPLY, tenant_id=tenant_id, actor_user_id=me
            ),
        )
    )
    assert str(needs_reply.id) in {str(x) for x in q_needs.scalars().all()}
    assert str(waiting.id) not in {str(x) for x in q_needs.scalars().all()}

    q_wait = await db.execute(
        select(CommunicationThread.id).where(
            CommunicationThread.tenant_id == tenant_id,
            thread_queue_clause(
                QUEUE_WAITING_FOR_REPLY, tenant_id=tenant_id, actor_user_id=me
            ),
        )
    )
    wait_ids = {str(x) for x in q_wait.scalars().all()}
    assert str(waiting.id) in wait_ids
    assert str(needs_reply.id) not in wait_ids

    q_me = await db.execute(
        select(CommunicationThread.id).where(
            CommunicationThread.tenant_id == tenant_id,
            thread_queue_clause(
                QUEUE_ASSIGNED_TO_ME, tenant_id=tenant_id, actor_user_id=me
            ),
        )
    )
    assert str(needs_reply.id) in {str(x) for x in q_me.scalars().all()}

    q_un = await db.execute(
        select(CommunicationThread.id).where(
            CommunicationThread.tenant_id == tenant_id,
            thread_queue_clause(
                QUEUE_UNASSIGNED, tenant_id=tenant_id, actor_user_id=me
            ),
        )
    )
    assert str(waiting.id) in {str(x) for x in q_un.scalars().all()}
