"""CRM list / mass-read security telemetry (emit_security_event_v1 only).

Phase 2 golden path companion to ``export_events`` — covers ``query_class=list``.
"""

from __future__ import annotations

from typing import Any

from backend.app.security.canonical_emit import emit_security_event_v1

ACCESS_EVENT_EXTRA_ALLOWLIST = frozenset(
    {
        "query_class",
        "route",
        "row_count",
        "limit",
        "offset",
        "duration_ms",
        "filter_scope",
        "reason",
        "response_mode",
    }
)


def clip_access_filter_scope(value: str | None, *, max_len: int = 256) -> str | None:
    """Keep ``filter_scope`` bounded; producers must not put SQL / raw filters here."""
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    return s[:max_len]


def emit_access_security_event_v1(
    *,
    event_type: str,
    result: str,
    severity: str,
    source: str,
    tenant_id: str | None,
    access_kind: str | None,
    entity_type: str,
    entity_id: str | None,
    query_class: str,
    route: str,
    actor_id: str | None = None,
    correlation_id: str | None = None,
    row_count: int | None = None,
    limit: int | None = None,
    offset: int | None = None,
    duration_ms: int | None = None,
    filter_scope: str | None = None,
    reason: str | None = None,
    response_mode: str | None = None,
) -> dict[str, Any]:
    """Emit a list/access-scoped security event with a strict ``extra`` allowlist."""
    extra: dict[str, Any] = {
        "query_class": str(query_class).strip()[:64],
        "route": str(route).strip()[:256],
    }
    if row_count is not None:
        extra["row_count"] = int(row_count)
    if limit is not None:
        extra["limit"] = int(limit)
    if offset is not None:
        extra["offset"] = int(offset)
    if duration_ms is not None:
        extra["duration_ms"] = max(0, int(duration_ms))
    fs = clip_access_filter_scope(filter_scope)
    if fs is not None:
        extra["filter_scope"] = fs
    if reason is not None:
        extra["reason"] = str(reason).strip()[:256]
    if response_mode is not None:
        extra["response_mode"] = str(response_mode).strip()[:64]

    return emit_security_event_v1(
        event_type=event_type,
        result=result,
        severity=severity,
        source=source,
        tenant_id=tenant_id,
        actor_id=actor_id,
        correlation_id=correlation_id,
        access_kind=access_kind,
        action=event_type,
        entity_type=entity_type,
        entity_id=entity_id,
        extra=extra,
        extra_allowlist=ACCESS_EVENT_EXTRA_ALLOWLIST,
    )


__all__ = [
    "ACCESS_EVENT_EXTRA_ALLOWLIST",
    "clip_access_filter_scope",
    "emit_access_security_event_v1",
]
