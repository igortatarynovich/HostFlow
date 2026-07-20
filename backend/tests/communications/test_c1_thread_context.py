"""C1.1 — ThreadContext is a Workspace read model (four blocks), not a domain SoT."""

from __future__ import annotations

import copy
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest
from sqlalchemy import func, select

from backend.app.communications.composer_policy import (
    ComposerPolicyError,
    enforce_manual_outbound_policy,
)
from backend.app.communications.thread_context import (
    CONTEXT_MESSAGE_SCAN_LIMIT,
    CONTEXT_VERSION,
    build_thread_context,
)
from backend.app.models.communication import CommunicationMessage, CommunicationThread
from backend.app.models.own_company import OwnCompany

REQUIRED_TOP_LEVEL = {
    "identity",
    "work_state",
    "capabilities",
    "workspace",
    "source",
    "context_version",
    "generated_at",
}

REQUIRED_IDENTITY = {"thread", "linked_entities", "participants", "origin"}
REQUIRED_WORK = {
    "assignee_id",
    "owner_id",
    "unread_count",
    "is_archived",
    "active_queues",
    "sla_due_at",
    "next_action",
}
REQUIRED_CAPS = {
    "allowed_intents",
    "allowed_channels",
    "bulk_allowed",
    "defaults",
    "policy_denials",
}
REQUIRED_WORKSPACE = {"draft", "delivery_summary", "timeline_cursor", "ui_hints"}

# Composer may only need these from ThreadContext — no follow-up capability/policy/link GETs.
COMPOSER_REQUIRED_FROM_CONTEXT = {
    ("capabilities", "allowed_intents"),
    ("capabilities", "allowed_channels"),
    ("capabilities", "defaults"),
    ("capabilities", "policy_denials"),
    ("workspace", "ui_hints"),
    ("workspace", "draft"),
    ("identity", "linked_entities"),
}


async def _own_company_id(db, tenant_id: str) -> str:
    oc_row = await db.execute(
        select(OwnCompany.id)
        .where(OwnCompany.tenant_id == tenant_id, OwnCompany.is_archived.is_(False))
        .limit(1)
    )
    oc = oc_row.scalar_one_or_none()
    if oc is None:
        oc = str(uuid.uuid4())
        db.add(OwnCompany(id=oc, tenant_id=tenant_id, name="OC C1 ctx"))
        await db.flush()
    return str(oc)


def _thread_state_snapshot(thread: CommunicationThread) -> dict:
    return {
        "assignee_id": thread.assignee_id,
        "owner_id": getattr(thread, "owner_id", None),
        "unread_count": int(thread.unread_count or 0),
        "is_archived": bool(thread.is_archived),
        "status": thread.status,
        "subject": thread.subject,
        "thread_meta": copy.deepcopy(thread.thread_meta)
        if isinstance(thread.thread_meta, dict)
        else thread.thread_meta,
    }


@pytest.mark.asyncio
async def test_build_thread_context_four_blocks(db, tenant_id: str, bootstrap: dict):
    oc = await _own_company_id(db, tenant_id)
    thread = CommunicationThread(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        own_company_id=oc,
        channel="email",
        status="open",
        subject="context contract",
        unread_count=2,
        assignee_id=str(bootstrap["recruiter_id"]),
        last_inbound_at=datetime.now(timezone.utc),
    )
    db.add(thread)
    await db.flush()

    ctx = await build_thread_context(
        db,
        tenant_id=tenant_id,
        thread=thread,
        actor_user_id=str(bootstrap["recruiter_id"]),
    )
    data = ctx.to_dict()
    assert REQUIRED_TOP_LEVEL <= set(data.keys())
    assert data["source"] == "communication.thread_context.v1"
    assert data["context_version"] == CONTEXT_VERSION
    assert data["generated_at"]
    datetime.fromisoformat(data["generated_at"].replace("Z", "+00:00"))
    assert REQUIRED_IDENTITY <= set(data["identity"].keys())
    assert REQUIRED_WORK <= set(data["work_state"].keys())
    assert REQUIRED_CAPS <= set(data["capabilities"].keys())
    assert REQUIRED_WORKSPACE <= set(data["workspace"].keys())
    assert data["identity"]["thread"]["id"] == str(thread.id)
    assert data["work_state"]["unread_count"] == 2
    assert "assigned_to_me" in data["work_state"]["active_queues"]
    assert isinstance(data["capabilities"]["allowed_intents"], list)


