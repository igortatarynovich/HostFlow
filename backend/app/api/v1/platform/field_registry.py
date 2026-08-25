"""Read-only Field Registry API (P1)."""

from __future__ import annotations

from backend.app.auth.trust_role_deps import require_trust_admin, require_trust_read, require_trust_write

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.deps import get_current_user
from backend.app.auth.hiring_workspace_roles import HIRING_CANDIDATE_PROFILE_READ_ROLES
from backend.app.db.deps import get_db_with_tenant
from backend.app.field_registry.candidate_layout_bridge import resolve_effective_candidate_card_layout
from backend.app.field_registry.resolver import list_canonical_fields_for_scope, resolve_effective_card_layout

router = APIRouter(
    prefix="/platform/field-registry",
    tags=["field-registry"],
    redirect_slashes=False,
)

class CanonicalFieldOut(BaseModel):
    id: str
    qualified_code: str
    module: str
    entity_type: str
    field_type: str
    label_key: Optional[str] = None
    name: str
    ownership: str
    reference_domain: Optional[str] = None
    pii_class: Optional[str] = None
    storage: Optional[dict] = None
    legacy_aliases: List[str] = Field(default_factory=list)
    registry_version: str
    status: str

class LayoutFieldOut(CanonicalFieldOut):
    section_code: str
    sort_order: int
    visible: bool
    required: bool
    label_override: Optional[str] = None

class LayoutSectionOut(BaseModel):
    code: str
    order: int
    fields: List[LayoutFieldOut]

class EffectiveCardLayoutOut(BaseModel):
    entity_type: str
    layout_code: Optional[str] = None
    layout_name: Optional[str] = None
    module: Optional[str] = None
    is_default: Optional[bool] = None
    resolution_source: str
    registry_version: Optional[str] = None
    sections: List[LayoutSectionOut]
    fields: List[LayoutFieldOut]
    candidate_id: Optional[str] = None
    candidate_profile_id: Optional[str] = None
    candidate_profile_code: Optional[str] = None
    process_profile_id: Optional[str] = None
    process_profile_code: Optional[str] = None
    process_profile_source: Optional[str] = None
    bridge_source: Optional[str] = None

class CanonicalFieldListOut(BaseModel):
    items: List[CanonicalFieldOut]
    count: int

@router.get("/fields", response_model=CanonicalFieldListOut)
async def list_canonical_fields(
    entity_type: Optional[str] = Query(None, description="Filter by entity type (candidate, vacancy, client)"),
    module: Optional[str] = Query(None, description="Filter by owning module"),
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    _: None = Depends(require_trust_read()),
    __user=Depends(get_current_user),
) -> CanonicalFieldListOut:
    """List canonical field definitions (tenant overrides merged over platform catalog)."""
    db, tenant_uuid = db_tenant
    items = await list_canonical_fields_for_scope(
        db,
        tenant_id=str(tenant_uuid),
        entity_type=entity_type,
        module=module,
    )
    return CanonicalFieldListOut(
        items=[CanonicalFieldOut.model_validate(row) for row in items],
        count=len(items),
    )

@router.get("/layouts/{layout_code}", response_model=EffectiveCardLayoutOut)
async def get_card_layout(
    layout_code: str,
    entity_type: str = Query(..., description="Entity type for validation/resolution"),
    module: Optional[str] = Query(None),
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    _: None = Depends(require_trust_read()),
    __user=Depends(get_current_user),
) -> EffectiveCardLayoutOut:
    """Get read-only card layout by code."""
    db, tenant_uuid = db_tenant
    payload = await resolve_effective_card_layout(
        db,
        tenant_id=str(tenant_uuid),
        entity_type=entity_type,
        layout_code=layout_code,
        module=module,
    )
    if payload.get("resolution_source") == "not_found":
        raise HTTPException(status_code=404, detail="Card layout not found")
    return EffectiveCardLayoutOut.model_validate(payload)

@router.get("/effective-layout", response_model=EffectiveCardLayoutOut)
async def get_effective_card_layout(
    entity_type: str = Query(..., description="Entity type (candidate, vacancy, client)"),
    layout_code: Optional[str] = Query(None, description="Explicit layout code; default used when omitted"),
    module: Optional[str] = Query(None),
    candidate_id: Optional[str] = Query(None, description="Candidate id for profile-bound layout (P3 bridge)"),
    candidate_profile_id: Optional[str] = Query(
        None, description="CandidateProfile id for layout bridge overlay (P3)"
    ),
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    _: None = Depends(require_trust_read()),
    __user=Depends(get_current_user),
) -> EffectiveCardLayoutOut:
    """Resolve effective read-only card layout for an entity type."""
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    if entity_type == "candidate" and (candidate_id or candidate_profile_id):
        payload = await resolve_effective_candidate_card_layout(
            db,
            tenant_id=tenant_id,
            candidate_id=candidate_id,
            candidate_profile_id=candidate_profile_id,
            layout_code=layout_code,
            module=module,
        )
    else:
        payload = await resolve_effective_card_layout(
            db,
            tenant_id=tenant_id,
            entity_type=entity_type,
            layout_code=layout_code,
            module=module,
        )
    if payload.get("resolution_source") == "not_found":
        raise HTTPException(status_code=404, detail="No card layout found for entity type")
    return EffectiveCardLayoutOut.model_validate(payload)
