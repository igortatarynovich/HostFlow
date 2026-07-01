"""Canonical reference values for outcome rules (PR-5)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from backend.app.models.intake_routing_enums import RouteIntent
from backend.app.modules.intake_routing.reference import normalize_route_intent


class OutcomeRuleType(str, Enum):
    create_candidate = "create_candidate"
    create_client = "create_client"
    create_service_order = "create_service_order"
    create_partner = "create_partner"
    review_queue = "review_queue"
    none = "none"
    unknown = "unknown"


class OutcomeEvent(str, Enum):
    ingest = "ingest"
    qualified = "qualified"
    won = "won"
    unknown = "unknown"


OUTCOME_RULE_TYPES: frozenset[str] = frozenset(t.value for t in OutcomeRuleType)
OUTCOME_EVENTS: frozenset[str] = frozenset(e.value for e in OutcomeEvent)

OUTCOME_RULE_TYPE_MEANINGS: dict[str, str] = {
    OutcomeRuleType.create_candidate.value: "create candidate",
    OutcomeRuleType.create_client.value: "create client",
    OutcomeRuleType.create_service_order.value: "create service order",
    OutcomeRuleType.create_partner.value: "create partner",
    OutcomeRuleType.review_queue.value: "send to manual review",
    OutcomeRuleType.none.value: "create no derivative entity",
    OutcomeRuleType.unknown.value: "unknown outcome action",
}


@dataclass(frozen=True)
class RouteIntentOutcomeRule:
    route_intent: str
    event: str
    outcome: str


ROUTE_INTENT_OUTCOME_RULES: tuple[RouteIntentOutcomeRule, ...] = (
    RouteIntentOutcomeRule(
        route_intent=RouteIntent.candidate_application.value,
        event=OutcomeEvent.ingest.value,
        outcome=OutcomeRuleType.create_candidate.value,
    ),
    RouteIntentOutcomeRule(
        route_intent=RouteIntent.sales_inquiry.value,
        event=OutcomeEvent.ingest.value,
        outcome=OutcomeRuleType.none.value,
    ),
    RouteIntentOutcomeRule(
        route_intent=RouteIntent.service_request.value,
        event=OutcomeEvent.qualified.value,
        outcome=OutcomeRuleType.create_service_order.value,
    ),
    RouteIntentOutcomeRule(
        route_intent=RouteIntent.sales_inquiry.value,
        event=OutcomeEvent.won.value,
        outcome=OutcomeRuleType.create_client.value,
    ),
    RouteIntentOutcomeRule(
        route_intent=RouteIntent.partner_inquiry.value,
        event=OutcomeEvent.qualified.value,
        outcome=OutcomeRuleType.create_partner.value,
    ),
    RouteIntentOutcomeRule(
        route_intent=RouteIntent.unknown.value,
        event=OutcomeEvent.ingest.value,
        outcome=OutcomeRuleType.review_queue.value,
    ),
)


def normalize_outcome_rule_type(raw: Any) -> str:
    value = str(raw or "").strip().lower()
    if value in OUTCOME_RULE_TYPES:
        return value
    return OutcomeRuleType.unknown.value


def normalize_outcome_event(raw: Any) -> str:
    value = str(raw or "").strip().lower()
    if value in OUTCOME_EVENTS:
        return value
    return OutcomeEvent.unknown.value


def find_route_intent_outcome_rules(route_intent: Any, event: Any) -> tuple[RouteIntentOutcomeRule, ...]:
    normalized_intent = normalize_route_intent(route_intent)
    normalized_event = normalize_outcome_event(event)
    if normalized_intent == RouteIntent.unknown.value or normalized_event == OutcomeEvent.unknown.value:
        return ()
    return tuple(
        rule
        for rule in ROUTE_INTENT_OUTCOME_RULES
        if rule.route_intent == normalized_intent and rule.event == normalized_event
    )


def outcome_reference_catalog() -> dict[str, object]:
    return {
        "outcome_rule_types": OUTCOME_RULE_TYPES,
        "outcome_events": OUTCOME_EVENTS,
        "outcome_rule_type_meanings": dict(OUTCOME_RULE_TYPE_MEANINGS),
        "route_intent_outcome_rules": tuple(ROUTE_INTENT_OUTCOME_RULES),
    }
