"""A3-FE3 — Workspace data fields closure via PATCH candidate."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from backend.tests.test_support.candidate_evidence_helpers import (
    get_requirements_workspace,
    setup_driver_ce_candidate,
)

pytestmark = pytest.mark.anyio


async def test_workspace_field_requirements_satisfied_after_address_patch(
    client: AsyncClient,
    manager_headers: dict[str, str],
    db,
    tenant_id: str,
) -> None:
    candidate, _ = await setup_driver_ce_candidate(db, tenant_id)
    cid = str(candidate.id)

    before = await get_requirements_workspace(client, manager_headers, cid)
    address_row = next(
        row
        for row in before["field_requirements"]["required_fields"]
        if row["qualified_code"] == "platform.identity.address"
    )
    assert address_row["satisfied"] is False

    patch_resp = await client.patch(
        f"/api/v1/candidates/{cid}",
        headers=manager_headers,
        json={
            "extra": {
                "citizenship": "UA",
                "experience_eu_years": "5",
                "address": "Warsaw, Test Street 1",
            },
            "personal_data": {
                "address": "Warsaw, Test Street 1",
                "citizenship": "UA",
            },
        },
    )
    assert patch_resp.status_code == 200, patch_resp.text

    after = await get_requirements_workspace(client, manager_headers, cid)
    address_after = next(
        row
        for row in after["field_requirements"]["required_fields"]
        if row["qualified_code"] == "platform.identity.address"
    )
    assert address_after["satisfied"] is True
    assert after["field_requirements"]["missing_count"] < before["field_requirements"]["missing_count"]

    citizenship_after = next(
        row
        for row in after["field_requirements"]["required_fields"]
        if row["qualified_code"] == "platform.identity.citizenship"
    )
    years_after = next(
        row
        for row in after["field_requirements"]["required_fields"]
        if row["qualified_code"] == "recruitment.candidate.experience.years_ce"
    )
    assert citizenship_after["satisfied"] is True
    assert years_after["satisfied"] is True

    transfer = after["transfer_readiness"]
    blocking_codes = {
        str(row.get("qualified_code") or row.get("field_code") or "")
        for row in transfer.get("blocking_reasons") or []
        if isinstance(row, dict)
    }
    assert "platform.identity.address" not in blocking_codes
