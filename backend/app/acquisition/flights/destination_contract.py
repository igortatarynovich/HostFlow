"""Acquisition / Flights — destination contract (R3.5 L0 boundary).

Flights owns routing dispatch contracts. Destination modules implement ports.
This module must NOT import Recruitment/Sales ORM or domain services.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

RESULT_APPLICATION = "application"
RESULT_SALES_INQUIRY = "sales_inquiry"

# Flights-owned dispatcher ids (not module-owned create handlers).
DISPATCHER_CANDIDATE_APPLICATION = "flights.candidate_application_dispatch"
DISPATCHER_SALES_INQUIRY = "flights.sales_inquiry_dispatch"

# Legacy R3 ids — superseded; runtime registry uses flights.* dispatchers.
LEGACY_HANDLER_RECRUITMENT_LEAD_DRAFT = "recruitment.lead_draft"
LEGACY_HANDLER_SALES_INQUIRY_DRAFT = "sales.inquiry_draft"


@dataclass(frozen=True, slots=True)
class DestinationSubmitRequest:
    """Neutral handoff request — no Lead/ORM types."""

    tenant_id: str
    transport_lead_id: str
    intake_state: dict[str, Any]
    route_intent: str
    presentation_code: Optional[str] = None
    source: str = "public_intake"
    handoff_id: Optional[str] = None
    idempotency_key: Optional[str] = None


@dataclass(frozen=True, slots=True)
class OpaqueResultRef:
    """Flights-stored destination pointer — no domain graph embedding."""

    module_owner: str
    result_type: str
    result_id: str


@dataclass(frozen=True, slots=True)
class DestinationDispatchResult:
    """Typed adapter response — string identities only.

    ``handler_id`` carries the Flights dispatcher id after the port adapter
    (historically named handler_id for Forms / R3 compat).
    """

    handler_id: str
    destination: str
    route_intent: str
    result_entity_type: str
    decision: Any
    created_candidate_id: Optional[str] = None
    transport_lead_id: Optional[str] = None
    effective_policy: Any = None
    result_entity_id: Optional[str] = None
    result_created: bool = False
    opaque_result: Optional[OpaqueResultRef] = None
    ledger_id: Optional[str] = None
    replayed_from_ledger: bool = False

    @property
    def dispatcher_id(self) -> str:
        return self.handler_id

    def opaque_ref(self) -> OpaqueResultRef:
        if self.opaque_result is not None:
            return self.opaque_result
        rid = str(self.result_entity_id or "").strip()
        if not rid:
            raise DestinationContractError(
                "opaque result reference requires result_entity_id",
                details={
                    "handler_id": self.handler_id,
                    "result_entity_type": self.result_entity_type,
                },
            )
        return OpaqueResultRef(
            module_owner=str(self.destination),
            result_type=str(self.result_entity_type),
            result_id=rid,
        )

    def assert_owns_domain(
        self,
        *,
        expected_destination: str,
        expected_result: str,
        require_result_id: bool = False,
    ) -> None:
        if self.destination != expected_destination:
            raise DestinationContractError(
                "adapter returned foreign destination",
                details={
                    "handler_id": self.handler_id,
                    "expected_destination": expected_destination,
                    "actual_destination": self.destination,
                },
            )
        if self.result_entity_type != expected_result:
            raise DestinationContractError(
                "adapter returned foreign result entity type",
                details={
                    "handler_id": self.handler_id,
                    "expected_result_entity_type": expected_result,
                    "actual_result_entity_type": self.result_entity_type,
                },
            )
        if expected_result == RESULT_APPLICATION and self.result_entity_type == RESULT_SALES_INQUIRY:
            raise DestinationContractError(
                "Recruitment intake port cannot return SalesInquiry",
                details={"handler_id": self.handler_id},
            )
        if expected_result == RESULT_SALES_INQUIRY and self.result_entity_type == RESULT_APPLICATION:
            raise DestinationContractError(
                "Sales intake port cannot return Application",
                details={"handler_id": self.handler_id},
            )
        if require_result_id or self.result_created:
            if not str(self.result_entity_id or "").strip():
                raise DestinationContractError(
                    "destination result object id is required",
                    details={
                        "handler_id": self.handler_id,
                        "result_entity_type": self.result_entity_type,
                        "result_created": self.result_created,
                    },
                )


DestinationHandlerResult = DestinationDispatchResult


class DestinationContractError(Exception):
    code = "flights_destination_contract_error"

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


DestinationHandlerDomainError = DestinationContractError
