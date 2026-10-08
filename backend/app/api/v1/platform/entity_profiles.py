"""Entity Profile Definition Registry API (P1–P2, ADR-043 authoring)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, List, Literal, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from backend.app.auth.deps import get_current_user
from backend.app.auth.hiring_workspace_roles import HIRING_CANDIDATE_PROFILE_READ_ROLES
from backend.app.auth.trust_role_deps import (
    require_trust_admin,
    require_trust_read,
    require_trust_write,
)
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
from backend.app.entity_profile.recruitment_policy import (
    RecruitmentProfilePolicy,
    load_recruitment_profile_policy,
)
from backend.app.entity_profile.recruitment_profile_authoring import (
    RecruitmentProfileAlreadyExistsError,
    RecruitmentProfileAuthoringError,
    RecruitmentProfileTemplateError,
    RecruitmentProfileVersionConflictError,
    create_recruitment_profile,
    publish_recruitment_profile_revision,
)
from backend.app.entity_profile.resolver import resolve_effective_entity_profile
from backend.app.models.entity_profile import EpEntityProfileVersion

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


class RecruitmentProfileFieldBindingIn(BaseModel):
    canonical_field_id: str
    qualified_code: str
    requirement_level: Literal["hidden", "optional", "required"]
    sort_order: int = 0


class RecruitmentProfileDocumentBindingIn(BaseModel):
    document_type_version_id: str
    requirement_level: Literal["hidden", "preferred", "required"]
    sort_order: int = 0


class RecruitmentProfileCreateIn(BaseModel):
    profile_code: str = Field(min_length=1)
    name: Optional[str] = None
    description: Optional[str] = None
    default_layout_code: Optional[str] = None
    config: Optional[dict[str, Any]] = None
    template_profile_code: Optional[str] = None
    fields: list[RecruitmentProfileFieldBindingIn] = Field(default_factory=list)
    documents: list[RecruitmentProfileDocumentBindingIn] = Field(default_factory=list)


class RecruitmentProfileRevisionIn(BaseModel):
    expected_published_version: int = Field(ge=1)
    fields: list[RecruitmentProfileFieldBindingIn] = Field(default_factory=list)
    documents: list[RecruitmentProfileDocumentBindingIn] = Field(default_factory=list)


class RecruitmentProfileFieldPolicyOut(BaseModel):
    canonical_field_id: str
    qualified_code: str
    requirement_level: str
    sort_order: int


class RecruitmentProfileDocumentPolicyOut(BaseModel):
    document_type_id: str
    document_type_code: str
    document_type_version_id: str
    document_type_version_code: str
    requirement_level: str
    sort_order: int


class RecruitmentProfilePublicationOut(BaseModel):
    entity_profile_id: str
    profile_version_id: str
    profile_code: str
    version: int
    tenant_id: str
    module_owner: str
    entity_type: str
    name: str
    description: Optional[str] = None
    default_layout_code: Optional[str] = None
    config: dict[str, Any] = Field(default_factory=dict)
    published_at: datetime
    fields: list[RecruitmentProfileFieldPolicyOut] = Field(default_factory=list)
    documents: list[RecruitmentProfileDocumentPolicyOut] = Field(default_factory=list)


def _binding_payloads(items: list[BaseModel]) -> list[dict[str, Any]]:
    return [item.model_dump() for item in items]


async def _load_recruitment_publication_out(
    db,
    *,
    tenant_id: str,
    profile_version_id: str,
) -> RecruitmentProfilePublicationOut:
    policy = await load_recruitment_profile_policy(
        db,
        tenant_id=tenant_id,
        profile_version_id=profile_version_id,
    )
    version = await db.scalar(
        select(EpEntityProfileVersion).where(
            EpEntityProfileVersion.id == profile_version_id,
            EpEntityProfileVersion.tenant_id == tenant_id,
        )
    )
    if version is None:
        raise EntityProfileNotFoundError(profile_version_id)
    return _recruitment_publication_out(version=version, policy=policy)


def _recruitment_publication_out(
    *,
    version: EpEntityProfileVersion,
    policy: RecruitmentProfilePolicy,
) -> RecruitmentProfilePublicationOut:
    return RecruitmentProfilePublicationOut(
        entity_profile_id=policy.entity_profile_id,
        profile_version_id=policy.profile_version_id,
        profile_code=policy.profile_code,
        version=policy.profile_version,
        tenant_id=policy.tenant_id,
        module_owner=policy.module_owner,
        entity_type=policy.entity_type,
        name=str(version.name),
        description=version.description,
        default_layout_code=version.default_layout_code,
        config=dict(version.config or {}),
        published_at=version.published_at,
        fields=[
            RecruitmentProfileFieldPolicyOut(
                canonical_field_id=item.canonical_field_id,
                qualified_code=item.qualified_code,
                requirement_level=item.requirement_level,
                sort_order=item.sort_order,
            )
            for item in policy.fields
        ],
        documents=[
            RecruitmentProfileDocumentPolicyOut(
                document_type_id=item.document_type_id,
                document_type_code=item.document_type_code,
                document_type_version_id=item.document_type_version_id,
                document_type_version_code=item.document_type_version_code,
                requirement_level=item.requirement_level,
                sort_order=item.sort_order,
            )
            for item in policy.documents
        ],
    )


async def _raise_recruitment_authoring_http(db, exc: Exception) -> None:
    await db.rollback()
    if isinstance(exc, RecruitmentProfileVersionConflictError):
        raise HTTPException(
            status_code=409,
            detail={
                "code": "recruitment_profile_version_conflict",
                "message": str(exc),
                "expected_version": exc.expected_version,
                "current_version": exc.current_version,
            },
        ) from exc
    if isinstance(exc, RecruitmentProfileAlreadyExistsError):
        raise HTTPException(
            status_code=409,
            detail={
                "code": "recruitment_profile_already_exists",
                "message": str(exc),
            },
        ) from exc
    if isinstance(exc, IntegrityError):
        raise HTTPException(
            status_code=409,
            detail={
                "code": "recruitment_profile_conflict",
                "message": "Recruitment Profile authoring conflict",
            },
        ) from exc
    if isinstance(exc, EntityProfileNotFoundError):
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if isinstance(exc, RecruitmentProfileTemplateError):
        code = "recruitment_profile_template_invalid"
    else:
        code = "recruitment_profile_authoring_invalid"
    raise HTTPException(
        status_code=422,
        detail={"code": code, "message": str(exc)},
    ) from exc

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


@router.post("/recruitment",
    response_model=RecruitmentProfilePublicationOut,
    status_code=201,
)
async def create_recruitment_profile_endpoint(
    body: RecruitmentProfileCreateIn,
    db_tenant: tuple = Depends(get_db_with_tenant),
    _role: str = Depends(require_trust_write()),
) -> RecruitmentProfilePublicationOut:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    try:
        published = await create_recruitment_profile(
            db,
            tenant_id=tenant_id,
            profile_code=body.profile_code,
            name=body.name,
            description=body.description,
            default_layout_code=body.default_layout_code,
            config=body.config,
            template_profile_code=body.template_profile_code,
            field_bindings=_binding_payloads(body.fields),
            document_bindings=_binding_payloads(body.documents),
        )
        profile_version_id = str(published.id)
        await db.commit()
    except (
        RecruitmentProfileAuthoringError,
        EntityProfileNotFoundError,
        IntegrityError,
        ValueError,
    ) as exc:
        await _raise_recruitment_authoring_http(db, exc)
    return await _load_recruitment_publication_out(
        db,
        tenant_id=tenant_id,
        profile_version_id=profile_version_id,
    )


@router.post("/recruitment/{entity_profile_id}/versions",
    response_model=RecruitmentProfilePublicationOut,
    status_code=201,
)
async def publish_recruitment_profile_revision_endpoint(
    entity_profile_id: str,
    body: RecruitmentProfileRevisionIn,
    db_tenant: tuple = Depends(get_db_with_tenant),
    _role: str = Depends(require_trust_write()),
) -> RecruitmentProfilePublicationOut:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    try:
        published = await publish_recruitment_profile_revision(
            db,
            tenant_id=tenant_id,
            entity_profile_id=entity_profile_id,
            expected_published_version=body.expected_published_version,
            field_bindings=_binding_payloads(body.fields),
            document_bindings=_binding_payloads(body.documents),
        )
        profile_version_id = str(published.id)
        await db.commit()
    except (
        RecruitmentProfileAuthoringError,
        EntityProfileNotFoundError,
        IntegrityError,
        ValueError,
    ) as exc:
        await _raise_recruitment_authoring_http(db, exc)
    return await _load_recruitment_publication_out(
        db,
        tenant_id=tenant_id,
        profile_version_id=profile_version_id,
    )

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
