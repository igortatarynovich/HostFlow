from __future__ import annotations

from backend.app.api.v1.candidates.acl import CandidateACL, resolve_candidate_acl
from backend.app.auth.deps import Role, UserCtx
from sqlalchemy.ext.asyncio import AsyncSession


async def resolve_restricted_acl(
    db: AsyncSession,
    tenant_id: str,
    user: UserCtx,
) -> CandidateACL | None:
    """
    Return a CandidateACL for the user only if they should be restricted.
    Administrators and superadmins are treated as unrestricted.
    """
    role = (user.role or "").strip().lower()
    if role in {Role.superadmin.value, Role.administrator.value}:
        return None

    acl = await resolve_candidate_acl(db, tenant_id, user)
    if acl.unrestricted:
        return None
    return acl
