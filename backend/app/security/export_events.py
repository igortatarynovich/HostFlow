"""Export security telemetry (emit_security_event_v1 only)."""

from __future__ import annotations

from typing import Any

from backend.app.security.canonical_emit import emit_security_event_v1

EXPORT_EVENT_EXTRA_ALLOWLIST = frozenset(
    {
        "export_type",
        "row_count",
        "byte_size",
        "filter_scope",
        "async_job_id",
        "export_scope",
        "contains_class3",
        "bulk_operation",
        "reason",
        "response_mode",
    }
)


def clip_export_filter_scope(value: str | None, *, max_len: int = 256) -> str | None:
    """Keep ``filter_scope`` bounded; producers must not put SQL / raw filters here."""
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    return s[:max_len]


def emit_export_security_event_v1(
    *,
    event_type: str,
    result: str,
    severity: str,
    source: str,
    tenant_id: str | None,
    access_kind: str | None,
    entity_type: str,
    entity_id: str | None,
    export_type: str,
    actor_id: str | None = None,
    correlation_id: str | None = None,
    row_count: int | None = None,
    byte_size: int | None = None,
    filter_scope: str | None = None,
    async_job_id: str | None = None,
    export_scope: str | None = None,
    contains_class3: bool | None = None,
    bulk_operation: bool | None = None,
    reason: str | None = None,
    response_mode: str | None = None,
) -> dict[str, Any]:
    """Emit an export-scoped security event with a strict ``extra`` allowlist."""
    extra: dict[str, Any] = {"export_type": str(export_type).strip()[:128]}
    if row_count is not None:
        extra["row_count"] = int(row_count)
    if byte_size is not None:
        extra["byte_size"] = int(byte_size)
    fs = clip_export_filter_scope(filter_scope)
    if fs is not None:
        extra["filter_scope"] = fs
    if async_job_id is not None:
        extra["async_job_id"] = str(async_job_id).strip()[:128]
    if export_scope is not None:
        extra["export_scope"] = str(export_scope).strip()[:64]
    if contains_class3 is not None:
        extra["contains_class3"] = bool(contains_class3)
    if bulk_operation is not None:
        extra["bulk_operation"] = bool(bulk_operation)
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
        extra_allowlist=EXPORT_EVENT_EXTRA_ALLOWLIST,
    )


__all__ = [
    "EXPORT_EVENT_EXTRA_ALLOWLIST",
    "clip_export_filter_scope",
    "emit_export_security_event_v1",
]
