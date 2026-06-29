"""HR document verification card logic (PR3)."""

from __future__ import annotations

from backend.app.services.hr_document_verification import (
    VERIFICATION_NOT_REQUIRED,
    VERIFICATION_VERIFIED,
    build_fields_to_review,
    document_required_for_position,
    verification_blocks_approval,
)
from backend.app.services.hr_profile_address import promote_address_fields
from backend.app.models.workforce_hr_document_verification import WorkforceHrDocumentVerification


def test_build_fields_to_review_manual_when_empty_profile() -> None:
    fields = build_fields_to_review(
        "Legal stay",
        {
            "employee": {"display_name": "Jan Kowalski"},
            "snapshot": {},
            "document": {},
            "context": {},
            "eligibility": {},
        },
        None,
    )
    assert len(fields) >= 1
    citizenship = next((f for f in fields if f["field_code"] == "citizenship"), None)
    assert citizenship is not None
    assert citizenship["needs_manual_confirmation"] is True


def test_optional_transport_docs_not_required_for_non_driver() -> None:
    assert document_required_for_position("Code95", "office") is False
    assert document_required_for_position("Code95", "driver") is True
    assert document_required_for_position("Legal stay", "office") is True


def test_verification_blocks_approval_skips_optional_missing() -> None:
    v = WorkforceHrDocumentVerification(
        tenant_id="t1",
        hr_review_id="r1",
        document_key="Code95",
        checklist_item_code="documents_uploaded",
        required=False,
        verification_status=VERIFICATION_NOT_REQUIRED,
    )
    legal = WorkforceHrDocumentVerification(
        tenant_id="t1",
        hr_review_id="r1",
        document_key="Legal stay",
        checklist_item_code="legal_stay_verified",
        required=True,
        verification_status=VERIFICATION_VERIFIED,
    )
    blocked = verification_blocks_approval(
        [legal, v],
        [
            {"document_key": "Legal stay", "status": "verified", "document_id": "d1"},
            {"document_key": "Code95", "status": "missing"},
        ],
    )
    assert blocked is False


def test_build_fields_to_review_passport_fields() -> None:
    fields = build_fields_to_review(
        "Passport / ID",
        {
            "employee": {
                "display_name": "Jan Kowalski",
                "meta": {"personal_data": {"birth_date": "1990-01-15", "passport_number": "AB123456"}},
            },
            "snapshot": {
                "birth_date": "1990-01-15",
                "passport_number": "AB123456",
                "passport_series": "AAA",
            },
            "document": {
                "number": "AB123456",
                "issue_date": "2020-05-01",
                "expires_at": "2030-05-01",
                "meta": {"series": "AAA"},
            },
            "context": {},
            "eligibility": {"citizenship": "UA"},
        },
        None,
    )
    codes = {f["field_code"] for f in fields}
    assert "birth_date" in codes
    assert "document_series" in codes
    assert "document_number" in codes
    assert "document_issue_date" in codes
    birth = next(f for f in fields if f["field_code"] == "birth_date")
    assert birth["needs_manual_confirmation"] is False
    assert "1990-01-15" in str(birth["current_profile_values"])


def test_build_fields_to_review_contacts_block() -> None:
    snapshot: dict[str, object] = {"email": "jan@example.com"}
    promote_address_fields(
        snapshot,
        {
            "country": "PL",
            "city": "Warsaw",
            "street": "Marszałkowska",
            "house": "10",
            "zip": "00-001",
        },
    )
    fields = build_fields_to_review(
        "Contacts & address",
        {
            "employee": {"display_name": "Jan Kowalski", "meta": {"personal_data": {"phone": "+48123456789"}}},
            "snapshot": {
                "email": "jan@example.com",
                **snapshot,
            },
            "contacts": {"phone": "+48123456789"},
            "handoff": {"candidate": {"email": "jan@example.com", "phone": "+48123456789"}},
            "document": {},
            "context": {},
            "eligibility": {},
        },
        None,
    )
    codes = {f["field_code"] for f in fields}
    assert "phone" in codes
    assert "email" in codes
    assert "address_country" in codes
    assert "address_street" in codes
    country = next(f for f in fields if f["field_code"] == "address_country")
    assert country["input_type"] == "country"
    assert "PL" in str(country["current_profile_values"])
    street = next(f for f in fields if f["field_code"] == "address_street")
    assert "Marszałkowska" in str(street["current_profile_values"])


def test_data_only_keys_constant() -> None:
    from backend.app.services.hr_verified_field_catalog import (
        DATA_ONLY_VERIFICATION_KEYS,
        OPTIONAL_FILE_VERIFICATION_KEYS,
    )

    assert "Contacts & address" in DATA_ONLY_VERIFICATION_KEYS
    assert "Work experience" in OPTIONAL_FILE_VERIFICATION_KEYS


def test_verification_blocks_approval_until_verified() -> None:
    v = WorkforceHrDocumentVerification(
        tenant_id="t1",
        hr_review_id="r1",
        document_key="Legal stay",
        checklist_item_code="legal_stay_verified",
        verification_status="pending",
    )
    blocked = verification_blocks_approval(
        [v],
        [{"document_key": "Legal stay", "status": "uploaded", "document_id": "d1"}],
    )
    assert blocked is True
    v.verification_status = VERIFICATION_VERIFIED
    assert (
        verification_blocks_approval(
            [v],
            [{"document_key": "Legal stay", "status": "verified", "document_id": "d1"}],
        )
        is False
    )
