from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, Dict, List, Optional, Tuple
from uuid import UUID

from fastapi import APIRouter, Body, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.trust_role_deps import require_trust_admin, require_trust_read, require_trust_write
from backend.app.auth.deps import Role, UserCtx, get_current_user
from backend.app.auth.tenant_scope import ensure_user_can_access_tenant
from backend.app.api.v1.platform import schemas as platform_schemas
from backend.app.api.v1.tenants import service as tenant_service
from backend.app.db.deps import get_db_with_tenant
from backend.app.models.tenant import TenantType
from backend.app.models.user import Role as UserRole
from backend.app.schemas.user import UserOut
from backend.app.services import users as users_service
from backend.app.services import tenant_branding
from backend.app.api.v1.settings.hiring_pipeline_gates_impl import (
    HIRING_GATES_READ_ROLES,
    HiringPipelineGatesPatch,
    HiringPipelineGatesPublicOut,
    get_hiring_pipeline_gates_core,
    patch_hiring_pipeline_gates_core,
)


router = APIRouter(prefix="/team", tags=["settings-team"], redirect_slashes=False)


class TeamOverviewResponse(BaseModel):
    members: list[UserOut]
    usage: platform_schemas.TenantUsageOut
    license: platform_schemas.TenantLicenseOut | None = None
    tenant: "TeamTenantSummary"
    modules: "TenantModuleSettings"


class TeamTenantSummary(BaseModel):
    id: UUID
    name: str
    slug: str
    workspace_label: str | None = None
    logo_url: str | None = None
    logo_meta: Dict[str, object] | None = None


class TenantBrandingPatch(BaseModel):
    workspace_label: str | None = Field(default=None, max_length=128)


class SeatRequestCreate(BaseModel):
    role: str = Field(..., min_length=2, max_length=64)
    requested_count: int = Field(..., gt=0, le=1000)
    message: str | None = Field(default=None, max_length=2000)


TenantModuleSettings = platform_schemas.TenantModuleSettings
TenantModuleSettingsPatch = platform_schemas.TenantModuleSettingsPatch
TenantRoleModuleMatrix = platform_schemas.TenantRoleModuleMatrix
EffectiveRoleModules = platform_schemas.EffectiveRoleModules
SeatRequestOut = platform_schemas.TenantSeatRequestOut


class VacancyRequirementsPresetIn(BaseModel):
    id: str = Field(..., min_length=1, max_length=64)
    label: str = Field(..., min_length=1, max_length=128)
    criteria: Dict[str, object] = Field(default_factory=dict)


class VacancyRequirementsPresetOut(BaseModel):
    id: str
    label: str
    criteria: Dict[str, object] = Field(default_factory=dict)
    updated_at: str | None = None


class VacancyRequirementsPresetListOut(BaseModel):
    items: list[VacancyRequirementsPresetOut]


class RiskModelV1SettingsOut(BaseModel):
    effective: Dict[str, Any]
    overrides: Dict[str, Any]


