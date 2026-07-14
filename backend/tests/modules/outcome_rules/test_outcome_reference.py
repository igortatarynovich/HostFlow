"""Outcome Rules reference catalog (PR-5)."""

from __future__ import annotations

from backend.app.models.intake_routing_enums import RouteIntent
from backend.app.modules.outcome_rules.reference import (
    OUTCOME_EVENTS,
    OUTCOME_RULE_TYPES,
    OutcomeEvent,
    OutcomeRuleType,
    find_route_intent_outcome_rules,
    normalize_outcome_event,
    normalize_outcome_rule_type,
    outcome_reference_catalog,
)


def test_outcome_reference_catalog_contains_rule_types_and_events() -> None:
    catalog = outcome_reference_catalog()

    assert catalog["outcome_rule_types"] == OUTCOME_RULE_TYPES
    assert catalog["outcome_events"] == OUTCOME_EVENTS
    assert OutcomeRuleType.create_candidate.value in catalog["outcome_rule_types"]
    assert OutcomeRuleType.create_client.value in catalog["outcome_rule_types"]
    assert OutcomeRuleType.create_service_order.value in catalog["outcome_rule_types"]
    assert OutcomeRuleType.create_partner.value in catalog["outcome_rule_types"]
    assert OutcomeRuleType.review_queue.value in catalog["outcome_rule_types"]
    assert OutcomeRuleType.none.value in catalog["outcome_rule_types"]


def test_normalizers_reject_unknown_values() -> None:
    assert normalize_outcome_rule_type("CREATE_CANDIDATE") == OutcomeRuleType.create_candidate.value
    assert normalize_outcome_rule_type("bad") == OutcomeRuleType.unknown.value
    assert normalize_outcome_event("INGEST") == OutcomeEvent.ingest.value
    assert normalize_outcome_event("bad") == OutcomeEvent.unknown.value


def test_route_intent_outcome_mapping_contains_pr5_baseline() -> None:
    candidate_ingest = find_route_intent_outcome_rules(
        RouteIntent.candidate_application.value,
        OutcomeEvent.ingest.value,
    )
    sales_ingest = find_route_intent_outcome_rules(
        RouteIntent.sales_inquiry.value,
        OutcomeEvent.ingest.value,
    )
    service_qualified = find_route_intent_outcome_rules(
        RouteIntent.service_request.value,
        OutcomeEvent.qualified.value,
    )
    sales_won = find_route_intent_outcome_rules(
        RouteIntent.sales_inquiry.value,
        OutcomeEvent.won.value,
    )

    assert [rule.outcome for rule in candidate_ingest] == [OutcomeRuleType.create_candidate.value]
    assert [rule.outcome for rule in sales_ingest] == [OutcomeRuleType.none.value]
    assert [rule.outcome for rule in service_qualified] == [
        OutcomeRuleType.create_service_order.value
    ]
    assert [rule.outcome for rule in sales_won] == [OutcomeRuleType.create_client.value]
