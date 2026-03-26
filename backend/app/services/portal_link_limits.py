"""Enforcement for client portal tokens on tenant links (§2.2 / §2.16, TenantLicense.max_public_portal_links)."""

from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.tenant import TenantLink
from backend.app.services.tenant_limits import get_tenant_limits


async def ensure_portal_token_issue_allowed(
    db: AsyncSession,
    *,
    agency_tenant_id: str,
    link: TenantLink,
) -> None:
    """Allow refresh when token already exists; otherwise enforce max_public_portal_links (>0)."""
    if link.portal_token:
        return
    limits = await get_tenant_limits(db, agency_tenant_id)
    cap = limits.max_public_portal_links
    if cap <= 0:
        return
    stmt = (
        select(func.count())
        .select_from(TenantLink)
        .where(TenantLink.agency_tenant_id == agency_tenant_id)
        .where(TenantLink.portal_token.is_not(None))
    )
    current = int((await db.execute(stmt)).scalar_one() or 0)
    if current >= cap:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "portal_link_limit_reached",
                "limit": cap,
                "current": current,
            },
        )
