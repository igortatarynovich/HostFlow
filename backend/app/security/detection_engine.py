"""Phase 7 detection engine — evaluate rules against canonical security events."""

from __future__ import annotations

import logging
import threading
import time
from collections import defaultdict, deque
from typing import Any

from backend.app.security.detection_rules import DetectionRule, burst_key, rules_for_event_type

logger = logging.getLogger("hostflow.security.detection")

# Process-local burst windows (v1). Multi-replica deployments need shared store later.
_burst_lock = threading.Lock()
_burst_events: dict[str, deque[float]] = defaultdict(deque)


def _record_burst(rule: DetectionRule, payload: dict[str, Any], *, now: float | None = None) -> int:
    """Append timestamp for burst key; return count inside window. 1 if no burst config."""
    if not rule.burst_threshold or not rule.burst_window_sec:
        return 1
    ts = float(now if now is not None else time.time())
    key = burst_key(rule, payload)
    window = float(rule.burst_window_sec)
    with _burst_lock:
        dq = _burst_events[key]
        dq.append(ts)
        cutoff = ts - window
        while dq and dq[0] < cutoff:
            dq.popleft()
        return len(dq)


def reset_burst_state_for_tests() -> None:
    with _burst_lock:
        _burst_events.clear()


def should_raise_alert(rule: DetectionRule, payload: dict[str, Any], *, now: float | None = None) -> bool:
    """Return True when this rule fires for the given canonical event payload."""
    et = str(payload.get("event_type") or "").strip().lower()
    if et not in rule.trigger_event_types:
        return False
    if not rule.burst_threshold or not rule.burst_window_sec:
        return True
    count = _record_burst(rule, payload, now=now)
    return count >= int(rule.burst_threshold)


def maybe_raise_detection_alerts(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Evaluate rules for ``payload``; emit ``detection.alert.raised`` when triggered.

    Skips ``detection.*`` events to avoid recursion. Failures are logged, never raised
    to producers (telemetry must not break CRM paths).
    """
    try:
        et = str(payload.get("event_type") or "").strip().lower()
        if not et or et.startswith("detection."):
            return []
        raised: list[dict[str, Any]] = []
        for rule in rules_for_event_type(et):
            if not should_raise_alert(rule, payload):
                continue
            from backend.app.security.detection_alerts import emit_detection_alert_v1

            alert = emit_detection_alert_v1(rule=rule, trigger=payload)
            raised.append(alert)
        return raised
    except Exception:
        logger.exception("maybe_raise_detection_alerts failed")
        return []


__all__ = [
    "maybe_raise_detection_alerts",
    "reset_burst_state_for_tests",
    "should_raise_alert",
]
