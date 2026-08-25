"""ADR-024 Stage 3C — Universal Submission Routing."""

from __future__ import annotations

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import inspect, select

from backend.app.acquisition.submission_routing import (
    ACQUISITION_ROUTING_V1_KEY,
    UnresolvedReason,
    resolve_universal_submission_routing,
)
from backend.app.db.session import async_session_maker
from backend.app.intake_platform.schemas import EffectivePolicy, SubmissionPolicy
from backend.app.intake_platform.submission_store import append_submission, list_submissions
from backend.app.models.campaign import (
    Campaign,
    CampaignRun,
    CampaignRunForm,
    CampaignRunIntakeSource,
    CampaignTarget,
)
from backend.app.models.intake_routing import IntakeSourceBinding, IntakeSourceProfile
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


async def _seed_form(*, tenant_id: str, title: str = "Form") -> str:
    form_id = str(uuid4())
    async with async_session_maker() as session:
        session.add(
            TenantLeadForm(
                id=form_id,
                tenant_id=tenant_id,
                title=title,
                public_slug=f"form-{form_id[:8]}",
                is_active=True,
                lifecycle_status="active",
                purpose="inquiry",
            )
        )
        await session.commit()
    return form_id


async def _seed_profile(
    *,
    tenant_id: str,
    own_company_id: str,
    route_intent: str = "candidate_application",
    provider: str = "public_intake",
    form_id: str | None = None,
) -> str:
    profile_id = str(uuid4())
    async with async_session_maker() as session:
        session.add(
            IntakeSourceProfile(
                id=profile_id,
                tenant_id=tenant_id,
                code=f"src-{profile_id[:8]}",
                name="Intake",
                provider=provider,
                channel="organic",
                own_company_id=own_company_id,
                route_intent=route_intent,
                is_active=True,
            )
        )
        await session.flush()
        if form_id:
            session.add(
                IntakeSourceBinding(
                    id=str(uuid4()),
                    tenant_id=tenant_id,
                    intake_source_profile_id=profile_id,
                    provider="public_intake",
                    external_key=f"lead_form_id:{form_id}",
                    external_key_secondary="",
                    label="Public form",
                    is_active=True,
                    priority=10,
                )
            )
        await session.commit()
    return profile_id


def _company_headers(auth_headers: dict, own_company_id: str) -> dict:
    return {**auth_headers, "X-Own-Company-Id": own_company_id}


