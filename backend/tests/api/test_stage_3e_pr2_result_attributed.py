"""Stage 3E PR-2 — ResultAttributed instrumentation."""

from __future__ import annotations

import ast
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import select, text

from backend.app.acquisition import result_attribution as attr_mod
from backend.app.acquisition.activity import list_activity_events
from backend.app.acquisition.flights.lifecycle import (
    FLIGHT_STATUS_ACTIVE,
    create_flight,
    transition_flight_status,
)
from backend.app.acquisition.result_attribution import (
    RESULT_TYPE_INTAKE_LEAD,
    record_result_attribution_from_routing,
    result_attributed_source_event_id,
)
from backend.app.acquisition.submission_routing import (
    RoutingDecisionStatus,
    RoutingSource,
    UniversalRoutingDecision,
    stamp_acquisition_routing_on_lead,
)
from backend.app.db.session import async_session_maker
from backend.app.models.acquisition_activity_event import ACTOR_TYPE_SYSTEM
from backend.app.models.campaign import Campaign
from backend.app.models.lead import Lead
from backend.app.models.own_company import OwnCompany
from backend.app.models.tenant import Tenant
from backend.tests.conftest import _init_data

_ATTR_PATH = Path(attr_mod.__file__)


async def _ensure_tenant(db, tenant_id: str) -> None:
    exists = (
        await db.execute(select(Tenant.id).where(Tenant.id == tenant_id))
    ).scalar_one_or_none()
    if exists is not None:
        return
    suffix = tenant_id.replace("-", "")[:8]
    db.add(
        Tenant(
            id=tenant_id,
            name=f"Tenant {suffix}",
            slug=f"t-{suffix}",
            api_key=f"api-{suffix}-{uuid4().hex[:8]}",
            is_active=True,
        )
    )
    await db.flush()


async def _own_company_id(db, tenant_id: str) -> str:
    row = await db.execute(
        select(OwnCompany.id)
        .where(OwnCompany.tenant_id == tenant_id, OwnCompany.is_archived.is_(False))
        .order_by(OwnCompany.created_at.asc())
        .limit(1)
    )
    oc = row.scalar_one_or_none()
    if oc is None:
        oc = str(uuid4())
        db.add(OwnCompany(id=oc, tenant_id=tenant_id, name=f"OC {uuid4().hex[:6]}"))
        await db.flush()
    return str(oc)


async def _seed_campaign_flight(db, *, tenant_id: str) -> tuple[Campaign, str]:
    await _ensure_tenant(db, tenant_id)
    oc = await _own_company_id(db, tenant_id)
    campaign = Campaign(
        id=str(uuid4()),
        tenant_id=tenant_id,
        own_company_id=oc,
        name=f"Campaign {uuid4().hex[:6]}",
        status="active",
        goal_type="hiring",
        primary_kpi="hires",
    )
    db.add(campaign)
    await db.flush()
    flight, _ = await create_flight(
        db,
        tenant_id=tenant_id,
        campaign_id=campaign.id,
        actor_type=ACTOR_TYPE_SYSTEM,
    )
    await transition_flight_status(
        db,
        flight=flight,
        new_status=FLIGHT_STATUS_ACTIVE,
        actor_type=ACTOR_TYPE_SYSTEM,
    )
    campaign.current_flight_id = flight.id
    await db.flush()
    return campaign, flight.id


async def _seed_routed_lead(
    db, *, tenant_id: str, campaign_id: str, flight_id: str
) -> Lead:
    oc = await _own_company_id(db, tenant_id)
    lead = Lead(
        id=str(uuid4()),
        tenant_id=tenant_id,
        own_company_id=oc,
        status="new",
        source="public_intake",
        lead_type="client",
        payload={},
        normalized={},
    )
    db.add(lead)
    await db.flush()
    stamp_acquisition_routing_on_lead(
        lead,
        UniversalRoutingDecision(
            status=RoutingDecisionStatus.routed.value,
            route_intent="sales_inquiry",
            campaign_id=campaign_id,
            campaign_run_id=flight_id,
            source=RoutingSource.campaign_target.value,
            decided_at="2026-07-21T12:00:00+00:00",
        ),
    )
    await db.flush()
    return lead


