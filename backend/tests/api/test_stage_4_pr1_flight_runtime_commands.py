"""Stage 4 PR-1 — Flight Runtime command service + Campaign coupling."""

from __future__ import annotations

import ast
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import select

from backend.app.acquisition.activity import list_activity_events
from backend.app.acquisition.flights import lifecycle as flight_lifecycle
from backend.app.acquisition.flights import runtime_commands as runtime_commands_mod
from backend.app.acquisition.flights.lifecycle import (
    FLIGHT_STATUS_ACTIVE,
    FLIGHT_STATUS_COMPLETED,
    FLIGHT_STATUS_PAUSED,
    FLIGHT_STATUS_PLANNED,
    create_flight,
)
from backend.app.acquisition.flights.runtime_commands import (
    FlightRuntimeError,
    execute_flight_command,
    update_flight_metadata,
)
from backend.app.acquisition.submission_routing import is_flight_routing_eligible
from backend.app.db.session import async_session_maker
from backend.app.models.acquisition_activity_event import ACTOR_TYPE_USER
from backend.app.models.campaign import Campaign
from backend.app.models.own_company import OwnCompany
from backend.app.models.tenant import Tenant
from backend.tests.conftest import _init_data

_RUNTIME_PATH = Path(runtime_commands_mod.__file__)
_LIFECYCLE_PATH = Path(flight_lifecycle.__file__)


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


async def _seed_draft_campaign_with_flight(db, *, tenant_id: str) -> tuple[Campaign, str]:
    await _ensure_tenant(db, tenant_id)
    oc = await _own_company_id(db, tenant_id)
    flight_id = str(uuid4())
    campaign = Campaign(
        id=str(uuid4()),
        tenant_id=tenant_id,
        own_company_id=oc,
        name=f"Campaign {uuid4().hex[:6]}",
        status="draft",
        goal_type="hiring",
        primary_kpi="hires",
        current_flight_id=flight_id,
    )
    db.add(campaign)
    await db.flush()
    flight, _ = await create_flight(
        db,
        tenant_id=tenant_id,
        campaign_id=campaign.id,
        flight_id=flight_id,
        actor_type=ACTOR_TYPE_USER,
        actor_id="user-1",
    )
    assert flight.status == FLIGHT_STATUS_PLANNED
    await db.flush()
    return campaign, flight_id


def test_runtime_commands_delegate_status_writes_to_lifecycle() -> None:
    src = _RUNTIME_PATH.read_text(encoding="utf-8")
    tree = ast.parse(src)
    assert "transition_flight_status" in src
    assert "append_activity_event" in src
    # Must not assign flight.status directly.
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Attribute) and target.attr == "status":
                    # campaign.status sync is allowed; flight.status is not.
                    if isinstance(target.value, ast.Name) and target.value.id == "flight":
                        raise AssertionError(
                            f"direct flight.status write at line {node.lineno}"
                        )
    assert "FlightCancelled" not in src
    assert '"cancel"' not in src


@pytest.mark.asyncio
async def test_launch_couples_campaign_active_and_emits_campaign_activated() -> None:
    data = await _init_data()
    tenant_id = data["tenant_id"]

    async with async_session_maker() as db:
        campaign, flight_id = await _seed_draft_campaign_with_flight(db, tenant_id=tenant_id)
        result = await execute_flight_command(
            db,
            tenant_id=tenant_id,
            campaign_id=campaign.id,
            flight_id=flight_id,
            command="launch",
            actor_type=ACTOR_TYPE_USER,
            actor_id="ops-1",
            reason="go-live",
        )
        await db.commit()

        assert result.flight.status == FLIGHT_STATUS_ACTIVE
        assert result.campaign.status == "active"
        assert result.flight_event.event_type == "FlightStarted"
        assert result.campaign_event is not None
        assert result.campaign_event.event_type == "CampaignActivated"
        assert is_flight_routing_eligible(
            association_is_active=True,
            campaign_status=result.campaign.status,
            flight_status=result.flight.status,
            starts_at=None,
            ends_at=None,
        )

        events = await list_activity_events(
            db, tenant_id=tenant_id, campaign_id=campaign.id, limit=50
        )
        types = [e.event_type for e in events]
        assert types.count("FlightStarted") == 1
        assert types.count("CampaignActivated") == 1


