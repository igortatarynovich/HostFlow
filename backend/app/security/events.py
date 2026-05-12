"""Security event emitters — canonical v1 (Phase 2 spike) + legacy compatibility shim."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from backend.app.security.canonical_emit import emit_security_event_v1
from backend.app.security.constants import SECURITY_SYSTEM_ACTOR_UNKNOWN
from backend.app.security.event_taxonomy import (
    EVENT_AUTH_IMPERSONATION_DB_BIND,
    EVENT_RLS_TENANT_CONTEXT_EXECUTE_DENIED,
    EVENT_SUPERADMIN_ELEVATED_DB_BIND,
    EVENT_SUPERADMIN_META_LEADS_OPERATIONAL_REMAP,
)
from backend.app.security.runtime_context import get_security_actor_id, get_security_correlation_id

logger = logging.getLogger("hostflow.security.events")

_EXTRA_BIND = frozenset({"access_kind", "jwt_tenant_id", "elevated_reason", "elevated_scope"})
_EXTRA_META_REMAP = frozenset(
    {"access_kind", "header_tenant_id", "effective_tenant_id", "elevated_reason", "elevated_scope", "jwt_tenant_id"}
)


def emit_security_event(
    action: str,
    *,
    tenant_id: str | None = None,
    actor_id: str | None = None,
    result: str,
    correlation_id: str | None = None,
    **extra: Any,
) -> None:
    """Legacy shim: known Phase-1 actions map to canonical v1; others keep deprecated payload shape."""
    if action == "http.db_bind.superadmin_elevated":
        emit_security_event_v1(
            event_type=EVENT_SUPERADMIN_ELEVATED_DB_BIND,
            result=result,
            severity="info",
            source="http:get_db_with_tenant",
            tenant_id=tenant_id,
            actor_id=actor_id,
            correlation_id=correlation_id,
            access_kind=(extra or {}).get("access_kind"),
            entity_type="tenant",
            entity_id=tenant_id,
            extra=extra,
            extra_allowlist=_EXTRA_BIND,
        )
        return
    if action == "http.db_bind.support_impersonation":
        emit_security_event_v1(
            event_type=EVENT_AUTH_IMPERSONATION_DB_BIND,
            result=result,
            severity="info",
            source="http:get_db_with_tenant",
            tenant_id=tenant_id,
            actor_id=actor_id,
            correlation_id=correlation_id,
            access_kind=(extra or {}).get("access_kind"),
            entity_type="tenant",
            entity_id=tenant_id,
            extra=extra,
            extra_allowlist=_EXTRA_BIND,
        )
        return
    if action == "http.db_bind.meta_leads_operational_remap":
        emit_security_event_v1(
            event_type=EVENT_SUPERADMIN_META_LEADS_OPERATIONAL_REMAP,
            result=result,
            severity="info",
            source="http:get_db_with_meta_leads_effective_tenant",
            tenant_id=tenant_id,
            actor_id=actor_id,
            correlation_id=correlation_id,
            access_kind=(extra or {}).get("access_kind"),
            entity_type="tenant",
            entity_id=tenant_id,
            extra=extra,
            extra_allowlist=_EXTRA_META_REMAP,
        )
        return
    if action == "db.execute.denied_missing_rls_tenant_context":
        emit_security_event_v1(
            event_type=EVENT_RLS_TENANT_CONTEXT_EXECUTE_DENIED,
            result=result,
            severity="high",
            source="db:tenant_enforcing_async_session",
            tenant_id=tenant_id,
            actor_id=actor_id,
            correlation_id=correlation_id,
            access_kind=str((extra or {}).get("access_kind") or "") or None,
            extra=extra,
            extra_allowlist=frozenset({"dialect"}),
        )
        return

    cid = correlation_id if correlation_id is not None else get_security_correlation_id()
    if not (cid or "").strip():
        cid = f"ephemeral:{uuid.uuid4().hex}"
    aid = actor_id if actor_id is not None else get_security_actor_id()
    if not (aid or "").strip():
        aid = SECURITY_SYSTEM_ACTOR_UNKNOWN
    payload: dict[str, Any] = {
        "schema": "hostflow.security_event",
        "schema_version": 1,
        "action": action,
        "tenant_id": tenant_id,
        "actor_id": aid,
        "result": result,
        "correlation_id": cid,
    }
    if extra:
        payload["extra"] = extra
    logger.info("security_event", extra={"security_event": payload})