@pytest.mark.asyncio
async def test_thread_context_is_read_only(db, tenant_id: str, bootstrap: dict):
    """GET/build ThreadContext must not mutate Thread work state or invent drafts."""
    oc = await _own_company_id(db, tenant_id)
    thread = CommunicationThread(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        own_company_id=oc,
        channel="email",
        status="open",
        subject="read-only",
        unread_count=3,
        assignee_id=None,
        owner_id=None,
        thread_meta={"note": "preserve"},
        last_inbound_at=datetime.now(timezone.utc),
    )
    db.add(thread)
    await db.flush()

    before = _thread_state_snapshot(thread)
    queues_before = (
        await build_thread_context(
            db,
            tenant_id=tenant_id,
            thread=thread,
            actor_user_id=str(bootstrap["recruiter_id"]),
        )
    ).work_state["active_queues"]

    # Second build — still must not write.
    await build_thread_context(
        db,
        tenant_id=tenant_id,
        thread=thread,
        actor_user_id=str(bootstrap["recruiter_id"]),
    )
    await db.refresh(thread)

    after = _thread_state_snapshot(thread)
    assert after == before
    assert "composer_draft" not in (after["thread_meta"] or {})
    assert after["unread_count"] == 3
    assert after["assignee_id"] is None
    assert after["owner_id"] is None

    queues_after = (
        await build_thread_context(
            db,
            tenant_id=tenant_id,
            thread=thread,
            actor_user_id=str(bootstrap["recruiter_id"]),
        )
    ).work_state["active_queues"]
    assert queues_after == queues_before


@pytest.mark.asyncio
async def test_thread_context_scales_with_thread_not_message_history(
    db, tenant_id: str, bootstrap: dict
):
    """Participant scan is bounded; unread/ownership stay Thread-sourced."""
    oc = await _own_company_id(db, tenant_id)
    thread = CommunicationThread(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        own_company_id=oc,
        channel="email",
        status="open",
        subject="scale",
        unread_count=7,
        assignee_id=str(bootstrap["recruiter_id"]),
    )
    db.add(thread)
    await db.flush()

    bulk = []
    for i in range(CONTEXT_MESSAGE_SCAN_LIMIT + 80):
        bulk.append(
            CommunicationMessage(
                id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                thread_id=str(thread.id),
                own_company_id=oc,
                channel="email",
                message_type="email",
                direction="inbound" if i % 2 == 0 else "outbound",
                body_text=f"msg-{i}",
                delivery_status="delivered",
                sender_address=f"s{i}@example.com",
                recipient_address=f"r{i}@example.com",
            )
        )
    db.add_all(bulk)
    await db.flush()

    msg_count = await db.scalar(
        select(func.count())
        .select_from(CommunicationMessage)
        .where(
            CommunicationMessage.tenant_id == tenant_id,
            CommunicationMessage.thread_id == str(thread.id),
        )
    )
    assert int(msg_count or 0) > CONTEXT_MESSAGE_SCAN_LIMIT

    before = _thread_state_snapshot(thread)
    ctx = await build_thread_context(
        db,
        tenant_id=tenant_id,
        thread=thread,
        actor_user_id=str(bootstrap["recruiter_id"]),
    )
    await db.refresh(thread)
    assert _thread_state_snapshot(thread) == before
    assert ctx.work_state["unread_count"] == 7
    assert len(ctx.identity["participants"]) <= 12
    assert (
        ctx.workspace["timeline_cursor"]["message_scan_limit"]
        == CONTEXT_MESSAGE_SCAN_LIMIT
    )


