"""API: HR review panel exposes candidate documents and blocks approve until verified."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from backend.tests.api.test_handoff_internal_hr import (
    _ensure_tenant_link_internal_hr,
    internal_hr_handoff_create_and_accept,
)
from backend.tests.test_support.candidate_handoff_gate import seed_documents_for_ready_for_handoff


async def _employee_id_for_candidate(client: AsyncClient, hr_headers: dict, candidate_id: str) -> str:
    lst = await client.get("/api/v1/workforce/employees", headers=hr_headers)
    assert lst.status_code == 200, lst.text
    matches = [e for e in lst.json() if str(e.get("candidate_id") or "") == str(candidate_id)]
    assert len(matches) == 1
    return str(matches[0]["id"])


@pytest.mark.anyio
async def test_hr_review_panel_links_candidate_passport_and_blocks_approve(
    client: AsyncClient,
    recruiter_headers: dict,
    hr_officer_headers: dict,
    manager_headers: dict,
    candidate_id: str,
    bootstrap: dict,
) -> None:
    tenant_id = bootstrap["tenant_id"]
    company_id = bootstrap["company_id"]
    await _ensure_tenant_link_internal_hr(
        client, manager_headers=manager_headers, tenant_id=tenant_id, company_id=company_id
    )
    await seed_documents_for_ready_for_handoff(client, manager_headers, candidate_id)

    patch_cand = await client.patch(
        f"/api/v1/candidates/{candidate_id}",
        headers=manager_headers,
        json={"extra": {"citizenship": "UA"}},
    )
    assert patch_cand.status_code == 200, patch_cand.text

    await internal_hr_handoff_create_and_accept(
        client,
        recruiter_headers=recruiter_headers,
        hr_officer_headers=hr_officer_headers,
        candidate_id=candidate_id,
        company_id=company_id,
    )
    emp_id = await _employee_id_for_candidate(client, hr_officer_headers, candidate_id)

    panel = await client.get(
        f"/api/v1/workforce/employees/{emp_id}/hr-review",
        headers=hr_officer_headers,
    )
    assert panel.status_code == 200, panel.text
    body = panel.json()
    assert body.get("can_approve") is False
    readiness = body.get("decision_readiness") or {}
    assert readiness.get("can_approve") is False

    plan = body.get("verification_plan") or {}
    assert plan.get("can_complete_verification") is False
    order = plan.get("verification_order") or []
    step_codes = [s.get("step_code") for s in order]
    assert "legal_identity" in step_codes
    hard_keys = [d.get("document_key") for d in plan.get("hard_blocker_documents") or []]
    assert "Passport / ID" in hard_keys
    assert plan.get("plan_mode") == "hybrid"
    not_req = plan.get("not_required_document_keys") or []
    assert "Driver license" in not_req

    docs = body.get("documents_for_approval") or []
    passport = next((d for d in docs if d.get("document_key") == "Passport / ID"), None)
    assert passport is not None, docs
    assert passport.get("document_id"), passport
    assert passport.get("open_url") or passport.get("file_url"), passport

    fields = passport.get("fields_to_review") or []
    cit = next((f for f in fields if f.get("field_code") == "citizenship"), None)
    assert cit is not None
    vals = cit.get("current_profile_values") or {}
    assert any("UA" in str(v) for v in vals.values()), vals

    bad = await client.post(
        f"/api/v1/workforce/employees/{emp_id}/hr-review/approve",
        headers=hr_officer_headers,
    )
    assert bad.status_code == 422, bad.text
    detail = bad.json().get("detail")
    if isinstance(detail, dict):
        assert detail.get("code") == "HR_REVIEW_BLOCKED"
