from __future__ import annotations

from typing import List, Tuple
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.v1.settings.hiring_pipeline_gates_impl import (
    HIRING_GATES_READ_ROLES,
    HiringPipelineGatesPatch,
    HiringPipelineGatesPublicOut,
    get_hiring_pipeline_gates_core,
    patch_hiring_pipeline_gates_core,
)
from backend.app.auth.deps import Role, UserCtx, get_current_user, require_roles
from backend.app.db.deps import get_db_with_tenant, get_db
from backend.app.api.v1.tenants import schemas
from backend.app.api.v1.tenants import service
from backend.app.services.portal_link_limits import ensure_portal_token_issue_allowed
from backend.app.services.tenant_links import list_links_for_agency
from backend.app.models.tenant import TenantLink, Tenant, TenantType
from backend.app.models.company import Company


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


@router.get(
    "/me/hiring-pipeline-gates",
    response_model=HiringPipelineGatesPublicOut,
    dependencies=[Depends(require_roles(*HIRING_GATES_READ_ROLES))],
)
async def get_hiring_pipeline_gates_me(
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> HiringPipelineGatesPublicOut:
    """Alias of `GET /api/v1/settings/team/hiring-pipeline-gates` (same auth & payload)."""
    return await get_hiring_pipeline_gates_core(ctx, db_tenant)


@router.patch(
    "/me/hiring-pipeline-gates",
    response_model=HiringPipelineGatesPublicOut,
    dependencies=[Depends(require_roles(Role.administrator))],
)
async def patch_hiring_pipeline_gates_me(
    payload: HiringPipelineGatesPatch,
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> HiringPipelineGatesPublicOut:
    """Alias of `PATCH /api/v1/settings/team/hiring-pipeline-gates`."""
    return await patch_hiring_pipeline_gates_core(payload, ctx, db_tenant)


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


# --- Tenant Links (handoff infrastructure) ---


@router.get(
    "/{tenant_id}/links/search-companies",
    response_model=List[schemas.CompanySearchOut],
    dependencies=[Depends(require_roles(Role.admin, Role.owner))],
)
async def search_companies_for_link(
    tenant_id: UUID,
    q: str = Query(..., min_length=1),
    db_tenant=Depends(get_db_with_tenant),
):
    """Search companies in other tenants (Tenant.type=company) by name or domain for linking as client."""
    db, current_tenant = db_tenant
    if str(current_tenant) != str(tenant_id):
        raise HTTPException(status_code=403, detail="Cannot access another tenant")
    search = f"%{q.strip()}%"
    stmt = (
        select(Company.id, Company.name, Company.tenant_id, Company.website)
        .join(Tenant, Tenant.id == Company.tenant_id)
        .where(Tenant.type == TenantType.company)
        .where(Company.tenant_id != str(tenant_id))
        .where(or_(Company.name.ilike(search), (Company.website or "").ilike(search)))
        .limit(20)
    )
    result = await db.execute(stmt)
    rows = result.all()
    return [
        schemas.CompanySearchOut(id=r.id, name=r.name, tenant_id=str(r.tenant_id), website=r.website)
        for r in rows
    ]


@router.post(
    "/{tenant_id}/links",
    response_model=schemas.TenantLinkWithCompanyOut,
    status_code=201,
    dependencies=[Depends(require_roles(Role.admin, Role.owner))],
)
async def create_tenant_link(
    tenant_id: UUID,
    payload: schemas.TenantLinkCreate,
    db_tenant=Depends(get_db_with_tenant),
):
    """Create tenant link (agency -> company or agency -> client tenant). Optionally create client by display_name."""
    db, current_tenant = db_tenant
    if str(current_tenant) != str(tenant_id):
        raise HTTPException(status_code=403, detail="Cannot modify links of another tenant")

    cid = str(payload.client_company_id) if payload.client_company_id else None
    tid = str(payload.client_tenant_id) if payload.client_tenant_id else None
    handoff_company = str(payload.handoff_include_company_id) if payload.handoff_include_company_id else None
    display_name = (payload.display_name or "").strip()

    if cid and tid:
        raise HTTPException(
            status_code=400,
            detail="Provide either client_company_id (portal-only) or client_tenant_id with handoff_include_company_id (tenant-backed), not both",
        )
    if tid and not handoff_company:
        raise HTTPException(
            status_code=400,
            detail="Tenant-backed link requires handoff_include_company_id",
        )

    features = {
        "handoff_enabled": payload.handoff_enabled,
        "see_vacancies": payload.see_vacancies,
        "see_reduced_profiles": payload.see_reduced_profiles,
    }
    if display_name:
        features["client_display_name"] = display_name

    if tid and handoff_company:
        # Link to existing employer tenant + company
        company = await db.get(Company, handoff_company)
        if not company or str(company.tenant_id) != tid:
            raise HTTPException(status_code=400, detail="Company must belong to the selected tenant")
        tenant = await db.get(Tenant, tid)
        if not tenant or tenant.type != TenantType.company:
            raise HTTPException(status_code=400, detail="Selected tenant must be an employer (type=company)")
        link = TenantLink(
            agency_tenant_id=str(tenant_id),
            client_company_id=None,
            client_tenant_id=tid,
            handoff_include_company_id=handoff_company,
            status="active",
            features_json=features,
        )
        db.add(link)
        await db.commit()
        await db.refresh(link)
        company_name = company.name
    elif cid:
        # Link to existing company (e.g. agency's own company for unnamed client)
        link = TenantLink(
            agency_tenant_id=str(tenant_id),
            client_company_id=cid,
            client_tenant_id=None,
            handoff_include_company_id=None,
            status="active",
            features_json=features,
        )
        db.add(link)
        await db.commit()
        await db.refresh(link)
        company = await db.get(Company, cid)
        company_name = company.name if company else None
    elif display_name:
        # Create new company in agency tenant and link
        new_company = Company(
            id=str(uuid4()),
            tenant_id=str(tenant_id),
            name=display_name,
        )
        db.add(new_company)
        await db.flush()
        link = TenantLink(
            agency_tenant_id=str(tenant_id),
            client_company_id=str(new_company.id),
            client_tenant_id=None,
            handoff_include_company_id=None,
            status="active",
            features_json=features,
        )
        db.add(link)
        await db.commit()
        await db.refresh(link)
        company_name = new_company.name
    else:
        raise HTTPException(
            status_code=400,
            detail="Provide display_name, or client_company_id, or (client_tenant_id and handoff_include_company_id)",
        )

    return schemas.TenantLinkWithCompanyOut(
        id=link.id,
        agency_tenant_id=link.agency_tenant_id,
        client_company_id=link.client_company_id,
        client_tenant_id=link.client_tenant_id,
        handoff_include_company_id=link.handoff_include_company_id,
        status=link.status,
        features_json=link.features_json,
        company_name=company_name,
        portal_token=link.portal_token,
        portal_expires_at=link.portal_expires_at,
    )


@router.get(
    "/{tenant_id}/links",
    response_model=List[schemas.TenantLinkWithCompanyOut],
    dependencies=[Depends(require_roles(Role.admin, Role.owner))],
)
async def list_tenant_links(
    tenant_id: UUID,
    db_tenant=Depends(get_db_with_tenant),
):
    """List tenant links for the agency (handoff feature config)."""
    from backend.app.models.company import Company
    from backend.app.models.tenant import Tenant

    db, current_tenant = db_tenant
    if str(current_tenant) != str(tenant_id):
        raise HTTPException(status_code=403, detail="Cannot access links of another tenant")
    links = await list_links_for_agency(db, str(tenant_id))
    result = []
    for link in links:
        company_name = None
        if link.client_company_id:
            company = await db.get(Company, link.client_company_id)
            company_name = company.name if company else None
        elif link.client_tenant_id:
            tenant = await db.get(Tenant, link.client_tenant_id)
            company_name = tenant.name if tenant else None
        result.append(schemas.TenantLinkWithCompanyOut(
            id=link.id,
            agency_tenant_id=link.agency_tenant_id,
            client_company_id=link.client_company_id,
            client_tenant_id=link.client_tenant_id,
            handoff_include_company_id=link.handoff_include_company_id,
            status=link.status,
            features_json=link.features_json,
            company_name=company_name,
            portal_token=link.portal_token,
            portal_expires_at=link.portal_expires_at,
        ))
    return result


@router.patch(
    "/{tenant_id}/links/{link_id}",
    response_model=schemas.TenantLinkWithCompanyOut,
    dependencies=[Depends(require_roles(Role.admin, Role.owner))],
)
async def update_tenant_link(
    tenant_id: UUID,
    link_id: UUID,
    payload: schemas.TenantLinkUpdate,
    db_tenant=Depends(get_db_with_tenant),
):
    """Update tenant link features (handoff_enabled, contact_policy)."""
    from sqlalchemy import select
    from backend.app.models.company import Company

    db, current_tenant = db_tenant
    if str(current_tenant) != str(tenant_id):
        raise HTTPException(status_code=403, detail="Cannot modify links of another tenant")
    result = await db.execute(
        select(TenantLink).where(
            TenantLink.id == str(link_id),
            TenantLink.agency_tenant_id == str(tenant_id),
        )
    )
    link = result.scalar_one_or_none()
    if not link:
        raise HTTPException(status_code=404, detail="Tenant link not found")
    updates = payload.model_dump(exclude_unset=True)
    if updates:
        features = dict(link.features_json or {})
        if "handoff_enabled" in updates:
            features["handoff_enabled"] = updates["handoff_enabled"]
        if "contact_policy" in updates and updates["contact_policy"] is not None:
            features["contact_policy"] = updates["contact_policy"]
        if "see_vacancies" in updates:
            features["see_vacancies"] = updates["see_vacancies"]
        if "see_reduced_profiles" in updates:
            features["see_reduced_profiles"] = updates["see_reduced_profiles"]
        link.features_json = features
        await db.commit()
        await db.refresh(link)
    company_name = None
    if link.client_company_id:
        company = await db.get(Company, link.client_company_id)
        company_name = company.name if company else None
    elif link.client_tenant_id:
        tenant = await db.get(Tenant, link.client_tenant_id)
        company_name = tenant.name if tenant else None
    return schemas.TenantLinkWithCompanyOut(
        id=link.id,
        agency_tenant_id=link.agency_tenant_id,
        client_company_id=link.client_company_id,
        client_tenant_id=link.client_tenant_id,
        handoff_include_company_id=link.handoff_include_company_id,
        status=link.status,
        features_json=link.features_json,
        company_name=company_name,
        portal_token=link.portal_token,
        portal_expires_at=link.portal_expires_at,
    )


@router.delete(
    "/{tenant_id}/links/{link_id}/portal-link",
    status_code=204,
    dependencies=[Depends(require_roles(Role.admin, Role.owner))],
)
async def revoke_portal_link(
    tenant_id: UUID,
    link_id: UUID,
    db_tenant=Depends(get_db_with_tenant),
):
    """Revoke portal access by clearing the token."""
    db, current_tenant = db_tenant
    if str(current_tenant) != str(tenant_id):
        raise HTTPException(status_code=403, detail="Cannot modify links of another tenant")
    result = await db.execute(
        select(TenantLink).where(
            TenantLink.id == str(link_id),
            TenantLink.agency_tenant_id == str(tenant_id),
        )
    )
    link = result.scalar_one_or_none()
    if not link:
        raise HTTPException(status_code=404, detail="Tenant link not found")
    link.portal_token = None
    link.portal_expires_at = None
    await db.commit()


@router.post(
    "/{tenant_id}/links/{link_id}/portal-link",
    response_model=schemas.PortalLinkOut,
    dependencies=[Depends(require_roles(Role.admin, Role.owner))],
)
async def create_or_update_portal_link(
    tenant_id: UUID,
    link_id: UUID,
    db_tenant=Depends(get_db_with_tenant),
):
    """Generate or refresh portal token for this client link. Returns URL and optional expires_at."""
    from secrets import token_urlsafe

    db, current_tenant = db_tenant
    if str(current_tenant) != str(tenant_id):
        raise HTTPException(status_code=403, detail="Cannot modify links of another tenant")
    result = await db.execute(
        select(TenantLink).where(
            TenantLink.id == str(link_id),
            TenantLink.agency_tenant_id == str(tenant_id),
        )
    )
    link = result.scalar_one_or_none()
    if not link:
        raise HTTPException(status_code=404, detail="Tenant link not found")
    await ensure_portal_token_issue_allowed(
        db,
        agency_tenant_id=str(tenant_id),
        link=link,
    )
    token = token_urlsafe(32)
    link.portal_token = token
    link.portal_expires_at = None  # optional: set if you add expiry param
    await db.commit()
    await db.refresh(link)
    path = f"/client-portal?token={token}"
    return schemas.PortalLinkOut(
        url=path,
        token=token,
        expires_at=link.portal_expires_at,
    )
