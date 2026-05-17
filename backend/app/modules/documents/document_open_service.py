"""Apply ``resolve_document_open`` to API payloads and emit open audit events."""

from __future__ import annotations

from typing import Any, Optional

from backend.app.models.document import Document
from backend.app.modules.documents.document_open_resolver import (
    DocumentOpenContext,
    DocumentOpenDecision,
    DocumentOpenSurface,
    resolve_document_open,
)
from backend.app.security.event_taxonomy import EVENT_DOCUMENT_FILE_ACCESS_REQUESTED

DOCUMENT_OPEN_EXTRA_ALLOWLIST = frozenset(
    {
        "document_class",
        "candidate_id",
        "reason",
        "open_surface",
        "file_route",
        "workforce_employee_id",
        "handoff_id",
    }
)


def build_open_context_for_workforce_document(
    *,
    tenant_id: str,
    document: Document,
    workforce_employee_id: str,
    surface: DocumentOpenSurface = "hr_workforce_employee",
    actor_id: Optional[str] = None,
    actor_role: Optional[str] = None,
    handoff_id: Optional[str] = None,
) -> DocumentOpenContext:
    return DocumentOpenContext(
        surface=surface,
        tenant_id=str(tenant_id),
        document_id=str(document.id),
        actor_id=actor_id,
        actor_role=actor_role,
        candidate_id=str(document.candidate_id) if document.candidate_id else None,
        workforce_employee_id=str(workforce_employee_id),
        handoff_id=handoff_id,
        doc_type=str(document.doc_type) if document.doc_type else None,
    )


def resolve_workforce_document_open(
    *,
    tenant_id: str,
    document: Document,
    workforce_employee_id: str,
    surface: DocumentOpenSurface = "hr_workforce_employee",
    actor_id: Optional[str] = None,
    actor_role: Optional[str] = None,
    handoff_id: Optional[str] = None,
) -> DocumentOpenDecision:
    ctx = build_open_context_for_workforce_document(
        tenant_id=tenant_id,
        document=document,
        workforce_employee_id=workforce_employee_id,
        surface=surface,
        actor_id=actor_id,
        actor_role=actor_role,
        handoff_id=handoff_id,
    )
    return resolve_document_open(ctx)


def open_fields_from_decision(decision: DocumentOpenDecision) -> dict[str, Optional[str]]:
    if not decision.allowed or not decision.open_url:
        return {
            "file_url": None,
            "open_url": None,
            "document_open_context": decision.document_open_context or None,
        }
    return {
        "file_url": decision.open_url,
        "open_url": decision.open_url,
        "document_open_context": decision.document_open_context,
    }


def apply_open_to_cand_doc_dict(
    row: dict[str, Any],
    *,
    tenant_id: str,
    document: Document,
    workforce_employee_id: str,
    surface: DocumentOpenSurface = "hr_workforce_employee",
    handoff_id: Optional[str] = None,
) -> dict[str, Any]:
    decision = resolve_workforce_document_open(
        tenant_id=tenant_id,
        document=document,
        workforce_employee_id=workforce_employee_id,
        surface=surface,
        handoff_id=handoff_id,
    )
    row.update(open_fields_from_decision(decision))
    return row


def enrich_documents_for_approval_open_urls(
    rows: list[dict[str, Any]],
    *,
    tenant_id: str,
    workforce_employee_id: Optional[str],
    handoff_id: Optional[str] = None,
    documents_by_id: Optional[dict[str, Document]] = None,
) -> list[dict[str, Any]]:
    """Attach ``open_url`` / ``document_open_context`` for HR review document rows."""
    emp_id = str(workforce_employee_id or "").strip()
    hid = str(handoff_id or "").strip() or None
    if not emp_id and not hid:
        return rows
    out: list[dict[str, Any]] = []
    for row in rows:
        r = dict(row)
        doc_id = str(r.get("document_id") or "").strip()
        if not doc_id:
            out.append(r)
            continue
        doc_type: Optional[str] = None
        if documents_by_id and doc_id in documents_by_id:
            doc_type = str(documents_by_id[doc_id].doc_type or "")
        ctx = DocumentOpenContext(
            surface="hr_handoff_review",
            tenant_id=str(tenant_id),
            document_id=doc_id,
            candidate_id=None,
            workforce_employee_id=emp_id or None,
            handoff_id=hid,
            doc_type=doc_type,
        )
        decision = resolve_document_open(ctx)
        r.update(open_fields_from_decision(decision))
        out.append(r)
    return out


