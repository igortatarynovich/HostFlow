"""Stage 6 PR-6b — ROI compose from Outcome commercial value."""

from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from backend.app.acquisition.contracts.outcome_commercial_value import (
    set_outcome_commercial_value,
)
from backend.app.acquisition.kpi_aggregates import aggregate_campaign_kpi, record_flight_spend
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
from backend.app.models.campaign import Campaign, CampaignRun
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
                title="ROI Drivers",
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
            "name": "ROI campaign",
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


@pytest.mark.asyncio
async def test_kpi_and_compare_include_roi(
    client: AsyncClient, auth_headers: dict, monkeypatch
):
    monkeypatch.setattr("backend.app.acquisition.campaign_service.enforce_module_gate", _allow_gate)
    data = await _init_data()
    tenant_id = data["tenant_id"]
    oc = await _default_own_company_id(tenant_id)
    vac = await _seed_vacancy(tenant_id=tenant_id, own_company_id=oc, company_id=data["company_id"])
    campaign = await _create_campaign(client, auth_headers, own_company_id=oc, vac_id=vac)
    flight_id = campaign["flights"][0]["id"]
    headers = _company_headers(auth_headers, oc)

    async with async_session_maker() as session:
        camp = await session.get(Campaign, campaign["id"])
        flight = await session.get(CampaignRun, flight_id)
        assert camp and flight
        camp.status = "active"
        flight.status = "active"
        await session.commit()

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
            lead, _routed(campaign_id=campaign["id"], flight_id=flight_id)
        )
        session.add(lead)
        await session.flush()
        attr = await record_result_attribution_from_routing(
            session,
            tenant_id=tenant_id,
            lead=lead,
            submission_id=str(uuid4()),
            result_type=RESULT_TYPE_INTAKE_LEAD,
            result_id=lead_id,
        )
        await record_flight_spend(
            session, tenant_id=tenant_id, flight_id=flight_id, amount="100.00", currency="EUR"
        )
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
            attribution_id=str(attr.id),
        )
        await set_outcome_commercial_value(
            session,
            tenant_id=tenant_id,
            outcome_id=str(outcome.id),
            amount="250.00",
            currency="EUR",
        )
        await session.commit()

    async with async_session_maker() as session:
        kpi = await aggregate_campaign_kpi(
            session, tenant_id=tenant_id, campaign_id=campaign["id"]
        )
    assert kpi.spend == Decimal("100.0000")
    assert kpi.outcome_value == Decimal("250.0000")
    # (250 - 100) / 100 = 1.5
    assert kpi.roi == Decimal("1.5000")

    resp = await client.get(
        f"/api/v1/platform/campaigns/{campaign['id']}/analytics/flight-compare",
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["outcome_value"] == "250.0000"
    assert body["roi"] == "1.5000"
    assert body["flights"][0]["roi"] == "1.5000"

    cohorts = await client.get(
        f"/api/v1/platform/campaigns/{campaign['id']}/analytics/cohorts",
        headers=headers,
        params={"window_days": 14, "bucket": "day"},
    )
    assert cohorts.status_code == 200, cohorts.text
    cbody = cohorts.json()
    assert cbody["outcome_value"] == "250.0000"
    assert cbody["roi"] == "1.5000"

    portfolio = await client.get(
        "/api/v1/platform/campaigns/analytics/portfolio",
        headers=headers,
        params={"limit": 50},
    )
    assert portfolio.status_code == 200, portfolio.text
    rows = [r for r in portfolio.json()["campaigns"] if r["campaign_id"] == campaign["id"]]
    assert rows
    assert rows[0]["outcome_value"] == "250.0000"
    assert rows[0]["roi"] == "1.5000"
