"""HR operational context: WorkforceHrCase, DocumentEntityLink, HR-only DocumentCheck (no status clobber)."""

from __future__ import annotations

from typing import Dict, List

import pytest
from httpx import AsyncClient

from backend.tests.api.test_handoff_internal_hr import (
    _ensure_tenant_link_internal_hr,
    internal_hr_handoff_create_and_accept,
)
from backend.tests.test_support.candidate_handoff_gate import seed_documents_for_ready_for_handoff


def _checks_sorted_asc(checks: List[dict]) -> List[dict]:
    return sorted(checks, key=lambda c: c.get("created_at") or "")


@pytest.mark.asyncio
async def test_hr_operational_context_case_links_and_hr_review_does_not_replace_recruitment_check(
    client: AsyncClient,
    recruiter_headers: Dict[str, str],
    hr_officer_headers: Dict[str, str],
    manager_headers: Dict[str, str],
    candidate_id: str,
    bootstrap: Dict[str, str],
) -> None:
    tenant_id = bootstrap["tenant_id"]
    company_id = bootstrap["company_id"]
    await _ensure_tenant_link_internal_hr(
        client, manager_headers=manager_headers, tenant_id=tenant_id, company_id=company_id
    )
    await seed_documents_for_ready_for_handoff(client, manager_headers, candidate_id)
    rec_json = {**recruiter_headers, "Content-Type": "application/json"}
    hr_json = {**hr_officer_headers, "Content-Type": "application/json"}

    doc_resp = await client.post(
        f"/api/v1/candidates/{candidate_id}/documents",
        headers=rec_json,
        json={"doc_type": "driver_license", "status": "uploaded"},
    )
    assert doc_resp.status_code == 201, doc_resp.text
    doc_id = doc_resp.json()["id"]

    rec_check = await client.post(
        f"/api/v1/db/documents/{doc_id}/check",
        headers=rec_json,
        json={
            "decision": "approved",
            "payload": {"review_module": "recruitment"},
        },
    )
    assert rec_check.status_code == 200, rec_check.text
    assert rec_check.json().get("status") in ("approved", "Approved")

    await internal_hr_handoff_create_and_accept(
        client,
        recruiter_headers=recruiter_headers,
        hr_officer_headers=hr_officer_headers,
        candidate_id=candidate_id,
        company_id=company_id,
    )

    lst = await client.get("/api/v1/workforce/employees", headers=hr_officer_headers)
    assert lst.status_code == 200, lst.text
    matches = [e for e in lst.json() if str(e.get("candidate_id") or "") == str(candidate_id)]
    assert len(matches) == 1
    emp_id = matches[0]["id"]

    ctx = await client.get(
        f"/api/v1/workforce/employees/{emp_id}/hr-operational-context",
        headers=hr_officer_headers,
    )
    assert ctx.status_code == 200, ctx.text
    body = ctx.json()
    assert body.get("hr_case") is not None
    assert body["hr_case"]["employee_id"] == emp_id
    assert str(body["hr_case"].get("source_candidate_id") or "") == str(candidate_id)
    links = body.get("document_links") or []
    assert len(links) >= 1
    assert any(l.get("document_id") == doc_id and l.get("relation_type") == "reused_for_hr" for l in links)

    hr_rev = await client.post(
        f"/api/v1/workforce/employees/{emp_id}/documents/{doc_id}/hr-review",
        headers={**hr_json, "Content-Type": "application/json"},
        json={"decision": "rejected", "comment": "hr lane sample"},
    )
    assert hr_rev.status_code == 200, hr_rev.text
    assert hr_rev.json().get("decision") == "rejected"

    doc_after = await client.get(
        f"/api/v1/db/documents/{doc_id}",
        headers=hr_officer_headers,
    )
    assert doc_after.status_code == 200, doc_after.text
    assert str(doc_after.json().get("status") or "").lower() == "approved"

    checks_resp = await client.get(
        f"/api/v1/db/documents/{doc_id}/checks",
        headers=hr_officer_headers,
    )
    assert checks_resp.status_code == 200, checks_resp.text
    checks = checks_resp.json()
    assert len(checks) >= 2
    ordered = _checks_sorted_asc(checks)
    payloads = [((c.get("payload") or {}) if isinstance(c.get("payload"), dict) else {}) for c in ordered]
    modules = [p.get("review_module") for p in payloads]
    assert "recruitment" in modules
    assert "hr" in modules
    rec_entry = next(c for c in ordered if (c.get("payload") or {}).get("review_module") == "recruitment")
    assert rec_entry.get("decision") == "approved"


@pytest.mark.asyncio
async def test_hr_review_forbidden_for_recruiter_and_supervisor(
    client: AsyncClient,
    recruiter_headers: Dict[str, str],
    supervisor_headers: Dict[str, str],
    hr_officer_headers: Dict[str, str],
    manager_headers: Dict[str, str],
    candidate_id: str,
    bootstrap: Dict[str, str],
) -> None:
    """HR-only review endpoint: hr_officer/administrator only (not recruiter/supervisor)."""
    tenant_id = bootstrap["tenant_id"]
    company_id = bootstrap["company_id"]
    await _ensure_tenant_link_internal_hr(
        client, manager_headers=manager_headers, tenant_id=tenant_id, company_id=company_id
    )
    await seed_documents_for_ready_for_handoff(client, manager_headers, candidate_id)
    rec_json = {**recruiter_headers, "Content-Type": "application/json"}

    doc_resp = await client.post(
        f"/api/v1/candidates/{candidate_id}/documents",
        headers=rec_json,
        json={"doc_type": "id_card", "status": "uploaded"},
    )
    assert doc_resp.status_code == 201, doc_resp.text
    doc_id = doc_resp.json()["id"]

    await internal_hr_handoff_create_and_accept(
        client,
        recruiter_headers=recruiter_headers,
        hr_officer_headers=hr_officer_headers,
        candidate_id=candidate_id,
        company_id=company_id,
    )

    lst = await client.get("/api/v1/workforce/employees", headers=recruiter_headers)
    assert lst.status_code == 200, lst.text
    matches = [e for e in lst.json() if str(e.get("candidate_id") or "") == str(candidate_id)]
    assert len(matches) == 1
    emp_id = matches[0]["id"]

    for headers, label in (
        (recruiter_headers, "recruiter"),
        (supervisor_headers, "supervisor"),
    ):
        resp = await client.post(
            f"/api/v1/workforce/employees/{emp_id}/documents/{doc_id}/hr-review",
            headers={**headers, "Content-Type": "application/json"},
            json={"decision": "approved"},
        )
        assert resp.status_code == 403, f"{label}: {resp.status_code} {resp.text}"

    ok = await client.post(
        f"/api/v1/workforce/employees/{emp_id}/documents/{doc_id}/hr-review",
        headers={**hr_officer_headers, "Content-Type": "application/json"},
        json={"decision": "approved", "comment": "hr ok"},
    )
    assert ok.status_code == 200, ok.text
