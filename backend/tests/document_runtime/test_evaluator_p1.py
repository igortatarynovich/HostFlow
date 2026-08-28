"""Document Runtime Engine P1 — evaluator and Readiness integration tests."""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from backend.app.document_runtime.constants import DOCUMENT_RUNTIME_V1
from backend.app.document_runtime.evaluator import evaluate_document_runtime
from backend.app.entity_profile.manifests.recruitment import recruitment_candidate_driver_ce_profile
from backend.app.requirement_rules.evaluator import evaluate_requirement_rules


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


def _approved_doc(doc_type: str, *, expires_on: str | None = None) -> dict:
    row: dict = {
        "document_type_code": doc_type,
        "type": doc_type,
        "status": "approved",
        "has_files": True,
    }
    if expires_on:
        row["expires_on"] = expires_on
    return row


def test_runtime_missing_document() -> None:
    runtime = evaluate_document_runtime(None, document_type_code="passport")
    assert runtime["evaluation_version"] == DOCUMENT_RUNTIME_V1
    assert runtime["workflow_status"] == "missing"
    assert runtime["satisfies_requirement"] is False
    assert runtime["runtime_signal"] == "missing"
    assert any(row["code"] == "document_missing" for row in runtime["blockers"])


def test_runtime_approved_valid() -> None:
    future = (date.today() + timedelta(days=120)).isoformat()
    runtime = evaluate_document_runtime(
        _approved_doc("passport", expires_on=future),
        document_type_code="passport",
    )
    assert runtime["workflow_status"] == "approved"
    assert runtime["expiry_status"] == "valid"
    assert runtime["satisfies_requirement"] is True
    assert runtime["blockers"] == []


def test_runtime_uploaded_not_satisfied() -> None:
    runtime = evaluate_document_runtime(
        {"document_type_code": "passport", "status": "uploaded", "has_files": True},
        document_type_code="passport",
    )
    assert runtime["workflow_status"] == "uploaded"
    assert runtime["satisfies_requirement"] is False
    assert runtime["runtime_signal"] == "pending_verification"
    assert any(row["code"] == "document_pending_verification" for row in runtime["warnings"])


def test_runtime_file_present_overrides_missing_status() -> None:
    runtime = evaluate_document_runtime(
        {"document_type_code": "passport", "status": "missing", "has_files": True},
        document_type_code="passport",
    )
    assert runtime["workflow_status"] == "uploaded"
    assert runtime["runtime_signal"] == "pending_verification"
    assert runtime["satisfies_requirement"] is False


def test_runtime_approved_without_file_is_missing() -> None:
    runtime = evaluate_document_runtime(
        {"document_type_code": "passport", "status": "approved", "has_files": False},
        document_type_code="passport",
    )
    assert runtime["workflow_status"] == "missing"
    assert runtime["runtime_signal"] == "missing"
    assert runtime["satisfies_requirement"] is False


def test_runtime_pending_review_not_satisfied() -> None:
    runtime = evaluate_document_runtime(
        {"document_type_code": "passport", "status": "submitted", "has_files": True},
        document_type_code="passport",
    )
    assert runtime["workflow_status"] == "pending_review"
    assert runtime["satisfies_requirement"] is False


def test_runtime_rejected_blocker() -> None:
    runtime = evaluate_document_runtime(
        {"document_type_code": "passport", "status": "rejected", "has_files": True},
        document_type_code="passport",
    )
    assert runtime["workflow_status"] == "rejected"
    assert runtime["satisfies_requirement"] is False
    assert any(row["code"] == "document_rejected" for row in runtime["blockers"])


def test_runtime_expired_blocker() -> None:
    past = (date.today() - timedelta(days=5)).isoformat()
    runtime = evaluate_document_runtime(
        _approved_doc("passport", expires_on=past),
        document_type_code="passport",
        reference_date=date.today(),
    )
    assert runtime["expiry_status"] == "expired"
    assert runtime["satisfies_requirement"] is False
    assert any(row["code"] == "document_expired" for row in runtime["blockers"])


def test_runtime_expiring_soon_warning_but_satisfied() -> None:
    soon = (date.today() + timedelta(days=10)).isoformat()
    runtime = evaluate_document_runtime(
        _approved_doc("passport", expires_on=soon),
        document_type_code="passport",
        reference_date=date.today(),
        expiring_soon_days=30,
    )
    assert runtime["expiry_status"] == "expiring_soon"
    assert runtime["satisfies_requirement"] is True
    assert any(row["code"] == "document_expiring_soon" for row in runtime["warnings"])


def test_runtime_no_expiry_when_optional() -> None:
    runtime = evaluate_document_runtime(
        _approved_doc("passport"),
        document_type_code="passport",
    )
    assert runtime["expiry_status"] == "no_expiry"
    assert runtime["satisfies_requirement"] is True


def test_requirement_evaluator_uses_document_runtime_v1() -> None:
    result = evaluate_requirement_rules(
        _profile_view_from_manifest(),
        context="readiness",
        normalized_payload={
            "recruitment.candidate.first_name": "Jan",
            "recruitment.candidate.last_name": "Kowalski",
            "recruitment.candidate.contacts.phone": "+48123456789",
        },
        documents=[
            _approved_doc("passport"),
            _approved_doc("driver_license"),
            _approved_doc("code95"),
            _approved_doc("tacho_card"),
        ],
    )
    assert result["satisfied"] is True
    runtime_section = result.get("document_runtime") or {}
    assert runtime_section.get("evaluation_version") == DOCUMENT_RUNTIME_V1
    assert runtime_section.get("evaluated_count") == 4
    assert all(row.get("satisfies_requirement") for row in runtime_section.get("documents") or [])


def test_requirement_evaluator_uploaded_is_not_satisfied() -> None:
    result = evaluate_requirement_rules(
        _profile_view_from_manifest(),
        context="readiness",
        normalized_payload={
            "recruitment.candidate.first_name": "Jan",
            "recruitment.candidate.last_name": "Kowalski",
            "recruitment.candidate.contacts.phone": "+48123456789",
        },
        documents=[
            {"document_type_code": "passport", "status": "uploaded", "has_files": True},
            _approved_doc("driver_license"),
            _approved_doc("code95"),
            _approved_doc("tacho_card"),
        ],
    )
    assert result["satisfied"] is False
    doc_blockers = [
        row for row in result["blockers"] if row.get("document_type_code") == "passport"
    ]
    assert doc_blockers
    assert doc_blockers[0].get("source_layer") == "document_runtime"


def test_requirement_evaluator_rejected_and_expired_blockers() -> None:
    past = (date.today() - timedelta(days=1)).isoformat()
    result = evaluate_requirement_rules(
        _profile_view_from_manifest(),
        context="readiness",
        normalized_payload={
            "recruitment.candidate.first_name": "Jan",
            "recruitment.candidate.last_name": "Kowalski",
            "recruitment.candidate.contacts.phone": "+48123456789",
        },
        documents=[
            _approved_doc("passport", expires_on=past),
            {"document_type_code": "driver_license", "status": "rejected", "has_files": True},
            _approved_doc("code95"),
            _approved_doc("tacho_card"),
        ],
    )
    assert result["satisfied"] is False
    codes = {row.get("document_type_code") for row in result["blockers"]}
    assert "passport" in codes
    assert "driver_license" in codes
