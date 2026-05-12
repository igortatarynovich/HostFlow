"""Own-company scoping for documents and document policies (§2.4)."""

from __future__ import annotations

from typing import Any, Optional

from fastapi import HTTPException
from sqlalchemy import and_, or_
from sqlalchemy.sql import ColumnElement

from backend.app.models.candidate import Candidate
from backend.app.models.document import Document


def resolved_document_own_company_id(cand: Candidate, active_own_company_id: Optional[str]) -> Optional[str]:
    """Effective own-company for document rows tied to this candidate.

    The UI persists ``X-Own-Company-Id`` globally (active workspace). That value can
    differ from ``Candidate.own_company_id`` while the user still opens the candidate
    card from the tenant-wide list (see candidates list: no own-company filter for the
    same reason). When the candidate is pinned to a workspace, document APIs should use
    that id so listings and summaries stay aligned with the card the user opened.
    """
    c = str(getattr(cand, "own_company_id", None) or "").strip()
    if c:
        return c
    a = str(active_own_company_id or "").strip()
    return a or None


def ensure_candidate_own_company_scope(cand: Candidate, own_company_id: Optional[str]) -> None:
    if not own_company_id:
        return
    c = str(getattr(cand, "own_company_id", None) or "").strip()
    if c and c != str(own_company_id).strip():
        raise HTTPException(status_code=404, detail="Candidate not found")


def documents_scope_clause(own_company_id: Optional[str]) -> Optional[ColumnElement[Any]]:
    """Filter documents visible under active own-company (join Candidate on Document.candidate_id)."""
    if not own_company_id:
        return None
    oc = str(own_company_id).strip()
    return or_(
        Document.own_company_id == oc,
        and_(Document.own_company_id.is_(None), Candidate.own_company_id == oc),
        and_(Document.own_company_id.is_(None), Candidate.own_company_id.is_(None)),
    )


def tenant_documents_own_company_clause(own_company_id: Optional[str]) -> Optional[ColumnElement[Any]]:
    """Filter tenant-wide document lists (no Candidate join) by Document.own_company_id."""
    if not own_company_id:
        return None
    oc = str(own_company_id).strip()
    return or_(Document.own_company_id == oc, Document.own_company_id.is_(None))


def document_policies_own_company_clause(own_company_id: Optional[str]) -> Optional[ColumnElement[Any]]:
    """Filter document_policies rows for active workspace + legacy NULL."""
    if not own_company_id:
        return None
    from backend.app.models.document_policy import DocumentPolicy

    oc = str(own_company_id).strip()
    return or_(DocumentPolicy.own_company_id == oc, DocumentPolicy.own_company_id.is_(None))


def ensure_document_own_company_matches(
    doc: Document,
    cand: Candidate,
    active_own_company_id: Optional[str],
) -> None:
    if not active_own_company_id:
        return
    oc = str(active_own_company_id).strip()
    doc_oc = str(getattr(doc, "own_company_id", None) or "").strip()
    cand_oc = str(getattr(cand, "own_company_id", None) or "").strip()
    effective = doc_oc or cand_oc
    if not effective:
        return
    if effective != oc:
        raise HTTPException(status_code=404, detail="Document not found")


__all__ = [
    "resolved_document_own_company_id",
    "ensure_candidate_own_company_scope",
    "documents_scope_clause",
    "tenant_documents_own_company_clause",
    "document_policies_own_company_clause",
    "ensure_document_own_company_matches",
]
