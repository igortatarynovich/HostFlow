"""Canonical security event emitter (schema v1) — transport-agnostic JSON log line."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Mapping

from backend.app.security.constants import SECURITY_SYSTEM_ACTOR_UNKNOWN
from backend.app.security.event_redaction import redact_and_size_extra_safe
from backend.app.security.event_taxonomy import category_from_event_type, validate_event_type
from backend.app.security.runtime_context import get_security_actor_id, get_security_correlation_id

logger = logging.getLogger("hostflow.security.events")

CANONICAL_SCHEMA_VERSION = 1

ALLOWED_SEVERITY = frozenset({"debug", "info", "low", "medium", "high", "critical"})
ALLOWED_RESULT = frozenset({"success", "denied", "error"})


def _normalize_result(result: str) -> str:
    r = (result or "").strip().lower()
    if r == "allowed":
        return "success"
    if r not in ALLOWED_RESULT:
        raise ValueError(f"Invalid security event result: {result!r}")
    return r


def emit_security_event_v1(
    *,
    event_type: str,
    result: str,
    severity: str,
    source: str,
    tenant_id: str | None = None,
    actor_id: str | None = None,
    correlation_id: str | None = None,
    access_kind: str | None = None,
    action: str | None = None,
    entity_type: str | None = None,
    entity_id: str | None = None,
    extra: Mapping[str, Any] | None = None,
    extra_allowlist: frozenset[str] | None = None,
) -> dict[str, Any]:
    """Emit one canonical security event. Returns the payload (for tests). Producers must not depend on transport."""
    et = validate_event_type(event_type)
    sev = (severity or "").strip().lower()
    if sev not in ALLOWED_SEVERITY:
        raise ValueError(f"Invalid severity: {severity!r}")
    res = _normalize_result(result)
    src = (source or "").strip()
    if not src:
        raise ValueError("source is required")

    cid = correlation_id if correlation_id is not None else get_security_correlation_id()
    if not (cid or "").strip():
        cid = f"ephemeral:{uuid.uuid4().hex}"
    aid = actor_id if actor_id is not None else get_security_actor_id()
    if not (aid or "").strip():
        aid = SECURITY_SYSTEM_ACTOR_UNKNOWN

    act = (action or "").strip() or et
    validate_event_type(act)  # action must follow same taxonomy rules

    ts = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    eid = str(uuid.uuid4())

    extra_out = redact_and_size_extra_safe(extra, allowlist=extra_allowlist)

    payload: dict[str, Any] = {
        "schema": "hostflow.security_event_canonical",
        "schema_version": CANONICAL_SCHEMA_VERSION,
        "event_id": eid,
        "event_type": et,
        "category": category_from_event_type(et),
        "severity": sev,
        "timestamp": ts,
        "tenant_id": tenant_id,
        "actor_id": aid,
        "correlation_id": cid,
        "access_kind": access_kind,
        "action": act,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "result": res,
        "source": src,
        "extra": extra_out,
    }
    logger.info("security_event", extra={"security_event": payload})
    try:
        from backend.app.security.detection_engine import maybe_raise_detection_alerts

        maybe_raise_detection_alerts(payload)
    except Exception:
        logger.exception("detection_engine hook failed")
    return payload
