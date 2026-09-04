"""Document Runtime Engine P2 — Document Hub consumer bridge tests."""

from __future__ import annotations

from datetime import date, timedelta

from backend.app.document_runtime.constants import DOCUMENT_RUNTIME_V1
from backend.app.document_runtime.hub_bridge import build_document_hub_runtime_checklist
from backend.app.entity_profile.constants import DRIVER_CE_PROFILE_CODE
from backend.app.entity_profile.manifests.recruitment import recruitment_candidate_driver_ce_profile
from backend.app.requirement_rules.document_hub_bridge import (
    apply_hub_requirements_to_checklist,
    map_requirement_evaluation_to_document_hub,
    merge_requirement_engine_into_owner_summary,
)
from backend.app.requirement_rules.evaluator import evaluate_requirement_rules
from backend.app.modules.documents.owner_summary import compute_owner_summary
from backend.app.services.document_ruleset import load_default_ruleset


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


def _approved(doc_type: str, *, expires_on: str | None = None) -> dict:
    row = {"type": doc_type, "status": "approved", "has_files": True}
    if expires_on:
        row["expires_on"] = expires_on
    return row


def _hub_for(documents: list[dict]) -> dict:
    evaluation = evaluate_requirement_rules(
        _profile_view_from_manifest(),
        context="readiness",
        normalized_payload={},
        documents=documents,
    )
    return map_requirement_evaluation_to_document_hub(evaluation, documents=documents)


def _item(hub: dict, doc_type: str) -> dict:
    for row in hub["document_runtime"]["items"]:
        if row["document_type_code"] == doc_type:
            return row
    raise AssertionError(f"Missing runtime item for {doc_type}")


def test_p2_hub_checklist_exposes_document_runtime_v1() -> None:
    hub = _hub_for([_approved("driver_qualification_card")])
    assert hub["document_runtime"]["evaluation_version"] == DOCUMENT_RUNTIME_V1
    assert hub["source_layers"] == ["document_runtime", "requirement_engine"]
    dqc = _item(hub, "driver_qualification_card")
    assert dqc["document_runtime"]["evaluation_version"] == DOCUMENT_RUNTIME_V1
    assert dqc["lifecycle_status"] == "approved"


def test_p2_approved_valid_satisfied() -> None:
    future = (date.today() + timedelta(days=120)).isoformat()
    hub = _hub_for([_approved("driver_qualification_card", expires_on=future)])
    item = _item(hub, "driver_qualification_card")
    assert item["satisfies_requirement"] is True
    assert item["status"] == "satisfied"
    assert item["expiry_status"] == "valid"
    assert item["blockers"] == []


def test_p2_uploaded_not_satisfied() -> None:
    hub = _hub_for([{"type": "driver_qualification_card", "status": "uploaded", "has_files": True}])
    item = _item(hub, "driver_qualification_card")
    assert item["satisfies_requirement"] is False
    assert item["status"] == "pending"
    assert item["lifecycle_status"] == "uploaded"


def test_p2_pending_review_not_satisfied() -> None:
    hub = _hub_for([{"type": "driver_qualification_card", "status": "submitted", "has_files": True}])
    item = _item(hub, "driver_qualification_card")
    assert item["satisfies_requirement"] is False
    assert item["lifecycle_status"] == "pending_review"
    assert item["status"] == "pending"


def test_p2_rejected_blocker() -> None:
    hub = _hub_for([{"type": "driver_qualification_card", "status": "rejected", "has_files": True}])
    item = _item(hub, "driver_qualification_card")
    assert item["satisfies_requirement"] is False
    assert item["status"] == "problem"
    assert any(row["code"] == "document_rejected" for row in item["blockers"])


def test_p2_expired_blocker() -> None:
    past = (date.today() - timedelta(days=3)).isoformat()
    hub = _hub_for([_approved("driver_qualification_card", expires_on=past)])
    item = _item(hub, "driver_qualification_card")
    assert item["satisfies_requirement"] is False
    assert item["status"] == "problem"
    assert any(row["code"] == "document_expired" for row in item["blockers"])


def test_p2_expiring_soon_warning_but_satisfied() -> None:
    soon = (date.today() + timedelta(days=10)).isoformat()
    hub = _hub_for([_approved("driver_qualification_card", expires_on=soon)])
    item = _item(hub, "driver_qualification_card")
    assert item["satisfies_requirement"] is True
    assert item["status"] == "satisfied"
    assert any(row["code"] == "document_expiring_soon" for row in item["warnings"])


def test_p2_missing_blocker() -> None:
    hub = _hub_for([])
    item = _item(hub, "driver_qualification_card")
    assert item["satisfies_requirement"] is False
    assert item["status"] == "missing"
    assert item["lifecycle_status"] == "missing"
    assert any(row["code"] == "document_missing" for row in item["blockers"])


def test_p2_best_instance_wins_over_weaker_duplicate() -> None:
    documents = [
        {"type": "driver_qualification_card", "status": "uploaded", "has_files": True, "document_id": "weak"},
        {"type": "driver_qualification_card", "status": "approved", "has_files": True, "document_id": "strong"},
    ]
    evaluation = evaluate_requirement_rules(
        _profile_view_from_manifest(),
        context="readiness",
        normalized_payload={},
        documents=documents,
    )
    checklist = build_document_hub_runtime_checklist(evaluation, documents=documents)
    dqc = next(row for row in checklist["items"] if row["document_type_code"] == "driver_qualification_card")
    assert dqc["document_id"] == "strong"
    assert dqc["satisfies_requirement"] is True


def test_p2_merge_owner_summary_includes_runtime_checklist() -> None:
    hub = _hub_for([{"type": "driver_qualification_card", "status": "uploaded", "has_files": True}])
    legacy = compute_owner_summary(
        {"position_category": "driver"},
        load_default_ruleset(),
        [{"type": "driver_qualification_card", "status": "uploaded"}],
    )
    merged = merge_requirement_engine_into_owner_summary(legacy, hub)
    assert merged["document_runtime"]["evaluation_version"] == DOCUMENT_RUNTIME_V1
    assert merged["checklist"]["runtimeItems"]
    assert merged["checklist"]["document_runtime"]["evaluation_version"] == DOCUMENT_RUNTIME_V1
    assert merged["required"]["ready_types"] == []
    assert "driver_qualification_card" in merged["required"]["in_progress_types"]


def test_p2_apply_hub_requirements_to_checklist() -> None:
    hub = _hub_for([_approved("driver_qualification_card")])
    checklist = apply_hub_requirements_to_checklist({"requiredTypes": []}, hub)
    assert checklist["requiredTypes"] == ["driver_qualification_card"]
    assert len(checklist["runtimeItems"]) == 1
    assert checklist["document_runtime"]["evaluation_version"] == DOCUMENT_RUNTIME_V1
