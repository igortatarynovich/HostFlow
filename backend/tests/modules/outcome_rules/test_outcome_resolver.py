"""OutcomeResolver pure behavior (PR-5)."""

from __future__ import annotations

from backend.app.models.intake_routing_enums import RouteIntent
from backend.app.modules.outcome_rules.reference import OutcomeEvent, OutcomeRuleType
from backend.app.services.outcome_resolver import resolve_outcomes


def _action_codes(route_intent: str, event: str) -> list[str]:
    return [action.code for action in resolve_outcomes(route_intent, event).actions]


def test_resolve_candidate_application_ingest_creates_candidate_action_only() -> None:
    result = resolve_outcomes(RouteIntent.candidate_application.value, OutcomeEvent.ingest.value)

    assert _action_codes(RouteIntent.candidate_application.value, OutcomeEvent.ingest.value) == [
        OutcomeRuleType.create_candidate.value
    ]
    assert result.warnings == ()
    assert result.blocking_reasons == ()


def test_resolve_sales_inquiry_ingest_creates_no_derivative_entity() -> None:
    result = resolve_outcomes(RouteIntent.sales_inquiry.value, OutcomeEvent.ingest.value)

    assert [action.code for action in result.actions] == [OutcomeRuleType.none.value]
    assert result.warnings == ()
    assert result.blocking_reasons == ()


def test_resolve_lifecycle_outcomes_without_creating_entities() -> None:
    assert _action_codes(RouteIntent.service_request.value, OutcomeEvent.qualified.value) == [
        OutcomeRuleType.create_service_order.value
    ]
    assert _action_codes(RouteIntent.sales_inquiry.value, OutcomeEvent.won.value) == [
        OutcomeRuleType.create_client.value
    ]
    assert _action_codes(RouteIntent.partner_inquiry.value, OutcomeEvent.qualified.value) == [
        OutcomeRuleType.create_partner.value
    ]


def test_no_rule_falls_back_to_review_queue_warning() -> None:
    result = resolve_outcomes(RouteIntent.service_request.value, OutcomeEvent.ingest.value)

    assert [action.code for action in result.actions] == [OutcomeRuleType.review_queue.value]
    assert result.warnings == ("no_outcome_rule",)
    assert result.blocking_reasons == ()


def test_unknown_inputs_block_resolution() -> None:
    result = resolve_outcomes("bad_intent", "bad_event")

    assert result.actions == ()
    assert result.warnings == ()
    assert result.blocking_reasons == ("unknown_route_intent", "unknown_outcome_event")
