from __future__ import annotations

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.deps import Role, UserCtx, get_current_user, require_roles
from backend.app.db.deps import get_db_with_tenant, get_db
from backend.app.api.v1.tenants import schemas
from backend.app.api.v1.tenants import service


router = APIRouter(prefix="/tenants", tags=["tenants"], redirect_slashes=False)


@router.get("/me", response_model=schemas.TenantMeOut)
async def get_me(
    ctx: UserCtx = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = ctx.tenant_id
    if not tenant_id:
        raise HTTPException(status_code=400, detail="Token missing tenant_id")
    tenant = await service.get_tenant(db, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return {"tenant": schemas.TenantOut.model_validate(tenant)}


@router.post(
    "/",
    response_model=schemas.TenantOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(Role.admin, Role.owner))],
)
async def create_tenant(
    payload: schemas.TenantCreate,
    db: AsyncSession = Depends(get_db),
):
    slug = service.normalize_slug(payload.slug)
    if not service.is_valid_slug(slug):
        raise HTTPException(status_code=422, detail="Slug may contain lowercase letters, digits or '-'")

    try:
        await service.ensure_slug_unique(db, slug)
    except ValueError:
        raise HTTPException(status_code=409, detail="Slug already in use") from None

    data = payload.model_dump()
    data["slug"] = slug
    tenant = await service.create_tenant(db, data)
    return schemas.TenantOut.model_validate(tenant)


@router.patch(
    "/{tenant_id}",
    response_model=schemas.TenantOut,
    dependencies=[Depends(require_roles(Role.admin, Role.owner))],
)
async def update_tenant(
    tenant_id: UUID,
    payload: schemas.TenantUpdate,
    db_tenant = Depends(get_db_with_tenant),
):
    db, current_tenant = db_tenant
    if str(current_tenant) != str(tenant_id):
        raise HTTPException(status_code=403, detail="Cannot modify another tenant")
    tenant = await service.get_tenant(db, str(tenant_id))
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    updates = payload.model_dump(exclude_unset=True)
    if "name" in updates and updates["name"]:
        updates["name"] = updates["name"].strip()
    if "settings" in updates and updates["settings"] is None:
        updates["settings"] = {}
    if "slug" in updates:
        raise HTTPException(status_code=422, detail="Slug cannot be changed")

    tenant = await service.update_tenant(db, tenant, updates)
    return schemas.TenantOut.model_validate(tenant)


@router.get(
    "/{tenant_id}/users",
    response_model=List[schemas.TenantUsersOut],
    dependencies=[Depends(require_roles(Role.admin, Role.owner, Role.manager))],
)
async def list_users(
    tenant_id: UUID,
    db_tenant = Depends(get_db_with_tenant),
):
    db, current_tenant = db_tenant
    if str(current_tenant) != str(tenant_id):
        raise HTTPException(status_code=403, detail="Cannot access users of another tenant")
    rows = await service.list_tenant_users(db, str(tenant_id))
    result = []
    for user, role, joined_at in rows:
        result.append(
            schemas.TenantUsersOut(
                id=user.id,
                email=user.email,
                role=role,
                joined_at=joined_at,
            )
        )
    return result


@router.post(
    "/{tenant_id}/apikey/reset",
    response_model=schemas.ApiKeyResetOut,
    dependencies=[Depends(require_roles(Role.admin, Role.owner))],
)
async def reset_api_key(
    tenant_id: UUID,
    db_tenant = Depends(get_db_with_tenant),
):
    db, current_tenant = db_tenant
    if str(current_tenant) != str(tenant_id):
        raise HTTPException(status_code=403, detail="Cannot rotate API key for another tenant")
    tenant = await service.get_tenant(db, str(tenant_id))
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    tenant = await service.rotate_api_key(db, tenant)
    return schemas.ApiKeyResetOut(
        api_key=tenant.api_key,
        tenant_id=tenant_id,
        rotated_at=tenant.updated_at,
    )
