"""Return internal HR handoff to recruitment from workforce employee record."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

from backend.tests.api.test_handoff_internal_hr import _ensure_tenant_link_internal_hr
from backend.tests.conftest import _init_data
from backend.tests.test_support.candidate_handoff_gate import seed_documents_for_ready_for_handoff


@pytest.mark.anyio
async def test_return_to_recruitment_from_employee_record(
    client: AsyncClient,
    manager_headers: dict[str, str],
    recruiter_headers: dict[str, str],
    hr_officer_headers: dict[str, str],
) -> None:
    data = await _init_data()
    tenant_id = data["tenant_id"]
    company_id = data["company_id"]
    await _ensure_tenant_link_internal_hr(
        client, manager_headers=manager_headers, tenant_id=tenant_id, company_id=company_id
    )

    tag = uuid.uuid4().hex[:8]
    create_resp = await client.post(
        "/api/v1/candidates",
        headers=manager_headers,
        json={
            "first_name": "WFRet",
            "last_name": f"T{tag}",
            "company_id": company_id,
        },
    )
    assert create_resp.status_code == 200, create_resp.text
    candidate_id = create_resp.json()["id"]

    await seed_documents_for_ready_for_handoff(client, manager_headers, candidate_id)

    patch_stage = await client.patch(
        f"/api/v1/candidates/{candidate_id}",
        headers=manager_headers,
        json={"stage": "ready_for_handoff"},
    )
    assert patch_stage.status_code == 200, patch_stage.text

    ho = await client.post(
        f"/api/v1/handoffs/candidates/{candidate_id}",
        headers={**recruiter_headers, "Content-Type": "application/json"},
        json={"client_company_id": company_id, "destination": "internal_hr"},
    )
    assert ho.status_code == 201, ho.text
    handoff_id = ho.json()["id"]

    acc = await client.post(
        f"/api/v1/handoffs/{handoff_id}/accept",
        headers=hr_officer_headers,
    )
    assert acc.status_code == 200, acc.text

    wf = await client.post(
        f"/api/v1/workforce/employees/from-candidate/{candidate_id}",
        headers={**recruiter_headers, "Content-Type": "application/json"},
        json={},
    )
    assert wf.status_code in (200, 201), wf.text
    employee_id = wf.json()["id"]

    elig = await client.get(
        f"/api/v1/workforce/employees/{employee_id}/return-to-recruitment/eligibility",
        headers=hr_officer_headers,
    )
    assert elig.status_code == 200, elig.text
    body = elig.json()
    assert body["can_return"] is True
    assert body["handoff_id"] == handoff_id
    assert body["candidate_id"] == candidate_id

    ret = await client.post(
        f"/api/v1/workforce/employees/{employee_id}/return-to-recruitment",
        headers={**hr_officer_headers, "Content-Type": "application/json"},
        json={"return_reason": "Missing documents — send back to recruitment"},
    )
    assert ret.status_code == 200, ret.text
    assert ret.json()["status"] == "returned"

    cand = await client.get(
        f"/api/v1/candidates/{candidate_id}",
        headers=recruiter_headers,
    )
    assert cand.status_code == 200, cand.text
    assert cand.json().get("stage") == "handoff_returned"

    # Employee row is deleted on return; eligibility by old id is 404 (not a stale 200).
    elig_gone = await client.get(
        f"/api/v1/workforce/employees/{employee_id}/return-to-recruitment/eligibility",
        headers=hr_officer_headers,
    )
    assert elig_gone.status_code == 404, elig_gone.text

    rec_json = {**recruiter_headers, "Content-Type": "application/json"}
    patch_after_return = await client.patch(
        f"/api/v1/candidates/{candidate_id}",
        headers=rec_json,
        json={
            "first_name": "BackInRecruitment",
            "override_reason": "Returned from HR — recruitment may correct dossier",
        },
    )
    assert patch_after_return.status_code == 200, patch_after_return.text
    assert patch_after_return.json().get("first_name") == "BackInRecruitment"
