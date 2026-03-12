from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import List, Tuple
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.deps import (
    Role,
    UserCtx,
    get_current_user,
    require_superadmin,
)
from backend.app.auth.jwt_tools import encode as encode_jwt
from backend.app.db.deps import get_db
from backend.app.api.v1.platform import schemas as platform_schemas
from backend.app.api.v1.tenants import service as tenant_service
from backend.app.models.tenant import (
    Tenant,
    TenantLicense,
    TenantSeatRequestStatus,
    TenantStatus,
    TenantType,
)
from backend.app.schemas.user import UserOut
from backend.app.services import tenant_branding, users as users_service
from backend.app.services.users import UserServiceError


router = APIRouter(
    prefix="/platform/tenants",
    tags=["platform-tenants"],
    redirect_slashes=False,
)


def _serialize_tenant(
    tenant: Tenant,
    license_entry: TenantLicense | None,
    usage: dict[str, float],
) -> platform_schemas.PlatformTenantOut:
    license_model = (
        platform_schemas.TenantLicenseOut.model_validate(license_entry)
        if license_entry
        else None
    )
    usage_model = platform_schemas.TenantUsageOut(**usage)
    return platform_schemas.PlatformTenantOut(
        id=UUID(str(tenant.id)),
        name=tenant.name,
        slug=tenant.slug,
        type=tenant.type,
        status=tenant.status,
        parent_tenant_id=UUID(str(tenant.parent_tenant_id))
        if tenant.parent_tenant_id
        else None,
        client_portal_enabled=tenant.client_portal_enabled,
        status_sharing_allowed=tenant.status_sharing_allowed,
        description=tenant.description,
        workspace_label=tenant.workspace_label,
        logo_url=tenant.logo_url,
        logo_meta=tenant.logo_meta,
        created_at=tenant.created_at,
        updated_at=tenant.updated_at,
        license=license_model,
        usage=usage_model,
    )


def _convert_uuid(value: UUID | None) -> str | None:
    return str(value) if value else None


def _tenant_payload_from_request(
    payload: platform_schemas.TenantProvisionIn,
) -> dict:
    return {
        "name": payload.name.strip(),
        "slug": payload.slug,
        "type": payload.type,
        "status": payload.status,
        "parent_tenant_id": _convert_uuid(payload.parent_tenant_id),
        "client_portal_enabled": payload.client_portal_enabled,
        "status_sharing_allowed": payload.status_sharing_allowed,
        "description": payload.description,
        "settings": payload.settings or {},
        "workspace_label": payload.workspace_label.strip() if payload.workspace_label else None,
        "logo_url": payload.logo_url,
        "logo_meta": payload.logo_meta or None,
    }


async def _create_tenant_admin_user(
    db: AsyncSession,
    *,
    tenant_id: str,
    actor_id: str | None,
    admin_payload: platform_schemas.TenantAdminCreate,
) -> platform_schemas.PlatformTenantAdminOut:
    try:
        entry, generated_password = await users_service.create_user(
            db,
            tenant_id=tenant_id,
            actor_id=actor_id,
            email=admin_payload.email,
            role="administrator",
            full_name=admin_payload.full_name,
            short_id=None,
            password=admin_payload.password,
            supervisor_id=None,
            company_ids=[],
        )
        await db.commit()
    except UserServiceError as exc:
        await db.rollback()
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    return platform_schemas.PlatformTenantAdminOut(
        user=UserOut(**entry),
        temporary_password=generated_password,
    )


