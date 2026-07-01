"""Canonical security event v1 — taxonomy, redaction, emitter."""

from __future__ import annotations

import pytest

from backend.app.security.canonical_emit import emit_security_event_v1
from backend.app.security.event_redaction import redact_and_size_extra
from backend.app.security.event_taxonomy import (
    EVENT_RLS_TENANT_CONTEXT_EXECUTE_DENIED,
    EVENT_SUPERADMIN_ELEVATED_DB_BIND,
    validate_event_type,
)


def test_validate_event_type_rejects_unknown_prefix() -> None:
    with pytest.raises(ValueError):
        validate_event_type("foo.bar")


def test_validate_event_type_accepts_namespaced() -> None:
    assert validate_event_type("superadmin.elevated.db_bind") == "superadmin.elevated.db_bind"


def test_redaction_strips_email_and_forbidden_keys() -> None:
    out = redact_and_size_extra(
        {"jwt_tenant_id": "x", "email": "secret@x.com", "password": "nope"},
        allowlist=frozenset({"jwt_tenant_id", "email", "password"}),
    )
    assert out["jwt_tenant_id"] == "x"
    assert out["email"] == "[REDACTED]"
    assert out["password"] == "[REDACTED]"


def test_emit_security_event_v1_payload_shape() -> None:
    p = emit_security_event_v1(
        event_type=EVENT_SUPERADMIN_ELEVATED_DB_BIND,
        result="success",
        severity="info",
        source="test:unit",
        tenant_id="11111111-1111-1111-1111-111111111111",
        access_kind="superadmin_elevated",
        entity_type="tenant",
        entity_id="11111111-1111-1111-1111-111111111111",
        actor_id="actor-test",
        correlation_id="cid-test",
        extra={"elevated_reason": "unit"},
        extra_allowlist=frozenset({"elevated_reason"}),
    )
    assert p["schema"] == "hostflow.security_event_canonical"
    assert p["schema_version"] == 1
    assert p["event_type"] == EVENT_SUPERADMIN_ELEVATED_DB_BIND
    assert p["category"] == "superadmin"
    assert p["result"] == "success"
    assert p["event_id"]
    assert p["timestamp"].endswith("Z")
    assert p["extra"]["elevated_reason"] == "unit"


def test_emit_security_event_v1_denied_rls() -> None:
    p = emit_security_event_v1(
        event_type=EVENT_RLS_TENANT_CONTEXT_EXECUTE_DENIED,
        result="denied",
        severity="high",
        source="test:unit",
        tenant_id=None,
        extra={"dialect": "postgresql"},
        extra_allowlist=frozenset({"dialect"}),
    )
    assert p["result"] == "denied"
    assert p["severity"] == "high"
    assert p["extra"]["dialect"] == "postgresql"
