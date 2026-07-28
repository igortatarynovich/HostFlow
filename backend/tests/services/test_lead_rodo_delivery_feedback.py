"""Unit tests: mailbox DSN → lead RODO undelivered / deferred gate."""

from __future__ import annotations

from backend.app.models.lead import Lead
from backend.app.services.lead_rodo import (
    lead_rodo_notice_status_from_normalized,
    lead_rodo_satisfied_from_normalized,
    lead_rodo_sent_from_normalized,
    mark_lead_rodo_undelivered,
)
from backend.app.services.lead_rodo_delivery_feedback import (
    parse_rodo_delivery_feedback,
)


def test_parse_invalid_recipient_ru_gmail_dsn():
    body = (
        "** Адрес не найден **\n\n"
        "Сообщение не доставлено, так как адрес lukaszhylak08@gmail.com не найден "
        "или не принимает входящие письма.\n"
        "550 5.1.1 The email account that you tried to reach does not exist."
    )
    parsed = parse_rodo_delivery_feedback(subject="Delivery Status Notification", body_text=body)
    assert parsed is not None
    assert parsed.recipient_email == "lukaszhylak08@gmail.com"
    assert parsed.outcome == "failed"
    assert parsed.reason_code == "invalid_recipient"


def test_parse_deferred_spf_interia():
    body = (
        "** Адрес не найден **\n"
        "адрес annawylag@interia.pl не найден\n"
        "451 4.4.0 Recipient address rejected: Deferred due to SPF unsafe"
    )
    parsed = parse_rodo_delivery_feedback(body_text=body)
    assert parsed is not None
    assert parsed.recipient_email == "annawylag@interia.pl"
    assert parsed.outcome == "deferred"
    assert parsed.reason_code == "spf_rejected"


def test_parse_not_yet_delivered():
    body = (
        "** Пока не доставлено **\n"
        "При доставке сообщения получателю lukasz-pera@1com.pl возникла временная ошибка. "
        "Gmail будет повторять попытки."
    )
    parsed = parse_rodo_delivery_feedback(body_text=body)
    assert parsed is not None
    assert parsed.recipient_email == "lukasz-pera@1com.pl"
    assert parsed.outcome == "deferred"
    assert parsed.reason_code == "deferred"


def test_sent_then_undelivered_clears_satisfied_and_allows_retry():
    lead = Lead(
        id="00000000-0000-0000-0000-000000000001",
        tenant_id="11111111-1111-1111-1111-111111111111",
        normalized={
            "email": "a@example.com",
            "rodo": {
                "status": "sent",
                "sent_at": "2026-07-27T08:00:00+00:00",
                "recipient": "a@example.com",
            },
        },
    )
    assert lead_rodo_satisfied_from_normalized(lead.normalized) is True
    assert lead_rodo_sent_from_normalized(lead.normalized) is True

    mark_lead_rodo_undelivered(
        lead,
        reason="Email address not found or does not accept mail.",
        reason_code="invalid_recipient",
        outcome="failed",
    )
    assert lead_rodo_satisfied_from_normalized(lead.normalized) is False
    assert lead_rodo_notice_status_from_normalized(lead.normalized) == "failed"
    assert lead_rodo_sent_from_normalized(lead.normalized) is False
    block = lead.normalized["rodo"]
    assert block["failure_reason_code"] == "invalid_recipient"
    assert block["sent_at"]  # audit retained


def test_deferred_also_blocks_satisfied():
    lead = Lead(
        id="00000000-0000-0000-0000-000000000002",
        tenant_id="11111111-1111-1111-1111-111111111111",
        normalized={
            "rodo": {"status": "sent", "sent_at": "2026-07-27T08:00:00+00:00"},
        },
    )
    mark_lead_rodo_undelivered(
        lead,
        reason="Delivery temporarily delayed by the recipient server.",
        reason_code="deferred",
        outcome="deferred",
    )
    assert lead_rodo_satisfied_from_normalized(lead.normalized) is False
    assert lead_rodo_notice_status_from_normalized(lead.normalized) == "deferred"
