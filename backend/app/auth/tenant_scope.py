"""Validate that the current user may act in the tenant from X-Tenant-Id / DB scope."""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.deps import Role, UserCtx
from backend.app.models.tenant import user_memberships as _user_memberships


async def ensure_user_can_access_tenant(db: AsyncSession, ctx: UserCtx, header_tenant_id: str) -> None:
    """
    Allow access when:
    - superadmin; or
    - JWT ``tenant_id`` matches the header tenant (normal single-tenant session); or
    - the user has a row in ``user_memberships`` for the header tenant (agency ↔ client switches).
    """
    tid = (header_tenant_id or "").strip()
    if not tid:
        raise HTTPException(status_code=400, detail="Missing tenant context")

    role = (ctx.role or "").strip().lower()
    if role == Role.superadmin.value:
        return

    token_tid = (ctx.tenant_id or "").strip()
    if token_tid and token_tid == tid:
        return

    uid = (ctx.sub or "").strip()
    if not uid:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")

    row = await db.execute(
        select(_user_memberships.c.user_id).where(
            _user_memberships.c.user_id == uid,
            _user_memberships.c.tenant_id == tid,
        ).limit(1)
    )
    if row.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden for tenant")
