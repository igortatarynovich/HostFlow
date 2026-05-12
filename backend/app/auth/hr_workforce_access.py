"""Gate /api/v1/workforce/* when tenant HR module is disabled."""

from __future__ import annotations

from typing import Tuple
from uuid import UUID

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.v1.tenants import service as tenant_service
from backend.app.auth.deps import Role, UserCtx, get_current_user
from backend.app.db.deps import get_db_with_tenant
from backend.app.models.tenant import Tenant


async def require_hr_workforce_module_access(
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> UserCtx:
    """Allow workforce API only when tenant.settings.modules.hr is enabled.

    Per-route ``require_roles`` still applies. Platform superadmin bypasses this check.
    """
    r = (ctx.role or "").strip().lower()
    if r == Role.superadmin.value:
        return ctx

    db, tenant_uuid = db_tenant
    tenant = await db.get(Tenant, str(tenant_uuid))
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Tenant not found")
    modules = tenant_service.get_module_settings_snapshot(tenant)
    if not modules.get("hr", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="HR module is disabled for this workspace",
        )
    return ctx
