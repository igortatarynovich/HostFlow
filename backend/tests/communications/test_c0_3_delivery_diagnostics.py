"""C0.3 — delivery diagnostics merge-gate contracts."""

from __future__ import annotations

import ast
import uuid
from pathlib import Path

import pytest
from sqlalchemy import select

from backend.app.communications.delivery_canon import (
    ALLOWED_TRANSITIONS,
    CANONICAL_STATUSES,
    STATUS_ACCEPTED,
    STATUS_CANCELLED,
    STATUS_DELIVERED,
    STATUS_FAILED,
    STATUS_QUEUED,
    STATUS_SENT,
    can_transition,
    normalize_canonical_status,
)
from backend.app.models.communication import CommunicationMessage
from backend.app.models.communication_delivery import CommunicationDelivery
from backend.app.communications.delivery_diagnostics import (
    apply_delivery_callback,
    get_delivery_diagnostics,
    record_delivery_attempt,
    request_manual_retry,
)
from backend.app.communications.delivery_errors import (
    REASON_INVALID_RECIPIENT,
    REASON_RATE_LIMIT,
    REASON_SEND_FAILED,
    REASON_TEMPORARY_TRANSPORT_ERROR,
    normalize_delivery_error,
)
from backend.app.communications.delivery_retry import retry_decision
from backend.app.communications.intent import CommunicationIntent
from backend.app.communications.send_communication import (
    CommunicationOrigin,
    CommunicationRecipient,
    SendCommunicationContent,
    SendCommunicationRequest,
    send_communication,
)
from backend.app.models.communication_delivery_attempt import CommunicationDeliveryAttempt
from backend.app.models.communication_delivery_callback_unresolved import (
    CommunicationDeliveryCallbackUnresolved,
)
from backend.app.models.own_company import OwnCompany

REPO = Path(__file__).resolve().parents[3]
BACKEND_APP = REPO / "backend" / "app"


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


async def _send_ok(db, *, tenant_id: str):
    oc = await _own_company_id(db, tenant_id)
    entity_id = str(uuid.uuid4())

    async def _transport():
        return None

    return await send_communication(
        db,
        SendCommunicationRequest(
            tenant_id=tenant_id,
            origin=CommunicationOrigin(entity_type="lead", entity_id=entity_id),
            recipients=[CommunicationRecipient(address=f"{uuid.uuid4().hex[:8]}@example.com")],
            channel="email",
            intent=CommunicationIntent.MANUAL_OUTBOUND,
            content=SendCommunicationContent(
                subject="C0.3 diagnostics",
                body_text="hello",
            ),
            own_company_id=oc,
            actor_id=None,
            purpose="test_c0_3",
        ),
        transport=_transport,
    )


def test_state_machine_monotonicity_explicit_allowlist():
    """Merge gate: only explicitly allowed transitions; no backward / revival."""
    forbidden = [
        (STATUS_DELIVERED, STATUS_SENT),
        (STATUS_DELIVERED, STATUS_ACCEPTED),
        (STATUS_DELIVERED, STATUS_QUEUED),
        (STATUS_DELIVERED, STATUS_FAILED),
        (STATUS_FAILED, STATUS_QUEUED),  # no rewind — retry appends attempt
        (STATUS_CANCELLED, STATUS_DELIVERED),
        (STATUS_CANCELLED, STATUS_QUEUED),
        (STATUS_CANCELLED, STATUS_SENT),
        (STATUS_SENT, STATUS_ACCEPTED),
        (STATUS_SENT, STATUS_QUEUED),
        (STATUS_ACCEPTED, STATUS_QUEUED),
    ]
    for cur, nxt in forbidden:
        assert can_transition(cur, nxt) is False, f"illegal {cur} → {nxt}"

    allowed = [
        (STATUS_QUEUED, STATUS_ACCEPTED),
        (STATUS_QUEUED, STATUS_SENT),
        (STATUS_QUEUED, STATUS_DELIVERED),
        (STATUS_ACCEPTED, STATUS_SENT),
        (STATUS_SENT, STATUS_DELIVERED),
        (STATUS_SENT, "bounced"),
        (STATUS_FAILED, STATUS_SENT),  # recovery via new attempt
        (STATUS_FAILED, STATUS_DELIVERED),
        (STATUS_DELIVERED, STATUS_DELIVERED),
        (STATUS_FAILED, STATUS_FAILED),
    ]
    for cur, nxt in allowed:
        assert can_transition(cur, nxt) is True, f"expected {cur} → {nxt}"

    # Exhaustive: any pair not in ALLOWED_TRANSITIONS must be rejected.
    for cur in CANONICAL_STATUSES:
        for nxt in CANONICAL_STATUSES:
            expected = (cur, nxt) in ALLOWED_TRANSITIONS
            assert can_transition(cur, nxt) is expected, f"{cur}→{nxt}"


