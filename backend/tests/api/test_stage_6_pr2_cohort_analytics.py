"""Stage 6 PR-2 — windowed day cohort analytics (read-only)."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from backend.app.acquisition.kpi_aggregates import record_flight_spend
from backend.app.acquisition.ops.cohort_analytics import compose_campaign_cohorts
from backend.app.acquisition.outcome_service import (
    apply_attribution_to_outcome,
    create_outcome,
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
from backend.app.models.campaign import Campaign, CampaignOutcome, CampaignRun
from backend.app.models.lead import Lead
from backend.app.models.own_company import OwnCompany
from backend.app.models.vacancy import Vacancy
from backend.tests.conftest import _init_data


async def _allow_gate(*_a, **_k):
    return None


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


async def _seed_vacancy(*, tenant_id: str, own_company_id: str, company_id: str) -> str:
    vac_id = str(uuid4())
    async with async_session_maker() as session:
        session.add(
            Vacancy(
                id=vac_id,
                tenant_id=tenant_id,
                own_company_id=own_company_id,
                company_id=company_id,
                title="Cohort Drivers",
                status="open",
                is_active=True,
                is_archived=False,
            )
        )
        await session.commit()
    return vac_id


def _company_headers(auth_headers: dict, own_company_id: str) -> dict:
    return {**auth_headers, "X-Own-Company-Id": own_company_id}


async def _create_campaign(
    client: AsyncClient,
    headers: dict,
    *,
    own_company_id: str,
    vac_id: str,
) -> dict:
    resp = await client.post(
        "/api/v1/platform/campaigns",
        headers=_company_headers(headers, own_company_id),
        json={
            "name": "Cohort campaign",
            "goal_type": "hiring",
            "primary_kpi": "applications",
            "targets": [
                {
                    "target_type": "vacancy",
                    "target_id": vac_id,
                    "route_intent": "candidate_application",
                    "role": "primary",
                }
            ],
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _routed(*, campaign_id: str, flight_id: str) -> UniversalRoutingDecision:
    return UniversalRoutingDecision(
        status=RoutingDecisionStatus.routed.value,
        route_intent="candidate_application",
        campaign_id=campaign_id,
        campaign_run_id=flight_id,
        campaign_target_id=None,
        intake_source_profile_id=None,
        form_id=None,
        source=RoutingSource.campaign_target.value,
        unresolved_reason=None,
        warnings=(),
        decided_at="2026-08-03T12:00:00+00:00",
    )


async def _attr_at(
    *,
    tenant_id: str,
    campaign_id: str,
    flight_id: str,
    created_at: datetime,
) -> str:
    lead_id = str(uuid4())
    async with async_session_maker() as session:
        lead = Lead(
            id=lead_id,
            tenant_id=tenant_id,
            status="new",
            stage="questionnaire_submitted",
            normalized={},
            payload={},
        )
        stamp_acquisition_routing_on_lead(
            lead, _routed(campaign_id=campaign_id, flight_id=flight_id)
        )
        session.add(lead)
        await session.flush()
        row = await record_result_attribution_from_routing(
            session,
            tenant_id=tenant_id,
            lead=lead,
            submission_id=str(uuid4()),
            result_type=RESULT_TYPE_INTAKE_LEAD,
            result_id=lead_id,
        )
        row.created_at = created_at
        await session.commit()
        return str(row.id)


@pytest.mark.asyncio
async def test_campaign_cohorts_day_buckets_and_cac_proxy(
    client: AsyncClient, auth_headers: dict, monkeypatch
):
    monkeypatch.setattr("backend.app.acquisition.campaign_service.enforce_module_gate", _allow_gate)
    data = await _init_data()
    tenant_id = data["tenant_id"]
    oc = await _default_own_company_id(tenant_id)
    vac = await _seed_vacancy(tenant_id=tenant_id, own_company_id=oc, company_id=data["company_id"])
    campaign = await _create_campaign(client, auth_headers, own_company_id=oc, vac_id=vac)
    flight_id = campaign["flights"][0]["id"]

    now = datetime(2026, 8, 3, 15, 0, tzinfo=timezone.utc)
    day0 = datetime(2026, 8, 2, 10, 0, tzinfo=timezone.utc)
    day1 = datetime(2026, 8, 3, 11, 0, tzinfo=timezone.utc)

    async with async_session_maker() as session:
        camp = await session.get(Campaign, campaign["id"])
        flight = await session.get(CampaignRun, flight_id)
        assert camp and flight
        camp.status = "active"
        flight.status = "active"
        await session.commit()

    await _attr_at(
        tenant_id=tenant_id,
        campaign_id=campaign["id"],
        flight_id=flight_id,
        created_at=day0,
    )
    await _attr_at(
        tenant_id=tenant_id,
        campaign_id=campaign["id"],
        flight_id=flight_id,
        created_at=day1,
    )
    attr_for_outcome = await _attr_at(
        tenant_id=tenant_id,
        campaign_id=campaign["id"],
        flight_id=flight_id,
        created_at=day1,
    )

    async with async_session_maker() as session:
        s0 = await record_flight_spend(
            session, tenant_id=tenant_id, flight_id=flight_id, amount="30.00", currency="EUR"
        )
        s1 = await record_flight_spend(
            session, tenant_id=tenant_id, flight_id=flight_id, amount="70.00", currency="EUR"
        )
        s0.created_at = day0
        s1.created_at = day1
        outcome = await create_outcome(
            session,
            tenant_id=tenant_id,
            campaign_id=campaign["id"],
            flight_id=flight_id,
            progress_target=1,
        )
        await apply_attribution_to_outcome(
            session,
            tenant_id=tenant_id,
            outcome_id=outcome.id,
            attribution_id=attr_for_outcome,
        )
        refreshed = await session.get(CampaignOutcome, outcome.id)
        assert refreshed
        refreshed.completed_at = day1
        await session.commit()

    async with async_session_maker() as session:
        series = await compose_campaign_cohorts(
            session,
            tenant_id=tenant_id,
            campaign_id=campaign["id"],
            window_days=2,
            now=now,
        )

    assert series.window_days == 2
    assert series.bucket == "day"
    assert len(series.buckets) == 2
    assert series.leads == 3
    assert series.spend == Decimal("100.0000")
    assert series.outcomes_completed == 1
    assert series.cost_per_lead == Decimal("33.3333")
    assert series.cost_per_outcome == Decimal("100.0000")

    b0, b1 = series.buckets
    assert b0.leads == 1
    assert b0.spend == Decimal("30.0000")
    assert b0.cost_per_lead == Decimal("30.0000")
    assert b1.leads == 2
    assert b1.spend == Decimal("70.0000")
    assert b1.outcomes_completed == 1
    assert b1.cost_per_outcome == Decimal("70.0000")

    resp = await client.get(
        f"/api/v1/platform/campaigns/{campaign['id']}/analytics/cohorts",
        headers=_company_headers(auth_headers, oc),
        params={"window_days": 2},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["bucket"] == "day"
    assert body["window_days"] == 2
    assert len(body["buckets"]) == 2


@pytest.mark.asyncio
async def test_campaign_cohorts_cross_company_404(
    client: AsyncClient, auth_headers: dict, monkeypatch
):
    monkeypatch.setattr("backend.app.acquisition.campaign_service.enforce_module_gate", _allow_gate)
    data = await _init_data()
    tenant_id = data["tenant_id"]
    oc = await _default_own_company_id(tenant_id)
    vac = await _seed_vacancy(tenant_id=tenant_id, own_company_id=oc, company_id=data["company_id"])
    campaign = await _create_campaign(client, auth_headers, own_company_id=oc, vac_id=vac)

    other_oc = str(uuid4())
    async with async_session_maker() as session:
        session.add(
            OwnCompany(
                id=other_oc,
                tenant_id=tenant_id,
                name="Other OC Cohorts",
                is_archived=False,
            )
        )
        await session.commit()

    resp = await client.get(
        f"/api/v1/platform/campaigns/{campaign['id']}/analytics/cohorts",
        headers=_company_headers(auth_headers, other_oc),
        params={"window_days": 7},
    )
    assert resp.status_code == 404, resp.text


@pytest.mark.asyncio
async def test_campaign_cohorts_week_bucket_rolls_up(
    client: AsyncClient, auth_headers: dict, monkeypatch
):
    monkeypatch.setattr("backend.app.acquisition.campaign_service.enforce_module_gate", _allow_gate)
    data = await _init_data()
    tenant_id = data["tenant_id"]
    oc = await _default_own_company_id(tenant_id)
    vac = await _seed_vacancy(tenant_id=tenant_id, own_company_id=oc, company_id=data["company_id"])
    campaign = await _create_campaign(client, auth_headers, own_company_id=oc, vac_id=vac)
    flight_id = campaign["flights"][0]["id"]

    # Sunday 2026-08-02 + Monday 2026-08-03 → two ISO weeks when window_days=2.
    now = datetime(2026, 8, 3, 15, 0, tzinfo=timezone.utc)
    day0 = datetime(2026, 8, 2, 10, 0, tzinfo=timezone.utc)
    day1 = datetime(2026, 8, 3, 11, 0, tzinfo=timezone.utc)

    async with async_session_maker() as session:
        camp = await session.get(Campaign, campaign["id"])
        flight = await session.get(CampaignRun, flight_id)
        assert camp and flight
        camp.status = "active"
        flight.status = "active"
        await session.commit()

    await _attr_at(
        tenant_id=tenant_id,
        campaign_id=campaign["id"],
        flight_id=flight_id,
        created_at=day0,
    )
    await _attr_at(
        tenant_id=tenant_id,
        campaign_id=campaign["id"],
        flight_id=flight_id,
        created_at=day1,
    )

    async with async_session_maker() as session:
        s0 = await record_flight_spend(
            session, tenant_id=tenant_id, flight_id=flight_id, amount="30.00", currency="EUR"
        )
        s1 = await record_flight_spend(
            session, tenant_id=tenant_id, flight_id=flight_id, amount="70.00", currency="EUR"
        )
        s0.created_at = day0
        s1.created_at = day1
        await session.commit()

    async with async_session_maker() as session:
        series = await compose_campaign_cohorts(
            session,
            tenant_id=tenant_id,
            campaign_id=campaign["id"],
            window_days=2,
            bucket="week",
            now=now,
        )

    assert series.bucket == "week"
    assert len(series.buckets) == 2
    assert series.leads == 2
    assert series.spend == Decimal("100.0000")
    # First week (Mon 2026-07-27): only Sunday Aug 2 inside window → 30 / 1
    assert series.buckets[0].bucket_start.date().isoformat() == "2026-07-27"
    assert series.buckets[0].spend == Decimal("30.0000")
    assert series.buckets[0].leads == 1
    # Second week (Mon 2026-08-03): Monday Aug 3 → 70 / 1
    assert series.buckets[1].bucket_start.date().isoformat() == "2026-08-03"
    assert series.buckets[1].spend == Decimal("70.0000")
    assert series.buckets[1].leads == 1

    resp = await client.get(
        f"/api/v1/platform/campaigns/{campaign['id']}/analytics/cohorts",
        headers=_company_headers(auth_headers, oc),
        params={"window_days": 2, "bucket": "week"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["bucket"] == "week"

    bad = await client.get(
        f"/api/v1/platform/campaigns/{campaign['id']}/analytics/cohorts",
        headers=_company_headers(auth_headers, oc),
        params={"bucket": "year"},
    )
    assert bad.status_code == 422, bad.text


@pytest.mark.asyncio
async def test_campaign_cohorts_month_bucket_rolls_up(
    client: AsyncClient, auth_headers: dict, monkeypatch
):
    monkeypatch.setattr("backend.app.acquisition.campaign_service.enforce_module_gate", _allow_gate)
    data = await _init_data()
    tenant_id = data["tenant_id"]
    oc = await _default_own_company_id(tenant_id)
    vac = await _seed_vacancy(tenant_id=tenant_id, own_company_id=oc, company_id=data["company_id"])
    campaign = await _create_campaign(client, auth_headers, own_company_id=oc, vac_id=vac)
    flight_id = campaign["flights"][0]["id"]

    # Jul 31 + Aug 2 within 90d window → two calendar months.
    now = datetime(2026, 8, 3, 15, 0, tzinfo=timezone.utc)
    day_jul = datetime(2026, 7, 31, 10, 0, tzinfo=timezone.utc)
    day_aug = datetime(2026, 8, 2, 11, 0, tzinfo=timezone.utc)

    async with async_session_maker() as session:
        camp = await session.get(Campaign, campaign["id"])
        flight = await session.get(CampaignRun, flight_id)
        assert camp and flight
        camp.status = "active"
        flight.status = "active"
        await session.commit()

    await _attr_at(
        tenant_id=tenant_id,
        campaign_id=campaign["id"],
        flight_id=flight_id,
        created_at=day_jul,
    )
    await _attr_at(
        tenant_id=tenant_id,
        campaign_id=campaign["id"],
        flight_id=flight_id,
        created_at=day_aug,
    )

    async with async_session_maker() as session:
        s0 = await record_flight_spend(
            session, tenant_id=tenant_id, flight_id=flight_id, amount="25.00", currency="EUR"
        )
        s1 = await record_flight_spend(
            session, tenant_id=tenant_id, flight_id=flight_id, amount="75.00", currency="EUR"
        )
        s0.created_at = day_jul
        s1.created_at = day_aug
        await session.commit()

    async with async_session_maker() as session:
        series = await compose_campaign_cohorts(
            session,
            tenant_id=tenant_id,
            campaign_id=campaign["id"],
            window_days=10,
            bucket="month",
            now=now,
        )

    assert series.bucket == "month"
    assert len(series.buckets) == 2
    assert series.buckets[0].bucket_start.date().isoformat() == "2026-07-01"
    assert series.buckets[0].spend == Decimal("25.0000")
    assert series.buckets[0].leads == 1
    assert series.buckets[1].bucket_start.date().isoformat() == "2026-08-01"
    assert series.buckets[1].spend == Decimal("75.0000")
    assert series.buckets[1].leads == 1

    resp = await client.get(
        f"/api/v1/platform/campaigns/{campaign['id']}/analytics/cohorts",
        headers=_company_headers(auth_headers, oc),
        params={"window_days": 10, "bucket": "month"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["bucket"] == "month"
