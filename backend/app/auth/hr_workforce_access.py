"""Gate /api/v1/workforce/* when tenant HR module is disabled."""

from __future__ import annotations

from typing import Tuple
from uuid import UUID

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.deps import Role, UserCtx, get_current_user
from backend.app.db.deps import get_db_with_tenant
from backend.app.module_registry.resolver import is_module_installed


async def require_hr_workforce_module_access(
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> UserCtx:
    """Allow workforce API only when the HR module is enabled.

    Per-route ``require_roles`` still applies. Platform superadmin bypasses this check.
    """
    r = (ctx.role or "").strip().lower()
    if r == Role.superadmin.value:
        return ctx

    db, tenant_uuid = db_tenant
    if not await is_module_installed(db, str(tenant_uuid), "hr"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="HR module is disabled for this workspace",
        )
    return ctx
