"""Handoff snapshot → HR verification profile namespace (PR11)."""

from backend.app.services.hr_document_verification import build_fields_to_review
from backend.app.services.hr_handoff_profile_context import build_handoff_profile_namespace


def test_build_handoff_profile_namespace_full_name_and_citizenship() -> None:
    ns = build_handoff_profile_namespace(
        {
            "candidate": {
                "name": {"first_name": "Sergii", "last_name": "Striushchenko"},
                "contacts": {"email": "s@example.com", "phone": "+48123456789"},
                "citizenship": "UA",
            }
        }
    )
    assert ns["candidate"]["full_name"] == "Sergii Striushchenko"
    assert ns["candidate"]["citizenship"] == "UA"
    assert ns["candidate"]["email"] == "s@example.com"


def test_build_fields_to_review_prefers_handoff_citizenship() -> None:
    handoff = build_handoff_profile_namespace(
        {"candidate": {"name": {"first_name": "A", "last_name": "B"}, "citizenship": "UA"}}
    )
    fields = build_fields_to_review(
        "Legal stay",
        {
            "handoff": handoff,
            "employee": {"display_name": "Other Name"},
            "snapshot": {"citizenship": "PL"},
            "document": {},
            "context": {},
            "eligibility": {"citizenship": "DE"},
        },
        None,
    )
    citizenship = next(f for f in fields if f["field_code"] == "citizenship")
    assert citizenship["current_profile_values"]["handoff.candidate.citizenship"] == "UA"
    assert citizenship["needs_manual_confirmation"] is False
