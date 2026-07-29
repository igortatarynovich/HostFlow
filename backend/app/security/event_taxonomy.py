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
    "access.",
    "export.",
    "upload.",
    "document.",
    "webhook.",
    "automation.",
    "superadmin.",
    "search.",
    "ai.",
    "detection.",
)

_EVENT_TYPE_RE = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z0-9_]+)+$")

# Spike canonical types (use these at call sites).
EVENT_SUPERADMIN_ELEVATED_DB_BIND = "superadmin.elevated.db_bind"
EVENT_AUTH_IMPERSONATION_DB_BIND = "auth.impersonation.db_bind"
EVENT_RLS_TENANT_CONTEXT_EXECUTE_DENIED = "rls.tenant_context.execute_denied"
EVENT_SUPERADMIN_META_LEADS_OPERATIONAL_REMAP = "superadmin.meta_leads.operational_remap"

# Mass list / CRM read surfaces (Phase 2 golden path — list half; export uses export.*)
EVENT_ACCESS_LIST_COMPLETED = "access.list.completed"
EVENT_ACCESS_LIST_DENIED = "access.list.denied"

# Document / signed URL access (Phase 3 — v1 telemetry)
EVENT_DOCUMENT_METADATA_READ = "document.metadata.read"
EVENT_DOCUMENT_FILE_ACCESS_REQUESTED = "document.file.access_requested"
EVENT_DOCUMENT_FILE_DOWNLOADED = "document.file.downloaded"
EVENT_DOCUMENT_SIGNED_URL_GENERATED = "document.signed_url.generated"
EVENT_DOCUMENT_SIGNED_URL_DENIED = "document.signed_url.denied"
EVENT_DOCUMENT_SIGNED_URL_EXPIRED = "document.signed_url.expired"
EVENT_DOCUMENT_SIGNED_URL_REPLAY_DENIED = "document.signed_url.replay_denied"

# Export telemetry (v1 — CLASS 3 / insider-risk surface)
EVENT_EXPORT_REQUESTED = "export.requested"
EVENT_EXPORT_GENERATED = "export.generated"
EVENT_EXPORT_DOWNLOADED = "export.downloaded"
EVENT_EXPORT_DENIED = "export.denied"
EVENT_EXPORT_EXPIRED = "export.expired"
EVENT_EXPORT_ANOMALY_DETECTED = "export.anomaly.detected"

# Search / AI retrieval audit (governance PR — call sites follow separately)
EVENT_SEARCH_RETRIEVAL_REQUESTED = "search.retrieval.requested"
EVENT_SEARCH_RETRIEVAL_COMPLETED = "search.retrieval.completed"
EVENT_SEARCH_RETRIEVAL_DENIED = "search.retrieval.denied"
EVENT_AI_RETRIEVAL_REQUESTED = "ai.retrieval.requested"
EVENT_AI_RETRIEVAL_COMPLETED = "ai.retrieval.completed"
EVENT_AI_RETRIEVAL_DENIED = "ai.retrieval.denied"

# Phase 7 — detection / alerting (reaction layer on top of telemetry)
EVENT_DETECTION_ALERT_RAISED = "detection.alert.raised"


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
