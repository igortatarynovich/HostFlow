"""GET /candidates/{id} missing/deleted payload and recreate-from-application."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from backend.app.db.session import async_session_maker
from backend.app.models import Candidate, Lead
from backend.tests.conftest import _init_data, _set_tenant


def _now_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


@pytest.mark.anyio
async def test_get_unknown_candidate_returns_structured_not_found(
    client: AsyncClient,
    manager_headers: dict[str, str],
) -> None:
    missing_id = str(uuid.uuid4())
    resp = await client.get(f"/api/v1/candidates/{missing_id}", headers=manager_headers)
    assert resp.status_code == 404, resp.text
    detail = resp.json()["detail"]
    assert detail["code"] == "candidate_not_found"
    assert detail["can_recreate"] is False
    assert detail.get("application_id") in (None, "")


@pytest.mark.anyio
async def test_get_deleted_candidate_without_application(
    client: AsyncClient,
    manager_headers: dict[str, str],
    candidate_id: str,
    tenant_id: str,
) -> None:
    async with async_session_maker() as session:
        await _set_tenant(session, tenant_id)
        cand = await session.get(Candidate, candidate_id)
        assert cand is not None
        cand.deleted_at = _now_naive()
        await session.commit()

    resp = await client.get(f"/api/v1/candidates/{candidate_id}", headers=manager_headers)
    assert resp.status_code == 404, resp.text
    detail = resp.json()["detail"]
    assert detail["code"] == "candidate_deleted"
    assert detail["can_recreate"] is False


@pytest.mark.anyio
async def test_deleted_candidate_with_application_can_recreate(
    client: AsyncClient,
    manager_headers: dict[str, str],
    candidate_id: str,
    tenant_id: str,
) -> None:
    data = await _init_data()
    lead_id = str(uuid.uuid4())
    async with async_session_maker() as session:
        await _set_tenant(session, tenant_id)
        cand = await session.get(Candidate, candidate_id)
        assert cand is not None
        cand.deleted_at = _now_naive()
        session.add(
            Lead(
                id=lead_id,
                tenant_id=tenant_id,
                company_id=data["company_id"],
                vacancy_id=getattr(cand, "vacancy_id", None),
                source="meta",
                lead_type="candidate",
                lead_target_type="candidate",
                payload={"id": f"recreate-{uuid.uuid4().hex[:8]}"},
                normalized={
                    "first_name": cand.first_name,
                    "last_name": cand.last_name,
                    "email": cand.email,
                    "phone": cand.phone,
                },
                status="processed",
                candidate_id=candidate_id,
                external_id=f"ext-{uuid.uuid4().hex[:12]}",
            )
        )
        await session.commit()

    resp = await client.get(f"/api/v1/candidates/{candidate_id}", headers=manager_headers)
    assert resp.status_code == 404, resp.text
    detail = resp.json()["detail"]
    assert detail["code"] == "candidate_deleted"
    assert detail["can_recreate"] is True
    assert detail["application_id"] == lead_id

    recreate = await client.post(
        f"/api/v1/candidates/{candidate_id}/recreate-from-application",
        headers=manager_headers,
    )
    assert recreate.status_code == 200, recreate.text
    body = recreate.json()
    new_id = body["candidate_id"]
    assert new_id != candidate_id
    assert body["application_id"] == lead_id

    live = await client.get(f"/api/v1/candidates/{new_id}", headers=manager_headers)
    assert live.status_code == 200, live.text
    assert live.json()["id"] == new_id

    gone = await client.get(f"/api/v1/candidates/{candidate_id}", headers=manager_headers)
    assert gone.status_code == 404
    assert gone.json()["detail"]["code"] == "candidate_deleted"
    assert gone.json()["detail"]["can_recreate"] is False

    async with async_session_maker() as session:
        await _set_tenant(session, tenant_id)
        lead = (
            await session.execute(select(Lead).where(Lead.id == lead_id))
        ).scalar_one()
        assert str(lead.candidate_id) == new_id


@pytest.mark.anyio
async def test_recreate_live_candidate_conflicts(
    client: AsyncClient,
    manager_headers: dict[str, str],
    candidate_id: str,
) -> None:
    resp = await client.post(
        f"/api/v1/candidates/{candidate_id}/recreate-from-application",
        headers=manager_headers,
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["detail"]["code"] == "candidate_exists"
