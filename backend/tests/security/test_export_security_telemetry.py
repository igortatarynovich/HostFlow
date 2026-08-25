"""Export security telemetry (v1)."""

from __future__ import annotations

import pytest

from backend.app.security.event_redaction import redact_and_size_extra
from backend.app.security.event_taxonomy import (
    EVENT_EXPORT_ANOMALY_DETECTED,
    EVENT_EXPORT_DENIED,
    EVENT_EXPORT_DOWNLOADED,
    EVENT_EXPORT_EXPIRED,
    EVENT_EXPORT_GENERATED,
    EVENT_EXPORT_REQUESTED,
    validate_event_type,
)
from backend.app.security.export_events import (
    EXPORT_ANOMALY_CLASS3_ROW_COUNT_THRESHOLD,
    EXPORT_ANOMALY_ROW_COUNT_THRESHOLD,
    EXPORT_EVENT_EXTRA_ALLOWLIST,
    clip_export_filter_scope,
    emit_export_security_event_v1,
    evaluate_export_anomaly_codes,
)


def test_export_event_types_validate() -> None:
    for et in (
        EVENT_EXPORT_REQUESTED,
        EVENT_EXPORT_GENERATED,
        EVENT_EXPORT_DOWNLOADED,
        EVENT_EXPORT_DENIED,
        EVENT_EXPORT_EXPIRED,
        EVENT_EXPORT_ANOMALY_DETECTED,
    ):
        assert validate_event_type(et) == et


def test_clip_export_filter_scope() -> None:
    long = "a" * 300
    assert clip_export_filter_scope(long) == "a" * 256
    assert clip_export_filter_scope("  x  ") == "x"


def test_evaluate_export_anomaly_codes_empty_for_normal() -> None:
    assert (
        evaluate_export_anomaly_codes(
            row_count=10,
            byte_size=1000,
            contains_class3=True,
            bulk_operation=False,
        )
        == []
    )


def test_evaluate_export_anomaly_codes_row_and_class3() -> None:
    codes = evaluate_export_anomaly_codes(
        row_count=EXPORT_ANOMALY_ROW_COUNT_THRESHOLD,
        byte_size=None,
        contains_class3=True,
        bulk_operation=True,
    )
    assert "row_count_threshold" in codes
    assert "class3_bulk" in codes
    codes2 = evaluate_export_anomaly_codes(
        row_count=EXPORT_ANOMALY_CLASS3_ROW_COUNT_THRESHOLD,
        byte_size=None,
        contains_class3=True,
        bulk_operation=False,
    )
    assert codes2 == ["class3_row_count"]


def test_emit_export_generated_emits_anomaly(monkeypatch: pytest.MonkeyPatch) -> None:
    emitted: list[str] = []

    def _capture(**kwargs):  # type: ignore[no-untyped-def]
        emitted.append(str(kwargs.get("event_type")))
        # Minimal shape expected by callers of emit_security_event_v1
        return {
            "event_type": kwargs.get("event_type"),
            "extra": kwargs.get("extra") or {},
            "entity_type": kwargs.get("entity_type"),
        }

    monkeypatch.setattr(
        "backend.app.security.export_events.emit_security_event_v1",
        _capture,
    )
    p = emit_export_security_event_v1(
        event_type=EVENT_EXPORT_GENERATED,
        result="success",
        severity="info",
        source="test:unit",
        tenant_id="11111111-1111-1111-1111-111111111111",
        access_kind="tenant_bound",
        entity_type="candidate",
        entity_id="22222222-2222-2222-2222-222222222222",
        export_type="candidate_documents_json",
        row_count=EXPORT_ANOMALY_ROW_COUNT_THRESHOLD,
        contains_class3=True,
        bulk_operation=False,
        export_scope="single_candidate",
    )
    assert p["event_type"] == EVENT_EXPORT_GENERATED
    assert EVENT_EXPORT_GENERATED in emitted
    assert EVENT_EXPORT_ANOMALY_DETECTED in emitted


def test_emit_export_security_event_v1_shape() -> None:
    p = emit_export_security_event_v1(
        event_type=EVENT_EXPORT_GENERATED,
        result="success",
        severity="info",
        source="test:unit",
        tenant_id="11111111-1111-1111-1111-111111111111",
        access_kind="tenant_bound",
        entity_type="candidate",
        entity_id="22222222-2222-2222-2222-222222222222",
        export_type="candidate_documents_json",
        actor_id="actor-1",
        correlation_id="cid-1",
        row_count=3,
        byte_size=1200,
        filter_scope="vc=recruitment",
        export_scope="single_candidate",
        contains_class3=True,
        bulk_operation=False,
        response_mode="inline_json",
    )
    assert p["event_type"] == EVENT_EXPORT_GENERATED
    assert p["entity_type"] == "candidate"
    assert p["extra"]["export_type"] == "candidate_documents_json"
    assert p["extra"]["row_count"] == 3
    assert p["extra"]["byte_size"] == 1200
    assert p["extra"]["export_scope"] == "single_candidate"
    assert p["extra"]["contains_class3"] is True
    assert p["extra"]["bulk_operation"] is False
    assert "url" not in p["extra"]


def test_export_extra_allowlist_closed() -> None:
    assert "rows" not in EXPORT_EVENT_EXTRA_ALLOWLIST
    assert "filename" not in EXPORT_EVENT_EXTRA_ALLOWLIST


def test_redaction_strips_export_leak_keys() -> None:
    out = redact_and_size_extra(
        {
            "export_type": "x",
            "rows": [{"name": "secret"}],
            "archive_path": "/tmp/evil.zip",
        },
        allowlist=frozenset({"export_type", "rows", "archive_path"}),
    )
    assert out["export_type"] == "x"
    assert out["rows"] == "[REDACTED]"
    assert out["archive_path"] == "[REDACTED]"
