"""C0.2 — inbound resolver merge-gate contracts."""

from __future__ import annotations

import ast
import uuid
from pathlib import Path

import pytest
from sqlalchemy import func, select

from backend.app.communications.entity_link import get_thread_entity_links
from backend.app.communications.inbound_dto import NormalizedInboundMessage
from backend.app.communications.inbound_ingest import (
    ingest_inbound_message,
    mark_inbound_unresolved_resolved,
)
from backend.app.communications.inbound_normalize import (
    extract_reply_message_ids,
    normalize_email_fields,
    normalize_message_id,
)
from backend.app.communications.intent import CommunicationIntent
from backend.app.communications.send_communication import (
    CommunicationOrigin,
    CommunicationRecipient,
    SendCommunicationContent,
    SendCommunicationRequest,
    send_communication,
)
from backend.app.models.candidate import Candidate
from backend.app.models.communication import CommunicationMessage, CommunicationThread
from backend.app.models.communication_inbound_unresolved import (
    REASON_AMBIGUOUS_ENTITY_CONTACT,
    REASON_CORRUPT_PAYLOAD,
    UNRESOLVED_STATUS_RESOLVED,
    CommunicationInboundUnresolved,
)
from backend.app.models.own_company import OwnCompany

REPO = Path(__file__).resolve().parents[3]
INGEST_ROUTE = (
    REPO
    / "backend"
    / "app"
    / "api"
    / "v1"
    / "communications"
    / "routes"
    / "ingest.py"
)


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


async def _send_outbound(db, *, tenant_id: str, entity_type: str, entity_id: str, to: str):
    oc = await _own_company_id(db, tenant_id)
    return await send_communication(
        db,
        SendCommunicationRequest(
            tenant_id=tenant_id,
            origin=CommunicationOrigin(entity_type=entity_type, entity_id=entity_id),
            recipients=[CommunicationRecipient(address=to)],
            channel="email",
            intent=CommunicationIntent.MANUAL_OUTBOUND,
            content=SendCommunicationContent(
                subject="HostFlow outbound",
                body_text="Please reply",
            ),
            actor_id=None,
            own_company_id=oc,
            purpose="test_outbound",
        ),
        skip_transport=True,
    )


def test_normalize_message_id_and_reply_headers() -> None:
    assert normalize_message_id("ABC@host.com") == "<abc@host.com>"
    assert normalize_message_id("<XyZ@Host.COM>") == "<xyz@host.com>"
    assert normalize_message_id("  <a@b.com>  ") == "<a@b.com>"
    ids = extract_reply_message_ids(
        {
            "In-Reply-To": "<a@x.com>",
            "References": "<b@x.com> <a@x.com>",
            "in-reply-to": "<a@x.com>",  # duplicate header casing
        }
    )
    assert ids == ["<a@x.com>", "<b@x.com>"]


def test_ingest_routes_have_no_legacy_thread_bypass() -> None:
    tree = ast.parse(INGEST_ROUTE.read_text(encoding="utf-8"))
    banned = {
        "_find_thread_for_inbound_email",
        "_find_thread_for_inbound_channel",
    }
    called: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in banned:
                called.add(node.func.id)
            if isinstance(node.func, ast.Attribute) and node.func.attr in banned:
                called.add(node.func.attr)
    assert not called, f"legacy bypass still called: {called}"
    text = INGEST_ROUTE.read_text(encoding="utf-8")
    assert "ingest_inbound_message" in text


@pytest.mark.asyncio
async def test_reply_joins_same_thread_and_entity(db, tenant_id: str) -> None:
    entity_id = str(uuid.uuid4())
    to_addr = "candidate@example.test"
    outbound = await _send_outbound(
        db,
        tenant_id=tenant_id,
        entity_type="candidate",
        entity_id=entity_id,
        to=to_addr,
    )
    out_msg = await db.get(CommunicationMessage, outbound.message_id)
    assert out_msg is not None
    assert out_msg.external_message_ref
    # Reply uses bare Message-ID (no brackets) — must still join.
    bare = out_msg.external_message_ref.strip("<>")
    inbound = normalize_email_fields(
        tenant_id=tenant_id,
        provider="imap",
        external_message_ref=f"<reply-{uuid.uuid4().hex}@client.test>",
        subject="Re: HostFlow outbound",
        from_address=to_addr,
        to_address="inbox@hostflow.test",
        text="Thanks",
        headers={"In-Reply-To": bare, "References": f"<{bare}>"},
    )
    result = await ingest_inbound_message(
        db,
        inbound=inbound,
        own_company_id=await _own_company_id(db, tenant_id),
    )
    assert result.thread_id == outbound.thread_id
    assert result.resolution.reason == "reply_headers"
    assert result.resolution.entity_id == entity_id
    assert result.unresolved_id is None
    links = await get_thread_entity_links(
        db, tenant_id=tenant_id, thread_id=result.thread_id
    )
    assert any(lnk.entity_type == "candidate" and lnk.entity_id == entity_id for lnk in links)


