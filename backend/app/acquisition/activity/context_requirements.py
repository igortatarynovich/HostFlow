"""Row-level semantic requirements for Activity events (not payload fields).

Envelope fields (``flight_id``, ``occurred_at``, …) live on ``AcquisitionActivityEvent``
columns. Payload validators own only the typed ``payload`` object.
"""

from __future__ import annotations

from backend.app.acquisition.activity.errors import InvalidActivityPayload

# Flight-zone events must be anchored to a Flight row reference.
REQUIRES_FLIGHT_ID: frozenset[str] = frozenset(
    {
        "FlightCreated",
        "FlightStarted",
        "FlightPaused",
        "FlightResumed",
        "FlightCompleted",
        "FlightFailed",
        "FlightAutoPaused",
        "FlightAutoResumed",
        "BudgetChanged",
        "AudienceChanged",
        "LearningPhaseEntered",
        "LearningPhaseExited",
        "SpendAnomalyDetected",
    }
)

REQUIRES_ENDPOINT_ID_ON_ROW: frozenset[str] = frozenset(
    {
        "EndpointChanged",
    }
)

REQUIRES_SUBMISSION_ID: frozenset[str] = frozenset(
    {
        "SubmissionReceived",
        "SubmissionNormalized",
        "SubmissionRejected",
        "ProviderSubmissionAccepted",
        "ProviderSubmissionRejected",
    }
)


def validate_event_context(
    *,
    event_type: str,
    flight_id: str | None,
    endpoint_id: str | None,
    submission_id: str | None,
) -> None:
    if event_type in REQUIRES_FLIGHT_ID and not (flight_id and str(flight_id).strip()):
        raise InvalidActivityPayload(
            event_type, "flight_id is required on the event envelope for this type"
        )
    if event_type in REQUIRES_ENDPOINT_ID_ON_ROW and not (
        endpoint_id and str(endpoint_id).strip()
    ):
        raise InvalidActivityPayload(
            event_type, "endpoint_id is required on the event envelope for this type"
        )
    if event_type in REQUIRES_SUBMISSION_ID and not (
        submission_id and str(submission_id).strip()
    ):
        raise InvalidActivityPayload(
            event_type, "submission_id is required on the event envelope for this type"
        )


__all__ = [
    "REQUIRES_FLIGHT_ID",
    "REQUIRES_ENDPOINT_ID_ON_ROW",
    "REQUIRES_SUBMISSION_ID",
    "validate_event_context",
]
