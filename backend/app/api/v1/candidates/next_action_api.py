"""HTTP surface for the per-candidate "what to do next" service.
Closes G-8 (stage 1a) — see `docs/specs/operations-loop.md`. The endpoint is
mounted as `GET /api/v1/candidates/{candidate_id}/next-action` and returns a
single primary CTA that the candidate detail page renders in its header.
Role gating mirrors `GET /candidates/{candidate_id}`: anyone with candidate
view access can ask "what should I do here?", but recruiter/supervisor/
manager still go through `ensure_candidate_access` so an ACL-restricted user
can't probe candidates they don't own.
The endpoint flips `is_client_tenant` based on the viewer's tenant kind so
the agency operator and the client operator see CTAs framed for their side
of the handoff, even though the candidate row is identical.
"""

from __future__ import annotations

from backend.app.auth.trust_role_deps import require_trust_admin, require_trust_read, require_trust_write

from typing import Tuple
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.v1.candidates.acl import ensure_candidate_access
from backend.app.auth.deps import UserCtx, get_current_user
from backend.app.auth.hiring_workspace_roles import HIRING_CANDIDATE_VIEW_ROLES
from backend.app.db.deps import get_db_with_tenant
from backend.app.models.candidate import Candidate
from backend.app.services.handoff import is_client_tenant_for_list
from backend.app.services.next_action import NextActionDTO, compute_candidate_next_action
from sqlalchemy import select

router = APIRouter()

@router.get(
    "/{candidate_id}/next-action",
    response_model=NextActionDTO,
    dependencies=[Depends(require_trust_read())],
    summary="Resolve the single primary 'what to do next' CTA for a candidate",
    description=(
        "Returns one canonical NextActionDTO. The DTO shape is stable across "
        "all branches (terminal / handoff / reminder / contact / idle) so the "
        "frontend always renders the same component. See "
        "`docs/specs/operations-loop.md` §G-8 for the precedence rules and "
        "reason codes."
    ),
)
async def get_candidate_next_action(
    candidate_id: UUID,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> NextActionDTO:
    db, tenant_id = db_tenant
    tenant_id_str = str(tenant_id)
    candidate_id_str = str(candidate_id)

    # 404 path: confirm the candidate exists in this tenant before doing
    # anything else. Returning a placeholder DTO would mask deleted/typo'd
    # IDs and make debugging painful.
    candidate_row = await db.scalar(
        select(Candidate.id).where(
            Candidate.id == candidate_id_str,
            Candidate.tenant_id == tenant_id_str,
        )
    )
    if candidate_row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate not found",
        )

    await ensure_candidate_access(db, tenant_id_str, candidate_id_str, current_user)

    is_client_tenant = await is_client_tenant_for_list(db, tenant_id_str)

    return await compute_candidate_next_action(
        db,
        tenant_id=tenant_id_str,
        candidate_id=candidate_id_str,
        is_client_tenant=is_client_tenant,
    )
