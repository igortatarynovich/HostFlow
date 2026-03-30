"""Shared recruiter UUID validation for tenant-scoped lead/candidate flows."""

from __future__ import annotations

from typing import Optional

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models import User


async def validate_tenant_recruiter_id(
    db: AsyncSession,
    tenant_id: str,
    recruiter_id: Optional[str],
) -> Optional[str]:
    if not recruiter_id:
        return None
    stmt = select(User.id).where(
        User.id == recruiter_id,
        User.is_active.is_(True),
        or_(User.tenant_id == tenant_id, User.tenant_id.is_(None)),
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()
