"""HR operational context after recruitment handoff: WorkforceHrCase + DocumentEntityLink (ADR-009 MVP)."""

from __future__ import annotations

from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.document_entity_link import DocumentEntityLink
from backend.app.models.workforce_employee import WorkforceEmployee
from backend.app.models.workforce_hr_case import WorkforceHrCase
from backend.app.services.document_hub_delivery_contract import (
    list_candidate_documents_via_contract,
)


async def _approved_fulfillment_document_ids(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate_id: str,
) -> set[str]:
    from backend.app.services.candidate_evidence_service import build_requirement_fulfillments_for_candidate

    fulfillments = await build_requirement_fulfillments_for_candidate(
        db,
        tenant_id=str(tenant_id).strip(),
        candidate_id=str(candidate_id).strip(),
    )
    ids: set[str] = set()
    for row in fulfillments or []:
        if not isinstance(row, dict):
            continue
        for doc in row.get("documents") or []:
            if not isinstance(doc, dict):
                continue
            did = str(doc.get("document_id") or "").strip()
            if did:
                ids.add(did)
    return ids


async def ensure_hr_operational_context(
    db: AsyncSession,
    tenant_id: str,
    employee: WorkforceEmployee,
) -> WorkforceHrCase:
    """Idempotent: one HR case per employee; link all active candidate documents to employee for HR reuse."""
    tid = str(tenant_id).strip()
    eid = str(employee.id).strip()
    row = (
        await db.execute(
            select(WorkforceHrCase).where(
                WorkforceHrCase.tenant_id == tid,
                WorkforceHrCase.employee_id == eid,
            )
        )
    ).scalar_one_or_none()

    cid = str(employee.candidate_id or "").strip() or None

    if row is None:
        row = WorkforceHrCase(
            id=str(uuid4()),
            tenant_id=tid,
            employee_id=eid,
            source_candidate_id=cid,
            status="open",
            meta={"source": "recruitment_handoff"},
        )
        db.add(row)
        await db.flush()
    elif cid and not (row.source_candidate_id or "").strip():
        row.source_candidate_id = cid
        await db.flush()

    if cid:
        fulfillment_doc_ids = await _approved_fulfillment_document_ids(
            db,
            tenant_id=tid,
            candidate_id=cid,
        )
        await ensure_hr_document_links(
            db,
            tenant_id=tid,
            candidate_id=cid,
            linked_entity_type="workforce_employee",
            linked_entity_id=eid,
            document_ids=sorted(fulfillment_doc_ids) if fulfillment_doc_ids else None,
        )

    from backend.app.services.workforce_hr_review import ensure_hr_review_for_employee

    await ensure_hr_review_for_employee(db, tid, employee)

    return row


async def ensure_hr_document_links(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate_id: str,
    linked_entity_type: str,
    linked_entity_id: str,
    document_ids: list[str] | None = None,
) -> None:
    """Idempotent links for candidate documents reused by HR surface.

    When ``document_ids`` is provided (from approved requirement fulfillments), only those
    documents are linked. Otherwise falls back to all active candidate documents (legacy).
    """
    tid = str(tenant_id).strip()
    cid = str(candidate_id).strip()
    etype = str(linked_entity_type).strip()
    eid = str(linked_entity_id).strip()
    if not (tid and cid and etype and eid):
        return

    if document_ids is not None:
        link_ids = [str(d).strip() for d in document_ids if str(d).strip()]
    else:
        docs = await list_candidate_documents_via_contract(
            db,
            tenant_id=tid,
            candidate_id=cid,
            include_deleted=False,
        )
        link_ids = [str(getattr(doc, "id", "") or "").strip() for doc in docs]
        link_ids = [did for did in link_ids if did]

    for did in link_ids:
        exists = (
            await db.execute(
                select(DocumentEntityLink.id).where(
                    DocumentEntityLink.tenant_id == tid,
                    DocumentEntityLink.document_id == did,
                    DocumentEntityLink.linked_entity_type == etype,
                    DocumentEntityLink.linked_entity_id == eid,
                    DocumentEntityLink.relation_type == "reused_for_hr",
                )
            )
        ).scalar_one_or_none()
        if exists:
            continue
        db.add(
            DocumentEntityLink(
                id=str(uuid4()),
                tenant_id=tid,
                document_id=did,
                linked_entity_type=etype,
                linked_entity_id=eid,
                relation_type="reused_for_hr",
                module_key="hr",
            )
        )
    await db.flush()
