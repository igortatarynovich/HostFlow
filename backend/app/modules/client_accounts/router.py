from __future__ import annotations

from typing import Optional, Tuple
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.deps import Role, UserCtx, get_current_user, require_roles
from backend.app.db.deps import get_db_with_tenant
from backend.app.modules.client_accounts import crud
from backend.app.modules.client_accounts.schemas import (
    ClientAccountCreate,
    ClientAccountListResponse,
    ClientAccountOut,
    ClientAccountUpdate,
)
from backend.app.modules.client_accounts.service import (
    create_client_account_service,
    get_client_account_or_404,
    to_client_account_out,
    update_client_account_service,
)
from backend.app.modules.companies import schemas as company_schemas

router = APIRouter(prefix="/client-accounts", tags=["client-accounts"], redirect_slashes=False)


@router.get("", response_model=ClientAccountListResponse)
@router.get("/", response_model=ClientAccountListResponse, include_in_schema=False)
async def list_client_accounts_endpoint(
    status_filter: Optional[str] = Query(None, alias="status"),
    limit: int = Query(200, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    _role: str = Depends(require_roles(Role.admin, Role.manager, Role.supervisor, Role.recruiter, Role.viewer)),
) -> ClientAccountListResponse:
    db, tenant_id = db_tenant
    items, total = await crud.list_client_accounts(
        db,
        tenant_id=str(tenant_id),
        status=status_filter,
        limit=limit,
        offset=offset,
    )
    return ClientAccountListResponse(
        items=[to_client_account_out(row) for row in items],
        total=total,
    )


@router.post("", response_model=ClientAccountOut, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=ClientAccountOut, status_code=status.HTTP_201_CREATED, include_in_schema=False)
async def create_client_account_endpoint(
    payload: ClientAccountCreate,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    _role: str = Depends(require_roles(Role.admin, Role.manager, Role.supervisor)),
) -> ClientAccountOut:
    db, tenant_id = db_tenant
    account = await create_client_account_service(db, tenant_id=str(tenant_id), data=payload)
    await db.commit()
    await db.refresh(account)
    return to_client_account_out(account)


@router.get("/{account_id}", response_model=ClientAccountOut)
async def get_client_account_endpoint(
    account_id: str,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    _role: str = Depends(require_roles(Role.admin, Role.manager, Role.supervisor, Role.recruiter, Role.viewer)),
) -> ClientAccountOut:
    db, tenant_id = db_tenant
    account = await get_client_account_or_404(db, tenant_id=str(tenant_id), account_id=account_id)
    return to_client_account_out(account)


@router.patch("/{account_id}", response_model=ClientAccountOut)
async def update_client_account_endpoint(
    account_id: str,
    payload: ClientAccountUpdate,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    _role: str = Depends(require_roles(Role.admin, Role.manager, Role.supervisor)),
) -> ClientAccountOut:
    db, tenant_id = db_tenant
    account = await update_client_account_service(
        db,
        tenant_id=str(tenant_id),
        account_id=account_id,
        data=payload,
    )
    await db.commit()
    await db.refresh(account)
    return to_client_account_out(account)


@router.get("/{account_id}/primary-company", response_model=company_schemas.CompanyOut)
async def get_client_account_primary_company_endpoint(
    account_id: str,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    _role: str = Depends(require_roles(Role.admin, Role.manager, Role.supervisor, Role.recruiter, Role.viewer)),
) -> company_schemas.CompanyOut:
    db, tenant_id = db_tenant
    account = await get_client_account_or_404(db, tenant_id=str(tenant_id), account_id=account_id)
    company = await crud.get_primary_company_for_account(db, tenant_id=str(tenant_id), account=account)
    if company is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Primary company not set")
    return company_schemas.CompanyOut.model_validate(company, from_attributes=True)
