from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models import ClientAccount, Company, Lead


async def get_client_account(
    db: AsyncSession,
    *,
    tenant_id: str,
    account_id: str,
) -> Optional[ClientAccount]:
    result = await db.execute(
        select(ClientAccount).where(
            ClientAccount.id == str(account_id),
            ClientAccount.tenant_id == tenant_id,
        )
    )
    return result.scalar_one_or_none()


async def get_client_account_by_source_lead(
    db: AsyncSession,
    *,
    tenant_id: str,
    source_lead_id: str,
) -> Optional[ClientAccount]:
    result = await db.execute(
        select(ClientAccount).where(
            ClientAccount.tenant_id == tenant_id,
            ClientAccount.source_lead_id == str(source_lead_id),
        )
    )
    return result.scalar_one_or_none()


async def list_client_accounts(
    db: AsyncSession,
    *,
    tenant_id: str,
    status: Optional[str] = None,
    limit: int = 200,
    offset: int = 0,
) -> tuple[list[ClientAccount], int]:
    filters = [ClientAccount.tenant_id == tenant_id]
    if status:
        filters.append(ClientAccount.status == status)
    total_result = await db.execute(select(func.count()).select_from(ClientAccount).where(*filters))
    total = int(total_result.scalar_one() or 0)
    rows = await db.execute(
        select(ClientAccount)
        .where(*filters)
        .order_by(ClientAccount.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(rows.scalars().all()), total


async def get_lead_for_update(
    db: AsyncSession,
    *,
    tenant_id: str,
    lead_id: str,
) -> Optional[Lead]:
    result = await db.execute(
        select(Lead)
        .where(Lead.id == str(lead_id), Lead.tenant_id == tenant_id)
        .with_for_update()
    )
    return result.scalar_one_or_none()


async def get_primary_company_for_account(
    db: AsyncSession,
    *,
    tenant_id: str,
    account: ClientAccount,
) -> Optional[Company]:
    company_id = str(getattr(account, "primary_company_id", "") or "").strip()
    if not company_id:
        return None
    result = await db.execute(
        select(Company).where(Company.id == company_id, Company.tenant_id == tenant_id)
    )
    company = result.scalar_one_or_none()
    if company is None:
        return None
    if str(getattr(company, "client_account_id", "") or "") not in ("", str(account.id)):
        # Stage 1: tolerate missing reverse link if primary pointer matches tenant.
        pass
    return company


def new_client_account_id() -> str:
    return str(uuid.uuid4())
