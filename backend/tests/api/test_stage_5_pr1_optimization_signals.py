"""Stage 5 PR-1 — read-only optimization signals / suggest_pause."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select

from backend.app.acquisition import append_activity_event
from backend.app.acquisition.ops.optimization_signals import (
    DELIVERY_ERROR_THRESHOLD,
    MIN_DECISION_VOLUME,
    MIN_ROUTING_SAMPLE,
    ROUTING_FAIL_RATE_THRESHOLD,
    OptimizationInputs,
    WindowCounters,
    evaluate_flight_optimization,
)
from backend.app.db.session import async_session_maker
from backend.app.models.acquisition_activity_event import (
    ACTOR_TYPE_SYSTEM,
    AcquisitionActivityEvent,
)
from backend.app.models.own_company import OwnCompany
from backend.tests.conftest import _init_data, _set_tenant


def _inputs(
    *,
    flight_status: str = "active",
    counters: WindowCounters,
    kpi_leads: int = 0,
    spend: str = "0.0000",
) -> OptimizationInputs:
    end = datetime(2026, 7, 23, 12, 0, tzinfo=timezone.utc)
    return OptimizationInputs(
        campaign_id="camp",
        flight_id="flight",
        campaign_status="active",
        flight_status=flight_status,
        window_hours=24,
        window_start=end - timedelta(hours=24),
        window_end=end,
        counters=counters,
        kpi_leads=kpi_leads,
        spend=spend,
    )


def test_evaluate_insufficient_volume_and_zero_intake() -> None:
    snap = evaluate_flight_optimization(
        _inputs(counters=WindowCounters(0, 0, 0, 0), spend="0.0000", kpi_leads=0)
    )
    assert snap.assessment == "insufficient_data"
    assert snap.recommended_action == "none"
    assert "insufficient_volume" in snap.reason_codes

    almost = evaluate_flight_optimization(
        _inputs(
            counters=WindowCounters(
                submissions=0,
                routing_completed=2,
                routing_failed=2,
                delivery_errors=0,
            )
        )
    )
    assert almost.counters.decision_volume == MIN_DECISION_VOLUME - 1
    assert almost.assessment == "insufficient_data"
    assert almost.recommended_action == "none"


def test_evaluate_routing_fail_rate_boundary() -> None:
    # Exactly on threshold: 3/6 = 0.50, sample >= MIN_ROUTING_SAMPLE
    on = evaluate_flight_optimization(
        _inputs(counters=WindowCounters(0, 3, 3, 0))
    )
    assert on.counters.routing_sample >= MIN_ROUTING_SAMPLE
    assert on.counters.routing_fail_rate == ROUTING_FAIL_RATE_THRESHOLD
    assert on.assessment == "suggest_pause"
    assert on.recommended_action == "suggest_pause"
    assert "routing_fail_rate" in on.reason_codes

    below = evaluate_flight_optimization(
        _inputs(counters=WindowCounters(0, 4, 2, 0))
    )
    assert below.counters.routing_fail_rate is not None
    assert below.counters.routing_fail_rate < ROUTING_FAIL_RATE_THRESHOLD
    assert below.assessment == "healthy"
    assert below.recommended_action == "none"

    above = evaluate_flight_optimization(
        _inputs(counters=WindowCounters(0, 2, 4, 0))
    )
    assert above.assessment == "suggest_pause"
    assert above.recommended_action == "suggest_pause"


def test_evaluate_delivery_errors_boundary() -> None:
    # Volume needs MIN_DECISION_VOLUME; delivery errors alone at threshold may be short.
    on = evaluate_flight_optimization(
        _inputs(
            counters=WindowCounters(
                submissions=2,
                routing_completed=0,
                routing_failed=0,
                delivery_errors=DELIVERY_ERROR_THRESHOLD,
            )
        )
    )
    assert on.counters.decision_volume >= MIN_DECISION_VOLUME
    assert on.assessment == "suggest_pause"
    assert "delivery_errors" in on.reason_codes

    below = evaluate_flight_optimization(
        _inputs(
            counters=WindowCounters(
                submissions=3,
                routing_completed=0,
                routing_failed=0,
                delivery_errors=DELIVERY_ERROR_THRESHOLD - 1,
            )
        )
    )
    assert below.assessment == "healthy"
    assert below.recommended_action == "none"


def test_evaluate_non_active_flight() -> None:
    for status in ("paused", "completed", "planned"):
        snap = evaluate_flight_optimization(
            _inputs(
                flight_status=status,
                counters=WindowCounters(0, 0, 10, 10),
            )
        )
        assert snap.assessment == "insufficient_data"
        assert snap.recommended_action == "none"
        assert "flight_not_active" in snap.reason_codes


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
            "name": f"S5 {uuid4().hex[:6]}",
            "goal_type": "hiring",
            "primary_kpi": "hires",
            "targets": [],
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _launch(
    client: AsyncClient, headers: dict, campaign_id: str, flight_id: str
) -> None:
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
    base: datetime | None = None,
) -> None:
    t0 = base or datetime.now(timezone.utc) - timedelta(minutes=30)
    async with async_session_maker() as session:
        await _set_tenant(session, tenant_id)
        for i, et in enumerate(event_types):
            payload: dict = {}
            if et == "SubmissionReceived":
                payload = {"normalized_schema_version": "1"}
            elif et == "RoutingCompleted":
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
                source_event_id=f"s5-{i}-{uuid4().hex[:8]}",
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


@pytest.mark.asyncio
async def test_http_zero_intake_insufficient_data(
    client: AsyncClient, auth_headers: dict, tenant_id: str
) -> None:
    await _init_data()
    own_company_id = await _default_own_company_id(tenant_id)
    headers = {**auth_headers, "X-Own-Company-Id": own_company_id}
    camp = await _create_campaign(client, headers)
    campaign_id = camp["id"]
    flight_id = camp["flights"][0]["id"]
    await _launch(client, headers, campaign_id, flight_id)

    resp = await client.get(
        f"/api/v1/platform/campaigns/{campaign_id}/flights/{flight_id}/optimization",
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["flight_status"] == "active"
    assert body["assessment"] == "insufficient_data"
    assert body["recommended_action"] == "none"
    assert body["spend"] == "0.0000"
    assert body["kpi_leads"] == 0
    assert body["counters"]["decision_volume"] == 0
    assert "insufficient_volume" in body["reason_codes"]


@pytest.mark.asyncio
async def test_http_routing_threshold_and_healthy(
    client: AsyncClient, auth_headers: dict, tenant_id: str
) -> None:
    await _init_data()
    own_company_id = await _default_own_company_id(tenant_id)
    headers = {**auth_headers, "X-Own-Company-Id": own_company_id}
    camp = await _create_campaign(client, headers)
    campaign_id = camp["id"]
    flight_id = camp["flights"][0]["id"]
    await _launch(client, headers, campaign_id, flight_id)

    # Exactly on fail-rate threshold
    await _seed_window_events(
        tenant_id=tenant_id,
        campaign_id=campaign_id,
        flight_id=flight_id,
        event_types=(["RoutingCompleted"] * 3) + (["RoutingFailed"] * 3),
    )
    on = await client.get(
        f"/api/v1/platform/campaigns/{campaign_id}/flights/{flight_id}/optimization",
        headers=headers,
    )
    assert on.status_code == 200, on.text
    assert on.json()["assessment"] == "suggest_pause"
    assert on.json()["recommended_action"] == "suggest_pause"
    assert "routing_fail_rate" in on.json()["reason_codes"]

    # Separate flight: below threshold → healthy
    camp2 = await _create_campaign(client, headers)
    c2, f2 = camp2["id"], camp2["flights"][0]["id"]
    await _launch(client, headers, c2, f2)
    await _seed_window_events(
        tenant_id=tenant_id,
        campaign_id=c2,
        flight_id=f2,
        event_types=(["RoutingCompleted"] * 4) + (["RoutingFailed"] * 2),
    )
    healthy = await client.get(
        f"/api/v1/platform/campaigns/{c2}/flights/{f2}/optimization",
        headers=headers,
    )
    assert healthy.status_code == 200, healthy.text
    assert healthy.json()["assessment"] == "healthy"
    assert healthy.json()["recommended_action"] == "none"


@pytest.mark.asyncio
async def test_http_paused_and_completed_no_pause_suggestion(
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
        event_types=(["RoutingFailed"] * 6),
    )

    paused = await client.post(
        f"/api/v1/platform/campaigns/{campaign_id}/flights/{flight_id}/pause",
        headers=headers,
        json={},
    )
    assert paused.status_code == 200, paused.text

    opt_paused = await client.get(
        f"/api/v1/platform/campaigns/{campaign_id}/flights/{flight_id}/optimization",
        headers=headers,
    )
    assert opt_paused.status_code == 200, opt_paused.text
    assert opt_paused.json()["flight_status"] == "paused"
    assert opt_paused.json()["assessment"] == "insufficient_data"
    assert opt_paused.json()["recommended_action"] == "none"
    assert "flight_not_active" in opt_paused.json()["reason_codes"]

    camp2 = await _create_campaign(client, headers)
    c2, f2 = camp2["id"], camp2["flights"][0]["id"]
    await _launch(client, headers, c2, f2)
    await _seed_window_events(
        tenant_id=tenant_id,
        campaign_id=c2,
        flight_id=f2,
        event_types=(["DeliveryErrorOccurred"] * 5),
    )
    completed = await client.post(
        f"/api/v1/platform/campaigns/{c2}/flights/{f2}/complete",
        headers=headers,
        json={},
    )
    assert completed.status_code == 200, completed.text
    opt_done = await client.get(
        f"/api/v1/platform/campaigns/{c2}/flights/{f2}/optimization",
        headers=headers,
    )
    assert opt_done.status_code == 200, opt_done.text
    assert opt_done.json()["flight_status"] == "completed"
    assert opt_done.json()["recommended_action"] == "none"
    assert "flight_not_active" in opt_done.json()["reason_codes"]


@pytest.mark.asyncio
async def test_http_repeat_get_has_no_side_effects(
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
        event_types=(["RoutingCompleted"] * 2) + (["RoutingFailed"] * 4),
    )

    before = await _activity_count(tenant_id, flight_id)
    first = await client.get(
        f"/api/v1/platform/campaigns/{campaign_id}/flights/{flight_id}/optimization",
        headers=headers,
    )
    second = await client.get(
        f"/api/v1/platform/campaigns/{campaign_id}/flights/{flight_id}/optimization",
        headers=headers,
    )
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["assessment"] == second.json()["assessment"] == "suggest_pause"
    assert first.json()["recommended_action"] == "suggest_pause"
    after = await _activity_count(tenant_id, flight_id)
    assert after == before

    runtime = await client.get(
        f"/api/v1/platform/campaigns/{campaign_id}/flights/{flight_id}/runtime",
        headers=headers,
    )
    assert runtime.status_code == 200
    assert runtime.json()["flight_status"] == "active"


@pytest.mark.asyncio
async def test_http_cross_company_optimization_404(
    client: AsyncClient, auth_headers: dict, tenant_id: str
) -> None:
    await _init_data()
    own_a = await _default_own_company_id(tenant_id)
    own_b = str(uuid4())
    async with async_session_maker() as session:
        session.add(
            OwnCompany(
                id=own_b,
                tenant_id=tenant_id,
                name=f"Foreign {uuid4().hex[:6]}",
                is_archived=False,
            )
        )
        await session.commit()

    camp = await client.post(
        "/api/v1/platform/campaigns",
        headers={**auth_headers, "X-Own-Company-Id": own_a},
        json={
            "name": f"S5 scope {uuid4().hex[:6]}",
            "goal_type": "hiring",
            "primary_kpi": "hires",
            "own_company_id": own_a,
            "targets": [],
        },
    )
    assert camp.status_code == 201, camp.text
    body = camp.json()
    path = (
        f"/api/v1/platform/campaigns/{body['id']}/flights/"
        f"{body['flights'][0]['id']}/optimization"
    )
    forbidden = await client.get(
        path, headers={**auth_headers, "X-Own-Company-Id": own_b}
    )
    assert forbidden.status_code == 404, forbidden.text
