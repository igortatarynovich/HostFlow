"""Stage 3E PR-3 — Acquisition Activity Timeline Read API."""

from __future__ import annotations

import ast
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from backend.app.acquisition import append_activity_event
from backend.app.acquisition.activity import ACTIVITY_LIST_ORDER
from backend.app.api.v1.platform import acquisition_activity as activity_api
from backend.app.db.session import async_session_maker
from backend.app.models.acquisition_activity_event import ACTOR_TYPE_SYSTEM
from backend.app.models.campaign import Campaign, CampaignRun
from backend.app.models.own_company import OwnCompany
from backend.app.models.tenant import Tenant
from backend.tests.conftest import _init_data

_API_PATH = Path(activity_api.__file__)
_LIST_URL = "/api/v1/platform/acquisition-activity"


async def _ensure_tenant(db, tenant_id: str) -> None:
    exists = (
        await db.execute(select(Tenant.id).where(Tenant.id == tenant_id))
    ).scalar_one_or_none()
    if exists is not None:
        return
    suffix = tenant_id.replace("-", "")[:8]
    db.add(
        Tenant(
            id=tenant_id,
            name=f"Tenant {suffix}",
            slug=f"t-{suffix}",
            api_key=f"api-{suffix}-{uuid4().hex[:8]}",
            is_active=True,
        )
    )
    await db.flush()


async def _own_company_id(db, tenant_id: str) -> str:
    row = await db.execute(
        select(OwnCompany.id)
        .where(OwnCompany.tenant_id == tenant_id, OwnCompany.is_archived.is_(False))
        .order_by(OwnCompany.created_at.asc())
        .limit(1)
    )
    oc = row.scalar_one_or_none()
    if oc is None:
        oc = str(uuid4())
        db.add(OwnCompany(id=oc, tenant_id=tenant_id, name=f"OC {uuid4().hex[:6]}"))
        await db.flush()
    return str(oc)


async def _seed_campaign_flight(db, *, tenant_id: str) -> tuple[Campaign, CampaignRun]:
    await _ensure_tenant(db, tenant_id)
    oc = await _own_company_id(db, tenant_id)
    campaign = Campaign(
        id=str(uuid4()),
        tenant_id=tenant_id,
        own_company_id=oc,
        name=f"Campaign {uuid4().hex[:6]}",
        status="active",
        goal_type="hiring",
        primary_kpi="hires",
    )
    db.add(campaign)
    await db.flush()
    flight = CampaignRun(
        id=str(uuid4()),
        tenant_id=tenant_id,
        campaign_id=campaign.id,
        code="flight_1",
        name="Flight 1",
        status="active",
    )
    db.add(flight)
    campaign.current_flight_id = flight.id
    await db.flush()
    return campaign, flight


def test_read_api_has_no_write_routes() -> None:
    src = _API_PATH.read_text(encoding="utf-8")
    assert "@router.post" not in src
    assert "@router.put" not in src
    assert "@router.patch" not in src
    assert "@router.delete" not in src
    assert "from backend.app.acquisition.activity.append_service" not in src
    assert "list_activity_events" in src
    assert "selectinload" not in src
    assert "joinedload" not in src
    flat: set[str] = set()
    for route in activity_api.router.routes:
        methods = getattr(route, "methods", None) or set()
        flat |= set(methods)
    assert flat <= {"GET", "HEAD"}
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            name = getattr(node.func, "id", None) or getattr(node.func, "attr", None)
            if name in {"AcquisitionActivityEvent", "append_activity_event"}:
                raise AssertionError(f"forbidden call at line {node.lineno}")


