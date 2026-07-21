"""Pure data contracts for the C2.2 Rule Evaluator (no ORM / I/O)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

OUTCOME_FIRE = "fire"
OUTCOME_SKIP = "skip"

SEVERITY_ERROR = "error"
SEVERITY_WARNING = "warning"
SEVERITY_INFO = "info"

DIAG_RULE_NOT_PUBLISHED = "rule_not_published"
DIAG_RULE_ARCHIVED = "rule_archived"
DIAG_RULE_DISABLED = "rule_disabled"
DIAG_TRIGGER_MISMATCH = "trigger_mismatch"
DIAG_TRIGGER_FILTER_MISMATCH = "trigger_filter_mismatch"
DIAG_CONDITIONS_UNMATCHED = "conditions_unmatched"
DIAG_INVALID_CONDITIONS = "invalid_conditions"
DIAG_INTENT_KEY_MISSING = "intent_key_missing"
DIAG_INVALID_EVENT = "invalid_event"

CONDITION_OPS = frozenset(
    {
        "eq",
        "neq",
        "in",
        "not_in",
        "exists",
        "and",
        "or",
        "not",
        "gt",
        "gte",
        "lt",
        "lte",
        "contains",
    }
)


@dataclass(frozen=True, slots=True)
class TriggerSpec:
    event_type: str
    event_filter: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class RuleVersionPayload:
    """Immutable snapshot of a published (or draft) rule version — loaded by caller."""

    rule_id: str
    rule_version_id: str
    version_status: str  # draft | published
    rule_status: str  # active | archived
    enabled: bool
    intent_key: str
    preferred_template_key: str | None
    channel: str | None
    recipient_strategy: str
    recipient_config: Mapping[str, Any]
    conditions: Mapping[str, Any]
    variables_mapping: Mapping[str, Any]
    triggers: tuple[TriggerSpec, ...]
    meta: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class EventPayload:
    """Normalized event input for evaluation (no bus / ORM)."""

    event_id: str
    event_type: str
    data: Mapping[str, Any]
    correlation_id: str | None = None


@dataclass(frozen=True, slots=True)
class PolicyContext:
    """Caller-supplied snapshot — evaluator never loads tenant/policy from DB."""

    # Reserved for future Intent Policy / consent flags (PR-3 emitter uses them).
    extras: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class Diagnostic:
    code: str
    severity: str
    message: str
    path: str | None = None
    details: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "severity": self.severity,
            "message": self.message,
            "path": self.path,
            "details": dict(self.details or {}),
        }


@dataclass(frozen=True, slots=True)
class EvaluationResult:
    ok: bool
    outcome: str  # fire | skip
    rule_id: str
    rule_version_id: str
    source_event_id: str
    event_type: str
    intent_key: str | None
    preferred_template_key: str | None
    channel: str | None
    recipient_strategy: str | None
    recipient_config: Mapping[str, Any]
    template_variables: Mapping[str, Any]
    matched_trigger_event_type: str | None
    reason_codes: tuple[str, ...]
    diagnostics: tuple[Diagnostic, ...]
    correlation_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "outcome": self.outcome,
            "rule_id": self.rule_id,
            "rule_version_id": self.rule_version_id,
            "source_event_id": self.source_event_id,
            "event_type": self.event_type,
            "intent_key": self.intent_key,
            "preferred_template_key": self.preferred_template_key,
            "channel": self.channel,
            "recipient_strategy": self.recipient_strategy,
            "recipient_config": dict(self.recipient_config or {}),
            "template_variables": dict(self.template_variables or {}),
            "matched_trigger_event_type": self.matched_trigger_event_type,
            "reason_codes": list(self.reason_codes),
            "diagnostics": [d.to_dict() for d in self.diagnostics],
            "correlation_id": self.correlation_id,
        }


__all__ = [
    "OUTCOME_FIRE",
    "OUTCOME_SKIP",
    "SEVERITY_ERROR",
    "SEVERITY_WARNING",
    "SEVERITY_INFO",
    "DIAG_RULE_NOT_PUBLISHED",
    "DIAG_RULE_ARCHIVED",
    "DIAG_RULE_DISABLED",
    "DIAG_TRIGGER_MISMATCH",
    "DIAG_TRIGGER_FILTER_MISMATCH",
    "DIAG_CONDITIONS_UNMATCHED",
    "DIAG_INVALID_CONDITIONS",
    "DIAG_INTENT_KEY_MISSING",
    "DIAG_INVALID_EVENT",
    "CONDITION_OPS",
    "TriggerSpec",
    "RuleVersionPayload",
    "EventPayload",
    "PolicyContext",
    "Diagnostic",
    "EvaluationResult",
]
