"""Service for tenant_links (agency ↔ client). Used for handoff feature."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.tenant import TenantLink


async def get_tenant_link(
    db: AsyncSession,
    agency_tenant_id: str,
    client_company_id: str | None = None,
    client_tenant_id: str | None = None,
) -> TenantLink | None:
    """Get active tenant link by agency and client (company or tenant)."""
    stmt = select(TenantLink).where(
        TenantLink.agency_tenant_id == agency_tenant_id,
        TenantLink.status == "active",
    )
    if client_company_id:
        stmt = stmt.where(TenantLink.client_company_id == client_company_id)
    elif client_tenant_id:
        stmt = stmt.where(TenantLink.client_tenant_id == client_tenant_id)
    else:
        return None
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def is_handoff_enabled(
    db: AsyncSession,
    agency_tenant_id: str,
    client_company_id: str | None = None,
    client_tenant_id: str | None = None,
) -> bool:
    """Check if handoff is enabled for the given agency–client link."""
    link = await get_tenant_link(
        db,
        agency_tenant_id=agency_tenant_id,
        client_company_id=client_company_id,
        client_tenant_id=client_tenant_id,
    )
    return link.get_handoff_enabled() if link else False


async def list_links_for_agency(
    db: AsyncSession,
    agency_tenant_id: str,
    status: str = "active",
) -> list[TenantLink]:
    """List all tenant links for an agency."""
    stmt = (
        select(TenantLink)
        .where(TenantLink.agency_tenant_id == agency_tenant_id)
        .where(TenantLink.status == status)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())
