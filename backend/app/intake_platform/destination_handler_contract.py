"""Destination handler contract — Intake Runtime Split R3/R4.

Shared Intake knows destination contracts only. Destination packages own
handler callables and create physical result objects (Application / SalesInquiry).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

RESULT_APPLICATION = "application"
RESULT_SALES_INQUIRY = "sales_inquiry"


@dataclass(frozen=True, slots=True)
class DestinationHandlerResult:
    handler_id: str
    destination: str
    route_intent: str
    result_entity_type: str
    decision: Any
    created_candidate_id: Optional[str] = None
    transport_lead_id: Optional[str] = None
    effective_policy: Any = None
    # R4 physical result identity (None only for disposition / unresolved paths).
    result_entity_id: Optional[str] = None
    result_created: bool = False

    def assert_owns_domain(
        self,
        *,
        expected_destination: str,
        expected_result: str,
        require_result_id: bool = False,
    ) -> None:
        if self.destination != expected_destination:
            raise DestinationHandlerDomainError(
                "handler returned foreign destination",
                details={
                    "handler_id": self.handler_id,
                    "expected_destination": expected_destination,
                    "actual_destination": self.destination,
                },
            )
        if self.result_entity_type != expected_result:
            raise DestinationHandlerDomainError(
                "handler returned foreign result entity type",
                details={
                    "handler_id": self.handler_id,
                    "expected_result_entity_type": expected_result,
                    "actual_result_entity_type": self.result_entity_type,
                },
            )
        if expected_result == RESULT_APPLICATION and self.result_entity_type == RESULT_SALES_INQUIRY:
            raise DestinationHandlerDomainError(
                "Recruitment handler cannot return SalesInquiry",
                details={"handler_id": self.handler_id},
            )
        if expected_result == RESULT_SALES_INQUIRY and self.result_entity_type == RESULT_APPLICATION:
            raise DestinationHandlerDomainError(
                "Sales handler cannot return Application",
                details={"handler_id": self.handler_id},
            )
        if require_result_id or self.result_created:
            if not str(self.result_entity_id or "").strip():
                raise DestinationHandlerDomainError(
                    "destination result object id is required",
                    details={
                        "handler_id": self.handler_id,
                        "result_entity_type": self.result_entity_type,
                        "result_created": self.result_created,
                    },
                )


class DestinationHandlerDomainError(Exception):
    code = "intake_destination_handler_domain_error"

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}
