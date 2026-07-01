"""Gate /api/v1/fleet/* to roles that may use the fleet workspace and tenant module flag."""

from __future__ import annotations

from typing import Tuple
from uuid import UUID

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.deps import Role, UserCtx, get_current_user
from backend.app.db.deps import get_db_with_tenant
from backend.app.module_registry.resolver import is_module_installed

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
        "fleet_manager",
    }
)


async def require_fleet_module_access(
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> UserCtx:
    """Allow fleet API when role is permitted and the fleet module is enabled."""
    r = (ctx.role or "").strip().lower()
    if r == Role.superadmin.value:
        return ctx
    if r not in _FLEET_MODULE_ROLES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Fleet module access denied for this role")

    db, tenant_uuid = db_tenant
    if not await is_module_installed(db, str(tenant_uuid), "fleet"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Fleet module is disabled for this workspace",
        )
    return ctx
