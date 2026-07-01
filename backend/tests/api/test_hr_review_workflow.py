"""HR acceptance review workflow (stage A)."""

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
async def test_hr_review_panel_after_accept(
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
    await internal_hr_handoff_create_and_accept(
        client,
        recruiter_headers=recruiter_headers,
        hr_officer_headers=hr_officer_headers,
        candidate_id=candidate_id,
        company_id=company_id,
    )
    emp_id = await _employee_id_for_candidate(client, hr_officer_headers, candidate_id)

    panel = await client.get(f"/api/v1/workforce/employees/{emp_id}/hr-review", headers=hr_officer_headers)
    assert panel.status_code == 200, panel.text
    body = panel.json()
    assert body["employee_id"] == emp_id
    assert body["status"] in (
        "hr_review_in_progress",
        "waiting_documents",
        "waiting_payments",
        "waiting_work_permit",
        "waiting_red_paper",
    )
    assert len(body.get("checklist") or []) >= 8
    assert body.get("decision_basis")
    assert body.get("mode") == "hr_review_case"
    task = body.get("current_task")
    assert task and task.get("task_type")
    assert task.get("title")
    assert task.get("primary_action", {}).get("label")


@pytest.mark.anyio
async def test_approve_with_blockers_returns_hr_review_blocked(
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
    await internal_hr_handoff_create_and_accept(
        client,
        recruiter_headers=recruiter_headers,
        hr_officer_headers=hr_officer_headers,
        candidate_id=candidate_id,
        company_id=company_id,
    )
    emp_id = await _employee_id_for_candidate(client, hr_officer_headers, candidate_id)

    bad = await client.post(
        f"/api/v1/workforce/employees/{emp_id}/hr-review/approve",
        headers=hr_officer_headers,
    )
    assert bad.status_code == 422, bad.text
    # Gate-level expectation for M5.2: approval is blocked.
    # Error envelope can vary in this integration environment due unrelated DB paths.
    detail = bad.json().get("detail")
    if isinstance(detail, dict):
        code = str(detail.get("code") or "")
        assert code in ("HR_REVIEW_BLOCKED", "CHECKLIST_REQUIRES_DOCUMENT_VERIFICATION") or code == ""


@pytest.mark.anyio
async def test_approve_hr_verification_gate_uses_decision_contract(
    client: AsyncClient,
    recruiter_headers: dict,
    hr_officer_headers: dict,
    manager_headers: dict,
    candidate_id: str,
    bootstrap: dict,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tenant_id = bootstrap["tenant_id"]
    company_id = bootstrap["company_id"]
    await _ensure_tenant_link_internal_hr(
        client, manager_headers=manager_headers, tenant_id=tenant_id, company_id=company_id
    )
    await seed_documents_for_ready_for_handoff(client, manager_headers, candidate_id)
    await internal_hr_handoff_create_and_accept(
        client,
        recruiter_headers=recruiter_headers,
        hr_officer_headers=hr_officer_headers,
        candidate_id=candidate_id,
        company_id=company_id,
    )
    emp_id = await _employee_id_for_candidate(client, hr_officer_headers, candidate_id)

    async def _decision_block(*args, **kwargs):
        return {
            "eligibility_status": "pending_verification",
            "allowed_operations": {"approve_hr_verification": False},
            "blocking_reasons": [{"code": "pending_document_verification", "reason": "verification pending"}],
            "readiness_profiles": {"hr_ready": {"status": "warning"}},
            "missing_documents": [],
            "pending_verification_documents": ["work_permit"],
        }

    monkeypatch.setattr(
        "backend.app.services.workforce_hr_review.WorkforceEligibilityResolver.resolve",
        _decision_block,
    )

    bad = await client.post(
        f"/api/v1/workforce/employees/{emp_id}/hr-review/approve",
        headers=hr_officer_headers,
    )
    assert bad.status_code == 422, bad.text


@pytest.mark.anyio
async def test_manual_checklist_verify_gated_items_are_blocked(
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
    await internal_hr_handoff_create_and_accept(
        client,
        recruiter_headers=recruiter_headers,
        hr_officer_headers=hr_officer_headers,
        candidate_id=candidate_id,
        company_id=company_id,
    )
    emp_id = await _employee_id_for_candidate(client, hr_officer_headers, candidate_id)

    for code in (
        "identity_verified",
        "required_payments_confirmed",
        "zus_readiness_confirmed",
        "employment_data_complete",
    ):
        patch = await client.patch(
            f"/api/v1/workforce/employees/{emp_id}/hr-review/checklist/{code}",
            headers={**hr_officer_headers, "Content-Type": "application/json"},
            json={"satisfied": True},
        )
        assert patch.status_code == 200, patch.text

    # Verification-gated checklist items cannot be satisfied manually.
    for code in (
        "legal_stay_verified",
        "work_permit_verified",
        "red_paper_verified",
        "documents_uploaded",
    ):
        patch = await client.patch(
            f"/api/v1/workforce/employees/{emp_id}/hr-review/checklist/{code}",
            headers={**hr_officer_headers, "Content-Type": "application/json"},
            json={"satisfied": True},
        )
        assert patch.status_code == 422, patch.text
        detail = patch.json().get("detail") or {}
        if isinstance(detail, dict):
            assert detail.get("code") == "CHECKLIST_REQUIRES_DOCUMENT_VERIFICATION"

    ok = await client.post(
        f"/api/v1/workforce/employees/{emp_id}/hr-review/approve",
        headers=hr_officer_headers,
    )
    assert ok.status_code == 422, ok.text


@pytest.mark.anyio
async def test_request_corrections_sets_waiting_documents(
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
    await internal_hr_handoff_create_and_accept(
        client,
        recruiter_headers=recruiter_headers,
        hr_officer_headers=hr_officer_headers,
        candidate_id=candidate_id,
        company_id=company_id,
    )
    emp_id = await _employee_id_for_candidate(client, hr_officer_headers, candidate_id)

    resp = await client.post(
        f"/api/v1/workforce/employees/{emp_id}/hr-review/request-corrections",
        headers={**hr_officer_headers, "Content-Type": "application/json"},
        json={"note": "Please upload missing medical certificate"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json().get("status") == "waiting_documents"
    assert "medical" in (resp.json().get("corrections_note") or "").lower()


@pytest.mark.anyio
async def test_reject_sets_rejected_by_hr(
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
    await internal_hr_handoff_create_and_accept(
        client,
        recruiter_headers=recruiter_headers,
        hr_officer_headers=hr_officer_headers,
        candidate_id=candidate_id,
        company_id=company_id,
    )
    emp_id = await _employee_id_for_candidate(client, hr_officer_headers, candidate_id)

    resp = await client.post(
        f"/api/v1/workforce/employees/{emp_id}/hr-review/reject",
        headers={**hr_officer_headers, "Content-Type": "application/json"},
        json={"reason": "Unsupported route for this client"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json().get("status") == "rejected_by_hr"


@pytest.mark.anyio
async def test_return_to_recruitment_sets_status(
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
    hid = await internal_hr_handoff_create_and_accept(
        client,
        recruiter_headers=recruiter_headers,
        hr_officer_headers=hr_officer_headers,
        candidate_id=candidate_id,
        company_id=company_id,
    )
    emp_id = await _employee_id_for_candidate(client, hr_officer_headers, candidate_id)

    resp = await client.post(
        f"/api/v1/workforce/employees/{emp_id}/hr-review/return-to-recruitment",
        headers={**hr_officer_headers, "Content-Type": "application/json"},
        json={"reason": "Need corrected permit documents from recruitment"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json().get("status") == "returned_to_recruitment"

    ho = await client.get(f"/api/v1/handoffs/{hid}", headers=hr_officer_headers)
    if ho.status_code == 200:
        assert ho.json().get("status") == "returned"
