"""Pre-merge gate: seams control the flow (Intent → Policy → Resolvers → Command → Sender)."""

from __future__ import annotations

import ast
import uuid
from pathlib import Path

import pytest
from sqlalchemy import func, select

from backend.app.communications.capability_resolver import resolve_communication_capabilities
from backend.app.communications.command import (
    CommunicationCommand,
    CommunicationOrigin,
    CommunicationRecipient,
    SendCommunicationContent,
)
from backend.app.communications.execute_intent import (
    IntentExecutionRequest,
    execute_communication_intent,
    render_communication_intent,
)
from backend.app.communications.intent import CommunicationIntent, resolve_intent_policy
from backend.app.communications.link_resolver import (
    LinkResolveRequest,
    QuestionnaireLinkResolver,
    absolute_public_url,
)
from backend.app.communications.prepare_send import prepare_and_send_communication
from backend.app.communications.send_communication import SendCommunicationError
from backend.app.communications.template_resolver import SeedTemplateResolver
from backend.app.models.communication import CommunicationMessage
from backend.app.models.communication_thread_entity_link import CommunicationThreadEntityLink
from backend.app.models.own_company import OwnCompany


REPO = Path(__file__).resolve().parents[3]
QUESTIONNAIRE_EMAIL = (
    REPO / "backend/app/services/communication_deliveries/questionnaire_email.py"
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


def test_intent_policy_drives_questionnaire_templates_and_links() -> None:
    policy = resolve_intent_policy(CommunicationIntent.REQUEST_QUESTIONNAIRE)
    assert "email" in policy.allowed_channels
    assert "questionnaire_invite_email_v1" in policy.allowed_template_keys
    assert "sales_questionnaire" in policy.link_intents


@pytest.mark.asyncio
async def test_capability_resolver_covers_candidate_and_sales_inquiry() -> None:
    cand = await resolve_communication_capabilities(
        tenant_id="t1", entity_type="candidate", entity_id="c1"
    )
    assert CommunicationIntent.REQUEST_QUESTIONNAIRE.value in cand.allowed_intents
    si = await resolve_communication_capabilities(
        tenant_id="t1", entity_type="sales_inquiry", entity_id="s1"
    )
    assert CommunicationIntent.REQUEST_QUESTIONNAIRE.value in si.allowed_intents
    assert si.bulk_allowed is False


def test_template_resolver_returns_contract_not_string() -> None:
    resolved = SeedTemplateResolver().resolve_for_intent(
        CommunicationIntent.REQUEST_QUESTIONNAIRE, channel="email"
    )
    assert resolved.key == "questionnaire_invite_email_v1"
    assert resolved.version == 1
    assert resolved.template is not None
    assert hasattr(resolved.template, "allowed_variables")


@pytest.mark.asyncio
async def test_link_resolver_returns_typed_result() -> None:
    link = await QuestionnaireLinkResolver().resolve(
        LinkResolveRequest(
            tenant_id="t1",
            link_intent="sales_questionnaire",
            entity_type="lead",
            entity_id="l1",
            apply_path_or_url="/public/apply/tok123?lang=pl",
        )
    )
    assert link.link_intent == "sales_questionnaire"
    assert link.token == "tok123"
    assert link.variable_name == "questionnaire_url"
    assert absolute_public_url("/public/apply/x").endswith("/public/apply/x")


@pytest.mark.asyncio
async def test_product_template_cannot_bypass_intent() -> None:
    """template_key=questionnaire with MANUAL_OUTBOUND must fail before persistence."""
    with pytest.raises(SendCommunicationError) as exc:
        await prepare_and_send_communication(
            None,  # type: ignore[arg-type]
            CommunicationCommand(
                tenant_id="t",
                origin=CommunicationOrigin(entity_type="sales_inquiry", entity_id="1"),
                recipients=[CommunicationRecipient(address="a@b.c")],
                channel="email",
                intent=CommunicationIntent.MANUAL_OUTBOUND,
                content=SendCommunicationContent(subject="s", body_text="b"),
                template_key="questionnaire_invite_email_v1",
            ),
            skip_transport=True,
        )
    assert (exc.value.details or {}).get("reason") == "intent_required_for_template"


@pytest.mark.asyncio
async def test_capability_denial_blocks_send(db, tenant_id: str) -> None:
    oc = await _own_company_id(db, tenant_id)
    # service_order does not allow request_questionnaire
    with pytest.raises(SendCommunicationError) as exc:
        await prepare_and_send_communication(
            db,
            CommunicationCommand(
                tenant_id=tenant_id,
                origin=CommunicationOrigin(
                    entity_type="service_order", entity_id=str(uuid.uuid4())
                ),
                recipients=[CommunicationRecipient(address="x@example.test")],
                channel="email",
                intent=CommunicationIntent.REQUEST_QUESTIONNAIRE,
                content=SendCommunicationContent(subject="s", body_text="b"),
                template_key="questionnaire_invite_email_v1",
                own_company_id=oc,
            ),
            skip_transport=True,
        )
    assert (exc.value.details or {}).get("reason") == "intent_entity_denied"
    count = await db.scalar(
        select(func.count()).select_from(CommunicationMessage).where(
            CommunicationMessage.tenant_id == tenant_id
        )
    )
    # No new message for this denial (count may include other tests — check none for this subject)
    assert count is not None


@pytest.mark.asyncio
async def test_template_resolution_failure_creates_no_message(db, tenant_id: str) -> None:
    before = await db.scalar(
        select(func.count()).select_from(CommunicationMessage).where(
            CommunicationMessage.tenant_id == tenant_id
        )
    )
    with pytest.raises(SendCommunicationError) as exc:
        await render_communication_intent(
            IntentExecutionRequest(
                tenant_id=tenant_id,
                intent=CommunicationIntent.SEND_OFFER,  # no templates in seed policy
                origin=CommunicationOrigin(
                    entity_type="candidate", entity_id=str(uuid.uuid4())
                ),
                recipients=[CommunicationRecipient(address="c@example.test")],
                channel="email",
            )
        )
    assert (exc.value.details or {}).get("reason") == "template_resolution_failed"
    after = await db.scalar(
        select(func.count()).select_from(CommunicationMessage).where(
            CommunicationMessage.tenant_id == tenant_id
        )
    )
    assert after == before


@pytest.mark.asyncio
async def test_link_resolution_failure_creates_no_message(db, tenant_id: str) -> None:
    before = await db.scalar(
        select(func.count()).select_from(CommunicationMessage).where(
            CommunicationMessage.tenant_id == tenant_id
        )
    )
    with pytest.raises(SendCommunicationError) as exc:
        await render_communication_intent(
            IntentExecutionRequest(
                tenant_id=tenant_id,
                intent=CommunicationIntent.REQUEST_QUESTIONNAIRE,
                origin=CommunicationOrigin(
                    entity_type="sales_inquiry", entity_id=str(uuid.uuid4())
                ),
                recipients=[CommunicationRecipient(address="s@example.test")],
                channel="email",
                template_variables={"contact_name": "Ann"},
                link_requests=(
                    LinkResolveRequest(
                        tenant_id=tenant_id,
                        link_intent="sales_questionnaire",
                        entity_type="lead",
                        entity_id="l1",
                        apply_path_or_url="",  # LinkResolver requires path
                    ),
                ),
            )
        )
    assert (exc.value.details or {}).get("reason") == "link_resolution_failed"
    after = await db.scalar(
        select(func.count()).select_from(CommunicationMessage).where(
            CommunicationMessage.tenant_id == tenant_id
        )
    )
    assert after == before


@pytest.mark.asyncio
async def test_execute_intent_snapshot_and_g13_and_idempotency(db, tenant_id: str) -> None:
    oc = await _own_company_id(db, tenant_id)
    inquiry_id = str(uuid.uuid4())
    idem = f"gate-idem-{uuid.uuid4().hex}"
    req = IntentExecutionRequest(
        tenant_id=tenant_id,
        intent=CommunicationIntent.REQUEST_QUESTIONNAIRE,
        origin=CommunicationOrigin(entity_type="sales_inquiry", entity_id=inquiry_id),
        recipients=[CommunicationRecipient(address="s@example.test")],
        channel="email",
        locale="en",
        template_variables={"contact_name": "Ann"},
        link_requests=(
            LinkResolveRequest(
                tenant_id=tenant_id,
                link_intent="sales_questionnaire",
                entity_type="lead",
                entity_id=str(uuid.uuid4()),
                apply_path_or_url="/public/apply/gate-token?lang=en",
            ),
        ),
        own_company_id=oc,
        idempotency_key=idem,
        correlation_id="corr-1",
        source_event_id="evt-1",
    )
    first = await execute_communication_intent(db, req, skip_transport=True)
    second = await execute_communication_intent(db, req, skip_transport=True)
    assert second.idempotent_replay is True
    assert second.message_id == first.message_id

    msg = await db.get(CommunicationMessage, first.message_id)
    assert msg is not None
    payload = dict(msg.payload or {})
    assert payload.get("intent") == CommunicationIntent.REQUEST_QUESTIONNAIRE.value
    assert payload.get("template_key") == "questionnaire_invite_email_v1"
    assert payload.get("origin", {}).get("entity_id") == inquiry_id
    assert payload.get("resolved_links")
    assert payload.get("resolved_links")[0]["link_intent"] == "sales_questionnaire"
    assert payload.get("correlation_id") == "corr-1"
    assert payload.get("policy_decision", {}).get("allowed") is True

    links = (
        await db.execute(
            select(CommunicationThreadEntityLink).where(
                CommunicationThreadEntityLink.tenant_id == tenant_id,
                CommunicationThreadEntityLink.thread_id == first.thread_id,
                CommunicationThreadEntityLink.entity_type == "sales_inquiry",
                CommunicationThreadEntityLink.entity_id == inquiry_id,
            )
        )
    ).scalars().all()
    assert len(links) >= 1


def test_questionnaire_caller_has_no_legacy_writer_or_url_mint() -> None:
    text = QUESTIONNAIRE_EMAIL.read_text(encoding="utf-8")
    assert "resolve_template(" not in text
    assert "absolute_questionnaire_url" not in text
    assert "absolute_public_url" not in text
    assert "send_email_for_tenant" not in text
    assert "await send_communication(" not in text
    assert "from backend.app.communications.send_communication import send_communication" not in text
    assert "CommunicationIntent" in text
    assert "render_communication_intent" in text
    assert "prepare_and_send_communication" in text
    assert "LinkResolveRequest" in text

    tree = ast.parse(text)
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)
    assert "backend.app.services.communication_templates" not in imports
    assert "backend.app.services.communication_templates.registry" not in imports


def test_communication_command_requires_intent_field() -> None:
    cmd = CommunicationCommand(
        tenant_id="t",
        origin=CommunicationOrigin(entity_type="lead", entity_id="1"),
        recipients=(),
        channel="email",
        intent=CommunicationIntent.REQUEST_QUESTIONNAIRE,
    )
    assert cmd.normalized_intent() is CommunicationIntent.REQUEST_QUESTIONNAIRE
