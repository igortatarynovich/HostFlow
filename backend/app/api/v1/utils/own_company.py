from __future__ import annotations

from typing import Optional

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.deps import UserCtx, get_current_user
from backend.app.db.deps import get_db_with_tenant
from backend.app.models import OwnCompany, Tenant, User
from backend.app.api.v1.utils.own_company_acl import (
    allowed_own_company_ids_from_prefs,
    first_resolvable_own_company_id,
    is_own_company_id_allowed_for_user,
    role_bypasses_own_company_acl,
)


async def ensure_default_own_company(
    db: AsyncSession, *, tenant_id: str, fallback_name: str = "My company"
) -> OwnCompany:
    row = await db.execute(
        select(OwnCompany)
        .where(OwnCompany.tenant_id == tenant_id)
        .order_by(OwnCompany.created_at.asc())
        .limit(1)
    )
    existing = row.scalar_one_or_none()
    if existing is not None:
        return existing

    tenant_row = await db.execute(select(Tenant.name).where(Tenant.id == tenant_id).limit(1))
    name = tenant_row.scalar_one_or_none() or fallback_name
    obj = OwnCompany(tenant_id=tenant_id, name=str(name).strip() or fallback_name)
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


async def resolve_own_company_id_for_session(
    db: AsyncSession,
    tenant_id: str,
    current_user: UserCtx,
    x_own_company_id: Optional[str] = None,
) -> str:
    """
    Resolve active own_company_id for a DB session already scoped to ``tenant_id``.

    Resolution order:
    1) X-Own-Company-Id header (must belong to tenant and pass optional ACL)
    2) User.preferences.active_own_company_id (same checks)
    3) First own company (created_at asc), optionally restricted by ACL

    Users with ``preferences.allowed_own_company_ids`` (non-empty list) are limited to those
    ids unless their role bypasses ACL (administrator / superadmin).
    """

    def _normalize(value: Optional[str]) -> Optional[str]:
        v = str(value or "").strip()
        return v or None

    prefs: dict = {}
    if current_user and current_user.sub:
        user_row = await db.execute(select(User.preferences).where(User.id == str(current_user.sub)).limit(1))
        raw_prefs = user_row.scalar_one_or_none()
        if isinstance(raw_prefs, dict):
            prefs = raw_prefs

    bypass = role_bypasses_own_company_acl(current_user.role if current_user else None)
    allowed = allowed_own_company_ids_from_prefs(prefs)

    header_id = _normalize(x_own_company_id)
    if header_id:
        row = await db.execute(
            select(OwnCompany.id).where(
                OwnCompany.id == header_id,
                OwnCompany.tenant_id == tenant_id,
                OwnCompany.is_archived.is_(False),
            )
        )
        ok = row.scalar_one_or_none()
        if ok and is_own_company_id_allowed_for_user(header_id, allowed=allowed, bypass=bypass):
            return header_id
        # Stale/mismatched header or ACL: ignore and fall back.

    pref_id: Optional[str] = None
    if isinstance(prefs, dict):
        pref_id = _normalize(prefs.get("active_own_company_id"))  # type: ignore[arg-type]
    if pref_id:
        row = await db.execute(
            select(OwnCompany.id).where(
                OwnCompany.id == pref_id,
                OwnCompany.tenant_id == tenant_id,
                OwnCompany.is_archived.is_(False),
            )
        )
        ok = row.scalar_one_or_none()
        if ok and is_own_company_id_allowed_for_user(pref_id, allowed=allowed, bypass=bypass):
            return pref_id

    first_id = await first_resolvable_own_company_id(db, tenant_id, allowed=allowed, bypass=bypass)
    if first_id:
        return str(first_id)

    raise HTTPException(
        status_code=status.HTTP_412_PRECONDITION_FAILED,
        detail={"code": "OWN_COMPANY_REQUIRED", "message": "Own company must be created first"},
    )


async def resolve_active_own_company_id(
    request: Request,
    db_tenant=Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
    x_own_company_id: Optional[str] = Header(default=None, alias="X-Own-Company-Id"),
) -> str:
    db, tenant_uuid = db_tenant
    return await resolve_own_company_id_for_session(
        db, str(tenant_uuid), current_user, x_own_company_id
    )


async def resolve_active_own_company_id_optional(
    request: Request,
    db_tenant=Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
    x_own_company_id: Optional[str] = Header(default=None, alias="X-Own-Company-Id"),
) -> Optional[str]:
    """
    Best-effort variant for list endpoints.

    Returns None instead of failing when own company is not configured yet
    or header points to an invalid company for current tenant.
    """
    try:
        return await resolve_active_own_company_id(
            request=request,
            db_tenant=db_tenant,
            current_user=current_user,
            x_own_company_id=x_own_company_id,
        )
    except HTTPException as exc:
        if exc.status_code in (
            status.HTTP_412_PRECONDITION_FAILED,
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        ):
            return None
        raise

