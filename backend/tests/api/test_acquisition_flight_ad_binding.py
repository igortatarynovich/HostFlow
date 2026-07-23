"""Meta Ad ID → Flight binding runtime (Acquisition cutover contract)."""

from __future__ import annotations

from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from backend.app.acquisition.flight_ad_binding import MISSING_CAMPAIGN_FLIGHT
from backend.app.acquisition.submission_routing import (
    RoutingSource,
    UnresolvedReason,
    resolve_universal_submission_routing,
)
from backend.app.db.session import async_session_maker
from backend.app.models.campaign import (
    Campaign,
    CampaignRun,
    CampaignRunForm,
    CampaignTarget,
    FlightAdBinding,
)
from backend.app.models.intake_routing import IntakeSourceProfile
from backend.app.models.lead import Lead
from backend.app.models.own_company import OwnCompany
from backend.app.models.tenant_lead_form import TenantLeadForm
from backend.app.models.company import Company
from backend.app.models.vacancy import Vacancy
from backend.tests.conftest import _init_data

DEFAULT_TENANT_ID = "11111111-1111-1111-1111-111111111111"


async def _own_company_id(tenant_id: str) -> str:
    async with async_session_maker() as session:
        row = await session.execute(
            select(OwnCompany.id)
            .where(OwnCompany.tenant_id == tenant_id, OwnCompany.is_archived.is_(False))
            .limit(1)
        )
        oc = row.scalar_one_or_none()
        assert oc
        return str(oc)


async def _company_id(tenant_id: str) -> str:
    async with async_session_maker() as session:
        row = await session.execute(
            select(Company.id).where(Company.tenant_id == tenant_id).limit(1)
        )
        cid = row.scalar_one_or_none()
        assert cid
        return str(cid)


async def _seed_campaign_flight(
    *,
    tenant_id: str,
    own_company_id: str,
    vacancy_id: str | None = None,
    campaign_status: str = "active",
    flight_status: str = "active",
) -> tuple[str, str]:
    async with async_session_maker() as session:
        campaign = Campaign(
            id=str(uuid4()),
            tenant_id=tenant_id,
            own_company_id=own_company_id,
            name=f"AdBind Camp {uuid4().hex[:6]}",
            status=campaign_status,
            goal_type="hiring",
            primary_kpi="applications",
        )
        session.add(campaign)
        await session.flush()
        flight = CampaignRun(
            id=str(uuid4()),
            tenant_id=tenant_id,
            campaign_id=campaign.id,
            name="Flight Ad",
            status=flight_status,
            code=f"f-{uuid4().hex[:6]}",
        )
        session.add(flight)
        await session.flush()
        campaign.current_flight_id = flight.id
        if vacancy_id:
            session.add(
                CampaignTarget(
                    id=str(uuid4()),
                    tenant_id=tenant_id,
                    campaign_id=campaign.id,
                    target_type="vacancy",
                    target_id=str(vacancy_id),
                    target_module="recruitment",
                    route_intent="candidate_application",
                    role="primary",
                    sort_order=0,
                )
            )
        await session.commit()
        return str(campaign.id), str(flight.id)


@pytest.mark.anyio
async def test_meta_ad_without_binding_is_missing_campaign_flight_no_profile_default():
    data = await _init_data()
    tenant_id = data["tenant_id"]
    oc = await _own_company_id(tenant_id)
    async with async_session_maker() as session:
        profile = IntakeSourceProfile(
            id=str(uuid4()),
            tenant_id=tenant_id,
            code=f"ad-prof-{uuid4().hex[:6]}",
            name="Profile",
            provider="meta",
            channel="paid",
            own_company_id=oc,
            route_intent="candidate_application",
            mapping_rules=[{"source": "email", "target": "email"}],
            is_active=True,
        )
        session.add(profile)
        await session.commit()
        pid = str(profile.id)

        decision = await resolve_universal_submission_routing(
            session,
            tenant_id=tenant_id,
            intake_source_profile_id=pid,
            form_id=None,
            provider="meta",
            provider_ad_id="998877001",
        )
    assert decision.status == "unresolved"
    assert decision.unresolved_reason == UnresolvedReason.missing_campaign_flight.value
    assert decision.source != RoutingSource.profile_default.value


@pytest.mark.anyio
async def test_meta_ad_binding_wins_over_form_flight(
    client: AsyncClient, manager_headers: dict
):
    data = await _init_data()
    tenant_id = data["tenant_id"]
    oc = await _own_company_id(tenant_id)
    company_id = await _company_id(tenant_id)
    ad_id = str(900_000_000 + (uuid4().int % 90_000_000))

    async with async_session_maker() as session:
        # Vacancy for CampaignTarget
        vac = Vacancy(
            id=str(uuid4()),
            tenant_id=tenant_id,
            own_company_id=oc,
            company_id=company_id,
            title="Warehouse",
            status="open",
            is_active=True,
            is_archived=False,
        )
        session.add(vac)
        await session.flush()
        form = TenantLeadForm(
            id=str(uuid4()),
            tenant_id=tenant_id,
            title="Form",
            public_slug=f"f-{uuid4().hex[:6]}",
            is_active=True,
            lifecycle_status="published",
            purpose="inquiry",
        )
        session.add(form)
        await session.flush()

        # Form-linked flight (wrong attribution if Form won)
        camp_form, flight_form = await _seed_inner(
            session, tenant_id=tenant_id, own_company_id=oc, vacancy_id=str(vac.id)
        )
        session.add(
            CampaignRunForm(
                id=str(uuid4()),
                tenant_id=tenant_id,
                campaign_run_id=flight_form,
                form_id=str(form.id),
                role="primary",
                is_active=True,
            )
        )
        # Ad-bound flight
        camp_ad, flight_ad = await _seed_inner(
            session, tenant_id=tenant_id, own_company_id=oc, vacancy_id=str(vac.id)
        )
        session.add(
            FlightAdBinding(
                id=str(uuid4()),
                tenant_id=tenant_id,
                provider="meta",
                provider_ad_id=ad_id,
                campaign_id=camp_ad,
                campaign_run_id=flight_ad,
                is_active=True,
            )
        )
        await session.commit()
        form_id = str(form.id)

        decision = await resolve_universal_submission_routing(
            session,
            tenant_id=tenant_id,
            form_id=form_id,
            provider="meta",
            provider_ad_id=ad_id,
        )
    assert decision.status == "routed"
    assert decision.campaign_run_id == flight_ad
    assert decision.campaign_run_id != flight_form
    assert decision.source == RoutingSource.flight_ad_binding.value


