"""Handoff snapshot → HR verification profile namespace (PR11)."""

from backend.app.services.hr_document_verification import build_fields_to_review
from backend.app.services.hr_handoff_profile_context import (
    build_handoff_profile_namespace,
    merge_recruiter_transport_fields,
)


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


def test_merge_recruiter_transport_from_snapshot_and_candidate_extra() -> None:
    payload = {
        "candidate": {"name": {"first_name": "Jan", "last_name": "Kowalski"}},
        "documents": [
            {"type": "driver_license", "expires_at": "2030-01-15"},
            {"type": "code95", "expires_at": "2029-06-01"},
            {"type": "tachograph_card", "expires_at": "2028-12-31"},
        ],
    }
    base = build_handoff_profile_namespace(payload)
    ns = merge_recruiter_transport_fields(
        base,
        snapshot_payload=payload,
        candidate_extra={
            "license_number": "ABC123456",
            "license_categories": ["C", "CE"],
            "tacho_card_number": "TACHO-99",
        },
    )
    assert ns["transport"]["driver_license"]["number"] == "ABC123456"
    assert ns["transport"]["driver_license"]["categories"] == "C, CE"
    assert ns["transport"]["driver_license"]["expires_at"] == "2030-01-15"
    assert ns["transport"]["code95"]["expires_at"] == "2029-06-01"
    assert ns["transport"]["tacho_card"]["expires_at"] == "2028-12-31"
    assert ns["transport"]["tacho_card"]["number"] == "TACHO-99"


def test_build_fields_to_review_driver_license_uses_handoff_transport() -> None:
    handoff = merge_recruiter_transport_fields(
        build_handoff_profile_namespace({"candidate": {"name": {"first_name": "A", "last_name": "B"}}}),
        candidate_extra={"license_number": "DL-1", "license_categories": ["B", "C"]},
    )
    fields = build_fields_to_review(
        "Driver license",
        {
            "handoff": handoff,
            "employee": {},
            "snapshot": {},
            "document": {"meta": {"license_number": "DL-DOC"}},
            "context": {},
            "eligibility": {},
        },
        None,
    )
    lic_num = next(f for f in fields if f["field_code"] == "driver_license_number")
    assert lic_num["current_profile_values"]["handoff.transport.driver_license.number"] == "DL-1"
    cats = next(f for f in fields if f["field_code"] == "driver_license_categories")
    assert cats["current_profile_values"]["handoff.transport.driver_license.categories"] == "B, C"