def test_error_taxonomy_never_bare_failed():
    err = normalize_delivery_error(raw_message="SMTP 550 mailbox unavailable")
    assert err.reason_code in {
        REASON_INVALID_RECIPIENT,
        REASON_TEMPORARY_TRANSPORT_ERROR,
        REASON_SEND_FAILED,
    }
    assert err.reason_code
    assert err.safe_message


def test_retry_policy_by_reason_not_text():
    permanent = retry_decision(reason_code=REASON_INVALID_RECIPIENT, attempt_number=1)
    assert permanent["allowed"] is False
    assert permanent["permanent_failure"] is True

    temporary = retry_decision(
        reason_code=REASON_TEMPORARY_TRANSPORT_ERROR, attempt_number=1
    )
    assert temporary["allowed"] is True
    assert temporary["next_retry_at"]

    rate = retry_decision(
        reason_code=REASON_RATE_LIMIT, attempt_number=1, retry_after_seconds=120
    )
    assert rate["allowed"] is True
    assert rate["retry_after_seconds"] == 120

    exhausted = retry_decision(
        reason_code=REASON_TEMPORARY_TRANSPORT_ERROR, attempt_number=5
    )
    assert exhausted["exhausted"] is True
    assert exhausted["allowed"] is False


@pytest.mark.asyncio
async def test_attempts_immutable_retry_appends(db, tenant_id):
    result = await _send_ok(db, tenant_id=tenant_id)
    assert result.delivery_id
    a1 = await record_delivery_attempt(
        db,
        tenant_id=tenant_id,
        message_id=result.message_id,
        delivery_id=result.delivery_id,
        provider="smtp",
        canonical_result=STATUS_FAILED,
        reason_code=REASON_TEMPORARY_TRANSPORT_ERROR,
        raw_message="421 try again",
    )
    a2 = await record_delivery_attempt(
        db,
        tenant_id=tenant_id,
        message_id=result.message_id,
        delivery_id=result.delivery_id,
        provider="smtp",
        canonical_result=STATUS_SENT,
    )
    assert a1.id != a2.id
    assert a2.attempt_number == a1.attempt_number + 1
    # Original row unchanged.
    reloaded = await db.get(CommunicationDeliveryAttempt, a1.id)
    assert reloaded is not None
    assert reloaded.canonical_result == STATUS_FAILED
    assert reloaded.reason_code == REASON_TEMPORARY_TRANSPORT_ERROR


@pytest.mark.asyncio
async def test_callback_idempotent_and_no_downgrade(db, tenant_id):
    result = await _send_ok(db, tenant_id=tenant_id)
    first = await apply_delivery_callback(
        db,
        tenant_id=tenant_id,
        provider="smtp",
        payload={
            "event_id": "evt-1",
            "provider_message_id": "prov-1",
            "canonical_status": "delivered",
            "status": "delivered",
        },
        message_id=result.message_id,
        delivery_id=result.delivery_id,
    )
    assert first["status"] == "applied"
    replay = await apply_delivery_callback(
        db,
        tenant_id=tenant_id,
        provider="smtp",
        payload={
            "event_id": "evt-1",
            "provider_message_id": "prov-1",
            "canonical_status": "delivered",
        },
        message_id=result.message_id,
        delivery_id=result.delivery_id,
    )
    assert replay["idempotent_replay"] is True

    ooo = await apply_delivery_callback(
        db,
        tenant_id=tenant_id,
        provider="smtp",
        payload={
            "event_id": "evt-2",
            "provider_message_id": "prov-1",
            "canonical_status": "sent",
            "status": "sent",
        },
        message_id=result.message_id,
        delivery_id=result.delivery_id,
    )
    assert ooo["status"] == "ignored_out_of_order"
    view = await get_delivery_diagnostics(
        db, tenant_id=tenant_id, message_id=result.message_id
    )
    assert view is not None
    assert view.status == STATUS_DELIVERED


@pytest.mark.asyncio
async def test_unresolved_callback_queued(db, tenant_id):
    out = await apply_delivery_callback(
        db,
        tenant_id=tenant_id,
        provider="smtp",
        payload={"event_id": "orphan-1", "canonical_status": "delivered"},
    )
    assert out["status"] == "unresolved"
    row = await db.get(
        CommunicationDeliveryCallbackUnresolved, out["unresolved_id"]
    )
    assert row is not None
    assert row.raw_payload.get("event_id") == "orphan-1"


