"""Test/helpers: seed SalesInquiry + Flights ledger + Review stamp for product convert."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.acquisition.flights.destination_contract import (
    DISPATCHER_SALES_INQUIRY,
    RESULT_SALES_INQUIRY,
)
from backend.app.acquisition.flights.destination_registry import DESTINATION_SALES
from backend.app.models.flight_dispatch_ledger import STATUS_CONFIRMED, FlightDispatchLedger
from backend.app.modules.leads import crud as leads_crud
from backend.app.modules.sales.services.ambiguous_match_review import mark_unique_match_not_required
from backend.app.modules.sales.services.sales_inquiry_service import ensure_sales_inquiry_for_transport_lead


async def ensure_product_convert_readiness(
    db: AsyncSession,
    *,
    tenant_id: str,
    lead_id: str,
) -> str:
    """Ensure SI + confirmed Sales Flights ledger + Review ``not_required`` for convert.

    Returns ``sales_inquiry_id``.
    """
    lead = await leads_crud.get_lead(db, tenant_id=tenant_id, lead_id=lead_id)
    if lead is None:
        raise RuntimeError(f"lead not found: {lead_id}")

    inquiry = await ensure_sales_inquiry_for_transport_lead(
        db,
        tenant_id=tenant_id,
        lead=lead,
        source="public_intake",
    )
    own_company_id = str(getattr(inquiry, "own_company_id", None) or getattr(lead, "own_company_id", "") or "")

    ledger = await db.scalar(
        select(FlightDispatchLedger)
        .where(
            FlightDispatchLedger.tenant_id == tenant_id,
            FlightDispatchLedger.transport_lead_id == str(lead.id),
            FlightDispatchLedger.destination == DESTINATION_SALES,
            FlightDispatchLedger.status == STATUS_CONFIRMED,
        )
        .order_by(FlightDispatchLedger.confirmed_at.desc().nullslast())
        .limit(1)
    )
    if ledger is None:
        ledger_id = str(uuid.uuid4())
        db.add(
            FlightDispatchLedger(
                id=ledger_id,
                tenant_id=tenant_id,
                idempotency_key=f"flights.dispatch:{tenant_id}:{lead.id}:sales_inquiry:convert-ready",
                transport_lead_id=str(lead.id),
                route_intent="sales_inquiry",
                destination=DESTINATION_SALES,
                dispatcher_id=DISPATCHER_SALES_INQUIRY,
                status=STATUS_CONFIRMED,
                module_owner=DESTINATION_SALES,
                result_type=RESULT_SALES_INQUIRY,
                result_id=str(inquiry.id),
                confirmed_at=datetime.now(timezone.utc),
            )
        )
        await db.flush()
    else:
        ledger_id = str(ledger.id)

    await mark_unique_match_not_required(
        db,
        tenant_id=tenant_id,
        sales_inquiry_id=str(inquiry.id),
        destination=DESTINATION_SALES,
        flights_ledger_id=ledger_id,
        own_company_id=own_company_id or None,
        actor_id="convert-readiness",
    )
    await db.commit()
    return str(inquiry.id)
