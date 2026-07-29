"""Stage 5 PR-2 — explainability + operator acknowledge/dismiss (no Flight mutation)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select

from backend.app.acquisition import append_activity_event
from backend.app.acquisition.ops.optimization_signals import (
    OptimizationInputs,
    WindowCounters,
    evaluate_flight_optimization,
)
from backend.app.db.session import async_session_maker
from backend.app.models.acquisition_activity_event import (
    ACTOR_TYPE_SYSTEM,
    AcquisitionActivityEvent,
)
from backend.app.models.campaign import CampaignRun
from backend.app.models.own_company import OwnCompany
from backend.tests.conftest import _init_data, _set_tenant


def test_evaluate_exposes_fingerprint_explanation_and_fail_rate() -> None:
    end = datetime(2026, 7, 23, 12, 0, tzinfo=timezone.utc)
    snap = evaluate_flight_optimization(
        OptimizationInputs(
            campaign_id="camp",
            flight_id="flight",
            campaign_status="active",
            flight_status="active",
            window_hours=24,
            window_start=end - timedelta(hours=24),
            window_end=end,
            counters=WindowCounters(0, 3, 3, 0),
            kpi_leads=0,
            spend="0.0000",
        )
    )
    assert snap.assessment == "suggest_pause"
    assert snap.signal_fingerprint
    assert "0.50" in snap.explanation or "fail" in snap.explanation.lower()
    assert snap.observed is not None
    assert snap.observed["routing_fail_rate"] == pytest.approx(0.5)
    assert snap.operator is None


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


async def _create_campaign(client: AsyncClient, headers: dict) -> dict:
    resp = await client.post(
        "/api/v1/platform/campaigns",
        headers=headers,
        json={
            "name": f"S5 PR2 {uuid4().hex[:6]}",
            "goal_type": "hiring",
            "primary_kpi": "hires",
            "targets": [],
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _launch(client: AsyncClient, headers: dict, campaign_id: str, flight_id: str) -> None:
    resp = await client.post(
        f"/api/v1/platform/campaigns/{campaign_id}/flights/{flight_id}/launch",
        headers=headers,
        json={},
    )
    assert resp.status_code == 200, resp.text


async def _seed_window_events(
    *,
    tenant_id: str,
    campaign_id: str,
    flight_id: str,
    event_types: list[str],
) -> None:
    t0 = datetime.now(timezone.utc) - timedelta(minutes=30)
    async with async_session_maker() as session:
        await _set_tenant(session, tenant_id)
        for i, et in enumerate(event_types):
            payload: dict = {}
            if et == "RoutingCompleted":
                payload = {"route_intent": "sales_inquiry"}
            elif et == "RoutingFailed":
                payload = {"reason_code": "no_target"}
            elif et == "DeliveryErrorOccurred":
                payload = {"error_code": "adapter_failed"}
            await append_activity_event(
                session,
                tenant_id=tenant_id,
                campaign_id=campaign_id,
                flight_id=flight_id,
                submission_id=str(uuid4()),
                event_type=et,
                event_version="1",
                payload=payload,
                actor_type=ACTOR_TYPE_SYSTEM,
                occurred_at=t0 + timedelta(seconds=i),
                source_event_id=f"s5pr2-{i}-{uuid4().hex[:8]}",
            )
        await session.commit()


async def _activity_count(tenant_id: str, flight_id: str) -> int:
    async with async_session_maker() as session:
        await _set_tenant(session, tenant_id)
        n = await session.scalar(
            select(func.count())
            .select_from(AcquisitionActivityEvent)
            .where(
                AcquisitionActivityEvent.tenant_id == tenant_id,
                AcquisitionActivityEvent.flight_id == flight_id,
            )
        )
        return int(n or 0)


async def _flight_status(tenant_id: str, flight_id: str) -> str:
    async with async_session_maker() as session:
        await _set_tenant(session, tenant_id)
        row = await session.get(CampaignRun, flight_id)
        assert row is not None
        return str(row.status)


@pytest.mark.asyncio
async def test_http_explainability_and_dismiss_audit(
    client: AsyncClient, auth_headers: dict, tenant_id: str
) -> None:
    await _init_data()
    own_company_id = await _default_own_company_id(tenant_id)
    headers = {**auth_headers, "X-Own-Company-Id": own_company_id}
    camp = await _create_campaign(client, headers)
    campaign_id = camp["id"]
    flight_id = camp["flights"][0]["id"]
    await _launch(client, headers, campaign_id, flight_id)
    await _seed_window_events(
        tenant_id=tenant_id,
        campaign_id=campaign_id,
        flight_id=flight_id,
        event_types=(["RoutingCompleted"] * 3) + (["RoutingFailed"] * 3),
    )

    before = await _activity_count(tenant_id, flight_id)
    get1 = await client.get(
        f"/api/v1/platform/campaigns/{campaign_id}/flights/{flight_id}/optimization",
        headers=headers,
    )
    assert get1.status_code == 200, get1.text
    body = get1.json()
    assert body["assessment"] == "suggest_pause"
    assert body["recommended_action"] == "suggest_pause"
    assert body["signal_fingerprint"]
    assert body["explanation"]
    assert body["observed"]["routing_fail_rate"] == pytest.approx(0.5)
    assert body["operator"] is None
    assert await _activity_count(tenant_id, flight_id) == before  # GET has no side effects

    dismiss = await client.post(
        f"/api/v1/platform/campaigns/{campaign_id}/flights/{flight_id}/optimization/operator-action",
        headers=headers,
        json={
            "action": "dismiss",
            "signal_fingerprint": body["signal_fingerprint"],
            "note": "noise for now",
        },
    )
    assert dismiss.status_code == 200, dismiss.text
    out = dismiss.json()
    assert out["assessment"] == "suggest_pause"
    assert out["recommended_action"] == "suggest_pause"
    assert out["operator"]["action"] == "dismiss"
    assert out["operator"]["signal_fingerprint"] == body["signal_fingerprint"]
    assert await _flight_status(tenant_id, flight_id) == "active"
    assert await _activity_count(tenant_id, flight_id) == before + 1

    get2 = await client.get(
        f"/api/v1/platform/campaigns/{campaign_id}/flights/{flight_id}/optimization",
        headers=headers,
    )
    assert get2.status_code == 200, get2.text
    assert get2.json()["operator"]["action"] == "dismiss"
    assert get2.json()["assessment"] == "suggest_pause"


@pytest.mark.asyncio
async def test_http_acknowledge_fingerprint_mismatch_409(
    client: AsyncClient, auth_headers: dict, tenant_id: str
) -> None:
    await _init_data()
    own_company_id = await _default_own_company_id(tenant_id)
    headers = {**auth_headers, "X-Own-Company-Id": own_company_id}
    camp = await _create_campaign(client, headers)
    campaign_id = camp["id"]
    flight_id = camp["flights"][0]["id"]
    await _launch(client, headers, campaign_id, flight_id)
    await _seed_window_events(
        tenant_id=tenant_id,
        campaign_id=campaign_id,
        flight_id=flight_id,
        event_types=(["RoutingCompleted"] * 3) + (["RoutingFailed"] * 3),
    )
    bad = await client.post(
        f"/api/v1/platform/campaigns/{campaign_id}/flights/{flight_id}/optimization/operator-action",
        headers=headers,
        json={"action": "acknowledge", "signal_fingerprint": "deadbeefdeadbeef"},
    )
    assert bad.status_code == 409, bad.text
