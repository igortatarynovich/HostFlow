"""Requirement Rules Engine P1 — registry, evaluator, API."""

from __future__ import annotations

from backend.app.entity_profile.manifests.recruitment import recruitment_candidate_driver_ce_profile
from backend.app.requirement_rules.constants import RULE_TYPE_DOCUMENT_REQUIRED, RULE_TYPE_FIELD_REQUIRED
from backend.app.requirement_rules.evaluator import evaluate_requirement_rules
from backend.app.requirement_rules.manifests.recruitment import DOCUMENT_PACK_MANIFESTS
from backend.app.requirement_rules.registry import build_requirement_rule_set, get_document_pack_manifest


def _approved_evidence(variant_code: str, documents: list[dict]) -> dict:
    return {
        "status": "approved",
        "evidence_variant_code": variant_code,
        "documents": documents,
    }


def _driver_ce_evidence(*, separate_license: bool = False) -> dict[str, dict]:
    license_evidence = (
        _approved_evidence(
            "separate_documents",
            [
                {"document_id": "d1", "document_type_code": "driver_license", "status": "approved", "has_files": True},
                {"document_id": "d2", "document_type_code": "code95", "status": "approved", "has_files": True},
            ],
        )
        if separate_license
        else _approved_evidence(
            "combined_eu_license",
            [{"document_id": "d1", "document_type_code": "driver_license_code95", "status": "approved", "has_files": True}],
        )
    )
    return {
        "identity_document": _approved_evidence(
            "identity_any",
            [{"document_id": "p1", "document_type_code": "passport", "status": "approved", "has_files": True}],
        ),
        "driver_license_with_code95": license_evidence,
        "tachograph_card": _approved_evidence(
            "tacho_any",
            [{"document_id": "t1", "document_type_code": "tacho_card", "status": "approved", "has_files": True}],
        ),
    }


def _profile_view_from_manifest() -> dict:
    manifest = recruitment_candidate_driver_ce_profile()
    return {
        "entity_profile_code": manifest["profile_code"],
        "profile_code": manifest["profile_code"],
        "profile": {
            "profile_code": manifest["profile_code"],
            "entity_type": manifest["entity_type"],
            "document_pack_code": manifest["document_pack_code"],
            "process_profile_code": manifest["process_profile_code"],
        },
        "fields": manifest["fields"],
    }


def test_p1_document_pack_manifest_driver_ce() -> None:
    pack = get_document_pack_manifest("recruitment.driver_ce_documents")
    assert pack is not None
    slot_codes = {row["slot_code"] for row in pack["required_slots"]}
    assert slot_codes == {"identity_document", "driver_license_with_code95", "tachograph_card"}


def test_p1_rule_set_intake_fields_only_no_documents() -> None:
    rule_set = build_requirement_rule_set(_profile_view_from_manifest(), context="intake")
    field_rules = [r for r in rule_set["rules"] if r["rule_type"] == RULE_TYPE_FIELD_REQUIRED]
    doc_rules = [r for r in rule_set["rules"] if r["rule_type"] == RULE_TYPE_DOCUMENT_REQUIRED]
    assert len(field_rules) == 3
    assert {r["qualified_code"] for r in field_rules} == {
        "recruitment.candidate.first_name",
        "recruitment.candidate.last_name",
        "recruitment.candidate.contacts.phone",
    }
    assert doc_rules == []
    assert rule_set["p1_sources_only"] is True
    assert "process_profile" in rule_set["excluded_sources"]


def test_p1_rule_set_readiness_includes_document_pack() -> None:
    rule_set = build_requirement_rule_set(_profile_view_from_manifest(), context="readiness")
    slot_rules = [r for r in rule_set["rules"] if r["rule_type"] == "document_slot_required"]
    assert len(slot_rules) == 3
    sources = {item["source"] for item in rule_set["rule_sources_applied"]}
    assert sources == {"entity_profile", "document_pack"}


def test_p1_evaluator_reports_missing_fields_and_documents() -> None:
    result = evaluate_requirement_rules(
        _profile_view_from_manifest(),
        context="readiness",
        normalized_payload={"recruitment.candidate.first_name": "Jan"},
        documents=[{"type": "passport", "status": "uploaded", "has_files": True}],
    )
    assert result["satisfied"] is False
    missing_field_codes = {b.get("qualified_code") for b in result["blockers"] if b.get("qualified_code")}
    assert "recruitment.candidate.last_name" in missing_field_codes
    missing_doc_codes = {b.get("document_type_code") for b in result["blockers"] if b.get("document_type_code")}
    missing_slot_codes = {b.get("slot_code") for b in result["blockers"] if b.get("slot_code")}
    assert "driver_license_with_code95" in missing_slot_codes or "driver_license" in missing_doc_codes
    assert "passport" not in missing_doc_codes or "identity_document" in missing_slot_codes


def test_p1_evaluator_satisfied_when_complete() -> None:
    result = evaluate_requirement_rules(
        _profile_view_from_manifest(),
        context="readiness",
        normalized_payload={
            "recruitment.candidate.first_name": "Jan",
            "recruitment.candidate.last_name": "Kowalski",
            "recruitment.candidate.contacts.phone": "+48123456789",
        },
        documents=[],
        candidate_evidence_by_requirement=_driver_ce_evidence(separate_license=True),
    )
    assert result["satisfied"] is True
    assert result["blockers"] == []
    assert result["evaluation_version"] == "requirement_evaluation_v1"


def test_p1_document_pack_manifest_registry_complete() -> None:
    assert "recruitment.driver_ce_documents" in DOCUMENT_PACK_MANIFESTS
