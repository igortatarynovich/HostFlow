"""ADR-024 Epic P — end-to-end public contract.

Campaign → Flight → Endpoint → Submission → Result → Outcome → KPI

Uses public Acquisition / Intake contracts and platform Campaign APIs.
Does **not** insert attribution/outcome/KPI rows by hand.
"""

from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import inspect, select

from backend.app.acquisition.kpi_aggregates import (
    aggregate_campaign_kpi,
    aggregate_flight_kpi,
    qualify_attribution,
    record_flight_spend,
)
from backend.app.acquisition.outcome_service import (
    STATUS_COMPLETED,
    apply_attribution_to_outcome,
    create_outcome,
)
from backend.app.acquisition.result_attribution import (
    RESULT_TYPE_INTAKE_LEAD,
    get_attribution_for_result,
    record_result_attribution_from_routing,
)
from backend.app.acquisition.submission_routing import (
    resolve_universal_submission_routing,
    stamp_acquisition_routing_on_lead,
)
from backend.app.db.session import async_session_maker
from backend.app.intake_platform.schemas import EffectivePolicy, SubmissionPolicy
from backend.app.intake_platform.submission_store import append_submission, list_submissions
from backend.app.models.campaign import (
    Campaign,
    CampaignFlightSpendEntry,
    CampaignOutcome,
    CampaignOutcomeResultLink,
    CampaignResultAttribution,
    CampaignResultQualification,
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


def _company_headers(auth_headers: dict, own_company_id: str) -> dict:
    return {**auth_headers, "X-Own-Company-Id": own_company_id}


@pytest.mark.asyncio
async def test_epic_p_public_chain_campaign_to_kpi(
    client: AsyncClient, auth_headers: dict, monkeypatch
):
    """Full public chain through services/contracts (Epic P DoD)."""
    monkeypatch.setattr("backend.app.acquisition.campaign_service.enforce_module_gate", _allow_gate)
    data = await _init_data()
    tenant_id = data["tenant_id"]
    oc = await _default_own_company_id(tenant_id)

    # --- Campaign + Flight (platform API) ---
    vac_id = str(uuid4())
    form_id = str(uuid4())
    async with async_session_maker() as session:
        session.add(
            Vacancy(
                id=vac_id,
                tenant_id=tenant_id,
                own_company_id=oc,
                company_id=data["company_id"],
                title="Epic P Drivers",
                status="open",
                is_active=True,
                is_archived=False,
            )
        )
        session.add(
            TenantLeadForm(
                id=form_id,
                tenant_id=tenant_id,
                title="Epic P Form",
                public_slug=f"epic-p-{form_id[:8]}",
                is_active=True,
                lifecycle_status="active",
                purpose="inquiry",
            )
        )
        await session.commit()

    resp = await client.post(
        "/api/v1/platform/campaigns",
        headers=_company_headers(auth_headers, oc),
        json={
            "name": "Epic P vertical",
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
    campaign = resp.json()
    campaign_id = campaign["id"]
    flight_id = campaign["flights"][0]["id"]
    assert campaign["current_flight_id"] == flight_id

    async with async_session_maker() as session:
        camp = await session.get(Campaign, campaign_id)
        flight = await session.get(CampaignRun, flight_id)
        assert camp and flight
        camp.status = "active"
        flight.status = "active"
        await session.commit()

    # --- Endpoint binding (Form is-a Endpoint specialization) ---
    hdrs = _company_headers(auth_headers, oc)
    bind = await client.post(
        f"/api/v1/platform/campaigns/{campaign_id}/forms",
        headers=hdrs,
        json={"form_id": form_id, "role": "primary"},
    )
    assert bind.status_code == 201, bind.text

    # --- Endpoint → Submission → Result attribution (routing + store + attribution services) ---
    lead_id = str(uuid4())
    async with async_session_maker() as session:
        decision = await resolve_universal_submission_routing(
            session,
            tenant_id=tenant_id,
            form_id=form_id,
            intake_source_profile_id=None,
        )
        assert decision.status == "routed"
        assert decision.campaign_id == campaign_id
        assert decision.campaign_run_id == flight_id
        assert decision.form_id == form_id

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

        policy = EffectivePolicy(
            purpose="inquiry",
            target_entity_profile_code="candidate",
            submission_policy=SubmissionPolicy(mode="create"),
            form_id=form_id,
            published_version=1,
            source={"endpoint_type": "hostflow_public_form"},
        )
        submission = await append_submission(
            session,
            tenant_id=tenant_id,
            lead_id=lead_id,
            effective_policy=policy,
            normalized_values={"email": "epic-p@example.com"},
            entry_context={"acquisition_routing_v1": decision.to_dict()},
            idempotency_key=f"epic-p-{lead_id}",
        )
        submission_id = str(submission["submission_id"])
        assert submission_id
        assert list_submissions(lead)

        attribution = await record_result_attribution_from_routing(
            session,
            tenant_id=tenant_id,
            lead=lead,
            submission_id=submission_id,
            result_type=RESULT_TYPE_INTAKE_LEAD,
            result_id=lead_id,
        )
        assert attribution.campaign_id == campaign_id
        assert attribution.campaign_run_id == flight_id
        assert attribution.endpoint_form_id == form_id
        assert attribution.submission_id == submission_id
        attr_id = str(attribution.id)

        # --- Outcome from attributed Result (separate service; not intake hook) ---
        outcome = await create_outcome(
            session,
            tenant_id=tenant_id,
            campaign_id=campaign_id,
            flight_id=flight_id,
            progress_target=1,
        )
        outcome, _link, applied = await apply_attribution_to_outcome(
            session,
            tenant_id=tenant_id,
            outcome_id=outcome.id,
            attribution_id=attr_id,
        )
        assert applied is True
        assert outcome.status == STATUS_COMPLETED
        assert outcome.progress_current == 1

        # --- Spend + KPI ---
        await record_flight_spend(
            session,
            tenant_id=tenant_id,
            flight_id=flight_id,
            amount="100.00",
            currency="EUR",
        )
        await qualify_attribution(session, tenant_id=tenant_id, attribution_id=attr_id)

        flight_kpi = await aggregate_flight_kpi(
            session, tenant_id=tenant_id, flight_id=flight_id
        )
        campaign_kpi = await aggregate_campaign_kpi(
            session, tenant_id=tenant_id, campaign_id=campaign_id
        )
        await session.commit()

    assert flight_kpi.leads == 1
    assert flight_kpi.qualified == 1
    assert flight_kpi.outcomes_completed == 1
    assert flight_kpi.converted == 1
    assert flight_kpi.spend == Decimal("100.0000")
    assert flight_kpi.cost_per_lead == Decimal("100.0000")
    assert flight_kpi.cost_per_outcome == Decimal("100.0000")

    assert campaign_kpi.spend == flight_kpi.spend
    assert campaign_kpi.leads == flight_kpi.leads
    assert campaign_kpi.qualified == flight_kpi.qualified
    assert campaign_kpi.converted == flight_kpi.converted
    assert campaign_kpi.outcomes_completed == flight_kpi.outcomes_completed
    assert campaign_kpi.cost_per_lead == flight_kpi.cost_per_lead
    assert campaign_kpi.cost_per_outcome == flight_kpi.cost_per_outcome

    # Ownership: Acquisition models still do not own Operations domain tables.
    forbidden = {
        "candidates",
        "recruitment_applications",
        "sales_inquiries",
        "inquiries",
        "client_accounts",
        "companies",
        "leads",
    }
    for model in (
        Campaign,
        CampaignRun,
        CampaignTarget,
        CampaignRunForm,
        CampaignRunIntakeSource,
        CampaignResultAttribution,
        CampaignOutcome,
        CampaignOutcomeResultLink,
        CampaignFlightSpendEntry,
        CampaignResultQualification,
    ):
        fk_tables = {
            fk.column.table.name for col in inspect(model).columns for fk in col.foreign_keys
        }
        assert not (fk_tables & forbidden)

    async with async_session_maker() as session:
        loaded = await get_attribution_for_result(
            session,
            tenant_id=tenant_id,
            result_type=RESULT_TYPE_INTAKE_LEAD,
            result_id=lead_id,
        )
        assert loaded is not None
        assert loaded.campaign_id == campaign_id
        assert loaded.campaign_run_id == flight_id
        assert loaded.endpoint_form_id == form_id
        assert loaded.submission_id == submission_id
