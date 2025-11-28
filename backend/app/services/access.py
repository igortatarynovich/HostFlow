from __future__ import annotations

from typing import List

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.access import UserCompanyAccess
from backend.app.models.user import User


async def list_company_access(
    db: AsyncSession,
    *,
    tenant_id: str,
    company_id: str,
) -> List[UserCompanyAccess]:
    rows = await db.execute(
        sa.select(UserCompanyAccess)
        .where(UserCompanyAccess.tenant_id == tenant_id)
        .where(UserCompanyAccess.company_id == company_id)
    )
    return list(rows.scalars())


async def list_company_access_with_users(
    db: AsyncSession,
    *,
    tenant_id: str,
    company_id: str,
):
    stmt = (
        sa.select(UserCompanyAccess, User)
        .join(User, User.id == UserCompanyAccess.user_id)
        .where(UserCompanyAccess.tenant_id == tenant_id)
        .where(UserCompanyAccess.company_id == company_id)
    )
    rows = await db.execute(stmt)
    return rows.all()


async def list_user_access(
    db: AsyncSession,
    *,
    tenant_id: str,
    user_id: str,
) -> List[UserCompanyAccess]:
    rows = await db.execute(
        sa.select(UserCompanyAccess)
        .where(UserCompanyAccess.tenant_id == tenant_id)
        .where(UserCompanyAccess.user_id == user_id)
    )
    return list(rows.scalars())


async def grant_company_access(
    db: AsyncSession,
    *,
    tenant_id: str,
    company_id: str,
    user_id: str,
    can_edit: bool,
) -> UserCompanyAccess:
    existing = await db.execute(
        sa.select(UserCompanyAccess)
        .where(UserCompanyAccess.tenant_id == tenant_id)
        .where(UserCompanyAccess.company_id == company_id)
        .where(UserCompanyAccess.user_id == user_id)
    )
    access = existing.scalar_one_or_none()
    if access:
        access.can_edit = can_edit
        await db.flush()
        return access

    access = UserCompanyAccess(
        tenant_id=tenant_id,
        company_id=company_id,
        user_id=user_id,
        can_edit=can_edit,
    )
    db.add(access)
    await db.flush()
    return access


async def revoke_company_access(
    db: AsyncSession,
    *,
    tenant_id: str,
    company_id: str,
    user_id: str,
) -> int:
    result = await db.execute(
        sa.delete(UserCompanyAccess)
        .where(UserCompanyAccess.tenant_id == tenant_id)
        .where(UserCompanyAccess.company_id == company_id)
        .where(UserCompanyAccess.user_id == user_id)
    )
    await db.flush()
    return int(result.rowcount or 0)
