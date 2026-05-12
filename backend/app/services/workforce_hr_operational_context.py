"""HR operational context after recruitment handoff: WorkforceHrCase + DocumentEntityLink (ADR-009 MVP)."""

from __future__ import annotations

from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.document_entity_link import DocumentEntityLink
from backend.app.models.workforce_employee import WorkforceEmployee
from backend.app.models.workforce_hr_case import WorkforceHrCase
from backend.app.modules.documents import crud as documents_crud


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
        docs = await documents_crud.list_candidate_documents(
            db,
            tid,
            cid,
            include_deleted=False,
        )
        for doc in docs:
            did = str(getattr(doc, "id", "") or "").strip()
            if not did:
                continue
            exists = (
                await db.execute(
                    select(DocumentEntityLink.id).where(
                        DocumentEntityLink.tenant_id == tid,
                        DocumentEntityLink.document_id == did,
                        DocumentEntityLink.linked_entity_type == "workforce_employee",
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
                    linked_entity_type="workforce_employee",
                    linked_entity_id=eid,
                    relation_type="reused_for_hr",
                    module_key="hr",
                )
            )
        await db.flush()

    return row
