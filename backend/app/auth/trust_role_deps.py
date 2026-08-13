"""ADR-036 FastAPI trust-role allowlists for route gates.

Use these instead of job-title / portal-legacy ``require_roles(...)`` lists.
Fine-grained access remains on module matrix (``require_module_gate``) and
entity ACL / org helpers — trust roles are only the coarse ceiling.
"""
from __future__ import annotations

from fastapi import Depends, HTTPException, status

from backend.app.auth.deps import Role, UserCtx, get_current_user, require_roles
from backend.app.auth.trust_roles import (
    TrustRole,
    is_portal_actor,
    normalize_trust_role,
)

# Canonical trust allowlists (legacy DB roles still pass via actor_satisfies bridges).
TRUST_READ_ROLES = (Role.administrator, Role.employee, Role.viewer)
TRUST_WRITE_ROLES = (Role.administrator, Role.employee)
TRUST_ADMIN_ROLES = (Role.administrator,)


def require_trust_read():
    """Administrator / employee / viewer (tenant or portal) — read ceiling."""
    return require_roles(*TRUST_READ_ROLES)


def require_trust_write():
    """Administrator / employee — mutate ceiling (module matrix still applies)."""
    return require_roles(*TRUST_WRITE_ROLES)


def require_trust_admin():
    """Tenant administrator (superadmin bypasses inside require_roles)."""
    return require_roles(*TRUST_ADMIN_ROLES)


def require_portal_context():
    """Require portal access_context (or legacy client_*). Admins bypass."""

    async def _checker(u: UserCtx = Depends(get_current_user)) -> str:
        ur = (u.role or "").strip().lower()
        trust = normalize_trust_role(ur)
        if trust in {TrustRole.superadmin.value, TrustRole.administrator.value}:
            return ur
        if not is_portal_actor(ur, getattr(u, "access_context", None)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Portal context required",
            )
        return ur

    return _checker


def require_trust_write_or_portal():
    """Mutate ceiling for employee/admin, or portal viewers (not tenant viewers)."""
    from backend.app.auth.trust_roles import actor_satisfies_role_allowlist

    async def _checker(u: UserCtx = Depends(get_current_user)) -> str:
        ur = (u.role or "").strip().lower()
        ctx = getattr(u, "access_context", None)
        trust = normalize_trust_role(ur)
        if trust in {TrustRole.superadmin.value, TrustRole.administrator.value}:
            return ur
        if actor_satisfies_role_allowlist(
            role=ur,
            allowed={Role.administrator.value, Role.employee.value},
            access_context=ctx,
        ):
            return ur
        if actor_satisfies_role_allowlist(
            role=ur,
            allowed={Role.viewer.value},
            access_context=ctx,
        ) and is_portal_actor(ur, ctx):
            return ur
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    return _checker
