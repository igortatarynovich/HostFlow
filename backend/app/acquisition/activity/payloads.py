"""Per-event-type versioned payload contracts (Catalog v0).

Versions are **per ``event_type``** (e.g. ``FlightStarted`` v1, ``BudgetChanged`` v2),
not a single catalog-wide version. Payload validation is semantic: required keys,
closed allowlists, and type checks — not “any JSON object”.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping

from backend.app.acquisition.activity.errors import InvalidActivityPayload

PayloadValidator = Callable[[dict[str, Any]], None]


@dataclass(frozen=True)
class PayloadSchema:
    """Closed payload schema for one ``event_type`` @ one ``event_version``."""

    required: frozenset[str] = frozenset()
    optional: frozenset[str] = frozenset()
    # At least one key from each inner frozenset must be present.
    require_one_of: tuple[frozenset[str], ...] = ()

    @property
    def allowed(self) -> frozenset[str]:
        ones = frozenset().union(*self.require_one_of) if self.require_one_of else frozenset()
        return self.required | self.optional | ones


def _require_dict(payload: dict[str, Any], event_type: str) -> None:
    if not isinstance(payload, dict):
        raise InvalidActivityPayload(event_type, "payload must be an object")


def _require_str(payload: dict[str, Any], key: str, event_type: str) -> str:
    value = payload.get(key)
    if value is None or not isinstance(value, str) or not value.strip():
        raise InvalidActivityPayload(event_type, f"payload.{key} is required")
    return value.strip()


def _optional_str(payload: dict[str, Any], key: str, event_type: str) -> None:
    if key not in payload or payload[key] is None:
        return
    if not isinstance(payload[key], str) or not str(payload[key]).strip():
        raise InvalidActivityPayload(event_type, f"payload.{key} must be a non-empty string")


def _optional_number(payload: dict[str, Any], key: str, event_type: str) -> None:
    if key not in payload or payload[key] is None:
        return
    try:
        float(payload[key])
    except (TypeError, ValueError) as exc:
        raise InvalidActivityPayload(event_type, f"payload.{key} must be numeric") from exc


def _apply_schema(event_type: str, schema: PayloadSchema, payload: dict[str, Any]) -> None:
    _require_dict(payload, event_type)
    unknown = set(payload.keys()) - set(schema.allowed)
    if unknown:
        raise InvalidActivityPayload(
            event_type,
            f"unknown payload fields not allowed for this event: {sorted(unknown)}",
        )
    for key in schema.required:
        if key not in payload or payload[key] is None:
            raise InvalidActivityPayload(event_type, f"payload.{key} is required")
    for group in schema.require_one_of:
        if not any(payload.get(k) is not None for k in group):
            raise InvalidActivityPayload(
                event_type,
                f"one of payload fields required: {sorted(group)}",
            )


def _schema_validator(
    event_type: str,
    schema: PayloadSchema,
    *,
    str_keys: frozenset[str] | None = None,
    number_keys: frozenset[str] | None = None,
) -> PayloadValidator:
    str_keys = str_keys or frozenset()
    number_keys = number_keys or frozenset()

    def _validate(payload: dict[str, Any]) -> None:
        _apply_schema(event_type, schema, payload)
        for key in str_keys:
            if key in schema.required or (
                key in payload and payload[key] is not None
            ):
                if key in schema.required:
                    _require_str(payload, key, event_type)
                else:
                    _optional_str(payload, key, event_type)
        for key in number_keys:
            _optional_number(payload, key, event_type)

    return _validate


_EMPTY = PayloadSchema()
_NOTE = PayloadSchema(optional=frozenset({"note"}))
# Flight lifecycle transition facts (PR-2): status change only — no provider fields.
_FLIGHT_CREATED = PayloadSchema(
    required=frozenset({"new_status"}),
    optional=frozenset({"previous_status", "reason"}),
)
_FLIGHT_TRANSITION = PayloadSchema(
    required=frozenset({"previous_status", "new_status"}),
    optional=frozenset({"reason"}),
)

# Per-type payload schemas (event_version pairing lives in catalog.py).
_SCHEMAS: dict[str, PayloadSchema] = {
    "CampaignCreated": _NOTE,
    "CampaignActivated": _NOTE,
    "CampaignPaused": _NOTE,
    "CampaignCompleted": _NOTE,
    "FlightCreated": _FLIGHT_CREATED,
    "FlightStarted": _FLIGHT_TRANSITION,
    "FlightPaused": _FLIGHT_TRANSITION,
    "FlightResumed": _FLIGHT_TRANSITION,
    "FlightCompleted": _FLIGHT_TRANSITION,
    "FlightFailed": PayloadSchema(
        required=frozenset({"reason_code", "previous_status", "new_status"}),
        optional=frozenset({"reason", "note"}),
    ),
    "BudgetChanged": PayloadSchema(
        required=frozenset({"currency"}),
        optional=frozenset({"amount", "new_amount", "previous_amount", "note"}),
        require_one_of=(frozenset({"amount", "new_amount"}),),
    ),
    "AudienceChanged": PayloadSchema(
        required=frozenset({"audience_ref"}),
        optional=frozenset({"change_kind", "note"}),
    ),
    "EndpointChanged": PayloadSchema(
        required=frozenset({"endpoint_id"}),
        optional=frozenset({"change_kind", "note"}),
    ),
    "ProviderSubmissionAccepted": PayloadSchema(
        optional=frozenset({"external_submission_id", "reason_code", "note"}),
    ),
    "ProviderSubmissionRejected": PayloadSchema(
        optional=frozenset({"external_submission_id", "reason_code", "note"}),
    ),
    "ProviderStatusChanged": PayloadSchema(
        required=frozenset({"status"}),
        optional=frozenset({"previous_status", "note"}),
    ),
    "LearningPhaseEntered": _NOTE,
    "LearningPhaseExited": _NOTE,
    "SubmissionReceived": PayloadSchema(
        optional=frozenset({"reason_code", "normalized_schema_version", "note"}),
    ),
    "SubmissionNormalized": PayloadSchema(
        optional=frozenset({"reason_code", "normalized_schema_version", "note"}),
    ),
    "SubmissionRejected": PayloadSchema(
        optional=frozenset({"reason_code", "normalized_schema_version", "note"}),
    ),
    "RoutingCompleted": PayloadSchema(
        optional=frozenset(
            {
                "route_intent",
                "routing_source",
                "campaign_target_id",
                "target_type",
                "reason_code",
                "note",
            }
        ),
    ),
    "RoutingFailed": PayloadSchema(
        optional=frozenset(
            {
                "route_intent",
                "routing_source",
                "campaign_target_id",
                "reason_code",
                "note",
            }
        ),
    ),
    "ResultAttributed": PayloadSchema(
        required=frozenset({"result_type", "result_id"}),
        optional=frozenset({"note"}),
    ),
    "OutcomeChanged": PayloadSchema(
        required=frozenset({"status"}),
        optional=frozenset({"previous_status", "note"}),
    ),
    "LeadCreated": PayloadSchema(
        required=frozenset({"lead_id", "submission_id"}),
        optional=frozenset({"route_intent", "module_owner", "note"}),
    ),
    "CandidateCreated": PayloadSchema(
        required=frozenset({"candidate_id", "lead_id", "submission_id"}),
        optional=frozenset({"route_intent", "module_owner", "note"}),
    ),
    "DuplicateDetected": PayloadSchema(
        required=frozenset({"entity_type", "entity_id"}),
        optional=frozenset({"duplicate_of_id", "note"}),
    ),
    "FlightAutoPaused": _NOTE,
    "FlightAutoResumed": _NOTE,
    "SpendAnomalyDetected": PayloadSchema(
        required=frozenset({"anomaly_code"}),
        optional=frozenset({"currency", "note"}),
    ),
    "DeliveryErrorOccurred": PayloadSchema(
        required=frozenset({"error_code"}),
        optional=frozenset({"provider", "note"}),
    ),
}

_STR_KEYS = {
    "FlightCreated": frozenset({"new_status", "previous_status", "reason"}),
    "FlightStarted": frozenset({"previous_status", "new_status", "reason"}),
    "FlightPaused": frozenset({"previous_status", "new_status", "reason"}),
    "FlightResumed": frozenset({"previous_status", "new_status", "reason"}),
    "FlightCompleted": frozenset({"previous_status", "new_status", "reason"}),
    "FlightFailed": frozenset(
        {"reason_code", "previous_status", "new_status", "reason", "note"}
    ),
    "BudgetChanged": frozenset({"currency", "note"}),
    "AudienceChanged": frozenset({"audience_ref", "change_kind", "note"}),
    "EndpointChanged": frozenset({"endpoint_id", "change_kind", "note"}),
    "ProviderSubmissionAccepted": frozenset(
        {"external_submission_id", "reason_code", "note"}
    ),
    "ProviderSubmissionRejected": frozenset(
        {"external_submission_id", "reason_code", "note"}
    ),
    "ProviderStatusChanged": frozenset({"status", "previous_status", "note"}),
    "SubmissionReceived": frozenset(
        {"reason_code", "normalized_schema_version", "note"}
    ),
    "SubmissionNormalized": frozenset(
        {"reason_code", "normalized_schema_version", "note"}
    ),
    "SubmissionRejected": frozenset(
        {"reason_code", "normalized_schema_version", "note"}
    ),
    "RoutingCompleted": frozenset(
        {
            "route_intent",
            "routing_source",
            "campaign_target_id",
            "target_type",
            "reason_code",
            "note",
        }
    ),
    "RoutingFailed": frozenset(
        {
            "route_intent",
            "routing_source",
            "campaign_target_id",
            "reason_code",
            "note",
        }
    ),
    "ResultAttributed": frozenset({"result_type", "result_id", "note"}),
    "OutcomeChanged": frozenset({"status", "previous_status", "note"}),
    "LeadCreated": frozenset({"lead_id", "submission_id", "route_intent", "module_owner", "note"}),
    "CandidateCreated": frozenset(
        {"candidate_id", "lead_id", "submission_id", "route_intent", "module_owner", "note"}
    ),
    "DuplicateDetected": frozenset(
        {"entity_type", "entity_id", "duplicate_of_id", "note"}
    ),
    "SpendAnomalyDetected": frozenset({"anomaly_code", "currency", "note"}),
    "DeliveryErrorOccurred": frozenset({"error_code", "provider", "note"}),
}

_NUMBER_KEYS = {
    "BudgetChanged": frozenset({"amount", "new_amount", "previous_amount"}),
}


def _build_validators() -> dict[str, PayloadValidator]:
    out: dict[str, PayloadValidator] = {}
    for event_type, schema in _SCHEMAS.items():
        out[event_type] = _schema_validator(
            event_type,
            schema,
            str_keys=_STR_KEYS.get(event_type, frozenset({"note"})),
            number_keys=_NUMBER_KEYS.get(event_type, frozenset()),
        )
    return out


PAYLOAD_VALIDATORS_V1: Mapping[str, PayloadValidator] = _build_validators()
PAYLOAD_SCHEMAS_V1: Mapping[str, PayloadSchema] = dict(_SCHEMAS)


def validate_activity_payload(*, event_type: str, event_version: str, payload: dict[str, Any]) -> None:
    """Validate payload for a specific ``event_type`` + ``event_version`` pair."""
    from backend.app.acquisition.activity.catalog import get_activity_event_contract
    from backend.app.acquisition.activity.errors import (
        UnknownActivityEventType,
        UnsupportedActivityEventVersion,
    )

    contract = get_activity_event_contract(event_type)
    if contract is None:
        raise UnknownActivityEventType(event_type)
    if event_version != contract.event_version:
        raise UnsupportedActivityEventVersion(
            event_type, event_version, contract.event_version
        )
    contract.validate_payload(payload if payload is not None else {})


__all__ = [
    "PayloadSchema",
    "PayloadValidator",
    "PAYLOAD_SCHEMAS_V1",
    "PAYLOAD_VALIDATORS_V1",
    "validate_activity_payload",
]
