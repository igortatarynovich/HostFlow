"""Intake Source / Form Builder admin API (P6 read, P8 write)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, List, Literal, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator

from backend.app.auth.trust_role_deps import require_trust_admin, require_trust_read, require_trust_write
from backend.app.auth.deps import Role, UserCtx, get_current_user
from backend.app.db.deps import get_db_with_tenant
from backend.app.services.intake_form_admin_context import (
    build_intake_form_admin_context,
    run_intake_form_smoke_test,
)
from backend.app.services.intake_mapping_admin_service import (
    build_intake_form_mapping_context,
    preview_intake_form_mapping,
    save_intake_form_mapping,
    test_intake_form_mapping_ingest,
)
from backend.app.services.intake_form_write_service import (
    create_public_intake_form,
    list_selectable_entity_profiles,
    load_entity_profile_presentation_preset,
    update_public_intake_form,
    upsert_public_intake_form_presentation,
)
from backend.app.services.lead_forms_quota import normalize_and_validate_public_slug

router = APIRouter(prefix="/intake-forms", tags=["settings-intake-forms"])


def _ensure_tenant(ctx: UserCtx, tenant_id: str) -> None:
    token_tenant = (ctx.tenant_id or "").strip()
    if token_tenant and token_tenant != tenant_id:
        raise HTTPException(status_code=403, detail="Forbidden for tenant")


class EntityProfileOptionOut(BaseModel):
    code: str
    name: str
    entity_type: str
    scope: str


class EntityProfileFieldOptionOut(BaseModel):
    qualified_code: str
    label: str
    intake_level: str
    field_type: Optional[str] = None
    sort_order: int


class EntityProfileFieldsOut(BaseModel):
    code: str
    name: Optional[str] = None
    fields: List[EntityProfileFieldOptionOut] = Field(default_factory=list)


class EntityProfilePresentationPresetOut(BaseModel):
    entity_profile_code: str
    presentation_code: str
    profile_name: Optional[str] = None
    fields: List[PresentationFieldIn] = Field(default_factory=list)


class PresentationRuleConditionIn(BaseModel):
    source_field: str = Field(..., min_length=1, max_length=191)
    operator: Literal["eq", "neq", "truthy", "falsy", "in"] = "eq"
    value: Optional[Any] = None


class PresentationRulesIn(BaseModel):
    show_if: Optional[PresentationRuleConditionIn] = None
    hide_if: Optional[PresentationRuleConditionIn] = None
    required_if: Optional[PresentationRuleConditionIn] = None
    readonly_if: Optional[PresentationRuleConditionIn] = None


class PresentationFieldIn(BaseModel):
    qualified_code: str = Field(..., min_length=1, max_length=191)
    label_override: Optional[str] = Field(default=None, max_length=255)
    intake_level: Literal["required", "optional", "hidden"] = "optional"
    sort_order: Optional[int] = None
    widget_hint: Optional[str] = Field(default=None, max_length=64)
    presentation_rules: Optional[PresentationRulesIn] = None


class IntakeFormCreateIn(BaseModel):
    title: str = Field(..., min_length=1, max_length=256)
    public_slug: str = Field(..., min_length=2, max_length=64)
    entity_profile_code: str = Field(..., min_length=1, max_length=128)
    fields: List[PresentationFieldIn] = Field(..., min_length=1)
    is_active: bool = True

    @field_validator("public_slug")
    @classmethod
    def _normalize_slug(cls, value: str) -> str:
        try:
            normalized = normalize_and_validate_public_slug(value)
        except ValueError as exc:
            raise ValueError(str(exc)) from exc
        if not normalized:
            raise ValueError("public_slug is required")
        return normalized


class IntakeFormPatchIn(BaseModel):
    title: Optional[str] = Field(default=None, max_length=256)
    public_slug: Optional[str] = Field(default=None, max_length=64)
    is_active: Optional[bool] = None
    entity_profile_code: Optional[str] = Field(default=None, max_length=128)
    lifecycle_status: Optional[Literal["draft", "active", "archived"]] = None

    @field_validator("public_slug")
    @classmethod
    def _normalize_slug(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        try:
            return normalize_and_validate_public_slug(value)
        except ValueError as exc:
            raise ValueError(str(exc)) from exc


class IntakeFormPresentationIn(BaseModel):
    entity_profile_code: str = Field(..., min_length=1, max_length=128)
    fields: List[PresentationFieldIn] = Field(..., min_length=1)


class IntakeFormSummaryOut(BaseModel):
    id: str
    title: str
    public_slug: Optional[str] = None
    is_active: bool
    entity_profile_code: Optional[str] = None
    intake_source_profile_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class IntakeFormDetailOut(BaseModel):
    form: dict[str, Any]
    intake_source_profile: Optional[dict[str, Any]] = None
    intake_source_profile_id: Optional[str] = None
    entity_profile: dict[str, Any]
    presentation: dict[str, Any]
    presentations_available: List[dict[str, Any]] = Field(default_factory=list)
    submit_destination: dict[str, Any]
    form_definition: Optional[dict[str, Any]] = None
    forms_platform: Optional[dict[str, Any]] = None


class IntakeFormSmokeTestOut(BaseModel):
    lead_id: str
    candidate_id: Optional[str] = None
    token: str
    expires_at: datetime
    contacts: dict[str, Any]
    stage: Optional[str] = None
    message: str


class MappingRuleIn(BaseModel):
    source: str | List[str]
    qualified_field_code: Optional[str] = Field(default=None, max_length=191)
    target: str = Field(default="", max_length=128)
    format: Literal["string", "lower", "upper", "csv"] = "string"
    overwrite: bool = True


class IntakeFormMappingOut(BaseModel):
    form_id: str
    public_slug: Optional[str] = None
    entity_profile_code: Optional[str] = None
    provider: str
    intake_source_profile_id: Optional[str] = None
    mapping_rules: List[dict[str, Any]] = Field(default_factory=list)
    provider_bindings: List[dict[str, Any]] = Field(default_factory=list)
    validation: Optional[dict[str, Any]] = None


class IntakeFormMappingPutIn(BaseModel):
    mapping_rules: List[MappingRuleIn] = Field(default_factory=list)


class IntakeFormMappingPreviewIn(BaseModel):
    sample_payload: dict[str, Any] = Field(default_factory=dict)
    mapping_rules: Optional[List[MappingRuleIn]] = None


class IntakeFormMappingPreviewOut(BaseModel):
    source_fields: List[dict[str, Any]]
    normalized_payload: dict[str, Any]
    ingest_envelope_v1: dict[str, Any]
    mapping_validation: dict[str, Any]
    accepted_rules: List[dict[str, Any]]


class IntakeFormMappingTestIn(BaseModel):
    sample_payload: dict[str, Any] = Field(default_factory=dict)
    mapping_rules: Optional[List[MappingRuleIn]] = None


class IntakeFormMappingTestOut(BaseModel):
    lead_id: str
    candidate_id: Optional[str] = None
    token: str
    expires_at: datetime
    normalized_payload: dict[str, Any]
    ingest_envelope_v1: dict[str, Any]
    mapping_validation: dict[str, Any]
    message: str


@router.get(
    "/entity-profiles",
    response_model=list[EntityProfileOptionOut],
    dependencies=[Depends(require_trust_write())],
)
async def list_intake_form_entity_profiles(
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: tuple = Depends(get_db_with_tenant),
) -> list[EntityProfileOptionOut]:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    _ensure_tenant(ctx, tenant_id)
    rows = await list_selectable_entity_profiles(db, tenant_id=tenant_id)
    return [EntityProfileOptionOut.model_validate(row) for row in rows]


@router.get(
    "/entity-profiles/{profile_code}/fields",
    response_model=EntityProfileFieldsOut,
    dependencies=[Depends(require_trust_write())],
)
async def get_intake_form_entity_profile_fields(
    profile_code: str,
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: tuple = Depends(get_db_with_tenant),
) -> EntityProfileFieldsOut:
    from backend.app.entity_profile.exceptions import EntityProfileNotFoundError
    from backend.app.entity_profile.facade import resolve_entity_profile_facade
    from backend.app.entity_profile.presentation_runtime import _effective_label

    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    _ensure_tenant(ctx, tenant_id)
    code = str(profile_code or "").strip()
    try:
        profile_view = await resolve_entity_profile_facade(
            db,
            tenant_id=tenant_id,
            entity_profile_code=code,
            include_presentations=False,
        )
    except EntityProfileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    profile_meta = profile_view.get("profile") or {}
    fields_out: list[EntityProfileFieldOptionOut] = []
    for row in profile_view.get("fields") or []:
        if not isinstance(row, dict):
            continue
        qcode = str(row.get("qualified_code") or "").strip()
        if not qcode:
            continue
        embedded = row.get("field") if isinstance(row.get("field"), dict) else {}
        label = _effective_label(
            qualified_code=qcode,
            field_row=row,
            presentation_overrides={},
        )
        fields_out.append(
            EntityProfileFieldOptionOut(
                qualified_code=qcode,
                label=label,
                intake_level=str(row.get("intake_level") or "optional"),
                field_type=str(embedded.get("field_type") or "") or None,
                sort_order=int(row.get("sort_order") or 0),
            )
        )
    fields_out.sort(key=lambda f: f.sort_order)
    return EntityProfileFieldsOut(
        code=code,
        name=profile_meta.get("name"),
        fields=fields_out,
    )


@router.get(
    "/entity-profiles/{profile_code}/presentation-preset",
    response_model=EntityProfilePresentationPresetOut,
    dependencies=[Depends(require_trust_write())],
)
async def get_intake_form_entity_profile_presentation_preset(
    profile_code: str,
    presentation_code: Optional[str] = None,
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: tuple = Depends(get_db_with_tenant),
) -> EntityProfilePresentationPresetOut:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    _ensure_tenant(ctx, tenant_id)
    payload = await load_entity_profile_presentation_preset(
        db,
        tenant_id=tenant_id,
        entity_profile_code=str(profile_code or "").strip(),
        presentation_code=str(presentation_code or "").strip() or None,
    )
    return EntityProfilePresentationPresetOut.model_validate(payload)


@router.post(
    "",
    response_model=IntakeFormDetailOut,
    dependencies=[Depends(require_trust_admin())],
)
async def create_intake_form(
    payload: IntakeFormCreateIn,
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: tuple = Depends(get_db_with_tenant),
) -> IntakeFormDetailOut:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    _ensure_tenant(ctx, tenant_id)
    result = await create_public_intake_form(
        db,
        tenant_id=tenant_id,
        title=payload.title,
        public_slug=payload.public_slug,
        entity_profile_code=payload.entity_profile_code,
        fields=[f.model_dump(exclude_none=True) for f in payload.fields],
        is_active=payload.is_active,
    )
    return IntakeFormDetailOut.model_validate(result)


@router.get(
    "/{form_id}",
    response_model=IntakeFormDetailOut,
    dependencies=[Depends(require_trust_write())],
)
async def get_intake_form_detail(
    form_id: str,
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: tuple = Depends(get_db_with_tenant),
) -> IntakeFormDetailOut:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    _ensure_tenant(ctx, tenant_id)
    payload = await build_intake_form_admin_context(db, tenant_id=tenant_id, form_id=form_id)
    return IntakeFormDetailOut.model_validate(payload)


@router.patch(
    "/{form_id}",
    response_model=IntakeFormDetailOut,
    dependencies=[Depends(require_trust_admin())],
)
async def patch_intake_form(
    form_id: str,
    payload: IntakeFormPatchIn,
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: tuple = Depends(get_db_with_tenant),
) -> IntakeFormDetailOut:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    _ensure_tenant(ctx, tenant_id)
    data = payload.model_dump(exclude_unset=True)
    result = await update_public_intake_form(
        db,
        tenant_id=tenant_id,
        form_id=form_id,
        title=data.get("title"),
        public_slug=data.get("public_slug"),
        is_active=data.get("is_active"),
        entity_profile_code=data.get("entity_profile_code"),
        lifecycle_status=data.get("lifecycle_status"),
    )
    return IntakeFormDetailOut.model_validate(result)


@router.put(
    "/{form_id}/presentation",
    response_model=IntakeFormDetailOut,
    dependencies=[Depends(require_trust_admin())],
)
async def put_intake_form_presentation(
    form_id: str,
    payload: IntakeFormPresentationIn,
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: tuple = Depends(get_db_with_tenant),
) -> IntakeFormDetailOut:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    _ensure_tenant(ctx, tenant_id)
    result = await upsert_public_intake_form_presentation(
        db,
        tenant_id=tenant_id,
        form_id=form_id,
        entity_profile_code=payload.entity_profile_code,
        fields=[f.model_dump(exclude_none=True) for f in payload.fields],
    )
    return IntakeFormDetailOut.model_validate(result)


@router.get(
    "/{form_id}/mapping",
    response_model=IntakeFormMappingOut,
    dependencies=[Depends(require_trust_write())],
)
async def get_intake_form_mapping(
    form_id: str,
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: tuple = Depends(get_db_with_tenant),
) -> IntakeFormMappingOut:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    _ensure_tenant(ctx, tenant_id)
    payload = await build_intake_form_mapping_context(db, tenant_id=tenant_id, form_id=form_id)
    return IntakeFormMappingOut.model_validate(payload)


@router.put(
    "/{form_id}/mapping",
    response_model=IntakeFormMappingOut,
    dependencies=[Depends(require_trust_admin())],
)
async def put_intake_form_mapping(
    form_id: str,
    payload: IntakeFormMappingPutIn,
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: tuple = Depends(get_db_with_tenant),
) -> IntakeFormMappingOut:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    _ensure_tenant(ctx, tenant_id)
    rules = [r.model_dump() for r in payload.mapping_rules]
    result = await save_intake_form_mapping(
        db,
        tenant_id=tenant_id,
        form_id=form_id,
        mapping_rules=rules,
    )
    return IntakeFormMappingOut.model_validate(result)


@router.post(
    "/{form_id}/mapping/preview",
    response_model=IntakeFormMappingPreviewOut,
    dependencies=[Depends(require_trust_write())],
)
async def post_intake_form_mapping_preview(
    form_id: str,
    payload: IntakeFormMappingPreviewIn,
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: tuple = Depends(get_db_with_tenant),
) -> IntakeFormMappingPreviewOut:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    _ensure_tenant(ctx, tenant_id)
    rules = [r.model_dump() for r in payload.mapping_rules] if payload.mapping_rules is not None else None
    result = await preview_intake_form_mapping(
        db,
        tenant_id=tenant_id,
        form_id=form_id,
        raw_payload=payload.sample_payload,
        mapping_rules=rules,
    )
    return IntakeFormMappingPreviewOut.model_validate(result)


@router.post(
    "/{form_id}/mapping/test-ingest",
    response_model=IntakeFormMappingTestOut,
    dependencies=[Depends(require_trust_admin())],
)
async def post_intake_form_mapping_test_ingest(
    form_id: str,
    payload: IntakeFormMappingTestIn,
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: tuple = Depends(get_db_with_tenant),
) -> IntakeFormMappingTestOut:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    _ensure_tenant(ctx, tenant_id)
    rules = [r.model_dump() for r in payload.mapping_rules] if payload.mapping_rules is not None else None
    result = await test_intake_form_mapping_ingest(
        db,
        tenant_id=tenant_id,
        form_id=form_id,
        raw_payload=payload.sample_payload,
        mapping_rules=rules,
    )
    return IntakeFormMappingTestOut.model_validate(result)


@router.post(
    "/{form_id}/smoke-test",
    response_model=IntakeFormSmokeTestOut,
    dependencies=[Depends(require_trust_admin())],
)
async def smoke_test_intake_form(
    form_id: str,
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: tuple = Depends(get_db_with_tenant),
) -> IntakeFormSmokeTestOut:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    _ensure_tenant(ctx, tenant_id)
    payload = await run_intake_form_smoke_test(db, tenant_id=tenant_id, form_id=form_id)
    return IntakeFormSmokeTestOut.model_validate(payload)
