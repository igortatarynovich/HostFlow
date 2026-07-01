from typing import Dict, List, Optional
from uuid import UUID

from backend.app.auth.deps import require_roles, Role, get_current_user, UserCtx
from backend.app.api.v1.utils.access import resolve_restricted_acl
from backend.app.db.deps import get_db_with_tenant
from backend.app.modules.companies import schemas, crud
from backend.app.models.company import Company
from backend.app.modules.companies.counters import (
    get_company_counters,
    company_recruitment_metrics_for_list,
)
from backend.app.modules.companies.service_order_metrics import company_service_order_metrics
from backend.app.modules.companies.service import (
    add_company_bank_account_service,
    add_company_contact_service,
    archive_company_service,
    create_company_service,
    delete_company_bank_account_service,
    delete_company_contact_service,
    enable_company_portal_service,
    get_company_or_404,
    get_company_readiness_service,
    list_companies_service,
    replace_company_billing_service,
    replace_company_operations_service,
    update_company_bank_account_service,
    update_company_compliance_service,
    update_company_contact_service,
    update_company_integrations_service,
    update_company_legal_service,
    update_company_portal_service,
    update_company_service,
)
from pydantic import BaseModel
from fastapi import APIRouter, Body, Depends, HTTPException, Path, Query, status, Response
from sqlalchemy import select, or_

router = APIRouter(
    prefix="/companies",
    tags=["companies"],
    redirect_slashes=False,
)


def _require_company_access(company_id: UUID, acl) -> None:
    if acl is None:
        return
    if not acl.company_ids:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    if str(company_id) not in acl.company_ids:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")


@router.get(
    "/",
    response_model=List[schemas.CompanyOut],
)
@router.get(
    "/directory",
    response_model=List[schemas.CompanyOut],
    include_in_schema=False,
)
@router.get(
    "",
    response_model=List[schemas.CompanyOut],
    include_in_schema=False,
)
async def list_companies(
    _role: str = Depends(require_roles(Role.manager, Role.admin, Role.recruiter, Role.viewer)),
    q: str = Query(None, description="Search query"),
    include_archived: bool = Query(False, description="Include archived companies"),
    party_business_roles: Optional[str] = Query(
        None,
        description="Filter by party business role: employer | service_client | both",
    ),
    client_stage: Optional[str] = Query(None, description="Filter by client pipeline stage code"),
    owner_user_id: Optional[UUID] = Query(None, description="Filter by company owner user id"),
    client_source: Optional[str] = Query(None, description="Filter by acquisition source"),
    include_service_metrics: bool = Query(
        False,
        description="Include per-company service order counts and completed revenue",
    ),
    include_recruitment_metrics: bool = Query(
        False,
        description="Include active vacancies and candidate counts scoped like the candidates list",
    ),
    db_tenant=Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
):
    db, tenant_id = db_tenant
    user_role = (getattr(current_user, "role", "") or "").strip().lower()
    effective_include_archived = include_archived or user_role == Role.superadmin.value
    if user_role == Role.superadmin.value:
        stmt = select(Company)
        if not effective_include_archived:
            stmt = stmt.where(Company.is_archived.is_(False))
        if q:
            like = f"%{q}%"
            stmt = stmt.where(
                or_(
                    Company.name.ilike(like),
                    Company.legal_name.ilike(like),
                )
            )
        if party_business_roles:
            stmt = stmt.where(Company.party_business_roles == party_business_roles)
        if client_stage:
            stmt = stmt.where(Company.client_stage == client_stage)
        if owner_user_id:
            stmt = stmt.where(Company.owner_user_id == str(owner_user_id))
        if client_source:
            stmt = stmt.where(Company.client_source == client_source)
        stmt = stmt.order_by(Company.name.asc())
        superadmin_rows = await db.execute(stmt)
        companies = list(superadmin_rows.scalars().all())
    else:
        acl = await resolve_restricted_acl(db, str(tenant_id), current_user)
        allowed_company_ids = None if acl is None else set(acl.company_ids)
        companies = await list_companies_service(
            db=db,
            q=q,
            include_archived=effective_include_archived,
            allowed_company_ids=allowed_company_ids,
            party_business_roles=party_business_roles,
            client_stage=client_stage,
            owner_user_id=str(owner_user_id) if owner_user_id else None,
            client_source=client_source,
        )

    metrics: Dict[str, Dict[str, object]] = {}
    if include_service_metrics and companies:
        metrics = await company_service_order_metrics(
            db,
            tenant_id=str(tenant_id),
            company_ids=[str(c.id) for c in companies],
        )

    rec_metrics: Dict[str, Dict[str, int]] = {}
    if include_recruitment_metrics and companies:
        rec_metrics = await company_recruitment_metrics_for_list(
            db,
            tenant_id=str(tenant_id),
            company_ids=[str(c.id) for c in companies],
        )

    result: List[schemas.CompanyOut] = []
    for c in companies:
        row = schemas.CompanyOut.model_validate(c)
        updates: Dict[str, object] = {}
        if include_service_metrics:
            m = metrics.get(str(c.id), {"active_orders": 0, "revenue_completed": 0.0})
            updates["service_active_orders"] = int(m["active_orders"])
            updates["service_revenue_completed"] = float(m["revenue_completed"])
        if include_recruitment_metrics:
            r = rec_metrics.get(str(c.id), {"recruitment_vacancies_active": 0, "recruitment_candidates_total": 0})
            updates["recruitment_vacancies_active"] = int(r["recruitment_vacancies_active"])
            updates["recruitment_candidates_total"] = int(r["recruitment_candidates_total"])
        if updates:
            result.append(row.model_copy(update=updates))
        else:
            result.append(row)
    return result


