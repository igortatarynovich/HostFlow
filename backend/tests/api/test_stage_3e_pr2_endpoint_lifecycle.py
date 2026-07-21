"""Stage 3E PR-2 — Endpoint association instrumentation via binding_service."""

from __future__ import annotations

import ast
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import select, text

from backend.app.acquisition import binding_service, endpoint_activity
from backend.app.acquisition.activity import list_activity_events
from backend.app.acquisition.activity.repository import get_by_source_event_id
from backend.app.acquisition.endpoint_activity import (
    CHANGE_KIND_ATTACHED,
    CHANGE_KIND_DETACHED,
    CHANGE_KIND_UPDATED,
    endpoint_source_event_id,
    form_endpoint_id,
    intake_source_endpoint_id,
)
from backend.app.acquisition.flights.lifecycle import create_flight
from backend.app.db.session import async_session_maker
from backend.app.models.acquisition_activity_event import (
    ACTOR_TYPE_SYSTEM,
    ACTOR_TYPE_USER,
)
from backend.app.models.campaign import Campaign, CampaignRunForm
from backend.app.models.intake_routing import IntakeSourceProfile
from backend.app.models.own_company import OwnCompany
from backend.app.models.tenant import Tenant
from backend.app.models.tenant_lead_form import TenantLeadForm
from backend.tests.conftest import _init_data

_BINDING_PATH = Path(binding_service.__file__)
_ENDPOINT_ACTIVITY_PATH = Path(endpoint_activity.__file__)


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
    campaign.current_flight_id = flight.id
    await db.flush()
    return campaign, flight.id


async def _seed_form(db, *, tenant_id: str) -> str:
    form_id = str(uuid4())
    db.add(
        TenantLeadForm(
            id=form_id,
            tenant_id=tenant_id,
            title=f"Form {form_id[:6]}",
            public_slug=f"form-{form_id[:8]}",
            is_active=True,
            lifecycle_status="active",
            purpose="inquiry",
        )
    )
    await db.flush()
    return form_id


async def _seed_intake_source(db, *, tenant_id: str, own_company_id: str) -> str:
    profile_id = str(uuid4())
    db.add(
        IntakeSourceProfile(
            id=profile_id,
            tenant_id=tenant_id,
            code=f"src-{profile_id[:8]}",
            name="Website intake",
            provider="public_intake",
            channel="organic",
            own_company_id=own_company_id,
            route_intent="candidate_application",
            is_active=True,
        )
    )
    await db.flush()
    return profile_id


def test_endpoint_instrumentation_writes_only_via_append() -> None:
    for path in (_BINDING_PATH, _ENDPOINT_ACTIVITY_PATH):
        src = path.read_text(encoding="utf-8")
        assert "append_activity_event" in src or path == _BINDING_PATH
        assert "AcquisitionActivityEvent(" not in src
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            name = getattr(func, "id", None) or getattr(func, "attr", None)
            if name == "AcquisitionActivityEvent":
                raise AssertionError(f"raw model construct in {path}:{node.lineno}")


@pytest.mark.asyncio
async def test_attach_form_emits_endpoint_changed() -> None:
    data = await _init_data()
    tenant_id = data["tenant_id"]

    async with async_session_maker() as db:
        camp, flight_id = await _seed_campaign_flight(db, tenant_id=tenant_id)
        form_id = await _seed_form(db, tenant_id=tenant_id)
        await binding_service.attach_form(
            db,
            tenant_id=tenant_id,
            campaign_id=camp.id,
            form_id=form_id,
            actor_type=ACTOR_TYPE_USER,
            actor_id="user-bind-1",
        )
        rows = await list_activity_events(
            db,
            tenant_id=tenant_id,
            flight_id=flight_id,
            event_types=["EndpointChanged"],
        )
        assert len(rows) == 1
        ev = rows[0]
        assert ev.endpoint_id == form_endpoint_id(form_id)
        assert ev.payload == {
            "endpoint_id": form_endpoint_id(form_id),
            "change_kind": CHANGE_KIND_ATTACHED,
        }
        assert ev.actor_type == ACTOR_TYPE_USER
        assert ev.actor_id == "user-bind-1"
        assert ev.provider is None
        link = (
            await db.execute(
                select(CampaignRunForm).where(
                    CampaignRunForm.campaign_run_id == flight_id,
                    CampaignRunForm.form_id == form_id,
                )
            )
        ).scalar_one()
        assert ev.source_event_id == endpoint_source_event_id(
            link.id, CHANGE_KIND_ATTACHED
        )
        await db.commit()


