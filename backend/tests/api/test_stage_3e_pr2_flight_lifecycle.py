"""Stage 3E PR-2 — Flight lifecycle instrumentation via transition service."""

from __future__ import annotations

import ast
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import select, text

from backend.app.acquisition.activity import list_activity_events
from backend.app.acquisition.activity.repository import get_by_source_event_id
from backend.app.acquisition.flights import lifecycle as flight_lifecycle
from backend.app.acquisition.flights.lifecycle import (
    FLIGHT_STATUS_ACTIVE,
    FLIGHT_STATUS_COMPLETED,
    FLIGHT_STATUS_PAUSED,
    FLIGHT_STATUS_PLANNED,
    FlightLifecycleError,
    create_flight,
    flight_lifecycle_source_event_id,
    transition_flight_status,
)
from backend.app.db.session import async_session_maker
from backend.app.models.acquisition_activity_event import (
    ACTOR_TYPE_SYSTEM,
    ACTOR_TYPE_USER,
)
from backend.app.models.campaign import Campaign, CampaignRun
from backend.app.models.own_company import OwnCompany
from backend.app.models.tenant import Tenant
from backend.tests.conftest import _init_data

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


async def _seed_campaign_shell(db, *, tenant_id: str) -> Campaign:
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
    return campaign


def test_lifecycle_module_writes_only_via_append_activity_event() -> None:
    src = _LIFECYCLE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(src)
    assert "append_activity_event" in src
    assert "AcquisitionActivityEvent(" not in src
    banned_adds = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr == "add" and isinstance(node.func.value, ast.Name):
                # db.add(flight) is allowed; db.add(AcquisitionActivityEvent) is not.
                if node.args and isinstance(node.args[0], ast.Call):
                    callee = node.args[0].func
                    name = getattr(callee, "id", None) or getattr(
                        getattr(callee, "attr", None), "attr", None
                    )
                    if name == "AcquisitionActivityEvent":
                        banned_adds.append(node.lineno)
    assert banned_adds == []
    assert "db.add(row)" not in src


@pytest.mark.asyncio
async def test_successful_transitions_emit_one_event_each() -> None:
    data = await _init_data()
    tenant_id = data["tenant_id"]
    t0 = datetime(2026, 7, 21, 10, 0, tzinfo=timezone.utc)

    async with async_session_maker() as db:
        camp = await _seed_campaign_shell(db, tenant_id=tenant_id)
        flight, created = await create_flight(
            db,
            tenant_id=tenant_id,
            campaign_id=camp.id,
            actor_type=ACTOR_TYPE_USER,
            actor_id="user-ops-1",
            occurred_at=t0,
        )
        camp.current_flight_id = flight.id
        await db.flush()

        assert created.event_type == "FlightCreated"
        assert created.source_event_id == flight_lifecycle_source_event_id(flight.id, 1)
        assert created.payload == {"new_status": FLIGHT_STATUS_PLANNED}
        assert created.actor_type == ACTOR_TYPE_USER
        assert created.actor_id == "user-ops-1"
        assert flight.status == FLIGHT_STATUS_PLANNED

        started = await transition_flight_status(
            db,
            flight=flight,
            new_status=FLIGHT_STATUS_ACTIVE,
            actor_type=ACTOR_TYPE_USER,
            actor_id="user-ops-1",
            occurred_at=t0 + timedelta(minutes=1),
            reason="launch",
        )
        assert started.event_type == "FlightStarted"
        assert started.payload == {
            "previous_status": FLIGHT_STATUS_PLANNED,
            "new_status": FLIGHT_STATUS_ACTIVE,
            "reason": "launch",
        }
        assert flight.status == FLIGHT_STATUS_ACTIVE

        paused = await transition_flight_status(
            db,
            flight=flight,
            new_status=FLIGHT_STATUS_PAUSED,
            actor_type=ACTOR_TYPE_SYSTEM,
            actor_id=None,
            occurred_at=t0 + timedelta(minutes=2),
        )
        assert paused.event_type == "FlightPaused"
        assert paused.actor_type == ACTOR_TYPE_SYSTEM
        assert flight.status == FLIGHT_STATUS_PAUSED

        resumed = await transition_flight_status(
            db,
            flight=flight,
            new_status=FLIGHT_STATUS_ACTIVE,
            actor_type=ACTOR_TYPE_SYSTEM,
            occurred_at=t0 + timedelta(minutes=3),
        )
        assert resumed.event_type == "FlightResumed"

        completed = await transition_flight_status(
            db,
            flight=flight,
            new_status=FLIGHT_STATUS_COMPLETED,
            actor_type=ACTOR_TYPE_USER,
            actor_id="user-ops-1",
            occurred_at=t0 + timedelta(minutes=4),
        )
        assert completed.event_type == "FlightCompleted"
        assert flight.status == FLIGHT_STATUS_COMPLETED

        rows = await list_activity_events(
            db, tenant_id=tenant_id, flight_id=flight.id
        )
        assert [r.event_type for r in rows] == [
            "FlightCreated",
            "FlightStarted",
            "FlightPaused",
            "FlightResumed",
            "FlightCompleted",
        ]
        assert [r.source_event_id for r in rows] == [
            flight_lifecycle_source_event_id(flight.id, n) for n in range(1, 6)
        ]
        count = await db.execute(
            text(
                "SELECT count(*) FROM acquisition_activity_events "
                "WHERE tenant_id = :t AND flight_id = :f"
            ),
            {"t": tenant_id, "f": flight.id},
        )
        assert count.scalar() == 5
        await db.commit()


