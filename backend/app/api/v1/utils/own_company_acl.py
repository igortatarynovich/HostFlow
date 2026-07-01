from __future__ import annotations

from typing import Any, FrozenSet, Optional, Set

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.deps import Role
from backend.app.models import OwnCompany

_OWN_COMPANY_ACL_BYPASS_ROLES: FrozenSet[str] = frozenset(
    {
        Role.superadmin.value,
        Role.administrator.value,
    }
)


def role_bypasses_own_company_acl(role: Optional[str]) -> bool:
    """Tenant admins / superadmin ignore per-user own-company ACL."""
    r = (role or "").strip().lower()
    if r in _OWN_COMPANY_ACL_BYPASS_ROLES:
        return True
    if r in ("admin", "owner"):
        return True
    return False


def allowed_own_company_ids_from_prefs(prefs: Any) -> Optional[Set[str]]:
    """
    Non-empty list in preferences → user may only use these own-company ids.
    Missing key / null / empty list → no restriction.
    """
    if not isinstance(prefs, dict):
        return None
    raw = prefs.get("allowed_own_company_ids")
    if raw is None:
        return None
    if not isinstance(raw, (list, tuple)):
        return None
    ids = {str(x).strip() for x in raw if x is not None and str(x).strip()}
    return ids if ids else None


def is_own_company_id_allowed_for_user(
    own_company_id: str,
    *,
    allowed: Optional[Set[str]],
    bypass: bool,
) -> bool:
    if bypass or allowed is None:
        return True
    return str(own_company_id).strip() in allowed


async def first_resolvable_own_company_id(
    db: AsyncSession,
    tenant_id: str,
    *,
    allowed: Optional[Set[str]],
    bypass: bool,
) -> Optional[str]:
    stmt = (
        select(OwnCompany.id)
        .where(
            OwnCompany.tenant_id == tenant_id,
            OwnCompany.is_archived.is_(False),
        )
        .order_by(OwnCompany.created_at.asc())
        .limit(1)
    )
    if allowed is not None and not bypass:
        stmt = stmt.where(OwnCompany.id.in_(allowed))
    row = await db.execute(stmt)
    fid = row.scalar_one_or_none()
    return str(fid) if fid else None
