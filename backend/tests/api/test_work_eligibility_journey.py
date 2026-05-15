"""GET /workforce/employees/{id}/work-eligibility/journey read-model."""

from __future__ import annotations

from typing import Dict

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_work_eligibility_journey_shape(
    client: AsyncClient,
    hr_officer_headers: Dict[str, str],
    bootstrap: Dict[str, str],
) -> None:
    h = {**hr_officer_headers, "Content-Type": "application/json"}
    create = await client.post(
        "/api/v1/workforce/employees",
        headers=h,
        json={
            "display_name": "Journey read-model",
            "status": "onboarding",
            "company_id": bootstrap["company_id"],
        },
    )
    assert create.status_code == 201, create.text
    emp_id = create.json()["id"]

    res = await client.get(
        f"/api/v1/workforce/employees/{emp_id}/work-eligibility/journey",
        headers=hr_officer_headers,
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert "steps" in body and "recommended_next_action" in body
    codes = [s["step_code"] for s in body["steps"]]
    assert codes == [
        "legal_stay",
        "work_permit_fee",
        "work_permit_application",
        "work_permit_received",
        "red_paper_fee",
        "red_paper_ordered",
        "red_paper_received",
        "zus_registration",
        "eligible_to_work",
    ]
    for s in body["steps"]:
        assert "status" in s and "label" in s
        assert isinstance(s.get("blockers"), list)
        assert isinstance(s.get("required_documents"), list)
