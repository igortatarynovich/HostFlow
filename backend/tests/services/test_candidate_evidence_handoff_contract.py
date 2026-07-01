"""Handoff snapshot contract: requirement_fulfillments[] (Recruitment → HR boundary)."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

import pytest

from backend.app.models import CandidateHandoff, Document
from backend.app.models.enums import (
    CandidateEvidenceStatus,
    DocumentKind,
    DocumentProcessType,
    DocumentRequestedFrom,
    DocumentStatus,
)
from backend.app.services.candidate_evidence_service import (
    approve_evidence,
    build_requirement_fulfillments_for_candidate,
    link_document_to_evidence,
    select_evidence_variant,
)
from backend.app.services.handoff_snapshot import build_handoff_snapshot_payload_v1
from backend.tests.test_support.candidate_evidence_helpers import (
    assert_handoff_requirement_fulfillments_contract,
    setup_driver_ce_candidate,
)

pytestmark = pytest.mark.anyio


async def _seed_approved_identity_evidence(
    db,
    tenant_id: str,
    candidate_id: str,
    user_id: str,
    *,
    doc_meta: dict | None = None,
    expire_date: date | None = None,
) -> CandidateEvidence:
    doc = Document(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        candidate_id=candidate_id,
        kind=DocumentKind.driver,
        doc_type="passport",
        status=DocumentStatus.approved,
        requested_from=DocumentRequestedFrom.driver,
        process_type=DocumentProcessType.none,
        expire_date=expire_date,
        files=[{"name": "passport.pdf", "url": "/uploads/test/passport.pdf"}],
        meta=doc_meta or {"extracted_fields": {"passport_number": "AB123456"}},
    )
    db.add(doc)
    await db.flush()

    evidence = await select_evidence_variant(
        db,
        tenant_id=tenant_id,
        candidate_id=candidate_id,
        requirement_code="identity_document",
        evidence_variant_code="identity_any",
        user_id=user_id,
    )
    await link_document_to_evidence(
        db,
        tenant_id=tenant_id,
        evidence_id=str(evidence.id),
        document_id=str(doc.id),
        user_id=user_id,
    )
    return await approve_evidence(
        db,
        tenant_id=tenant_id,
        evidence_id=str(evidence.id),
        user_id=user_id,
    )


async def test_handoff_snapshot_includes_requirement_fulfillments(
    db,
    tenant_id: str,
    bootstrap: dict,
) -> None:
    candidate, _ = await setup_driver_ce_candidate(db, tenant_id)
    await _seed_approved_identity_evidence(
        db,
        tenant_id,
        str(candidate.id),
        bootstrap["admin_id"],
    )
    await db.commit()

    handoff = CandidateHandoff(
        id=str(uuid.uuid4()),
        agency_tenant_id=tenant_id,
        client_tenant_id=str(uuid.uuid4()),
        candidate_id=str(candidate.id),
        handoff_type="candidate_handoff",
        destination="hr",
        requested_by_user_id=bootstrap["admin_id"],
        requested_at=datetime.now(timezone.utc),
        status="pending",
    )

    payload = await build_handoff_snapshot_payload_v1(
        db,
        handoff=handoff,
        candidate=candidate,
    )

    fulfillments = payload.get("requirement_fulfillments")
    assert isinstance(fulfillments, list)
    assert_handoff_requirement_fulfillments_contract(fulfillments, min_count=1)

    identity = next(row for row in fulfillments if row["requirement_code"] == "identity_document")
    assert identity["evidence_variant_code"] == "identity_any"
    assert identity["requirement_public_name"]
    assert len(identity["documents"]) == 1
    doc_ref = identity["documents"][0]
    assert doc_ref["document_type_code"] == "passport"
    assert doc_ref["extracted_fields"]["passport_number"] == "AB123456"


async def test_build_requirement_fulfillments_excludes_rejected_and_superseded(
    db,
    tenant_id: str,
    bootstrap: dict,
) -> None:
    candidate, _ = await setup_driver_ce_candidate(db, tenant_id)
    user_id = bootstrap["admin_id"]
    cid = str(candidate.id)

    approved = await _seed_approved_identity_evidence(db, tenant_id, cid, user_id)
    await db.flush()

    rejected = await select_evidence_variant(
        db,
        tenant_id=tenant_id,
        candidate_id=cid,
        requirement_code="tachograph_card",
        evidence_variant_code="tacho_any",
        user_id=user_id,
    )
    from backend.app.services.candidate_evidence_service import reject_evidence

    await reject_evidence(
        db,
        tenant_id=tenant_id,
        evidence_id=str(rejected.id),
        user_id=user_id,
        reason="test reject",
    )

    superseded = await select_evidence_variant(
        db,
        tenant_id=tenant_id,
        candidate_id=cid,
        requirement_code="driver_license_with_code95",
        evidence_variant_code="combined_eu_license",
        user_id=user_id,
    )
    from backend.app.services.candidate_evidence_service import supersede_evidence

    await supersede_evidence(
        db,
        tenant_id=tenant_id,
        evidence=superseded,
        user_id=user_id,
        replacement_evidence_id=None,
    )
    await db.commit()

    fulfillments = await build_requirement_fulfillments_for_candidate(
        db,
        tenant_id=tenant_id,
        candidate_id=cid,
    )
    assert_handoff_requirement_fulfillments_contract(fulfillments, min_count=1)
    codes = {row["requirement_code"] for row in fulfillments}
    assert "identity_document" in codes
    assert "tachograph_card" not in codes
    assert "driver_license_with_code95" not in codes
    assert all(row["evidence_id"] == str(approved.id) for row in fulfillments if row["requirement_code"] == "identity_document")


async def test_empty_fulfillments_still_valid_contract(db, tenant_id: str) -> None:
    candidate, _ = await setup_driver_ce_candidate(db, tenant_id)
    fulfillments = await build_requirement_fulfillments_for_candidate(
        db,
        tenant_id=tenant_id,
        candidate_id=str(candidate.id),
    )
    assert fulfillments == []
    assert_handoff_requirement_fulfillments_contract(fulfillments, min_count=0)
