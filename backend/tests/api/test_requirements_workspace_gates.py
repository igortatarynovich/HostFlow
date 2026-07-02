"""A4 — stage PATCH and handoff create gated on workspace.summary.handoff_ready."""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.tests.test_support.candidate_evidence_helpers import (
    close_driver_ce_requirements,
    ensure_tenant_link_internal_hr,
    get_requirements_workspace,
    setup_driver_ce_candidate,
)

pytestmark = pytest.mark.anyio


async def test_stage_patch_blocked_when_workspace_handoff_not_ready(
    client: AsyncClient,
    manager_headers: dict[str, str],
    db,
    tenant_id: str,
) -> None:
    candidate, _ = await setup_driver_ce_candidate(db, tenant_id)
    cid = str(candidate.id)

    workspace = await get_requirements_workspace(client, manager_headers, cid)
    assert workspace["summary"]["handoff_ready"] is False

    patch = await client.patch(
        f"/api/v1/candidates/{cid}",
        headers=manager_headers,
        json={"stage": "ready_for_handoff"},
    )
    assert patch.status_code == 409, patch.text
    detail = patch.json().get("detail") or {}
    assert detail.get("code") == "handoff_docs_incomplete"


async def test_handoff_create_blocked_when_workspace_handoff_not_ready(
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

    # Stage API blocks ready_for_handoff while handoff_ready is false — set stage directly to
    # isolate handoff create gate on the same transfer policy signal.
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


async def test_stage_and_handoff_allowed_when_workspace_handoff_ready(
    client: AsyncClient,
    manager_headers: dict[str, str],
    recruiter_headers: dict[str, str],
    db,
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
    await close_driver_ce_requirements(client, manager_headers, candidate_id=cid)

    workspace = await get_requirements_workspace(client, manager_headers, cid)
    assert workspace["summary"]["all_fulfilled"] is True
    assert workspace["summary"]["handoff_ready"] is True
    assert workspace["transfer_readiness"]["handoff_create_allowed"] is True

    patch = await client.patch(
        f"/api/v1/candidates/{cid}",
        headers=manager_headers,
        json={"stage": "ready_for_handoff"},
    )
    assert patch.status_code == 200, patch.text
    assert str(patch.json().get("stage") or "").lower() == "ready_for_handoff"

    handoff = await client.post(
        f"/api/v1/handoffs/candidates/{cid}",
        headers=recruiter_headers,
        json={"client_company_id": company_id, "destination": "internal_hr"},
    )
    assert handoff.status_code == 201, handoff.text
