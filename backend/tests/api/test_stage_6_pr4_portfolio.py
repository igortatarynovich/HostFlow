"""Stage 6 PR-4 — cross-campaign portfolio analytics (read-only)."""

from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from backend.app.acquisition.kpi_aggregates import record_flight_spend
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
                title="Portfolio Drivers",
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
    name: str,
) -> dict:
    resp = await client.post(
        "/api/v1/platform/campaigns",
        headers=_company_headers(headers, own_company_id),
        json={
            "name": name,
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


async def _attr(*, tenant_id: str, campaign_id: str, flight_id: str) -> None:
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
        await record_result_attribution_from_routing(
            session,
            tenant_id=tenant_id,
            lead=lead,
            submission_id=str(uuid4()),
            result_type=RESULT_TYPE_INTAKE_LEAD,
            result_id=lead_id,
        )
        await session.commit()


@pytest.mark.asyncio
async def test_campaign_portfolio_marks_best_cpl(
    client: AsyncClient, auth_headers: dict, monkeypatch
):
    monkeypatch.setattr("backend.app.acquisition.campaign_service.enforce_module_gate", _allow_gate)
    data = await _init_data()
    tenant_id = data["tenant_id"]
    oc = await _default_own_company_id(tenant_id)
    vac = await _seed_vacancy(tenant_id=tenant_id, own_company_id=oc, company_id=data["company_id"])
    camp_a = await _create_campaign(
        client, auth_headers, own_company_id=oc, vac_id=vac, name="Portfolio A"
    )
    camp_b = await _create_campaign(
        client, auth_headers, own_company_id=oc, vac_id=vac, name="Portfolio B"
    )
    flight_a = camp_a["flights"][0]["id"]
    flight_b = camp_b["flights"][0]["id"]

    async with async_session_maker() as session:
        for cid, fid in ((camp_a["id"], flight_a), (camp_b["id"], flight_b)):
            camp = await session.get(Campaign, cid)
            flight = await session.get(CampaignRun, fid)
            assert camp and flight
            camp.status = "active"
            flight.status = "active"
        await session.commit()

    await _attr(tenant_id=tenant_id, campaign_id=camp_a["id"], flight_id=flight_a)
    await _attr(tenant_id=tenant_id, campaign_id=camp_a["id"], flight_id=flight_a)
    await _attr(tenant_id=tenant_id, campaign_id=camp_b["id"], flight_id=flight_b)

    async with async_session_maker() as session:
        await record_flight_spend(
            session, tenant_id=tenant_id, flight_id=flight_a, amount="100.00", currency="EUR"
        )
        await record_flight_spend(
            session, tenant_id=tenant_id, flight_id=flight_b, amount="40.00", currency="EUR"
        )
        await session.commit()

    resp = await client.get(
        "/api/v1/platform/campaigns/analytics/portfolio",
        headers=_company_headers(auth_headers, oc),
        params={"limit": 50},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    by_id = {row["campaign_id"]: row for row in body["campaigns"]}
    assert camp_a["id"] in by_id
    assert camp_b["id"] in by_id
    assert by_id[camp_a["id"]]["cost_per_lead"] == "50.0000"
    assert by_id[camp_b["id"]]["cost_per_lead"] == "40.0000"
    assert by_id[camp_a["id"]]["is_best_cpl"] is False
    defined = [r for r in body["campaigns"] if r.get("cost_per_lead") is not None]
    best = min(Decimal(r["cost_per_lead"]) for r in defined)
    assert Decimal(by_id[camp_b["id"]]["cost_per_lead"]) == best or Decimal(
        by_id[camp_b["id"]]["cost_per_lead"]
    ) > best
    if Decimal(by_id[camp_b["id"]]["cost_per_lead"]) == best:
        assert by_id[camp_b["id"]]["is_best_cpl"] is True
    assert body["leads"] >= 3
    assert Decimal(body["spend"]) >= Decimal("140.0000")


@pytest.mark.asyncio
async def test_campaign_portfolio_isolated_by_company(
    client: AsyncClient, auth_headers: dict, monkeypatch
):
    monkeypatch.setattr("backend.app.acquisition.campaign_service.enforce_module_gate", _allow_gate)
    data = await _init_data()
    tenant_id = data["tenant_id"]
    oc = await _default_own_company_id(tenant_id)
    vac = await _seed_vacancy(tenant_id=tenant_id, own_company_id=oc, company_id=data["company_id"])
    camp = await _create_campaign(
        client, auth_headers, own_company_id=oc, vac_id=vac, name="Portfolio Own"
    )

    other_oc = str(uuid4())
    async with async_session_maker() as session:
        session.add(
            OwnCompany(
                id=other_oc,
                tenant_id=tenant_id,
                name="Other OC Portfolio",
                is_archived=False,
            )
        )
        await session.commit()

    resp = await client.get(
        "/api/v1/platform/campaigns/analytics/portfolio",
        headers=_company_headers(auth_headers, other_oc),
    )
    assert resp.status_code == 200, resp.text
    ids = {row["campaign_id"] for row in resp.json()["campaigns"]}
    assert camp["id"] not in ids
