"""ADR-024 Stage 3D PR-2 — Outcome lifecycle + attributed Result ledger."""

from __future__ import annotations

from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import inspect, select

from backend.app.acquisition.outcome_service import (
    STATUS_ACTIVE,
    STATUS_CANCELLED,
    STATUS_COMPLETED,
    STATUS_CREATED,
    STATUS_FAILED,
    OutcomeError,
    apply_attribution_to_outcome,
    create_outcome,
    get_outcome,
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
from backend.app.models.campaign import (
    Campaign,
    CampaignOutcome,
    CampaignOutcomeResultLink,
    CampaignRun,
)
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
    name: str = "Stage 3D Outcome",
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


async def _activate_campaign_and_flight(campaign_id: str, flight_id: str) -> None:
    async with async_session_maker() as session:
        campaign = await session.get(Campaign, campaign_id)
        flight = await session.get(CampaignRun, flight_id)
        assert campaign and flight
        campaign.status = "active"
        flight.status = "active"
        await session.commit()


def _routed_decision(*, campaign_id: str, flight_id: str) -> UniversalRoutingDecision:
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


async def _record_attribution(
    *,
    tenant_id: str,
    campaign_id: str,
    flight_id: str,
    result_id: str | None = None,
) -> str:
    lead_id = str(uuid4())
    rid = result_id or lead_id
    decision = _routed_decision(campaign_id=campaign_id, flight_id=flight_id)
    async with async_session_maker() as session:
        lead = Lead(
            id=lead_id,
            tenant_id=tenant_id,
            status="new",
            stage="questionnaire_submitted",
            normalized={},
            payload={},
        )
        stamp_acquisition_routing_on_lead(lead, decision)
        session.add(lead)
        await session.flush()
        attr = await record_result_attribution_from_routing(
            session,
            tenant_id=tenant_id,
            lead=lead,
            submission_id=str(uuid4()),
            result_type=RESULT_TYPE_INTAKE_LEAD,
            result_id=rid,
        )
        await session.commit()
        return str(attr.id)


def test_outcome_models_do_not_own_operations_domain():
    forbidden = {
        "candidates",
        "recruitment_applications",
        "sales_inquiries",
        "inquiries",
        "client_accounts",
        "companies",
        "leads",
    }
    for model in (CampaignOutcome, CampaignOutcomeResultLink):
        fk_tables = {
            fk.column.table.name for col in inspect(model).columns for fk in col.foreign_keys
        }
        assert not (fk_tables & forbidden)


@pytest.mark.asyncio
async def test_first_attributed_result_activates_outcome(
    client: AsyncClient, auth_headers: dict, monkeypatch
):
    monkeypatch.setattr("backend.app.acquisition.campaign_service.enforce_module_gate", _allow_gate)
    data = await _init_data()
    tenant_id = data["tenant_id"]
    oc = await _default_own_company_id(tenant_id)
    vac = await _seed_vacancy(tenant_id=tenant_id, own_company_id=oc, company_id=data["company_id"])
    campaign = await _create_campaign(client, auth_headers, own_company_id=oc, vac_id=vac)
    flight_id = campaign["flights"][0]["id"]
    await _activate_campaign_and_flight(campaign["id"], flight_id)

    attr_id = await _record_attribution(
        tenant_id=tenant_id, campaign_id=campaign["id"], flight_id=flight_id
    )

    async with async_session_maker() as session:
        outcome = await create_outcome(
            session,
            tenant_id=tenant_id,
            campaign_id=campaign["id"],
            flight_id=flight_id,
            progress_target=2,
        )
        assert outcome.status == STATUS_CREATED
        outcome, _link, applied = await apply_attribution_to_outcome(
            session, tenant_id=tenant_id, outcome_id=outcome.id, attribution_id=attr_id
        )
        await session.commit()
        assert applied is True
        assert outcome.status == STATUS_ACTIVE
        assert outcome.progress_current == 1
        assert outcome.activated_at is not None


@pytest.mark.asyncio
async def test_reprocessing_same_result_is_idempotent(
    client: AsyncClient, auth_headers: dict, monkeypatch
):
    monkeypatch.setattr("backend.app.acquisition.campaign_service.enforce_module_gate", _allow_gate)
    data = await _init_data()
    tenant_id = data["tenant_id"]
    oc = await _default_own_company_id(tenant_id)
    vac = await _seed_vacancy(tenant_id=tenant_id, own_company_id=oc, company_id=data["company_id"])
    campaign = await _create_campaign(client, auth_headers, own_company_id=oc, vac_id=vac)
    flight_id = campaign["flights"][0]["id"]
    await _activate_campaign_and_flight(campaign["id"], flight_id)
    attr_id = await _record_attribution(
        tenant_id=tenant_id, campaign_id=campaign["id"], flight_id=flight_id
    )

    async with async_session_maker() as session:
        outcome = await create_outcome(
            session,
            tenant_id=tenant_id,
            campaign_id=campaign["id"],
            flight_id=flight_id,
            progress_target=3,
        )
        await apply_attribution_to_outcome(
            session, tenant_id=tenant_id, outcome_id=outcome.id, attribution_id=attr_id
        )
        outcome, _link, applied = await apply_attribution_to_outcome(
            session, tenant_id=tenant_id, outcome_id=outcome.id, attribution_id=attr_id
        )
        await session.commit()
        assert applied is False
        assert outcome.progress_current == 1


@pytest.mark.asyncio
async def test_two_results_increase_progress_to_two_and_complete(
    client: AsyncClient, auth_headers: dict, monkeypatch
):
    monkeypatch.setattr("backend.app.acquisition.campaign_service.enforce_module_gate", _allow_gate)
    data = await _init_data()
    tenant_id = data["tenant_id"]
    oc = await _default_own_company_id(tenant_id)
    vac = await _seed_vacancy(tenant_id=tenant_id, own_company_id=oc, company_id=data["company_id"])
    campaign = await _create_campaign(client, auth_headers, own_company_id=oc, vac_id=vac)
    flight_id = campaign["flights"][0]["id"]
    await _activate_campaign_and_flight(campaign["id"], flight_id)
    a1 = await _record_attribution(
        tenant_id=tenant_id, campaign_id=campaign["id"], flight_id=flight_id
    )
    a2 = await _record_attribution(
        tenant_id=tenant_id, campaign_id=campaign["id"], flight_id=flight_id
    )

    async with async_session_maker() as session:
        outcome = await create_outcome(
            session,
            tenant_id=tenant_id,
            campaign_id=campaign["id"],
            flight_id=flight_id,
            progress_target=2,
        )
        await apply_attribution_to_outcome(
            session, tenant_id=tenant_id, outcome_id=outcome.id, attribution_id=a1
        )
        outcome, _link, applied = await apply_attribution_to_outcome(
            session, tenant_id=tenant_id, outcome_id=outcome.id, attribution_id=a2
        )
        await session.commit()
        assert applied is True
        assert outcome.progress_current == 2
        assert outcome.status == STATUS_COMPLETED
        assert outcome.completed_at is not None


@pytest.mark.asyncio
async def test_result_from_other_campaign_is_rejected(
    client: AsyncClient, auth_headers: dict, monkeypatch
):
    monkeypatch.setattr("backend.app.acquisition.campaign_service.enforce_module_gate", _allow_gate)
    data = await _init_data()
    tenant_id = data["tenant_id"]
    oc = await _default_own_company_id(tenant_id)
    vac = await _seed_vacancy(tenant_id=tenant_id, own_company_id=oc, company_id=data["company_id"])
    c1 = await _create_campaign(client, auth_headers, own_company_id=oc, vac_id=vac, name="C1")
    c2 = await _create_campaign(client, auth_headers, own_company_id=oc, vac_id=vac, name="C2")
    await _activate_campaign_and_flight(c1["id"], c1["flights"][0]["id"])
    await _activate_campaign_and_flight(c2["id"], c2["flights"][0]["id"])
    foreign_attr = await _record_attribution(
        tenant_id=tenant_id, campaign_id=c2["id"], flight_id=c2["flights"][0]["id"]
    )

    async with async_session_maker() as session:
        outcome = await create_outcome(
            session,
            tenant_id=tenant_id,
            campaign_id=c1["id"],
            flight_id=c1["flights"][0]["id"],
            progress_target=1,
        )
        with pytest.raises(OutcomeError, match="campaign/flight"):
            await apply_attribution_to_outcome(
                session,
                tenant_id=tenant_id,
                outcome_id=outcome.id,
                attribution_id=foreign_attr,
            )


@pytest.mark.asyncio
async def test_terminal_outcome_does_not_reactivate(
    client: AsyncClient, auth_headers: dict, monkeypatch
):
    monkeypatch.setattr("backend.app.acquisition.campaign_service.enforce_module_gate", _allow_gate)
    data = await _init_data()
    tenant_id = data["tenant_id"]
    oc = await _default_own_company_id(tenant_id)
    vac = await _seed_vacancy(tenant_id=tenant_id, own_company_id=oc, company_id=data["company_id"])
    campaign = await _create_campaign(client, auth_headers, own_company_id=oc, vac_id=vac)
    flight_id = campaign["flights"][0]["id"]
    await _activate_campaign_and_flight(campaign["id"], flight_id)
    a1 = await _record_attribution(
        tenant_id=tenant_id, campaign_id=campaign["id"], flight_id=flight_id
    )
    a2 = await _record_attribution(
        tenant_id=tenant_id, campaign_id=campaign["id"], flight_id=flight_id
    )

    async with async_session_maker() as session:
        outcome = await create_outcome(
            session,
            tenant_id=tenant_id,
            campaign_id=campaign["id"],
            flight_id=flight_id,
            progress_target=1,
        )
        await apply_attribution_to_outcome(
            session, tenant_id=tenant_id, outcome_id=outcome.id, attribution_id=a1
        )
        assert outcome.status == STATUS_COMPLETED
        with pytest.raises(OutcomeError, match="rejects progress"):
            await apply_attribution_to_outcome(
                session, tenant_id=tenant_id, outcome_id=outcome.id, attribution_id=a2
            )
        await session.commit()


@pytest.mark.asyncio
async def test_failed_and_cancelled_reject_progress_mutations(
    client: AsyncClient, auth_headers: dict, monkeypatch
):
    monkeypatch.setattr("backend.app.acquisition.campaign_service.enforce_module_gate", _allow_gate)
    data = await _init_data()
    tenant_id = data["tenant_id"]
    oc = await _default_own_company_id(tenant_id)
    vac = await _seed_vacancy(tenant_id=tenant_id, own_company_id=oc, company_id=data["company_id"])
    campaign = await _create_campaign(client, auth_headers, own_company_id=oc, vac_id=vac)
    flight_id = campaign["flights"][0]["id"]
    await _activate_campaign_and_flight(campaign["id"], flight_id)

    async with async_session_maker() as session:
        failed = await create_outcome(
            session,
            tenant_id=tenant_id,
            campaign_id=campaign["id"],
            flight_id=flight_id,
            progress_target=2,
        )
        # activate then fail
        a1 = await _record_attribution(
            tenant_id=tenant_id, campaign_id=campaign["id"], flight_id=flight_id
        )
        await apply_attribution_to_outcome(
            session, tenant_id=tenant_id, outcome_id=failed.id, attribution_id=a1
        )
        await mark_outcome_failed(session, tenant_id=tenant_id, outcome_id=failed.id)
        assert failed.status == STATUS_FAILED
        a2 = await _record_attribution(
            tenant_id=tenant_id, campaign_id=campaign["id"], flight_id=flight_id
        )
        with pytest.raises(OutcomeError, match="rejects progress"):
            await apply_attribution_to_outcome(
                session, tenant_id=tenant_id, outcome_id=failed.id, attribution_id=a2
            )

        cancelled = await create_outcome(
            session,
            tenant_id=tenant_id,
            campaign_id=campaign["id"],
            flight_id=flight_id,
            progress_target=2,
        )
        await mark_outcome_cancelled(session, tenant_id=tenant_id, outcome_id=cancelled.id)
        assert cancelled.status == STATUS_CANCELLED
        a3 = await _record_attribution(
            tenant_id=tenant_id, campaign_id=campaign["id"], flight_id=flight_id
        )
        with pytest.raises(OutcomeError, match="rejects progress"):
            await apply_attribution_to_outcome(
                session, tenant_id=tenant_id, outcome_id=cancelled.id, attribution_id=a3
            )
        await session.commit()


@pytest.mark.asyncio
async def test_tenant_isolation_on_outcome_get(
    client: AsyncClient, auth_headers: dict, monkeypatch
):
    monkeypatch.setattr("backend.app.acquisition.campaign_service.enforce_module_gate", _allow_gate)
    data = await _init_data()
    tenant_id = data["tenant_id"]
    oc = await _default_own_company_id(tenant_id)
    vac = await _seed_vacancy(tenant_id=tenant_id, own_company_id=oc, company_id=data["company_id"])
    campaign = await _create_campaign(client, auth_headers, own_company_id=oc, vac_id=vac)
    flight_id = campaign["flights"][0]["id"]
    await _activate_campaign_and_flight(campaign["id"], flight_id)

    async with async_session_maker() as session:
        outcome = await create_outcome(
            session,
            tenant_id=tenant_id,
            campaign_id=campaign["id"],
            flight_id=flight_id,
            progress_target=1,
        )
        await session.commit()
        oid = outcome.id

    async with async_session_maker() as session:
        assert await get_outcome(session, tenant_id=tenant_id, outcome_id=oid) is not None
        assert await get_outcome(session, tenant_id=str(uuid4()), outcome_id=oid) is None


@pytest.mark.asyncio
async def test_soft_revoke_does_not_decrease_progress(
    client: AsyncClient, auth_headers: dict, monkeypatch
):
    """Policy: Result deletion soft-revokes ledger; progress stays (no COUNT(*) recalc)."""
    monkeypatch.setattr("backend.app.acquisition.campaign_service.enforce_module_gate", _allow_gate)
    data = await _init_data()
    tenant_id = data["tenant_id"]
    oc = await _default_own_company_id(tenant_id)
    vac = await _seed_vacancy(tenant_id=tenant_id, own_company_id=oc, company_id=data["company_id"])
    campaign = await _create_campaign(client, auth_headers, own_company_id=oc, vac_id=vac)
    flight_id = campaign["flights"][0]["id"]
    await _activate_campaign_and_flight(campaign["id"], flight_id)
    result_id = str(uuid4())
    attr_id = await _record_attribution(
        tenant_id=tenant_id,
        campaign_id=campaign["id"],
        flight_id=flight_id,
        result_id=result_id,
    )

    async with async_session_maker() as session:
        outcome = await create_outcome(
            session,
            tenant_id=tenant_id,
            campaign_id=campaign["id"],
            flight_id=flight_id,
            progress_target=3,
        )
        await apply_attribution_to_outcome(
            session, tenant_id=tenant_id, outcome_id=outcome.id, attribution_id=attr_id
        )
        assert outcome.progress_current == 1
        link = await soft_revoke_outcome_result(
            session,
            tenant_id=tenant_id,
            outcome_id=outcome.id,
            result_type=RESULT_TYPE_INTAKE_LEAD,
            result_id=result_id,
            reason="result_deleted",
        )
        await session.refresh(outcome)
        await session.commit()
        assert link.revoked_at is not None
        assert outcome.progress_current == 1
        assert outcome.status == STATUS_ACTIVE
