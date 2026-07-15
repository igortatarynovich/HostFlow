"""HR operational context after recruitment handoff: WorkforceHrCase + DocumentEntityLink (ADR-009 MVP)."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.document_entity_link import DocumentEntityLink
from backend.app.models.workforce_employee import WorkforceEmployee
from backend.app.models.workforce_hr_case import WorkforceHrCase
from backend.app.modules.documents import crud as documents_crud
from backend.app.modules.documents.crud import create_document_check
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


def _serialize_hr_case(row: WorkforceHrCase) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "tenant_id": str(row.tenant_id),
        "employee_id": str(row.employee_id),
        "source_candidate_id": str(row.source_candidate_id) if row.source_candidate_id else None,
        "status": str(row.status or "open"),
        "notes": row.notes,
        "meta": row.meta if isinstance(row.meta, dict) else {},
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def _serialize_document_link(row: DocumentEntityLink) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "document_id": str(row.document_id),
        "linked_entity_type": str(row.linked_entity_type),
        "linked_entity_id": str(row.linked_entity_id),
        "relation_type": str(row.relation_type),
        "module_key": row.module_key,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


async def _list_hr_document_links(
    db: AsyncSession,
    *,
    tenant_id: str,
    employee_id: str,
) -> list[DocumentEntityLink]:
    return list(
        (
            await db.execute(
                select(DocumentEntityLink).where(
                    DocumentEntityLink.tenant_id == str(tenant_id).strip(),
                    DocumentEntityLink.linked_entity_type == "workforce_employee",
                    DocumentEntityLink.linked_entity_id == str(employee_id).strip(),
                    DocumentEntityLink.relation_type == "reused_for_hr",
                )
            )
        ).scalars().all()
    )


async def get_hr_operational_context_bundle(
    db: AsyncSession,
    tenant_id: str,
    employee: WorkforceEmployee,
    *,
    lazy_backfill_links: bool = True,
) -> dict[str, Any]:
    """Return HR case + document links; lazy backfill links all candidate docs on read."""
    hr_case = await ensure_hr_operational_context(db, tenant_id, employee)
    cid = str(employee.candidate_id or "").strip() or None
    if lazy_backfill_links and cid:
        await ensure_hr_document_links(
            db,
            tenant_id=str(tenant_id).strip(),
            candidate_id=cid,
            linked_entity_type="workforce_employee",
            linked_entity_id=str(employee.id).strip(),
            document_ids=None,
        )
    links = await _list_hr_document_links(
        db,
        tenant_id=str(tenant_id).strip(),
        employee_id=str(employee.id).strip(),
    )
    return {
        "hr_case": _serialize_hr_case(hr_case),
        "document_links": [_serialize_document_link(link) for link in links],
    }


async def submit_employee_document_hr_review(
    db: AsyncSession,
    *,
    tenant_id: str,
    employee: WorkforceEmployee,
    document_id: str,
    reviewer_id: str | None,
    decision: str,
    comment: str | None = None,
    reason_code: str | None = None,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """HR-only document check lane: does not mutate Document.status."""
    decision_norm = str(decision or "").strip().lower()
    if decision_norm not in {"approved", "rejected"}:
        raise ValueError("INVALID_DECISION")

    tid = str(tenant_id).strip()
    did = str(document_id).strip()
    cid = str(employee.candidate_id or "").strip()
    if not cid:
        raise ValueError("EMPLOYEE_CANDIDATE_MISSING")

    await ensure_hr_operational_context(db, tid, employee)
    await ensure_hr_document_links(
        db,
        tenant_id=tid,
        candidate_id=cid,
        linked_entity_type="workforce_employee",
        linked_entity_id=str(employee.id).strip(),
        document_ids=None,
    )

    doc = await documents_crud.get_document(db, tid, did)
    if not doc:
        raise ValueError("DOCUMENT_NOT_FOUND")
    if str(getattr(doc, "candidate_id", "") or "").strip() != cid:
        raise ValueError("DOCUMENT_NOT_ACCESSIBLE")

    check_payload = {"review_module": "hr"}
    if isinstance(payload, dict):
        check_payload.update(payload)

    check = await create_document_check(
        db,
        tid,
        did,
        reviewer_id=reviewer_id,
        decision=decision_norm,
        reason_code=reason_code,
        comment=comment,
        payload=check_payload,
    )
    return {
        "id": str(check.id),
        "document_id": did,
        "decision": check.decision,
        "comment": check.comment,
        "reason_code": check.reason_code,
        "payload": check.payload if isinstance(check.payload, dict) else {},
        "reviewer_id": str(check.reviewer_id) if check.reviewer_id else None,
        "created_at": check.created_at.isoformat() if check.created_at else None,
    }