def build_workforce_cand_doc(
    document: Document,
    *,
    tenant_id: str,
    workforce_employee_id: str,
    surface: DocumentOpenSurface = "hr_workforce_employee",
    handoff_id: Optional[str] = None,
):
    """CandDoc for HR workforce list/profile with resolver-provided open URLs."""
    from backend.app.api.v1.candidate_documents import CandDoc

    cd = CandDoc.from_document(document, hr_workforce_view=True)
    decision = resolve_workforce_document_open(
        tenant_id=tenant_id,
        document=document,
        workforce_employee_id=workforce_employee_id,
        surface=surface,
        handoff_id=handoff_id,
    )
    fields = open_fields_from_decision(decision)
    return cd.model_copy(update=fields)


async def stream_workforce_employee_document_file(
    *,
    db_tenant,
    current_user,
    own_company_id,
    workforce_employee_id: str,
    document_id,
    surface: DocumentOpenSurface = "hr_workforce_employee",
    handoff_id: Optional[str] = None,
):
    """Validate open policy, audit, and stream file for a workforce-linked document."""
    from uuid import UUID

    from fastapi import HTTPException

    from backend.app.api.v1.candidate_documents import get_candidate_document_file
    from backend.app.models.document import Document
    from backend.app.services import workforce_employees as we_svc

    db, tid = db_tenant
    tenant_id = str(tid)
    emp = await we_svc.get_employee(db, tenant_id, workforce_employee_id)
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    cid = (emp.candidate_id or "").strip()
    if not cid:
        raise HTTPException(status_code=404, detail="No linked candidate")
    doc_row = await db.get(Document, str(document_id))
    if not doc_row or str(doc_row.candidate_id or "") != cid:
        raise HTTPException(status_code=404, detail="Document not found")

    access_kind = str(db.info.get("security_access_kind") or "").strip() or None
    open_ctx = build_open_context_for_workforce_document(
        tenant_id=tenant_id,
        document=doc_row,
        workforce_employee_id=workforce_employee_id,
        surface=surface,
        actor_id=str(current_user.sub) if getattr(current_user, "sub", None) else None,
        actor_role=str(getattr(current_user, "role", "") or "") or None,
        handoff_id=handoff_id,
    )
    open_decision = resolve_workforce_document_open(
        tenant_id=tenant_id,
        document=doc_row,
        workforce_employee_id=workforce_employee_id,
        surface=surface,
        actor_id=open_ctx.actor_id,
        actor_role=open_ctx.actor_role,
        handoff_id=handoff_id,
    )
    if not open_decision.allowed:
        audit_document_open(
            ctx=open_ctx,
            decision=open_decision,
            access_kind=access_kind,
            result="denied",
        )
        raise HTTPException(status_code=404, detail="Document not found")
    audit_document_open(
        ctx=open_ctx,
        decision=open_decision,
        access_kind=access_kind,
        result="success",
    )
    return await get_candidate_document_file(
        UUID(cid),
        document_id if isinstance(document_id, UUID) else UUID(str(document_id)),
        db_tenant=db_tenant,
        current_user=current_user,
        own_company_id=own_company_id,
    )


def audit_document_open(
    *,
    ctx: DocumentOpenContext,
    decision: DocumentOpenDecision,
    access_kind: Optional[str] = None,
    result: str = "success",
) -> None:
    """Emit security telemetry when a document file open is requested."""
    extra: dict[str, Any] = {
        "open_surface": ctx.surface,
        "file_route": decision.file_route,
    }
    if ctx.workforce_employee_id:
        extra["workforce_employee_id"] = str(ctx.workforce_employee_id)
    if ctx.handoff_id:
        extra["handoff_id"] = str(ctx.handoff_id)
    if ctx.candidate_id:
        extra["candidate_id"] = str(ctx.candidate_id)
    if decision.deny_reason:
        extra["reason"] = str(decision.deny_reason)
    if ctx.doc_type:
        extra["document_class"] = str(ctx.doc_type)

    from backend.app.security.canonical_emit import emit_security_event_v1

    emit_security_event_v1(
        event_type=EVENT_DOCUMENT_FILE_ACCESS_REQUESTED,
        result=result,
        severity="info" if result == "success" else "low",
        source="document_open_resolver",
        tenant_id=str(ctx.tenant_id),
        actor_id=ctx.actor_id,
        access_kind=access_kind,
        action=EVENT_DOCUMENT_FILE_ACCESS_REQUESTED,
        entity_type="document",
        entity_id=str(ctx.document_id),
        extra=extra,
        extra_allowlist=DOCUMENT_OPEN_EXTRA_ALLOWLIST,
    )
__all__ = [
    "apply_open_to_cand_doc_dict",
    "audit_document_open",
    "build_workforce_cand_doc",
    "build_open_context_for_workforce_document",
    "enrich_documents_for_approval_open_urls",
    "open_fields_from_decision",
    "resolve_workforce_document_open",
    "stream_workforce_employee_document_file",
]
