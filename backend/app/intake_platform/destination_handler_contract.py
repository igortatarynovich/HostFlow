"""Destination handler contract — Intake Runtime Split R3.

Shared Intake knows destination contracts only. Destination packages own
handler callables. Result entity types are semantic until R4 physical models.
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

    def assert_owns_domain(self, *, expected_destination: str, expected_result: str) -> None:
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


class DestinationHandlerDomainError(Exception):
    code = "intake_destination_handler_domain_error"

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}
