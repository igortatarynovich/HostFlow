"""ADR-014 Phase 2 — document open resolver unit tests."""

from __future__ import annotations

from backend.app.modules.documents.document_open_resolver import (
    DocumentOpenContext,
    document_visible_in_open_surface,
    resolve_document_open,
)


def test_hr_workforce_surface_allows_transport_and_recruitment_types() -> None:
    assert document_visible_in_open_surface("tacho_card", "hr_workforce_employee") is True
    assert document_visible_in_open_surface("residence_permit", "hr_workforce_employee") is True
    assert document_visible_in_open_surface("passport", "hr_workforce_employee") is True


def test_recruitment_surface_blocks_hr_only_medical() -> None:
    assert document_visible_in_open_surface("medical_certificate", "recruitment_candidate") is False
    assert document_visible_in_open_surface("passport", "recruitment_candidate") is True


def test_resolve_hr_workforce_open_url() -> None:
    decision = resolve_document_open(
        DocumentOpenContext(
            surface="hr_workforce_employee",
            tenant_id="t1",
            document_id="d1",
            workforce_employee_id="e1",
            doc_type="tacho_card",
        )
    )
    assert decision.allowed is True
    assert decision.file_route == "workforce_employee"
    assert decision.open_url == "/api/v1/workforce/employees/e1/documents/d1/file"
    assert decision.document_open_context == "hr_workforce_employee"


def test_resolve_recruitment_candidate_open_url() -> None:
    decision = resolve_document_open(
        DocumentOpenContext(
            surface="recruitment_candidate",
            tenant_id="t1",
            document_id="d1",
            candidate_id="c1",
            doc_type="passport",
        )
    )
    assert decision.allowed is True
    assert decision.file_route == "candidate"
    assert "/api/v1/candidates/c1/documents/d1/file" == decision.open_url


def test_resolve_hr_handoff_prefers_workforce_when_employee_known() -> None:
    decision = resolve_document_open(
        DocumentOpenContext(
            surface="hr_handoff_review",
            tenant_id="t1",
            document_id="d1",
            workforce_employee_id="e1",
            handoff_id="h1",
            doc_type="residence_permit",
        )
    )
    assert decision.allowed is True
    assert decision.file_route == "workforce_employee"
    assert "workforce/employees/e1" in (decision.open_url or "")