@pytest.mark.asyncio
async def test_pause_couples_campaign_paused() -> None:
    data = await _init_data()
    tenant_id = data["tenant_id"]

    async with async_session_maker() as db:
        campaign, flight_id = await _seed_draft_campaign_with_flight(db, tenant_id=tenant_id)
        await execute_flight_command(
            db,
            tenant_id=tenant_id,
            campaign_id=campaign.id,
            flight_id=flight_id,
            command="launch",
            actor_type=ACTOR_TYPE_USER,
            actor_id="ops-1",
        )
        paused = await execute_flight_command(
            db,
            tenant_id=tenant_id,
            campaign_id=campaign.id,
            flight_id=flight_id,
            command="pause",
            actor_type=ACTOR_TYPE_USER,
            actor_id="ops-1",
        )
        await db.commit()

        assert paused.flight.status == FLIGHT_STATUS_PAUSED
        assert paused.campaign.status == "paused"
        assert paused.campaign_event is not None
        assert paused.campaign_event.event_type == "CampaignPaused"
        assert not is_flight_routing_eligible(
            association_is_active=True,
            campaign_status=paused.campaign.status,
            flight_status=paused.flight.status,
            starts_at=None,
            ends_at=None,
        )


@pytest.mark.asyncio
async def test_resume_reactivates_campaign() -> None:
    data = await _init_data()
    tenant_id = data["tenant_id"]

    async with async_session_maker() as db:
        campaign, flight_id = await _seed_draft_campaign_with_flight(db, tenant_id=tenant_id)
        await execute_flight_command(
            db,
            tenant_id=tenant_id,
            campaign_id=campaign.id,
            flight_id=flight_id,
            command="launch",
            actor_type=ACTOR_TYPE_USER,
            actor_id="ops-1",
        )
        await execute_flight_command(
            db,
            tenant_id=tenant_id,
            campaign_id=campaign.id,
            flight_id=flight_id,
            command="pause",
            actor_type=ACTOR_TYPE_USER,
            actor_id="ops-1",
        )
        resumed = await execute_flight_command(
            db,
            tenant_id=tenant_id,
            campaign_id=campaign.id,
            flight_id=flight_id,
            command="resume",
            actor_type=ACTOR_TYPE_USER,
            actor_id="ops-1",
        )
        await db.commit()

        assert resumed.flight.status == FLIGHT_STATUS_ACTIVE
        assert resumed.campaign.status == "active"
        assert resumed.flight_event.event_type == "FlightResumed"
        assert resumed.campaign_event is not None
        assert resumed.campaign_event.event_type == "CampaignActivated"


@pytest.mark.asyncio
async def test_complete_does_not_change_campaign_status() -> None:
    data = await _init_data()
    tenant_id = data["tenant_id"]

    async with async_session_maker() as db:
        campaign, flight_id = await _seed_draft_campaign_with_flight(db, tenant_id=tenant_id)
        await execute_flight_command(
            db,
            tenant_id=tenant_id,
            campaign_id=campaign.id,
            flight_id=flight_id,
            command="launch",
            actor_type=ACTOR_TYPE_USER,
            actor_id="ops-1",
        )
        completed = await execute_flight_command(
            db,
            tenant_id=tenant_id,
            campaign_id=campaign.id,
            flight_id=flight_id,
            command="complete",
            actor_type=ACTOR_TYPE_USER,
            actor_id="ops-1",
        )
        await db.commit()

        assert completed.flight.status == FLIGHT_STATUS_COMPLETED
        assert completed.campaign.status == "active"
        assert completed.campaign_event is None
        assert completed.flight_event.event_type == "FlightCompleted"

        events = await list_activity_events(
            db, tenant_id=tenant_id, campaign_id=campaign.id, limit=50
        )
        assert "CampaignCompleted" not in {e.event_type for e in events}