@pytest.mark.asyncio
async def test_operator_diagnostics_without_logs(db, tenant_id):
    result = await _send_ok(db, tenant_id=tenant_id)
    await record_delivery_attempt(
        db,
        tenant_id=tenant_id,
        message_id=result.message_id,
        delivery_id=result.delivery_id,
        provider="smtp",
        canonical_result=STATUS_FAILED,
        reason_code=REASON_RATE_LIMIT,
        retry_after_seconds=30,
        raw_message="429 too many",
    )
    view = await get_delivery_diagnostics(
        db, tenant_id=tenant_id, message_id=result.message_id
    )
    assert view is not None
    data = view.to_dict()
    assert data["status"]
    assert data["last_attempt"]["reason_code"] == REASON_RATE_LIMIT
    assert data["last_attempt"]["retryable"] is True
    assert data["timeline"]
    assert "raw_provider_payload" not in data
    assert "stack" not in str(data).lower()


@pytest.mark.asyncio
async def test_manual_retry_audited_path(db, tenant_id):
    result = await _send_ok(db, tenant_id=tenant_id)
    await record_delivery_attempt(
        db,
        tenant_id=tenant_id,
        message_id=result.message_id,
        delivery_id=result.delivery_id,
        provider="smtp",
        canonical_result=STATUS_FAILED,
        reason_code=REASON_TEMPORARY_TRANSPORT_ERROR,
        raw_message="timeout",
    )
    delivery_before = await db.get(CommunicationDelivery, result.delivery_id)
    assert delivery_before is not None
    assert normalize_canonical_status(delivery_before.status) == STATUS_FAILED

    decision = await request_manual_retry(
        db,
        tenant_id=tenant_id,
        message_id=result.message_id,
        actor_user_id="user-1",
    )
    assert decision["allowed"] is True
    assert decision["scheduled"] is True
    # Canonical delivery status must not rewind failed → queued.
    delivery_after = await db.get(CommunicationDelivery, result.delivery_id)
    assert delivery_after is not None
    assert normalize_canonical_status(delivery_after.status) == STATUS_FAILED


@pytest.mark.asyncio
async def test_retry_does_not_create_new_message_or_delivery(db, tenant_id):
    """Merge gate: Message → Delivery → Attempt#N (same message/delivery ids)."""
    result = await _send_ok(db, tenant_id=tenant_id)
    msg_id = result.message_id
    delivery_id = result.delivery_id
    assert delivery_id

    await record_delivery_attempt(
        db,
        tenant_id=tenant_id,
        message_id=msg_id,
        delivery_id=delivery_id,
        provider="smtp",
        canonical_result=STATUS_FAILED,
        reason_code=REASON_TEMPORARY_TRANSPORT_ERROR,
        raw_message="timeout",
    )
    await request_manual_retry(
        db,
        tenant_id=tenant_id,
        message_id=msg_id,
        actor_user_id="ops-1",
    )
    await record_delivery_attempt(
        db,
        tenant_id=tenant_id,
        message_id=msg_id,
        delivery_id=delivery_id,
        provider="smtp",
        canonical_result=STATUS_SENT,
    )

    attempts = (
        await db.execute(
            select(CommunicationDeliveryAttempt)
            .where(
                CommunicationDeliveryAttempt.tenant_id == tenant_id,
                CommunicationDeliveryAttempt.message_id == msg_id,
            )
            .order_by(CommunicationDeliveryAttempt.attempt_number.asc())
        )
    ).scalars().all()
    assert len(attempts) >= 3
    assert {a.message_id for a in attempts} == {msg_id}
    assert {a.delivery_id for a in attempts} == {delivery_id}
    assert [a.attempt_number for a in attempts] == list(
        range(1, len(attempts) + 1)
    )

    # Still a single message + delivery row for this send.
    msg = await db.get(CommunicationMessage, msg_id)
    assert msg is not None
    assert str((msg.payload or {}).get("delivery_id")) == delivery_id


@pytest.mark.asyncio
async def test_timeline_from_immutable_attempts_only(db, tenant_id):
    """Merge gate: timeline reconstructs what/when/why/who/callback from attempts."""
    result = await _send_ok(db, tenant_id=tenant_id)
    # Fail first so manual retry is meaningful; keep same message/delivery.
    await record_delivery_attempt(
        db,
        tenant_id=tenant_id,
        message_id=result.message_id,
        delivery_id=result.delivery_id,
        provider="smtp",
        canonical_result=STATUS_FAILED,
        reason_code=REASON_TEMPORARY_TRANSPORT_ERROR,
        raw_message="421 try later",
    )
    await request_manual_retry(
        db,
        tenant_id=tenant_id,
        message_id=result.message_id,
        actor_user_id="manager-7",
    )
    await apply_delivery_callback(
        db,
        tenant_id=tenant_id,
        provider="smtp",
        payload={
            "event_id": "cb-ok",
            "canonical_status": "delivered",
            "status": "delivered",
            "provider_message_id": "pm-9",
        },
        message_id=result.message_id,
        delivery_id=result.delivery_id,
    )
    # Out-of-order callback must still appear on the timeline.
    await apply_delivery_callback(
        db,
        tenant_id=tenant_id,
        provider="smtp",
        payload={
            "event_id": "cb-ooo",
            "canonical_status": "sent",
            "status": "sent",
        },
        message_id=result.message_id,
        delivery_id=result.delivery_id,
    )

    view = await get_delivery_diagnostics(
        db, tenant_id=tenant_id, message_id=result.message_id
    )
    assert view is not None
    assert view.timeline
    kinds = {e["kind"] for e in view.timeline}
    assert "provider_callback" in kinds
    assert "manual_retry" in kinds
    callback_events = [
        e for e in view.timeline if e.get("provider_event_id") == "cb-ooo"
    ]
    assert callback_events
    assert callback_events[0].get("applied") is False
    manual = [e for e in view.timeline if e["kind"] == "manual_retry"]
    assert manual
    assert manual[0].get("initiated_by") == "manager-7"
    assert manual[0].get("reason_code") == REASON_TEMPORARY_TRANSPORT_ERROR
    # Every timeline entry carries when + canonical result (no status-only magic).
    for e in view.timeline:
        assert e.get("at")
        assert e.get("canonical_result")
        assert e.get("attempt_number") is not None