@pytest.mark.asyncio
async def test_update_and_detach_form_emit_and_idempotent_update() -> None:
    data = await _init_data()
    tenant_id = data["tenant_id"]

    async with async_session_maker() as db:
        camp, flight_id = await _seed_campaign_flight(db, tenant_id=tenant_id)
        form_id = await _seed_form(db, tenant_id=tenant_id)
        await binding_service.attach_form(
            db,
            tenant_id=tenant_id,
            campaign_id=camp.id,
            form_id=form_id,
            actor_type=ACTOR_TYPE_SYSTEM,
        )
        link = (
            await db.execute(
                select(CampaignRunForm).where(
                    CampaignRunForm.campaign_run_id == flight_id,
                    CampaignRunForm.form_id == form_id,
                )
            )
        ).scalar_one()

        await binding_service.update_form_link(
            db,
            tenant_id=tenant_id,
            campaign_id=camp.id,
            link_id=link.id,
            is_active=False,
            actor_type=ACTOR_TYPE_SYSTEM,
        )
        # no-op update → no extra event
        await binding_service.update_form_link(
            db,
            tenant_id=tenant_id,
            campaign_id=camp.id,
            link_id=link.id,
            is_active=False,
            actor_type=ACTOR_TYPE_USER,
            actor_id="noop",
        )
        updated = await get_by_source_event_id(
            db,
            tenant_id=tenant_id,
            source_event_id=endpoint_source_event_id(
                link.id, CHANGE_KIND_UPDATED, suffix="0:primary"
            ),
        )
        assert updated is not None
        assert updated.payload["change_kind"] == CHANGE_KIND_UPDATED

        await binding_service.detach_form(
            db,
            tenant_id=tenant_id,
            campaign_id=camp.id,
            link_id=link.id,
            actor_type=ACTOR_TYPE_SYSTEM,
        )
        rows = await list_activity_events(
            db,
            tenant_id=tenant_id,
            flight_id=flight_id,
            event_types=["EndpointChanged"],
        )
        assert [r.payload["change_kind"] for r in rows] == [
            CHANGE_KIND_ATTACHED,
            CHANGE_KIND_UPDATED,
            CHANGE_KIND_DETACHED,
        ]
        await db.commit()


@pytest.mark.asyncio
async def test_rollback_drops_endpoint_event() -> None:
    data = await _init_data()
    tenant_id = data["tenant_id"]

    async with async_session_maker() as db:
        camp, flight_id = await _seed_campaign_flight(db, tenant_id=tenant_id)
        form_id = await _seed_form(db, tenant_id=tenant_id)
        await db.commit()

    async with async_session_maker() as db:
        await binding_service.attach_form(
            db,
            tenant_id=tenant_id,
            campaign_id=camp.id,
            form_id=form_id,
            actor_type=ACTOR_TYPE_SYSTEM,
        )
        await db.rollback()

    async with async_session_maker() as db:
        rows = await list_activity_events(
            db,
            tenant_id=tenant_id,
            flight_id=flight_id,
            event_types=["EndpointChanged"],
        )
        assert rows == []
        count = await db.execute(
            text(
                "SELECT count(*) FROM acq_campaign_run_forms "
                "WHERE campaign_run_id = :f AND form_id = :form"
            ),
            {"f": flight_id, "form": form_id},
        )
        assert count.scalar() == 0


@pytest.mark.asyncio
async def test_intake_source_attach_and_tenant_isolation() -> None:
    data = await _init_data()
    tenant_a = data["tenant_id"]
    tenant_b = str(uuid4())

    async with async_session_maker() as db:
        camp_a, flight_a = await _seed_campaign_flight(db, tenant_id=tenant_a)
        camp_b, flight_b = await _seed_campaign_flight(db, tenant_id=tenant_b)
        profile_a = await _seed_intake_source(
            db, tenant_id=tenant_a, own_company_id=camp_a.own_company_id
        )
        profile_b = await _seed_intake_source(
            db, tenant_id=tenant_b, own_company_id=camp_b.own_company_id
        )
        await binding_service.attach_intake_source(
            db,
            tenant_id=tenant_a,
            campaign_id=camp_a.id,
            intake_source_profile_id=profile_a,
            actor_type=ACTOR_TYPE_SYSTEM,
        )
        await binding_service.attach_intake_source(
            db,
            tenant_id=tenant_b,
            campaign_id=camp_b.id,
            intake_source_profile_id=profile_b,
            actor_type=ACTOR_TYPE_SYSTEM,
        )
        rows_a = await list_activity_events(
            db, tenant_id=tenant_a, flight_id=flight_a, event_types=["EndpointChanged"]
        )
        rows_b = await list_activity_events(
            db, tenant_id=tenant_b, flight_id=flight_b, event_types=["EndpointChanged"]
        )
        assert len(rows_a) == 1 and len(rows_b) == 1
        assert rows_a[0].endpoint_id == intake_source_endpoint_id(profile_a)
        assert rows_b[0].endpoint_id == intake_source_endpoint_id(profile_b)
        assert not ({r.id for r in rows_a} & {r.id for r in rows_b})
        await db.commit()