@pytest.mark.asyncio
async def test_rollback_emits_zero_events() -> None:
    data = await _init_data()
    tenant_id = data["tenant_id"]

    async with async_session_maker() as db:
        camp = await _seed_campaign_shell(db, tenant_id=tenant_id)
        flight, _ = await create_flight(
            db,
            tenant_id=tenant_id,
            campaign_id=camp.id,
            actor_type=ACTOR_TYPE_SYSTEM,
        )
        await db.commit()
        flight_id = flight.id

    async with async_session_maker() as db:
        flight = await db.get(CampaignRun, flight_id)
        assert flight is not None
        await transition_flight_status(
            db,
            flight=flight,
            new_status=FLIGHT_STATUS_ACTIVE,
            actor_type=ACTOR_TYPE_SYSTEM,
        )
        await db.rollback()

    async with async_session_maker() as db:
        rows = await list_activity_events(
            db, tenant_id=tenant_id, flight_id=flight_id
        )
        assert [r.event_type for r in rows] == ["FlightCreated"]
        flight = await db.get(CampaignRun, flight_id)
        assert flight is not None
        assert flight.status == FLIGHT_STATUS_PLANNED


@pytest.mark.asyncio
async def test_retry_returns_same_event() -> None:
    data = await _init_data()
    tenant_id = data["tenant_id"]

    async with async_session_maker() as db:
        camp = await _seed_campaign_shell(db, tenant_id=tenant_id)
        flight, created = await create_flight(
            db,
            tenant_id=tenant_id,
            campaign_id=camp.id,
            actor_type=ACTOR_TYPE_SYSTEM,
        )
        first = await transition_flight_status(
            db,
            flight=flight,
            new_status=FLIGHT_STATUS_ACTIVE,
            actor_type=ACTOR_TYPE_SYSTEM,
        )
        second = await transition_flight_status(
            db,
            flight=flight,
            new_status=FLIGHT_STATUS_ACTIVE,
            actor_type=ACTOR_TYPE_USER,
            actor_id="should-not-change",
        )
        assert second.id == first.id
        assert second.source_event_id == first.source_event_id
        assert second.actor_type == ACTOR_TYPE_SYSTEM
        assert first.id != created.id

        # create retry via same source key returns same FlightCreated
        again = await get_by_source_event_id(
            db,
            tenant_id=tenant_id,
            source_event_id=flight_lifecycle_source_event_id(flight.id, 1),
        )
        assert again is not None and again.id == created.id

        count = await db.execute(
            text(
                "SELECT count(*) FROM acquisition_activity_events "
                "WHERE tenant_id = :t AND flight_id = :f"
            ),
            {"t": tenant_id, "f": flight.id},
        )
        assert count.scalar() == 2
        await db.commit()


@pytest.mark.asyncio
async def test_tenant_isolation_for_lifecycle_events() -> None:
    data = await _init_data()
    tenant_a = data["tenant_id"]
    tenant_b = str(uuid4())

    async with async_session_maker() as db:
        camp_a = await _seed_campaign_shell(db, tenant_id=tenant_a)
        camp_b = await _seed_campaign_shell(db, tenant_id=tenant_b)
        flight_a, _ = await create_flight(
            db,
            tenant_id=tenant_a,
            campaign_id=camp_a.id,
            actor_type=ACTOR_TYPE_SYSTEM,
        )
        flight_b, _ = await create_flight(
            db,
            tenant_id=tenant_b,
            campaign_id=camp_b.id,
            actor_type=ACTOR_TYPE_SYSTEM,
        )
        await transition_flight_status(
            db,
            flight=flight_a,
            new_status=FLIGHT_STATUS_ACTIVE,
            actor_type=ACTOR_TYPE_SYSTEM,
        )
        rows_a = await list_activity_events(db, tenant_id=tenant_a, flight_id=flight_a.id)
        rows_b = await list_activity_events(db, tenant_id=tenant_b, flight_id=flight_b.id)
        assert all(r.tenant_id == tenant_a for r in rows_a)
        assert all(r.tenant_id == tenant_b for r in rows_b)
        assert not ({r.id for r in rows_a} & {r.id for r in rows_b})
        cross = await list_activity_events(db, tenant_id=tenant_b, flight_id=flight_a.id)
        assert cross == []
        await db.commit()


