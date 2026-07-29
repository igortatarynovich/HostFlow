"""Canonical literals for security runtime (actors, scopes)."""

from __future__ import annotations

# Used when no authenticated user is in context (deny paths, pre-auth failures).
SECURITY_SYSTEM_ACTOR_UNKNOWN = "system:unknown"

# Elevated cross-tenant DB bind (superadmin); default when header omitted.
SECURITY_ELEVATED_SCOPE_CROSS_TENANT_RLS = "cross_tenant_rls"
SECURITY_ELEVATED_SCOPE_META_LEADS_OPS = "meta_leads_operational_tenant"
SECURITY_ELEVATED_SCOPE_SUPPORT_SESSION = "support_session"

ALLOWED_ELEVATED_SCOPES: frozenset[str] = frozenset(
    {
        SECURITY_ELEVATED_SCOPE_CROSS_TENANT_RLS,
        SECURITY_ELEVATED_SCOPE_META_LEADS_OPS,
        SECURITY_ELEVATED_SCOPE_SUPPORT_SESSION,
        "global",
    }
)

# Phase 5 — time-bound platform impersonation (JWT exp).
IMPERSONATION_TTL_MINUTES = 30
IMPERSONATION_REASON_MIN_LEN = 3
IMPERSONATION_REASON_MAX_LEN = 2000
