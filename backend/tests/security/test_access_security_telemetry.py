"""Access list security telemetry (Phase 2 golden path)."""

from __future__ import annotations

from backend.app.security.access_events import (
    ACCESS_EVENT_EXTRA_ALLOWLIST,
    clip_access_filter_scope,
    emit_access_security_event_v1,
)
from backend.app.security.event_redaction import redact_and_size_extra
from backend.app.security.event_taxonomy import (
    EVENT_ACCESS_LIST_COMPLETED,
    EVENT_ACCESS_LIST_DENIED,
    validate_event_type,
)


def test_access_event_types_validate() -> None:
    for et in (EVENT_ACCESS_LIST_COMPLETED, EVENT_ACCESS_LIST_DENIED):
        assert validate_event_type(et) == et


def test_clip_access_filter_scope() -> None:
    assert clip_access_filter_scope("a" * 300) == "a" * 256
    assert clip_access_filter_scope("  x  ") == "x"


def test_emit_access_security_event_v1_shape() -> None:
    p = emit_access_security_event_v1(
        event_type=EVENT_ACCESS_LIST_COMPLETED,
        result="success",
        severity="info",
        source="test:unit",
        tenant_id="11111111-1111-1111-1111-111111111111",
        access_kind="tenant_bound",
        entity_type="tenant",
        entity_id="11111111-1111-1111-1111-111111111111",
        query_class="list",
        route="GET /api/v1/candidates",
        actor_id="actor-1",
        correlation_id="cid-1",
        row_count=42,
        limit=50,
        offset=0,
        duration_ms=12,
        filter_scope="client=0;q=1",
        response_mode="json_list",
    )
    assert p["event_type"] == EVENT_ACCESS_LIST_COMPLETED
    assert p["extra"]["query_class"] == "list"
    assert p["extra"]["route"] == "GET /api/v1/candidates"
    assert p["extra"]["row_count"] == 42
    assert p["extra"]["duration_ms"] == 12
    assert "q" not in p["extra"]
    assert "items" not in p["extra"]


def test_access_extra_allowlist_closed() -> None:
    assert "items" not in ACCESS_EVENT_EXTRA_ALLOWLIST
    assert "query" not in ACCESS_EVENT_EXTRA_ALLOWLIST


def test_redaction_keeps_allowlisted_access_keys() -> None:
    out = redact_and_size_extra(
        {
            "query_class": "list",
            "route": "GET /api/v1/candidates",
            "row_count": 1,
            "secret_query": "should-drop",
        },
        allowlist=ACCESS_EVENT_EXTRA_ALLOWLIST,
    )
    assert out["query_class"] == "list"
    assert "secret_query" not in out
