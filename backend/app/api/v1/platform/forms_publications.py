"""ADR-007 Forms platform read API (C4 publication bridge)."""

from __future__ import annotations

from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from backend.app.auth.deps import UserCtx, get_current_user, require_roles
from backend.app.auth.hiring_workspace_roles import HIRING_CANDIDATE_PROFILE_READ_ROLES
from backend.app.db.deps import get_db_with_tenant
from backend.app.forms_platform.handlers import list_registered_handlers
from backend.app.forms_platform.publication_bridge import resolve_forms_platform_publication

router = APIRouter(
    prefix="/platform/forms",
    tags=["forms-platform"],
    redirect_slashes=False,
)


class SubmissionHandlerOut(BaseModel):
    handler_id: str
    module_owner: str
    creates: list[str] = Field(default_factory=list)
    creates_on_create: dict[str, bool] = Field(default_factory=dict)
    route_intent: str


class FormPublicationOut(BaseModel):
    contract_version: str
    adr: str
    publication_id: str
    storage_backend: str
    title: str
    public_slug: Optional[str] = None
    is_active: bool
    lifecycle_status: Optional[str] = None
    published_version: Optional[int] = None
    published_at: Optional[str] = None
    has_immutable_snapshot: Optional[bool] = None
    consent_pin: Optional[dict[str, Any]] = None
    mode: str
    tier: str
    module_owner: str
    entity_profile_code: str
    presentation_code: Optional[str] = None
    intake_source_profile_id: Optional[str] = None
    public_intake_path: str
    public_apply_path_template: str
    submission_handler: SubmissionHandlerOut
    capabilities: dict[str, bool] = Field(default_factory=dict)
    canon: Optional[str] = None


class FormHandlersOut(BaseModel):
    handlers: list[SubmissionHandlerOut] = Field(default_factory=list)


def _ensure_tenant(ctx: UserCtx, tenant_id: str) -> None:
    token_tenant = (ctx.tenant_id or "").strip()
    if token_tenant and token_tenant != tenant_id:
        raise HTTPException(status_code=403, detail="Forbidden for tenant")


@router.get("/handlers", response_model=FormHandlersOut)
async def list_forms_platform_handlers(
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: tuple = Depends(get_db_with_tenant),
) -> FormHandlersOut:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    _ensure_tenant(ctx, tenant_id)
    rows = list_registered_handlers()
    return FormHandlersOut(handlers=[SubmissionHandlerOut.model_validate(row) for row in rows])


@router.get("/publications/resolve", response_model=FormPublicationOut)
async def resolve_form_publication(
    public_slug: Optional[str] = Query(default=None, min_length=2, max_length=64),
    form_id: Optional[str] = Query(default=None, min_length=1, max_length=36),
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: tuple = Depends(get_db_with_tenant),
) -> FormPublicationOut:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    _ensure_tenant(ctx, tenant_id)
    if not public_slug and not form_id:
        raise HTTPException(status_code=422, detail="public_slug or form_id is required")

    publication: dict[str, Any] | None = await resolve_forms_platform_publication(
        db,
        tenant_id=tenant_id,
        public_slug=public_slug,
        form_id=form_id,
    )
    if publication is None:
        raise HTTPException(status_code=404, detail="Form publication not found")
    return FormPublicationOut.model_validate(publication)
