"""Unit tests for lead RODO information-obligation evaluation."""

from __future__ import annotations

from types import SimpleNamespace

from backend.app.services.lead_rodo import lead_rodo_satisfied_from_normalized
from backend.app.services.lead_rodo_obligation import (
    evaluate_lead_rodo_obligation,
    stamp_obligation_evaluation,
)


def test_public_form_with_notice_at_source_is_compliant_no_email() -> None:
    d = evaluate_lead_rodo_obligation(
        source="public_form",
        normalized={"email": "a@example.com", "rodo_notice_at_source": True},
    )
    assert d.action == "no_delivery_source_provided"
    assert d.article == "13"
    assert d.collection_path == "direct"


def test_meta_without_notice_proof_requires_delivery() -> None:
    d = evaluate_lead_rodo_obligation(
        source="meta",
        normalized={"email": "a@example.com"},
    )
    assert d.action == "delivery_required"
    assert d.article == "13"
    assert d.reason_code == "direct_collection_notice_unproven"


def test_csv_import_requires_art_14_delivery() -> None:
    d = evaluate_lead_rodo_obligation(
        source="csv_import",
        normalized={"email": "a@example.com"},
    )
    assert d.action == "delivery_required"
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


def test_lawful_exemption_is_recorded() -> None:
    d = evaluate_lead_rodo_obligation(
        source="linkedin",
        normalized={"rodo": {"status": "exempt", "exemption_code": "art_14_5_b"}},
    )
    assert d.action == "no_delivery_exempt"
    assert d.reason_code == "art_14_5_b"
    assert lead_rodo_satisfied_from_normalized(
        {"rodo": {"status": "exempt", "exemption_code": "art_14_5_b"}}
    )


def test_stamp_preserves_controller_and_sets_exempt_status(monkeypatch) -> None:
    monkeypatch.setattr(
        "sqlalchemy.orm.attributes.flag_modified",
        lambda *_args, **_kwargs: None,
    )
    lead = SimpleNamespace(normalized={})
    d = evaluate_lead_rodo_obligation(
        source="referral",
        normalized={"rodo_exempt": True},
    )
    stamp_obligation_evaluation(
        lead,
        d,
        controller_own_company_id="oc-1",
        controller_name="DANEMA TSL",
    )
    block = lead.normalized["rodo"]
    assert block["status"] == "exempt"
    assert block["controller_name"] == "DANEMA TSL"
    assert block["obligation"]["action"] == "no_delivery_exempt"
    assert block["article"] == "14"
