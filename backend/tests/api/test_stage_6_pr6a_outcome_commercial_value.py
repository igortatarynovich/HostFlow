"""Stage 6 PR-6a — Outcome commercial value contract + HTTP."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from backend.app.acquisition.contracts import outcome_commercial_value as ocv_mod
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
                title="OCV Drivers",
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
            "name": "OCV campaign",
            "goal_type": "sales",
            "primary_kpi": "revenue",
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
    # sales+vacancy may 422 — use hiring if needed
    if resp.status_code != 201:
        resp = await client.post(
            "/api/v1/platform/campaigns",
            headers=_company_headers(headers, own_company_id),
            json={
                "name": "OCV campaign",
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


async def _complete_outcome(*, tenant_id: str, campaign_id: str, flight_id: str) -> str:
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
        attr = await record_result_attribution_from_routing(
            session,
            tenant_id=tenant_id,
            lead=lead,
            submission_id=str(uuid4()),
            result_type=RESULT_TYPE_INTAKE_LEAD,
            result_id=lead_id,
        )
        outcome = await create_outcome(
            session,
            tenant_id=tenant_id,
            campaign_id=campaign_id,
            flight_id=flight_id,
            progress_target=1,
        )
        await apply_attribution_to_outcome(
            session,
            tenant_id=tenant_id,
            outcome_id=outcome.id,
            attribution_id=str(attr.id),
        )
        await session.commit()
        return str(outcome.id)


def test_commercial_value_writer_is_contract_only() -> None:
    root = Path(__file__).resolve().parents[2] / "app"
    offenders: list[str] = []
    for path in root.rglob("*.py"):
        if path.resolve() == Path(ocv_mod.__file__).resolve():
            continue
        text = path.read_text(encoding="utf-8")
        if "commercial_value_amount" in text and "commercial_value_amount =" in text:
            # model definition uses mapped_column assignment — allow models/campaign.py
            if path.name == "campaign.py" and "models" in path.parts:
                continue
            offenders.append(str(path.relative_to(root.parent.parent)))
    assert offenders == [], f"non-contract writers of commercial_value_*: {offenders}"


@pytest.mark.asyncio
async def test_put_get_outcome_commercial_value(
    client: AsyncClient, auth_headers: dict, monkeypatch
):
    monkeypatch.setattr("backend.app.acquisition.campaign_service.enforce_module_gate", _allow_gate)
    data = await _init_data()
    tenant_id = data["tenant_id"]
    oc = await _default_own_company_id(tenant_id)
    vac = await _seed_vacancy(tenant_id=tenant_id, own_company_id=oc, company_id=data["company_id"])
    campaign = await _create_campaign(client, auth_headers, own_company_id=oc, vac_id=vac)
    flight_id = campaign["flights"][0]["id"]

    async with async_session_maker() as session:
        camp = await session.get(Campaign, campaign["id"])
        flight = await session.get(CampaignRun, flight_id)
        assert camp and flight
        camp.status = "active"
        flight.status = "active"
        await session.commit()

    outcome_id = await _complete_outcome(
        tenant_id=tenant_id, campaign_id=campaign["id"], flight_id=flight_id
    )
    headers = _company_headers(auth_headers, oc)
    base = f"/api/v1/platform/campaigns/{campaign['id']}/outcomes/{outcome_id}/commercial-value"

    missing = await client.get(base, headers=headers)
    assert missing.status_code == 404

    bad_amt = await client.put(base, headers=headers, json={"amount": "0", "currency": "EUR"})
    assert bad_amt.status_code == 422

    bad_cur = await client.put(base, headers=headers, json={"amount": "100", "currency": "EU"})
    assert bad_cur.status_code == 422

    ok = await client.put(
        base, headers=headers, json={"amount": "250.50", "currency": "eur"}
    )
    assert ok.status_code == 200, ok.text
    body = ok.json()
    assert body["outcome_id"] == outcome_id
    assert body["amount"] == "250.5000"
    assert body["currency"] == "EUR"
    assert body["source"] == "declared_v1"
    assert body["as_of"]

    got = await client.get(base, headers=headers)
    assert got.status_code == 200, got.text
    assert got.json()["amount"] == "250.5000"


@pytest.mark.asyncio
async def test_commercial_value_rejects_non_completed(
    client: AsyncClient, auth_headers: dict, monkeypatch
):
    monkeypatch.setattr("backend.app.acquisition.campaign_service.enforce_module_gate", _allow_gate)
    data = await _init_data()
    tenant_id = data["tenant_id"]
    oc = await _default_own_company_id(tenant_id)
    vac = await _seed_vacancy(tenant_id=tenant_id, own_company_id=oc, company_id=data["company_id"])
    campaign = await _create_campaign(client, auth_headers, own_company_id=oc, vac_id=vac)
    flight_id = campaign["flights"][0]["id"]

    async with async_session_maker() as session:
        camp = await session.get(Campaign, campaign["id"])
        flight = await session.get(CampaignRun, flight_id)
        assert camp and flight
        camp.status = "active"
        flight.status = "active"
        outcome = await create_outcome(
            session,
            tenant_id=tenant_id,
            campaign_id=campaign["id"],
            flight_id=flight_id,
            progress_target=1,
        )
        await session.commit()
        outcome_id = str(outcome.id)

    resp = await client.put(
        f"/api/v1/platform/campaigns/{campaign['id']}/outcomes/{outcome_id}/commercial-value",
        headers=_company_headers(auth_headers, oc),
        json={"amount": "10", "currency": "EUR"},
    )
    assert resp.status_code == 422
    assert "completed" in resp.json()["detail"].lower()