@pytest.mark.asyncio
async def test_context_completeness_for_composer(db, tenant_id: str, bootstrap: dict):
    """One ThreadContext payload contains everything Composer needs to render."""
    oc = await _own_company_id(db, tenant_id)
    thread = CommunicationThread(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        own_company_id=oc,
        channel="email",
        status="open",
        subject="complete",
        unread_count=1,
    )
    db.add(thread)
    await db.flush()

    data = (
        await build_thread_context(
            db,
            tenant_id=tenant_id,
            thread=thread,
            actor_user_id=str(bootstrap["recruiter_id"]),
        )
    ).to_dict()

    for block, key in COMPOSER_REQUIRED_FROM_CONTEXT:
        assert key in data[block], f"missing {block}.{key} for Composer"
    assert isinstance(data["capabilities"]["allowed_intents"], list)
    assert isinstance(data["capabilities"]["allowed_channels"], list)
    assert "intent" in data["capabilities"]["defaults"]
    assert "channel" in data["capabilities"]["defaults"]
    assert "can_compose" in data["workspace"]["ui_hints"]
    assert isinstance(data["identity"]["linked_entities"], list)


def test_composer_context_completeness_no_extra_fetches():
    """Contract: Composer + work-area compose path do not re-fetch platform allow-lists."""
    root = Path(__file__).resolve().parents[3]
    paths = [
        root / "hostflow-frontend/src/components/communications/ThreadComposer.tsx",
        root
        / "hostflow-frontend/src/components/communications/CommunicationsThreadWorkArea.tsx",
    ]
    banned = (
        "getThreadCapabilities",
        "getMessageDeliveryDiagnostics",
        "getThreadEntityLinks",
        "/capabilities",
        "/delivery-diagnostics",
        "entity-links",
        "evaluateIntentPolicy",
        "resolveCapabilities",
    )
    for path in paths:
        text = path.read_text(encoding="utf-8")
        for token in banned:
            assert token not in text, f"{path.name} must not reference {token}"
    composer = paths[0].read_text(encoding="utf-8")
    assert "ThreadContext" in composer
    assert "context.capabilities" in composer or "capabilities" in composer


@pytest.mark.asyncio
async def test_archived_thread_blocks_compose(db, tenant_id: str, bootstrap: dict):
    oc = await _own_company_id(db, tenant_id)
    thread = CommunicationThread(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        own_company_id=oc,
        channel="email",
        status="closed",
        subject="archived",
        is_archived=True,
        unread_count=0,
    )
    db.add(thread)
    await db.flush()

    ctx = await build_thread_context(
        db,
        tenant_id=tenant_id,
        thread=thread,
        actor_user_id=str(bootstrap["recruiter_id"]),
    )
    assert ctx.workspace["ui_hints"]["can_compose"] is False
    assert ctx.workspace["ui_hints"]["compose_blocked_reason"] == "archived"

    with pytest.raises(ComposerPolicyError) as exc:
        await enforce_manual_outbound_policy(
            db,
            tenant_id=tenant_id,
            thread=thread,
            actor_id=str(bootstrap["recruiter_id"]),
            intent_key="manual_outbound",
            channel="email",
        )
    assert exc.value.denial.reason_code == "thread_archived"


def test_composer_does_not_call_legacy_capability_or_diagnostics_apis():
    """Contract: ThreadComposer must not fetch links/capabilities/diagnostics itself."""
    root = Path(__file__).resolve().parents[3]
    composer = (
        root / "hostflow-frontend/src/components/communications/ThreadComposer.tsx"
    ).read_text(encoding="utf-8")
    banned = (
        "getThreadCapabilities",
        "getMessageDeliveryDiagnostics",
        "getThreadEntityLinks",
        "listCommunicationThreads",
        "/capabilities",
        "/delivery-diagnostics",
    )
    for token in banned:
        assert token not in composer, f"Composer must not reference {token}"
    assert "ThreadContext" in composer
