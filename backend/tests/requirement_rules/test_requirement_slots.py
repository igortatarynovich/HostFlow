"""Requirement document slots — registry and Candidate Evidence evaluator."""

from __future__ import annotations

from backend.app.requirement_rules.evaluator import evaluate_requirement_rules
from backend.app.requirement_rules.registry import build_requirement_rule_set, get_document_pack_manifest
from backend.app.requirement_rules.slot_evaluator import evaluate_document_slot
from backend.app.requirement_rules.slot_registry import get_slot_definition, load_slot_registry


def _approved_evidence(variant_code: str, documents: list[dict]) -> dict:
    return {
        "status": "approved",
        "evidence_variant_code": variant_code,
        "documents": documents,
    }


def test_slot_registry_loads() -> None:
    registry = load_slot_registry()
    assert registry["version"] == "1.0.0"
    assert get_slot_definition("driver_license_with_code95") is not None


def test_legal_stay_requires_candidate_evidence_without_guessing() -> None:
    result = evaluate_document_slot(
        "legal_stay_confirmation",
        citizenship="UA",
        documents=[
            {
                "document_type_code": "residence_card",
                "status": "approved",
                "has_files": True,
                "expire_date": "2027-01-01",
            },
        ],
    )
    assert result["status"] == "missing"
    assert any("candidate_evidence_required" in str(b.get("code")) for b in result["blockers"])


def test_legal_stay_satisfied_by_approved_evidence() -> None:
    result = evaluate_document_slot(
        "legal_stay_confirmation",
        citizenship="UA",
        candidate_evidence=_approved_evidence(
            "legal_stay_any",
            [
                {
                    "document_id": "doc-1",
                    "document_type_code": "residence_card",
                    "status": "approved",
                    "has_files": True,
                    "expire_date": "2027-01-01",
                },
            ],
        ),
    )
    assert result["status"] == "satisfied"


def test_legal_stay_not_applicable_for_eu() -> None:
    result = evaluate_document_slot(
        "legal_stay_confirmation",
        citizenship="PL",
        candidate_evidence=None,
    )
    assert result["status"] == "not_applicable"


def test_driver_license_code95_combined_single_document() -> None:
    result = evaluate_document_slot(
        "driver_license_with_code95",
        candidate_evidence=_approved_evidence(
            "combined_eu_license",
            [
                {
                    "document_id": "doc-1",
                    "document_type_code": "driver_license_code95",
                    "status": "approved",
                    "has_files": True,
                },
            ],
        ),
    )
    assert result["status"] == "satisfied"
    assert result.get("chosen_alternative_code") == "combined_eu_license"


def test_driver_license_code95_separate_two_documents() -> None:
    result = evaluate_document_slot(
        "driver_license_with_code95",
        candidate_evidence=_approved_evidence(
            "separate_documents",
            [
                {"document_id": "doc-1", "document_type_code": "driver_license", "status": "approved", "has_files": True},
                {"document_id": "doc-2", "document_type_code": "code95", "status": "approved", "has_files": True},
            ],
        ),
    )
    assert result["status"] == "satisfied"
    assert result.get("chosen_alternative_code") == "separate_documents"


def test_driver_license_code95_missing_when_only_license_in_evidence() -> None:
    result = evaluate_document_slot(
        "driver_license_with_code95",
        candidate_evidence=_approved_evidence(
            "separate_documents",
            [
                {"document_id": "doc-1", "document_type_code": "driver_license", "status": "approved", "has_files": True},
            ],
        ),
    )
    assert result["status"] in {"missing", "pending_verification"}


def test_driver_ce_pack_uses_slots() -> None:
    pack = get_document_pack_manifest("recruitment.driver_ce_documents")
    assert pack is not None
    slots = {row["slot_code"] for row in pack["required_slots"]}
    assert slots == {"identity_document", "driver_license_with_code95", "tachograph_card"}


