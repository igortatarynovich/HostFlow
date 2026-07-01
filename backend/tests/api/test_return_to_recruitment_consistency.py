"""§6.7 — return-to-recruitment: lock release, permissions, mutations, no duplicates on re-handoff."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select, text

from backend.app.db.session import async_session_maker
from backend.app.models.document import Document
from backend.app.models.workforce_employee import WorkforceEmployee
from backend.tests.api.test_handoff_internal_hr import _ensure_tenant_link_internal_hr
from backend.tests.conftest import _init_data
from backend.tests.test_support.candidate_handoff_gate import seed_documents_for_ready_for_handoff


async def _set_rls_tenant(session, tenant_id: str) -> None:
    await session.execute(
        text("SELECT set_config('app.tenant_id', :tenant_id, false)"),
        {"tenant_id": tenant_id},
    )


async def _count_active_documents(session, tenant_id: str, candidate_id: str) -> int:
    await _set_rls_tenant(session, tenant_id)
    r = await session.execute(
        select(func.count())
        .select_from(Document)
        .where(
            Document.tenant_id == tenant_id,
            Document.candidate_id == candidate_id,
            Document.deleted_at.is_(None),
        )
    )
    return int(r.scalar_one() or 0)


async def _count_employees_for_candidate(session, tenant_id: str, candidate_id: str) -> int:
    await _set_rls_tenant(session, tenant_id)
    r = await session.execute(
        select(func.count())
        .select_from(WorkforceEmployee)
        .where(
            WorkforceEmployee.tenant_id == tenant_id,
            WorkforceEmployee.candidate_id == candidate_id,
            WorkforceEmployee.status.notin_(("returned_to_recruitment", "returned", "terminated")),
        )
    )
    return int(r.scalar_one() or 0)


@pytest.mark.anyio
async def test_return_to_recruitment_releases_operational_lock_and_repeat_handoff_no_duplicates(
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
            "first_name": "RetCon",
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

    async with async_session_maker() as session:
        assert await _count_employees_for_candidate(session, tenant_id, candidate_id) == 1

    lst = await client.get("/api/v1/workforce/employees", headers=hr_officer_headers)
    assert lst.status_code == 200, lst.text
    matches = [r for r in lst.json() if str(r.get("candidate_id") or "") == str(candidate_id)]
    assert len(matches) == 1, lst.json()
    employee_id = str(matches[0]["id"])

    rec_json = {**recruiter_headers, "Content-Type": "application/json"}
    locked_detail = await client.get(f"/api/v1/candidates/{candidate_id}", headers=recruiter_headers)
    assert locked_detail.status_code == 200, locked_detail.text
    locked_body = locked_detail.json()
    assert locked_body.get("can_edit") is False
    perm = locked_body.get("permissions") or {}
    assert perm.get("operational_owner") == "hr"

    locked_patch = await client.patch(
        f"/api/v1/candidates/{candidate_id}",
        headers=rec_json,
        json={"first_name": "ShouldBeBlocked"},
    )
    assert locked_patch.status_code == 403, locked_patch.text

    ret = await client.post(
        f"/api/v1/workforce/employees/{employee_id}/hr-review/return-to-recruitment",
        headers={**hr_officer_headers, "Content-Type": "application/json"},
        json={"reason": "§6.7 regression — return releases recruitment operational lock"},
    )
    assert ret.status_code == 200, ret.text
    assert ret.json().get("status") == "returned_to_recruitment"

    async with async_session_maker() as session:
        assert await _count_employees_for_candidate(session, tenant_id, candidate_id) == 0

    open_detail = await client.get(f"/api/v1/candidates/{candidate_id}", headers=recruiter_headers)
    assert open_detail.status_code == 200, open_detail.text
    open_body = open_detail.json()
    assert open_body.get("can_edit") is True, open_body
    perm_open = open_body.get("permissions") or {}
    assert perm_open.get("operational_owner") == "recruitment"
    assert perm_open.get("readonly_reason") in (None, "")

    patch_ok = await client.patch(
        f"/api/v1/candidates/{candidate_id}",
        headers=rec_json,
        json={"first_name": "RecruiterEditsAgain"},
    )
    assert patch_ok.status_code == 200, patch_ok.text
    assert patch_ok.json().get("first_name") == "RecruiterEditsAgain"

    note = await client.post(
        f"/api/v1/candidates/{candidate_id}/notes",
        headers=rec_json,
        json={"text": "after return", "visibility": "internal"},
    )
    assert note.status_code == 201, note.text

    task = await client.post(
        "/api/v1/activities",
        headers=rec_json,
        json={
            "title": "post-return task",
            "entity_type": "candidate",
            "entity_id": candidate_id,
            "due_at": "2026-05-09T12:00:00Z",
            "type": "custom",
        },
    )
    assert task.status_code == 201, task.text

    permit = await client.post(
        f"/api/v1/candidates/{candidate_id}/permits",
        headers=rec_json,
        json={"permit_type": "regression_permit", "status": "active"},
    )
    assert permit.status_code == 201, permit.text

    db_doc = await client.post(
        f"/api/v1/db/candidate/{candidate_id}/documents",
        headers=rec_json,
        json={"doc_type": "driver_license", "status": "requested"},
    )
    assert db_doc.status_code == 201, db_doc.text

    async with async_session_maker() as session:
        n_docs = await _count_active_documents(session, tenant_id, candidate_id)

    patch_ready = await client.patch(
        f"/api/v1/candidates/{candidate_id}",
        headers=rec_json,
        json={"stage": "ready_for_handoff"},
    )
    assert patch_ready.status_code == 200, patch_ready.text

    ho2 = await client.post(
        f"/api/v1/handoffs/candidates/{candidate_id}",
        headers=rec_json,
        json={"client_company_id": company_id, "destination": "internal_hr"},
    )
    assert ho2.status_code == 201, ho2.text
    handoff2_id = ho2.json()["id"]

    acc2 = await client.post(
        f"/api/v1/handoffs/{handoff2_id}/accept",
        headers=hr_officer_headers,
    )
    assert acc2.status_code == 200, acc2.text

    wf2 = await client.post(
        f"/api/v1/workforce/employees/from-candidate/{candidate_id}",
        headers=rec_json,
        json={},
    )
    assert wf2.status_code in (200, 201), wf2.text
    employee2_id = wf2.json()["id"]
    assert employee2_id, wf2.text

    async with async_session_maker() as session:
        assert await _count_employees_for_candidate(session, tenant_id, candidate_id) == 1
        assert await _count_active_documents(session, tenant_id, candidate_id) == n_docs
