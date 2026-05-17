"""
ADR-014 Phase 2 — document **open** context (who opens, in which surface, which file route).

Separates file endpoint selection from ``viewer_channel`` list filtering.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional

from backend.app.modules.documents.document_visibility_and_locks import (
    document_type_primary_visibility_scope,
    viewer_readable_scopes,
)

DocumentOpenSurface = Literal[
    "recruitment_candidate",
    "hr_workforce_employee",
    "hr_handoff_review",
    "client_portal",
]

DocumentFileRoute = Literal[
    "workforce_employee",
    "handoff_review",
    "candidate",
    "db",
    "client_portal",
]


@dataclass(frozen=True)
class DocumentOpenContext:
    surface: DocumentOpenSurface
    tenant_id: str
    document_id: str
    actor_id: Optional[str] = None
    actor_role: Optional[str] = None
    candidate_id: Optional[str] = None
    workforce_employee_id: Optional[str] = None
    handoff_id: Optional[str] = None
    doc_type: Optional[str] = None


@dataclass(frozen=True)
class DocumentOpenDecision:
    allowed: bool
    file_route: DocumentFileRoute
    open_url: Optional[str] = None
    document_open_context: str = ""
    viewer_channel: str = "recruitment"
    deny_reason: Optional[str] = None


def _workforce_open_url(employee_id: str, document_id: str) -> str:
    return (
        f"/api/v1/workforce/employees/{employee_id}/documents/{document_id}/file"
    )


def _handoff_open_url(handoff_id: str, document_id: str) -> str:
    return f"/api/v1/handoffs/{handoff_id}/documents/{document_id}/file"


def _candidate_open_url(candidate_id: str, document_id: str) -> str:
    return f"/api/v1/candidates/{candidate_id}/documents/{document_id}/file"


def _db_open_url(document_id: str) -> str:
    return f"/api/v1/db/documents/{document_id}/file"


def _client_portal_open_url(document_id: str) -> str:
    return f"/api/v1/client-portal/documents/{document_id}/file"


def document_visible_in_open_surface(
    doc_type: Optional[str],
    surface: DocumentOpenSurface,
) -> bool:
    """Whether a document type may be opened in the given surface (read/open policy v1)."""
    if surface in ("hr_workforce_employee", "hr_handoff_review"):
        return True
    if surface == "recruitment_candidate":
        primary = document_type_primary_visibility_scope(doc_type)
        return primary in viewer_readable_scopes("recruitment")
    if surface == "client_portal":
        primary = document_type_primary_visibility_scope(doc_type)
        return primary in ("shared",)
    return False


def resolve_document_open(ctx: DocumentOpenContext) -> DocumentOpenDecision:
    """
    Resolve canonical file route and open URL for a document in a product surface.

    HR employee / handoff review surfaces expose **all** linked candidate document types
    (recruitment, transport, hr, shared) via workforce or handoff file routes — not
  ``X-Document-Viewer-Channel: hr`` on ``/db/documents``.
    """
    doc_id = str(ctx.document_id or "").strip()
    if not doc_id:
        return DocumentOpenDecision(
            allowed=False,
            file_route="db",
            document_open_context=ctx.surface,
            deny_reason="missing_document_id",
        )

    if not document_visible_in_open_surface(ctx.doc_type, ctx.surface):
        return DocumentOpenDecision(
            allowed=False,
            file_route="db",
            document_open_context=ctx.surface,
            viewer_channel="recruitment",
            deny_reason="document_type_not_visible_in_surface",
        )

    if ctx.surface == "hr_workforce_employee":
        emp_id = str(ctx.workforce_employee_id or "").strip()
        if not emp_id:
            return DocumentOpenDecision(
                allowed=False,
                file_route="workforce_employee",
                document_open_context=ctx.surface,
                deny_reason="missing_workforce_employee_id",
            )
        return DocumentOpenDecision(
            allowed=True,
            file_route="workforce_employee",
            open_url=_workforce_open_url(emp_id, doc_id),
            document_open_context=ctx.surface,
        )

    if ctx.surface == "hr_handoff_review":
        emp_id = str(ctx.workforce_employee_id or "").strip()
        handoff_id = str(ctx.handoff_id or "").strip()
        if emp_id:
            return DocumentOpenDecision(
                allowed=True,
                file_route="workforce_employee",
                open_url=_workforce_open_url(emp_id, doc_id),
                document_open_context=ctx.surface,
            )
        if handoff_id:
            return DocumentOpenDecision(
                allowed=True,
                file_route="handoff_review",
                open_url=_handoff_open_url(handoff_id, doc_id),
                document_open_context=ctx.surface,
            )
        return DocumentOpenDecision(
            allowed=False,
            file_route="handoff_review",
            document_open_context=ctx.surface,
            deny_reason="missing_handoff_or_employee",
        )

    if ctx.surface == "recruitment_candidate":
        cid = str(ctx.candidate_id or "").strip()
        if cid:
            return DocumentOpenDecision(
                allowed=True,
                file_route="candidate",
                open_url=_candidate_open_url(cid, doc_id),
                document_open_context=ctx.surface,
                viewer_channel="recruitment",
            )
        return DocumentOpenDecision(
            allowed=True,
            file_route="db",
            open_url=_db_open_url(doc_id),
            document_open_context=ctx.surface,
            viewer_channel="recruitment",
        )

    if ctx.surface == "client_portal":
        return DocumentOpenDecision(
            allowed=True,
            file_route="client_portal",
            open_url=_client_portal_open_url(doc_id),
            document_open_context=ctx.surface,
            viewer_channel="recruitment",
        )

    return DocumentOpenDecision(
        allowed=False,
        file_route="db",
        document_open_context=ctx.surface,
        deny_reason="unknown_surface",
    )


__all__ = [
    "DocumentFileRoute",
    "DocumentOpenContext",
    "DocumentOpenDecision",
    "DocumentOpenSurface",
    "document_visible_in_open_surface",
    "resolve_document_open",
]
