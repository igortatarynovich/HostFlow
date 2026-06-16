"""Outcome Rules Foundation (PR-5)."""

from backend.app.modules.outcome_rules.reference import (
    OUTCOME_EVENTS,
    OUTCOME_RULE_TYPES,
    ROUTE_INTENT_OUTCOME_RULES,
    OutcomeEvent,
    OutcomeRuleType,
    normalize_outcome_event,
    normalize_outcome_rule_type,
    outcome_reference_catalog,
)

__all__ = [
    "OUTCOME_EVENTS",
    "OUTCOME_RULE_TYPES",
    "ROUTE_INTENT_OUTCOME_RULES",
    "OutcomeEvent",
    "OutcomeRuleType",
    "normalize_outcome_event",
    "normalize_outcome_rule_type",
    "outcome_reference_catalog",
]
