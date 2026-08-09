"""Read-only Entity Profile Definition Registry API (P1–P2)."""

from __future__ import annotations

from backend.app.auth.trust_role_deps import require_trust_admin, require_trust_read, require_trust_write

from typing import Any, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from backend.app.auth.deps import get_current_user
from backend.app.auth.hiring_workspace_roles import HIRING_CANDIDATE_PROFILE_READ_ROLES
from backend.app.db.deps import get_db_with_tenant
from backend.app.entity_profile.exceptions import EntityProfileNotFoundError
from backend.app.entity_profile.facade import (
    resolve_entity_profile_facade,
    resolve_entity_profile_for_intake_source,
)
from backend.app.entity_profile.presentation_runtime import (
    FormPresentationNotFoundError,
    resolve_form_presentation,
    resolve_form_presentation_for_intake_source,
)
from backend.app.entity_profile.resolver import resolve_effective_entity_profile

router = APIRouter(
    prefix="/platform/entity-profiles",
    tags=["entity-profiles"],
    redirect_slashes=False,
)

class CanonicalFieldRefOut(BaseModel):
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

class EntityProfileFieldOut(BaseModel):
    qualified_code: Optional[str] = None
    sort_order: int
    intake_level: str
    card_save_level: str
    transition_level: str
    is_active: bool
    canonical_field_id: Optional[str] = None
    field: Optional[CanonicalFieldRefOut] = None
    legacy_field_key: Optional[str] = None
    label_override: Optional[str] = None

class EntityProfileMetaOut(BaseModel):
    id: str
    profile_code: Optional[str] = None
    entity_type: str
    module_owner: str
    name: str
    description: Optional[str] = None
    default_layout_code: Optional[str] = None
    document_pack_code: Optional[str] = None
    process_profile_code: Optional[str] = None
    registry_version: str
    status: str
    version: int
    config: dict[str, Any] = Field(default_factory=dict)

class IntakePresentationOut(BaseModel):
    presentation_code: str
    field_subset: List[str]
    presentation_overrides: dict[str, Any] = Field(default_factory=dict)
    intake_source_binding_id: Optional[str] = None

class FormPresentationFieldOut(BaseModel):
    qualified_code: str
    sort_order: int
    intake_level: str
    label: str
    field_type: Optional[str] = None
    field: Optional[dict[str, Any]] = None
    presentation_overrides: dict[str, Any] = Field(default_factory=dict)
    widget_hint: Optional[str] = None

class FormPresentationRuntimeOut(BaseModel):
    contract_version: str
    entity_profile_code: str
    presentation_code: str
    resolution_source: str
    registry_version: str
    entity_type: Optional[str] = None
    profile_name: Optional[str] = None
    field_subset: List[str]
    fields: List[FormPresentationFieldOut]
    warnings: List[str] = Field(default_factory=list)
    intake_source_profile_id: Optional[str] = None
    ownership: str = "display_only"

class EffectiveEntityProfileOut(BaseModel):
    profile_code: Optional[str] = None
    entity_profile_code: Optional[str] = None
    resolution_source: str
    bridge_source: Optional[str] = None
    profile: Optional[EntityProfileMetaOut] = None
    fields: List[EntityProfileFieldOut]
    presentations: List[IntakePresentationOut] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    candidate_profile_id: Optional[str] = None
    candidate_profile_code: Optional[str] = None
    intake_source_profile_id: Optional[str] = None
    intake_source_profile_code: Optional[str] = None

