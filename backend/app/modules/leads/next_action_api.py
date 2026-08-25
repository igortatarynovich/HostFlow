"""HTTP surface for the per-lead "what to do next" service.

Closes G-8 stage 2.0 — see `docs/specs/operations-loop.md`. The endpoint is
mounted as `GET /api/v1/leads/{lead_id}/next-action` and returns the same
canonical `NextActionDTO` shape that the candidate variant returns, so the
frontend `<NextActionBadge>` renders the lead CTA without any branching.

Role gating mirrors `GET /leads/{lead_id}` in
`backend/app/modules/leads/router.py` (admin / manager / recruiter / viewer).
"""

from __future__ import annotations

from typing import Tuple
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.trust_role_deps import require_trust_admin, require_trust_read, require_trust_write
from backend.app.auth.deps import Role, UserCtx, get_current_user
from backend.app.db.deps import get_db_with_tenant
from backend.app.models.lead import Lead
from backend.app.services.next_action import NextActionDTO, compute_lead_next_action

router = APIRouter()


@router.get(
    "/{lead_id}/next-action",
    response_model=NextActionDTO,
    dependencies=[
        Depends(require_trust_read())
    ],
    summary="Resolve the single primary 'what to do next' CTA for a lead",
    description=(
        "Returns one canonical NextActionDTO. The DTO shape is stable across "
        "all branches (terminal / routing / reminder / unqualified / idle) so "
        "the frontend always renders the same component. See "
        "`docs/specs/operations-loop.md` §G-8 for the precedence rules and "
        "reason codes."
    ),
)
async def get_lead_next_action(
    lead_id: str,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> NextActionDTO:
    db, tenant_id = db_tenant
    tenant_id_str = str(tenant_id)
    lead_id_str = str(lead_id or "").strip()
    if not lead_id_str:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")

    # 404 path: confirm the lead exists in this tenant before doing anything
    # else. Returning a placeholder DTO would mask deleted/typo'd IDs and
    # make debugging painful.
    lead_row = await db.scalar(
        select(Lead.id).where(
            Lead.id == lead_id_str,
            Lead.tenant_id == tenant_id_str,
        )
    )
    if lead_row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")

    # No own_company / ACL gating on next-action surface: a viewer who can
    # already read the lead via `GET /leads/{id}` should be able to ask
    # "what's the next action?". The CTA is metadata, not a write operation.
    _ = current_user

    return await compute_lead_next_action(
        db,
        tenant_id=tenant_id_str,
        lead_id=lead_id_str,
    )
