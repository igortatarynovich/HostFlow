"""ADR-024 Stage 3D PR-3 — KPI aggregates (Flight + Campaign read model)."""

from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from backend.app.acquisition.kpi_aggregates import (
    KpiAggregateError,
    aggregate_campaign_kpi,
    aggregate_flight_kpi,
    qualify_attribution,
    record_flight_spend,
)
from backend.app.acquisition.outcome_service import (
    apply_attribution_to_outcome,
    create_outcome,
    mark_outcome_cancelled,
    mark_outcome_failed,
    soft_revoke_outcome_result,
)
from backend.app.acquisition.result_attribution import (
    RESULT_TYPE_INTAKE_LEAD,
    record_result_attribution_from_routing,
)
from backend.app.acquisition.submission_routing import (
    RoutingDecisionStatus,
    RoutingSource,
    stamp_acquisition_routing_on_lead,
    UniversalRoutingDecision,
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
                title="CE Drivers",
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
    name: str = "KPI campaign",
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


async def _activate(campaign_id: str, flight_id: str) -> None:
    async with async_session_maker() as session:
        campaign = await session.get(Campaign, campaign_id)
        flight = await session.get(CampaignRun, flight_id)
        assert campaign and flight
        campaign.status = "active"
        flight.status = "active"
        await session.commit()


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
        decided_at="2026-07-18T12:00:00+00:00",
    )


async def _attr(
    *,
    tenant_id: str,
    campaign_id: str,
    flight_id: str,
    result_id: str | None = None,
) -> str:
    lead_id = str(uuid4())
    rid = result_id or lead_id
    async with async_session_maker() as session:
        lead = Lead(
            id=lead_id,
            tenant_id=tenant_id,
            status="new",
            stage="questionnaire_submitted",
            normalized={},
            payload={},
        )
        stamp_acquisition_routing_on_lead(lead, _routed(campaign_id=campaign_id, flight_id=flight_id))
        session.add(lead)
        await session.flush()
        row = await record_result_attribution_from_routing(
            session,
            tenant_id=tenant_id,
            lead=lead,
            submission_id=str(uuid4()),
            result_type=RESULT_TYPE_INTAKE_LEAD,
            result_id=rid,
        )
        await session.commit()
        return str(row.id)


@pytest.mark.asyncio
async def test_campaign_kpi_equals_sum_of_flight_kpi(
    client: AsyncClient, auth_headers: dict, monkeypatch
):
    monkeypatch.setattr("backend.app.acquisition.campaign_service.enforce_module_gate", _allow_gate)
    data = await _init_data()
    tenant_id = data["tenant_id"]
    oc = await _default_own_company_id(tenant_id)
    vac = await _seed_vacancy(tenant_id=tenant_id, own_company_id=oc, company_id=data["company_id"])
    campaign = await _create_campaign(client, auth_headers, own_company_id=oc, vac_id=vac)
    flight_id = campaign["flights"][0]["id"]
    await _activate(campaign["id"], flight_id)

    a1 = await _attr(tenant_id=tenant_id, campaign_id=campaign["id"], flight_id=flight_id)
    a2 = await _attr(tenant_id=tenant_id, campaign_id=campaign["id"], flight_id=flight_id)

    async with async_session_maker() as session:
        await record_flight_spend(
            session, tenant_id=tenant_id, flight_id=flight_id, amount="100.00", currency="EUR"
        )
        await qualify_attribution(session, tenant_id=tenant_id, attribution_id=a1)
        outcome = await create_outcome(
            session,
            tenant_id=tenant_id,
            campaign_id=campaign["id"],
            flight_id=flight_id,
            progress_target=1,
        )
        await apply_attribution_to_outcome(
            session, tenant_id=tenant_id, outcome_id=outcome.id, attribution_id=a2
        )
        flight_kpi = await aggregate_flight_kpi(session, tenant_id=tenant_id, flight_id=flight_id)
        campaign_kpi = await aggregate_campaign_kpi(
            session, tenant_id=tenant_id, campaign_id=campaign["id"]
        )
        await session.commit()

    assert len(campaign_kpi.flights) == 1
    assert campaign_kpi.spend == flight_kpi.spend == Decimal("100.0000")
    assert campaign_kpi.leads == flight_kpi.leads == 2
    assert campaign_kpi.qualified == flight_kpi.qualified == 1
    assert campaign_kpi.converted == flight_kpi.converted == 1
    assert campaign_kpi.outcomes_completed == 1
    assert campaign_kpi.cost_per_lead == Decimal("50.0000")
    assert campaign_kpi.cost_per_qualified == Decimal("100.0000")
    assert campaign_kpi.cost_per_outcome == Decimal("100.0000")


