"""Submission handler registry — ADR-007 target entity mapping (C4 MVP)."""

from __future__ import annotations

from typing import Any

from backend.app.forms_platform.constants import (
    HANDLER_RECRUITMENT_CLIENT_LEAD_DRAFT,
    HANDLER_RECRUITMENT_LEAD_DRAFT,
)


def resolve_submission_handler(*, route_intent: str | None) -> dict[str, Any]:
    """Map intake route intent to ADR-007 submission handler metadata."""
    intent = str(route_intent or "candidate_application").strip().lower()
    if intent in {"sales_inquiry", "client_lead"}:
        return {
            "handler_id": HANDLER_RECRUITMENT_CLIENT_LEAD_DRAFT,
            "module_owner": "recruitment",
            "creates": ["lead"],
            "creates_on_create": {"lead_draft": True, "candidate": False},
            "route_intent": intent,
        }
    return {
        "handler_id": HANDLER_RECRUITMENT_LEAD_DRAFT,
        "module_owner": "recruitment",
        "creates": ["lead"],
        "creates_on_create": {"lead_draft": True, "candidate": False},
        "route_intent": intent or "candidate_application",
    }


def list_registered_handlers() -> list[dict[str, Any]]:
    """Known handlers for admin/platform introspection."""
    return [
        resolve_submission_handler(route_intent="candidate_application"),
        resolve_submission_handler(route_intent="client_lead"),
    ]
