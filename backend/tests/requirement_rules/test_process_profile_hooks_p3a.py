"""P3A — Process Profile hooks tests."""

from __future__ import annotations

from backend.app.entity_profile.manifests.recruitment import recruitment_candidate_driver_ce_profile
from backend.app.process_engine.manifests.recruitment import DEFAULT_PROFILE_CODE
from backend.app.requirement_rules.constants import (
    SOURCE_DOCUMENT_PACK,
    SOURCE_ENTITY_PROFILE,
    SOURCE_PROCESS_PROFILE,
    RULE_TYPE_DOCUMENT_REQUIRED,
    RULE_TYPE_FIELD_REQUIRED,
)
from backend.app.requirement_rules.evaluator import evaluate_requirement_rules
from backend.app.requirement_rules.process_profile_source import build_process_profile_rules
from backend.app.requirement_rules.registry import build_requirement_rule_set, merge_requirement_rules


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


def test_p3a_process_profile_rules_only_at_matching_stage() -> None:
    rules_handoff = build_process_profile_rules(
        process_profile_code=DEFAULT_PROFILE_CODE,
        context="transition",
        stage_code="ready_for_handoff",
        transition_code="ready_for_handoff_gate",
    )
    rules_other_stage = build_process_profile_rules(
        process_profile_code=DEFAULT_PROFILE_CODE,
        context="transition",
        stage_code="documents_received",
    )
    rules_no_stage = build_process_profile_rules(
        process_profile_code=DEFAULT_PROFILE_CODE,
        context="transition",
        stage_code=None,
    )

    assert rules_handoff
    assert rules_other_stage == []
    assert rules_no_stage == []

    field_codes = {row["qualified_code"] for row in rules_handoff if row["rule_type"] == RULE_TYPE_FIELD_REQUIRED}
    assert "recruitment.candidate.contacts.email" in field_codes
    assert "platform.identity.address" in field_codes
    assert "recruitment.candidate.contacts.phone" in field_codes

    rules_with_occupied = build_process_profile_rules(
        process_profile_code=DEFAULT_PROFILE_CODE,
        context="transition",
        stage_code="ready_for_handoff",
        occupied_field_targets={"recruitment.candidate.contacts.phone"},
        occupied_doc_targets=set(),
    )
    occupied_field_codes = {row["qualified_code"] for row in rules_with_occupied if row["rule_type"] == RULE_TYPE_FIELD_REQUIRED}
    assert "recruitment.candidate.contacts.phone" not in occupied_field_codes

    doc_codes = {row["document_type_code"] for row in rules_handoff if row["rule_type"] == RULE_TYPE_DOCUMENT_REQUIRED}
    assert doc_codes == {"medical_certificate"}


def test_p3a_merge_order_entity_profile_document_pack_process_profile() -> None:
    rule_set = build_requirement_rule_set(
        _profile_view_from_manifest(),
        context="transition",
        stage_code="ready_for_handoff",
        transition_code="ready_for_handoff_gate",
    )
    sources = [row["source"] for row in rule_set["rule_sources_applied"]]
    assert sources == [SOURCE_ENTITY_PROFILE, SOURCE_DOCUMENT_PACK, SOURCE_PROCESS_PROFILE]
    assert rule_set["p1_sources_only"] is False
    assert "process_profile" not in rule_set["excluded_sources"]
    assert rule_set["stage_code"] == "ready_for_handoff"
    assert rule_set["transition_code"] == "ready_for_handoff_gate"

    field_rules = [r for r in rule_set["rules"] if r["rule_type"] == RULE_TYPE_FIELD_REQUIRED]
    field_sources = {r["qualified_code"]: r["source"] for r in field_rules}
    assert field_sources["recruitment.candidate.contacts.email"] == SOURCE_PROCESS_PROFILE
    assert field_sources["platform.identity.address"] == SOURCE_PROCESS_PROFILE

    doc_rules = [r for r in rule_set["rules"] if r["rule_type"] == RULE_TYPE_DOCUMENT_REQUIRED]
    assert len(doc_rules) == 5
    assert {r["document_type_code"] for r in doc_rules} == {
        "passport",
        "driver_license",
        "code95",
        "tacho_card",
        "medical_certificate",
    }
    pack_doc = next(r for r in doc_rules if r["document_type_code"] == "passport")
    pe_doc = next(r for r in doc_rules if r["document_type_code"] == "medical_certificate")
    assert pack_doc["source"] == SOURCE_DOCUMENT_PACK
    assert pe_doc["source"] == SOURCE_PROCESS_PROFILE
    assert doc_rules.index(pack_doc) < doc_rules.index(pe_doc)


