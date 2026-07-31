"""Stage 4 PR-3 — KPI HTTP, runtime snapshot, Live Intake Monitor."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from backend.app.acquisition import append_activity_event
from backend.app.acquisition.kpi_aggregates import aggregate_flight_kpi
from backend.app.acquisition.submission_routing import ACQUISITION_ROUTING_V1_KEY
from backend.app.db.session import async_session_maker
from backend.app.models.acquisition_activity_event import ACTOR_TYPE_SYSTEM
from backend.app.models.lead import Lead
from backend.app.models.own_company import OwnCompany
from backend.tests.conftest import _init_data, _set_tenant


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
            "name": f"PR3 {uuid4().hex[:6]}",
            "goal_type": "hiring",
            "primary_kpi": "hires",
            "targets": [],
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


@pytest.mark.asyncio
async def test_kpi_and_runtime_snapshot_http(
    client: AsyncClient, auth_headers: dict, tenant_id: str
) -> None:
    await _init_data()
    own_company_id = await _default_own_company_id(tenant_id)
    headers = {**auth_headers, "X-Own-Company-Id": own_company_id}
    camp = await _create_campaign(client, headers)
    campaign_id = camp["id"]
    flight_id = camp["flights"][0]["id"]

    camp_kpi = await client.get(
        f"/api/v1/platform/campaigns/{campaign_id}/kpi",
        headers=headers,
    )
    assert camp_kpi.status_code == 200, camp_kpi.text
    body = camp_kpi.json()
    assert body["campaign_id"] == campaign_id
    assert body["leads"] == 0
    assert body["spend"] == "0.0000"
    assert len(body["flights"]) == 1

    flight_kpi = await client.get(
        f"/api/v1/platform/campaigns/{campaign_id}/flights/{flight_id}/kpi",
        headers=headers,
    )
    assert flight_kpi.status_code == 200, flight_kpi.text
    assert flight_kpi.json()["flight_id"] == flight_id

    async with async_session_maker() as session:
        await _set_tenant(session, tenant_id)
        expected = await aggregate_flight_kpi(
            session, tenant_id=tenant_id, flight_id=flight_id
        )
    assert flight_kpi.json()["spend"] == str(expected.spend)
    assert flight_kpi.json()["leads"] == expected.leads

    runtime = await client.get(
        f"/api/v1/platform/campaigns/{campaign_id}/flights/{flight_id}/runtime",
        headers=headers,
    )
    assert runtime.status_code == 200, runtime.text
    snap = runtime.json()
    assert snap["flight_id"] == flight_id
    assert snap["campaign_status"] == "draft"
    assert snap["flight_status"] == "planned"
    assert snap["is_current"] is True
    assert snap["endpoints"]["forms_total"] == 0
    assert snap["kpi"]["flight_id"] == flight_id
    assert "generated_at" in snap

    missing = await client.get(
        f"/api/v1/platform/campaigns/{campaign_id}/flights/{uuid4()}/runtime",
        headers=headers,
    )
    assert missing.status_code == 404


@pytest.mark.asyncio
async def test_live_intake_monitor_counters_and_allowlist(
    client: AsyncClient, auth_headers: dict, tenant_id: str
) -> None:
    await _init_data()
    own_company_id = await _default_own_company_id(tenant_id)
    headers = {**auth_headers, "X-Own-Company-Id": own_company_id}
    camp = await _create_campaign(client, headers)
    campaign_id = camp["id"]
    flight_id = camp["flights"][0]["id"]
    t0 = datetime(2026, 7, 23, 10, 0, tzinfo=timezone.utc)

    async with async_session_maker() as session:
        await _set_tenant(session, tenant_id)
        for i, et in enumerate(
            ["SubmissionReceived", "SubmissionReceived", "LeadCreated", "RoutingFailed"]
        ):
            payload: dict = {}
            if et == "LeadCreated":
                payload = {
                    "lead_id": str(uuid4()),
                    "submission_id": str(uuid4()),
                }
            elif et == "RoutingFailed":
                payload = {"reason_code": "no_target"}
            elif et == "SubmissionReceived":
                payload = {"normalized_schema_version": "1"}
            await append_activity_event(
                session,
                tenant_id=tenant_id,
                campaign_id=campaign_id,
                flight_id=flight_id,
                submission_id=str(uuid4()) if et != "RoutingFailed" else str(uuid4()),
                event_type=et,
                event_version="1",
                payload=payload,
                actor_type=ACTOR_TYPE_SYSTEM,
                occurred_at=t0 + timedelta(minutes=i),
                source_event_id=f"pr3-mon-{i}-{uuid4().hex[:8]}",
            )
        # Outside allowlist — must not appear in items
        await append_activity_event(
            session,
            tenant_id=tenant_id,
            campaign_id=campaign_id,
            flight_id=flight_id,
            event_type="FlightCreated",
            event_version="1",
            payload={"new_status": "planned"},
            actor_type=ACTOR_TYPE_SYSTEM,
            occurred_at=t0 + timedelta(minutes=10),
            source_event_id=f"pr3-mon-flight-{uuid4().hex[:8]}",
        )
        await session.commit()

    mon = await client.get(
        f"/api/v1/platform/campaigns/{campaign_id}/flights/{flight_id}/monitor/live-intake",
        headers=headers,
        params={"limit": 10},
    )
    assert mon.status_code == 200, mon.text
    body = mon.json()
    # submissions = Flight-attributed Lead rows (applicants), not Activity SubmissionReceived
    assert body["counters"]["submissions"] == 0
    assert body["counters"]["leads_activity"] == 1
    assert body["counters"]["routing_failed"] == 1
    assert body["counters"]["candidates"] == 0
    types = {item["event_type"] for item in body["items"]}
    assert "SubmissionReceived" in types
    assert "LeadCreated" in types
    assert "RoutingFailed" in types
    assert "FlightCreated" not in types
    assert "FlightCreated" not in body["event_types"]
    assert isinstance(body.get("applicants"), list)

    # Stamp two applicants onto this Flight — counter must match list SoT
    async with async_session_maker() as session:
        await _set_tenant(session, tenant_id)
        for i in range(2):
            lid = str(uuid4())
            session.add(
                Lead(
                    id=lid,
                    tenant_id=tenant_id,
                    source="meta",
                    status="processed",
                    lead_type="candidate",
                    lead_target_type="candidate",
                    external_id=f"pr3-app-{i}-{uuid4().hex[:8]}",
                    normalized={
                        "full_name": f"Applicant {i}",
                        "phone": f"+48111000{i:03d}",
                        ACQUISITION_ROUTING_V1_KEY: {
                            "status": "routed",
                            "campaign_id": campaign_id,
                            "campaign_run_id": flight_id,
                            "route_intent": "candidate_application",
                        },
                    },
                    payload={"ad_id": "120000000000000001"},
                )
            )
        await session.commit()

    mon2 = await client.get(
        f"/api/v1/platform/campaigns/{campaign_id}/flights/{flight_id}/monitor/live-intake",
        headers=headers,
        params={"limit": 10},
    )
    assert mon2.status_code == 200, mon2.text
    body2 = mon2.json()
    assert body2["counters"]["submissions"] == 2
    assert len(body2["applicants"]) == 2

    # Filtered subset
    filtered = await client.get(
        f"/api/v1/platform/campaigns/{campaign_id}/flights/{flight_id}/monitor/live-intake",
        headers=headers,
        params=[("event_type", "RoutingFailed")],
    )
    assert filtered.status_code == 200, filtered.text
    assert all(i["event_type"] == "RoutingFailed" for i in filtered.json()["items"])
    assert filtered.json()["counters"]["submissions"] == 2  # counters stay flight-wide

    bad = await client.get(
        f"/api/v1/platform/campaigns/{campaign_id}/flights/{flight_id}/monitor/live-intake",
        headers=headers,
        params=[("event_type", "FlightStarted")],
    )
    assert bad.status_code == 422