async def _seed_inner(session, *, tenant_id, own_company_id, vacancy_id):
    campaign = Campaign(
        id=str(uuid4()),
        tenant_id=tenant_id,
        own_company_id=own_company_id,
        name=f"Camp {uuid4().hex[:5]}",
        status="active",
        goal_type="hiring",
        primary_kpi="applications",
    )
    session.add(campaign)
    await session.flush()
    flight = CampaignRun(
        id=str(uuid4()),
        tenant_id=tenant_id,
        campaign_id=campaign.id,
        name="F",
        status="active",
        code=f"c-{uuid4().hex[:5]}",
    )
    session.add(flight)
    await session.flush()
    campaign.current_flight_id = flight.id
    session.add(
        CampaignTarget(
            id=str(uuid4()),
            tenant_id=tenant_id,
            campaign_id=campaign.id,
            target_type="vacancy",
            target_id=str(vacancy_id),
            target_module="recruitment",
            route_intent="candidate_application",
            role="primary",
            sort_order=0,
        )
    )
    await session.flush()
    return str(campaign.id), str(flight.id)


@pytest.mark.anyio
async def test_attach_ad_binding_reprocesses_missing_campaign_flight(
    client: AsyncClient, manager_headers: dict
):
    data = await _init_data()
    tenant_id = data["tenant_id"]
    oc = await _own_company_id(tenant_id)
    company_id = await _company_id(tenant_id)
    ad_id = str(800_000_000 + (uuid4().int % 90_000_000))

    async with async_session_maker() as session:
        vac = Vacancy(
            id=str(uuid4()),
            tenant_id=tenant_id,
            own_company_id=oc,
            company_id=company_id,
            title="Pickers",
            status="open",
            is_active=True,
            is_archived=False,
        )
        session.add(vac)
        await session.flush()
        camp_id, flight_id = await _seed_campaign_flight(
            tenant_id=tenant_id, own_company_id=oc, vacancy_id=str(vac.id)
        )
        # waiting lead
        lead = Lead(
            id=str(uuid4()),
            tenant_id=tenant_id,
            own_company_id=oc,
            source="meta",
            status="needs_routing",
            ad_id=int(ad_id),
            payload={"ad_id": ad_id, "field_data": []},
            normalized={
                "ad_id": ad_id,
                "email": f"wait-{uuid4().hex[:6]}@example.com",
                "acquisition_routing_v1": {
                    "status": "unresolved",
                    "unresolved_reason": MISSING_CAMPAIGN_FLIGHT,
                },
            },
            error=MISSING_CAMPAIGN_FLIGHT,
            external_id=f"meta-lead-{uuid4().hex[:10]}",
        )
        # other needs_routing (mapping) must not reprocess
        other = Lead(
            id=str(uuid4()),
            tenant_id=tenant_id,
            own_company_id=oc,
            source="meta",
            status="needs_routing",
            ad_id=int(ad_id),
            payload={},
            normalized={"ad_id": ad_id},
            error="MAPPING_FAILED",
            external_id=f"meta-lead-{uuid4().hex[:10]}",
        )
        session.add_all([lead, other])
        await session.commit()
        lead_id = str(lead.id)
        other_id = str(other.id)

    headers = dict(manager_headers)
    headers["X-Tenant-Id"] = tenant_id
    headers["X-Own-Company-Id"] = oc
    headers["Content-Type"] = "application/json"
    resp = await client.post(
        f"/api/v1/platform/campaigns/{camp_id}/flights/{flight_id}/ad-bindings",
        headers=headers,
        json={"provider_ad_id": ad_id, "provider": "meta"},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["provider_ad_id"] == ad_id
    assert body["flight_id"] == flight_id
    assert body["reprocess"]["matched"] >= 1

    async with async_session_maker() as session:
        waiting = await session.get(Lead, lead_id)
        untouched = await session.get(Lead, other_id)
        assert waiting is not None
        assert untouched is not None
        # Reprocess attempted; either routed further or still blocked by gates,
        # but must not stay on missing_campaign_flight if Flight is active+target.
        stamp = (waiting.normalized or {}).get("acquisition_routing_v1") or {}
        assert stamp.get("unresolved_reason") != MISSING_CAMPAIGN_FLIGHT or waiting.candidate_id
        assert untouched.error == "MAPPING_FAILED"
