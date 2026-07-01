"""Negative cases: Candidate Evidence approval rules and fulfillment boundaries."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone

import pytest
from httpx import AsyncClient

from backend.app.models.candidate_evidence import CandidateEvidence, CandidateEvidenceDocument
from backend.app.models.document import Document
from backend.app.models.enums import (
    CandidateEvidenceStatus,
    DocumentKind,
    DocumentProcessType,
    DocumentRequestedFrom,
    DocumentStatus,
)
from backend.app.requirement_rules.slot_evaluator import evaluate_document_slot
from backend.app.services.candidate_evidence_service import (
    load_candidate_documents_snapshot,
    load_candidate_evidence_snapshots,
    select_evidence_variant,
    serialize_candidate_evidence,
    supersede_evidence,
)
from backend.tests.test_support.candidate_evidence_helpers import (
    checklist_item,
    get_checklist,
    link_evidence_document,
    post_document,
    select_evidence,
    setup_driver_ce_candidate,
)

pytestmark = pytest.mark.anyio


async def test_cannot_approve_without_required_documents(
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
        requirement_code="driver_license_with_code95",
        evidence_variant_code="separate_documents",
    )
    resp = await client.post(
        f"/api/v1/candidates/{candidate.id}/requirements/evidence/{evidence['evidence_id']}/approve",
        headers=manager_headers,
    )
    assert resp.status_code == 400, resp.text
    assert "Missing linked documents" in resp.text or "No linked document" in resp.text


async def test_cannot_approve_with_only_partial_all_of_documents(
    client: AsyncClient,
    manager_headers: dict[str, str],
    db,
    tenant_id: str,
) -> None:
    candidate, _ = await setup_driver_ce_candidate(db, tenant_id)
    license_id = await post_document(
        client,
        manager_headers,
        candidate_id=str(candidate.id),
        doc_type="driver_license",
    )
    evidence = await select_evidence(
        client,
        manager_headers,
        candidate_id=str(candidate.id),
        requirement_code="driver_license_with_code95",
        evidence_variant_code="separate_documents",
    )
    await link_evidence_document(
        client,
        manager_headers,
        candidate_id=str(candidate.id),
        evidence_id=evidence["evidence_id"],
        document_id=license_id,
    )
    resp = await client.post(
        f"/api/v1/candidates/{candidate.id}/requirements/evidence/{evidence['evidence_id']}/approve",
        headers=manager_headers,
    )
    assert resp.status_code == 400, resp.text


async def test_rejected_evidence_does_not_fulfill_requirement(
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
    reject = await client.post(
        f"/api/v1/candidates/{candidate.id}/requirements/evidence/{evidence['evidence_id']}/reject",
        headers=manager_headers,
        json={"reason": "wrong scan"},
    )
    assert reject.status_code == 200, reject.text

    checklist = await get_checklist(client, manager_headers, str(candidate.id))
    item = checklist_item(checklist, "identity_document")
    assert item["fulfilled"] is False
    assert item["evaluation"]["status"] == "missing"


async def test_superseded_evidence_does_not_fulfill_requirement(
    db,
    tenant_id: str,
    bootstrap: dict,
) -> None:
    candidate, _ = await setup_driver_ce_candidate(db, tenant_id)
    user_id = bootstrap["admin_id"]

    old = await select_evidence_variant(
        db,
        tenant_id=tenant_id,
        candidate_id=str(candidate.id),
        requirement_code="identity_document",
        evidence_variant_code="identity_any",
        user_id=user_id,
    )
    await supersede_evidence(
        db,
        tenant_id=tenant_id,
        evidence=old,
        user_id=user_id,
        replacement_evidence_id=None,
    )
    await db.commit()

    snapshots = await load_candidate_evidence_snapshots(
        db,
        tenant_id=tenant_id,
        candidate_id=str(candidate.id),
    )
    assert "identity_document" not in snapshots

    evaluation = evaluate_document_slot(
        "identity_document",
        candidate_evidence=serialize_candidate_evidence(old, []),
    )
    assert evaluation["status"] == "missing"


async def test_expired_linked_document_blocks_approve(
    client: AsyncClient,
    manager_headers: dict[str, str],
    db,
    tenant_id: str,
) -> None:
    candidate, _ = await setup_driver_ce_candidate(db, tenant_id)
    expired = (date.today() - timedelta(days=10)).isoformat()
    passport_id = await post_document(
        client,
        manager_headers,
        candidate_id=str(candidate.id),
        doc_type="passport",
        expires_at=expired,
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
    resp = await client.post(
        f"/api/v1/candidates/{candidate.id}/requirements/evidence/{evidence['evidence_id']}/approve",
        headers=manager_headers,
    )
    assert resp.status_code == 400, resp.text


async def test_approved_evidence_with_expired_document_not_satisfied(
    db,
    tenant_id: str,
    bootstrap: dict,
) -> None:
    candidate, _ = await setup_driver_ce_candidate(db, tenant_id)
    user_id = bootstrap["admin_id"]
    doc = Document(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        candidate_id=str(candidate.id),
        kind=DocumentKind.driver,
        doc_type="passport",
        status=DocumentStatus.approved,
        requested_from=DocumentRequestedFrom.driver,
        process_type=DocumentProcessType.none,
        expire_date=date.today() - timedelta(days=5),
    )
    db.add(doc)
    await db.flush()

    evidence = CandidateEvidence(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        candidate_id=str(candidate.id),
        requirement_code="identity_document",
        evidence_variant_code="identity_any",
        status=CandidateEvidenceStatus.approved.value,
        approved_by=user_id,
        approved_at=datetime.now(timezone.utc),
    )
    db.add(evidence)
    await db.flush()
    db.add(
        CandidateEvidenceDocument(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            candidate_evidence_id=str(evidence.id),
            document_id=str(doc.id),
            linked_by=user_id,
        )
    )
    await db.commit()

    doc_snapshots = await load_candidate_documents_snapshot(
        db,
        tenant_id=tenant_id,
        candidate_id=str(candidate.id),
    )
    linked = [row for row in doc_snapshots if str(row.get("document_id")) == str(doc.id)]
    payload = serialize_candidate_evidence(evidence, linked)
    evaluation = evaluate_document_slot("identity_document", candidate_evidence=payload)
    assert evaluation["status"] != "satisfied"