@pytest.mark.asyncio
async def test_manual_and_system_actors() -> None:
    data = await _init_data()
    tenant_id = data["tenant_id"]

    async with async_session_maker() as db:
        camp = await _seed_campaign_shell(db, tenant_id=tenant_id)
        flight, created = await create_flight(
            db,
            tenant_id=tenant_id,
            campaign_id=camp.id,
            actor_type=ACTOR_TYPE_USER,
            actor_id="manual-user-9",
        )
        assert created.actor_type == ACTOR_TYPE_USER
        assert created.actor_id == "manual-user-9"

        started = await transition_flight_status(
            db,
            flight=flight,
            new_status=FLIGHT_STATUS_ACTIVE,
            actor_type=ACTOR_TYPE_SYSTEM,
            actor_id=None,
        )
        assert started.actor_type == ACTOR_TYPE_SYSTEM
        assert started.actor_id is None
        await db.commit()


@pytest.mark.asyncio
async def test_event_order_preserved_across_lifecycle() -> None:
    data = await _init_data()
    tenant_id = data["tenant_id"]
    t0 = datetime(2026, 7, 21, 12, 0, tzinfo=timezone.utc)

    async with async_session_maker() as db:
        camp = await _seed_campaign_shell(db, tenant_id=tenant_id)
        flight, _ = await create_flight(
            db,
            tenant_id=tenant_id,
            campaign_id=camp.id,
            actor_type=ACTOR_TYPE_SYSTEM,
            occurred_at=t0,
        )
        await transition_flight_status(
            db,
            flight=flight,
            new_status=FLIGHT_STATUS_ACTIVE,
            actor_type=ACTOR_TYPE_SYSTEM,
            occurred_at=t0 + timedelta(seconds=10),
        )
        await transition_flight_status(
            db,
            flight=flight,
            new_status=FLIGHT_STATUS_PAUSED,
            actor_type=ACTOR_TYPE_SYSTEM,
            occurred_at=t0 + timedelta(seconds=20),
        )
        await transition_flight_status(
            db,
            flight=flight,
            new_status=FLIGHT_STATUS_ACTIVE,
            actor_type=ACTOR_TYPE_SYSTEM,
            occurred_at=t0 + timedelta(seconds=30),
        )
        await transition_flight_status(
            db,
            flight=flight,
            new_status=FLIGHT_STATUS_COMPLETED,
            actor_type=ACTOR_TYPE_SYSTEM,
            occurred_at=t0 + timedelta(seconds=40),
        )
        rows = await list_activity_events(db, tenant_id=tenant_id, flight_id=flight.id)
        occurred = [r.occurred_at for r in rows]
        assert occurred == sorted(occurred)
        assert [r.event_type for r in rows] == [
            "FlightCreated",
            "FlightStarted",
            "FlightPaused",
            "FlightResumed",
            "FlightCompleted",
        ]
        await db.commit()


@pytest.mark.asyncio
async def test_unsupported_transition_and_flight_failed_not_invented() -> None:
    data = await _init_data()
    tenant_id = data["tenant_id"]

    async with async_session_maker() as db:
        camp = await _seed_campaign_shell(db, tenant_id=tenant_id)
        flight, _ = await create_flight(
            db,
            tenant_id=tenant_id,
            campaign_id=camp.id,
            actor_type=ACTOR_TYPE_SYSTEM,
        )
        with pytest.raises(FlightLifecycleError, match="unsupported flight transition"):
            await transition_flight_status(
                db,
                flight=flight,
                new_status="failed",
                actor_type=ACTOR_TYPE_SYSTEM,
                reason="boom",
            )
        assert flight.status == FLIGHT_STATUS_PLANNED
        rows = await list_activity_events(db, tenant_id=tenant_id, flight_id=flight.id)
        assert [r.event_type for r in rows] == ["FlightCreated"]
        await db.commit()


@pytest.mark.asyncio
async def test_create_campaign_emits_flight_created() -> None:
    from backend.app.acquisition.campaign_service import create_campaign
    from backend.app.auth.deps import UserCtx

    data = await _init_data()
    tenant_id = data["tenant_id"]
    user_id = data["admin_id"]

    async with async_session_maker() as db:
        oc = await _own_company_id(db, tenant_id)
        ctx = UserCtx(
            sub=user_id,
            email=data["admin_email"],
            role="administrator",
            tenant_id=tenant_id,
            supervisor_id=None,
            raw={},
        )
        campaign = await create_campaign(
            db,
            tenant_id=tenant_id,
            ctx=ctx,
            own_company_id=oc,
            name=f"Lifecycle Camp {uuid4().hex[:6]}",
            goal_type="hiring",
            primary_kpi="hires",
        )
        flight_id = campaign.current_flight_id
        assert flight_id
        rows = await list_activity_events(
            db, tenant_id=tenant_id, flight_id=str(flight_id)
        )
        assert len(rows) == 1
        assert rows[0].event_type == "FlightCreated"
        assert rows[0].campaign_id == campaign.id
        assert rows[0].flight_id == flight_id
        assert rows[0].actor_type == ACTOR_TYPE_USER
        assert rows[0].actor_id == user_id
        assert rows[0].payload["new_status"] == FLIGHT_STATUS_PLANNED
        assert "provider" not in rows[0].payload
        await db.commit()
