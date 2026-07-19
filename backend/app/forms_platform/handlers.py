"""Submission handler resolution via Destination Registry (Runtime Split R1/R2).

Fail-closed: missing route_intent does not default to candidate_application.
sales_inquiry resolves to Sales-owned handler — never recruitment.client_lead_draft.
"""

from __future__ import annotations

from typing import Any

from backend.app.forms_platform.errors import FormsRoutingUnresolvedError
from backend.app.intake_platform.destination_registry import (
    DestinationUnknownIntentError,
    platform_destination_registry,
)


def resolve_submission_handler(*, route_intent: str | None) -> dict[str, Any]:
    """Map explicit route_intent to destination-owned handler metadata.

    Raises FormsRoutingUnresolvedError when intent is missing/unknown (R1).
    """
    try:
        entry = platform_destination_registry().resolve(route_intent)
    except DestinationUnknownIntentError as exc:
        raise FormsRoutingUnresolvedError(
            details=dict(exc.details),
            message=exc.message,
        ) from exc
    return entry.to_handler_dict()


def list_registered_handlers() -> list[dict[str, Any]]:
    """Known destination handlers for admin/platform introspection."""
    return [e.to_handler_dict() for e in platform_destination_registry().list_entries()]


def disposition_handler(*, reason: str, route_intent: str | None = None) -> dict[str, Any]:
    """Non-dispatching handler metadata for unresolved routing (no domain objects)."""
    return {
        "handler_id": "intake.disposition_unresolved",
        "module_owner": None,
        "destination": None,
        "route_intent": route_intent,
        "creates": [],
        "creates_on_create": {
            "lead_draft": False,
            "candidate": False,
            "application": False,
            "sales_inquiry": False,
        },
        "routing_status": "unresolved",
        "routing_reason": reason,
    }
