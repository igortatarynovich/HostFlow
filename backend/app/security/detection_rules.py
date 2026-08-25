"""Phase 7 detection rules — owners, thresholds, runbook links (SSOT-aligned)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class DetectionRule:
    """One detection rule. Alerts without a runbook path are forbidden in this registry."""

    rule_id: str
    owner: str
    title: str
    trigger_event_types: frozenset[str]
    severity: str
    runbook_path: str
    # Optional burst: count of matching events per key within window_sec.
    burst_threshold: int | None = None
    burst_window_sec: int | None = None
    # Key template fields from payload: tenant_id|actor_id|event_type
    burst_key_fields: tuple[str, ...] = ("tenant_id", "actor_id")


DETECTION_RUNBOOK = "docs/security/detection-runbooks.md"

DETECTION_RULES: tuple[DetectionRule, ...] = (
    DetectionRule(
        rule_id="export_anomaly_v1",
        owner="security-champion",
        title="Export anomaly threshold exceeded",
        trigger_event_types=frozenset({"export.anomaly.detected"}),
        severity="medium",
        runbook_path=DETECTION_RUNBOOK,
    ),
    DetectionRule(
        rule_id="retrieval_denied_burst_v1",
        owner="security-champion",
        title="Burst of search retrieval denials",
        trigger_event_types=frozenset({"search.retrieval.denied"}),
        severity="medium",
        runbook_path=DETECTION_RUNBOOK,
        burst_threshold=5,
        burst_window_sec=600,
        burst_key_fields=("tenant_id", "actor_id"),
    ),
    DetectionRule(
        rule_id="document_signed_url_denied_burst_v1",
        owner="security-champion",
        title="Burst of signed URL denials",
        trigger_event_types=frozenset({"document.signed_url.denied"}),
        severity="medium",
        runbook_path=DETECTION_RUNBOOK,
        burst_threshold=10,
        burst_window_sec=600,
        burst_key_fields=("tenant_id", "actor_id"),
    ),
)


def rules_for_event_type(event_type: str) -> list[DetectionRule]:
    et = (event_type or "").strip().lower()
    return [r for r in DETECTION_RULES if et in r.trigger_event_types]


def burst_key(rule: DetectionRule, payload: dict[str, Any]) -> str:
    parts = [rule.rule_id]
    for field in rule.burst_key_fields:
        parts.append(str(payload.get(field) or "-"))
    return "|".join(parts)


__all__ = [
    "DETECTION_RULES",
    "DETECTION_RUNBOOK",
    "DetectionRule",
    "burst_key",
    "rules_for_event_type",
]
