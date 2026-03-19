from __future__ import annotations

from typing import Optional

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.deps import UserCtx, get_current_user
from backend.app.db.deps import get_db_with_tenant
from backend.app.models import OwnCompany, Tenant, User


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


async def resolve_active_own_company_id(
    request: Request,
    db_tenant=Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
    x_own_company_id: Optional[str] = Header(default=None, alias="X-Own-Company-Id"),
) -> str:
    """
    Resolve active own_company_id for scoping.

    Resolution order:
    1) X-Own-Company-Id header
    2) User.preferences.active_own_company_id
    3) First own company (created_at asc)
    """
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)

    def _normalize(value: Optional[str]) -> Optional[str]:
        v = str(value or "").strip()
        return v or None

    header_id = _normalize(x_own_company_id)
    if header_id:
        row = await db.execute(
            select(OwnCompany.id).where(
                OwnCompany.id == header_id,
                OwnCompany.tenant_id == tenant_id,
            )
        )
        ok = row.scalar_one_or_none()
        if ok:
            return header_id
        # Stale/mismatched header: ignore it and fall back to preference/default.
        # This prevents read endpoints from failing with 422 for client sessions.

    pref_id: Optional[str] = None
    if current_user and current_user.sub:
        user_row = await db.execute(select(User.preferences).where(User.id == str(current_user.sub)).limit(1))
        prefs = user_row.scalar_one_or_none()
        if isinstance(prefs, dict):
            pref_id = _normalize(prefs.get("active_own_company_id"))  # type: ignore[arg-type]
    if pref_id:
        row = await db.execute(
            select(OwnCompany.id).where(
                OwnCompany.id == pref_id,
                OwnCompany.tenant_id == tenant_id,
            )
        )
        ok = row.scalar_one_or_none()
        if ok:
            return pref_id

    row = await db.execute(
        select(OwnCompany.id)
        .where(OwnCompany.tenant_id == tenant_id, OwnCompany.is_archived.is_(False))
        .order_by(OwnCompany.created_at.asc())
        .limit(1)
    )
    first_id = row.scalar_one_or_none()
    if first_id:
        return str(first_id)

    raise HTTPException(
        status_code=status.HTTP_412_PRECONDITION_FAILED,
        detail={"code": "OWN_COMPANY_REQUIRED", "message": "Own company must be created first"},
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

