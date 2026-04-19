"""DB session scoped to the Meta Leads data tenant (may differ from X-Tenant-Id for platform superadmin)."""

from __future__ import annotations

from typing import AsyncGenerator, Tuple
from uuid import UUID

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.deps import UserCtx, get_current_user
from backend.app.db.deps import (
    PUBLIC_LEGACY_DEFAULT_TENANT_UUID,
    bind_tenant_context_to_session,
    get_db,
)
from backend.app.modules.leads.meta_tenant_resolve import resolve_meta_leads_effective_tenant_id


def ensure_token_matches_header_tenant(ctx: UserCtx, header_tenant_id: str) -> None:
    token_tenant = (ctx.tenant_id or "").strip()
    if token_tenant and token_tenant != header_tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden for tenant")


async def get_db_with_meta_leads_effective_tenant(
    db: AsyncSession = Depends(get_db),
    tenant_id_header: str | None = Header(None, alias="X-Tenant-Id"),
    ctx: UserCtx = Depends(get_current_user),
) -> AsyncGenerator[Tuple[AsyncSession, UUID, str], None]:
    """
    Yields (db, effective_tenant_uuid, header_tenant_id_str).

    RLS / tenant_visibility are bound to effective_tenant_uuid (Focus when remapped).
    Call ensure_token_matches_header_tenant(ctx, header_tid) in the route before using effective id.
    """
    raw = (tenant_id_header or "").strip()
    if not raw:
        raw = str(PUBLIC_LEGACY_DEFAULT_TENANT_UUID)
    try:
        UUID(raw)
    except Exception:
        raise HTTPException(status_code=400, detail="X-Tenant-Id must be a valid UUID")

    effective_str = resolve_meta_leads_effective_tenant_id(ctx, raw)
    try:
        effective_uuid = UUID(effective_str)
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="META_LEADS_OPERATIONAL_TENANT_ID must be a valid UUID when set",
        )

    await bind_tenant_context_to_session(db, effective_uuid)
    yield db, effective_uuid, raw
