"""HR review document SoT: candidate hub files + recruiter profile fields."""

from __future__ import annotations

import pytest

from backend.app.services.hr_document_verification import build_fields_to_review
from backend.app.services.hr_review_document_resolution import (
    DOC_KEY_CANDIDATE_TYPES,
    merge_candidate_documents_into_approval_rows,
    pick_candidate_document_for_key,
)
from backend.app.services.workforce_hr_review import finalize_hr_review_can_approve


def test_legal_stay_maps_residence_card_doc_types() -> None:
    legal = DOC_KEY_CANDIDATE_TYPES["Legal stay"]
    assert "residence_card" in legal
    assert "karta_pobytu" in legal
    assert "residence_permit" in legal


def test_pick_candidate_document_for_key_residence_card() -> None:
    from backend.app.models.document import Document

    doc = Document(
        tenant_id="t1",
        candidate_id="c1",
        doc_type="residence_card",
        status="uploaded",
    )
    picked = pick_candidate_document_for_key({"residence_card": [doc]}, "Legal stay")
    assert picked is doc


def test_legacy_finalize_blocks_on_unverified_required_doc_without_hybrid_plan() -> None:
    """Non-hybrid: legacy documents_for_approval loop still gates approve (PR15)."""
    panel = {
        "status": "hr_review_in_progress",
        "failed_required_items": [],
        "blockers": [],
        "documents_for_approval": [
            {
                "document_key": "Legal stay",
                "required": True,
                "document_id": "d1",
                "verification_status": "pending",
            }
        ],
        "data_verification_summary": {"total": 1, "ready_for_approval": False},
    }
    assert finalize_hr_review_can_approve(panel) is False


def test_build_fields_to_review_shows_handoff_citizenship() -> None:
    fields = build_fields_to_review(
        "Legal stay",
        {
            "employee": {"display_name": "Jan Kowalski"},
            "snapshot": {},
            "document": {"expires_at": "2030-01-01"},
            "context": {},
            "eligibility": {"citizenship": "PL"},
            "handoff": {"candidate": {"citizenship": "UA", "full_name": "Jan Kowalski"}},
            "candidate": {"citizenship": "UA"},
        },
        None,
    )
    citizenship = next(f for f in fields if f["field_code"] == "citizenship")
    assert citizenship["current_profile_values"].get("handoff.candidate.citizenship") == "UA"
    assert citizenship["needs_manual_confirmation"] is False
