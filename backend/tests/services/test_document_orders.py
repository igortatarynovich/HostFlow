"""Unit tests for document_orders (handoff / checklist parity with owner summary)."""

from __future__ import annotations

from types import SimpleNamespace

from backend.app.models.enums import DocumentStatus
from backend.app.services.document_orders import missing_base_requirements


def test_driver_license_satisfies_driver_license_code95_slot():
    checklist = {"requiredTypes": ["driver_license_code95"]}
    docs = [SimpleNamespace(doc_type="driver_license", status=DocumentStatus.approved)]
    assert missing_base_requirements(checklist, docs) == []


def test_driver_license_code95_doc_still_satisfies():
    checklist = {"requiredTypes": ["driver_license_code95"]}
    docs = [
        SimpleNamespace(doc_type="driver_license_code95", status=DocumentStatus.received)
    ]
    assert missing_base_requirements(checklist, docs) == []


def test_code95_alone_does_not_satisfy_combined_slot():
    checklist = {"requiredTypes": ["driver_license_code95"]}
    docs = [SimpleNamespace(doc_type="code95", status=DocumentStatus.approved)]
    assert missing_base_requirements(checklist, docs) == ["driver_license_code95"]


def test_verified_status_counts_ready_for_handoff_gate():
    checklist = {"requiredTypes": ["tacho_card"]}
    docs = [SimpleNamespace(doc_type="tacho_card", status=DocumentStatus.verified)]
    assert missing_base_requirements(checklist, docs) == []


def test_legacy_card_tacho_alias_counts_as_tacho_card():
    """DB/catalog legacy type string must normalize so handoff gate sees the document."""
    checklist = {"requiredTypes": ["tacho_card"]}
    docs = [SimpleNamespace(doc_type="card_tacho", status=DocumentStatus.approved)]
    assert missing_base_requirements(checklist, docs) == []


def test_last_check_approved_counts_ready_when_status_still_uploaded():
    """Parity with owner_summary._effective_status — gate must not lag behind UI."""
    checklist = {"requiredTypes": ["tacho_card", "driver_license_code95"]}
    docs = [
        SimpleNamespace(
            id="t1",
            doc_type="tacho_card",
            status=DocumentStatus.uploaded,
        ),
        SimpleNamespace(
            id="d1",
            doc_type="driver_license",
            status=DocumentStatus.in_progress,
        ),
    ]
    checks = {
        "t1": SimpleNamespace(decision="approved"),
        "d1": SimpleNamespace(decision="approved"),
    }
    assert missing_base_requirements(checklist, docs, last_check_by_document_id=checks) == []


def test_last_check_rejected_blocks_even_if_row_status_approved():
    checklist = {"requiredTypes": ["tacho_card"]}
    docs = [SimpleNamespace(id="t1", doc_type="tacho_card", status=DocumentStatus.approved)]
    checks = {"t1": SimpleNamespace(decision="rejected")}
    assert missing_base_requirements(checklist, docs, last_check_by_document_id=checks) == [
        "tacho_card"
    ]
