"""C0.1b merge criteria — registry, policy, snapshot, bypass ban."""

from __future__ import annotations

import ast
import uuid
from pathlib import Path

import pytest
from sqlalchemy import func, select

from backend.app.communications.command import (
    CommunicationCommand,
    CommunicationOrigin,
    CommunicationRecipient,
    SendCommunicationContent,
)
from backend.app.communications.execute_intent import (
    IntentExecutionRequest,
    execute_communication_intent,
)
from backend.app.communications.intent import (
    CommunicationIntent,
    assert_enum_matches_registry,
)
from backend.app.communications.intent_policy import evaluate_intent_policy
from backend.app.communications.intent_registry import (
    get_intent_definition,
    is_combination_allowed,
    iter_allowed_matrix,
    list_intent_definitions,
)
from backend.app.communications.link_resolver import LinkResolveRequest
from backend.app.communications.prepare_send import prepare_and_send_communication
from backend.app.communications.send_communication import SendCommunicationError
from backend.app.models.communication import CommunicationMessage
from backend.app.models.own_company import OwnCompany

REPO = Path(__file__).resolve().parents[3]
BACKEND_APP = REPO / "backend" / "app"

# Production outbound Canon entrypoints (must not shrink without replacing callers).
_CANON_SENDER_MODULES = {
    "backend.app.communications.prepare_send",
    "backend.app.communications.execute_intent",
    "backend.app.services.communication_deliveries.questionnaire_email",
}

# send_email_for_tenant call sites allowed until migrated (must not grow).
_SMTP_ALLOWLIST = {
    "backend/app/communications/prepare_send.py",
    "backend/app/services/tenant_email.py",
    "backend/app/services/lead_communications.py",
    "backend/app/services/lead_rodo.py",
    "backend/app/services/rodo.py",
    "backend/app/services/candidate_notifications.py",
    "backend/app/services/draft_reminders.py",
    "backend/app/services/contact_attempts.py",
    "backend/app/services/risk_intel_digest_email.py",
    "backend/app/api/v1/communications/_helpers/dispatch.py",
    "backend/app/api/v1/communications/_helpers/telegram_intake/candidate_link.py",
}

# Direct CommunicationMessage( construction outside Canon writer / inbound / inbox.
_MESSAGE_CTOR_ALLOWLIST = {
    "backend/app/communications/send_communication.py",
    "backend/app/communications/inbound_ingest.py",
    "backend/app/api/v1/communications/routes/messages.py",
    "backend/app/api/v1/communications/routes/ingest.py",
    "backend/app/api/v1/communications/_helpers/ingest.py",
    "backend/app/models/communication.py",
}

_DELIVERY_CTOR_ALLOWLIST = {
    "backend/app/communications/send_communication.py",
    "backend/app/models/communication_delivery.py",
}


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


def test_enum_matches_intent_registry() -> None:
    assert_enum_matches_registry()
    assert get_intent_definition("request_questionnaire").default_template_key


def test_new_intent_requires_registry_entry() -> None:
    with pytest.raises(Exception):
        get_intent_definition("not_a_real_intent_xyz")


def test_matrix_deny_by_default_unknown_combination() -> None:
    assert is_combination_allowed(
        entity_type="sales_inquiry",
        intent_key="request_questionnaire",
        channel="email",
    )
    assert not is_combination_allowed(
        entity_type="service_order",
        intent_key="request_questionnaire",
        channel="email",
    )
    assert not is_combination_allowed(
        entity_type="sales_inquiry",
        intent_key="request_questionnaire",
        channel="sms",
    )
    denied = evaluate_intent_policy(
        intent_key="request_questionnaire",
        entity_type="service_order",
        channel="email",
    )
    assert denied.allowed is False
    assert denied.reason_code == "intent_entity_denied"


def test_matrix_triples_come_only_from_registry() -> None:
    triples = list(iter_allowed_matrix())
    assert triples
    for entity_type, intent_key, channel in triples:
        assert is_combination_allowed(
            entity_type=entity_type, intent_key=intent_key, channel=channel
        )


def test_typed_policy_result_fields() -> None:
    allowed = evaluate_intent_policy(
        intent_key="request_questionnaire",
        entity_type="sales_inquiry",
        channel="email",
    )
    assert allowed.allowed is True
    assert allowed.reason_code == "allowed"
    assert allowed.requires_consent is False
    assert allowed.allows_automation is True
    assert "sales_questionnaire" in allowed.required_link_intents
    assert allowed.default_template_key == "questionnaire_invite_email_v1"
    assert allowed.to_dict()["intent_key"] == "request_questionnaire"


