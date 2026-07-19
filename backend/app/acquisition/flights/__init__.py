"""Acquisition Flights package — routing dispatch boundary (ADR-024 / R3.5)."""

from backend.app.acquisition.flights.destination_contract import (
    DISPATCHER_CANDIDATE_APPLICATION,
    DISPATCHER_SALES_INQUIRY,
    DestinationDispatchResult,
    DestinationSubmitRequest,
)
from backend.app.acquisition.flights.destination_registry import (
    platform_destination_registry,
    reset_platform_destination_registry_for_tests,
)
from backend.app.acquisition.flights.dispatcher import dispatch_destination_submit

__all__ = [
    "DISPATCHER_CANDIDATE_APPLICATION",
    "DISPATCHER_SALES_INQUIRY",
    "DestinationDispatchResult",
    "DestinationSubmitRequest",
    "dispatch_destination_submit",
    "platform_destination_registry",
    "reset_platform_destination_registry_for_tests",
]
