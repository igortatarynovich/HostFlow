"""Search / AI retrieval audit telemetry (emit_security_event_v1 only).

Governance: docs/security/retrieval-audit-governance.md
"""

from __future__ import annotations

from typing import Any, Sequence

from backend.app.security.canonical_emit import emit_security_event_v1

RETRIEVAL_EVENT_EXTRA_ALLOWLIST = frozenset(
    {
        "retrieval_type",
        "retrieval_scope",
        "requested_entity_types",
        "returned_count",
        "filtered_count",
        "denied_count",
        "policy_scope",
        "contains_class3",
        "reason",
        "model_context_used",
        "response_mode",
    }
)


def _clip_reason(value: str | None, *, max_len: int = 256) -> str | None:
    if value is None:
        return None
    s = str(value).strip().replace("\n", " ").replace("\r", " ")
    if not s:
        return None
    return s[:max_len]


def _encode_requested_entity_types(types: Sequence[str] | None, *, max_len: int = 512) -> str | None:
    if not types:
        return None
    parts = [str(t).strip() for t in types if str(t).strip()]
    if not parts:
        return None
    out = ",".join(parts)[:max_len]
    return out or None


def emit_retrieval_security_event_v1(
    *,
    event_type: str,
    result: str,
    severity: str,
    source: str,
    tenant_id: str | None,
    access_kind: str | None,
    entity_type: str | None = None,
    entity_id: str | None = None,
    actor_id: str | None = None,
    correlation_id: str | None = None,
    retrieval_type: str | None = None,
    retrieval_scope: str | None = None,
    requested_entity_types: Sequence[str] | None = None,
    returned_count: int | None = None,
    filtered_count: int | None = None,
    denied_count: int | None = None,
    policy_scope: str | None = None,
    contains_class3: bool | None = None,
    reason: str | None = None,
    model_context_used: bool | None = None,
    response_mode: str | None = None,
) -> dict[str, Any]:
    """Emit a retrieval-scoped security event; ``extra`` is strictly allowlisted (no raw query/prompt/context)."""
    extra: dict[str, Any] = {}
    if retrieval_type is not None:
        extra["retrieval_type"] = str(retrieval_type).strip()[:128]
    if retrieval_scope is not None:
        extra["retrieval_scope"] = str(retrieval_scope).strip()[:128]
    et = _encode_requested_entity_types(requested_entity_types)
    if et is not None:
        extra["requested_entity_types"] = et
    if returned_count is not None:
        extra["returned_count"] = int(returned_count)
    if filtered_count is not None:
        extra["filtered_count"] = int(filtered_count)
    if denied_count is not None:
        extra["denied_count"] = int(denied_count)
    if policy_scope is not None:
        extra["policy_scope"] = str(policy_scope).strip()[:128]
    if contains_class3 is not None:
        extra["contains_class3"] = bool(contains_class3)
    r = _clip_reason(reason)
    if r is not None:
        extra["reason"] = r
    if model_context_used is not None:
        extra["model_context_used"] = bool(model_context_used)
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
        extra=extra or None,
        extra_allowlist=RETRIEVAL_EVENT_EXTRA_ALLOWLIST,
    )


__all__ = [
    "RETRIEVAL_EVENT_EXTRA_ALLOWLIST",
    "emit_retrieval_security_event_v1",
]