def test_result_attribution_writes_only_via_append() -> None:
    src = _ATTR_PATH.read_text(encoding="utf-8")
    assert "append_activity_event" in src
    assert "AcquisitionActivityEvent(" not in src
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            name = getattr(node.func, "id", None) or getattr(node.func, "attr", None)
            if name == "AcquisitionActivityEvent":
                raise AssertionError(f"raw construct at line {node.lineno}")


@pytest.mark.asyncio
async def test_record_attribution_emits_result_attributed() -> None:
    data = await _init_data()
    tenant_id = data["tenant_id"]

    async with async_session_maker() as db:
        camp, flight_id = await _seed_campaign_flight(db, tenant_id=tenant_id)
        lead = await _seed_routed_lead(
            db, tenant_id=tenant_id, campaign_id=camp.id, flight_id=flight_id
        )
        submission_id = str(uuid4())
        row = await record_result_attribution_from_routing(
            db,
            tenant_id=tenant_id,
            lead=lead,
            submission_id=submission_id,
            result_type=RESULT_TYPE_INTAKE_LEAD,
            result_id=str(lead.id),
        )
        events = await list_activity_events(
            db,
            tenant_id=tenant_id,
            submission_id=submission_id,
            event_types=["ResultAttributed"],
        )
        assert len(events) == 1
        ev = events[0]
        assert ev.campaign_id == camp.id
        assert ev.flight_id == flight_id
        assert ev.submission_id == submission_id
        assert ev.result_id == row.result_id
        assert ev.payload == {
            "result_type": RESULT_TYPE_INTAKE_LEAD,
            "result_id": str(lead.id),
        }
        assert ev.source_event_id == result_attributed_source_event_id(
            result_type=RESULT_TYPE_INTAKE_LEAD, result_id=str(lead.id)
        )
        assert ev.provider is None
        await db.commit()


@pytest.mark.asyncio
async def test_attribution_retry_same_activity_event() -> None:
    data = await _init_data()
    tenant_id = data["tenant_id"]

    async with async_session_maker() as db:
        camp, flight_id = await _seed_campaign_flight(db, tenant_id=tenant_id)
        lead = await _seed_routed_lead(
            db, tenant_id=tenant_id, campaign_id=camp.id, flight_id=flight_id
        )
        submission_id = str(uuid4())
        first = await record_result_attribution_from_routing(
            db,
            tenant_id=tenant_id,
            lead=lead,
            submission_id=submission_id,
            result_type=RESULT_TYPE_INTAKE_LEAD,
            result_id=str(lead.id),
        )
        second = await record_result_attribution_from_routing(
            db,
            tenant_id=tenant_id,
            lead=lead,
            submission_id=submission_id,
            result_type=RESULT_TYPE_INTAKE_LEAD,
            result_id=str(lead.id),
        )
        assert first.id == second.id
        count = await db.execute(
            text(
                "SELECT count(*) FROM acquisition_activity_events "
                "WHERE tenant_id = :t AND event_type = 'ResultAttributed' "
                "AND result_id = :r"
            ),
            {"t": tenant_id, "r": str(lead.id)},
        )
        assert count.scalar() == 1
        await db.commit()


@pytest.mark.asyncio
async def test_attribution_rollback_drops_activity() -> None:
    data = await _init_data()
    tenant_id = data["tenant_id"]

    async with async_session_maker() as db:
        camp, flight_id = await _seed_campaign_flight(db, tenant_id=tenant_id)
        lead = await _seed_routed_lead(
            db, tenant_id=tenant_id, campaign_id=camp.id, flight_id=flight_id
        )
        await db.commit()
        lead_id = lead.id
        campaign_id = camp.id

    async with async_session_maker() as db:
        lead = await db.get(Lead, lead_id)
        assert lead is not None
        submission_id = str(uuid4())
        await record_result_attribution_from_routing(
            db,
            tenant_id=tenant_id,
            lead=lead,
            submission_id=submission_id,
            result_type=RESULT_TYPE_INTAKE_LEAD,
            result_id=lead_id,
        )
        await db.rollback()

    async with async_session_maker() as db:
        rows = await list_activity_events(
            db,
            tenant_id=tenant_id,
            campaign_id=campaign_id,
            event_types=["ResultAttributed"],
        )
        assert rows == []
