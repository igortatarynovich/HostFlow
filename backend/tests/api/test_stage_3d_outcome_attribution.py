"""ADR-024 Stage 3D PR-1 — Result attribution from Universal Routing.

Full chain Outcome/KPI coverage lands in later 3D PRs; this module locks:
- automatic attribution from ``acquisition_routing_v1`` + submission_id
- no manual campaign/flight override
- ownership: no FK to Operations domain tables
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import inspect, select

from backend.app.acquisition.result_attribution import (
    RESULT_TYPE_INTAKE_LEAD,
    AttributionError,
    build_attribution_from_routing,
    get_attribution_for_result,
    get_attribution_for_submission,
    record_result_attribution_from_routing,
)
from backend.app.acquisition.submission_routing import (
    ACQUISITION_ROUTING_V1_KEY,
    RoutingDecisionStatus,
    RoutingSource,
    stamp_acquisition_routing_on_lead,
    UniversalRoutingDecision,
)
from backend.app.db.session import async_session_maker
from backend.app.models.campaign import (
    Campaign,
    CampaignResultAttribution,
    CampaignRun,
    CampaignRunForm,
    CampaignRunIntakeSource,
    CampaignTarget,
)
from backend.app.models.lead import Lead
from backend.app.models.own_company import OwnCompany
from backend.app.models.tenant_lead_form import TenantLeadForm
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


async def _seed_form(*, tenant_id: str) -> str:
    form_id = str(uuid4())
    async with async_session_maker() as session:
        session.add(
            TenantLeadForm(
                id=form_id,
                tenant_id=tenant_id,
                title="Form 3D",
                public_slug=f"form-{form_id[:8]}",
                is_active=True,
                lifecycle_status="active",
                purpose="inquiry",
            )
        )
        await session.commit()
    return form_id


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
            "name": "Stage 3D campaign",
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


async def _attach_form(client, headers, campaign_id: str, form_id: str) -> None:
    resp = await client.post(
        f"/api/v1/platform/campaigns/{campaign_id}/forms",
        headers=headers,
        json={"form_id": form_id, "role": "primary"},
    )
    assert resp.status_code == 201, resp.text


def _routed_decision(
    *,
    campaign_id: str,
    flight_id: str,
    form_id: str | None = None,
    profile_id: str | None = None,
) -> UniversalRoutingDecision:
    return UniversalRoutingDecision(
        status=RoutingDecisionStatus.routed.value,
        route_intent="candidate_application",
        campaign_id=campaign_id,
        campaign_run_id=flight_id,
        campaign_target_id=None,
        intake_source_profile_id=profile_id,
        form_id=form_id,
        source=RoutingSource.campaign_target.value,
        unresolved_reason=None,
        warnings=(),
        decided_at="2026-07-18T12:00:00+00:00",
    )


async def _seed_lead_with_routing(
    *,
    tenant_id: str,
    decision: UniversalRoutingDecision,
) -> Lead:
    lead_id = str(uuid4())
    async with async_session_maker() as session:
        lead = Lead(
            id=lead_id,
            tenant_id=tenant_id,
            status="new",
            stage="questionnaire_submitted",
            normalized={},
        )
        stamp_acquisition_routing_on_lead(lead, decision)
        session.add(lead)
        await session.commit()
        await session.refresh(lead)
        return lead


def test_result_attribution_model_does_not_own_operations_domain():
    forbidden = {
        "candidates",
        "recruitment_applications",
        "sales_inquiries",
        "inquiries",
        "client_accounts",
        "companies",
        "leads",
    }
    fk_tables = {
        fk.column.table.name
        for col in inspect(CampaignResultAttribution).columns
        for fk in col.foreign_keys
    }
    assert not (fk_tables & forbidden)
    assert fk_tables <= {"acq_campaigns", "acq_campaign_runs"}


def test_build_attribution_requires_routed_campaign_stamp():
    lead = Lead(id=str(uuid4()), tenant_id=str(uuid4()), normalized={})
    with pytest.raises(AttributionError, match="missing"):
        build_attribution_from_routing(
            lead=lead,
            submission_id=str(uuid4()),
            result_type=RESULT_TYPE_INTAKE_LEAD,
            result_id=str(lead.id),
        )

    lead.normalized = {
        ACQUISITION_ROUTING_V1_KEY: {
            "status": "unresolved",
            "campaign_id": str(uuid4()),
            "campaign_run_id": str(uuid4()),
        }
    }
    with pytest.raises(AttributionError, match="routed"):
        build_attribution_from_routing(
            lead=lead,
            submission_id=str(uuid4()),
            result_type=RESULT_TYPE_INTAKE_LEAD,
            result_id=str(lead.id),
        )


@pytest.mark.asyncio
async def test_record_attribution_from_routing_persists_chain_links(
    client: AsyncClient, auth_headers: dict, monkeypatch
):
    monkeypatch.setattr("backend.app.acquisition.campaign_service.enforce_module_gate", _allow_gate)
    data = await _init_data()
    tenant_id = data["tenant_id"]
    oc = await _default_own_company_id(tenant_id)
    vac = await _seed_vacancy(tenant_id=tenant_id, own_company_id=oc, company_id=data["company_id"])
    form_id = await _seed_form(tenant_id=tenant_id)

    campaign = await _create_campaign(client, auth_headers, own_company_id=oc, vac_id=vac)
    flight_id = campaign["flights"][0]["id"]
    await _activate_campaign_and_flight(campaign["id"], flight_id)
    hdrs = _company_headers(auth_headers, oc)
    await _attach_form(client, hdrs, campaign["id"], form_id)

    decision = _routed_decision(
        campaign_id=campaign["id"], flight_id=flight_id, form_id=form_id
    )
    lead = await _seed_lead_with_routing(tenant_id=tenant_id, decision=decision)
    submission_id = str(uuid4())

    async with async_session_maker() as session:
        db_lead = await session.get(Lead, lead.id)
        assert db_lead is not None
        row = await record_result_attribution_from_routing(
            session,
            tenant_id=tenant_id,
            lead=db_lead,
            submission_id=submission_id,
            result_type=RESULT_TYPE_INTAKE_LEAD,
            result_id=str(db_lead.id),
        )
        await session.commit()
        assert row.campaign_id == campaign["id"]
        assert row.campaign_run_id == flight_id
        assert row.endpoint_form_id == form_id
        assert row.submission_id == submission_id
        assert row.lead_id == str(db_lead.id)

    async with async_session_maker() as session:
        loaded = await get_attribution_for_result(
            session,
            tenant_id=tenant_id,
            result_type=RESULT_TYPE_INTAKE_LEAD,
            result_id=str(lead.id),
        )
        assert loaded is not None
        assert loaded.campaign_id == campaign["id"]
        assert loaded.campaign_run_id == flight_id
        assert loaded.endpoint_form_id == form_id
        assert loaded.submission_id == submission_id

        by_sub = await get_attribution_for_submission(
            session, tenant_id=tenant_id, submission_id=submission_id
        )
        assert by_sub is not None
        assert by_sub.id == loaded.id


@pytest.mark.asyncio
async def test_manual_attribution_override_is_rejected(
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

    decision = _routed_decision(campaign_id=campaign["id"], flight_id=flight_id)
    lead = await _seed_lead_with_routing(tenant_id=tenant_id, decision=decision)

    async with async_session_maker() as session:
        db_lead = await session.get(Lead, lead.id)
        assert db_lead is not None
        with pytest.raises(AttributionError, match="manual attribution"):
            await record_result_attribution_from_routing(
                session,
                tenant_id=tenant_id,
                lead=db_lead,
                submission_id=str(uuid4()),
                result_type=RESULT_TYPE_INTAKE_LEAD,
                result_id=str(db_lead.id),
                campaign_id=str(uuid4()),
            )


@pytest.mark.asyncio
async def test_attribution_idempotent_and_preserves_links(
    client: AsyncClient, auth_headers: dict, monkeypatch
):
    monkeypatch.setattr("backend.app.acquisition.campaign_service.enforce_module_gate", _allow_gate)
    data = await _init_data()
    tenant_id = data["tenant_id"]
    oc = await _default_own_company_id(tenant_id)
    vac = await _seed_vacancy(tenant_id=tenant_id, own_company_id=oc, company_id=data["company_id"])
    form_id = await _seed_form(tenant_id=tenant_id)

    campaign = await _create_campaign(client, auth_headers, own_company_id=oc, vac_id=vac)
    flight_id = campaign["flights"][0]["id"]
    await _activate_campaign_and_flight(campaign["id"], flight_id)
    hdrs = _company_headers(auth_headers, oc)
    await _attach_form(client, hdrs, campaign["id"], form_id)

    decision = _routed_decision(
        campaign_id=campaign["id"], flight_id=flight_id, form_id=form_id
    )
    lead = await _seed_lead_with_routing(tenant_id=tenant_id, decision=decision)
    submission_id = str(uuid4())

    async with async_session_maker() as session:
        db_lead = await session.get(Lead, lead.id)
        assert db_lead is not None
        first = await record_result_attribution_from_routing(
            session,
            tenant_id=tenant_id,
            lead=db_lead,
            submission_id=submission_id,
            result_type=RESULT_TYPE_INTAKE_LEAD,
            result_id=str(db_lead.id),
        )
        second = await record_result_attribution_from_routing(
            session,
            tenant_id=tenant_id,
            lead=db_lead,
            submission_id=submission_id,
            result_type=RESULT_TYPE_INTAKE_LEAD,
            result_id=str(db_lead.id),
        )
        await session.commit()
        assert first.id == second.id
        assert second.campaign_id == campaign["id"]
        assert second.campaign_run_id == flight_id
        assert second.endpoint_form_id == form_id


@pytest.mark.asyncio
async def test_deleting_campaign_cascades_attribution_not_domain_tables(
    client: AsyncClient, auth_headers: dict, monkeypatch
):
    """Forbidden-object rule: attribution rows cascade with Campaign; Lead stays."""
    monkeypatch.setattr("backend.app.acquisition.campaign_service.enforce_module_gate", _allow_gate)
    data = await _init_data()
    tenant_id = data["tenant_id"]
    oc = await _default_own_company_id(tenant_id)
    vac = await _seed_vacancy(tenant_id=tenant_id, own_company_id=oc, company_id=data["company_id"])

    campaign = await _create_campaign(client, auth_headers, own_company_id=oc, vac_id=vac)
    flight_id = campaign["flights"][0]["id"]
    await _activate_campaign_and_flight(campaign["id"], flight_id)

    decision = _routed_decision(campaign_id=campaign["id"], flight_id=flight_id)
    lead = await _seed_lead_with_routing(tenant_id=tenant_id, decision=decision)
    submission_id = str(uuid4())

    async with async_session_maker() as session:
        db_lead = await session.get(Lead, lead.id)
        assert db_lead is not None
        await record_result_attribution_from_routing(
            session,
            tenant_id=tenant_id,
            lead=db_lead,
            submission_id=submission_id,
            result_type=RESULT_TYPE_INTAKE_LEAD,
            result_id=str(db_lead.id),
        )
        await session.commit()

    async with async_session_maker() as session:
        camp = await session.get(Campaign, campaign["id"])
        assert camp is not None
        await session.delete(camp)
        await session.commit()

    async with async_session_maker() as session:
        assert await session.get(Lead, lead.id) is not None
        remaining = await session.execute(
            select(CampaignResultAttribution).where(
                CampaignResultAttribution.tenant_id == tenant_id,
                CampaignResultAttribution.submission_id == submission_id,
            )
        )
        assert remaining.scalar_one_or_none() is None


@pytest.mark.asyncio
@pytest.mark.xfail(reason="Epic P PR-3: Primary KPI aggregates not implemented yet", strict=False)
async def test_chain_skeleton_kpi_aggregates_placeholder():
    """Contract-test skeleton: Flight/Campaign KPI roll-up (filled in PR-3)."""
    raise AssertionError("KPI aggregates pending Epic P PR-3")


def test_stage_3d_models_export_includes_attribution():
    # Ensure association models from prior stages remain importable alongside 3D.
    assert CampaignRunForm.__tablename__ == "acq_campaign_run_forms"
    assert CampaignRunIntakeSource.__tablename__ == "acq_campaign_run_intake_sources"
    assert CampaignTarget.__tablename__ == "acq_campaign_targets"
    assert CampaignResultAttribution.__tablename__ == "acq_result_attributions"