@pytest.mark.asyncio
async def test_launch_idempotent_retry_no_duplicate_campaign_event() -> None:
    data = await _init_data()
    tenant_id = data["tenant_id"]

    async with async_session_maker() as db:
        campaign, flight_id = await _seed_draft_campaign_with_flight(db, tenant_id=tenant_id)
        first = await execute_flight_command(
            db,
            tenant_id=tenant_id,
            campaign_id=campaign.id,
            flight_id=flight_id,
            command="launch",
            actor_type=ACTOR_TYPE_USER,
            actor_id="ops-1",
        )
        second = await execute_flight_command(
            db,
            tenant_id=tenant_id,
            campaign_id=campaign.id,
            flight_id=flight_id,
            command="launch",
            actor_type=ACTOR_TYPE_USER,
            actor_id="ops-1",
        )
        await db.commit()

        assert first.flight_event.id == second.flight_event.id
        assert second.campaign_event is None
        assert second.campaign.status == "active"

        events = await list_activity_events(
            db, tenant_id=tenant_id, campaign_id=campaign.id, limit=50
        )
        assert [e.event_type for e in events].count("CampaignActivated") == 1
        assert [e.event_type for e in events].count("FlightStarted") == 1


@pytest.mark.asyncio
async def test_illegal_transition_rejected_and_campaign_untouched() -> None:
    data = await _init_data()
    tenant_id = data["tenant_id"]

    async with async_session_maker() as db:
        campaign, flight_id = await _seed_draft_campaign_with_flight(db, tenant_id=tenant_id)
        await db.commit()
        campaign_id = campaign.id

    async with async_session_maker() as db:
        with pytest.raises(FlightRuntimeError, match="unsupported flight transition"):
            await execute_flight_command(
                db,
                tenant_id=tenant_id,
                campaign_id=campaign_id,
                flight_id=flight_id,
                command="pause",
                actor_type=ACTOR_TYPE_USER,
                actor_id="ops-1",
            )
        await db.rollback()

    async with async_session_maker() as db:
        camp = await db.get(Campaign, campaign_id)
        assert camp is not None
        assert camp.status == "draft"


@pytest.mark.asyncio
async def test_rollback_drops_flight_and_campaign_coupling() -> None:
    data = await _init_data()
    tenant_id = data["tenant_id"]

    async with async_session_maker() as db:
        campaign, flight_id = await _seed_draft_campaign_with_flight(db, tenant_id=tenant_id)
        await db.commit()
        campaign_id = campaign.id

    async with async_session_maker() as db:
        await execute_flight_command(
            db,
            tenant_id=tenant_id,
            campaign_id=campaign_id,
            flight_id=flight_id,
            command="launch",
            actor_type=ACTOR_TYPE_USER,
            actor_id="ops-1",
        )
        await db.rollback()

    async with async_session_maker() as db:
        camp = await db.get(Campaign, campaign_id)
        assert camp is not None
        assert camp.status == "draft"
        events = await list_activity_events(
            db, tenant_id=tenant_id, campaign_id=campaign_id, limit=50
        )
        types = {e.event_type for e in events}
        assert "FlightStarted" not in types
        assert "CampaignActivated" not in types
        assert "FlightCreated" in types


@pytest.mark.asyncio
async def test_metadata_update_rejects_window_inversion() -> None:
    data = await _init_data()
    tenant_id = data["tenant_id"]
    t0 = datetime(2026, 7, 21, 12, 0, tzinfo=timezone.utc)

    async with async_session_maker() as db:
        campaign, flight_id = await _seed_draft_campaign_with_flight(db, tenant_id=tenant_id)
        with pytest.raises(FlightRuntimeError, match="ends_at"):
            await update_flight_metadata(
                db,
                tenant_id=tenant_id,
                campaign_id=campaign.id,
                flight_id=flight_id,
                starts_at=t0,
                ends_at=t0.replace(hour=10),
            )


def test_cancel_not_in_lifecycle_or_runtime_matrix() -> None:
    life = _LIFECYCLE_PATH.read_text(encoding="utf-8")
    runtime = _RUNTIME_PATH.read_text(encoding="utf-8")
    assert "FlightCancelled" not in life
    assert '"cancel"' not in runtime
    assert "launch" in runtime and "complete" in runtime
