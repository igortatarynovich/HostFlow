"""Unit tests for requirements workspace service helpers."""

from __future__ import annotations

from backend.app.services.requirements_workspace_service import (
    build_field_requirements_section,
    build_workspace_summary,
)


def test_build_field_requirements_section_marks_missing() -> None:
    evaluation = {
        "required_fields": [
            {"qualified_code": "platform.identity.address", "level": "blocking"},
            {"qualified_code": "recruitment.candidate.contacts.phone", "level": "blocking"},
        ],
        "blockers": [
            {"qualified_code": "platform.identity.address", "code": "field_required"},
        ],
    }
    payload = {"recruitment.candidate.contacts.phone": "+48111222333"}

    section = build_field_requirements_section(evaluation, normalized_payload=payload)
    assert section["missing_count"] == 1
    assert section["satisfied"] is False

    address = next(row for row in section["required_fields"] if row["qualified_code"] == "platform.identity.address")
    phone = next(row for row in section["required_fields"] if row["qualified_code"] == "recruitment.candidate.contacts.phone")
    assert address["satisfied"] is False
    assert phone["satisfied"] is True


def test_build_workspace_summary_combines_fields_and_slots() -> None:
    checklist = {
        "all_fulfilled": True,
        "requirements": [
            {"fulfilled": True, "evaluation": {"status": "satisfied"}},
            {"fulfilled": False, "evaluation": {"status": "not_applicable"}},
        ],
        "pipeline_blockers": {"unfulfilled_requirements": [], "pending_review_requirements": []},
    }
    field_requirements = {"required_fields": [{"satisfied": False}], "missing_count": 1, "satisfied": False}
    transfer_readiness = {"transfer_allowed": False}

    summary = build_workspace_summary(
        checklist=checklist,
        field_requirements=field_requirements,
        transfer_readiness=transfer_readiness,
    )
    assert summary["all_fulfilled"] is False
    assert summary["handoff_ready"] is False
    assert summary["blocking_open_count"] == 1