def test_requirement_evaluator_satisfied_with_combined_license() -> None:
    from backend.app.entity_profile.manifests.recruitment import recruitment_candidate_driver_ce_profile

    manifest = recruitment_candidate_driver_ce_profile()
    profile_view = {
        "entity_profile_code": manifest["profile_code"],
        "profile_code": manifest["profile_code"],
        "profile": manifest,
        "fields": manifest["fields"],
    }
    evidence = {
        "identity_document": _approved_evidence(
            "identity_any",
            [{"document_id": "p1", "document_type_code": "passport", "status": "approved", "has_files": True}],
        ),
        "driver_license_with_code95": _approved_evidence(
            "combined_eu_license",
            [{"document_id": "d1", "document_type_code": "driver_license_code95", "status": "approved", "has_files": True}],
        ),
        "tachograph_card": _approved_evidence(
            "tacho_any",
            [{"document_id": "t1", "document_type_code": "tacho_card", "status": "approved", "has_files": True}],
        ),
    }
    result = evaluate_requirement_rules(
        profile_view,
        context="readiness",
        normalized_payload={
            "recruitment.candidate.first_name": "Jan",
            "recruitment.candidate.last_name": "Kowalski",
            "recruitment.candidate.contacts.phone": "+48123456789",
        },
        documents=[],
        candidate_evidence_by_requirement=evidence,
    )
    assert result["satisfied"] is True
    assert result["blockers"] == []


def test_requirement_evaluator_not_satisfied_without_evidence() -> None:
    from backend.app.entity_profile.manifests.recruitment import recruitment_candidate_driver_ce_profile

    manifest = recruitment_candidate_driver_ce_profile()
    profile_view = {
        "entity_profile_code": manifest["profile_code"],
        "profile_code": manifest["profile_code"],
        "profile": manifest,
        "fields": manifest["fields"],
    }
    result = evaluate_requirement_rules(
        profile_view,
        context="readiness",
        normalized_payload={
            "recruitment.candidate.first_name": "Jan",
            "recruitment.candidate.last_name": "Kowalski",
            "recruitment.candidate.contacts.phone": "+48123456789",
        },
        documents=[
            {"document_type_code": "passport", "status": "approved", "has_files": True},
            {"document_type_code": "driver_license_code95", "status": "approved", "has_files": True},
            {"document_type_code": "tacho_card", "status": "approved", "has_files": True},
        ],
        candidate_evidence_by_requirement={},
    )
    assert result["satisfied"] is False


def test_requirement_evaluator_satisfied_with_separate_license_and_code95() -> None:
    from backend.app.entity_profile.manifests.recruitment import recruitment_candidate_driver_ce_profile

    manifest = recruitment_candidate_driver_ce_profile()
    profile_view = {
        "entity_profile_code": manifest["profile_code"],
        "profile_code": manifest["profile_code"],
        "profile": manifest,
        "fields": manifest["fields"],
    }
    evidence = {
        "identity_document": _approved_evidence(
            "identity_any",
            [{"document_id": "p1", "document_type_code": "passport", "status": "approved", "has_files": True}],
        ),
        "driver_license_with_code95": _approved_evidence(
            "separate_documents",
            [
                {"document_id": "d1", "document_type_code": "driver_license", "status": "approved", "has_files": True},
                {"document_id": "d2", "document_type_code": "code95", "status": "approved", "has_files": True},
            ],
        ),
        "tachograph_card": _approved_evidence(
            "tacho_any",
            [{"document_id": "t1", "document_type_code": "tacho_card", "status": "approved", "has_files": True}],
        ),
    }
    result = evaluate_requirement_rules(
        profile_view,
        context="readiness",
        normalized_payload={
            "recruitment.candidate.first_name": "Jan",
            "recruitment.candidate.last_name": "Kowalski",
            "recruitment.candidate.contacts.phone": "+48123456789",
        },
        documents=[],
        candidate_evidence_by_requirement=evidence,
    )
    assert result["satisfied"] is True


def test_requirement_rule_set_readiness_has_slot_rules() -> None:
    from backend.app.entity_profile.manifests.recruitment import recruitment_candidate_driver_ce_profile

    manifest = recruitment_candidate_driver_ce_profile()
    profile_view = {
        "entity_profile_code": manifest["profile_code"],
        "profile_code": manifest["profile_code"],
        "profile": manifest,
        "fields": manifest["fields"],
    }
    rule_set = build_requirement_rule_set(profile_view, context="readiness")
    slot_rules = [r for r in rule_set["rules"] if r["rule_type"] == "document_slot_required"]
    doc_rules = [r for r in rule_set["rules"] if r["rule_type"] == "document_required"]
    assert len(slot_rules) == 3
    assert doc_rules == []