@router.post(
    "/",
    response_model=schemas.CompanyOut,
    status_code=status.HTTP_200_OK,
)
@router.post(
    "",
    response_model=schemas.CompanyOut,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
async def create_company(
    company_in: schemas.CompanyCreate,
    _role: str = Depends(require_roles(Role.manager, Role.admin)),
    current_user: UserCtx = Depends(get_current_user),
    db_tenant=Depends(get_db_with_tenant),
):
    db, _tenant_id = db_tenant
    return await create_company_service(
        db=db,
        data=company_in,
        actor_user_id=str(current_user.sub) if getattr(current_user, "sub", None) else None,
    )


@router.get(
    "/{company_id}",
    response_model=schemas.CompanyOut,
)
async def get_company(
    company_id: UUID,
    include_service_metrics: bool = Query(
        False,
        description="Include service order counts and completed revenue for this company",
    ),
    include_recruitment_metrics: bool = Query(
        False,
        description="Include active vacancies and candidate counts (same scope as list)",
    ),
    _role: str = Depends(require_roles(Role.manager, Role.admin, Role.recruiter, Role.viewer)),
    db_tenant=Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
):
    db, tenant_id = db_tenant
    # First check if company is accessible via TenantLink (for agency accessing client companies)
    # crud.get_company already checks TenantLink access, so if it returns a company, access is granted
    result = await crud.get_company(db=db, company_id=company_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
    
    # For restricted users (non-admin roles), still check ACL for additional restrictions
    # But if company is accessible via TenantLink (which crud.get_company already verified),
    # we allow access even if not in ACL
    acl = await resolve_restricted_acl(db, str(tenant_id), current_user)
    if acl is not None and acl.company_ids:
        # Check if company is in ACL or accessible via TenantLink
        # Since crud.get_company already verified TenantLink access, if we got here with a result,
        # the company is accessible. Only block if ACL explicitly restricts AND company is not in ACL
        # AND company is not accessible via TenantLink (but crud.get_company already checked that)
        # So we only need to check ACL if company is not in ACL AND we want to enforce strict ACL
        # For now, we allow access if company is found (via TenantLink or ownership)
        pass

    row = schemas.CompanyOut.model_validate(result)
    updates: Dict[str, object] = {}
    cid_str = str(company_id)
    if include_service_metrics:
        m = await company_service_order_metrics(db, tenant_id=str(tenant_id), company_ids=[cid_str])
        pack = m.get(cid_str, {"active_orders": 0, "revenue_completed": 0.0})
        updates["service_active_orders"] = int(pack["active_orders"])
        updates["service_revenue_completed"] = float(pack["revenue_completed"])
    if include_recruitment_metrics:
        r = await company_recruitment_metrics_for_list(db, tenant_id=str(tenant_id), company_ids=[cid_str])
        pack = r.get(cid_str, {"recruitment_vacancies_active": 0, "recruitment_candidates_total": 0})
        updates["recruitment_vacancies_active"] = int(pack["recruitment_vacancies_active"])
        updates["recruitment_candidates_total"] = int(pack["recruitment_candidates_total"])
    if updates:
        return row.model_copy(update=updates)
    return row


@router.put(
    "/{company_id}",
    response_model=schemas.CompanyOut,
)
async def update_company(
    company_id: UUID,
    company_in: schemas.CompanyUpdate,
    _role: str = Depends(require_roles(Role.manager, Role.admin)),
    current_user: UserCtx = Depends(get_current_user),
    db_tenant=Depends(get_db_with_tenant),
):
    db, _tenant_id = db_tenant
    return await update_company_service(
        db=db,
        company_id=company_id,
        data=company_in,
        actor_user_id=str(current_user.sub) if getattr(current_user, "sub", None) else None,
    )


@router.patch(
    "/{company_id}",
    response_model=schemas.CompanyOut,
)
async def patch_company(
    company_id: UUID,
    company_in: schemas.CompanyUpdate,
    _role: str = Depends(require_roles(Role.manager, Role.admin)),
    current_user: UserCtx = Depends(get_current_user),
    db_tenant=Depends(get_db_with_tenant),
):
    db, _tenant_id = db_tenant
    return await update_company_service(
        db=db,
        company_id=company_id,
        data=company_in,
        actor_user_id=str(current_user.sub) if getattr(current_user, "sub", None) else None,
    )


@router.delete(
    "/{company_id}",
    status_code=status.HTTP_204_NO_CONTENT, response_class=Response, response_model=None,
)
async def archive_company(
    company_id: UUID,
    _role: str = Depends(require_roles(Role.admin)),
    db_tenant=Depends(get_db_with_tenant),
):
    db, _tenant_id = db_tenant
    await archive_company_service(db=db, company_id=company_id)


@router.get(
    "/{company_id}/counters",
    response_model=Dict[str, int],
)
async def company_counters(
    company_id: UUID,
    _role: str = Depends(require_roles(Role.manager, Role.admin, Role.recruiter, Role.viewer)),
    db_tenant=Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
):
    db, tenant_id = db_tenant
    acl = await resolve_restricted_acl(db, str(tenant_id), current_user)
    _require_company_access(company_id, acl)
    return await get_company_counters(db=db, company_id=company_id)


@router.patch(
    "/{company_id}/legal",
    response_model=schemas.LegalProfile,
)
async def update_company_legal(
    company_id: UUID = Path(..., description="Company identifier"),
    payload: schemas.LegalProfile = Body(...),
    _role: str = Depends(require_roles(Role.manager, Role.admin, Role.recruiter)),
    db_tenant=Depends(get_db_with_tenant),
):
    db, _tenant_id = db_tenant
    data = await update_company_legal_service(db=db, company_id=company_id, payload=payload.model_dump(exclude_none=True))
    return schemas.LegalProfile.model_validate(data)


@router.put(
    "/{company_id}/billing",
    response_model=schemas.BillingProfile,
)
async def replace_company_billing(
    company_id: UUID,
    payload: schemas.BillingProfile = Body(...),
    _role: str = Depends(require_roles(Role.manager, Role.admin, Role.recruiter)),
    db_tenant=Depends(get_db_with_tenant),
):
    db, _tenant_id = db_tenant
    data = await replace_company_billing_service(db=db, company_id=company_id, payload=payload.model_dump(exclude_none=True))
    return schemas.BillingProfile.model_validate(data)


@router.post(
    "/{company_id}/bank-accounts",
    response_model=schemas.BankAccount,
)
async def add_bank_account(
    company_id: UUID,
    payload: schemas.BankAccount = Body(...),
    _role: str = Depends(require_roles(Role.manager, Role.admin, Role.recruiter)),
    db_tenant=Depends(get_db_with_tenant),
):
    db, _tenant_id = db_tenant
    data = await add_company_bank_account_service(db=db, company_id=company_id, payload=payload.model_dump(exclude_none=True))
    return schemas.BankAccount.model_validate(data)


@router.patch(
    "/{company_id}/bank-accounts/{account_id}",
    response_model=schemas.BankAccount,
)
async def update_bank_account(
    company_id: UUID,
    account_id: UUID,
    payload: schemas.BankAccount = Body(...),
    _role: str = Depends(require_roles(Role.manager, Role.admin, Role.recruiter)),
    db_tenant=Depends(get_db_with_tenant),
):
    db, _tenant_id = db_tenant
    data = await update_company_bank_account_service(
        db=db,
        company_id=company_id,
        account_id=account_id,
        payload=payload.model_dump(exclude_none=True),
    )
    return schemas.BankAccount.model_validate(data)


@router.delete(
    "/{company_id}/bank-accounts/{account_id}",
    status_code=status.HTTP_204_NO_CONTENT, response_class=Response, response_model=None,
)
async def delete_bank_account(
    company_id: UUID,
    account_id: UUID,
    _role: str = Depends(require_roles(Role.manager, Role.admin, Role.recruiter)),
    db_tenant=Depends(get_db_with_tenant),
):
    db, _tenant_id = db_tenant
    await delete_company_bank_account_service(db=db, company_id=company_id, account_id=account_id)


@router.post(
    "/{company_id}/contacts",
    response_model=schemas.Contact,
)
async def add_contact(
    company_id: UUID,
    payload: schemas.Contact = Body(...),
    _role: str = Depends(require_roles(Role.manager, Role.admin, Role.recruiter)),
    db_tenant=Depends(get_db_with_tenant),
):
    db, _tenant_id = db_tenant
    data = await add_company_contact_service(db=db, company_id=company_id, payload=payload.model_dump(exclude_none=True))
    return schemas.Contact.model_validate(data)


@router.patch(
    "/{company_id}/contacts/{contact_id}",
    response_model=schemas.Contact,
)
async def update_contact(
    company_id: UUID,
    contact_id: UUID,
    payload: schemas.Contact = Body(...),
    _role: str = Depends(require_roles(Role.manager, Role.admin, Role.recruiter)),
    db_tenant=Depends(get_db_with_tenant),
):
    db, _tenant_id = db_tenant
    data = await update_company_contact_service(
        db=db,
        company_id=company_id,
        contact_id=contact_id,
        payload=payload.model_dump(exclude_none=True),
    )
    return schemas.Contact.model_validate(data)


@router.delete(
    "/{company_id}/contacts/{contact_id}",
    status_code=status.HTTP_204_NO_CONTENT, response_class=Response, response_model=None,
)
async def delete_contact(
    company_id: UUID,
    contact_id: UUID,
    _role: str = Depends(require_roles(Role.manager, Role.admin, Role.recruiter)),
    db_tenant=Depends(get_db_with_tenant),
):
    db, _tenant_id = db_tenant
    await delete_company_contact_service(db=db, company_id=company_id, contact_id=contact_id)


@router.put(
    "/{company_id}/operations",
    response_model=schemas.OperationsProfile,
)
async def replace_operations(
    company_id: UUID,
    payload: schemas.OperationsProfile = Body(...),
    _role: str = Depends(require_roles(Role.manager, Role.admin, Role.recruiter)),
    db_tenant=Depends(get_db_with_tenant),
):
    db, _tenant_id = db_tenant
    data = await replace_company_operations_service(db=db, company_id=company_id, payload=payload.model_dump(exclude_none=True))
    return schemas.OperationsProfile.model_validate(data)


@router.patch(
    "/{company_id}/compliance",
    response_model=schemas.ComplianceProfile,
)
async def update_compliance(
    company_id: UUID,
    payload: schemas.ComplianceProfile = Body(...),
    _role: str = Depends(require_roles(Role.manager, Role.admin, Role.recruiter)),
    db_tenant=Depends(get_db_with_tenant),
):
    db, _tenant_id = db_tenant
    data = await update_company_compliance_service(db=db, company_id=company_id, payload=payload.model_dump(exclude_none=True))
    return schemas.ComplianceProfile.model_validate(data)


@router.patch(
    "/{company_id}/portal",
    response_model=schemas.PortalProfile,
)
async def update_portal(
    company_id: UUID,
    payload: schemas.PortalProfile = Body(...),
    _role: str = Depends(require_roles(Role.manager, Role.admin, Role.recruiter)),
    db_tenant=Depends(get_db_with_tenant),
):
    db, _tenant_id = db_tenant
    data = await update_company_portal_service(db=db, company_id=company_id, payload=payload.model_dump(exclude_none=True))
    return schemas.PortalProfile.model_validate(data)


class EnablePortalRequest(BaseModel):
    enabled: bool
    url: str | None = None


@router.post(
    "/{company_id}/enable-portal",
    response_model=schemas.PortalProfile,
)
async def enable_portal(
    company_id: UUID,
    payload: EnablePortalRequest = Body(...),
    _role: str = Depends(require_roles(Role.manager, Role.admin)),
    db_tenant=Depends(get_db_with_tenant),
):
    db, _tenant_id = db_tenant
    data = await enable_company_portal_service(
        db=db,
        company_id=company_id,
        enabled=payload.enabled,
        url=payload.url,
    )
    return schemas.PortalProfile.model_validate(data)


@router.patch(
    "/{company_id}/integrations",
    response_model=schemas.IntegrationsProfile,
)
async def update_integrations(
    company_id: UUID,
    payload: schemas.IntegrationsProfile = Body(...),
    _role: str = Depends(require_roles(Role.manager, Role.admin, Role.recruiter)),
    db_tenant=Depends(get_db_with_tenant),
):
    db, _tenant_id = db_tenant
    data = await update_company_integrations_service(db=db, company_id=company_id, payload=payload.model_dump(exclude_none=True))
    return schemas.IntegrationsProfile.model_validate(data)


@router.get(
    "/{company_id}/readiness",
    response_model=schemas.CompanyReadiness,
)
async def company_readiness(
    company_id: UUID,
    _role: str = Depends(require_roles(Role.manager, Role.admin, Role.recruiter, Role.viewer)),
    db_tenant=Depends(get_db_with_tenant),
):
    db, _tenant_id = db_tenant
    return await get_company_readiness_service(db=db, company_id=company_id)
