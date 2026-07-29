"""Unified global search v1 (CRM core entities)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.deps import Role, require_roles, get_current_user, UserCtx
from backend.app.db.deps import get_db_with_tenant
from backend.app.api.v1.utils.own_company import resolve_active_own_company_id_optional
from backend.app.security.event_taxonomy import EVENT_SEARCH_RETRIEVAL_COMPLETED
from backend.app.security.retrieval_events import emit_retrieval_security_event_v1
from backend.app.services.global_search_v1 import run_global_search_v1

router = APIRouter(prefix="/search", tags=["search"], redirect_slashes=False)

GLOBAL_SEARCH_ROLES = (
    Role.superadmin,
    Role.administrator,
    Role.supervisor,
    Role.recruiter,
    Role.viewer,
    Role.client_manager,
    Role.client_processor,
    Role.compliance_officer,
)


class GlobalSearchItemOut(BaseModel):
    type: str = Field(
        description=(
            "candidate | company | vacancy | lead | document | invoice | service_order | "
            "conversation | task"
        ),
    )
    id: str
    title: str
    subtitle: str | None = None
    link: str


class GlobalSearchResponse(BaseModel):
    q: str
    items: list[GlobalSearchItemOut]


@router.get("", response_model=GlobalSearchResponse)
async def global_search(
    q: str = Query(..., min_length=2, max_length=200, description="Search string"),
    limit: int = Query(4, ge=1, le=20, description="Max hits per entity type before merge"),
    max_results: int = Query(24, ge=1, le=50, description="Max items after merge/rank"),
    scope_tenant_id: UUID | None = Query(
        None,
        description="Optional tenant scope override (same semantics as candidates list).",
    ),
    assignee_scope: str = Query(
        "mine",
        pattern="^(mine|team)$",
        description="Reminder/task slice: mine (default) or team — same as GET /reminders assignee_scope.",
    ),
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
    own_company_id: str | None = Depends(resolve_active_own_company_id_optional),
    _role: str = Depends(require_roles(*GLOBAL_SEARCH_ROLES)),
) -> GlobalSearchResponse:
    db, tenant_uuid = db_tenant
    payload = await run_global_search_v1(
        db,
        header_tenant_id=tenant_uuid,
        scope_tenant_id=scope_tenant_id,
        current_user=current_user,
        own_company_id=own_company_id,
        q=q,
        limit_per_type=limit,
        max_results=max_results,
        assignee_scope=assignee_scope,
    )
    items = payload.get("items") if isinstance(payload, dict) else None
    returned = len(items) if isinstance(items, list) else 0
    scope = str(scope_tenant_id or tenant_uuid)
    ak = db.info.get("security_access_kind")
    emit_retrieval_security_event_v1(
        event_type=EVENT_SEARCH_RETRIEVAL_COMPLETED,
        result="success",
        severity="info",
        source="http:GET /api/v1/search",
        tenant_id=scope,
        access_kind=str(ak).strip() if ak else "tenant_bound",
        entity_type="tenant",
        entity_id=scope,
        actor_id=str(getattr(current_user, "sub", "") or "") or None,
        retrieval_type="global_search_v1",
        retrieval_scope="tenant",
        returned_count=returned,
        contains_class3=False,
        response_mode="json_list",
    )
    return GlobalSearchResponse.model_validate(payload)
