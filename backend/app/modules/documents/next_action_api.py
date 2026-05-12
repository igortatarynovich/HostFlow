"""HTTP surface for the per-document "what to do next" service.

Closes G-8 stage 2.2 — see `docs/specs/operations-loop.md`. Mounted as
`GET /api/v1/db/documents/{document_id}/next-action` (the documents router
uses prefix `/db`, see `backend/app/modules/documents/router.py`). The
response is the same canonical `NextActionDTO` shape that the candidate /
lead / vacancy variants return, so the frontend `<NextActionBadge>`
renders without any branching.

Auth gating intentionally mirrors `GET /db/documents/{document_id}` in
`backend/app/modules/documents/router.py:api_get_document` — that endpoint
has no explicit `require_roles` and relies on tenant scoping + ACL via
`_get_document_with_access`. Tightening the next-action surface would be
inconsistent: anyone who can already read the document should be able to
ask "what's the next action?".

``document_id`` is typed as **str** (not ``UUID``) so checklist **synthetic** ids
``synthetic::{doc_type}::{candidate_id}`` are accepted; the service returns a
``document_missing`` CTA without **422** path validation errors.

Soft-delete handling: we DO NOT exclude `deleted_at IS NOT NULL` here.
The service returns a `terminal_deleted` DTO for soft-deleted documents,
which is the truthful answer; 404 would be misleading because the row
still exists.
"""

from __future__ import annotations

from typing import Tuple

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.deps import get_db_with_tenant
from backend.app.models.document import Document
from backend.app.services.next_action import NextActionDTO, compute_document_next_action

router = APIRouter()


@router.get(
    "/documents/{document_id}/next-action",
    response_model=NextActionDTO,
    summary="Resolve the single primary 'what to do next' CTA for a document",
    description=(
        "Returns one canonical NextActionDTO. The DTO shape is stable across "
        "all branches (deleted / cancelled / overdue / expired / reminder / "
        "missing / rejected / verification / expiring_soon / awaiting / idle) "
        "so the frontend always renders the same component. See "
        "`docs/specs/operations-loop.md` §G-8 for the precedence rules and "
        "reason codes."
    ),
)
async def get_document_next_action(
    document_id: str,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> NextActionDTO:
    db, tenant_id = db_tenant
    tenant_id_str = str(tenant_id)
    document_id_str = str(document_id).strip()

    synthetic = document_id_str.startswith("synthetic::")
    if not synthetic:
        document_row = await db.scalar(
            select(Document.id).where(
                Document.id == document_id_str,
                Document.tenant_id == tenant_id_str,
            )
        )
        if document_row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found",
            )

    return await compute_document_next_action(
        db,
        tenant_id=tenant_id_str,
        document_id=document_id_str,
    )
