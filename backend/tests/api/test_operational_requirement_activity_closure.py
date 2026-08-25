"""A3-B4 — operational (activity-type) requirements in workspace + complete-activity API."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models import Lead
from backend.tests.test_support.candidate_evidence_helpers import (
    get_requirements_workspace,
    setup_driver_ce_candidate,
)

pytestmark = pytest.mark.anyio


async def _create_call_activity(
    client: AsyncClient,
    headers: dict[str, str],
    *,
    candidate_id: str,
    activity_type: str = "call",
    complete: bool = False,
) -> str:
    due_at = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    created = await client.post(
        "/api/v1/activities",
        headers=headers,
        json={
            "title": "Call candidate",
            "type": activity_type,
            "entity_type": "candidate",
            "entity_id": candidate_id,
            "due_at": due_at,
        },
    )
    assert created.status_code == 201, created.text
    activity_id = created.json()["id"]
    if complete:
        done = await client.post(
            f"/api/v1/activities/{activity_id}/complete",
            headers=headers,
        )
        assert done.status_code == 200, done.text
    return str(activity_id)


async def test_workspace_includes_first_contact_operational_requirement_open(
    client: AsyncClient,
    manager_headers: dict[str, str],
    db: AsyncSession,
    tenant_id: str,
) -> None:
    candidate, _ = await setup_driver_ce_candidate(db, tenant_id)
    workspace = await get_requirements_workspace(client, manager_headers, str(candidate.id))
    ops = workspace.get("operational_requirements") or []
    assert len(ops) == 1
    row = ops[0]
    assert row["requirement_code"] == "first_contact_completed"
    assert row["type"] == "activity"
    assert row["status"] == "open"
    assert row.get("activity_id") is None


async def test_complete_activity_closes_operational_requirement(
    client: AsyncClient,
    manager_headers: dict[str, str],
    db: AsyncSession,
    tenant_id: str,
) -> None:
    candidate, _ = await setup_driver_ce_candidate(db, tenant_id)
    cid = str(candidate.id)
    activity_id = await _create_call_activity(
        client,
        manager_headers,
        candidate_id=cid,
        complete=False,
    )

    closed = await client.post(
        f"/api/v1/candidates/{cid}/requirements/first_contact_completed/complete-activity",
        headers=manager_headers,
        json={"activity_id": activity_id},
    )
    assert closed.status_code == 200, closed.text
    body = closed.json()
    assert body["status"] == "satisfied"
    assert body["activity_id"] == activity_id
    assert body["satisfied_via"] == "manual"

    workspace = await get_requirements_workspace(client, manager_headers, cid)
    ops = workspace["operational_requirements"]
    assert ops[0]["status"] == "satisfied"
    assert workspace["summary"]["blocking_open_count"] >= 0


async def test_done_call_activity_auto_satisfies_operational_requirement(
    client: AsyncClient,
    manager_headers: dict[str, str],
    db: AsyncSession,
    tenant_id: str,
) -> None:
    candidate, _ = await setup_driver_ce_candidate(db, tenant_id)
    cid = str(candidate.id)
    await _create_call_activity(
        client,
        manager_headers,
        candidate_id=cid,
        complete=True,
    )

    workspace = await get_requirements_workspace(client, manager_headers, cid)
    row = workspace["operational_requirements"][0]
    assert row["status"] == "satisfied"
    assert row["satisfied_via"] == "activity"
    assert row.get("activity_id")


async def test_lead_continuity_auto_satisfies_first_contact(
    client: AsyncClient,
    manager_headers: dict[str, str],
    db: AsyncSession,
    tenant_id: str,
) -> None:
    candidate, company_id = await setup_driver_ce_candidate(db, tenant_id)
    cid = str(candidate.id)
    lead = Lead(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        company_id=company_id,
        candidate_id=cid,
        stage="contacted",
        status="active",
        source="test",
        normalized={},
    )
    db.add(lead)
    await db.commit()

    workspace = await get_requirements_workspace(client, manager_headers, cid)
    row = workspace["operational_requirements"][0]
    assert row["status"] == "satisfied"
    assert row["satisfied_via"] == "lead_continuity"
    assert "lead_stage:contacted" in (row.get("continuity_reasons") or [])


async def test_request_info_lead_continuity_auto_satisfies_first_contact(
    client: AsyncClient,
    manager_headers: dict[str, str],
    db: AsyncSession,
    tenant_id: str,
) -> None:
    """Guard 4: info_requested intake on linked lead closes first_contact via continuity."""
    candidate, company_id = await setup_driver_ce_candidate(db, tenant_id)
    cid = str(candidate.id)
    lead = Lead(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        company_id=company_id,
        candidate_id=cid,
        stage="new",
        status="processed",
        source="test",
        normalized={
            "intake_resolution_v1": {
                "status": "info_requested",
                "last_decision": "request_info",
                "note": "Awaiting documents",
            }
        },
    )
    db.add(lead)
    await db.commit()

    workspace = await get_requirements_workspace(client, manager_headers, cid)
    row = workspace["operational_requirements"][0]
    assert row["status"] == "satisfied"
    assert row["satisfied_via"] == "lead_continuity"
    assert any(
        str(r).startswith("intake_resolution:info_requested")
        for r in (row.get("continuity_reasons") or [])
    )


async def test_complete_activity_rejects_wrong_candidate(
    client: AsyncClient,
    manager_headers: dict[str, str],
    db: AsyncSession,
    tenant_id: str,
) -> None:
    candidate_a, _ = await setup_driver_ce_candidate(db, tenant_id)
    candidate_b, _ = await setup_driver_ce_candidate(db, tenant_id)
    activity_id = await _create_call_activity(
        client,
        manager_headers,
        candidate_id=str(candidate_a.id),
    )

    resp = await client.post(
        f"/api/v1/candidates/{candidate_b.id}/requirements/first_contact_completed/complete-activity",
        headers=manager_headers,
        json={"activity_id": activity_id},
    )
    assert resp.status_code == 422, resp.text
