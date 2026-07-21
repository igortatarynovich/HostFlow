"""Stage 3E Event Catalog — closed types with **per-event** versions.

There is **no** global ``catalog_version``. Each ``ActivityEventContract`` carries
its own ``event_version`` so ``FlightStarted`` can stay at ``\"1\"`` while
``BudgetChanged`` independently moves to ``\"2\"``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from backend.app.acquisition.activity.payloads import (
    PAYLOAD_VALIDATORS_V1,
    PayloadValidator,
)


@dataclass(frozen=True)
class ActivityEventContract:
    event_type: str
    """Closed catalog type name (e.g. ``FlightStarted``)."""

    event_version: str
    """Version of **this** event type's payload/envelope contract only."""

    zone: str
    validate_payload: PayloadValidator


def _contract(event_type: str, *, zone: str, version: str = "1") -> ActivityEventContract:
    validator = PAYLOAD_VALIDATORS_V1.get(event_type)
    if validator is None:
        raise RuntimeError(f"missing payload validator for catalog type {event_type!r}")
    return ActivityEventContract(
        event_type=event_type,
        event_version=version,
        zone=zone,
        validate_payload=validator,
    )


# Catalog membership is additive-only. Per-type versions may diverge over time.
_CATALOG: tuple[ActivityEventContract, ...] = (
    # Campaign
    _contract("CampaignCreated", zone="campaign"),
    _contract("CampaignActivated", zone="campaign"),
    _contract("CampaignPaused", zone="campaign"),
    _contract("CampaignCompleted", zone="campaign"),
    # Flight
    _contract("FlightCreated", zone="flight"),
    _contract("FlightStarted", zone="flight"),
    _contract("FlightPaused", zone="flight"),
    _contract("FlightResumed", zone="flight"),
    _contract("FlightCompleted", zone="flight"),
    _contract("FlightFailed", zone="flight"),
    # Configuration
    _contract("BudgetChanged", zone="configuration"),
    _contract("AudienceChanged", zone="configuration"),
    _contract("EndpointChanged", zone="configuration"),
    # Provider lifecycle
    _contract("ProviderSubmissionAccepted", zone="provider"),
    _contract("ProviderSubmissionRejected", zone="provider"),
    _contract("ProviderStatusChanged", zone="provider"),
    _contract("LearningPhaseEntered", zone="provider"),
    _contract("LearningPhaseExited", zone="provider"),
    # Intake pipeline
    _contract("SubmissionReceived", zone="intake"),
    _contract("SubmissionNormalized", zone="intake"),
    _contract("SubmissionRejected", zone="intake"),
    _contract("RoutingCompleted", zone="intake"),
    _contract("RoutingFailed", zone="intake"),
    _contract("ResultAttributed", zone="intake"),
    _contract("OutcomeChanged", zone="intake"),
    # Business entity signals (typed refs in payload — no ORM ownership)
    _contract("LeadCreated", zone="business_entities"),
    _contract("CandidateCreated", zone="business_entities"),
    _contract("DuplicateDetected", zone="business_entities"),
    # Automation / monitoring
    _contract("FlightAutoPaused", zone="automation_monitoring"),
    _contract("FlightAutoResumed", zone="automation_monitoring"),
    _contract("SpendAnomalyDetected", zone="automation_monitoring"),
    _contract("DeliveryErrorOccurred", zone="automation_monitoring"),
)

ACTIVITY_EVENT_CATALOG: Mapping[str, ActivityEventContract] = {
    c.event_type: c for c in _CATALOG
}

ACTIVITY_EVENT_TYPES: frozenset[str] = frozenset(ACTIVITY_EVENT_CATALOG.keys())


def get_activity_event_contract(event_type: str) -> ActivityEventContract | None:
    return ACTIVITY_EVENT_CATALOG.get(event_type)


__all__ = [
    "ActivityEventContract",
    "ACTIVITY_EVENT_CATALOG",
    "ACTIVITY_EVENT_TYPES",
    "get_activity_event_contract",
]
