"""C0.1 DoD — platform SendCommunication for supported origins."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import func, select

from backend.app.communications.entity_link import get_thread_entity_links
from backend.app.communications.intent import CommunicationIntent
from backend.app.communications.send_communication import (
    CommunicationOrigin,
    CommunicationRecipient,
    SendCommunicationContent,
    SendCommunicationError,
    SendCommunicationRequest,
    find_thread_id_for_origin,
    send_communication,
)
from backend.app.models.communication import CommunicationMessage, CommunicationThread
from backend.app.models.communication_thread_entity_link import CommunicationThreadEntityLink
from backend.app.models.own_company import OwnCompany


async def _own_company_id(db, tenant_id: str) -> str:
    row = await db.execute(
        select(OwnCompany.id)
        .where(OwnCompany.tenant_id == tenant_id, OwnCompany.is_archived.is_(False))
        .order_by(OwnCompany.created_at.asc())
        .limit(1)
    )
    oc = row.scalar_one_or_none()
    if oc is None:
        oc = str(uuid.uuid4())
        db.add(OwnCompany(id=oc, tenant_id=tenant_id, name=f"OC {uuid.uuid4().hex[:6]}"))
        await db.flush()
    return str(oc)


async def _send(
    db,
    *,
    tenant_id: str,
    entity_type: str,
    entity_id: str,
    related: list[CommunicationOrigin] | None = None,
    thread_id: str | None = None,
    idempotency_key: str | None = None,
    skip_transport: bool = True,
):
    oc = await _own_company_id(db, tenant_id)
    return await send_communication(
        db,
        SendCommunicationRequest(
            tenant_id=tenant_id,
            origin=CommunicationOrigin(entity_type=entity_type, entity_id=entity_id),
            recipients=[CommunicationRecipient(address=f"{entity_type}@example.test")],
            channel="email",
            intent=CommunicationIntent.MANUAL_OUTBOUND,
            content=SendCommunicationContent(
                subject=f"Hello {entity_type}",
                body_text=f"Body for {entity_type}",
            ),
            actor_id=None,
            own_company_id=oc,
            related_entities=tuple(related or ()),
            thread_id=thread_id,
            idempotency_key=idempotency_key,
            purpose="test_outbound",
        ),
        skip_transport=skip_transport,
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "entity_type",
    ["candidate", "application", "sales_inquiry", "client_account", "lead"],
)
async def test_send_communication_from_supported_origins(
    db, tenant_id: str, entity_type: str
) -> None:
    entity_id = str(uuid.uuid4())
    result = await _send(db, tenant_id=tenant_id, entity_type=entity_type, entity_id=entity_id)
    assert result.message_id
    assert result.thread_id
    assert result.origin_entity_type == entity_type
    assert result.origin_entity_id == entity_id
    links = await get_thread_entity_links(
        db, tenant_id=tenant_id, thread_id=result.thread_id
    )
    assert any(
        lnk.entity_type == entity_type and lnk.entity_id == entity_id for lnk in links
    )
    msg = await db.get(CommunicationMessage, result.message_id)
    assert msg is not None
    assert str(msg.thread_id) == result.thread_id
    assert msg.direction == "outbound"


@pytest.mark.asyncio
async def test_resend_reuses_origin_thread(db, tenant_id: str) -> None:
    entity_id = str(uuid.uuid4())
    first = await _send(
        db, tenant_id=tenant_id, entity_type="candidate", entity_id=entity_id
    )
    second = await _send(
        db, tenant_id=tenant_id, entity_type="candidate", entity_id=entity_id
    )
    assert first.thread_id == second.thread_id
    assert first.message_id != second.message_id
    found = await find_thread_id_for_origin(
        db,
        tenant_id=tenant_id,
        channel="email",
        origin=CommunicationOrigin(entity_type="candidate", entity_id=entity_id),
    )
    assert found == first.thread_id


@pytest.mark.asyncio
async def test_different_origins_same_address_get_different_threads(
    db, tenant_id: str
) -> None:
    """One person ≠ one thread: work context / origin separates threads."""
    cand = str(uuid.uuid4())
    client = str(uuid.uuid4())
    a = await _send(db, tenant_id=tenant_id, entity_type="candidate", entity_id=cand)
    b = await _send(
        db, tenant_id=tenant_id, entity_type="client_account", entity_id=client
    )
    assert a.thread_id != b.thread_id


@pytest.mark.asyncio
async def test_idempotent_replay_returns_same_message(db, tenant_id: str) -> None:
    entity_id = str(uuid.uuid4())
    key = f"idem-{uuid.uuid4().hex}"
    first = await _send(
        db,
        tenant_id=tenant_id,
        entity_type="lead",
        entity_id=entity_id,
        idempotency_key=key,
    )
    second = await _send(
        db,
        tenant_id=tenant_id,
        entity_type="lead",
        entity_id=entity_id,
        idempotency_key=key,
    )
    assert second.idempotent_replay is True
    assert second.message_id == first.message_id
    assert second.thread_id == first.thread_id
    count = await db.scalar(
        select(func.count())
        .select_from(CommunicationMessage)
        .where(CommunicationMessage.thread_id == first.thread_id)
    )
    assert count == 1


@pytest.mark.asyncio
async def test_cannot_send_without_g13_when_ensure_fails(
    db, tenant_id: str, monkeypatch
) -> None:
    entity_id = str(uuid.uuid4())

    async def _boom(*_a, **_k):
        from backend.app.communications.entity_link import ThreadEntityLinkError

        raise ThreadEntityLinkError("forced", details={"reason": "forced"})

    import importlib

    send_comm_mod = importlib.import_module("backend.app.communications.send_communication")
    monkeypatch.setattr(send_comm_mod, "ensure_thread_entity_link", _boom)
    with pytest.raises(SendCommunicationError):
        await _send(
            db,
            tenant_id=tenant_id,
            entity_type="sales_inquiry",
            entity_id=entity_id,
        )
    await db.rollback()
    link_count = await db.scalar(
        select(func.count())
        .select_from(CommunicationThreadEntityLink)
        .where(
            CommunicationThreadEntityLink.tenant_id == tenant_id,
            CommunicationThreadEntityLink.entity_id == entity_id,
        )
    )
    assert link_count == 0
    msg_count = await db.scalar(
        select(func.count())
        .select_from(CommunicationMessage)
        .where(
            CommunicationMessage.tenant_id == tenant_id,
            CommunicationMessage.recipient_id == entity_id,
        )
    )
    assert msg_count == 0


@pytest.mark.asyncio
async def test_lead_facade_and_related_sales_inquiry_links(db, tenant_id: str) -> None:
    lead_id = str(uuid.uuid4())
    si_id = str(uuid.uuid4())
    result = await _send(
        db,
        tenant_id=tenant_id,
        entity_type="lead",
        entity_id=lead_id,
        related=[CommunicationOrigin(entity_type="sales_inquiry", entity_id=si_id)],
    )
    links = await get_thread_entity_links(
        db, tenant_id=tenant_id, thread_id=result.thread_id
    )
    types = {lnk.entity_type: lnk.entity_id for lnk in links}
    assert types.get("lead") == lead_id
    assert types.get("sales_inquiry") == si_id