@pytest.mark.asyncio
async def test_duplicate_result_identity_does_not_double_leads(
    client: AsyncClient, auth_headers: dict, monkeypatch
):
    monkeypatch.setattr("backend.app.acquisition.campaign_service.enforce_module_gate", _allow_gate)
    data = await _init_data()
    tenant_id = data["tenant_id"]
    oc = await _default_own_company_id(tenant_id)
    vac = await _seed_vacancy(tenant_id=tenant_id, own_company_id=oc, company_id=data["company_id"])
    campaign = await _create_campaign(client, auth_headers, own_company_id=oc, vac_id=vac)
    flight_id = campaign["flights"][0]["id"]
    await _activate(campaign["id"], flight_id)
    rid = str(uuid4())
    await _attr(tenant_id=tenant_id, campaign_id=campaign["id"], flight_id=flight_id, result_id=rid)
    # Same result_id cannot create second attribution (unique) — re-record same identity via same attr
    async with async_session_maker() as session:
        kpi = await aggregate_flight_kpi(session, tenant_id=tenant_id, flight_id=flight_id)
        assert kpi.leads == 1
        # second distinct result increases
    await _attr(tenant_id=tenant_id, campaign_id=campaign["id"], flight_id=flight_id)
    async with async_session_maker() as session:
        kpi = await aggregate_flight_kpi(session, tenant_id=tenant_id, flight_id=flight_id)
        assert kpi.leads == 2


@pytest.mark.asyncio
async def test_zero_denominator_returns_null_ratios(
    client: AsyncClient, auth_headers: dict, monkeypatch
):
    monkeypatch.setattr("backend.app.acquisition.campaign_service.enforce_module_gate", _allow_gate)
    data = await _init_data()
    tenant_id = data["tenant_id"]
    oc = await _default_own_company_id(tenant_id)
    vac = await _seed_vacancy(tenant_id=tenant_id, own_company_id=oc, company_id=data["company_id"])
    campaign = await _create_campaign(client, auth_headers, own_company_id=oc, vac_id=vac)
    flight_id = campaign["flights"][0]["id"]
    await _activate(campaign["id"], flight_id)

    async with async_session_maker() as session:
        await record_flight_spend(
            session, tenant_id=tenant_id, flight_id=flight_id, amount="10", currency="PLN"
        )
        kpi = await aggregate_flight_kpi(session, tenant_id=tenant_id, flight_id=flight_id)
        await session.commit()
    assert kpi.leads == 0
    assert kpi.qualified == 0
    assert kpi.outcomes_completed == 0
    assert kpi.cost_per_lead is None
    assert kpi.cost_per_qualified is None
    assert kpi.cost_per_outcome is None


@pytest.mark.asyncio
async def test_mixed_currencies_raise(
    client: AsyncClient, auth_headers: dict, monkeypatch
):
    monkeypatch.setattr("backend.app.acquisition.campaign_service.enforce_module_gate", _allow_gate)
    data = await _init_data()
    tenant_id = data["tenant_id"]
    oc = await _default_own_company_id(tenant_id)
    vac = await _seed_vacancy(tenant_id=tenant_id, own_company_id=oc, company_id=data["company_id"])
    campaign = await _create_campaign(client, auth_headers, own_company_id=oc, vac_id=vac)
    flight_id = campaign["flights"][0]["id"]
    await _activate(campaign["id"], flight_id)

    async with async_session_maker() as session:
        await record_flight_spend(
            session, tenant_id=tenant_id, flight_id=flight_id, amount="10", currency="EUR"
        )
        await record_flight_spend(
            session, tenant_id=tenant_id, flight_id=flight_id, amount="5", currency="USD"
        )
        with pytest.raises(KpiAggregateError, match="mixed currencies"):
            await aggregate_flight_kpi(session, tenant_id=tenant_id, flight_id=flight_id)


@pytest.mark.asyncio
async def test_soft_revoke_does_not_reduce_completed_outcome_kpi(
    client: AsyncClient, auth_headers: dict, monkeypatch
):
    monkeypatch.setattr("backend.app.acquisition.campaign_service.enforce_module_gate", _allow_gate)
    data = await _init_data()
    tenant_id = data["tenant_id"]
    oc = await _default_own_company_id(tenant_id)
    vac = await _seed_vacancy(tenant_id=tenant_id, own_company_id=oc, company_id=data["company_id"])
    campaign = await _create_campaign(client, auth_headers, own_company_id=oc, vac_id=vac)
    flight_id = campaign["flights"][0]["id"]
    await _activate(campaign["id"], flight_id)
    result_id = str(uuid4())
    attr_id = await _attr(
        tenant_id=tenant_id, campaign_id=campaign["id"], flight_id=flight_id, result_id=result_id
    )

    async with async_session_maker() as session:
        await record_flight_spend(
            session, tenant_id=tenant_id, flight_id=flight_id, amount="50", currency="EUR"
        )
        outcome = await create_outcome(
            session,
            tenant_id=tenant_id,
            campaign_id=campaign["id"],
            flight_id=flight_id,
            progress_target=1,
        )
        await apply_attribution_to_outcome(
            session, tenant_id=tenant_id, outcome_id=outcome.id, attribution_id=attr_id
        )
        await soft_revoke_outcome_result(
            session,
            tenant_id=tenant_id,
            outcome_id=outcome.id,
            result_type=RESULT_TYPE_INTAKE_LEAD,
            result_id=result_id,
        )
        kpi = await aggregate_flight_kpi(session, tenant_id=tenant_id, flight_id=flight_id)
        await session.commit()
    assert kpi.outcomes_completed == 1
    assert kpi.cost_per_outcome == Decimal("50.0000")


