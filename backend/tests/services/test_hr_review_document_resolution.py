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


def test_legal_stay_maps_passport_doc_type() -> None:
    assert "passport" in DOC_KEY_CANDIDATE_TYPES["Legal stay"]
    assert "national_id" in DOC_KEY_CANDIDATE_TYPES["Legal stay"]


def test_finalize_can_approve_false_when_required_doc_unverified() -> None:
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
