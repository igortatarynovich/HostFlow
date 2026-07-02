"""B1 — handoff create returns structured 409 gate (parity with stage PATCH)."""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.tests.test_support.candidate_evidence_helpers import (
    ensure_tenant_link_internal_hr,
    get_requirements_workspace,
    setup_driver_ce_candidate,
)

pytestmark = pytest.mark.anyio


async def test_handoff_create_returns_409_handoff_docs_incomplete(
    client: AsyncClient,
    manager_headers: dict[str, str],
    recruiter_headers: dict[str, str],
    db: AsyncSession,
    tenant_id: str,
) -> None:
    candidate, company_id = await setup_driver_ce_candidate(db, tenant_id)
    cid = str(candidate.id)

    await ensure_tenant_link_internal_hr(
        client,
        manager_headers=manager_headers,
        tenant_id=tenant_id,
        company_id=company_id,
    )

    workspace = await get_requirements_workspace(client, manager_headers, cid)
    assert workspace["summary"]["handoff_ready"] is False

    await db.execute(
        text("UPDATE candidates SET stage = 'ready_for_handoff' WHERE id = :id"),
        {"id": cid},
    )
    await db.commit()

    handoff = await client.post(
        f"/api/v1/handoffs/candidates/{cid}",
        headers=recruiter_headers,
        json={"client_company_id": company_id, "destination": "internal_hr"},
    )
    assert handoff.status_code == 409, handoff.text
    detail = handoff.json().get("detail") or {}
    assert detail.get("code") == "handoff_docs_incomplete"
    assert isinstance(detail.get("blocking_reasons"), list)
    assert detail.get("transfer_policy", {}).get("policy_version")


async def test_handoff_bulk_returns_structured_gate_errors(
    client: AsyncClient,
    manager_headers: dict[str, str],
    recruiter_headers: dict[str, str],
    db: AsyncSession,
    tenant_id: str,
) -> None:
    candidate, company_id = await setup_driver_ce_candidate(db, tenant_id)
    cid = str(candidate.id)

    await ensure_tenant_link_internal_hr(
        client,
        manager_headers=manager_headers,
        tenant_id=tenant_id,
        company_id=company_id,
    )

    await db.execute(
        text("UPDATE candidates SET stage = 'ready_for_handoff' WHERE id = :id"),
        {"id": cid},
    )
    await db.commit()

    bulk = await client.post(
        "/api/v1/handoffs/bulk",
        headers=recruiter_headers,
        json={"candidate_ids": [cid], "client_company_id": company_id},
    )
    assert bulk.status_code == 200, bulk.text
    body = bulk.json()
    assert body["created"] == 0
    assert body["failed"] == 1
    assert len(body["errors"]) == 1
    row = body["errors"][0]
    assert row["candidate_id"] == cid
    assert row.get("detail", {}).get("code") == "handoff_docs_incomplete"
