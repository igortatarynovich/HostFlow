"""Stage 3E PR-2 — OutcomeChanged instrumentation."""

from __future__ import annotations

import ast
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import select, text

from backend.app.acquisition import outcome_service as outcome_mod
from backend.app.acquisition.activity import list_activity_events
from backend.app.acquisition.flights.lifecycle import (
    FLIGHT_STATUS_ACTIVE,
    create_flight,
    transition_flight_status,
)
from backend.app.acquisition.outcome_service import (
    STATUS_ACTIVE,
    STATUS_CANCELLED,
    STATUS_COMPLETED,
    STATUS_CREATED,
    STATUS_FAILED,
    apply_attribution_to_outcome,
    create_outcome,
    mark_outcome_cancelled,
    mark_outcome_failed,
    outcome_changed_source_event_id,
)
from backend.app.acquisition.result_attribution import (
    RESULT_TYPE_INTAKE_LEAD,
    record_result_attribution_from_routing,
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

_OUTCOME_PATH = Path(outcome_mod.__file__)


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


async def _seed_attribution(
    db, *, tenant_id: str, campaign_id: str, flight_id: str
) -> str:
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
    attr = await record_result_attribution_from_routing(
        db,
        tenant_id=tenant_id,
        lead=lead,
        submission_id=str(uuid4()),
        result_type=RESULT_TYPE_INTAKE_LEAD,
        result_id=str(lead.id),
    )
    return str(attr.id)


def test_outcome_service_writes_only_via_append() -> None:
    src = _OUTCOME_PATH.read_text(encoding="utf-8")
    assert "append_activity_event" in src
    assert "AcquisitionActivityEvent(" not in src
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            name = getattr(node.func, "id", None) or getattr(node.func, "attr", None)
            if name == "AcquisitionActivityEvent":
                raise AssertionError(f"raw construct at line {node.lineno}")


@pytest.mark.asyncio
async def test_create_outcome_emits_outcome_changed() -> None:
    data = await _init_data()
    tenant_id = data["tenant_id"]

    async with async_session_maker() as db:
        camp, flight_id = await _seed_campaign_flight(db, tenant_id=tenant_id)
        outcome = await create_outcome(
            db,
            tenant_id=tenant_id,
            campaign_id=camp.id,
            flight_id=flight_id,
        )
        events = await list_activity_events(
            db,
            tenant_id=tenant_id,
            outcome_id=outcome.id,
            event_types=["OutcomeChanged"],
        )
        assert len(events) == 1
        ev = events[0]
        assert ev.campaign_id == camp.id
        assert ev.flight_id == flight_id
        assert ev.outcome_id == outcome.id
        assert ev.payload == {"status": STATUS_CREATED}
        assert ev.source_event_id == outcome_changed_source_event_id(
            outcome_id=outcome.id,
            previous_status=None,
            new_status=STATUS_CREATED,
        )
        assert ev.provider is None
        await db.commit()


@pytest.mark.asyncio
async def test_apply_attribution_emits_activate_and_complete() -> None:
    data = await _init_data()
    tenant_id = data["tenant_id"]

    async with async_session_maker() as db:
        camp, flight_id = await _seed_campaign_flight(db, tenant_id=tenant_id)
        attr_id = await _seed_attribution(
            db, tenant_id=tenant_id, campaign_id=camp.id, flight_id=flight_id
        )
        outcome = await create_outcome(
            db,
            tenant_id=tenant_id,
            campaign_id=camp.id,
            flight_id=flight_id,
            progress_target=2,
        )
        outcome, _link, applied = await apply_attribution_to_outcome(
            db,
            tenant_id=tenant_id,
            outcome_id=outcome.id,
            attribution_id=attr_id,
        )
        assert applied is True
        assert outcome.status == STATUS_ACTIVE

        events = await list_activity_events(
            db,
            tenant_id=tenant_id,
            outcome_id=outcome.id,
            event_types=["OutcomeChanged"],
        )
        statuses = [e.payload.get("status") for e in events]
        assert statuses == [STATUS_CREATED, STATUS_ACTIVE]
        assert events[1].payload == {
            "status": STATUS_ACTIVE,
            "previous_status": STATUS_CREATED,
        }
        assert events[1].source_event_id == outcome_changed_source_event_id(
            outcome_id=outcome.id,
            previous_status=STATUS_CREATED,
            new_status=STATUS_ACTIVE,
        )

        # Idempotent re-apply while still active: no extra OutcomeChanged rows.
        outcome, _link, applied_again = await apply_attribution_to_outcome(
            db,
            tenant_id=tenant_id,
            outcome_id=outcome.id,
            attribution_id=attr_id,
        )
        assert applied_again is False
        again = await list_activity_events(
            db,
            tenant_id=tenant_id,
            outcome_id=outcome.id,
            event_types=["OutcomeChanged"],
        )
        assert len(again) == 2

        # Second distinct result completes the Outcome.
        attr2 = await _seed_attribution(
            db, tenant_id=tenant_id, campaign_id=camp.id, flight_id=flight_id
        )
        outcome, _link, applied2 = await apply_attribution_to_outcome(
            db,
            tenant_id=tenant_id,
            outcome_id=outcome.id,
            attribution_id=attr2,
        )
        assert applied2 is True
        assert outcome.status == STATUS_COMPLETED
        final = await list_activity_events(
            db,
            tenant_id=tenant_id,
            outcome_id=outcome.id,
            event_types=["OutcomeChanged"],
        )
        assert [e.payload.get("status") for e in final] == [
            STATUS_CREATED,
            STATUS_ACTIVE,
            STATUS_COMPLETED,
        ]
        assert final[-1].payload == {
            "status": STATUS_COMPLETED,
            "previous_status": STATUS_ACTIVE,
        }
        await db.commit()


@pytest.mark.asyncio
async def test_mark_failed_and_cancelled_emit_outcome_changed() -> None:
    data = await _init_data()
    tenant_id = data["tenant_id"]

    async with async_session_maker() as db:
        camp, flight_id = await _seed_campaign_flight(db, tenant_id=tenant_id)
        # failed is only legal from active — activate via attribution first.
        failed = await create_outcome(
            db,
            tenant_id=tenant_id,
            campaign_id=camp.id,
            flight_id=flight_id,
            progress_target=2,
        )
        attr_id = await _seed_attribution(
            db, tenant_id=tenant_id, campaign_id=camp.id, flight_id=flight_id
        )
        await apply_attribution_to_outcome(
            db,
            tenant_id=tenant_id,
            outcome_id=failed.id,
            attribution_id=attr_id,
        )
        await mark_outcome_failed(db, tenant_id=tenant_id, outcome_id=failed.id)

        cancelled = await create_outcome(
            db,
            tenant_id=tenant_id,
            campaign_id=camp.id,
            flight_id=flight_id,
        )
        await mark_outcome_cancelled(
            db, tenant_id=tenant_id, outcome_id=cancelled.id
        )

        failed_events = await list_activity_events(
            db,
            tenant_id=tenant_id,
            outcome_id=failed.id,
            event_types=["OutcomeChanged"],
        )
        assert [e.payload["status"] for e in failed_events] == [
            STATUS_CREATED,
            STATUS_ACTIVE,
            STATUS_FAILED,
        ]
        assert failed_events[-1].payload["previous_status"] == STATUS_ACTIVE

        cancelled_events = await list_activity_events(
            db,
            tenant_id=tenant_id,
            outcome_id=cancelled.id,
            event_types=["OutcomeChanged"],
        )
        assert [e.payload["status"] for e in cancelled_events] == [
            STATUS_CREATED,
            STATUS_CANCELLED,
        ]
        await db.commit()


@pytest.mark.asyncio
async def test_outcome_changed_rollback_drops_activity() -> None:
    data = await _init_data()
    tenant_id = data["tenant_id"]

    async with async_session_maker() as db:
        camp, flight_id = await _seed_campaign_flight(db, tenant_id=tenant_id)
        await db.commit()
        campaign_id = camp.id

    async with async_session_maker() as db:
        await create_outcome(
            db,
            tenant_id=tenant_id,
            campaign_id=campaign_id,
            flight_id=flight_id,
        )
        await db.rollback()

    async with async_session_maker() as db:
        rows = await list_activity_events(
            db,
            tenant_id=tenant_id,
            campaign_id=campaign_id,
            event_types=["OutcomeChanged"],
        )
        assert rows == []
        count = await db.execute(
            text(
                "SELECT count(*) FROM acquisition_activity_events "
                "WHERE tenant_id = :t AND event_type = 'OutcomeChanged' "
                "AND campaign_id = :c"
            ),
            {"t": tenant_id, "c": campaign_id},
        )
        assert count.scalar() == 0
