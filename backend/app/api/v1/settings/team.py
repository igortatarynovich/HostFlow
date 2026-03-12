from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Tuple
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.deps import Role, UserCtx, get_current_user, require_roles
from backend.app.api.v1.platform import schemas as platform_schemas
from backend.app.api.v1.tenants import service as tenant_service
from backend.app.db.deps import get_db_with_tenant
from backend.app.schemas.user import UserOut
from backend.app.services import users as users_service
from backend.app.services import tenant_branding


router = APIRouter(prefix="/team", tags=["settings-team"], redirect_slashes=False)


def _ensure_tenant(ctx: UserCtx, tenant_id: str) -> None:
    if (ctx.role or "").strip().lower() == Role.superadmin.value:
        return
    token_tenant = (ctx.tenant_id or "").strip()
    if token_tenant and token_tenant != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden for tenant")


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


@router.get(
    "",
    response_model=TeamOverviewResponse,
    dependencies=[Depends(require_roles(Role.administrator, Role.supervisor))],
)
async def get_team_overview(
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> TeamOverviewResponse:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    _ensure_tenant(ctx, tenant_id)
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
    dependencies=[Depends(require_roles(Role.administrator))],
)
async def update_branding(
    payload: TenantBrandingPatch,
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> TeamTenantSummary:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    _ensure_tenant(ctx, tenant_id)
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
    dependencies=[Depends(require_roles(Role.administrator))],
)
async def upload_branding_logo(
    file: UploadFile = File(...),
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> TeamTenantSummary:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    _ensure_tenant(ctx, tenant_id)
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
            require_roles(
                Role.administrator,
                Role.supervisor,
                Role.recruiter,
                Role.client_manager,
                Role.client_processor,
                Role.viewer,
            )
        )
    ],
)
async def get_module_settings(
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> TenantModuleSettings:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    _ensure_tenant(ctx, tenant_id)
    tenant = await tenant_service.get_tenant(db, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    modules = tenant_service.get_module_settings_snapshot(tenant)
    return TenantModuleSettings(**modules)


@router.get(
    "/module-matrix",
    response_model=TenantRoleModuleMatrix,
    dependencies=[Depends(require_roles(Role.administrator))],
)
async def get_module_matrix(
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> TenantRoleModuleMatrix:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    _ensure_tenant(ctx, tenant_id)
    tenant = await tenant_service.get_tenant(db, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    matrix = tenant_service.get_role_module_matrix_snapshot(tenant)
    return TenantRoleModuleMatrix.model_validate(matrix)


@router.get(
    "/module-matrix/effective",
    response_model=EffectiveRoleModules,
    dependencies=[
        Depends(
            require_roles(
                Role.administrator,
                Role.supervisor,
                Role.recruiter,
                Role.client_manager,
                Role.client_processor,
                Role.viewer,
            )
        )
    ],
)
async def get_effective_module_permissions(
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> EffectiveRoleModules:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    _ensure_tenant(ctx, tenant_id)
    tenant = await tenant_service.get_tenant(db, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    modules = tenant_service.get_effective_role_module_permissions(
        tenant,
        role=ctx.role,
        user_id=ctx.sub,
    )
    return EffectiveRoleModules(role=ctx.role, modules=modules)


@router.patch(
    "/modules",
    response_model=TenantModuleSettings,
    dependencies=[Depends(require_roles(Role.administrator))],
)
async def update_module_settings(
    payload: TenantModuleSettingsPatch,
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> TenantModuleSettings:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    _ensure_tenant(ctx, tenant_id)
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
    dependencies=[Depends(require_roles(Role.administrator))],
)
async def list_seat_requests(
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    limit: int = 50,
) -> List[SeatRequestOut]:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    _ensure_tenant(ctx, tenant_id)
    requests = await tenant_service.list_seat_requests(db, tenant_id, limit=limit)
    return [SeatRequestOut.model_validate(item) for item in requests]


@router.post(
    "/seat-requests",
    response_model=SeatRequestOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(Role.administrator))],
)
async def create_seat_request(
    payload: SeatRequestCreate,
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> SeatRequestOut:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    _ensure_tenant(ctx, tenant_id)
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