@pytest.mark.asyncio
async def test_unknown_inbound_goes_to_unresolved_queue(db, tenant_id: str) -> None:
    inbound = normalize_email_fields(
        tenant_id=tenant_id,
        provider="imap",
        external_message_ref=f"<unknown-{uuid.uuid4().hex}@stranger.test>",
        subject="Cold email",
        from_address=f"stranger-{uuid.uuid4().hex[:8]}@nowhere.test",
        to_address="inbox@hostflow.test",
        text="Who are you?",
        headers={},
    )
    result = await ingest_inbound_message(
        db,
        inbound=inbound,
        own_company_id=await _own_company_id(db, tenant_id),
    )
    assert result.message_id
    assert result.resolution.reason == "unresolved"
    assert result.unresolved_id
    row = await db.get(CommunicationInboundUnresolved, result.unresolved_id)
    assert row is not None
    assert str(row.message_id) == result.message_id
    msg = await db.get(CommunicationMessage, result.message_id)
    assert msg is not None


@pytest.mark.asyncio
async def test_provider_message_id_idempotent(db, tenant_id: str) -> None:
    ext = f"<idem-{uuid.uuid4().hex}@provider.test>"
    inbound = normalize_email_fields(
        tenant_id=tenant_id,
        external_message_ref=ext,
        subject="Once",
        from_address="once@example.test",
        to_address="inbox@hostflow.test",
        text="body",
    )
    first = await ingest_inbound_message(
        db,
        inbound=inbound,
        own_company_id=await _own_company_id(db, tenant_id),
    )
    second = await ingest_inbound_message(
        db,
        inbound=inbound,
        own_company_id=await _own_company_id(db, tenant_id),
    )
    assert first.message_id == second.message_id
    assert second.duplicate_message is True
    count = await db.scalar(
        select(func.count())
        .select_from(CommunicationMessage)
        .where(
            CommunicationMessage.tenant_id == tenant_id,
            CommunicationMessage.external_message_ref == normalize_message_id(ext),
        )
    )
    assert int(count or 0) == 1


@pytest.mark.asyncio
async def test_idempotency_scoped_by_channel_account(db, tenant_id: str) -> None:
    ext = f"<acct-{uuid.uuid4().hex}@provider.test>"
    oc = await _own_company_id(db, tenant_id)
    a = normalize_email_fields(
        tenant_id=tenant_id,
        channel_account_id="account-aaa",
        external_message_ref=ext,
        from_address="x@example.test",
        to_address="inbox@hostflow.test",
        text="a",
    )
    b = normalize_email_fields(
        tenant_id=tenant_id,
        channel_account_id="account-bbb",
        external_message_ref=ext,
        from_address="x@example.test",
        to_address="inbox@hostflow.test",
        text="b",
    )
    ra = await ingest_inbound_message(db, inbound=a, own_company_id=oc)
    rb = await ingest_inbound_message(db, inbound=b, own_company_id=oc)
    assert ra.message_id != rb.message_id
    assert ra.duplicate_message is False
    assert rb.duplicate_message is False


@pytest.mark.asyncio
async def test_ambiguous_entity_contact_goes_unresolved(db, tenant_id: str) -> None:
    email = f"dup-{uuid.uuid4().hex[:8]}@example.test"
    for _ in range(2):
        db.add(
            Candidate(
                id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                first_name="Dup",
                last_name="Cand",
                email=email,
            )
        )
    await db.flush()

    inbound = normalize_email_fields(
        tenant_id=tenant_id,
        external_message_ref=f"<ambig-{uuid.uuid4().hex}@example.test>",
        from_address=email,
        to_address="inbox@hostflow.test",
        text="hello",
    )
    result = await ingest_inbound_message(
        db,
        inbound=inbound,
        own_company_id=await _own_company_id(db, tenant_id),
    )
    assert result.resolution.reason == "unresolved"
    assert result.resolution.details.get("reason_code") == REASON_AMBIGUOUS_ENTITY_CONTACT
    assert result.unresolved_id
    assert len(result.resolution.details.get("matches") or []) >= 2
    row = await db.get(CommunicationInboundUnresolved, result.unresolved_id)
    assert row is not None
    assert row.resolution_reason == REASON_AMBIGUOUS_ENTITY_CONTACT


