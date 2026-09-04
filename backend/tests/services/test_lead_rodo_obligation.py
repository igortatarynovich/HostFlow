"""Unit tests for lead RODO information-obligation evaluation."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from backend.app.services.lead_rodo import (
    ComplianceTransitionError,
    _stamp_lead_rodo_sent,
    lead_rodo_satisfied_from_normalized,
    mark_lead_rodo_source_provided,
)
from backend.app.services.lead_rodo_obligation import (
    apply_compliance_transition,
    current_compliance_state,
    evaluate_lead_rodo_obligation,
    stamp_obligation_evaluation,
)


def test_public_form_with_notice_at_source_is_compliant_no_email() -> None:
    d = evaluate_lead_rodo_obligation(
        source="public_form",
        normalized={"email": "a@example.com", "rodo_notice_at_source": True},
    )
    assert d.action == "no_delivery_source_provided"
    assert d.state == "compliant"
    assert d.article == "13"
    assert d.collection_path == "direct"


def test_meta_without_notice_proof_requires_delivery() -> None:
    d = evaluate_lead_rodo_obligation(
        source="meta",
        normalized={"email": "a@example.com"},
    )
    assert d.action == "delivery_required"
    assert d.state == "delivery_required"
    assert d.article == "13"
    assert d.reason_code == "direct_collection_notice_unproven"


def test_csv_import_requires_art_14_delivery() -> None:
    d = evaluate_lead_rodo_obligation(
        source="csv_import",
        normalized={"email": "a@example.com"},
    )
    assert d.action == "delivery_required"
    assert d.state == "delivery_required"
    assert d.article == "14"
    assert d.collection_path == "indirect"


def test_manual_third_party_requires_art_14() -> None:
    d = evaluate_lead_rodo_obligation(source="manual", normalized={"email": "a@example.com"})
    assert d.action == "delivery_required"
    assert d.article == "14"


def test_already_sent_does_not_resend() -> None:
    d = evaluate_lead_rodo_obligation(
        source="webhook",
        normalized={"rodo": {"status": "sent", "sent_at": "2026-09-01T00:00:00Z"}},
    )
    assert d.action == "no_delivery_already_notified"
    assert d.state == "compliant"


def test_lawful_exemption_is_recorded() -> None:
    d = evaluate_lead_rodo_obligation(
        source="linkedin",
        normalized={"rodo": {"status": "exempt", "exemption_code": "art_14_5_b"}},
    )
    assert d.action == "no_delivery_exempt"
    assert d.state == "exempt"
    assert d.reason_code == "art_14_5_b"
    assert lead_rodo_satisfied_from_normalized(
        {"rodo": {"status": "exempt", "exemption_code": "art_14_5_b"}}
    )


def test_unknown_source_is_review_required_not_silent() -> None:
    d = evaluate_lead_rodo_obligation(source="scraped_forum", normalized={"email": "a@example.com"})
    assert d.state == "review_required"
    assert d.action == "review_required"
    assert d.reason_code == "collection_path_unknown"
    assert d.collection_path == "unknown"
    assert not lead_rodo_satisfied_from_normalized({"rodo": {"status": "review_required"}})


def test_empty_source_is_review_required() -> None:
    d = evaluate_lead_rodo_obligation(source="", normalized={"email": "a@example.com"})
    assert d.state == "review_required"
    assert d.reason_code == "collection_path_unknown"


def test_unknown_source_with_notice_at_source_is_compliant() -> None:
    d = evaluate_lead_rodo_obligation(
        source="mystery",
        normalized={"rodo_notice_at_source": True},
    )
    assert d.state == "compliant"
    assert d.action == "no_delivery_source_provided"


def test_exemption_without_reason_is_review_required() -> None:
    d = evaluate_lead_rodo_obligation(
        source="manual",
        normalized={"rodo_exempt": True},
    )
    assert d.state == "review_required"
    assert d.reason_code == "exemption_reason_missing"
    assert not lead_rodo_satisfied_from_normalized({"rodo": {"status": "review_required"}})


def test_stamp_writes_assessment_evidence_and_exempt_status(monkeypatch) -> None:
    monkeypatch.setattr(
        "sqlalchemy.orm.attributes.flag_modified",
        lambda *_args, **_kwargs: None,
    )
    lead = SimpleNamespace(normalized={})
    d = evaluate_lead_rodo_obligation(
        source="referral",
        normalized={"rodo_exempt_code": "art_14_5_b"},
    )
    stamp_obligation_evaluation(
        lead,
        d,
        controller_own_company_id="oc-1",
        controller_name="DANEMA TSL",
    )
    block = lead.normalized["rodo"]
    assert block["status"] == "exempt"
    assert block["compliance_state"] == "exempt"
    assert block["controller_name"] == "DANEMA TSL"
    assert block["obligation"]["action"] == "no_delivery_exempt"
    assert block["obligation"]["state"] == "exempt"
    assert block["article"] == "14"
    assert block["assessment"]["reason_code"] == "art_14_5_b"
    assert block["assessment"]["controller_name"] == "DANEMA TSL"


def test_stamp_review_required_is_actionable(monkeypatch) -> None:
    monkeypatch.setattr(
        "sqlalchemy.orm.attributes.flag_modified",
        lambda *_args, **_kwargs: None,
    )
    lead = SimpleNamespace(normalized={})
    d = evaluate_lead_rodo_obligation(source="unknown-channel", normalized={})
    stamp_obligation_evaluation(lead, d)
    block = lead.normalized["rodo"]
    assert block["status"] == "review_required"
    assert block["compliance_state"] == "review_required"
    assert block["assessment"]["reason_code"] == "collection_path_unknown"
    assert "delivery_evidence" not in block


def test_open_status_wins_over_closed_compliance_state() -> None:
    block = {"status": "review_required", "compliance_state": "compliant"}
    assert current_compliance_state(block) == "review_required"
    assert not lead_rodo_satisfied_from_normalized({"rodo": block})


def test_delivery_failed_cannot_become_delivered_without_send_proof() -> None:
    block = {"status": "failed", "compliance_state": "delivery_failed"}
    assert not apply_compliance_transition(block, "delivered")
    assert block["compliance_state"] == "delivery_failed"
    assert not lead_rodo_satisfied_from_normalized({"rodo": block})


def test_delivery_failed_becomes_delivered_with_smtp_proof() -> None:
    block = {
        "status": "failed",
        "compliance_state": "delivery_failed",
        "delivery_evidence": {
            "state": "delivered",
            "recipient": "a@example.com",
            "sent_at": "2026-09-04T00:00:00Z",
            "delivery_via": "tenant_smtp",
            "attempts": [{"via": "tenant_smtp", "ok": True}],
        },
    }
    assert apply_compliance_transition(block, "delivered")
    assert block["compliance_state"] == "delivered"


def test_webhook_notify_is_not_delivery_proof() -> None:
    block = {
        "status": "delivery_required",
        "compliance_state": "delivery_required",
        "delivery_evidence": {
            "state": "delivered",
            "recipient": "a@example.com",
            "sent_at": "2026-09-04T00:00:00Z",
            "delivery_via": "webhook",
        },
    }
    assert not apply_compliance_transition(block, "delivered")
    assert not lead_rodo_satisfied_from_normalized(
        {"rodo": {**block, "status": "sent", "compliance_state": "delivered", "sent_at": "2026-09-04T00:00:00Z"}}
    )


def test_review_required_to_exempt_requires_valid_reason_code() -> None:
    block = {"status": "review_required", "compliance_state": "review_required"}
    assert not apply_compliance_transition(block, "exempt")
    block["exemption_code"] = "not_a_real_code"
    assert not apply_compliance_transition(block, "exempt")
    block["exemption_code"] = "art_14_5_b"
    assert apply_compliance_transition(block, "exempt")
    assert block["compliance_state"] == "exempt"


def test_satisfied_status_is_not_a_universal_resolve() -> None:
    assert not lead_rodo_satisfied_from_normalized({"rodo": {"status": "satisfied"}})


def test_stamp_does_not_overwrite_delivery_failed_with_delivery_required(monkeypatch) -> None:
    monkeypatch.setattr(
        "sqlalchemy.orm.attributes.flag_modified",
        lambda *_args, **_kwargs: None,
    )
    lead = SimpleNamespace(
        normalized={
            "rodo": {
                "status": "failed",
                "compliance_state": "delivery_failed",
                "delivery_evidence": {"state": "delivery_failed"},
            }
        }
    )
    d = evaluate_lead_rodo_obligation(source="csv_import", normalized=lead.normalized)
    assert d.state == "delivery_required"
    stamp_obligation_evaluation(lead, d)
    assert lead.normalized["rodo"]["compliance_state"] == "delivery_failed"
    assert not lead_rodo_satisfied_from_normalized(lead.normalized)


def test_review_required_to_compliant_requires_operator_proof(monkeypatch) -> None:
    monkeypatch.setattr(
        "sqlalchemy.orm.attributes.flag_modified",
        lambda *_args, **_kwargs: None,
    )
    lead = SimpleNamespace(
        normalized={"rodo": {"status": "review_required", "compliance_state": "review_required"}}
    )
    with pytest.raises(ComplianceTransitionError) as exc:
        mark_lead_rodo_source_provided(lead, actor_id=None, proof="operator_attestation")
    assert exc.value.code == "RODO_OPERATOR_REQUIRED"
    assert lead.normalized["rodo"]["compliance_state"] == "review_required"

    mark_lead_rodo_source_provided(
        lead,
        actor_id="user-1",
        note="Shown the clause at the job fair",
        proof="operator_attestation",
    )
    block = lead.normalized["rodo"]
    assert block["status"] == "source_provided"
    assert block["compliance_state"] == "compliant"
    assert block["assessment"]["reason_code"] == "source_provided_operator"
    assert block["assessment"]["actor_id"] == "user-1"
    assert lead_rodo_satisfied_from_normalized(lead.normalized)


def test_stamp_sent_closes_delivery_failed_only_with_smtp_proof(monkeypatch) -> None:
    monkeypatch.setattr(
        "sqlalchemy.orm.attributes.flag_modified",
        lambda *_args, **_kwargs: None,
    )
    lead = SimpleNamespace(
        normalized={"rodo": {"status": "failed", "compliance_state": "delivery_failed"}}
    )
    _stamp_lead_rodo_sent(
        lead,
        email="a@example.com",
        channel="email",
        rodo_version_id="v1",
        auto_trigger=None,
        ingest_source=None,
        extra={
            "delivery_via": "tenant_smtp",
            "attempts": [{"via": "tenant_smtp", "ok": True}],
        },
    )
    assert lead.normalized["rodo"]["compliance_state"] == "delivered"
    assert lead.normalized["rodo"]["status"] == "sent"
    assert lead_rodo_satisfied_from_normalized(lead.normalized)


def test_stamp_sent_rejects_webhook_as_proof(monkeypatch) -> None:
    monkeypatch.setattr(
        "sqlalchemy.orm.attributes.flag_modified",
        lambda *_args, **_kwargs: None,
    )
    lead = SimpleNamespace(
        normalized={"rodo": {"status": "delivery_required", "compliance_state": "delivery_required"}}
    )
    _stamp_lead_rodo_sent(
        lead,
        email="a@example.com",
        channel="email",
        rodo_version_id="v1",
        auto_trigger=None,
        ingest_source=None,
        extra={"delivery_via": "webhook"},
    )
    block = lead.normalized["rodo"]
    assert block["compliance_state"] == "delivery_failed"
    assert block["status"] == "failed"
    assert not lead_rodo_satisfied_from_normalized(lead.normalized)
