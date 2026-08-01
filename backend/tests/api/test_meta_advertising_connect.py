"""Connect Meta Advertising — preview + connect-all (forms secondary + ads)."""

from __future__ import annotations

from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from backend.app.db.session import async_session_maker
from backend.app.models.campaign import (
    Campaign,
    CampaignRun,
    CampaignRunIntakeSource,
    CampaignTarget,
    FlightAdBinding,
)
from backend.app.models.company import Company
from backend.app.models.lead import Lead
from backend.app.models.own_company import OwnCompany
from backend.app.models.vacancy import Vacancy
from backend.tests.conftest import _init_data


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
) -> tuple[str, str]:
    async with async_session_maker() as session:
        campaign = Campaign(
            id=str(uuid4()),
            tenant_id=tenant_id,
            own_company_id=own_company_id,
            name=f"MetaAdv {uuid4().hex[:6]}",
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
            name="Flight MetaAdv",
            status="active",
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


def _headers(manager_headers: dict, tenant_id: str, own_company_id: str) -> dict:
    headers = dict(manager_headers)
    headers["X-Tenant-Id"] = tenant_id
    headers["X-Own-Company-Id"] = own_company_id
    headers["Content-Type"] = "application/json"
    return headers


@pytest.mark.anyio
async def test_meta_advertising_preview_from_leads_fallback(
    client: AsyncClient, manager_headers: dict, monkeypatch: pytest.MonkeyPatch
):
    data = await _init_data()
    tenant_id = data["tenant_id"]
    oc = await _own_company_id(tenant_id)
    company_id = await _company_id(tenant_id)
    meta_campaign_id = f"1202{uuid4().int % 10**14:014d}"
    form_a = f"1015{uuid4().int % 10**12:012d}"
    form_b = f"1568{uuid4().int % 10**12:012d}"
    ad_a = f"1202{uuid4().int % 10**14:014d}"
    ad_b = f"1202{uuid4().int % 10**14:014d}"

    async with async_session_maker() as session:
        vac = Vacancy(
            id=str(uuid4()),
            tenant_id=tenant_id,
            own_company_id=oc,
            company_id=company_id,
            title="Magazynier preview",
            status="open",
            is_active=True,
            is_archived=False,
        )
        session.add(vac)
        await session.flush()
        camp_id, _flight_id = await _seed_campaign_flight(
            tenant_id=tenant_id, own_company_id=oc, vacancy_id=str(vac.id)
        )
        for aid, fid in ((ad_a, form_a), (ad_b, form_b)):
            session.add(
                Lead(
                    id=str(uuid4()),
                    tenant_id=tenant_id,
                    own_company_id=oc,
                    source="meta",
                    status="new",
                    ad_id=int(aid) if aid.isdigit() else None,
                    payload={
                        "entry": [
                            {
                                "changes": [
                                    {
                                        "value": {
                                            "form_id": fid,
                                            "campaign_id": meta_campaign_id,
                                            "ad_id": aid,
                                        }
                                    }
                                ]
                            }
                        ]
                    },
                    normalized={"form_id": fid, "ad_id": aid},
                    external_id=f"meta-lead-{uuid4().hex[:10]}",
                )
            )
        await session.commit()

    monkeypatch.setattr(
        "backend.app.acquisition.meta_advertising._marketing_access_token",
        lambda *a, **k: _async_none(),
    )

    headers = _headers(manager_headers, tenant_id, oc)
    resp = await client.get(
        f"/api/v1/platform/campaigns/{camp_id}/meta-advertising/preview",
        headers=headers,
        params={"meta_campaign_id": meta_campaign_id},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["source"] == "leads_fallback"
    form_ids = {f["form_id"] for f in body["forms"]}
    ad_ids = {a["ad_id"] for a in body["ads"]}
    assert form_a in form_ids and form_b in form_ids
    assert ad_a in ad_ids and ad_b in ad_ids


async def _async_none():
    return None


@pytest.mark.anyio
async def test_meta_advertising_preview_from_graph(
    client: AsyncClient, manager_headers: dict, monkeypatch: pytest.MonkeyPatch
):
    data = await _init_data()
    tenant_id = data["tenant_id"]
    oc = await _own_company_id(tenant_id)
    company_id = await _company_id(tenant_id)
    meta_campaign_id = f"1202{uuid4().int % 10**14:014d}"
    meta_adset_id = f"1202{uuid4().int % 10**14:014d}"
    form_ids = [f"f{i}-{uuid4().hex[:8]}" for i in range(3)]
    ad_ids = [f"a{i}-{uuid4().hex[:8]}" for i in range(3)]

    async with async_session_maker() as session:
        vac = Vacancy(
            id=str(uuid4()),
            tenant_id=tenant_id,
            own_company_id=oc,
            company_id=company_id,
            title="Graph preview",
            status="open",
            is_active=True,
            is_archived=False,
        )
        session.add(vac)
        await session.flush()
        camp_id, _ = await _seed_campaign_flight(
            tenant_id=tenant_id, own_company_id=oc, vacancy_id=str(vac.id)
        )

    async def _token(*_a, **_k):
        return "test-token"

    async def _node(campaign_id: str, _token: str):
        return {"id": campaign_id, "name": "Magazynier Ads"}

    async def _ads(campaign_id: str, _token: str, *, limit: int = 100):
        assert campaign_id == meta_campaign_id
        return [
            {
                "ad_id": ad_ids[i],
                "ad_name": f"Ad {i}",
                "adset_id": meta_adset_id if i < 2 else f"other-{i}",
                "lead_gen_form_id": form_ids[i],
                "form_name": f"Form {i}",
            }
            for i in range(3)
        ]

    monkeypatch.setattr(
        "backend.app.acquisition.meta_advertising._marketing_access_token",
        _token,
    )
    monkeypatch.setattr(
        "backend.app.modules.leads.meta_marketing_graph.fetch_campaign_node",
        _node,
    )
    monkeypatch.setattr(
        "backend.app.modules.leads.meta_marketing_graph.fetch_campaign_lead_ads",
        _ads,
    )

    headers = _headers(manager_headers, tenant_id, oc)
    resp = await client.get(
        f"/api/v1/platform/campaigns/{camp_id}/meta-advertising/preview",
        headers=headers,
        params={"meta_campaign_id": meta_campaign_id, "meta_adset_id": meta_adset_id},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["source"] == "graph"
    assert body["meta_campaign_name"] == "Magazynier Ads"
    assert len(body["ads"]) == 2
    assert {a["ad_id"] for a in body["ads"]} == {ad_ids[0], ad_ids[1]}
    assert {f["form_id"] for f in body["forms"]} == {form_ids[0], form_ids[1]}


@pytest.mark.anyio
async def test_meta_advertising_connect_all_idempotent_secondary(
    client: AsyncClient, manager_headers: dict
):
    data = await _init_data()
    tenant_id = data["tenant_id"]
    oc = await _own_company_id(tenant_id)
    company_id = await _company_id(tenant_id)
    meta_campaign_id = f"1202{uuid4().int % 10**14:014d}"
    form_ids = [f"form-{uuid4().hex[:10]}" for _ in range(3)]
    ad_ids = [f"1202{uuid4().int % 10**14:014d}" for _ in range(3)]

    async with async_session_maker() as session:
        vac = Vacancy(
            id=str(uuid4()),
            tenant_id=tenant_id,
            own_company_id=oc,
            company_id=company_id,
            title="Connect-all vac",
            status="open",
            is_active=True,
            is_archived=False,
        )
        session.add(vac)
        await session.flush()
        camp_id, flight_id = await _seed_campaign_flight(
            tenant_id=tenant_id, own_company_id=oc, vacancy_id=str(vac.id)
        )

    headers = _headers(manager_headers, tenant_id, oc)
    payload = {
        "meta_campaign_id": meta_campaign_id,
        "form_ids": form_ids,
        "ad_ids": ad_ids,
    }
    resp = await client.post(
        f"/api/v1/platform/campaigns/{camp_id}/meta-advertising/connect",
        headers=headers,
        json=payload,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert sorted(body["forms_attached"]) == sorted(form_ids)
    assert body["forms_skipped"] == []
    assert sorted(body["ads_attached"]) == sorted(ad_ids)
    assert body["ads_skipped"] == []

    campaign = body["campaign"]
    flight = next(f for f in campaign["flights"] if f["id"] == flight_id)
    intake = [s for s in flight["intake_sources"] if s.get("is_active")]
    assert len(intake) == 3
    roles = {s["role"] for s in intake}
    assert "primary" in roles
    assert "secondary" in roles
    assert sum(1 for s in intake if s["role"] == "primary") == 1
    assert sum(1 for s in intake if s["role"] == "secondary") == 2
    bindings = [b for b in (flight.get("ad_bindings") or []) if b.get("is_active")]
    assert len(bindings) == 3

    # Idempotent replay — skip all
    resp2 = await client.post(
        f"/api/v1/platform/campaigns/{camp_id}/meta-advertising/connect",
        headers=headers,
        json=payload,
    )
    assert resp2.status_code == 200, resp2.text
    body2 = resp2.json()
    assert body2["forms_attached"] == []
    assert sorted(body2["forms_skipped"]) == sorted(form_ids)
    assert body2["ads_attached"] == []
    assert sorted(body2["ads_skipped"]) == sorted(ad_ids)

    async with async_session_maker() as session:
        links = (
            await session.execute(
                select(CampaignRunIntakeSource).where(
                    CampaignRunIntakeSource.campaign_run_id == flight_id,
                    CampaignRunIntakeSource.is_active.is_(True),
                )
            )
        ).scalars().all()
        assert len(links) == 3
        ads = (
            await session.execute(
                select(FlightAdBinding).where(
                    FlightAdBinding.tenant_id == tenant_id,
                    FlightAdBinding.campaign_run_id == flight_id,
                    FlightAdBinding.is_active.is_(True),
                )
            )
        ).scalars().all()
        assert len(ads) == 3