@router.get(
    "",
    response_model=TeamOverviewResponse,
    dependencies=[Depends(require_trust_write())],
)
async def get_team_overview(
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> TeamOverviewResponse:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    await ensure_user_can_access_tenant(db, ctx, tenant_id)
    tenant = await tenant_service.get_tenant(db, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    members_raw = await users_service.list_users(db, tenant_id)
    members = [UserOut(**entry) for entry in members_raw]
    license_entry = await tenant_service.get_tenant_license(db, tenant_id)
    usage = await tenant_service.get_usage_snapshot(db, tenant_id)
    license_model = (
        platform_schemas.TenantLicenseOut.model_validate(license_entry) if license_entry else None
    )
    modules = tenant_service.get_module_settings_snapshot(tenant)
    return TeamOverviewResponse(
        members=members,
        usage=platform_schemas.TenantUsageOut(**usage),
        license=license_model,
        tenant=TeamTenantSummary(
            id=UUID(tenant.id),
            name=tenant.name,
            slug=tenant.slug,
            workspace_label=tenant.workspace_label,
            logo_url=tenant.logo_url,
            logo_meta=tenant.logo_meta or None,
        ),
        modules=TenantModuleSettings(**modules),
    )


@router.patch(
    "/branding",
    response_model=TeamTenantSummary,
    dependencies=[Depends(require_trust_admin())],
)
async def update_branding(
    payload: TenantBrandingPatch,
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> TeamTenantSummary:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    await ensure_user_can_access_tenant(db, ctx, tenant_id)
    tenant = await tenant_service.get_tenant(db, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    updates: Dict[str, object] = {}
    if payload.workspace_label is not None:
        trimmed = payload.workspace_label.strip()
        updates["workspace_label"] = trimmed or None
    if updates:
        tenant = await tenant_service.update_tenant(db, tenant, updates)
    return TeamTenantSummary(
        id=UUID(tenant.id),
        name=tenant.name,
        slug=tenant.slug,
        workspace_label=tenant.workspace_label,
        logo_url=tenant.logo_url,
        logo_meta=tenant.logo_meta or None,
    )


@router.post(
    "/branding/logo",
    response_model=TeamTenantSummary,
    dependencies=[Depends(require_trust_admin())],
)
async def upload_branding_logo(
    file: UploadFile = File(...),
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> TeamTenantSummary:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    await ensure_user_can_access_tenant(db, ctx, tenant_id)
    tenant = await tenant_service.get_tenant(db, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    logo_url, logo_meta = await tenant_branding.save_tenant_logo(tenant_id, file)
    tenant = await tenant_service.update_tenant(
        db,
        tenant,
        {"logo_url": logo_url, "logo_meta": logo_meta},
    )
    return TeamTenantSummary(
        id=UUID(tenant.id),
        name=tenant.name,
        slug=tenant.slug,
        workspace_label=tenant.workspace_label,
        logo_url=tenant.logo_url,
        logo_meta=tenant.logo_meta or None,
    )


@router.get(
    "/modules",
    response_model=TenantModuleSettings,
    dependencies=[
        Depends(
            require_trust_read()
        )
    ],
)
async def get_module_settings(
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> TenantModuleSettings:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    await ensure_user_can_access_tenant(db, ctx, tenant_id)
    tenant = await tenant_service.get_tenant(db, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    modules = tenant_service.get_module_settings_snapshot(tenant)
    return TenantModuleSettings(**modules)


@router.get(
    "/vacancy-requirements-presets",
    response_model=VacancyRequirementsPresetListOut,
    dependencies=[Depends(require_trust_write())],
)
async def list_vacancy_requirements_presets(
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> VacancyRequirementsPresetListOut:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    await ensure_user_can_access_tenant(db, ctx, tenant_id)
    tenant = await tenant_service.get_tenant(db, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    items = tenant_service.get_vacancy_requirements_presets_snapshot(tenant)
    return VacancyRequirementsPresetListOut(items=[VacancyRequirementsPresetOut(**i) for i in items])


@router.put(
    "/vacancy-requirements-presets/{preset_id}",
    response_model=VacancyRequirementsPresetListOut,
    dependencies=[Depends(require_trust_write())],
)
async def upsert_vacancy_requirements_preset(
    preset_id: str,
    payload: VacancyRequirementsPresetIn,
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> VacancyRequirementsPresetListOut:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    await ensure_user_can_access_tenant(db, ctx, tenant_id)
    tenant = await tenant_service.get_tenant(db, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    try:
        items = await tenant_service.upsert_vacancy_requirements_preset(
            db,
            tenant,
            preset_id=preset_id,
            label=payload.label,
            criteria=dict(payload.criteria or {}),
            actor_id=str(ctx.sub or "").strip() or None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return VacancyRequirementsPresetListOut(items=[VacancyRequirementsPresetOut(**i) for i in items])


@router.delete(
    "/vacancy-requirements-presets/{preset_id}",
    response_model=VacancyRequirementsPresetListOut,
    dependencies=[Depends(require_trust_write())],
)
async def delete_vacancy_requirements_preset(
    preset_id: str,
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> VacancyRequirementsPresetListOut:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    await ensure_user_can_access_tenant(db, ctx, tenant_id)
    tenant = await tenant_service.get_tenant(db, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    try:
        items = await tenant_service.delete_vacancy_requirements_preset(
            db,
            tenant,
            preset_id=preset_id,
            actor_id=str(ctx.sub or "").strip() or None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return VacancyRequirementsPresetListOut(items=[VacancyRequirementsPresetOut(**i) for i in items])

@router.get(
    "/module-matrix",
    response_model=TenantRoleModuleMatrix,
    dependencies=[Depends(require_trust_admin())],
)
async def get_module_matrix(
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> TenantRoleModuleMatrix:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    await ensure_user_can_access_tenant(db, ctx, tenant_id)
    tenant = await tenant_service.get_tenant(db, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    matrix = tenant_service.get_role_module_matrix_snapshot(tenant)
    return TenantRoleModuleMatrix.model_validate(matrix)


@router.patch(
    "/module-matrix",
    response_model=TenantRoleModuleMatrix,
    dependencies=[Depends(require_trust_admin())],
)
async def patch_module_matrix(
    payload: platform_schemas.TenantRoleModuleMatrixPatch,
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> TenantRoleModuleMatrix:
    """Tenant admin edits operational role×module matrix within ADR-036 trust ceilings."""
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    await ensure_user_can_access_tenant(db, ctx, tenant_id)
    tenant = await tenant_service.get_tenant(db, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        matrix = tenant_service.get_role_module_matrix_snapshot(tenant)
    else:
        try:
            matrix = await tenant_service.update_role_module_matrix(
                db,
                tenant,
                updates,  # type: ignore[arg-type]
                actor_id=ctx.sub,
                actor_is_superadmin=False,
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
    return TenantRoleModuleMatrix.model_validate(matrix)


class PermissionPresetOut(BaseModel):
    id: str
    trust_role: str
    modules: Dict[str, Dict[str, bool]]


class PermissionPresetListOut(BaseModel):
    items: List[PermissionPresetOut]


class PermissionPresetApplyUserIn(BaseModel):
    user_id: str = Field(..., min_length=1)


class PermissionPresetApplyMatrixIn(BaseModel):
    target: str = Field(default="employee", description="Trust matrix column to fill (employee only).")


@router.get(
    "/permission-presets",
    response_model=PermissionPresetListOut,
    dependencies=[Depends(require_trust_admin())],
)
async def list_permission_presets(
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> PermissionPresetListOut:
    from backend.app.auth.trust_roles import (
        get_permission_preset,
        list_permission_preset_ids,
        trust_role_for_preset,
    )

    db, tenant_uuid = db_tenant
    await ensure_user_can_access_tenant(db, ctx, str(tenant_uuid))
    items = [
        PermissionPresetOut(
            id=pid,
            trust_role=trust_role_for_preset(pid),
            modules=get_permission_preset(pid),
        )
        for pid in list_permission_preset_ids()
    ]
    return PermissionPresetListOut(items=items)


@router.post(
    "/permission-presets/{preset_id}/apply-user",
    response_model=platform_schemas.TenantUserModuleOverrides,
    dependencies=[Depends(require_trust_admin())],
)
async def apply_permission_preset_to_user(
    preset_id: str,
    payload: PermissionPresetApplyUserIn,
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> platform_schemas.TenantUserModuleOverrides:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    await ensure_user_can_access_tenant(db, ctx, tenant_id)
    tenant = await tenant_service.get_tenant(db, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    try:
        overrides = await tenant_service.apply_permission_preset_to_user(
            db,
            tenant,
            user_id=payload.user_id,
            preset_id=preset_id,
            actor_id=ctx.sub,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return platform_schemas.TenantUserModuleOverrides.model_validate({"users": overrides})


@router.post(
    "/permission-presets/{preset_id}/apply-matrix",
    response_model=TenantRoleModuleMatrix,
    dependencies=[Depends(require_trust_admin())],
)
async def apply_permission_preset_to_matrix(
    preset_id: str,
    payload: PermissionPresetApplyMatrixIn | None = None,
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> TenantRoleModuleMatrix:
    """Apply a starter-pack preset onto the Employee matrix column (not a new system role)."""
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    await ensure_user_can_access_tenant(db, ctx, tenant_id)
    tenant = await tenant_service.get_tenant(db, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    target = (payload.target if payload else "employee") or "employee"
    if target != "employee":
        raise HTTPException(status_code=422, detail="preset_matrix_target_must_be_employee")
    try:
        matrix = await tenant_service.apply_permission_preset_to_employee_matrix(
            db,
            tenant,
            preset_id=preset_id,
            actor_id=ctx.sub,
            actor_is_superadmin=False,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return TenantRoleModuleMatrix.model_validate(matrix)


@router.get(
    "/module-matrix/effective",
    response_model=EffectiveRoleModules,
    dependencies=[
        Depends(
            require_trust_read()
        )
    ],
)
async def get_effective_module_permissions(
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> EffectiveRoleModules:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    await ensure_user_can_access_tenant(db, ctx, tenant_id)
    tenant = await tenant_service.get_tenant(db, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    # Match frontend usePermissions: on client (company) workspaces, JWT role "recruiter"
    # is treated as client-side hiring staff; permissions use client_processor matrix there.
    # Using recruiter cells here made documents.manage false when only client_processor had
    # documents editable in the role matrix.
    role_for_matrix = str(ctx.role or "").strip().lower()
    if getattr(tenant, "type", None) == TenantType.company and role_for_matrix == UserRole.recruiter.value:
        role_for_matrix = UserRole.client_processor.value
    if role_for_matrix == "employee":
        # Prefer employee matrix column when present
        pass
    modules = tenant_service.get_effective_role_module_permissions(
        tenant,
        role=role_for_matrix,
        user_id=ctx.sub,
    )
    return EffectiveRoleModules(role=ctx.role, modules=modules)


@router.patch(
    "/modules",
    response_model=TenantModuleSettings,
    dependencies=[Depends(require_trust_admin())],
)
async def update_module_settings(
    payload: TenantModuleSettingsPatch,
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> TenantModuleSettings:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    await ensure_user_can_access_tenant(db, ctx, tenant_id)
    tenant = await tenant_service.get_tenant(db, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    updates = payload.model_dump(exclude_unset=True)
    try:
        modules = await tenant_service.update_module_settings(
            db,
            tenant,
            updates,
            actor_id=ctx.sub,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return TenantModuleSettings(**modules)


@router.get(
    "/seat-requests",
    response_model=List[SeatRequestOut],
    dependencies=[Depends(require_trust_admin())],
)
async def list_seat_requests(
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    limit: int = 50,
) -> List[SeatRequestOut]:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    await ensure_user_can_access_tenant(db, ctx, tenant_id)
    requests = await tenant_service.list_seat_requests(db, tenant_id, limit=limit)
    return [SeatRequestOut.model_validate(item) for item in requests]


@router.post(
    "/seat-requests",
    response_model=SeatRequestOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_trust_admin())],
)
async def create_seat_request(
    payload: SeatRequestCreate,
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> SeatRequestOut:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    await ensure_user_can_access_tenant(db, ctx, tenant_id)
    if not ctx.sub:
        raise HTTPException(status_code=400, detail="Missing actor")
    try:
        entry = await tenant_service.create_seat_request(
            db,
            tenant_id,
            requested_by=ctx.sub,
            role=payload.role,
            requested_count=payload.requested_count,
            message=payload.message,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return SeatRequestOut.model_validate(entry)


@router.get(
    "/hiring-pipeline-gates",
    response_model=HiringPipelineGatesPublicOut,
    dependencies=[Depends(require_trust_read())],
)
async def get_hiring_pipeline_gates(
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> HiringPipelineGatesPublicOut:
    return await get_hiring_pipeline_gates_core(ctx, db_tenant)


@router.patch(
    "/hiring-pipeline-gates",
    response_model=HiringPipelineGatesPublicOut,
    dependencies=[Depends(require_trust_admin())],
)
async def patch_hiring_pipeline_gates(
    payload: HiringPipelineGatesPatch,
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> HiringPipelineGatesPublicOut:
    return await patch_hiring_pipeline_gates_core(payload, ctx, db_tenant)


@router.get(
    "/transfer-policy",
    dependencies=[Depends(require_trust_write())],
)
async def get_transfer_policy_settings(
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> dict:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    await ensure_user_can_access_tenant(db, ctx, tenant_id)
    from backend.app.services.transfer_policy_resolver import resolve_tenant_transfer_policy_summary

    return await resolve_tenant_transfer_policy_summary(db, tenant_id=tenant_id)


@router.get(
    "/risk-model-v1",
    response_model=RiskModelV1SettingsOut,
    dependencies=[Depends(require_trust_read())],
)
async def get_risk_model_v1_settings(
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> RiskModelV1SettingsOut:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    await ensure_user_can_access_tenant(db, ctx, tenant_id)
    tenant = await tenant_service.get_tenant(db, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    view = await tenant_service.get_risk_model_v1_settings_view(db, tenant)
    return RiskModelV1SettingsOut(**view)


@router.patch(
    "/risk-model-v1",
    response_model=RiskModelV1SettingsOut,
    dependencies=[Depends(require_trust_admin())],
)
async def patch_risk_model_v1_settings(
    payload: Annotated[Dict[str, Any], Body()],
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> RiskModelV1SettingsOut:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    await ensure_user_can_access_tenant(db, ctx, tenant_id)
    tenant = await tenant_service.get_tenant(db, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    if not isinstance(payload, dict):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Body must be a JSON object",
        )
    try:
        view = await tenant_service.patch_risk_model_v1_settings(db, tenant, payload)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    return RiskModelV1SettingsOut(**view)