@router.get(
    "",
    response_model=platform_schemas.PlatformTenantList,
    dependencies=[Depends(require_superadmin())],
)
async def list_platform_tenants(
    status: List[TenantStatus] | None = Query(default=None),
    tenant_type: List[TenantType] | None = Query(default=None),
    plan: List[str] | None = Query(default=None),
    q: str | None = Query(default=None, alias="search"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> platform_schemas.PlatformTenantList:
    rows, total = await tenant_service.list_tenants_with_licenses(
        db,
        statuses=status,
        tenant_types=tenant_type,
        plans=plan,
        search=q,
        limit=limit,
        offset=offset,
    )
    items = [_serialize_tenant(t, lic, usage) for t, lic, usage in rows]
    return platform_schemas.PlatformTenantList(total=total, items=items)


@router.get(
    "/{tenant_id}",
    response_model=platform_schemas.PlatformTenantOut,
    dependencies=[Depends(require_superadmin())],
)
async def get_platform_tenant(
    tenant_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> platform_schemas.PlatformTenantOut:
    tenant_data = await tenant_service.get_tenant_with_details(db, str(tenant_id))
    if tenant_data is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    tenant, license_entry, usage = tenant_data
    return _serialize_tenant(tenant, license_entry, usage)


@router.post(
    "",
    response_model=platform_schemas.PlatformTenantOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_superadmin())],
)
async def create_platform_tenant(
    payload: platform_schemas.TenantProvisionIn,
    ctx: UserCtx = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> platform_schemas.PlatformTenantOut:
    tenant_payload = _tenant_payload_from_request(payload)
    license_payload = payload.license.model_dump()
    try:
        tenant, license_entry = await tenant_service.create_tenant_with_license(
            db,
            tenant_payload=tenant_payload,
            license_payload=license_payload,
        )
    except ValueError as exc:
        key = str(exc)
        if key == "invalid_slug":
            raise HTTPException(status_code=422, detail="Invalid slug") from exc
        if key == "slug_exists":
            raise HTTPException(status_code=409, detail="Slug already in use") from exc
        raise
    usage = await tenant_service.get_usage_snapshot(db, tenant.id)

    if payload.initial_admin:
        await _create_tenant_admin_user(
            db,
            tenant_id=str(tenant.id),
            actor_id=ctx.sub,
            admin_payload=payload.initial_admin,
        )

    return _serialize_tenant(tenant, license_entry, usage)


@router.get(
    "/{tenant_id}/modules",
    response_model=platform_schemas.TenantModuleSettings,
    dependencies=[Depends(require_superadmin())],
)
async def get_platform_tenant_modules(
    tenant_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> platform_schemas.TenantModuleSettings:
    tenant = await tenant_service.get_tenant(db, str(tenant_id))
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    modules = tenant_service.get_module_settings_snapshot(tenant)
    return platform_schemas.TenantModuleSettings(**modules)


@router.patch(
    "/{tenant_id}/modules",
    response_model=platform_schemas.TenantModuleSettings,
    dependencies=[Depends(require_superadmin())],
)
async def update_platform_tenant_modules(
    tenant_id: UUID,
    payload: platform_schemas.TenantModuleSettingsPatch,
    ctx: UserCtx = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> platform_schemas.TenantModuleSettings:
    tenant = await tenant_service.get_tenant(db, str(tenant_id))
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        modules = tenant_service.get_module_settings_snapshot(tenant)
    else:
        modules = await tenant_service.update_module_settings(
            db,
            tenant,
            updates,
            actor_id=ctx.sub,
        )
    return platform_schemas.TenantModuleSettings(**modules)


@router.get(
    "/{tenant_id}/module-matrix",
    response_model=platform_schemas.TenantRoleModuleMatrix,
    dependencies=[Depends(require_superadmin())],
)
async def get_platform_tenant_module_matrix(
    tenant_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> platform_schemas.TenantRoleModuleMatrix:
    tenant = await tenant_service.get_tenant(db, str(tenant_id))
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    matrix = tenant_service.get_role_module_matrix_snapshot(tenant)
    return platform_schemas.TenantRoleModuleMatrix.model_validate(matrix)


@router.patch(
    "/{tenant_id}/module-matrix",
    response_model=platform_schemas.TenantRoleModuleMatrix,
    dependencies=[Depends(require_superadmin())],
)
async def update_platform_tenant_module_matrix(
    tenant_id: UUID,
    payload: platform_schemas.TenantRoleModuleMatrixPatch,
    ctx: UserCtx = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> platform_schemas.TenantRoleModuleMatrix:
    tenant = await tenant_service.get_tenant(db, str(tenant_id))
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        matrix = tenant_service.get_role_module_matrix_snapshot(tenant)
    else:
        matrix = await tenant_service.update_role_module_matrix(
            db,
            tenant,
            updates,  # type: ignore[arg-type]
            actor_id=ctx.sub,
        )
    return platform_schemas.TenantRoleModuleMatrix.model_validate(matrix)


@router.get(
    "/{tenant_id}/module-overrides/users",
    response_model=List[UserOut],
    dependencies=[Depends(require_superadmin())],
)
async def list_platform_tenant_override_users(
    tenant_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> List[UserOut]:
    tenant = await tenant_service.get_tenant(db, str(tenant_id))
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    members_raw = await users_service.list_users(db, str(tenant_id))
    return [UserOut(**entry) for entry in members_raw if entry.get("user_id")]


@router.get(
    "/{tenant_id}/module-overrides",
    response_model=platform_schemas.TenantUserModuleOverrides,
    dependencies=[Depends(require_superadmin())],
)
async def get_platform_tenant_user_module_overrides(
    tenant_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> platform_schemas.TenantUserModuleOverrides:
    tenant = await tenant_service.get_tenant(db, str(tenant_id))
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    members_raw = await users_service.list_users(db, str(tenant_id))
    allowed_user_ids = {str(entry.get("user_id") or "").strip() for entry in members_raw}
    allowed_user_ids.discard("")
    overrides = tenant_service.get_user_module_overrides_snapshot(
        tenant,
        allowed_user_ids=allowed_user_ids,
    )
    return platform_schemas.TenantUserModuleOverrides(users=overrides)


@router.patch(
    "/{tenant_id}/module-overrides",
    response_model=platform_schemas.TenantUserModuleOverrides,
    dependencies=[Depends(require_superadmin())],
)
async def update_platform_tenant_user_module_overrides(
    tenant_id: UUID,
    payload: platform_schemas.TenantUserModuleOverridesPatch,
    ctx: UserCtx = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> platform_schemas.TenantUserModuleOverrides:
    tenant = await tenant_service.get_tenant(db, str(tenant_id))
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    members_raw = await users_service.list_users(db, str(tenant_id))
    allowed_user_ids = {str(entry.get("user_id") or "").strip() for entry in members_raw}
    allowed_user_ids.discard("")
    updates = payload.model_dump(exclude_unset=True).get("users", {})
    try:
        if not updates:
            overrides = tenant_service.get_user_module_overrides_snapshot(
                tenant,
                allowed_user_ids=allowed_user_ids,
            )
        else:
            overrides = await tenant_service.update_user_module_overrides(
                db,
                tenant,
                updates,  # type: ignore[arg-type]
                actor_id=ctx.sub,
                allowed_user_ids=allowed_user_ids,
            )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return platform_schemas.TenantUserModuleOverrides(users=overrides)


@router.patch(
    "/{tenant_id}",
    response_model=platform_schemas.PlatformTenantOut,
    dependencies=[Depends(require_superadmin())],
)
async def patch_platform_tenant(
    tenant_id: UUID,
    payload: platform_schemas.PlatformTenantPatch,
    db: AsyncSession = Depends(get_db),
) -> platform_schemas.PlatformTenantOut:
    tenant_data = await tenant_service.get_tenant_with_details(db, str(tenant_id))
    if tenant_data is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    tenant, license_entry, usage = tenant_data
    updates = payload.model_dump(exclude_unset=True)
    if "name" in updates and updates["name"]:
        updates["name"] = updates["name"].strip()
    if "workspace_label" in updates and updates["workspace_label"]:
        updates["workspace_label"] = updates["workspace_label"].strip()
    if updates:
        tenant = await tenant_service.update_tenant(db, tenant, updates)
    return _serialize_tenant(tenant, license_entry, usage)


@router.post(
    "/{tenant_id}/logo",
    response_model=platform_schemas.PlatformTenantOut,
    dependencies=[Depends(require_superadmin())],
)
async def upload_platform_tenant_logo(
    tenant_id: UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
) -> platform_schemas.PlatformTenantOut:
    tenant_data = await tenant_service.get_tenant_with_details(db, str(tenant_id))
    if tenant_data is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    tenant, license_entry, usage = tenant_data
    logo_url, logo_meta = await tenant_branding.save_tenant_logo(str(tenant_id), file)
    tenant = await tenant_service.update_tenant(
        db,
        tenant,
        {
            "logo_url": logo_url,
            "logo_meta": logo_meta,
        },
    )
    return _serialize_tenant(tenant, license_entry, usage)


@router.post(
    "/{tenant_id}/admins",
    response_model=platform_schemas.PlatformTenantAdminOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_superadmin())],
)
async def create_tenant_admin(
    tenant_id: UUID,
    payload: platform_schemas.TenantAdminCreate,
    ctx: UserCtx = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> platform_schemas.PlatformTenantAdminOut:
    tenant = await tenant_service.get_tenant(db, str(tenant_id))
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return await _create_tenant_admin_user(
        db,
        tenant_id=str(tenant_id),
        actor_id=ctx.sub,
        admin_payload=payload,
    )


@router.get(
    "/{tenant_id}/vacancies",
    response_model=platform_schemas.TenantVacancyAccessList,
    dependencies=[Depends(require_superadmin())],
)
async def list_tenant_shared_vacancies(
    tenant_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> platform_schemas.TenantVacancyAccessList:
    tenant = await tenant_service.get_tenant(db, str(tenant_id))
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    rows = await tenant_service.list_tenant_vacancy_access(db, str(tenant_id))
    items = [
        platform_schemas.TenantVacancyAccessItem(
            vacancy_id=UUID(row["vacancy_id"]),
            title=row["title"],
            company_name=row.get("company_name"),
            status=row.get("status"),
        )
        for row in rows
    ]
    return platform_schemas.TenantVacancyAccessList(items=items)


@router.put(
    "/{tenant_id}/vacancies",
    response_model=platform_schemas.TenantVacancyAccessList,
    dependencies=[Depends(require_superadmin())],
)
async def update_tenant_shared_vacancies(
    tenant_id: UUID,
    payload: platform_schemas.TenantVacancyAccessUpdate,
    db: AsyncSession = Depends(get_db),
) -> platform_schemas.TenantVacancyAccessList:
    tenant = await tenant_service.get_tenant(db, str(tenant_id))
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    try:
        await tenant_service.set_tenant_vacancy_access(
            db,
            tenant_id=str(tenant_id),
            vacancy_ids=[str(v) for v in payload.vacancy_ids],
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    rows = await tenant_service.list_tenant_vacancy_access(db, str(tenant_id))
    items = [
        platform_schemas.TenantVacancyAccessItem(
            vacancy_id=UUID(row["vacancy_id"]),
            title=row["title"],
            company_name=row.get("company_name"),
            status=row.get("status"),
        )
        for row in rows
    ]
    return platform_schemas.TenantVacancyAccessList(items=items)


@router.get(
    "/{tenant_id}/vacancy-options",
    response_model=list[platform_schemas.TenantVacancyOption],
    dependencies=[Depends(require_superadmin())],
)
async def list_tenant_vacancy_options(
    tenant_id: UUID,
    search: str | None = Query(default=None, min_length=1, max_length=120),
    limit: int = Query(default=25, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> list[platform_schemas.TenantVacancyOption]:
    tenant = await tenant_service.get_tenant(db, str(tenant_id))
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    rows = await tenant_service.list_shareable_vacancies(
        db,
        str(tenant_id),
        search=search,
        limit=limit,
    )
    return [
        platform_schemas.TenantVacancyOption(
            vacancy_id=UUID(row["vacancy_id"]),
            title=row["title"],
            company_name=row.get("company_name"),
            tenant_id=UUID(row["tenant_id"]) if row.get("tenant_id") else tenant_id,
            status=row.get("status"),
        )
        for row in rows
    ]


@router.get(
    "/{tenant_id}/seat-requests",
    response_model=list[platform_schemas.TenantSeatRequestOut],
    dependencies=[Depends(require_superadmin())],
)
async def list_platform_seat_requests(
    tenant_id: UUID,
    status: TenantSeatRequestStatus | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> list[platform_schemas.TenantSeatRequestOut]:
    tenant = await tenant_service.get_tenant(db, str(tenant_id))
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    rows = await tenant_service.list_seat_requests(
        db,
        str(tenant_id),
        status=status,
        limit=200,
    )
    return [platform_schemas.TenantSeatRequestOut.model_validate(item) for item in rows]


@router.post(
    "/{tenant_id}/seat-requests/{request_id}/decision",
    response_model=platform_schemas.TenantSeatRequestOut,
    dependencies=[Depends(require_superadmin())],
)
async def decide_seat_request(
    tenant_id: UUID,
    request_id: UUID,
    payload: platform_schemas.TenantSeatRequestDecision,
    ctx: UserCtx = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> platform_schemas.TenantSeatRequestOut:
    tenant = await tenant_service.get_tenant(db, str(tenant_id))
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    entry = await tenant_service.get_seat_request(db, str(tenant_id), str(request_id))
    if entry is None:
        raise HTTPException(status_code=404, detail="Seat request not found")
    try:
        target_status = TenantSeatRequestStatus(payload.status)
        updated = await tenant_service.resolve_seat_request(
            db,
            entry,
            status=target_status,
            actor_id=ctx.sub,
            resolution_notes=payload.resolution_notes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return platform_schemas.TenantSeatRequestOut.model_validate(updated)


@router.patch(
    "/{tenant_id}/license",
    response_model=platform_schemas.PlatformTenantOut,
    dependencies=[Depends(require_superadmin())],
)
async def update_license(
    tenant_id: UUID,
    payload: platform_schemas.TenantLicensePatch,
    ctx: UserCtx = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> platform_schemas.PlatformTenantOut:
    tenant_data = await tenant_service.get_tenant_with_details(db, str(tenant_id))
    if tenant_data is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    tenant, _, usage = tenant_data
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        license_entry = await tenant_service.get_tenant_license(db, str(tenant_id))
    else:
        license_entry = await tenant_service.upsert_license(
            db,
            tenant_id=str(tenant_id),
            payload=changes,
            actor_id=ctx.sub,
        )
    return _serialize_tenant(tenant, license_entry, usage)


@router.post(
    "/{tenant_id}/suspend",
    response_model=platform_schemas.PlatformTenantOut,
    dependencies=[Depends(require_superadmin())],
)
async def change_status(
    tenant_id: UUID,
    payload: platform_schemas.TenantStatusChange,
    ctx: UserCtx = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> platform_schemas.PlatformTenantOut:
    tenant_data = await tenant_service.get_tenant_with_details(db, str(tenant_id))
    if tenant_data is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    tenant, license_entry, _ = tenant_data
    status_value = payload.status or TenantStatus.suspended
    tenant = await tenant_service.set_tenant_status(
        db,
        tenant,
        status=status_value,
        actor_id=ctx.sub,
        client_portal_enabled=payload.client_portal_enabled,
        reason=payload.reason,
    )
    usage = await tenant_service.get_usage_snapshot(db, str(tenant_id))
    return _serialize_tenant(tenant, license_entry, usage)


@router.post(
    "/{tenant_id}/impersonate",
    response_model=platform_schemas.TenantImpersonationOut,
    dependencies=[Depends(require_superadmin())],
)
async def impersonate_tenant(
    tenant_id: UUID,
    ctx: UserCtx = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> platform_schemas.TenantImpersonationOut:
    tenant = await tenant_service.get_tenant(db, str(tenant_id))
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=30)
    token_payload = {
        "sub": ctx.sub,
        "email": ctx.email,
        "role": Role.administrator.value,
        "tenant_id": str(tenant_id),
        "type": "impersonation",
        "impersonated_by": ctx.tenant_id,
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
    }
    token = encode_jwt(token_payload)
    return platform_schemas.TenantImpersonationOut(token=token, expires_at=expires_at)
