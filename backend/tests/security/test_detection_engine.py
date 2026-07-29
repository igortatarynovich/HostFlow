"""Phase 7 detection engine unit tests."""

from __future__ import annotations

from backend.app.security.detection_engine import (
    maybe_raise_detection_alerts,
    reset_burst_state_for_tests,
    should_raise_alert,
)
from backend.app.security.detection_rules import DETECTION_RULES, rules_for_event_type
from backend.app.security.event_taxonomy import (
    EVENT_DETECTION_ALERT_RAISED,
    EVENT_EXPORT_ANOMALY_DETECTED,
    EVENT_SEARCH_RETRIEVAL_DENIED,
    validate_event_type,
)


def test_detection_alert_event_type_validates() -> None:
    assert validate_event_type(EVENT_DETECTION_ALERT_RAISED) == EVENT_DETECTION_ALERT_RAISED


def test_every_rule_has_owner_and_runbook() -> None:
    assert DETECTION_RULES
    for rule in DETECTION_RULES:
        assert rule.owner.strip()
        assert rule.runbook_path.startswith("docs/security/")
        assert rule.rule_id.strip()


def test_export_anomaly_rule_fires_immediately() -> None:
    rules = rules_for_event_type(EVENT_EXPORT_ANOMALY_DETECTED)
    assert len(rules) == 1
    payload = {
        "event_type": EVENT_EXPORT_ANOMALY_DETECTED,
        "tenant_id": "t1",
        "actor_id": "a1",
    }
    assert should_raise_alert(rules[0], payload) is True


def test_retrieval_denied_burst_threshold(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    reset_burst_state_for_tests()
    rules = rules_for_event_type(EVENT_SEARCH_RETRIEVAL_DENIED)
    rule = rules[0]
    assert rule.burst_threshold == 5
    payload = {
        "event_type": EVENT_SEARCH_RETRIEVAL_DENIED,
        "tenant_id": "t-burst",
        "actor_id": "u-burst",
    }
    now = 1_700_000_000.0
    for i in range(4):
        assert should_raise_alert(rule, payload, now=now + i) is False
    assert should_raise_alert(rule, payload, now=now + 4) is True


def test_maybe_raise_skips_detection_events(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    called = {"n": 0}

    def _boom(**_k):  # type: ignore[no-untyped-def]
        called["n"] += 1
        raise AssertionError("should not emit")

    monkeypatch.setattr(
        "backend.app.security.detection_alerts.emit_detection_alert_v1",
        _boom,
    )
    out = maybe_raise_detection_alerts(
        {"event_type": EVENT_DETECTION_ALERT_RAISED, "tenant_id": "t"}
    )
    assert out == []
    assert called["n"] == 0


def test_maybe_raise_on_export_anomaly(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    reset_burst_state_for_tests()
    seen: list[str] = []

    def _capture(*, rule, trigger):  # type: ignore[no-untyped-def]
        seen.append(rule.rule_id)
        return {"event_type": EVENT_DETECTION_ALERT_RAISED, "rule": rule.rule_id}

    monkeypatch.setattr(
        "backend.app.security.detection_alerts.emit_detection_alert_v1",
        _capture,
    )
    raised = maybe_raise_detection_alerts(
        {
            "event_type": EVENT_EXPORT_ANOMALY_DETECTED,
            "event_id": "e1",
            "tenant_id": "t1",
            "actor_id": "a1",
            "source": "test",
            "extra": {"anomaly_codes": "row_count_threshold"},
        }
    )
    assert seen == ["export_anomaly_v1"]
    assert len(raised) == 1
