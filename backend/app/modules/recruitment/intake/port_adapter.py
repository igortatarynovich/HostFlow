"""Recruitment inbound adapter — implements Flights RecruitmentIntakePort.

Owns the bridge into Recruitment domain create services.
Must not import Sales.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.acquisition.flights.destination_contract import (
    DISPATCHER_CANDIDATE_APPLICATION,
    DestinationDispatchResult,
    DestinationSubmitRequest,
)
from backend.app.models.lead import Lead
from backend.app.modules.recruitment.intake.lead_draft_handler import (
    handle_candidate_application_draft,
)


class RecruitmentIntakeAdapter:
    """Published inbound port for candidate_application."""

    async def accept(
        self,
        db: AsyncSession,
        request: DestinationSubmitRequest,
    ) -> DestinationDispatchResult:
        lead = await db.get(Lead, request.transport_lead_id)
        if lead is None:
            raise LookupError(f"transport lead not found: {request.transport_lead_id}")
        raw = await handle_candidate_application_draft(
            db,
            tenant_id=request.tenant_id,
            draft_lead=lead,
            intake_state=request.intake_state,
            presentation_code=request.presentation_code,
            source=request.source,
        )
        return DestinationDispatchResult(
            handler_id=DISPATCHER_CANDIDATE_APPLICATION,
            destination=raw.destination,
            route_intent=raw.route_intent,
            result_entity_type=raw.result_entity_type,
            decision=raw.decision,
            created_candidate_id=raw.created_candidate_id,
            transport_lead_id=raw.transport_lead_id,
            effective_policy=raw.effective_policy,
            result_entity_id=raw.result_entity_id,
            result_created=raw.result_created,
        )
