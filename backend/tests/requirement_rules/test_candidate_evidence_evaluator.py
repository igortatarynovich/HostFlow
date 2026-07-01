"""Candidate Evidence evaluator status mapping."""

from __future__ import annotations

from backend.app.requirement_rules.slot_evaluator import evaluate_document_slot


def test_pending_review_is_not_fulfilled() -> None:
    result = evaluate_document_slot(
        "identity_document",
        candidate_evidence={
            "status": "pending_review",
            "evidence_variant_code": "identity_any",
            "documents": [
                {
                    "document_id": "doc-1",
                    "document_type_code": "passport",
                    "status": "approved",
                    "has_files": True,
                }
            ],
        },
    )
    assert result["status"] == "pending_verification"


def test_rejected_evidence_blocks_requirement() -> None:
    result = evaluate_document_slot(
        "identity_document",
        candidate_evidence={
            "status": "rejected",
            "evidence_variant_code": "identity_any",
            "documents": [],
        },
    )
    assert result["status"] == "missing"
    assert any("rejected" in str(b.get("code")) for b in result["blockers"])
