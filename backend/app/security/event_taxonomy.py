"""Security event taxonomy — namespace rules (Phase 2 spike).

``event_type`` / ``action`` must start with one of these prefixes to pass validation.
"""

from __future__ import annotations

import re

# Namespace roots (strict). Extend via PR + taxonomy doc, not ad-hoc strings.
ALLOWED_EVENT_PREFIXES: tuple[str, ...] = (
    "auth.",
    "rls.",
    "db.",
    "export.",
    "upload.",
    "document.",
    "webhook.",
    "automation.",
    "superadmin.",
    "search.",
    "ai.",
)

_EVENT_TYPE_RE = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z0-9_]+)+$")

# Spike canonical types (use these at call sites).
EVENT_SUPERADMIN_ELEVATED_DB_BIND = "superadmin.elevated.db_bind"
EVENT_AUTH_IMPERSONATION_DB_BIND = "auth.impersonation.db_bind"
EVENT_RLS_TENANT_CONTEXT_EXECUTE_DENIED = "rls.tenant_context.execute_denied"
EVENT_SUPERADMIN_META_LEADS_OPERATIONAL_REMAP = "superadmin.meta_leads.operational_remap"


def validate_event_type(event_type: str) -> str:
    """Return normalized ``event_type`` or raise ``ValueError``."""
    et = (event_type or "").strip().lower()
    if not et or not _EVENT_TYPE_RE.match(et):
        raise ValueError(f"Invalid event_type format: {event_type!r}")
    if not any(et.startswith(p) for p in ALLOWED_EVENT_PREFIXES):
        raise ValueError(
            f"event_type {et!r} must start with one of: " + ", ".join(ALLOWED_EVENT_PREFIXES)
        )
    return et


def category_from_event_type(event_type: str) -> str:
    """First segment of ``event_type`` (must match a known category root without trailing dot)."""
    et = validate_event_type(event_type)
    return et.split(".", 1)[0]
