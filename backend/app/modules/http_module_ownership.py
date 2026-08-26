"""HTTP path → product module ownership for Stage 2B gates (ADR-023).

Hostname is NOT an authorization source. Ownership is derived from the API path.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Literal

# Gate modules for the five business products.
# Services capability endpoints inherit Sales entitlement (not a sixth licensed module).
GateModuleKey = Literal["recruitment", "hr", "sales", "fleet", "finance"]

GATE_MODULE_KEYS: Final[frozenset[str]] = frozenset(
    {"recruitment", "hr", "sales", "fleet", "finance"}
)


@dataclass(frozen=True, slots=True)
class HttpModuleOwnership:
    """Longest-prefix match wins."""

    prefix: str
    module: GateModuleKey
    notes: str = ""


# Product + legacy surfaces that MUST pass through require_module_gate.
# Keep in sync with mounts in backend/app/main.py and domain_ownership.py.
HTTP_MODULE_OWNED_PREFIXES: Final[tuple[HttpModuleOwnership, ...]] = (
    # Recruitment
    HttpModuleOwnership("/api/v1/recruitment/candidates", "recruitment"),
    HttpModuleOwnership("/api/v1/recruitment/applications", "recruitment"),
    HttpModuleOwnership("/api/v1/candidates", "recruitment", "legacy"),
    HttpModuleOwnership("/api/v1/vacancies", "recruitment"),
    # HR
    HttpModuleOwnership("/api/v1/hr", "hr"),
    HttpModuleOwnership("/api/v1/workforce", "hr", "legacy"),
    # Sales
    HttpModuleOwnership("/api/v1/sales/inquiries", "sales"),
    HttpModuleOwnership("/api/v1/sales/clients", "sales"),
    HttpModuleOwnership("/api/v1/client-accounts", "sales", "legacy"),
    # Services capability mounts under Sales deploy host — gate key is sales (not a 6th product module).
    HttpModuleOwnership("/api/v1/services/catalog", "sales", "services capability → sales entitlement"),
    HttpModuleOwnership("/api/v1/services/orders", "sales", "services capability → sales entitlement"),
    HttpModuleOwnership("/api/v1/service-orders", "sales", "legacy → sales"),
    HttpModuleOwnership("/api/v1/services", "sales", "legacy catalog root → sales"),
    # Fleet
    HttpModuleOwnership("/api/v1/fleet", "fleet"),
    # Finance
    HttpModuleOwnership("/api/v1/finance/invoices", "finance"),
    HttpModuleOwnership("/api/v1/finance/payments", "finance"),
    HttpModuleOwnership("/api/v1/invoices", "finance", "legacy"),
)

# Paths under /api/v1 that are intentionally not module-gated (platform / auth / public).
# Integrity tests: every other /api/v1 business surface must appear in HTTP_MODULE_OWNED_PREFIXES
# or this allowlist.
HTTP_MODULE_GATE_EXEMPT_PREFIXES: Final[tuple[str, ...]] = (
    "/api/v1/auth",
    "/api/v1/health",
    "/api/v1/meta",
    "/api/v1/public",
    "/api/v1/settings",
    "/api/v1/platform",
    "/api/v1/admin",
    "/api/v1/tenants",
    "/api/v1/users",
    "/api/v1/onboarding",
    "/api/v1/notifications",
    "/api/v1/communications",
    "/api/v1/documents",
    "/api/v1/search",
    "/api/v1/calendar",
    "/api/v1/reminders",
    "/api/v1/activities",
    "/api/v1/automation",
    "/api/v1/goals",
    "/api/v1/analytics",
    "/api/v1/fx",
    "/api/v1/catalogs",
    "/api/v1/own-companies",
    "/api/v1/legal",
    "/api/v1/forms",
    "/api/v1/field-registry",
    "/api/v1/entity-profiles",
    "/api/v1/requirement",
    "/api/v1/notification-events",
    "/api/v1/module-registry",
    "/api/v1/billing",
    "/api/v1/leads",  # transport/admin intake — not a product module surface
    "/api/v1/stages",
    "/api/v1/funnels",
    "/api/v1/custom-fields",
    "/api/v1/candidate-profiles",
    "/api/v1/candidate-stages",
    "/api/v1/document-policies",
    "/api/v1/document-merge",
    "/api/v1/contact-attempts",
    "/api/v1/handoffs",
    "/api/v1/next-actions",
    "/api/v1/recruiters",
    "/api/v1/companies",
    "/api/v1/additional-services",
)


def resolve_http_module_owner(path: str) -> GateModuleKey | None:
    """Return owning gate module for a request path, or None if not a gated surface."""
    raw = (path or "").split("?", 1)[0]
    ranked = sorted(HTTP_MODULE_OWNED_PREFIXES, key=lambda row: len(row.prefix), reverse=True)
    for row in ranked:
        if raw == row.prefix or raw.startswith(row.prefix + "/") or raw.startswith(row.prefix + "?"):
            return row.module
        # Exact prefix match without trailing slash variants
        if raw.rstrip("/") == row.prefix.rstrip("/"):
            return row.module
    return None


def is_module_gate_exempt(path: str) -> bool:
    raw = (path or "").split("?", 1)[0]
    for prefix in HTTP_MODULE_GATE_EXEMPT_PREFIXES:
        if raw == prefix or raw.startswith(prefix + "/") or raw.startswith(prefix + "?"):
            return True
    return False


def owned_prefixes_for_module(module: GateModuleKey) -> tuple[str, ...]:
    return tuple(row.prefix for row in HTTP_MODULE_OWNED_PREFIXES if row.module == module)
