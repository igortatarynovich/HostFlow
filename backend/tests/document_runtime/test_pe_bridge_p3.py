"""Document Runtime Engine P3 — Process Engine transition gate bridge tests."""

from __future__ import annotations

from datetime import date, timedelta

from backend.app.document_runtime.constants import DOCUMENT_RUNTIME_V1
from backend.app.document_runtime.pe_bridge import build_transition_gate_from_evaluation
from backend.app.entity_profile.manifests.recruitment import recruitment_candidate_driver_ce_profile
from backend.app.requirement_rules.evaluator import evaluate_requirement_rules
from backend.app.requirement_rules.transition_bridge import (
    TRANSITION_CONTEXT,
    map_requirement_evaluation_to_transition_gate,
    merge_transition_requirement_gate,
)

SOURCE_LAYER = "document_runtime"


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


def _payload_handoff_complete() -> dict:
    return {
        "recruitment.candidate.first_name": "Jan",
        "recruitment.candidate.last_name": "Kowalski",
        "recruitment.candidate.contacts.phone": "+48123456789",
        "recruitment.candidate.contacts.email": "jan@example.com",
        "platform.identity.address": "Warsaw",
    }


def _approved(doc_type: str, *, expires_on: str | None = None) -> dict:
    row = {"type": doc_type, "status": "approved", "has_files": True}
    if expires_on:
        row["expires_on"] = expires_on
    return row


def _handoff_documents(**overrides: dict) -> list[dict]:
    base = {
        "passport": _approved("passport"),
        "driver_license": _approved("driver_license"),
        "code95": _approved("code95"),
        "tacho_card": _approved("tacho_card"),
        "medical_certificate": _approved("medical_certificate"),
    }
    base.update(overrides)
    return list(base.values())


def _gate(documents: list[dict], *, payload: dict | None = None) -> dict:
    evaluation = evaluate_requirement_rules(
        _profile_view_from_manifest(),
        context=TRANSITION_CONTEXT,
        stage_code="ready_for_handoff",
        transition_code="ready_for_handoff_gate",
        normalized_payload=payload or _payload_handoff_complete(),
        documents=documents,
    )
    return map_requirement_evaluation_to_transition_gate(evaluation, documents=documents)


def _doc_reason(gate: dict, doc_type: str) -> dict:
    for row in gate["blocking_reasons"]:
        if row.get("document_type_code") == doc_type:
            return row
    raise AssertionError(f"No blocker for {doc_type}")


def test_p3_gate_includes_document_runtime_v1() -> None:
    gate = _gate([_approved("passport")])
    assert gate["document_runtime"]["evaluation_version"] == DOCUMENT_RUNTIME_V1
    assert "document_runtime" in gate["source_layers"]


def test_p3_approved_valid_allows_transition() -> None:
    future = (date.today() + timedelta(days=90)).isoformat()
    gate = _gate(_handoff_documents(passport=_approved("passport", expires_on=future)))
    assert gate["satisfied"] is True
    assert gate["blocking_reasons"] == []


def test_p3_missing_blocks_transition() -> None:
    gate = _gate([], payload=_payload_handoff_complete())
    assert gate["satisfied"] is False
    reason = _doc_reason(gate, "passport")
    assert reason["source_layer"] == SOURCE_LAYER
    assert reason["document_runtime"]["evaluation_version"] == DOCUMENT_RUNTIME_V1
    assert reason["lifecycle_status"] == "missing"


def test_p3_uploaded_blocks_transition() -> None:
    gate = _gate(
        _handoff_documents(
            passport={"type": "passport", "status": "uploaded", "has_files": True},
        )
    )
    assert gate["satisfied"] is False
    reason = _doc_reason(gate, "passport")
    assert reason["source_layer"] == SOURCE_LAYER
    assert reason["lifecycle_status"] == "uploaded"
    assert "passport" in gate["pending_documents"]


def test_p3_pending_review_blocks_transition() -> None:
    gate = _gate(
        _handoff_documents(
            passport={"type": "passport", "status": "submitted", "has_files": True},
        )
    )
    assert gate["satisfied"] is False
    reason = _doc_reason(gate, "passport")
    assert reason["lifecycle_status"] == "pending_review"


def test_p3_rejected_blocks_transition() -> None:
    gate = _gate(
        _handoff_documents(
            passport={"type": "passport", "status": "rejected", "has_files": True},
        )
    )
    assert gate["satisfied"] is False
    reason = _doc_reason(gate, "passport")
    assert reason["code"] == "document_rejected"
    assert reason["source_layer"] == SOURCE_LAYER
    assert "passport" in gate["problem_documents"]


def test_p3_expired_blocks_transition() -> None:
    past = (date.today() - timedelta(days=2)).isoformat()
    gate = _gate(_handoff_documents(passport=_approved("passport", expires_on=past)))
    assert gate["satisfied"] is False
    reason = _doc_reason(gate, "passport")
    assert reason["code"] == "document_expired"
    assert reason["source_layer"] == SOURCE_LAYER


def test_p3_expiring_soon_warning_not_blocker() -> None:
    soon = (date.today() + timedelta(days=14)).isoformat()
    gate = _gate(_handoff_documents(passport=_approved("passport", expires_on=soon)))
    assert gate["satisfied"] is True
    assert gate["blocking_reasons"] == []
    assert any(
        row.get("code") == "document_expiring_soon" and row.get("source_layer") == SOURCE_LAYER
        for row in gate["warnings"]
    )
    assert any(isinstance(row.get("document_runtime"), dict) for row in gate["warnings"])


def test_p3_merge_includes_document_runtime_on_report() -> None:
    gate = _gate([{"type": "passport", "status": "uploaded", "has_files": True}])
    merged = merge_transition_requirement_gate(
        {
            "transfer_allowed": True,
            "handoff_create_allowed": True,
            "blocking_reasons": [],
            "warnings": [],
            "source_layers": ["document_packs"],
        },
        gate,
    )
    assert merged["transfer_allowed"] is False
    assert "document_runtime" in merged["source_layers"]
    assert merged["document_runtime"]["evaluation_version"] == DOCUMENT_RUNTIME_V1
    assert merged["requirement_gate"]["document_runtime"]["evaluation_version"] == DOCUMENT_RUNTIME_V1
    assert any(row.get("source_layer") == SOURCE_LAYER for row in merged["blocking_reasons"])


def test_p3_build_transition_gate_preserves_field_blockers() -> None:
    evaluation = evaluate_requirement_rules(
        _profile_view_from_manifest(),
        context=TRANSITION_CONTEXT,
        stage_code="ready_for_handoff",
        transition_code="ready_for_handoff_gate",
        normalized_payload={"recruitment.candidate.first_name": "Jan"},
        documents=_handoff_documents(),
    )
    runtime_gate = build_transition_gate_from_evaluation(evaluation)
    assert runtime_gate["satisfied"] is False
    assert any(row.get("source_layer") == "requirement_engine" for row in runtime_gate["blocking_reasons"])
