"""Compat shim — destination dispatch lives in Acquisition/Flights (R3.5)."""

from backend.app.acquisition.flights.dispatcher import (  # noqa: F401
    dispatch_destination_submit,
    get_handler_callable,
    registered_handler_callables,
    reset_handler_callables_for_tests,
)

__all__ = [
    "dispatch_destination_submit",
    "get_handler_callable",
    "registered_handler_callables",
    "reset_handler_callables_for_tests",
]
