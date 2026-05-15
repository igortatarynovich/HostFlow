"""PR-2: PATCH tax / insurance / compliance legal profiles (HR workspace)."""

from __future__ import annotations

from typing import Dict

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_patch_tax_insurance_compliance_profiles(
    client: AsyncClient,
    hr_officer_headers: Dict[str, str],
    bootstrap: Dict[str, str],
) -> None:
    h = {**hr_officer_headers, "Content-Type": "application/json"}
    create = await client.post(
        "/api/v1/workforce/employees",
        headers=h,
        json={
            "display_name": "Legal profiles patch",
            "status": "onboarding",
            "company_id": bootstrap["company_id"],
        },
    )
    assert create.status_code == 201, create.text
    emp_id = create.json()["id"]

    tax = await client.patch(
        f"/api/v1/workforce/employees/{emp_id}/tax-profile",
        headers=h,
        json={"tax_residency_country": "PL", "pit2_submitted": True},
    )
    assert tax.status_code == 200, tax.text
    body = tax.json()
    assert body["employee_id"] == emp_id
    assert body.get("tax_residency_country") == "PL"
    assert body.get("pit2_submitted") is True

    ins = await client.patch(
        f"/api/v1/workforce/employees/{emp_id}/insurance-profile",
        headers=h,
        json={"status": "registered", "zus_title_code": "01"},
    )
    assert ins.status_code == 200, ins.text
    assert ins.json().get("status") == "registered"
    assert ins.json().get("zus_title_code") == "01"

    comp = await client.patch(
        f"/api/v1/workforce/employees/{emp_id}/compliance-state",
        headers=h,
        json={"status": "ok", "missing_count": 0, "cannot_work": False},
    )
    assert comp.status_code == 200, comp.text
    assert comp.json().get("status") == "ok"
    assert comp.json().get("cannot_work") is False
