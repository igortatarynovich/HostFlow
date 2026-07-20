"""C0.1 — G13 thread entity links: idempotency, outbound gate, questionnaire binding."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import func, select

from backend.app.communications.entity_link import (
    ThreadEntityLinkError,
    ensure_thread_entity_link,
    get_thread_entity_links,
    require_entity_links_for_outbound,
)
from backend.app.models.communication import CommunicationMessage, CommunicationThread
from backend.app.models.communication_thread_entity_link import CommunicationThreadEntityLink
from backend.app.models.own_company import OwnCompany
from backend.app.models.sales_inquiry import SalesInquiry
from backend.app.modules.leads import crud as leads_crud
from backend.app.modules.sales.communication.questionnaire_pipeline import (
    ensure_sales_questionnaire_pipeline_binding,
)


async def _own_company_id(db, tenant_id: str) -> str:
    row = await db.execute(
        select(OwnCompany.id)
        .where(OwnCompany.tenant_id == tenant_id, OwnCompany.is_archived.is_(False))
        .order_by(OwnCompany.created_at.asc())
        .limit(1)
    )
    own_company_id = row.scalar_one_or_none()
    if own_company_id is None:
        own_company_id = str(uuid.uuid4())
        db.add(OwnCompany(id=own_company_id, tenant_id=tenant_id, name=f"OC {uuid.uuid4().hex[:6]}"))
        await db.flush()
    return str(own_company_id)


@pytest.mark.asyncio
async def test_ensure_thread_entity_link_idempotent(db, tenant_id: str) -> None:
    thread = CommunicationThread(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        channel="email",
        subject="G13 idempotent",
        status="open",
    )
    db.add(thread)
    await db.flush()

    first = await ensure_thread_entity_link(
        db,
        tenant_id=tenant_id,
        thread_id=str(thread.id),
        entity_type="sales_inquiry",
        entity_id="si-1",
        is_immutable=True,
    )
    second = await ensure_thread_entity_link(
        db,
        tenant_id=tenant_id,
        thread_id=str(thread.id),
        entity_type="sales_inquiry",
        entity_id="si-1",
        is_immutable=True,
    )
    assert first.link_id == second.link_id
    count = await db.scalar(
        select(func.count())
        .select_from(CommunicationThreadEntityLink)
        .where(
            CommunicationThreadEntityLink.tenant_id == tenant_id,
            CommunicationThreadEntityLink.thread_id == str(thread.id),
        )
    )
    assert count == 1


@pytest.mark.asyncio
async def test_questionnaire_binder_writes_g13_sales_inquiry_and_lead(db, tenant_id: str) -> None:
    oc = await _own_company_id(db, tenant_id)
    lead = await leads_crud.create_lead(
        db,
        tenant_id=tenant_id,
        own_company_id=oc,
        company_id=None,
        vacancy_id=None,
        payload={},
        normalized={"email": "q@example.com", "company_name": "Q Co"},
        source="meta",
        lead_type="client",
        lead_target_type="client_lead",
    )
    inquiry = SalesInquiry(
        tenant_id=tenant_id,
        lead_id=str(lead.id),
        status="open",
        source="public_intake",
        own_company_id=oc,
    )
    db.add(inquiry)
    await db.flush()
    await db.commit()

    binding = await ensure_sales_questionnaire_pipeline_binding(
        db,
        tenant_id=tenant_id,
        lead=lead,
        locale="pl",
        actor_user_id=None,
    )
    links = await get_thread_entity_links(
        db, tenant_id=tenant_id, thread_id=binding.thread_id
    )
    types = {lnk.entity_type: lnk.entity_id for lnk in links}
    assert types.get("sales_inquiry") == binding.sales_inquiry_id
    assert types.get("lead") == str(lead.id)

    binding2 = await ensure_sales_questionnaire_pipeline_binding(
        db,
        tenant_id=tenant_id,
        lead=lead,
        locale="pl",
        thread_id=binding.thread_id,
    )
    assert binding2.thread_id == binding.thread_id
    count = await db.scalar(
        select(func.count())
        .select_from(CommunicationThreadEntityLink)
        .where(
            CommunicationThreadEntityLink.tenant_id == tenant_id,
            CommunicationThreadEntityLink.thread_id == binding.thread_id,
        )
    )
    assert count == 2


@pytest.mark.asyncio
async def test_outbound_without_origin_still_allowed(db, tenant_id: str) -> None:
    thread = CommunicationThread(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        channel="email",
        subject="Address only",
        status="open",
    )
    db.add(thread)
    await db.flush()
    links = await require_entity_links_for_outbound(db, tenant_id=tenant_id, thread=thread)
    assert links == []


@pytest.mark.asyncio
async def test_outbound_with_known_origin_auto_ensures_g13(db, tenant_id: str) -> None:
    cand_id = str(uuid.uuid4())
    thread = CommunicationThread(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        channel="email",
        subject="Origin known",
        status="open",
        entity_type="candidate",
        entity_id=cand_id,
    )
    db.add(thread)
    await db.flush()
    links = await require_entity_links_for_outbound(db, tenant_id=tenant_id, thread=thread)
    assert len(links) == 1
    assert links[0].entity_type == "candidate"
    assert links[0].entity_id == cand_id


@pytest.mark.asyncio
async def test_ensure_link_error_prevents_message_commit(db, tenant_id: str, monkeypatch) -> None:
    """Link failure before message write leaves no CommunicationMessage row."""
    thread = CommunicationThread(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        channel="email",
        subject="Fail closed",
        status="open",
        entity_type="lead",
        entity_id=str(uuid.uuid4()),
    )
    db.add(thread)
    await db.flush()

    async def _boom(*_a, **_k):
        raise ThreadEntityLinkError(
            "forced link failure",
            details={"reason": "forced"},
        )

    monkeypatch.setattr(
        "backend.app.communications.entity_link.ensure_thread_entity_link",
        _boom,
    )

    with pytest.raises(ThreadEntityLinkError):
        await require_entity_links_for_outbound(db, tenant_id=tenant_id, thread=thread)

    await db.rollback()
    count = await db.scalar(
        select(func.count())
        .select_from(CommunicationMessage)
        .where(CommunicationMessage.thread_id == str(thread.id))
    )
    assert count == 0
    link_count = await db.scalar(
        select(func.count())
        .select_from(CommunicationThreadEntityLink)
        .where(CommunicationThreadEntityLink.thread_id == str(thread.id))
    )
    assert link_count == 0
