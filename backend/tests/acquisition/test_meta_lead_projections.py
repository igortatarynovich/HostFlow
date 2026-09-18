"""Meta lead → Acquisition activity + attribution projection."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import select, text

from backend.app.acquisition.activity import list_activity_events
from backend.app.acquisition.endpoint_activity import intake_source_endpoint_id
from backend.app.acquisition.flights.lifecycle import (
    FLIGHT_STATUS_ACTIVE,
    create_flight,
    transition_flight_status,
)
from backend.app.acquisition.meta_lead_projections import (
    backfill_meta_lead_projections,
    meta_lead_submission_id,
    project_meta_lead_into_acquisition,
)
from backend.app.acquisition.submission_routing import RoutingDecisionStatus
from backend.app.db.session import async_session_maker
from backend.app.models.acquisition_activity_event import ACTOR_TYPE_SYSTEM
from backend.app.models.campaign import Campaign, CampaignResultAttribution
from backend.app.models.lead import Lead
from backend.app.models.own_company import OwnCompany
from backend.app.models.tenant import Tenant


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


async def _seed_campaign_active_flight(db, *, tenant_id: str) -> tuple[Campaign, str]:
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
    return campaign, str(flight.id)


@pytest.mark.asyncio
async def test_project_meta_lead_writes_activity_and_attribution() -> None:
    tenant_id = str(uuid4())
    profile_id = str(uuid4())
    async with async_session_maker() as db:
        await db.execute(text("SELECT set_config('app.tenant_id', :tid, true)"), {"tid": tenant_id})
        campaign, flight_id = await _seed_campaign_active_flight(db, tenant_id=tenant_id)
        lead_id = str(uuid4())
        stamp = {
            "status": RoutingDecisionStatus.routed.value,
            "campaign_id": campaign.id,
            "campaign_run_id": flight_id,
            "intake_source_profile_id": profile_id,
            "route_intent": "recruitment_application",
            "form_id": "999001",
        }
        lead = Lead(
            id=lead_id,
            tenant_id=tenant_id,
            source="meta",
            status="duplicated",
            external_id=f"lg-{uuid4().hex[:10]}",
            created_at=datetime.now(timezone.utc),
            normalized={"acquisition_routing_v1": stamp, "form_id": "999001"},
            payload={},
        )
        db.add(lead)
        await db.flush()

        await project_meta_lead_into_acquisition(
            db, tenant_id=tenant_id, lead=lead, normalized=lead.normalized
        )
        await db.flush()

        events = await list_activity_events(
            db, tenant_id=tenant_id, campaign_id=campaign.id, limit=50
        )
        types = {e.event_type for e in events}
        assert "SubmissionReceived" in types
        assert "LeadCreated" in types
        endpoint = intake_source_endpoint_id(profile_id)
        assert any(e.endpoint_id == endpoint for e in events if e.event_type == "SubmissionReceived")
        assert any(e.submission_id == meta_lead_submission_id(lead_id) for e in events)

        attr = (
            await db.execute(
                select(CampaignResultAttribution).where(
                    CampaignResultAttribution.tenant_id == tenant_id,
                    CampaignResultAttribution.lead_id == lead_id,
                )
            )
        ).scalar_one_or_none()
        assert attr is not None
        assert attr.result_type == "intake_lead"
        assert attr.campaign_id == campaign.id

        # Idempotent second call
        await project_meta_lead_into_acquisition(
            db, tenant_id=tenant_id, lead=lead, normalized=lead.normalized
        )
        await db.flush()
        count = (
            await db.execute(
                select(CampaignResultAttribution.id).where(
                    CampaignResultAttribution.tenant_id == tenant_id,
                    CampaignResultAttribution.lead_id == lead_id,
                )
            )
        ).scalars().all()
        assert len(count) == 1
        await db.rollback()


@pytest.mark.asyncio
async def test_backfill_meta_lead_projections_scans_routed_meta() -> None:
    tenant_id = str(uuid4())
    async with async_session_maker() as db:
        campaign, flight_id = await _seed_campaign_active_flight(db, tenant_id=tenant_id)
        await db.execute(text("SELECT set_config('app.tenant_id', :tid, true)"), {"tid": tenant_id})
        lead = Lead(
            id=str(uuid4()),
            tenant_id=tenant_id,
            source="meta",
            status="processed",
            external_id=f"lg-{uuid4().hex[:10]}",
            created_at=datetime.now(timezone.utc),
            normalized={
                "acquisition_routing_v1": {
                    "status": RoutingDecisionStatus.routed.value,
                    "campaign_id": campaign.id,
                    "campaign_run_id": flight_id,
                    "intake_source_profile_id": str(uuid4()),
                }
            },
            payload={},
        )
        db.add(lead)
        await db.flush()
        stats = await backfill_meta_lead_projections(db, tenant_id=tenant_id, limit=100)
        assert stats["scanned"] >= 1
        assert stats["projected"] >= 1
        events = await list_activity_events(
            db, tenant_id=tenant_id, campaign_id=campaign.id, limit=20
        )
        assert any(e.event_type == "SubmissionReceived" for e in events)
        await db.rollback()
