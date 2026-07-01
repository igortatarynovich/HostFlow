"""API integration: Candidate Evidence workflow (Recruitment confirms requirements)."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select, text

from backend.app.db.session import async_session_maker
from backend.app.models.candidate_evidence import CandidateEvidence
from backend.app.models.enums import CandidateEvidenceStatus
from backend.app.models.recruitment_application import RecruitmentApplication
from backend.tests.conftest import _set_tenant
from backend.tests.test_support.candidate_evidence_helpers import (
    DRIVER_CE_REQUIREMENTS,
    approve_evidence_api,
    checklist_item,
    get_checklist,
    link_evidence_document,
    post_document,
    replace_evidence_api,
    select_evidence,
    setup_driver_ce_candidate,
)

pytestmark = pytest.mark.anyio


async def test_checklist_shows_missing_without_evidence(
    client: AsyncClient,
    manager_headers: dict[str, str],
    db,
    tenant_id: str,
) -> None:
    candidate, _company_id = await setup_driver_ce_candidate(db, tenant_id)
    checklist = await get_checklist(client, manager_headers, str(candidate.id))

    assert checklist["candidate_id"] == str(candidate.id)
    assert checklist["all_fulfilled"] is False
    codes = {item["requirement_code"] for item in checklist["requirements"]}
    assert codes == set(DRIVER_CE_REQUIREMENTS)

    identity = checklist_item(checklist, "identity_document")
    assert identity["candidate_evidence"] is None
    assert identity["fulfilled"] is False
    assert identity["evaluation"]["status"] == "missing"


async def test_select_evidence_sets_selected_status(
    client: AsyncClient,
    manager_headers: dict[str, str],
    db,
    tenant_id: str,
) -> None:
    candidate, _ = await setup_driver_ce_candidate(db, tenant_id)
    evidence = await select_evidence(
        client,
        manager_headers,
        candidate_id=str(candidate.id),
        requirement_code="identity_document",
        evidence_variant_code="identity_any",
    )
    assert evidence["status"] == CandidateEvidenceStatus.selected.value
    assert evidence["evidence_variant_code"] == "identity_any"
    assert evidence["requirement_code"] == "identity_document"

    checklist = await get_checklist(client, manager_headers, str(candidate.id))
    item = checklist_item(checklist, "identity_document")
    assert item["candidate_evidence"]["status"] == CandidateEvidenceStatus.selected.value
    assert item["evaluation"]["status"] == "pending_evidence"
    assert item["fulfilled"] is False


async def test_link_document_moves_to_pending_review(
    client: AsyncClient,
    manager_headers: dict[str, str],
    db,
    tenant_id: str,
) -> None:
    candidate, _ = await setup_driver_ce_candidate(db, tenant_id)
    passport_id = await post_document(
        client,
        manager_headers,
        candidate_id=str(candidate.id),
        doc_type="passport",
    )
    evidence = await select_evidence(
        client,
        manager_headers,
        candidate_id=str(candidate.id),
        requirement_code="identity_document",
        evidence_variant_code="identity_any",
    )
    await link_evidence_document(
        client,
        manager_headers,
        candidate_id=str(candidate.id),
        evidence_id=evidence["evidence_id"],
        document_id=passport_id,
    )

    checklist = await get_checklist(client, manager_headers, str(candidate.id))
    item = checklist_item(checklist, "identity_document")
    assert item["candidate_evidence"]["status"] == CandidateEvidenceStatus.pending_review.value
    assert item["evaluation"]["status"] == "pending_verification"
    assert item["fulfilled"] is False


async def test_approve_evidence_marks_requirement_fulfilled(
    client: AsyncClient,
    manager_headers: dict[str, str],
    db,
    tenant_id: str,
) -> None:
    candidate, _ = await setup_driver_ce_candidate(db, tenant_id)
    passport_id = await post_document(
        client,
        manager_headers,
        candidate_id=str(candidate.id),
        doc_type="passport",
    )
    evidence = await select_evidence(
        client,
        manager_headers,
        candidate_id=str(candidate.id),
        requirement_code="identity_document",
        evidence_variant_code="identity_any",
    )
    await link_evidence_document(
        client,
        manager_headers,
        candidate_id=str(candidate.id),
        evidence_id=evidence["evidence_id"],
        document_id=passport_id,
    )
    approved = await approve_evidence_api(
        client,
        manager_headers,
        candidate_id=str(candidate.id),
        evidence_id=evidence["evidence_id"],
    )
    assert approved["status"] == CandidateEvidenceStatus.approved.value

    checklist = await get_checklist(client, manager_headers, str(candidate.id))
    item = checklist_item(checklist, "identity_document")
    assert item["fulfilled"] is True
    assert item["evaluation"]["status"] == "satisfied"
    assert item["candidate_evidence"]["status"] == CandidateEvidenceStatus.approved.value


async def test_replace_evidence_supersedes_previous_row(
    client: AsyncClient,
    manager_headers: dict[str, str],
    db,
    tenant_id: str,
) -> None:
    candidate, _ = await setup_driver_ce_candidate(db, tenant_id)
    passport_id = await post_document(
        client,
        manager_headers,
        candidate_id=str(candidate.id),
        doc_type="passport",
    )
    national_id = await post_document(
        client,
        manager_headers,
        candidate_id=str(candidate.id),
        doc_type="national_id",
    )

    first = await select_evidence(
        client,
        manager_headers,
        candidate_id=str(candidate.id),
        requirement_code="identity_document",
        evidence_variant_code="identity_any",
    )
    await link_evidence_document(
        client,
        manager_headers,
        candidate_id=str(candidate.id),
        evidence_id=first["evidence_id"],
        document_id=passport_id,
    )
    await approve_evidence_api(
        client,
        manager_headers,
        candidate_id=str(candidate.id),
        evidence_id=first["evidence_id"],
    )

    replacement = await replace_evidence_api(
        client,
        manager_headers,
        candidate_id=str(candidate.id),
        requirement_code="identity_document",
        evidence_variant_code="identity_any",
    )
    assert replacement["evidence_id"] != first["evidence_id"]
    assert replacement["status"] == CandidateEvidenceStatus.selected.value

    async with async_session_maker() as session:
        await _set_tenant(session, tenant_id)
        old_row = await session.get(CandidateEvidence, first["evidence_id"])
        assert old_row is not None
        assert old_row.status == CandidateEvidenceStatus.superseded.value
        assert str(old_row.superseded_by_evidence_id) == replacement["evidence_id"]

        active_rows = (
            await session.execute(
                select(CandidateEvidence).where(
                    CandidateEvidence.tenant_id == tenant_id,
                    CandidateEvidence.candidate_id == str(candidate.id),
                    CandidateEvidence.requirement_code == "identity_document",
                    CandidateEvidence.status.in_(
                        [
                            CandidateEvidenceStatus.selected.value,
                            CandidateEvidenceStatus.pending_review.value,
                            CandidateEvidenceStatus.approved.value,
                        ]
                    ),
                )
            )
        ).scalars().all()
        assert len(active_rows) == 1
        assert str(active_rows[0].id) == replacement["evidence_id"]

    await link_evidence_document(
        client,
        manager_headers,
        candidate_id=str(candidate.id),
        evidence_id=replacement["evidence_id"],
        document_id=national_id,
    )


async def test_handoff_lock_blocks_evidence_mutations(
    client: AsyncClient,
    recruiter_headers: dict[str, str],
    db,
    tenant_id: str,
    bootstrap: dict,
) -> None:
    candidate, _ = await setup_driver_ce_candidate(db, tenant_id)
    app_id = str(uuid.uuid4())
    try:
        async with async_session_maker() as session:
            await _set_tenant(session, tenant_id)
            session.add(
                RecruitmentApplication(
                    id=app_id,
                    tenant_id=tenant_id,
                    candidate_id=str(candidate.id),
                    status="handed_off",
                    recruiter_id=bootstrap["recruiter_id"],
                )
            )
            await session.commit()

        resp = await client.post(
            f"/api/v1/candidates/{candidate.id}/requirements/identity_document/select-evidence",
            headers=recruiter_headers,
            json={"evidence_variant_code": "identity_any"},
        )
        assert resp.status_code == 403, resp.text
        assert "Recruitment locked" in resp.text
    finally:
        async with async_session_maker() as session:
            await _set_tenant(session, tenant_id)
            await session.execute(
                text("DELETE FROM recruitment_applications WHERE id = :id"),
                {"id": app_id},
            )
            await session.commit()
