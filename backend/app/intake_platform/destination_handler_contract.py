"""Compat shim — destination contract lives in Acquisition/Flights (R3.5)."""

from backend.app.acquisition.flights.destination_contract import (  # noqa: F401
    RESULT_APPLICATION,
    RESULT_SALES_INQUIRY,
    DestinationContractError,
    DestinationDispatchResult,
    DestinationHandlerDomainError,
    DestinationHandlerResult,
    DestinationSubmitRequest,
)

__all__ = [
    "RESULT_APPLICATION",
    "RESULT_SALES_INQUIRY",
    "DestinationContractError",
    "DestinationDispatchResult",
    "DestinationHandlerDomainError",
    "DestinationHandlerResult",
    "DestinationSubmitRequest",
]
