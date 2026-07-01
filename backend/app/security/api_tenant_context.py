"""HTTP API: classify tenant DB bind vs JWT (superadmin elevated, support impersonation, tenant-bound)."""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING

from backend.app.auth.deps import Role
from backend.app.security.constants import (
    ALLOWED_ELEVATED_SCOPES,
    SECURITY_ELEVATED_SCOPE_CROSS_TENANT_RLS,
    SECURITY_ELEVATED_SCOPE_META_LEADS_OPS,
    SECURITY_ELEVATED_SCOPE_SUPPORT_SESSION,
)

if TYPE_CHECKING:
    from backend.app.auth.deps import UserCtx


class SecurityAccessKind(str, Enum):
    tenant_bound = "tenant_bound"
    superadmin_elevated = "superadmin_elevated"
    support_impersonation = "support_impersonation"


def _norm_tenant_id(value: str | None) -> str:
    return (value or "").strip().lower()


def _support_impersonation_matches_header(user: "UserCtx", header_tid: str) -> bool:
    raw = user.raw or {}
    imp = raw.get("impersonating_tenant_id")
    if imp is None:
        return False
    return _norm_tenant_id(str(imp)) == _norm_tenant_id(header_tid)


def classify_api_tenant_access(
    user: "UserCtx | None",
    *,
    header_tenant_id: str,
    elevated_reason: str | None,
    elevated_scope: str | None,
) -> tuple[SecurityAccessKind, str | None]:
    """Return ``(access_kind, default_elevated_scope)``.

    ``default_elevated_scope`` is set only for elevated kinds (superadmin / support).
    """
    ht = _norm_tenant_id(header_tenant_id)
    if not user:
        return SecurityAccessKind.tenant_bound, None

    jwt_tid = _norm_tenant_id(user.tenant_id)
    role = (user.role or "").strip().lower()

    if not jwt_tid or jwt_tid == ht:
        return SecurityAccessKind.tenant_bound, None

    if role == Role.superadmin.value:
        scope = (elevated_scope or "").strip() or SECURITY_ELEVATED_SCOPE_CROSS_TENANT_RLS
        if scope not in ALLOWED_ELEVATED_SCOPES:
            scope = SECURITY_ELEVATED_SCOPE_CROSS_TENANT_RLS
        return SecurityAccessKind.superadmin_elevated, scope

    if _support_impersonation_matches_header(user, header_tenant_id):
        scope = (elevated_scope or "").strip() or SECURITY_ELEVATED_SCOPE_SUPPORT_SESSION
        if scope not in ALLOWED_ELEVATED_SCOPES:
            scope = SECURITY_ELEVATED_SCOPE_SUPPORT_SESSION
        return SecurityAccessKind.support_impersonation, scope

    return SecurityAccessKind.tenant_bound, None


def require_elevated_reason_or_raise(*, reason: str | None, detail: str) -> str:
    cleaned = (reason or "").strip()
    if not cleaned:
        from fastapi import HTTPException, status

        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)
    return cleaned

