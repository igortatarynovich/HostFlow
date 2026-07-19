"""Destination handler dispatch — Intake Runtime Split R3.

Shared Intake resolves destination registry entry → owned callable.
Missing handler → fail-closed disposition (no Recruitment fallback).
"""

from __future__ import annotations

from typing import Any, Awaitable, Callable, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.forms_platform.constants import (
    HANDLER_RECRUITMENT_LEAD_DRAFT,
    HANDLER_SALES_INQUIRY_DRAFT,
)
from backend.app.forms_platform.errors import FormsRoutingUnresolvedError
from backend.app.intake_platform.destination_handler_contract import (
    RESULT_APPLICATION,
    RESULT_SALES_INQUIRY,
    DestinationHandlerDomainError,
    DestinationHandlerResult,
)
from backend.app.intake_platform.destination_registry import (
    DESTINATION_RECRUITMENT,
    DESTINATION_SALES,
    DestinationMissingHandlerError,
    DestinationUnknownIntentError,
    platform_destination_registry,
)
from backend.app.models.lead import Lead

DestinationHandlerFn = Callable[..., Awaitable[DestinationHandlerResult]]

_HANDLER_CALLABLES: dict[str, DestinationHandlerFn] | None = None


def _load_handler_callables() -> dict[str, DestinationHandlerFn]:
    # Lazy import so packages can import contract/registry without cycles.
    from backend.app.modules.recruitment.intake.lead_draft_handler import (
        handle_candidate_application_draft,
    )
    from backend.app.modules.sales.intake.inquiry_draft_handler import handle_sales_inquiry_draft

    return {
        HANDLER_RECRUITMENT_LEAD_DRAFT: handle_candidate_application_draft,
        HANDLER_SALES_INQUIRY_DRAFT: handle_sales_inquiry_draft,
    }


def registered_handler_callables() -> dict[str, DestinationHandlerFn]:
    global _HANDLER_CALLABLES
    if _HANDLER_CALLABLES is None:
        _HANDLER_CALLABLES = _load_handler_callables()
    return dict(_HANDLER_CALLABLES)


def reset_handler_callables_for_tests(
    mapping: dict[str, DestinationHandlerFn] | None = None,
) -> None:
    global _HANDLER_CALLABLES
    _HANDLER_CALLABLES = mapping


def get_handler_callable(handler_id: str) -> DestinationHandlerFn | None:
    return registered_handler_callables().get(str(handler_id or "").strip())


def _expected_result_for_destination(destination: str) -> str:
    if destination == DESTINATION_RECRUITMENT:
        return RESULT_APPLICATION
    if destination == DESTINATION_SALES:
        return RESULT_SALES_INQUIRY
    raise DestinationHandlerDomainError(
        "unsupported destination for result entity mapping",
        details={"destination": destination},
    )


async def dispatch_destination_submit(
    db: AsyncSession,
    *,
    route_intent: str | None,
    tenant_id: str,
    draft_lead: Lead,
    intake_state: dict[str, Any],
    presentation_code: Optional[str] = None,
    source: str = "public_intake",
) -> DestinationHandlerResult:
    """Resolve registry entry and invoke the single owned destination handler."""
    try:
        entry = platform_destination_registry().resolve(route_intent)
    except DestinationUnknownIntentError as exc:
        raise FormsRoutingUnresolvedError(
            details=dict(exc.details),
            message=exc.message,
        ) from exc

    handler = get_handler_callable(entry.handler_id)
    if handler is None:
        raise DestinationMissingHandlerError(
            "destination handler callable is not registered",
            details={
                "handler_id": entry.handler_id,
                "route_intent": entry.route_intent,
                "destination": entry.destination,
                "reason": "missing_handler_callable",
            },
        )

    result = await handler(
        db,
        tenant_id=str(tenant_id),
        draft_lead=draft_lead,
        intake_state=intake_state,
        presentation_code=presentation_code,
        source=source,
    )
    result.assert_owns_domain(
        expected_destination=entry.destination,
        expected_result=_expected_result_for_destination(entry.destination),
        require_result_id=bool(result.result_created),
    )
    if result.handler_id != entry.handler_id:
        raise DestinationHandlerDomainError(
            "handler_id mismatch after dispatch",
            details={
                "expected_handler_id": entry.handler_id,
                "actual_handler_id": result.handler_id,
            },
        )
    if result.route_intent != entry.route_intent:
        raise DestinationHandlerDomainError(
            "route_intent mismatch after dispatch",
            details={
                "expected_route_intent": entry.route_intent,
                "actual_route_intent": result.route_intent,
            },
        )
    return result
