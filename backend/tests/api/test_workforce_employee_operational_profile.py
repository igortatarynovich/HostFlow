"""HR employee operational profile read-model (GET /workforce/employees/{id}/operational-profile)."""

from __future__ import annotations

from typing import Any, Dict

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_operational_profile_hr_officer_shape(
    client: AsyncClient,
    hr_officer_headers: Dict[str, str],
    bootstrap: Dict[str, str],
) -> None:
    h = {**hr_officer_headers, "Content-Type": "application/json"}
    create = await client.post(
        "/api/v1/workforce/employees",
        headers=h,
        json={
            "display_name": "Operational profile test",
            "status": "onboarding",
            "company_id": bootstrap["company_id"],
        },
    )
    assert create.status_code == 201, create.text
    emp_id = create.json()["id"]

    resp = await client.get(
        f"/api/v1/workforce/employees/{emp_id}/operational-profile",
        headers=hr_officer_headers,
    )
    assert resp.status_code == 200, resp.text
    body: Dict[str, Any] = resp.json()
    for k in (
        "employee",
        "operational_summary",
        "transfer",
        "recruiter_summary",
        "documents_linked",
        "documents_missing",
        "documents_expiring",
        "risks",
        "alerts",
        "onboarding_overdue_count",
        "timeline",
        "employment_operational",
        "hr_bundle",
    ):
        assert k in body, body
    assert body["employee"]["id"] == emp_id
    osum = body["operational_summary"]
    assert "employee_status" in osum and "compliance_status" in osum
    assert isinstance(body["documents_linked"], list)
    assert isinstance(body["hr_bundle"]["onboarding_tasks"], list)
    hb = body["hr_bundle"]
    assert isinstance(hb.get("work_eligibility_payment_requirements"), list)
    assert hb.get("tax_profile") is not None
    assert hb.get("insurance_profile") is not None
    assert hb.get("compliance_state") is not None
    summ = hb.get("hr_document_context_summary") or {}
    assert "total" in summ and "items" in summ and "by_context_type" in summ


@pytest.mark.asyncio
async def test_operational_profile_recruiter_forbidden(
    client: AsyncClient, recruiter_headers: Dict[str, str]
) -> None:
    resp = await client.get(
        "/api/v1/workforce/employees/does-not-matter/operational-profile",
        headers=recruiter_headers,
    )
    assert resp.status_code == 403, resp.text
