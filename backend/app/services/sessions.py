from __future__ import annotations

from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.session import AuthRefreshToken


async def revoke_user_sessions(
    db: AsyncSession,
    *,
    user_id: str,
    tenant_id: str,
    actor_id: Optional[str] = None,
) -> int:
    stmt = (
        update(AuthRefreshToken)
        .where(AuthRefreshToken.user_id == user_id)
        .where(AuthRefreshToken.tenant_id == tenant_id)
        .where(AuthRefreshToken.revoked_at.is_(None))
        .values(revoked_by=actor_id)
    )
    result = await db.execute(stmt)
    await db.flush()
    return int(result.rowcount or 0)


async def list_active_sessions(
    db: AsyncSession,
    *,
    user_id: str,
    tenant_id: str,
):
    rows = await db.execute(
        select(AuthRefreshToken).where(AuthRefreshToken.user_id == user_id).where(
            AuthRefreshToken.tenant_id == tenant_id
        )
    )
    return list(rows.scalars())