def test_provider_callback_cannot_assign_delivery_status_directly():
    """Merge gate: provider path never mutates delivery.status outside diagnostics."""
    allow_assign = {
        "delivery_diagnostics.py",  # sole writer for transitions
        "send_communication.py",  # initial create / skip_transport seed only
        "communication_delivery.py",  # model defaults
    }
    hits: list[str] = []
    roots = [
        BACKEND_APP / "communications",
        BACKEND_APP / "api" / "v1" / "communications",
        BACKEND_APP / "services",
    ]
    for root in roots:
        if not root.is_dir():
            continue
        for path in root.rglob("*.py"):
            if path.name in allow_assign:
                continue
            rel = str(path.relative_to(REPO)).replace("\\", "/")
            if "/tests/" in rel:
                continue
            text = path.read_text(encoding="utf-8")
            # Ban provider-branched status writes.
            if "if provider" in text and "delivery.status" in text:
                hits.append(f"{rel}:provider_branch_delivery_status")
            tree = ast.parse(text)
            for node in ast.walk(tree):
                if not isinstance(node, ast.Assign):
                    continue
                for target in node.targets:
                    if (
                        isinstance(target, ast.Attribute)
                        and target.attr == "status"
                        and isinstance(target.value, ast.Name)
                        and target.value.id == "delivery"
                    ):
                        hits.append(f"{rel}:delivery.status=")
    # Public callback route must only call apply_delivery_callback.
    cb_route = (
        BACKEND_APP
        / "api"
        / "v1"
        / "communications"
        / "routes"
        / "delivery_diagnostics.py"
    )
    route_text = cb_route.read_text(encoding="utf-8")
    assert "apply_delivery_callback" in route_text
    assert "delivery.status =" not in route_text
    assert hits == [], f"Direct delivery.status mutation outside platform: {hits}"


def test_no_provider_status_checks_outside_diagnostics_platform():
    """Ban direct provider-specific delivery status polling outside platform path."""
    banned_call_names = {
        "get_sms_status",
        "check_delivery_status",
        "fetch_provider_delivery_status",
        "poll_smsapi_status",
        "poll_provider_status",
    }
    allow_files = {
        "delivery_diagnostics.py",
        "delivery_canon.py",
        "delivery_errors.py",
        "delivery_retry.py",
    }
    hits: list[str] = []
    for path in BACKEND_APP.rglob("*.py"):
        if path.name in allow_files:
            continue
        rel = str(path.relative_to(REPO)).replace("\\", "/")
        if "/tests/" in rel:
            continue
        if not any(
            p in rel
            for p in (
                "/communications/",
                "/services/communication",
                "/services/communications",
                "/api/v1/communications/",
            )
        ):
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            name = None
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    name = node.func.id
                elif isinstance(node.func, ast.Attribute):
                    name = node.func.attr
            if name and name in banned_call_names:
                hits.append(f"{rel}:{name}")
    assert hits == [], f"Provider status checks outside diagnostics platform: {hits}"


def test_lead_communication_failed_no_longer_produced():
    path = BACKEND_APP / "services" / "lead_communications.py"
    text = path.read_text(encoding="utf-8")
    tree = ast.parse(text)
    produced = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr == "lead_communication_failed":
            produced.append(node.lineno)
    assert produced == [], (
        "lead.communication.failed must not be produced; use communication.delivery.failed "
        f"(lines {produced})"
    )
    assert "communication_delivery_failed" in text


def test_send_communication_records_attempt_on_transport_failure():
    path = BACKEND_APP / "communications" / "send_communication.py"
    text = path.read_text(encoding="utf-8")
    assert "record_delivery_attempt" in text
    assert "REASON_SEND_FAILED" in text