@pytest.mark.asyncio
async def test_forbidden_combination_blocks_before_message(db, tenant_id: str) -> None:
    oc = await _own_company_id(db, tenant_id)
    before = await db.scalar(
        select(func.count()).select_from(CommunicationMessage).where(
            CommunicationMessage.tenant_id == tenant_id
        )
    )
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
    after = await db.scalar(
        select(func.count()).select_from(CommunicationMessage).where(
            CommunicationMessage.tenant_id == tenant_id
        )
    )
    assert after == before


@pytest.mark.asyncio
async def test_full_immutable_snapshot_on_message(db, tenant_id: str) -> None:
    oc = await _own_company_id(db, tenant_id)
    inquiry_id = str(uuid.uuid4())
    result = await execute_communication_intent(
        db,
        IntentExecutionRequest(
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
                    apply_path_or_url="/public/apply/snap-token?lang=en",
                ),
            ),
            own_company_id=oc,
            idempotency_key=f"snap-{uuid.uuid4().hex}",
            correlation_id="corr-snap",
            source_event_id="evt-snap",
        ),
        skip_transport=True,
    )
    msg = await db.get(CommunicationMessage, result.message_id)
    assert msg is not None
    snap = dict((msg.payload or {}).get("snapshot") or {})
    for key in (
        "schema_version",
        "intent_key",
        "intent_version",
        "policy_decision",
        "origin",
        "recipients",
        "channel",
        "template_key",
        "template_version",
        "rendered_subject",
        "rendered_body_text",
        "resolved_variables",
        "links",
        "compliance_decision",
        "correlation_id",
        "idempotency_key",
    ):
        assert key in snap, key
    assert snap["intent_key"] == "request_questionnaire"
    assert snap["origin"]["entity_id"] == inquiry_id
    assert snap["template_key"] == "questionnaire_invite_email_v1"
    assert snap["links"][0]["token"] == "snap-token"
    assert snap["policy_decision"]["allowed"] is True
    # Snapshot must not require live template registry to interpret what was sent.
    assert snap["rendered_body_text"]
    assert "Ann" in snap["rendered_body_text"]


def _iter_py_files() -> list[Path]:
    return sorted(p for p in BACKEND_APP.rglob("*.py") if "migrations" not in p.parts)


def _module_calls_name(path: Path, name: str) -> bool:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError:
        return False
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id == name:
                return True
            if isinstance(func, ast.Attribute) and func.attr == name:
                return True
    return False


def test_legacy_bypass_allowlist_does_not_grow() -> None:
    smtp_hits = []
    msg_hits = []
    delivery_hits = []
    for path in _iter_py_files():
        rel = str(path.relative_to(REPO)).replace("\\", "/")
        text = path.read_text(encoding="utf-8")
        if "send_email_for_tenant" in text and _module_calls_name(path, "send_email_for_tenant"):
            # Definition site in tenant_email is allowed; call sites tracked.
            if rel.endswith("tenant_email.py") and "async def send_email_for_tenant" in text:
                continue
            if rel not in _SMTP_ALLOWLIST:
                smtp_hits.append(rel)
        if "CommunicationMessage(" in text and rel not in _MESSAGE_CTOR_ALLOWLIST:
            # Skip type hints / docs-only mentions without Call
            if _module_calls_name(path, "CommunicationMessage") or "CommunicationMessage(" in text:
                # Narrow: only files that construct (assignment / call with keyword)
                if "CommunicationMessage(" in text and "class CommunicationMessage" not in text:
                    msg_hits.append(rel)
        if "CommunicationDelivery(" in text and rel not in _DELIVERY_CTOR_ALLOWLIST:
            if "class CommunicationDelivery" not in text:
                delivery_hits.append(rel)
    assert smtp_hits == [], f"New SMTP bypasses (not on allowlist): {smtp_hits}"
    assert msg_hits == [], f"New CommunicationMessage writers: {msg_hits}"
    assert delivery_hits == [], f"New CommunicationDelivery writers: {delivery_hits}"


def test_production_canon_callers_use_sender_path() -> None:
    q = BACKEND_APP / "services/communication_deliveries/questionnaire_email.py"
    text = q.read_text(encoding="utf-8")
    assert "prepare_and_send_communication" in text
    assert "await send_communication(" not in text
    assert "send_email_for_tenant" not in text


def test_registry_is_sole_intent_definition_source() -> None:
    """No parallel _INTENT_POLICIES table outside registry."""
    intent_py = (BACKEND_APP / "communications/intent.py").read_text(encoding="utf-8")
    assert "_INTENT_POLICIES" not in intent_py
    assert "intent_registry" in intent_py
    assert len(list_intent_definitions()) >= 8
