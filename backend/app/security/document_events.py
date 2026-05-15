"""Document access security telemetry (emit_security_event_v1 only)."""

from __future__ import annotations

from typing import Any

from backend.app.security.canonical_emit import emit_security_event_v1

DOCUMENT_EVENT_EXTRA_ALLOWLIST = frozenset(
    {
        "document_class",
        "candidate_id",
        "reason",
        "file_version",
        "response_mode",
        "upload_presign",
        "has_presigned_url_shape",
        "intake_channel",
    }
)


def url_looks_presigned(url: str | None) -> bool:
    """Heuristic for presigned/public GET shapes — inspect only in-process, never log ``url``."""
    if not url or not isinstance(url, str):
        return False
    u = url.lower()
    return (
        "x-amz-" in u
        or "x-goog-" in u
        or "signature=" in u
        or "awsaccesskeyid=" in u
    )


def emit_document_security_event_v1(
    *,
    event_type: str,
    result: str,
    severity: str,
    source: str,
    tenant_id: str | None,
    document_id: str | None,
    access_kind: str | None,
    actor_id: str | None = None,
    correlation_id: str | None = None,
    document_class: str | None = None,
    candidate_id: str | None = None,
    reason: str | None = None,
    file_version: int | None = None,
    response_mode: str | None = None,
    upload_presign: bool | None = None,
    has_presigned_url_shape: bool | None = None,
    intake_channel: str | None = None,
) -> dict[str, Any]:
    """Emit a document-scoped security event with a strict ``extra`` allowlist."""
    extra: dict[str, Any] = {}
    if document_class is not None:
        extra["document_class"] = str(document_class)
    if candidate_id is not None:
        extra["candidate_id"] = str(candidate_id)
    if reason is not None:
        extra["reason"] = str(reason)
    if file_version is not None:
        extra["file_version"] = int(file_version)
    if response_mode is not None:
        extra["response_mode"] = str(response_mode)
    if upload_presign is not None:
        extra["upload_presign"] = bool(upload_presign)
    if has_presigned_url_shape is not None:
        extra["has_presigned_url_shape"] = bool(has_presigned_url_shape)
    if intake_channel is not None:
        extra["intake_channel"] = str(intake_channel)

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
        entity_type="document",
        entity_id=document_id,
        extra=extra,
        extra_allowlist=DOCUMENT_EVENT_EXTRA_ALLOWLIST,
    )


__all__ = [
    "DOCUMENT_EVENT_EXTRA_ALLOWLIST",
    "emit_document_security_event_v1",
    "url_looks_presigned",
]
