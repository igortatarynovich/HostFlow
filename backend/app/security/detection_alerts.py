"""Phase 7 alert emission + optional webhook sink."""

from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request
from typing import Any

from backend.app.security.canonical_emit import emit_security_event_v1
from backend.app.security.detection_rules import DetectionRule
from backend.app.security.event_taxonomy import EVENT_DETECTION_ALERT_RAISED

logger = logging.getLogger("hostflow.security.detection")

DETECTION_ALERT_EXTRA_ALLOWLIST = frozenset(
    {
        "rule_id",
        "rule_title",
        "owner",
        "runbook_path",
        "trigger_event_type",
        "trigger_event_id",
        "trigger_source",
        "anomaly_codes",
        "reason",
    }
)


def _webhook_url() -> str | None:
    # Prefer settings when importable; fall back to env for early boot / tests.
    try:
        from backend.app.core.settings import settings

        url = getattr(settings, "security_alert_webhook_url", None)
        if url and str(url).strip():
            return str(url).strip()
    except Exception:
        pass
    raw = (os.environ.get("SECURITY_ALERT_WEBHOOK_URL") or "").strip()
    return raw or None


def _post_webhook(url: str, body: dict[str, Any], *, timeout_sec: float = 2.0) -> None:
    data = json.dumps(body, default=str).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            _ = resp.read(256)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        logger.warning("security alert webhook failed: %s", exc)


def emit_detection_alert_v1(*, rule: DetectionRule, trigger: dict[str, Any]) -> dict[str, Any]:
    """Emit ``detection.alert.raised`` and optionally POST a compact webhook payload."""
    extra: dict[str, Any] = {
        "rule_id": rule.rule_id,
        "rule_title": rule.title[:128],
        "owner": rule.owner[:64],
        "runbook_path": rule.runbook_path[:256],
        "trigger_event_type": str(trigger.get("event_type") or "")[:128],
        "trigger_event_id": str(trigger.get("event_id") or "")[:64],
        "trigger_source": str(trigger.get("source") or "")[:256],
    }
    trig_extra = trigger.get("extra") if isinstance(trigger.get("extra"), dict) else {}
    if trig_extra.get("anomaly_codes") is not None:
        extra["anomaly_codes"] = str(trig_extra.get("anomaly_codes"))[:256]
    if trig_extra.get("reason") is not None:
        extra["reason"] = str(trig_extra.get("reason"))[:256]

    payload = emit_security_event_v1(
        event_type=EVENT_DETECTION_ALERT_RAISED,
        result="success",
        severity=rule.severity,
        source=f"detection:{rule.rule_id}",
        tenant_id=trigger.get("tenant_id"),  # type: ignore[arg-type]
        actor_id=trigger.get("actor_id"),  # type: ignore[arg-type]
        correlation_id=trigger.get("correlation_id"),  # type: ignore[arg-type]
        access_kind=trigger.get("access_kind"),  # type: ignore[arg-type]
        entity_type=trigger.get("entity_type"),  # type: ignore[arg-type]
        entity_id=trigger.get("entity_id"),  # type: ignore[arg-type]
        action=EVENT_DETECTION_ALERT_RAISED,
        extra=extra,
        extra_allowlist=DETECTION_ALERT_EXTRA_ALLOWLIST,
    )

    url = _webhook_url()
    if url:
        _post_webhook(
            url,
            {
                "text": (
                    f"[HostFlow security] {rule.title} "
                    f"(rule={rule.rule_id} tenant={trigger.get('tenant_id')} "
                    f"trigger={trigger.get('event_type')}) "
                    f"runbook={rule.runbook_path}"
                ),
                "rule_id": rule.rule_id,
                "severity": rule.severity,
                "tenant_id": trigger.get("tenant_id"),
                "trigger_event_type": trigger.get("event_type"),
                "correlation_id": trigger.get("correlation_id"),
                "runbook_path": rule.runbook_path,
            },
        )
    return payload


__all__ = [
    "DETECTION_ALERT_EXTRA_ALLOWLIST",
    "emit_detection_alert_v1",
]
