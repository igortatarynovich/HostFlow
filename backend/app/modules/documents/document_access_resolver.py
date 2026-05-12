"""
ADR-014 Phase 2 — DocumentAccessResolver.

Orchestrates candidate document **read** and **mutation** access: owner access via
``candidate_document_owner_access``, workspace slice, minimal policy surface
(read / mutate / destructive), visibility stub, process-lock hook.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Optional
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.modules.documents.candidate_document_owner_access import (
    load_candidate_documents_owner_context,
)
from backend.app.modules.documents.document_visibility_and_locks import (
    document_operation_allowed,
    resolve_process_locks_stub,
    resolve_visibility_scope_stub,
    viewer_readable_scopes,
)
from backend.app.services.own_company_doc_scope import resolved_document_own_company_id

DocumentAccessPolicy = Literal["read", "mutate", "destructive_mutate"]


@dataclass(frozen=True)
class DocumentAccessContext:
    """Resolved access for candidate document operations (read / mutate / destructive)."""

    candidate_context: Any
    resolved_workspace_own_company_id: Optional[str]
    access_policy: DocumentAccessPolicy = "read"
    visibility_scope_stub: str = "recruitment"
    process_locks_stub: frozenset[str] = field(default_factory=frozenset)
    viewer_channel: str = "recruitment"
    viewer_readable_scopes: frozenset[str] = field(
        default_factory=lambda: frozenset({"recruitment", "shared"})
    )


class DocumentAccessResolver:
    """Policy-ready resolver; owner access is delegated to the owner-access provider."""

    @staticmethod
    def _document_access_context_for_policy(
        cand_ctx: Any,
        workspace_own_company_header: Optional[str],
        *,
        access_policy: DocumentAccessPolicy,
        viewer_channel: str = "recruitment",
    ) -> DocumentAccessContext:
        own_for_docs = resolved_document_own_company_id(
            cand_ctx.candidate,
            workspace_own_company_header,
        )
        vis = resolve_visibility_scope_stub(cand_ctx.candidate)
        locks = resolve_process_locks_stub(cand_ctx.candidate)
        v_ch = (viewer_channel or "recruitment").strip().lower() or "recruitment"
        return DocumentAccessContext(
            candidate_context=cand_ctx,
            resolved_workspace_own_company_id=own_for_docs,
            access_policy=access_policy,
            visibility_scope_stub=vis,
            process_locks_stub=locks,
            viewer_channel=v_ch,
            viewer_readable_scopes=viewer_readable_scopes(v_ch),
        )

    @staticmethod
    async def resolve_for_candidate_documents(
        session: AsyncSession,
        tenant_id: str,
        candidate_id: UUID,
        *,
        workspace_own_company_header: Optional[str],
        viewer_channel: str = "recruitment",
    ) -> DocumentAccessContext:
        """Resolve owner access + workspace slice for candidate document **reads**."""
        cand_ctx = await load_candidate_documents_owner_context(
            session, tenant_id, candidate_id
        )
        return DocumentAccessResolver._document_access_context_for_policy(
            cand_ctx,
            workspace_own_company_header,
            access_policy="read",
            viewer_channel=viewer_channel,
        )

    @staticmethod
    async def resolve_for_candidate_document_mutations(
        session: AsyncSession,
        tenant_id: str,
        candidate_id: UUID,
        *,
        workspace_own_company_header: Optional[str],
        viewer_channel: str = "recruitment",
    ) -> DocumentAccessContext:
        """Semantic entrypoint for **mutations** (non-destructive slice + owner)."""
        cand_ctx = await load_candidate_documents_owner_context(
            session, tenant_id, candidate_id
        )
        return DocumentAccessResolver._document_access_context_for_policy(
            cand_ctx,
            workspace_own_company_header,
            access_policy="mutate",
            viewer_channel=viewer_channel,
        )

    @staticmethod
    async def resolve_for_candidate_destructive_document_mutations(
        session: AsyncSession,
        tenant_id: str,
        candidate_id: UUID,
        *,
        workspace_own_company_header: Optional[str],
        viewer_channel: str = "recruitment",
    ) -> DocumentAccessContext:
        """Destructive mutation path: same context as mutate + **process lock** enforcement."""
        cand_ctx = await load_candidate_documents_owner_context(
            session, tenant_id, candidate_id
        )
        ctx = DocumentAccessResolver._document_access_context_for_policy(
            cand_ctx,
            workspace_own_company_header,
            access_policy="destructive_mutate",
            viewer_channel=viewer_channel,
        )
        DocumentAccessResolver.ensure_destructive_mutation_allowed(ctx)
        return ctx

    @staticmethod
    def ensure_destructive_mutation_allowed(ctx: DocumentAccessContext) -> None:
        """Block destructive operations when process-lock tokens apply (Product Phase 2)."""
        if ctx.viewer_channel != "recruitment":
            raise HTTPException(
                status_code=403,
                detail="Operation blocked (viewer channel)",
            )
        if not document_operation_allowed(
            access_policy="destructive_mutate",
            process_locks=ctx.process_locks_stub,
        ):
            raise HTTPException(
                status_code=403,
                detail="Operation blocked (process lock)",
            )

    @staticmethod
    async def resolve_for_candidate_summary(
        session: AsyncSession,
        tenant_id: str,
        candidate_id: UUID,
        *,
        workspace_own_company_header: Optional[str],
        viewer_channel: str = "recruitment",
    ) -> DocumentAccessContext:
        """Alias for ``resolve_for_candidate_documents`` (migration seam name)."""
        return await DocumentAccessResolver.resolve_for_candidate_documents(
            session,
            tenant_id,
            candidate_id,
            workspace_own_company_header=workspace_own_company_header,
            viewer_channel=viewer_channel,
        )


__all__ = [
    "DocumentAccessContext",
    "DocumentAccessPolicy",
    "DocumentAccessResolver",
]
