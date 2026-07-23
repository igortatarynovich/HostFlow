"""Stage 4 PR-5 — RBAC + company-scope hardening for ops routes."""

from __future__ import annotations

from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from backend.app.db.session import async_session_maker
from backend.app.models.own_company import OwnCompany
from backend.tests.conftest import _init_data


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


async def _seed_own_company(tenant_id: str, *, name: str) -> str:
    oc_id = str(uuid4())
    async with async_session_maker() as session:
        session.add(
            OwnCompany(id=oc_id, tenant_id=tenant_id, name=name, is_archived=False)
        )
        await session.commit()
    return oc_id


async def _create_campaign(
    client: AsyncClient, headers: dict, *, own_company_id: str
) -> dict:
    resp = await client.post(
        "/api/v1/platform/campaigns",
        headers={**headers, "X-Own-Company-Id": own_company_id},
        json={
            "name": f"PR5 {uuid4().hex[:6]}",
            "goal_type": "hiring",
            "primary_kpi": "hires",
            "own_company_id": own_company_id,
            "targets": [],
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


@pytest.mark.asyncio
async def test_viewer_cannot_launch_flight(
    client: AsyncClient,
    auth_headers: dict,
    viewer_headers: dict,
    tenant_id: str,
) -> None:
    await _init_data()
    own_company_id = await _default_own_company_id(tenant_id)
    camp = await _create_campaign(client, auth_headers, own_company_id=own_company_id)
    flight_id = camp["flights"][0]["id"]

    forbidden = await client.post(
        f"/api/v1/platform/campaigns/{camp['id']}/flights/{flight_id}/launch",
        headers={**viewer_headers, "X-Own-Company-Id": own_company_id},
        json={},
    )
    assert forbidden.status_code == 403, forbidden.text

    ok = await client.post(
        f"/api/v1/platform/campaigns/{camp['id']}/flights/{flight_id}/launch",
        headers={**auth_headers, "X-Own-Company-Id": own_company_id},
        json={},
    )
    assert ok.status_code == 200, ok.text


@pytest.mark.asyncio
async def test_cross_company_ops_reads_are_404(
    client: AsyncClient, auth_headers: dict, tenant_id: str
) -> None:
    await _init_data()
    own_a = await _default_own_company_id(tenant_id)
    own_b = await _seed_own_company(tenant_id, name=f"Foreign {uuid4().hex[:6]}")
    camp = await _create_campaign(client, auth_headers, own_company_id=own_a)
    campaign_id = camp["id"]
    flight_id = camp["flights"][0]["id"]

    for path in (
        f"/api/v1/platform/campaigns/{campaign_id}/kpi",
        f"/api/v1/platform/campaigns/{campaign_id}/flights/{flight_id}/kpi",
        f"/api/v1/platform/campaigns/{campaign_id}/flights/{flight_id}/runtime",
        f"/api/v1/platform/campaigns/{campaign_id}/flights/{flight_id}/monitor/live-intake",
    ):
        resp = await client.get(
            path,
            headers={**auth_headers, "X-Own-Company-Id": own_b},
        )
        assert resp.status_code == 404, f"{path} -> {resp.status_code} {resp.text}"
