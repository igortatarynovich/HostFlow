"""HR document verification card logic (PR3)."""

from __future__ import annotations

from backend.app.services.hr_document_verification import (
    VERIFICATION_NOT_REQUIRED,
    VERIFICATION_VERIFIED,
    build_fields_to_review,
    document_required_for_position,
    verification_blocks_approval,
)
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
