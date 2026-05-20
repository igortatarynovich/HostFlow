"""Role-based HR verification required fields."""

from backend.app.services.hr_data_verification import build_data_verification_items
from backend.app.services.hr_verification_requirements import (
    DRIVER_POSITION_CRITICAL_FIELD_CODES,
    resolve_critical_field_codes,
)


def test_resolve_critical_non_driver_excludes_transport() -> None:
    codes = resolve_critical_field_codes("warehouse")
    assert "driver_license_number" not in codes
    assert "tacho_card_expiry" not in codes
    assert "full_name" in codes


def test_resolve_critical_driver_includes_transport_and_exams() -> None:
    codes = resolve_critical_field_codes("driver")
    for code in DRIVER_POSITION_CRITICAL_FIELD_CODES:
        assert code in codes
    assert "full_name" in codes


def test_build_data_verification_items_driver_marks_transport_required() -> None:
    panel = {
        "position_category": "driver",
        "verification_critical_field_codes": sorted(resolve_critical_field_codes("driver")),
        "documents_for_approval": [
            {
                "document_key": "Tacho card",
                "label": "Tacho card",
                "document_id": "doc-t",
                "open_url": "https://example/tacho",
                "fields_to_review": [
                    {
                        "field_code": "tacho_card_number",
                        "label": "Tacho card number",
                        "current_profile_values": {"handoff.transport.tacho_card.number": "T-1"},
                        "confirmed": False,
                    },
                ],
            },
        ],
        "verified_fields": [],
    }
    items = build_data_verification_items(panel)
    tacho = next(i for i in items if i["field_code"] == "tacho_card_number")
    assert tacho["required_for_approval"] is True

    panel_non_driver = {
        "position_category": "office",
        "verification_critical_field_codes": sorted(resolve_critical_field_codes("office")),
        "documents_for_approval": panel["documents_for_approval"],
        "verified_fields": [],
    }
    items_office = build_data_verification_items(panel_non_driver)
    tacho_office = next(i for i in items_office if i["field_code"] == "tacho_card_number")
    assert tacho_office["required_for_approval"] is False