@router.get("/resolve", response_model=EffectiveEntityProfileOut)
async def resolve_entity_profile(
    entity_profile_code: Optional[str] = Query(None, description="Explicit Entity Profile registry code"),
    candidate_profile_id: Optional[str] = Query(None, description="Legacy CandidateProfile id fallback"),
    candidate_profile_code: Optional[str] = Query(None, description="Legacy CandidateProfile code fallback"),
    intake_source_profile_id: Optional[str] = Query(None, description="Intake source profile id (uses its entity_profile_code)"),
    include_presentations: bool = Query(False),
    db_tenant: tuple = Depends(get_db_with_tenant),
    _: None = Depends(require_trust_read()),
    __user=Depends(get_current_user),
) -> EffectiveEntityProfileOut:
    """Unified facade: registry when entity_profile_code is set; legacy fallback otherwise."""
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    try:
        if intake_source_profile_id:
            payload = await resolve_entity_profile_for_intake_source(
                db,
                tenant_id=tenant_id,
                intake_source_profile_id=intake_source_profile_id,
                entity_profile_code=entity_profile_code,
                candidate_profile_id=candidate_profile_id,
                candidate_profile_code=candidate_profile_code,
                include_presentations=include_presentations,
            )
        else:
            payload = await resolve_entity_profile_facade(
                db,
                tenant_id=tenant_id,
                entity_profile_code=entity_profile_code,
                candidate_profile_id=candidate_profile_id,
                candidate_profile_code=candidate_profile_code,
                include_presentations=include_presentations,
            )
    except EntityProfileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return EffectiveEntityProfileOut.model_validate(payload)

@router.get("/presentations/resolve", response_model=FormPresentationRuntimeOut)
async def resolve_form_presentation_endpoint(
    presentation_code: str = Query(..., description="Form presentation code, e.g. recruitment.candidate.driver_ce.meta_short"),
    entity_profile_code: Optional[str] = Query(None, description="Entity Profile registry code"),
    intake_source_profile_id: Optional[str] = Query(None, description="Resolve entity_profile_code from intake source"),
    db_tenant: tuple = Depends(get_db_with_tenant),
    _: None = Depends(require_trust_read()),
    __user=Depends(get_current_user),
) -> FormPresentationRuntimeOut:
    """Form Presentation Runtime (P5A) — display-only field schema for public/Meta forms."""
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    try:
        if intake_source_profile_id and not entity_profile_code:
            payload = await resolve_form_presentation_for_intake_source(
                db,
                tenant_id=tenant_id,
                intake_source_profile_id=str(intake_source_profile_id),
                presentation_code=presentation_code,
            )
        else:
            if not entity_profile_code:
                raise HTTPException(
                    status_code=422,
                    detail="entity_profile_code or intake_source_profile_id is required",
                )
            payload = await resolve_form_presentation(
                db,
                tenant_id=tenant_id,
                entity_profile_code=str(entity_profile_code),
                presentation_code=presentation_code,
                intake_source_profile_id=intake_source_profile_id,
            )
    except FormPresentationNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return FormPresentationRuntimeOut.model_validate(payload)

@router.get("/{profile_code}/presentations/{presentation_code}", response_model=FormPresentationRuntimeOut)
async def get_form_presentation(
    profile_code: str,
    presentation_code: str,
    intake_source_profile_id: Optional[str] = Query(None),
    db_tenant: tuple = Depends(get_db_with_tenant),
    _: None = Depends(require_trust_read()),
    __user=Depends(get_current_user),
) -> FormPresentationRuntimeOut:
    """Get Form Presentation Runtime schema for a profile + presentation code."""
    db, tenant_uuid = db_tenant
    try:
        payload = await resolve_form_presentation(
            db,
            tenant_id=str(tenant_uuid),
            entity_profile_code=profile_code,
            presentation_code=presentation_code,
            intake_source_profile_id=intake_source_profile_id,
        )
    except FormPresentationNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return FormPresentationRuntimeOut.model_validate(payload)

@router.get("/{profile_code}", response_model=EffectiveEntityProfileOut)
async def get_entity_profile(
    profile_code: str,
    include_presentations: bool = Query(False, description="Include intake presentation subsets"),
    db_tenant: tuple = Depends(get_db_with_tenant),
    _: None = Depends(require_trust_read()),
    __user=Depends(get_current_user),
) -> EffectiveEntityProfileOut:
    """Get read-only Entity Profile with Field Registry-backed field definitions."""
    db, tenant_uuid = db_tenant
    try:
        payload = await resolve_entity_profile_facade(
            db,
            tenant_id=str(tenant_uuid),
            entity_profile_code=profile_code,
            include_presentations=include_presentations,
        )
    except EntityProfileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return EffectiveEntityProfileOut.model_validate(payload)
