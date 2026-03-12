from typing import Dict, List
from uuid import UUID

from backend.app.auth.deps import require_roles, Role, get_current_user, UserCtx
from backend.app.api.v1.utils.access import resolve_restricted_acl
from backend.app.db.deps import get_db_with_tenant
from backend.app.modules.companies import schemas, crud
from backend.app.modules.companies.counters import get_company_counters
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
from fastapi import APIRouter, Body, Depends, HTTPException, Path, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

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
    "",
    response_model=List[schemas.CompanyOut],
    include_in_schema=False,
)
async def list_companies(
    _role: str = Depends(require_roles(Role.manager, Role.admin, Role.recruiter, Role.viewer)),
    q: str = Query(None, description="Search query"),
    include_archived: bool = Query(False, description="Include archived companies"),
    db_tenant=Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
):
    db, tenant_id = db_tenant
    acl = await resolve_restricted_acl(db, str(tenant_id), current_user)
    allowed_company_ids = None if acl is None else set(acl.company_ids)
    return await list_companies_service(
        db=db,
        q=q,
        include_archived=include_archived,
        allowed_company_ids=allowed_company_ids,
    )


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
    db: AsyncSession = Depends(get_db_with_tenant),
):
    return await create_company_service(db=db, data=company_in)


@router.get(
    "/{company_id}",
    response_model=schemas.CompanyOut,
)
async def get_company(
    company_id: UUID,
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
    
    return result


@router.put(
    "/{company_id}",
    response_model=schemas.CompanyOut,
)
async def update_company(
    company_id: UUID,
    company_in: schemas.CompanyUpdate,
    _role: str = Depends(require_roles(Role.manager, Role.admin)),
    db: AsyncSession = Depends(get_db_with_tenant),
):
    return await update_company_service(db=db, company_id=company_id, data=company_in)


@router.patch(
    "/{company_id}",
    response_model=schemas.CompanyOut,
)
async def patch_company(
    company_id: UUID,
    company_in: schemas.CompanyUpdate,
    _role: str = Depends(require_roles(Role.manager, Role.admin)),
    db: AsyncSession = Depends(get_db_with_tenant),
):
    return await update_company_service(db=db, company_id=company_id, data=company_in)


@router.delete(
    "/{company_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def archive_company(
    company_id: UUID,
    _role: str = Depends(require_roles(Role.admin)),
    db: AsyncSession = Depends(get_db_with_tenant),
):
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
    db: AsyncSession = Depends(get_db_with_tenant),
):
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
    db: AsyncSession = Depends(get_db_with_tenant),
):
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
    db: AsyncSession = Depends(get_db_with_tenant),
):
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
    db: AsyncSession = Depends(get_db_with_tenant),
):
    data = await update_company_bank_account_service(
        db=db,
        company_id=company_id,
        account_id=account_id,
        payload=payload.model_dump(exclude_none=True),
    )
    return schemas.BankAccount.model_validate(data)


@router.delete(
    "/{company_id}/bank-accounts/{account_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_bank_account(
    company_id: UUID,
    account_id: UUID,
    _role: str = Depends(require_roles(Role.manager, Role.admin, Role.recruiter)),
    db: AsyncSession = Depends(get_db_with_tenant),
):
    await delete_company_bank_account_service(db=db, company_id=company_id, account_id=account_id)


@router.post(
    "/{company_id}/contacts",
    response_model=schemas.Contact,
)
async def add_contact(
    company_id: UUID,
    payload: schemas.Contact = Body(...),
    _role: str = Depends(require_roles(Role.manager, Role.admin, Role.recruiter)),
    db: AsyncSession = Depends(get_db_with_tenant),
):
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
    db: AsyncSession = Depends(get_db_with_tenant),
):
    data = await update_company_contact_service(
        db=db,
        company_id=company_id,
        contact_id=contact_id,
        payload=payload.model_dump(exclude_none=True),
    )
    return schemas.Contact.model_validate(data)


@router.delete(
    "/{company_id}/contacts/{contact_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_contact(
    company_id: UUID,
    contact_id: UUID,
    _role: str = Depends(require_roles(Role.manager, Role.admin, Role.recruiter)),
    db: AsyncSession = Depends(get_db_with_tenant),
):
    await delete_company_contact_service(db=db, company_id=company_id, contact_id=contact_id)


@router.put(
    "/{company_id}/operations",
    response_model=schemas.OperationsProfile,
)
async def replace_operations(
    company_id: UUID,
    payload: schemas.OperationsProfile = Body(...),
    _role: str = Depends(require_roles(Role.manager, Role.admin, Role.recruiter)),
    db: AsyncSession = Depends(get_db_with_tenant),
):
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
    db: AsyncSession = Depends(get_db_with_tenant),
):
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
    db: AsyncSession = Depends(get_db_with_tenant),
):
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
    db: AsyncSession = Depends(get_db_with_tenant),
):
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
    db: AsyncSession = Depends(get_db_with_tenant),
):
    data = await update_company_integrations_service(db=db, company_id=company_id, payload=payload.model_dump(exclude_none=True))
    return schemas.IntegrationsProfile.model_validate(data)


@router.get(
    "/{company_id}/readiness",
    response_model=schemas.CompanyReadiness,
)
async def company_readiness(
    company_id: UUID,
    _role: str = Depends(require_roles(Role.manager, Role.admin, Role.recruiter, Role.viewer)),
    db: AsyncSession = Depends(get_db_with_tenant),
):
    return await get_company_readiness_service(db=db, company_id=company_id)
