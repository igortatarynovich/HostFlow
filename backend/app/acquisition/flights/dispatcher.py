"""Flights destination dispatcher (R3.5).

Owns routing decision → destination adapter call.
Loads only published port adapters — never Recruitment/Sales ORM/services.
"""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.acquisition.flights.destination_contract import (
    DISPATCHER_CANDIDATE_APPLICATION,
    DISPATCHER_SALES_INQUIRY,
    RESULT_APPLICATION,
    RESULT_SALES_INQUIRY,
    DestinationContractError,
    DestinationDispatchResult,
    DestinationSubmitRequest,
)
from backend.app.acquisition.flights.destination_registry import (
    DESTINATION_RECRUITMENT,
    DESTINATION_SALES,
    DestinationMissingHandlerError,
    DestinationUnknownIntentError,
    platform_destination_registry,
)
from backend.app.acquisition.flights.ports import DestinationIntakePort
from backend.app.forms_platform.errors import FormsRoutingUnresolvedError
from backend.app.models.lead import Lead

_PORT_REGISTRY: dict[str, DestinationIntakePort] | None = None


def _load_default_ports() -> dict[str, DestinationIntakePort]:
    # Lazy import of published inbound adapters only (not domain services/ORM).
    from backend.app.modules.recruitment.intake.port_adapter import RecruitmentIntakeAdapter
    from backend.app.modules.sales.intake.port_adapter import SalesIntakeAdapter

    return {
        DISPATCHER_CANDIDATE_APPLICATION: RecruitmentIntakeAdapter(),
        DISPATCHER_SALES_INQUIRY: SalesIntakeAdapter(),
    }


def registered_destination_ports() -> dict[str, DestinationIntakePort]:
    global _PORT_REGISTRY
    if _PORT_REGISTRY is None:
        _PORT_REGISTRY = _load_default_ports()
    return dict(_PORT_REGISTRY)


def reset_handler_callables_for_tests(
    mapping: dict[str, Any] | None = None,
) -> None:
    """Test helper — inject ports or callables compatible with DestinationIntakePort.accept."""
    global _PORT_REGISTRY
    if mapping is None:
        _PORT_REGISTRY = None
        return
    ports: dict[str, DestinationIntakePort] = {}
    for key, value in mapping.items():
        if hasattr(value, "accept"):
            ports[key] = value
        else:
            ports[key] = _CallablePort(value)
    _PORT_REGISTRY = ports


def registered_handler_callables() -> dict[str, Any]:
    """Compat for R3 tests expecting callable map."""
    return {
        did: getattr(port, "accept", port) for did, port in registered_destination_ports().items()
    }


def get_handler_callable(handler_id: str) -> Any | None:
    return registered_destination_ports().get(str(handler_id or "").strip())


class _CallablePort:
    """Wrap a legacy async callable(db, tenant_id=..., draft_lead=...) as a port."""

    def __init__(self, fn: Any) -> None:
        self._fn = fn

    async def accept(self, db: AsyncSession, request: DestinationSubmitRequest) -> DestinationDispatchResult:
        from types import SimpleNamespace

        lead: Any = None
        if db is not None and request.transport_lead_id:
            lead = await db.get(Lead, request.transport_lead_id)
        draft = lead if lead is not None else SimpleNamespace(id=request.transport_lead_id)
        raw = await self._fn(
            db,
            tenant_id=request.tenant_id,
            draft_lead=draft,
            intake_state=request.intake_state,
            presentation_code=request.presentation_code,
            source=request.source,
        )
        if isinstance(raw, DestinationDispatchResult):
            return raw
        return DestinationDispatchResult(
            handler_id=str(getattr(raw, "handler_id", None) or getattr(raw, "dispatcher_id", "")),
            destination=str(getattr(raw, "destination", "")),
            route_intent=str(getattr(raw, "route_intent", "")),
            result_entity_type=str(getattr(raw, "result_entity_type", "")),
            decision=getattr(raw, "decision", None),
            created_candidate_id=getattr(raw, "created_candidate_id", None),
            transport_lead_id=getattr(raw, "transport_lead_id", None),
            effective_policy=getattr(raw, "effective_policy", None),
            result_entity_id=getattr(raw, "result_entity_id", None),
            result_created=bool(getattr(raw, "result_created", False)),
        )


def _expected_result_for_destination(destination: str) -> str:
    if destination == DESTINATION_RECRUITMENT:
        return RESULT_APPLICATION
    if destination == DESTINATION_SALES:
        return RESULT_SALES_INQUIRY
    raise DestinationContractError(
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
) -> DestinationDispatchResult:
    """Flights dispatcher: resolve registry → call destination intake port."""
    try:
        entry = platform_destination_registry().resolve(route_intent)
    except DestinationUnknownIntentError as exc:
        raise FormsRoutingUnresolvedError(
            details=dict(exc.details),
            message=exc.message,
        ) from exc

    port = registered_destination_ports().get(entry.dispatcher_id)
    if port is None:
        raise DestinationMissingHandlerError(
            "destination intake port is not registered",
            details={
                "dispatcher_id": entry.dispatcher_id,
                "route_intent": entry.route_intent,
                "destination": entry.destination,
                "reason": "missing_handler_callable",
            },
        )

    request = DestinationSubmitRequest(
        tenant_id=str(tenant_id),
        transport_lead_id=str(draft_lead.id),
        intake_state=intake_state,
        route_intent=entry.route_intent,
        presentation_code=presentation_code,
        source=source,
    )
    result = await port.accept(db, request)
    result.assert_owns_domain(
        expected_destination=entry.destination,
        expected_result=_expected_result_for_destination(entry.destination),
        require_result_id=bool(result.result_created),
    )
    if result.handler_id != entry.dispatcher_id:
        raise DestinationContractError(
            "dispatcher_id mismatch after dispatch",
            details={
                "expected_dispatcher_id": entry.dispatcher_id,
                "actual_dispatcher_id": result.handler_id,
            },
        )
    if result.route_intent != entry.route_intent:
        raise DestinationContractError(
            "route_intent mismatch after dispatch",
            details={
                "expected_route_intent": entry.route_intent,
                "actual_route_intent": result.route_intent,
            },
        )
    return result
