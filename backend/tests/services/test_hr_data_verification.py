"""Tests for unified HR data verification read-model."""

from backend.app.services.hr_data_verification import (
    build_data_verification_items,
    summarize_data_verification,
)


def test_build_data_verification_items_dedupes_by_field_code() -> None:
    panel = {
        "documents_for_approval": [
            {
                "document_key": "Legal stay",
                "label": "Legal stay",
                "document_id": "doc-1",
                "open_url": "https://example/doc-1",
                "verification_status": "pending",
                "fields_to_review": [
                    {
                        "field_code": "citizenship",
                        "label": "Citizenship",
                        "downstream_use": ["work_permit"],
                        "current_profile_values": {"snapshot.citizenship": "UA"},
                        "confirmed": False,
                    },
                ],
            },
            {
                "document_key": "Work permit",
                "label": "Work permit",
                "document_id": "doc-2",
                "open_url": "https://example/doc-2",
                "fields_to_review": [
                    {
                        "field_code": "citizenship",
                        "label": "Citizenship",
                        "current_profile_values": {"eligibility.citizenship": "UA"},
                        "confirmed": False,
                    },
                ],
            },
        ],
        "verified_fields": [
            {
                "field_code": "citizenship",
                "field_label": "Citizenship",
                "status": "pending",
                "is_critical": True,
            }
        ],
    }
    items = build_data_verification_items(panel)
    citizenship = [i for i in items if i["field_code"] == "citizenship"]
    assert len(citizenship) == 1
    assert citizenship[0]["recruiter_value"] == "UA"
    assert citizenship[0]["source_document_type"] == "Legal stay"
    assert citizenship[0]["required_for_approval"] is True
    assert citizenship[0]["can_confirm"] is True


def test_summarize_data_verification_counts() -> None:
    items = [
        {"field_code": "a", "status": "verified", "required_for_approval": True},
        {"field_code": "b", "status": "pending", "required_for_approval": True},
        {"field_code": "c", "status": "missing", "required_for_approval": False},
    ]
    summary = summarize_data_verification(items, employment_identity={"status": "incomplete"})
    assert summary["total"] == 3
    assert summary["verified_count"] == 1
    assert summary["pending_count"] == 1
    assert summary["missing_count"] == 1
    assert summary["critical_total"] == 2
    assert summary["critical_verified"] == 1
    assert summary["identity_status"] == "incomplete"