@pytest.mark.asyncio
async def test_list_activity_filters_and_order(
    client: AsyncClient, auth_headers: dict
) -> None:
    data = await _init_data()
    tenant_id = data["tenant_id"]
    t0 = datetime(2026, 7, 21, 10, 0, tzinfo=timezone.utc)

    async with async_session_maker() as db:
        camp, flight = await _seed_campaign_flight(db, tenant_id=tenant_id)
        other, other_flight = await _seed_campaign_flight(db, tenant_id=tenant_id)
        payloads = {
            "FlightCreated": {"new_status": "planned"},
            "FlightStarted": {"previous_status": "planned", "new_status": "active"},
            "EndpointChanged": {"endpoint_id": "form:ep-unique", "change_kind": "attached"},
        }
        endpoint_id = f"form:ep-{uuid4().hex[:8]}"
        payloads["EndpointChanged"] = {
            "endpoint_id": endpoint_id,
            "change_kind": "attached",
        }
        for i, et in enumerate(["FlightCreated", "FlightStarted", "EndpointChanged"]):
            await append_activity_event(
                db,
                tenant_id=tenant_id,
                campaign_id=camp.id,
                flight_id=flight.id,
                endpoint_id=endpoint_id if et == "EndpointChanged" else None,
                event_type=et,
                event_version="1",
                payload=payloads[et],
                actor_type=ACTOR_TYPE_SYSTEM,
                occurred_at=t0 + timedelta(minutes=i),
                source_event_id=f"read-api-{i}-{uuid4().hex[:8]}",
            )
        await append_activity_event(
            db,
            tenant_id=tenant_id,
            campaign_id=other.id,
            flight_id=other_flight.id,
            event_type="FlightCreated",
            event_version="1",
            payload={"new_status": "planned"},
            actor_type=ACTOR_TYPE_SYSTEM,
            occurred_at=t0 + timedelta(hours=1),
            source_event_id=f"other-{uuid4().hex[:8]}",
        )
        await db.commit()
        campaign_id = camp.id
        flight_id = flight.id

    resp = await client.get(
        _LIST_URL,
        headers=auth_headers,
        params={"campaign_id": campaign_id, "limit": 50},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["order"] == list(ACTIVITY_LIST_ORDER)
    types = [item["event_type"] for item in body["items"]]
    assert types == ["FlightCreated", "FlightStarted", "EndpointChanged"]
    assert all(item["campaign_id"] == campaign_id for item in body["items"])

    by_flight = await client.get(
        _LIST_URL,
        headers=auth_headers,
        params={"flight_id": flight_id},
    )
    assert by_flight.status_code == 200
    assert len(by_flight.json()["items"]) == 3

    by_type = await client.get(
        _LIST_URL,
        headers=auth_headers,
        params=[("campaign_id", campaign_id), ("event_type", "FlightStarted")],
    )
    assert by_type.status_code == 200
    assert [i["event_type"] for i in by_type.json()["items"]] == ["FlightStarted"]

    by_endpoint = await client.get(
        _LIST_URL,
        headers=auth_headers,
        params={"campaign_id": campaign_id, "endpoint_id": endpoint_id},
    )
    assert by_endpoint.status_code == 200
    assert len(by_endpoint.json()["items"]) == 1
    assert by_endpoint.json()["items"][0]["event_type"] == "EndpointChanged"


@pytest.mark.asyncio
async def test_cursor_pagination_stable(
    client: AsyncClient, auth_headers: dict
) -> None:
    data = await _init_data()
    tenant_id = data["tenant_id"]
    t0 = datetime(2026, 7, 21, 12, 0, tzinfo=timezone.utc)

    async with async_session_maker() as db:
        camp, flight = await _seed_campaign_flight(db, tenant_id=tenant_id)
        ids: list[str] = []
        for i in range(5):
            row = await append_activity_event(
                db,
                tenant_id=tenant_id,
                campaign_id=camp.id,
                flight_id=flight.id,
                event_type="FlightPaused" if i % 2 else "FlightResumed",
                event_version="1",
                payload={
                    "previous_status": "active" if i % 2 else "paused",
                    "new_status": "paused" if i % 2 else "active",
                },
                actor_type=ACTOR_TYPE_SYSTEM,
                occurred_at=t0 + timedelta(seconds=i),
                source_event_id=f"page-{i}-{uuid4().hex[:8]}",
            )
            ids.append(row.id)
        await db.commit()
        campaign_id = camp.id

    page1 = await client.get(
        _LIST_URL,
        headers=auth_headers,
        params={"campaign_id": campaign_id, "limit": 2},
    )
    assert page1.status_code == 200
    b1 = page1.json()
    assert len(b1["items"]) == 2
    assert b1["next_cursor"] is not None
    assert [i["id"] for i in b1["items"]] == ids[:2]

    page2 = await client.get(
        _LIST_URL,
        headers=auth_headers,
        params={
            "campaign_id": campaign_id,
            "limit": 2,
            "after_occurred_at": b1["next_cursor"]["occurred_at"],
            "after_id": b1["next_cursor"]["id"],
        },
    )
    assert page2.status_code == 200
    b2 = page2.json()
    assert [i["id"] for i in b2["items"]] == ids[2:4]
    assert b2["next_cursor"] is not None

    page3 = await client.get(
        _LIST_URL,
        headers=auth_headers,
        params={
            "campaign_id": campaign_id,
            "limit": 2,
            "after_occurred_at": b2["next_cursor"]["occurred_at"],
            "after_id": b2["next_cursor"]["id"],
        },
    )
    assert page3.status_code == 200
    b3 = page3.json()
    assert [i["id"] for i in b3["items"]] == ids[4:]
    assert b3["next_cursor"] is None


@pytest.mark.asyncio
async def test_cursor_stable_when_occurred_at_ties(
    client: AsyncClient, auth_headers: dict
) -> None:
    data = await _init_data()
    tenant_id = data["tenant_id"]
    tie = datetime(2026, 7, 21, 15, 0, tzinfo=timezone.utc)

    async with async_session_maker() as db:
        camp, flight = await _seed_campaign_flight(db, tenant_id=tenant_id)
        for i in range(3):
            await append_activity_event(
                db,
                tenant_id=tenant_id,
                campaign_id=camp.id,
                flight_id=flight.id,
                event_type="FlightStarted",
                event_version="1",
                payload={"previous_status": "planned", "new_status": "active"},
                actor_type=ACTOR_TYPE_SYSTEM,
                occurred_at=tie,
                source_event_id=f"tie-{i}-{uuid4().hex[:8]}",
            )
        await db.commit()
        campaign_id = camp.id

    full = await client.get(
        _LIST_URL,
        headers=auth_headers,
        params={"campaign_id": campaign_id, "limit": 50},
    )
    assert full.status_code == 200
    ordered = [i["id"] for i in full.json()["items"]]
    assert len(ordered) == 3
    assert len(set(i["occurred_at"] for i in full.json()["items"])) == 1

    page1 = await client.get(
        _LIST_URL,
        headers=auth_headers,
        params={"campaign_id": campaign_id, "limit": 2},
    )
    assert page1.status_code == 200
    b1 = page1.json()
    assert [i["id"] for i in b1["items"]] == ordered[:2]
    assert b1["next_cursor"]["id"] == ordered[1]

    page2 = await client.get(
        _LIST_URL,
        headers=auth_headers,
        params={
            "campaign_id": campaign_id,
            "limit": 2,
            "after_occurred_at": b1["next_cursor"]["occurred_at"],
            "after_id": b1["next_cursor"]["id"],
        },
    )
    assert page2.status_code == 200
    assert [i["id"] for i in page2.json()["items"]] == ordered[2:]
    # Strict > (occurred_at, id): cursor row must not reappear.
    assert ordered[1] not in [i["id"] for i in page2.json()["items"]]


@pytest.mark.asyncio
async def test_cursor_params_must_be_paired(
    client: AsyncClient, auth_headers: dict
) -> None:
    resp = await client.get(
        _LIST_URL,
        headers=auth_headers,
        params={"after_id": str(uuid4())},
    )
    assert resp.status_code == 422
    resp2 = await client.get(
        _LIST_URL,
        headers=auth_headers,
        params={"after_occurred_at": "2026-07-21T12:00:00+00:00"},
    )
    assert resp2.status_code == 422


@pytest.mark.asyncio
async def test_time_bounds_are_exclusive(
    client: AsyncClient, auth_headers: dict
) -> None:
    data = await _init_data()
    tenant_id = data["tenant_id"]
    t0 = datetime(2026, 7, 21, 16, 0, tzinfo=timezone.utc)

    async with async_session_maker() as db:
        camp, flight = await _seed_campaign_flight(db, tenant_id=tenant_id)
        for i, label in enumerate(["a", "b", "c"]):
            await append_activity_event(
                db,
                tenant_id=tenant_id,
                campaign_id=camp.id,
                flight_id=flight.id,
                event_type="FlightCreated",
                event_version="1",
                payload={"new_status": "planned"},
                actor_type=ACTOR_TYPE_SYSTEM,
                occurred_at=t0 + timedelta(minutes=i),
                source_event_id=f"bound-{label}-{uuid4().hex[:8]}",
            )
        await db.commit()
        campaign_id = camp.id

    # occurred_after exclusive: equal to first → only b,c
    after = await client.get(
        _LIST_URL,
        headers=auth_headers,
        params={
            "campaign_id": campaign_id,
            "occurred_after": t0.isoformat(),
        },
    )
    assert after.status_code == 200
    assert len(after.json()["items"]) == 2

    # occurred_before exclusive: equal to last → only a,b
    before = await client.get(
        _LIST_URL,
        headers=auth_headers,
        params={
            "campaign_id": campaign_id,
            "occurred_before": (t0 + timedelta(minutes=2)).isoformat(),
        },
    )
    assert before.status_code == 200
    assert len(before.json()["items"]) == 2


@pytest.mark.asyncio
async def test_unknown_event_type_and_malformed_ids_are_422(
    client: AsyncClient, auth_headers: dict
) -> None:
    bad_type = await client.get(
        _LIST_URL,
        headers=auth_headers,
        params=[("event_type", "NotACatalogType")],
    )
    assert bad_type.status_code == 422

    bad_campaign = await client.get(
        _LIST_URL,
        headers=auth_headers,
        params={"campaign_id": "not-a-uuid"},
    )
    assert bad_campaign.status_code == 422

    bad_cursor = await client.get(
        _LIST_URL,
        headers=auth_headers,
        params={
            "after_occurred_at": "2026-07-21T12:00:00+00:00",
            "after_id": "not-a-uuid",
        },
    )
    assert bad_cursor.status_code == 422

    bad_dt = await client.get(
        _LIST_URL,
        headers=auth_headers,
        params={"occurred_after": "yesterday"},
    )
    assert bad_dt.status_code == 422


@pytest.mark.asyncio
async def test_limit_upper_bound(client: AsyncClient, auth_headers: dict) -> None:
    resp = await client.get(
        _LIST_URL,
        headers=auth_headers,
        params={"limit": 201},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_tenant_isolation_on_all_filters(
    client: AsyncClient, auth_headers: dict
) -> None:
    data = await _init_data()
    tenant_a = data["tenant_id"]
    tenant_b = str(uuid4())
    submission_b = str(uuid4())
    outcome_b = str(uuid4())

    async with async_session_maker() as db:
        camp_a, flight_a = await _seed_campaign_flight(db, tenant_id=tenant_a)
        camp_b, flight_b = await _seed_campaign_flight(db, tenant_id=tenant_b)
        await append_activity_event(
            db,
            tenant_id=tenant_a,
            campaign_id=camp_a.id,
            flight_id=flight_a.id,
            event_type="FlightCreated",
            event_version="1",
            payload={"new_status": "planned"},
            actor_type=ACTOR_TYPE_SYSTEM,
            source_event_id=f"iso-a-{uuid4().hex[:8]}",
        )
        await append_activity_event(
            db,
            tenant_id=tenant_b,
            campaign_id=camp_b.id,
            flight_id=flight_b.id,
            endpoint_id="form:secret-b",
            submission_id=submission_b,
            outcome_id=outcome_b,
            result_id="result-secret-b",
            event_type="FlightCreated",
            event_version="1",
            payload={"new_status": "planned"},
            actor_type=ACTOR_TYPE_SYSTEM,
            source_event_id=f"iso-b-{uuid4().hex[:8]}",
        )
        await db.commit()
        flight_b_id = flight_b.id
        campaign_a = camp_a.id
        campaign_b = camp_b.id

    # Own tenant data still visible.
    own = await client.get(
        _LIST_URL,
        headers=auth_headers,
        params={"campaign_id": campaign_a},
    )
    assert own.status_code == 200
    assert own.json()["items"]
    assert all(i["tenant_id"] == tenant_a for i in own.json()["items"])

    # Foreign filter keys must not leak tenant B rows to tenant A token.
    for params in (
        {"campaign_id": campaign_b},
        {"flight_id": flight_b_id},
        {"submission_id": submission_b},
        {"outcome_id": outcome_b},
        {"endpoint_id": "form:secret-b"},
        {"result_id": "result-secret-b"},
    ):
        resp = await client.get(_LIST_URL, headers=auth_headers, params=params)
        assert resp.status_code == 200, params
        assert resp.json()["items"] == [], params


@pytest.mark.asyncio
async def test_unauthenticated_rejected(client: AsyncClient) -> None:
    resp = await client.get(_LIST_URL)
    assert resp.status_code in {401, 403}