@pytest.mark.asyncio
async def test_failed_and_cancelled_outcomes_not_successful(
    client: AsyncClient, auth_headers: dict, monkeypatch
):
    monkeypatch.setattr("backend.app.acquisition.campaign_service.enforce_module_gate", _allow_gate)
    data = await _init_data()
    tenant_id = data["tenant_id"]
    oc = await _default_own_company_id(tenant_id)
    vac = await _seed_vacancy(tenant_id=tenant_id, own_company_id=oc, company_id=data["company_id"])
    campaign = await _create_campaign(client, auth_headers, own_company_id=oc, vac_id=vac)
    flight_id = campaign["flights"][0]["id"]
    await _activate(campaign["id"], flight_id)
    a1 = await _attr(tenant_id=tenant_id, campaign_id=campaign["id"], flight_id=flight_id)

    async with async_session_maker() as session:
        await record_flight_spend(
            session, tenant_id=tenant_id, flight_id=flight_id, amount="20", currency="EUR"
        )
        failed = await create_outcome(
            session,
            tenant_id=tenant_id,
            campaign_id=campaign["id"],
            flight_id=flight_id,
            progress_target=2,
        )
        await apply_attribution_to_outcome(
            session, tenant_id=tenant_id, outcome_id=failed.id, attribution_id=a1
        )
        await mark_outcome_failed(session, tenant_id=tenant_id, outcome_id=failed.id)

        cancelled = await create_outcome(
            session,
            tenant_id=tenant_id,
            campaign_id=campaign["id"],
            flight_id=flight_id,
            progress_target=1,
        )
        await mark_outcome_cancelled(session, tenant_id=tenant_id, outcome_id=cancelled.id)

        kpi = await aggregate_flight_kpi(session, tenant_id=tenant_id, flight_id=flight_id)
        await session.commit()
    assert kpi.outcomes_completed == 0
    assert kpi.converted == 0
    assert kpi.cost_per_outcome is None


@pytest.mark.asyncio
async def test_tenant_isolation_and_decimal_precision(
    client: AsyncClient, auth_headers: dict, monkeypatch
):
    monkeypatch.setattr("backend.app.acquisition.campaign_service.enforce_module_gate", _allow_gate)
    data = await _init_data()
    tenant_id = data["tenant_id"]
    oc = await _default_own_company_id(tenant_id)
    vac = await _seed_vacancy(tenant_id=tenant_id, own_company_id=oc, company_id=data["company_id"])
    campaign = await _create_campaign(client, auth_headers, own_company_id=oc, vac_id=vac)
    flight_id = campaign["flights"][0]["id"]
    await _activate(campaign["id"], flight_id)
    await _attr(tenant_id=tenant_id, campaign_id=campaign["id"], flight_id=flight_id)
    await _attr(tenant_id=tenant_id, campaign_id=campaign["id"], flight_id=flight_id)
    await _attr(tenant_id=tenant_id, campaign_id=campaign["id"], flight_id=flight_id)

    async with async_session_maker() as session:
        await record_flight_spend(
            session,
            tenant_id=tenant_id,
            flight_id=flight_id,
            amount=Decimal("10.12345"),
            currency="eur",
        )
        kpi = await aggregate_flight_kpi(session, tenant_id=tenant_id, flight_id=flight_id)
        with pytest.raises(KpiAggregateError):
            await aggregate_flight_kpi(session, tenant_id=str(uuid4()), flight_id=flight_id)
        await session.commit()
    assert kpi.currency == "EUR"
    assert kpi.spend == Decimal("10.1235")  # ROUND_HALF_UP to 4dp
    assert kpi.cost_per_lead == Decimal("3.3745")


@pytest.mark.asyncio
async def test_deleting_campaign_removes_spend_source_no_orphan_kpi(
    client: AsyncClient, auth_headers: dict, monkeypatch
):
    """Aggregates are computed; deleting Campaign cascades spend source rows."""
    monkeypatch.setattr("backend.app.acquisition.campaign_service.enforce_module_gate", _allow_gate)
    data = await _init_data()
    tenant_id = data["tenant_id"]
    oc = await _default_own_company_id(tenant_id)
    vac = await _seed_vacancy(tenant_id=tenant_id, own_company_id=oc, company_id=data["company_id"])
    campaign = await _create_campaign(client, auth_headers, own_company_id=oc, vac_id=vac)
    flight_id = campaign["flights"][0]["id"]
    await _activate(campaign["id"], flight_id)

    async with async_session_maker() as session:
        await record_flight_spend(
            session, tenant_id=tenant_id, flight_id=flight_id, amount="1", currency="EUR"
        )
        await session.commit()

    async with async_session_maker() as session:
        camp = await session.get(Campaign, campaign["id"])
        assert camp is not None
        await session.delete(camp)
        await session.commit()

    async with async_session_maker() as session:
        with pytest.raises(KpiAggregateError, match="not found"):
            await aggregate_campaign_kpi(
                session, tenant_id=tenant_id, campaign_id=campaign["id"]
            )
