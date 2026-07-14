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
    elevated_reason: str | None = Header(None, alias="X-HostFlow-Elevated-Reason"),
    elevated_scope: str | None = Header(None, alias="X-HostFlow-Elevated-Scope"),
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

    from backend.app.security.api_tenant_context import require_elevated_reason_or_raise
    from backend.app.security.constants import (
        ALLOWED_ELEVATED_SCOPES,
        SECURITY_ELEVATED_SCOPE_META_LEADS_OPS,
    )
    from backend.app.security.canonical_emit import emit_security_event_v1
    from backend.app.security.event_taxonomy import EVENT_SUPERADMIN_META_LEADS_OPERATIONAL_REMAP
    from backend.app.security.runtime_context import set_security_actor_id

    if getattr(ctx, "sub", None):
        set_security_actor_id(str(ctx.sub))

    if str(effective_uuid) != raw:
        er = require_elevated_reason_or_raise(
            reason=elevated_reason,
            detail=(
                "X-HostFlow-Elevated-Reason is required when Meta leads DB tenant "
                "differs from X-Tenant-Id (operational remap)"
            ),
        )
        scope = (elevated_scope or "").strip() or SECURITY_ELEVATED_SCOPE_META_LEADS_OPS
        if scope not in ALLOWED_ELEVATED_SCOPES:
            scope = SECURITY_ELEVATED_SCOPE_META_LEADS_OPS
        emit_security_event_v1(
            event_type=EVENT_SUPERADMIN_META_LEADS_OPERATIONAL_REMAP,
            result="success",
            severity="info",
            source="http:get_db_with_meta_leads_effective_tenant",
            tenant_id=str(effective_uuid),
            access_kind="superadmin_elevated",
            entity_type="tenant",
            entity_id=str(effective_uuid),
            extra={
                "access_kind": "superadmin_elevated",
                "header_tenant_id": raw,
                "effective_tenant_id": str(effective_uuid),
                "elevated_reason": er,
                "elevated_scope": scope,
                "jwt_tenant_id": (ctx.tenant_id or "").strip(),
            },
            extra_allowlist=frozenset(
                {
                    "access_kind",
                    "header_tenant_id",
                    "effective_tenant_id",
                    "elevated_reason",
                    "elevated_scope",
                    "jwt_tenant_id",
                }
            ),
        )
        db.info["security_access_kind"] = "superadmin_elevated"
        db.info["security_elevated_reason"] = er
        db.info["security_elevated_scope"] = scope
    else:
        db.info["security_access_kind"] = "tenant_bound"
        db.info["security_elevated_reason"] = None
        db.info["security_elevated_scope"] = None

    db.info["tenant_rls_enforcement"] = True
    await bind_tenant_context_to_session(db, effective_uuid)
    yield db, effective_uuid, raw
