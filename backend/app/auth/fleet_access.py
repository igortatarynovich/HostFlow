"""Gate /api/v1/fleet/* to roles that may use the fleet workspace and tenant module flag."""

from __future__ import annotations

from typing import Tuple
from uuid import UUID

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.v1.tenants import service as tenant_service
from backend.app.auth.deps import Role, UserCtx, get_current_user
from backend.app.db.deps import get_db_with_tenant
from backend.app.models.tenant import Tenant

_FLEET_MODULE_ROLES = frozenset(
    {
        Role.superadmin.value,
        Role.administrator.value,
        Role.supervisor.value,
        Role.recruiter.value,
        Role.viewer.value,
        Role.client_manager.value,
        Role.client_processor.value,
        Role.compliance_officer.value,
        Role.fleet_manager.value,
    }
)


async def require_fleet_module_access(
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> UserCtx:
    """Allow fleet API when role is permitted and tenant.settings.modules.fleet is enabled."""
    r = (ctx.role or "").strip().lower()
    if r == Role.superadmin.value:
        return ctx
    if r not in _FLEET_MODULE_ROLES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Fleet module access denied for this role")

    db, tenant_uuid = db_tenant
    tenant = await db.get(Tenant, str(tenant_uuid))
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Tenant not found")
    modules = tenant_service.get_module_settings_snapshot(tenant)
    if not modules.get("fleet", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Fleet module is disabled for this workspace",
        )
    return ctx
