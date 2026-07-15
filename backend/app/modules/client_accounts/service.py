from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models import ClientAccount
from backend.app.modules.client_accounts import crud
from backend.app.modules.client_accounts.schemas import (
    ClientAccountCreate,
    ClientAccountOut,
    ClientAccountUpdate,
)


async def create_client_account_service(
    db: AsyncSession,
    *,
    tenant_id: str,
    data: ClientAccountCreate,
) -> ClientAccount:
    account = ClientAccount(
        id=crud.new_client_account_id(),
        tenant_id=tenant_id,
        own_company_id=data.own_company_id,
        display_name=data.display_name.strip(),
        status=data.status,
        owner_user_id=str(data.owner_user_id) if data.owner_user_id else None,
        primary_company_id=data.primary_company_id,
        source_lead_id=data.source_lead_id,
    )
    if data.primary_company_id:
        await _assert_company_tenant(db, tenant_id=tenant_id, company_id=data.primary_company_id)
    if data.source_lead_id:
        await _assert_lead_tenant(db, tenant_id=tenant_id, lead_id=data.source_lead_id)
    db.add(account)
    await db.flush()
    return account


async def update_client_account_service(
    db: AsyncSession,
    *,
    tenant_id: str,
    account_id: str,
    data: ClientAccountUpdate,
) -> ClientAccount:
    account = await get_client_account_or_404(db, tenant_id=tenant_id, account_id=account_id)
    if data.display_name is not None:
        account.display_name = data.display_name.strip()
    if data.status is not None:
        account.status = data.status
    if data.owner_user_id is not None:
        account.owner_user_id = str(data.owner_user_id)
    if data.primary_company_id is not None:
        if data.primary_company_id:
            await _assert_company_tenant(db, tenant_id=tenant_id, company_id=data.primary_company_id)
        account.primary_company_id = data.primary_company_id or None
    await db.flush()
    return account


async def get_client_account_or_404(
    db: AsyncSession,
    *,
    tenant_id: str,
    account_id: str,
) -> ClientAccount:
    account = await crud.get_client_account(db, tenant_id=tenant_id, account_id=account_id)
    if account is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client account not found")
    return account


async def _assert_company_tenant(db: AsyncSession, *, tenant_id: str, company_id: str) -> None:
    from backend.app.models import Company
    from sqlalchemy import select

    row = await db.execute(
        select(Company.id).where(Company.id == company_id, Company.tenant_id == tenant_id)
    )
    if row.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Company not found in tenant")


async def _assert_lead_tenant(db: AsyncSession, *, tenant_id: str, lead_id: str) -> None:
    from backend.app.models import Lead
    from sqlalchemy import select

    row = await db.execute(select(Lead.id).where(Lead.id == lead_id, Lead.tenant_id == tenant_id))
    if row.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Lead not found in tenant")


def to_client_account_out(account: ClientAccount) -> ClientAccountOut:
    return ClientAccountOut.model_validate(account, from_attributes=True)
