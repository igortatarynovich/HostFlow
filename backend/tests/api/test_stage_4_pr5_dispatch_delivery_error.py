"""Stage 4 PR-5 — DeliveryErrorOccurred from Flights dispatcher failures."""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import select

from backend.app.acquisition.activity import list_activity_events
from backend.app.acquisition.flights.destination_contract import DISPATCHER_SALES_INQUIRY
from backend.app.acquisition.flights.dispatcher import (
    dispatch_destination_submit,
    reset_handler_callables_for_tests,
)
from backend.app.db.session import async_session_maker
from backend.app.models.campaign import Campaign, CampaignRun
from backend.app.models.lead import Lead
from backend.app.models.own_company import OwnCompany
from backend.tests.conftest import _init_data, _set_tenant


async def _default_own_company_id(tenant_id: str) -> str:
    async with async_session_maker() as session:
        row = await session.execute(
            select(OwnCompany.id)
            .where(OwnCompany.tenant_id == tenant_id, OwnCompany.is_archived.is_(False))
            .limit(1)
        )
        oc = row.scalar_one_or_none()
        assert oc
        return str(oc)


@pytest.mark.asyncio
async def test_dispatcher_adapter_failure_emits_delivery_error() -> None:
    data = await _init_data()
    tenant_id = data["tenant_id"]
    own_company_id = await _default_own_company_id(tenant_id)
    campaign_id = str(uuid4())
    flight_id = str(uuid4())
    lead_id = str(uuid4())

    class _BoomPort:
        async def accept(self, _db, request):  # noqa: ANN001
            raise RuntimeError("adapter exploded")

    reset_handler_callables_for_tests({DISPATCHER_SALES_INQUIRY: _BoomPort()})
    try:
        async with async_session_maker() as db:
            await _set_tenant(db, tenant_id)
            db.add(
                Campaign(
                    id=campaign_id,
                    tenant_id=tenant_id,
                    own_company_id=own_company_id,
                    name="PR5 delivery",
                    status="active",
                    goal_type="hiring",
                    primary_kpi="hires",
                    current_flight_id=flight_id,
                )
            )
            db.add(
                CampaignRun(
                    id=flight_id,
                    tenant_id=tenant_id,
                    campaign_id=campaign_id,
                    code="flight_1",
                    name="Flight 1",
                    status="active",
                )
            )
            lead = Lead(
                id=lead_id,
                tenant_id=tenant_id,
                status="new",
                source="test",
                normalized={
                    "acquisition_routing_v1": {
                        "campaign_id": campaign_id,
                        "flight_id": flight_id,
                        "status": "routed",
                    }
                },
            )
            db.add(lead)
            await db.commit()

            with pytest.raises(RuntimeError, match="adapter exploded"):
                await dispatch_destination_submit(
                    db,
                    route_intent="sales_inquiry",
                    tenant_id=tenant_id,
                    draft_lead=lead,
                    intake_state={
                        "submission_id": str(uuid4()),
                        "acquisition_routing_v1": {
                            "campaign_id": campaign_id,
                            "flight_id": flight_id,
                        },
                    },
                )
            await db.commit()

            events = await list_activity_events(
                db,
                tenant_id=tenant_id,
                campaign_id=campaign_id,
                flight_id=flight_id,
                event_types=["DeliveryErrorOccurred"],
                limit=10,
            )
            assert len(events) == 1
            assert events[0].payload.get("error_code") == "RuntimeError"
            assert str(events[0].source_event_id or "").startswith(
                "acq.dispatch.delivery_error:"
            )
    finally:
        reset_handler_callables_for_tests(None)


@pytest.mark.asyncio
async def test_dispatcher_failure_without_campaign_skips_emit() -> None:
    data = await _init_data()
    tenant_id = data["tenant_id"]
    lead_id = str(uuid4())

    class _BoomPort:
        async def accept(self, _db, request):  # noqa: ANN001
            raise RuntimeError("no campaign context")

    reset_handler_callables_for_tests({DISPATCHER_SALES_INQUIRY: _BoomPort()})
    try:
        async with async_session_maker() as db:
            await _set_tenant(db, tenant_id)
            lead = Lead(
                id=lead_id,
                tenant_id=tenant_id,
                status="new",
                source="test",
                normalized={},
            )
            db.add(lead)
            await db.commit()

            with pytest.raises(RuntimeError):
                await dispatch_destination_submit(
                    db,
                    route_intent="sales_inquiry",
                    tenant_id=tenant_id,
                    draft_lead=lead,
                    intake_state={"submission_id": str(uuid4())},
                )
            await db.commit()

            # No campaign → no DeliveryErrorOccurred rows for this tenant with this note
            events = await list_activity_events(
                db,
                tenant_id=tenant_id,
                event_types=["DeliveryErrorOccurred"],
                limit=50,
            )
            assert all(
                (e.payload or {}).get("note") != "no campaign context" for e in events
            )
    finally:
        reset_handler_callables_for_tests(None)

