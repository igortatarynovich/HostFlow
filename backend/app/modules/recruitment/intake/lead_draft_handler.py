"""Recruitment-owned intake handler — recruitment.lead_draft (Runtime Split R3).

Must not import Sales models/services/packages.
Lead remains temporary transport until R4 Application result object.
"""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.entity_profile.public_intake_draft_session import submit_public_intake_lead_draft
from backend.app.forms_platform.constants import HANDLER_RECRUITMENT_LEAD_DRAFT
from backend.app.intake_platform.destination_handler_contract import (
    RESULT_APPLICATION,
    DestinationHandlerResult,
)
from backend.app.intake_platform.destination_registry import DESTINATION_RECRUITMENT
from backend.app.models.intake_routing_enums import RouteIntent
from backend.app.models.lead import Lead

HANDLER_ID = HANDLER_RECRUITMENT_LEAD_DRAFT
ROUTE_INTENT = RouteIntent.candidate_application.value


async def handle_candidate_application_draft(
    db: AsyncSession,
    *,
    tenant_id: str,
    draft_lead: Lead,
    intake_state: dict[str, Any],
    presentation_code: Optional[str] = None,
    source: str = "public_intake",
) -> DestinationHandlerResult:
    """Recruitment destination handler for route_intent=candidate_application.

    Accepts only candidate_application. Never owns sales_inquiry.
    """
    _ = presentation_code  # reserved for R5 handoff envelope parity
    state = {**intake_state, "application_kind": "candidate"}
    decision, created_candidate_id = await submit_public_intake_lead_draft(
        db,
        tenant_id=str(tenant_id),
        lead=draft_lead,
        intake_state=state,
        source=source,
        route_intent_override=ROUTE_INTENT,
    )
    return DestinationHandlerResult(
        handler_id=HANDLER_ID,
        destination=DESTINATION_RECRUITMENT,
        route_intent=ROUTE_INTENT,
        result_entity_type=RESULT_APPLICATION,
        decision=decision,
        created_candidate_id=created_candidate_id,
        transport_lead_id=str(draft_lead.id),
        effective_policy=None,
    )