def test_p3a_merge_order_preserves_entity_profile_before_process_profile() -> None:
    profile_view = _profile_view_from_manifest()
    profile_view["fields"] = [
        {
            "qualified_code": "recruitment.candidate.first_name",
            "intake_level": "required",
            "card_save_level": "required",
            "transition_level": "required",
        }
    ]
    ep_rules = [
        {
            "rule_type": RULE_TYPE_FIELD_REQUIRED,
            "source": SOURCE_ENTITY_PROFILE,
            "qualified_code": "recruitment.candidate.first_name",
            "target": "recruitment.candidate.first_name",
        }
    ]
    pe_rules = build_process_profile_rules(
        process_profile_code=DEFAULT_PROFILE_CODE,
        context="transition",
        stage_code="ready_for_handoff",
        occupied_field_targets={"recruitment.candidate.first_name"},
    )
    merged = merge_requirement_rules(ep_rules, [], pe_rules)
    assert merged[0]["source"] == SOURCE_ENTITY_PROFILE
    assert all(r.get("qualified_code") != "recruitment.candidate.first_name" or r["source"] == SOURCE_ENTITY_PROFILE for r in merged)


def test_p3a_process_profile_does_not_override_canonical_targets() -> None:
    ep_rules = [
        {
            "rule_type": RULE_TYPE_FIELD_REQUIRED,
            "source": SOURCE_ENTITY_PROFILE,
            "qualified_code": "recruitment.candidate.contacts.phone",
            "target": "recruitment.candidate.contacts.phone",
        }
    ]
    pack_rules = [
        {
            "rule_type": RULE_TYPE_DOCUMENT_REQUIRED,
            "source": SOURCE_DOCUMENT_PACK,
            "document_type_code": "passport",
            "target": "passport",
        }
    ]
    pe_rules = build_process_profile_rules(
        process_profile_code=DEFAULT_PROFILE_CODE,
        context="transition",
        stage_code="ready_for_handoff",
        occupied_field_targets={"recruitment.candidate.contacts.phone"},
        occupied_doc_targets={"passport"},
    )
    merged = merge_requirement_rules(ep_rules, pack_rules, pe_rules)
    assert sum(1 for r in merged if r.get("qualified_code") == "recruitment.candidate.contacts.phone") == 1
    assert sum(1 for r in merged if r.get("document_type_code") == "passport") == 1
    assert all(r.get("source") != SOURCE_PROCESS_PROFILE or r.get("document_type_code") != "passport" for r in merged)


def test_p3a_stage_blocker_only_in_stage_context() -> None:
    evaluation = evaluate_requirement_rules(
        _profile_view_from_manifest(),
        context="transition",
        stage_code="ready_for_handoff",
        transition_code="ready_for_handoff_gate",
        normalized_payload={
            "recruitment.candidate.first_name": "Jan",
            "recruitment.candidate.last_name": "Kowalski",
            "recruitment.candidate.contacts.phone": "+48111222333",
        },
        documents=[
            {"type": "passport", "status": "uploaded"},
            {"type": "driver_license", "status": "uploaded"},
            {"type": "code95", "status": "uploaded"},
            {"type": "tacho_card", "status": "uploaded"},
        ],
    )
    missing_fields = {row.get("qualified_code") for row in evaluation["blockers"] if row.get("qualified_code")}
    missing_docs = {row.get("document_type_code") for row in evaluation["blockers"] if row.get("document_type_code")}
    assert "recruitment.candidate.contacts.email" in missing_fields
    assert "platform.identity.address" in missing_fields
    assert "medical_certificate" in missing_docs
    assert evaluation["process_profile_code"] == DEFAULT_PROFILE_CODE
    assert evaluation["stage_code"] == "ready_for_handoff"


def test_p3a_readiness_without_stage_keeps_p1_behavior() -> None:
    rule_set = build_requirement_rule_set(_profile_view_from_manifest(), context="readiness")
    assert rule_set["p1_sources_only"] is True
    assert "process_profile" in rule_set["excluded_sources"]
    sources = {row["source"] for row in rule_set["rule_sources_applied"]}
    assert sources == {SOURCE_ENTITY_PROFILE, SOURCE_DOCUMENT_PACK}

    evaluation = evaluate_requirement_rules(_profile_view_from_manifest(), context="readiness", normalized_payload={}, documents=[])
    assert evaluation["p1_sources_only"] is True
    assert evaluation.get("stage_code") is None
    pe_field_blockers = {
        row.get("qualified_code")
        for row in evaluation["blockers"]
        if row.get("qualified_code") in {"platform.identity.address", "recruitment.candidate.contacts.email"}
    }
    assert pe_field_blockers == set()
