"""A3-C — legal_stay_confirmation not_applicable for EU citizenship."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from backend.tests.test_support.candidate_evidence_helpers import (
    checklist_item,
    get_requirements_workspace,
    setup_driver_ce_candidate,
)

pytestmark = pytest.mark.anyio


async def test_workspace_legal_stay_not_applicable_for_eu_citizenship(
    client: AsyncClient,
    manager_headers: dict[str, str],
    db,
    tenant_id: str,
) -> None:
    candidate, _ = await setup_driver_ce_candidate(db, tenant_id)
    cid = str(candidate.id)

    patch_resp = await client.patch(
        f"/api/v1/candidates/{cid}",
        headers=manager_headers,
        json={
            "extra": {"citizenship": "PL"},
            "personal_data": {"citizenship": "PL"},
        },
    )
    assert patch_resp.status_code == 200, patch_resp.text

    workspace = await get_requirements_workspace(client, manager_headers, cid)
    item = checklist_item(workspace["checklist"], "legal_stay_confirmation")
    assert item["evaluation"]["status"] == "not_applicable"
    assert item["fulfilled"] is True

    missing = workspace["pipeline_blockers"].get("missing_requirements") or []
    assert "legal_stay_confirmation" not in missing

    blocking_codes = {
        str(row.get("requirement_code") or row.get("code") or "")
        for row in workspace["transfer_readiness"].get("blocking_reasons") or []
        if isinstance(row, dict)
    }
    assert "legal_stay_confirmation" not in blocking_codes


async def test_workspace_legal_stay_required_for_non_eu(
    client: AsyncClient,
    manager_headers: dict[str, str],
    db,
    tenant_id: str,
) -> None:
    candidate, _ = await setup_driver_ce_candidate(db, tenant_id)
    cid = str(candidate.id)

    patch_resp = await client.patch(
        f"/api/v1/candidates/{cid}",
        headers=manager_headers,
        json={
            "extra": {"citizenship": "UA"},
            "personal_data": {"citizenship": "UA"},
        },
    )
    assert patch_resp.status_code == 200, patch_resp.text

    workspace = await get_requirements_workspace(client, manager_headers, cid)
    item = checklist_item(workspace["checklist"], "legal_stay_confirmation")
    assert item["evaluation"]["status"] == "missing"
    assert item["fulfilled"] is False
    assert "legal_stay_confirmation" in (workspace["pipeline_blockers"].get("missing_requirements") or [])
