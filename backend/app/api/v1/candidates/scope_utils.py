"""Shared tenant scope for candidate list vs detail (scope_tenant_id query override)."""

from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.deps import UserCtx
from backend.app.db.deps import compute_tenant_visibility_for_tenant
from backend.app.services.tenant_visibility import TenantVisibility


def resolve_optional_scope_tenant_uuid(
    scope_tenant_id: str | None = Query(
        default=None,
        description=(
            "Optional workspace tenant scope override (same as list/detail). "
            "Empty or whitespace is ignored. Must be a valid UUID when non-empty."
        ),
    ),
) -> UUID | None:
    """
    Query ``scope_tenant_id`` as str so clients sending ``?scope_tenant_id=`` do not
    hit FastAPI's UUID parser (which returns 422 for empty string).
    """
    if scope_tenant_id is None:
        return None
    s = str(scope_tenant_id).strip()
    if not s:
        return None
    try:
        return UUID(s)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid scope_tenant_id: expected a UUID",
        ) from None


def candidate_scope_tenant_str(
    header_tenant: UUID,
    scope_tenant_id: UUID | None,
    current_user: UserCtx,
) -> str:
    """Same rule as list_candidates: optional scope_tenant_id overrides X-Tenant-Id for visibility."""
    if scope_tenant_id is not None:
        return str(scope_tenant_id)
    header_s = str(header_tenant).strip()
    jwt_s = str(current_user.tenant_id or "").strip()
    return header_s or jwt_s or header_s


async def bind_candidate_scope_rls(db: AsyncSession, scope_tenant: str) -> None:
    """Set Postgres ``app.tenant_id`` for RLS and align ``db.info['tenant_visibility']``.

    When ``scope_tenant_id`` overrides ``X-Tenant-Id``, ``get_tenant_visibility(db, scope)``
    used to return an empty ``TenantVisibility`` (header cache mismatch), dropping
    shared vacancy/company branches from ``_candidate_scope_clause`` and causing
    spurious 404 on ``GET /candidates/{id}`` while the list still showed the row.
    """
    try:
        await db.execute(
            text("SELECT set_config('app.tenant_id', :tid, true)"),
            {"tid": scope_tenant},
        )
    except Exception:
        pass
    tid = str(scope_tenant).strip()
    if not tid:
        return
    try:
        scope_uuid = UUID(tid)
    except Exception:
        return
    info = getattr(db, "info", None)
    if not isinstance(info, dict):
        return
    cached = info.get("tenant_visibility")
    if isinstance(cached, TenantVisibility) and cached.tenant_id == tid:
        return
    try:
        info["tenant_visibility"] = await compute_tenant_visibility_for_tenant(db, scope_uuid)
        info["tenant_id"] = scope_uuid
    except Exception:
        pass
