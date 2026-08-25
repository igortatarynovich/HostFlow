"""Document Hub Phase 2 slice: HR links prefer approved fulfillment document_ids."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import func, select

from backend.app.models import Candidate, Document
from backend.app.models.document_entity_link import DocumentEntityLink
from backend.app.models.enums import DocumentKind, DocumentRequestedFrom, DocumentStatus
from backend.app.services.workforce_hr_operational_context import ensure_hr_document_links

pytestmark = pytest.mark.anyio


async def test_ensure_hr_document_links_filters_to_explicit_document_ids(db, tenant_id: str) -> None:
    cid = str(uuid.uuid4())
    eid = str(uuid.uuid4())
    doc_linked = str(uuid.uuid4())
    doc_skipped = str(uuid.uuid4())

    db.add(
        Candidate(
            id=cid,
            tenant_id=tenant_id,
            first_name="Link",
            last_name="Filter",
            stage="ready_for_handoff",
            status="ready_for_handoff",
        )
    )
    for doc_id, number in ((doc_linked, "LINK-1"), (doc_skipped, "SKIP-2")):
        db.add(
            Document(
                id=doc_id,
                tenant_id=tenant_id,
                candidate_id=cid,
                kind=DocumentKind.driver,
                doc_type="passport",
                status=DocumentStatus.approved,
                requested_from=DocumentRequestedFrom.driver,
                meta={"extracted_fields": {"number": number, "country": "PL", "issued_at": "2020-01-01", "expires_at": "2030-01-01"}},
            )
        )
    await db.flush()

    await ensure_hr_document_links(
        db,
        tenant_id=tenant_id,
        candidate_id=cid,
        linked_entity_type="workforce_employee",
        linked_entity_id=eid,
        document_ids=[doc_linked],
    )
    await db.commit()

    rows = (
        await db.execute(
            select(DocumentEntityLink.document_id).where(
                DocumentEntityLink.tenant_id == tenant_id,
                DocumentEntityLink.linked_entity_id == eid,
            )
        )
    ).scalars().all()
    assert list(rows) == [doc_linked]

    count = (
        await db.execute(
            select(func.count())
            .select_from(DocumentEntityLink)
            .where(
                DocumentEntityLink.tenant_id == tenant_id,
                DocumentEntityLink.linked_entity_id == eid,
            )
        )
    ).scalar_one()
    assert int(count or 0) == 1
