"""Recruitment-owned intake handler — recruitment.lead_draft (Runtime Split R3/R4).

Must not import Sales models/services/packages.
Creates Application as destination result; Lead is optional transport only.
"""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.entity_profile.public_intake_draft_session import (
    get_public_intake_draft_block,
    submit_public_intake_lead_draft,
)
from backend.app.forms_platform.constants import HANDLER_RECRUITMENT_LEAD_DRAFT
from backend.app.intake_platform.destination_handler_contract import (
    RESULT_APPLICATION,
    DestinationHandlerResult,
)
from backend.app.intake_platform.destination_registry import DESTINATION_RECRUITMENT
from backend.app.models.intake_routing_enums import RouteIntent
from backend.app.models.lead import Lead
from backend.app.modules.recruitment.services.application_result_service import (
    ensure_application_result_for_transport_lead,
)

HANDLER_ID = HANDLER_RECRUITMENT_LEAD_DRAFT
ROUTE_INTENT = RouteIntent.candidate_application.value


def _idempotency_key(lead: Lead, intake_state: dict[str, Any]) -> str:
    block = get_public_intake_draft_block(lead)
    token = str(block.get("intake_token") or "").strip()
    if token:
        return f"recruitment.application:{token}"
    return f"recruitment.application:lead:{lead.id}"


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

    Accepts only candidate_application. Never owns sales_inquiry / SalesInquiry.
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

    candidate_id = str(created_candidate_id or getattr(draft_lead, "candidate_id", None) or "").strip() or None
    result_entity_id: Optional[str] = None
    result_created = False
    if candidate_id:
        app = await ensure_application_result_for_transport_lead(
            db,
            tenant_id=str(tenant_id),
            lead=draft_lead,
            candidate_id=candidate_id,
            source=source,
            idempotency_key=_idempotency_key(draft_lead, state),
        )
        if app is not None:
            result_entity_id = str(app.id)
            result_created = True

    return DestinationHandlerResult(
        handler_id=HANDLER_ID,
        destination=DESTINATION_RECRUITMENT,
        route_intent=ROUTE_INTENT,
        result_entity_type=RESULT_APPLICATION,
        decision=decision,
        created_candidate_id=created_candidate_id,
        transport_lead_id=str(draft_lead.id),
        effective_policy=None,
        result_entity_id=result_entity_id,
        result_created=result_created,
    )
