"""OutcomeResolver — pure outcome action resolution (PR-5)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from backend.app.models.intake_routing_enums import RouteIntent
from backend.app.modules.intake_routing.reference import normalize_route_intent
from backend.app.modules.outcome_rules.reference import (
    OutcomeEvent,
    OutcomeRuleType,
    find_route_intent_outcome_rules,
    normalize_outcome_event,
)


@dataclass(frozen=True)
class OutcomeAction:
    code: str
    route_intent: str
    event: str

    def to_dict(self) -> dict[str, str]:
        return {
            "code": self.code,
            "route_intent": self.route_intent,
            "event": self.event,
        }


@dataclass(frozen=True)
class OutcomeResolution:
    actions: tuple[OutcomeAction, ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)
    blocking_reasons: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, list[dict[str, str]] | list[str]]:
        return {
            "actions": [action.to_dict() for action in self.actions],
            "warnings": list(self.warnings),
            "blocking_reasons": list(self.blocking_reasons),
        }


class OutcomeResolver:
    """Resolve configured outcome actions without creating derivative entities."""

    @staticmethod
    def resolve(route_intent: Any, event: Any) -> OutcomeResolution:
        normalized_intent = normalize_route_intent(route_intent)
        normalized_event = normalize_outcome_event(event)
        warnings: list[str] = []
        blocking_reasons: list[str] = []

        if normalized_intent == RouteIntent.unknown.value:
            blocking_reasons.append("unknown_route_intent")
        if normalized_event == OutcomeEvent.unknown.value:
            blocking_reasons.append("unknown_outcome_event")
        if blocking_reasons:
            return OutcomeResolution(
                warnings=tuple(warnings),
                blocking_reasons=tuple(blocking_reasons),
            )

        rules = find_route_intent_outcome_rules(normalized_intent, normalized_event)
        if not rules:
            warnings.append("no_outcome_rule")
            return OutcomeResolution(
                actions=(
                    OutcomeAction(
                        code=OutcomeRuleType.review_queue.value,
                        route_intent=normalized_intent,
                        event=normalized_event,
                    ),
                ),
                warnings=tuple(warnings),
            )

        actions = tuple(
            OutcomeAction(
                code=rule.outcome,
                route_intent=normalized_intent,
                event=normalized_event,
            )
            for rule in rules
        )
        return OutcomeResolution(actions=actions)


def resolve_outcomes(route_intent: Any, event: Any) -> OutcomeResolution:
    return OutcomeResolver.resolve(route_intent, event)


__all__ = [
    "OutcomeAction",
    "OutcomeResolution",
    "OutcomeResolver",
    "resolve_outcomes",
]