async def _create_campaign(
    client: AsyncClient,
    headers: dict,
    *,
    own_company_id: str,
    vac_id: str,
    route_intent: str = "candidate_application",
    name: str = "Stage 3C campaign",
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
                    "route_intent": route_intent,
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


async def _attach_profile(client, headers, campaign_id: str, profile_id: str) -> None:
    resp = await client.post(
        f"/api/v1/platform/campaigns/{campaign_id}/intake-sources",
        headers=headers,
        json={"intake_source_profile_id": profile_id, "role": "primary"},
    )
    assert resp.status_code == 201, resp.text


def test_acquisition_routing_models_do_not_own_operations_domain():
    forbidden = {
        "candidates",
        "recruitment_applications",
        "sales_inquiries",
        "inquiries",
        "client_accounts",
        "companies",
    }
    for model in (Campaign, CampaignRun, CampaignTarget, CampaignRunForm, CampaignRunIntakeSource):
        fk_tables = {
            fk.column.table.name for col in inspect(model).columns for fk in col.foreign_keys
        }
        assert not (fk_tables & forbidden)


@pytest.mark.asyncio
async def test_form_only_campaign_routing(client: AsyncClient, auth_headers: dict, monkeypatch):
    monkeypatch.setattr("backend.app.acquisition.campaign_service.enforce_module_gate", _allow_gate)
    data = await _init_data()
    tenant_id = data["tenant_id"]
    oc = await _default_own_company_id(tenant_id)
    vac = await _seed_vacancy(tenant_id=tenant_id, own_company_id=oc, company_id=data["company_id"])
    form_id = await _seed_form(tenant_id=tenant_id)
    profile_id = await _seed_profile(tenant_id=tenant_id, own_company_id=oc, route_intent="sales_inquiry")

    campaign = await _create_campaign(client, auth_headers, own_company_id=oc, vac_id=vac)
    flight_id = campaign["flights"][0]["id"]
    await _activate_campaign_and_flight(campaign["id"], flight_id)
    hdrs = _company_headers(auth_headers, oc)
    await _attach_form(client, hdrs, campaign["id"], form_id)

    async with async_session_maker() as session:
        decision = await resolve_universal_submission_routing(
            session,
            tenant_id=tenant_id,
            form_id=form_id,
            intake_source_profile_id=profile_id,
        )
    assert decision.status == "routed"
    assert decision.source == "campaign_target"
    assert decision.route_intent == "candidate_application"
    assert decision.campaign_run_id == flight_id


@pytest.mark.asyncio
async def test_profile_only_campaign_routing(client: AsyncClient, auth_headers: dict, monkeypatch):
    monkeypatch.setattr("backend.app.acquisition.campaign_service.enforce_module_gate", _allow_gate)
    data = await _init_data()
    tenant_id = data["tenant_id"]
    oc = await _default_own_company_id(tenant_id)
    vac = await _seed_vacancy(tenant_id=tenant_id, own_company_id=oc, company_id=data["company_id"])
    form_id = await _seed_form(tenant_id=tenant_id)
    profile_id = await _seed_profile(tenant_id=tenant_id, own_company_id=oc, route_intent="sales_inquiry")

    campaign = await _create_campaign(
        client, auth_headers, own_company_id=oc, vac_id=vac, route_intent="candidate_application"
    )
    flight_id = campaign["flights"][0]["id"]
    await _activate_campaign_and_flight(campaign["id"], flight_id)
    hdrs = _company_headers(auth_headers, oc)
    await _attach_profile(client, hdrs, campaign["id"], profile_id)

    async with async_session_maker() as session:
        decision = await resolve_universal_submission_routing(
            session,
            tenant_id=tenant_id,
            form_id=form_id,
            intake_source_profile_id=profile_id,
        )
    assert decision.status == "routed"
    assert decision.source == "campaign_target"
    assert decision.route_intent == "candidate_application"
    assert decision.campaign_run_id == flight_id


@pytest.mark.asyncio
async def test_same_flight_via_form_and_profile_is_not_conflict(
    client: AsyncClient, auth_headers: dict, monkeypatch
):
    monkeypatch.setattr("backend.app.acquisition.campaign_service.enforce_module_gate", _allow_gate)
    data = await _init_data()
    tenant_id = data["tenant_id"]
    oc = await _default_own_company_id(tenant_id)
    vac = await _seed_vacancy(tenant_id=tenant_id, own_company_id=oc, company_id=data["company_id"])
    form_id = await _seed_form(tenant_id=tenant_id)
    profile_id = await _seed_profile(tenant_id=tenant_id, own_company_id=oc)

    campaign = await _create_campaign(client, auth_headers, own_company_id=oc, vac_id=vac)
    flight_id = campaign["flights"][0]["id"]
    await _activate_campaign_and_flight(campaign["id"], flight_id)
    hdrs = _company_headers(auth_headers, oc)
    await _attach_form(client, hdrs, campaign["id"], form_id)
    await _attach_profile(client, hdrs, campaign["id"], profile_id)

    async with async_session_maker() as session:
        decision = await resolve_universal_submission_routing(
            session,
            tenant_id=tenant_id,
            form_id=form_id,
            intake_source_profile_id=profile_id,
        )
    assert decision.status == "routed"
    assert decision.campaign_run_id == flight_id
    assert decision.unresolved_reason is None


@pytest.mark.asyncio
async def test_form_profile_flight_conflict(client: AsyncClient, auth_headers: dict, monkeypatch):
    monkeypatch.setattr("backend.app.acquisition.campaign_service.enforce_module_gate", _allow_gate)
    data = await _init_data()
    tenant_id = data["tenant_id"]
    oc = await _default_own_company_id(tenant_id)
    vac = await _seed_vacancy(tenant_id=tenant_id, own_company_id=oc, company_id=data["company_id"])
    form_id = await _seed_form(tenant_id=tenant_id)
    profile_id = await _seed_profile(tenant_id=tenant_id, own_company_id=oc)

    c1 = await _create_campaign(client, auth_headers, own_company_id=oc, vac_id=vac, name="C1")
    c2 = await _create_campaign(client, auth_headers, own_company_id=oc, vac_id=vac, name="C2")
    await _activate_campaign_and_flight(c1["id"], c1["flights"][0]["id"])
    await _activate_campaign_and_flight(c2["id"], c2["flights"][0]["id"])
    hdrs = _company_headers(auth_headers, oc)
    await _attach_form(client, hdrs, c1["id"], form_id)
    await _attach_profile(client, hdrs, c2["id"], profile_id)

    async with async_session_maker() as session:
        decision = await resolve_universal_submission_routing(
            session,
            tenant_id=tenant_id,
            form_id=form_id,
            intake_source_profile_id=profile_id,
        )
    assert decision.status == "unresolved"
    assert decision.unresolved_reason == UnresolvedReason.form_profile_flight_conflict.value


@pytest.mark.asyncio
async def test_profile_on_two_eligible_flights(client: AsyncClient, auth_headers: dict, monkeypatch):
    monkeypatch.setattr("backend.app.acquisition.campaign_service.enforce_module_gate", _allow_gate)
    data = await _init_data()
    tenant_id = data["tenant_id"]
    oc = await _default_own_company_id(tenant_id)
    vac = await _seed_vacancy(tenant_id=tenant_id, own_company_id=oc, company_id=data["company_id"])
    profile_id = await _seed_profile(tenant_id=tenant_id, own_company_id=oc)

    c1 = await _create_campaign(client, auth_headers, own_company_id=oc, vac_id=vac, name="A")
    c2 = await _create_campaign(client, auth_headers, own_company_id=oc, vac_id=vac, name="B")
    await _activate_campaign_and_flight(c1["id"], c1["flights"][0]["id"])
    await _activate_campaign_and_flight(c2["id"], c2["flights"][0]["id"])
    hdrs = _company_headers(auth_headers, oc)
    await _attach_profile(client, hdrs, c1["id"], profile_id)
    await _attach_profile(client, hdrs, c2["id"], profile_id)

    async with async_session_maker() as session:
        decision = await resolve_universal_submission_routing(
            session,
            tenant_id=tenant_id,
            intake_source_profile_id=profile_id,
        )
    assert decision.status == "unresolved"
    assert decision.unresolved_reason == UnresolvedReason.multiple_active_flights.value


@pytest.mark.asyncio
async def test_no_links_uses_profile_default(client: AsyncClient, auth_headers: dict, monkeypatch):
    monkeypatch.setattr("backend.app.acquisition.campaign_service.enforce_module_gate", _allow_gate)
    data = await _init_data()
    tenant_id = data["tenant_id"]
    oc = await _default_own_company_id(tenant_id)
    profile_id = await _seed_profile(
        tenant_id=tenant_id, own_company_id=oc, route_intent="sales_inquiry"
    )

    async with async_session_maker() as session:
        decision = await resolve_universal_submission_routing(
            session,
            tenant_id=tenant_id,
            intake_source_profile_id=profile_id,
        )
    assert decision.status == "routed"
    assert decision.source == "profile_default"
    assert decision.route_intent == "sales_inquiry"
    assert decision.campaign_run_id is None


@pytest.mark.asyncio
async def test_inactive_campaign_falls_through_to_profile_default(
    client: AsyncClient, auth_headers: dict, monkeypatch
):
    monkeypatch.setattr("backend.app.acquisition.campaign_service.enforce_module_gate", _allow_gate)
    data = await _init_data()
    tenant_id = data["tenant_id"]
    oc = await _default_own_company_id(tenant_id)
    vac = await _seed_vacancy(tenant_id=tenant_id, own_company_id=oc, company_id=data["company_id"])
    form_id = await _seed_form(tenant_id=tenant_id)
    profile_id = await _seed_profile(
        tenant_id=tenant_id, own_company_id=oc, route_intent="sales_inquiry"
    )

    campaign = await _create_campaign(client, auth_headers, own_company_id=oc, vac_id=vac)
    # Leave campaign draft / flight planned — not routing-eligible
    hdrs = _company_headers(auth_headers, oc)
    await _attach_form(client, hdrs, campaign["id"], form_id)
    await _attach_profile(client, hdrs, campaign["id"], profile_id)

    async with async_session_maker() as session:
        decision = await resolve_universal_submission_routing(
            session,
            tenant_id=tenant_id,
            form_id=form_id,
            intake_source_profile_id=profile_id,
        )
    assert decision.status == "routed"
    assert decision.source == "profile_default"
    assert decision.route_intent == "sales_inquiry"


@pytest.mark.asyncio
async def test_unknown_profile_intent_unresolved(client: AsyncClient, auth_headers: dict, monkeypatch):
    monkeypatch.setattr("backend.app.acquisition.campaign_service.enforce_module_gate", _allow_gate)
    data = await _init_data()
    tenant_id = data["tenant_id"]
    oc = await _default_own_company_id(tenant_id)
    profile_id = await _seed_profile(tenant_id=tenant_id, own_company_id=oc, route_intent="unknown")

    async with async_session_maker() as session:
        decision = await resolve_universal_submission_routing(
            session,
            tenant_id=tenant_id,
            intake_source_profile_id=profile_id,
        )
    assert decision.status == "unresolved"
    assert decision.unresolved_reason == UnresolvedReason.unknown_route_intent.value


@pytest.mark.asyncio
async def test_submit_persists_submission_before_decision_layer_failure(
    client: AsyncClient, auth_headers: dict, monkeypatch
):
    monkeypatch.setattr("backend.app.acquisition.campaign_service.enforce_module_gate", _allow_gate)
    data = await _init_data()
    tenant_id = data["tenant_id"]
    oc = await _default_own_company_id(tenant_id)
    form_id = await _seed_form(tenant_id=tenant_id)
    profile_id = await _seed_profile(tenant_id=tenant_id, own_company_id=oc, form_id=form_id)

    lead_id = str(uuid4())
    async with async_session_maker() as session:
        session.add(
            Lead(
                id=lead_id,
                tenant_id=tenant_id,
                own_company_id=oc,
                source="public_intake",
                status="new",
                stage="intake_draft",
                lead_type="client",
                payload={},
                normalized={
                    "public_intake_draft_v1": {"intake_token": f"tok-{lead_id[:8]}"},
                },
            )
        )
        await session.commit()

    monkeypatch.setattr(
        "backend.app.modules.sales.intake.inquiry_draft_handler.submit_public_intake_lead_draft",
        AsyncMock(side_effect=RuntimeError("decision_layer_boom")),
    )

    from backend.app.intake_platform import intake_submit_service as svc

    async with async_session_maker() as session:
        lead = await session.get(Lead, lead_id)
        assert lead is not None
        with pytest.raises(RuntimeError, match="decision_layer_boom"):
            await svc.submit_client_public_intake_with_policy(
                session,
                tenant_id=tenant_id,
                draft_lead=lead,
                intake_state={
                    "lead_form": {"id": form_id},
                    "application_kind": "candidate",
                    "contacts": {"email": "a@example.com"},
                },
            )
        await session.commit()

    async with async_session_maker() as session:
        lead = await session.get(Lead, lead_id)
        assert lead is not None
        submissions = list_submissions(lead)
        assert len(submissions) == 1
        stamp = (lead.normalized or {}).get(ACQUISITION_ROUTING_V1_KEY)
        assert isinstance(stamp, dict)
        assert stamp.get("status") == "routed"
        assert stamp.get("source") == "profile_default"
        assert submissions[0].get("source", {}).get("acquisition_routing_v1", {}).get("status") == "routed"


@pytest.mark.asyncio
async def test_idempotent_submission_replay_does_not_duplicate(
    client: AsyncClient, auth_headers: dict, monkeypatch
):
    monkeypatch.setattr("backend.app.acquisition.campaign_service.enforce_module_gate", _allow_gate)
    data = await _init_data()
    tenant_id = data["tenant_id"]
    oc = await _default_own_company_id(tenant_id)
    lead_id = str(uuid4())
    async with async_session_maker() as session:
        session.add(
            Lead(
                id=lead_id,
                tenant_id=tenant_id,
                own_company_id=oc,
                source="public_intake",
                status="new",
                lead_type="client",
                payload={},
                normalized={},
            )
        )
        await session.commit()

    policy = EffectivePolicy(
        purpose="inquiry",
        target_entity_profile_code="",
        submission_policy=SubmissionPolicy.from_dict({"mode": "create"}),
    )
    key = f"idem-{lead_id}"
    async with async_session_maker() as session:
        first = await append_submission(
            session,
            tenant_id=tenant_id,
            lead_id=lead_id,
            effective_policy=policy,
            normalized_values={"x": 1},
            entry_context={"acquisition_routing_v1": {"status": "routed"}},
            idempotency_key=key,
        )
        second = await append_submission(
            session,
            tenant_id=tenant_id,
            lead_id=lead_id,
            effective_policy=policy,
            normalized_values={"x": 2},
            entry_context={"acquisition_routing_v1": {"status": "routed"}},
            idempotency_key=key,
        )
        await session.commit()
        assert first["submission_id"] == second["submission_id"]
        lead = await session.get(Lead, lead_id)
        assert len(list_submissions(lead)) == 1


@pytest.mark.asyncio
async def test_unresolved_skip_decision_layer(client: AsyncClient, auth_headers: dict, monkeypatch):
    monkeypatch.setattr("backend.app.acquisition.campaign_service.enforce_module_gate", _allow_gate)
    data = await _init_data()
    tenant_id = data["tenant_id"]
    oc = await _default_own_company_id(tenant_id)
    vac = await _seed_vacancy(tenant_id=tenant_id, own_company_id=oc, company_id=data["company_id"])
    form_id = await _seed_form(tenant_id=tenant_id)
    profile_id = await _seed_profile(tenant_id=tenant_id, own_company_id=oc, form_id=form_id)

    c1 = await _create_campaign(client, auth_headers, own_company_id=oc, vac_id=vac, name="U1")
    c2 = await _create_campaign(client, auth_headers, own_company_id=oc, vac_id=vac, name="U2")
    await _activate_campaign_and_flight(c1["id"], c1["flights"][0]["id"])
    await _activate_campaign_and_flight(c2["id"], c2["flights"][0]["id"])
    hdrs = _company_headers(auth_headers, oc)
    await _attach_form(client, hdrs, c1["id"], form_id)
    await _attach_profile(client, hdrs, c2["id"], profile_id)

    lead_id = str(uuid4())
    async with async_session_maker() as session:
        session.add(
            Lead(
                id=lead_id,
                tenant_id=tenant_id,
                own_company_id=oc,
                source="public_intake",
                status="new",
                stage="intake_draft",
                lead_type="client",
                payload={},
                normalized={"public_intake_draft_v1": {"intake_token": f"tok-{lead_id[:8]}"}},
            )
        )
        await session.commit()

    dl_mock = AsyncMock(return_value=(object(), "should-not-run"))
    monkeypatch.setattr(
        "backend.app.modules.sales.intake.inquiry_draft_handler.submit_public_intake_lead_draft",
        dl_mock,
    )

    from backend.app.intake_platform import intake_submit_service as svc

    async with async_session_maker() as session:
        lead = await session.get(Lead, lead_id)
        decision, created_id, _ = await svc.submit_client_public_intake_with_policy(
            session,
            tenant_id=tenant_id,
            draft_lead=lead,
            intake_state={
                "lead_form": {"id": form_id},
                "application_kind": "candidate",
                "contacts": {"email": "b@example.com"},
            },
        )
        await session.commit()

    assert created_id is None
    assert decision.disposition == "review_queue"
    dl_mock.assert_not_called()

    async with async_session_maker() as session:
        lead = await session.get(Lead, lead_id)
        assert lead.status == "needs_routing"
        assert lead.error == UnresolvedReason.form_profile_flight_conflict.value
        assert len(list_submissions(lead)) == 1
        stamp = (lead.normalized or {}).get(ACQUISITION_ROUTING_V1_KEY)
        assert stamp["status"] == "unresolved"
        assert stamp["unresolved_reason"] == UnresolvedReason.form_profile_flight_conflict.value