@pytest.mark.asyncio
async def test_manual_resolution_keeps_audit(db, tenant_id: str) -> None:
    inbound = normalize_email_fields(
        tenant_id=tenant_id,
        external_message_ref=f"<manual-{uuid.uuid4().hex}@x.test>",
        from_address=f"orphan-{uuid.uuid4().hex[:6]}@x.test",
        to_address="inbox@hostflow.test",
        text="orphan",
    )
    result = await ingest_inbound_message(
        db,
        inbound=inbound,
        own_company_id=await _own_company_id(db, tenant_id),
    )
    assert result.unresolved_id
    entity_id = str(uuid.uuid4())
    actor = str(uuid.uuid4())
    row = await mark_inbound_unresolved_resolved(
        db,
        tenant_id=tenant_id,
        unresolved_id=result.unresolved_id,
        actor_user_id=actor,
        entity_type="candidate",
        entity_id=entity_id,
        thread_id=result.thread_id,
    )
    assert row.status == UNRESOLVED_STATUS_RESOLVED
    assert row.resolved_by_user_id == actor
    assert row.resolved_at is not None
    assert row.resolved_entity_type == "candidate"
    assert row.resolved_entity_id == entity_id
    assert row.resolved_thread_id == result.thread_id
    links = await get_thread_entity_links(
        db, tenant_id=tenant_id, thread_id=result.thread_id
    )
    assert any(lnk.entity_type == "candidate" and lnk.entity_id == entity_id for lnk in links)


@pytest.mark.asyncio
async def test_corrupt_payload_force_unresolved(db, tenant_id: str) -> None:
    inbound = NormalizedInboundMessage(
        tenant_id=tenant_id,
        channel="email",
        external_message_ref=f"<corrupt-{uuid.uuid4().hex}@x.test>",
        sender_address="broken@x.test",
        body_text="raw",
        payload={"raw": "???"},
        force_unresolved_reason_code=REASON_CORRUPT_PAYLOAD,
    )
    result = await ingest_inbound_message(
        db,
        inbound=inbound,
        own_company_id=await _own_company_id(db, tenant_id),
    )
    assert result.message_id
    assert result.unresolved_id
    assert result.resolution.details.get("reason_code") == REASON_CORRUPT_PAYLOAD
    row = await db.get(CommunicationInboundUnresolved, result.unresolved_id)
    assert row is not None
    assert row.resolution_reason == REASON_CORRUPT_PAYLOAD


@pytest.mark.asyncio
async def test_entity_contact_candidate_writes_g13(db, tenant_id: str) -> None:
    email = f"cand-{uuid.uuid4().hex[:8]}@example.test"
    cand_id = str(uuid.uuid4())
    db.add(
        Candidate(
            id=cand_id,
            tenant_id=tenant_id,
            first_name="Inbound",
            last_name="Cand",
            email=email,
        )
    )
    await db.flush()

    inbound = normalize_email_fields(
        tenant_id=tenant_id,
        external_message_ref=f"<contact-{uuid.uuid4().hex}@example.test>",
        subject="Hi",
        from_address=email,
        to_address="inbox@hostflow.test",
        text="hello",
    )
    result = await ingest_inbound_message(
        db,
        inbound=inbound,
        own_company_id=await _own_company_id(db, tenant_id),
    )
    assert result.resolution.reason == "entity_contact"
    assert result.resolution.entity_id == cand_id
    assert result.entity_link_ids
    # Idempotent G13
    again = await ingest_inbound_message(
        db,
        inbound=normalize_email_fields(
            tenant_id=tenant_id,
            external_message_ref=f"<contact2-{uuid.uuid4().hex}@example.test>",
            from_address=email,
            to_address="inbox@hostflow.test",
            text="again",
        ),
        own_company_id=await _own_company_id(db, tenant_id),
    )
    links = await get_thread_entity_links(
        db, tenant_id=tenant_id, thread_id=again.thread_id
    )
    assert sum(1 for lnk in links if lnk.entity_id == cand_id) == 1


@pytest.mark.asyncio
async def test_provider_thread_ref_reuses_thread(db, tenant_id: str) -> None:
    entity_id = str(uuid.uuid4())
    outbound = await _send_outbound(
        db,
        tenant_id=tenant_id,
        entity_type="lead",
        entity_id=entity_id,
        to="lead@example.test",
    )
    thread = await db.get(CommunicationThread, outbound.thread_id)
    assert thread is not None
    conv = f"conv-{uuid.uuid4().hex}"
    thread.channel_thread_ref = conv
    await db.flush()

    inbound = normalize_email_fields(
        tenant_id=tenant_id,
        provider="gmail",
        provider_thread_ref=conv,
        external_message_ref=f"<pt-{uuid.uuid4().hex}@mail.gmail.com>",
        subject="Re: HostFlow outbound",
        from_address="lead@example.test",
        to_address="inbox@hostflow.test",
        text="reply via provider thread",
    )
    result = await ingest_inbound_message(
        db,
        inbound=inbound,
        own_company_id=await _own_company_id(db, tenant_id),
    )
    assert result.thread_id == outbound.thread_id
    assert result.resolution.reason == "provider_thread"
