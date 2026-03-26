"""Next Best Action (NBA) v0 — grouped operational buckets."""

from __future__ import annotations

from typing import Tuple
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.deps import Role, UserCtx, get_current_user, require_roles
from backend.app.db.deps import get_db_with_tenant
from backend.app.api.v1.utils.own_company import resolve_active_own_company_id
from backend.app.modules.leads import service
from backend.app.modules.leads.schemas import LeadNextActionsResponse

router = APIRouter(prefix="/next-actions", tags=["next-actions"])


@router.get("", response_model=LeadNextActionsResponse)
@router.get("/", response_model=LeadNextActionsResponse, include_in_schema=False)
async def get_next_actions(
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    own_company_id: str = Depends(resolve_active_own_company_id),
    current_user: UserCtx = Depends(get_current_user),
    _role: str = Depends(require_roles(Role.admin, Role.manager, Role.recruiter, Role.viewer)),
) -> LeadNextActionsResponse:
    """
    NBA snapshot: lead buckets + assignee-scoped candidate buckets (§2.3).
    Includes `plan_code`, `nba_tier`, and per-group `locked` / `required_plan` for lead SLA.
    """
    db, tenant_id = db_tenant
    return await service.lead_next_actions_snapshot(
        db,
        tenant_id=str(tenant_id),
        own_company_id=own_company_id,
        actor_user_id=str(current_user.sub or "").strip() or None,
    )
