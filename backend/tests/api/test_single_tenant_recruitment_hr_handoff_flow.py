"""Single-tenant contour: internal HR handoff + accept → WorkforceEmployee; documents reused (no copy).

Covers roadmap DOD (docs/specs/workflows/implementation-roadmap-single-tenant-hr-handoff.md §1).
PR-5: workforce materialization is not driven by candidate stage alone.
"""

from __future__ import annotations

import json
import re
from typing import Dict

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select, text

from backend.app.db.session import async_session_maker
from backend.app.models.audit import ActivityLog
from backend.app.models.document import Document
from backend.app.models.workforce_employee import WorkforceEmployee
from backend.tests.api.test_handoff_internal_hr import (
    _ensure_tenant_link_internal_hr,
    internal_hr_handoff_create_and_accept,
)
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
    """Active workforce rows linked to candidate (excludes returned-to-recruitment)."""
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


def _employee_id_for_candidate(rows: list, candidate_id: str) -> str:
    matches = [e for e in rows if str(e.get("candidate_id") or "") == str(candidate_id)]
    assert len(matches) == 1, f"expected one workforce row for candidate, got {len(matches)}"
    return str(matches[0]["id"])


@pytest.mark.asyncio
async def test_internal_hr_accept_handoff_workforce_idempotent_hr_reads_same_document(
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
    rec_json = {**recruiter_headers, "Content-Type": "application/json"}
    hr_json = {**hr_officer_headers, "Content-Type": "application/json"}
    enrich = await client.patch(
        f"/api/v1/candidates/{candidate_id}",
        headers=rec_json,
        json={
            "note": "handoff note from recruitment",
            "personal_data": {
                "citizenship": "UA",
                "work_country": "PL",
                "passport_number": "PP-123456",
            },
            "extra": {
                "citizenship": "UA",
                "work_country": "PL",
                "position_category": "driver",
                "legal_status": "temporary_residence",
                "license_number": "DL-998877",
                "code95_number": "C95-111",
                "recruiter_notes": "priority candidate",
                "handoff_notes": "docs complete",
            },
        },
    )
    assert enrich.status_code == 200, enrich.text

    doc_resp = await client.post(
        f"/api/v1/candidates/{candidate_id}/documents",
        headers=rec_json,
        json={"doc_type": "driver_license", "status": "uploaded"},
    )
    assert doc_resp.status_code == 201, doc_resp.text
    doc_id = doc_resp.json()["id"]

    await seed_documents_for_ready_for_handoff(client, manager_headers, candidate_id)

    async with async_session_maker() as session:
        n_docs_before = await _count_active_documents(session, tenant_id, candidate_id)
    assert n_docs_before >= 1

    await internal_hr_handoff_create_and_accept(
        client,
        recruiter_headers=recruiter_headers,
        hr_officer_headers=hr_officer_headers,
        candidate_id=candidate_id,
        company_id=company_id,
    )

    cand = await client.get(f"/api/v1/candidates/{candidate_id}", headers=rec_json)
    assert cand.status_code == 200, cand.text
    assert str(cand.json().get("stage") or "").lower() == "processing_by_hr"

    async with async_session_maker() as session:
        assert await _count_employees_for_candidate(session, tenant_id, candidate_id) == 1
        assert await _count_active_documents(session, tenant_id, candidate_id) == n_docs_before

    lst = await client.get("/api/v1/workforce/employees", headers=hr_officer_headers)
    assert lst.status_code == 200, lst.text
    emp_id = _employee_id_for_candidate(lst.json(), candidate_id)

    hr_docs = await client.get(
        f"/api/v1/workforce/employees/{emp_id}/documents",
        headers=hr_officer_headers,
    )
    assert hr_docs.status_code == 200, hr_docs.text
    hr_body = hr_docs.json()
    hr_doc_ids = {d["id"] for d in hr_body}
    assert doc_id in hr_doc_ids
    hr_dump = json.dumps(hr_body)
    assert not re.search(
        r"/api/v1/candidates/[^/\"]+/documents/[^/\"]+/file",
        hr_dump,
    ), hr_dump
    for row in hr_body:
        fid = row.get("id")
        assert row.get("document_open_context") == "hr_workforce_employee"
        url = row.get("open_url") or row.get("file_url")
        assert url == f"/api/v1/workforce/employees/{emp_id}/documents/{fid}/file"

    op = await client.get(
        f"/api/v1/workforce/employees/{emp_id}/operational-profile",
        headers=hr_officer_headers,
    )
    assert op.status_code == 200, op.text
    rs = (op.json().get("recruiter_summary") or {})
    assert rs.get("citizenship") == "UA"
    assert rs.get("work_country") == "PL"
    assert rs.get("position_category") == "driver"
    assert rs.get("legal_status") == "temporary_residence"
    assert (rs.get("document_field_values") or {}).get("license_number") == "DL-998877"
    assert (rs.get("notes") or {}).get("handoff_notes") == "docs complete"
    assert (rs.get("personal_data") or {}).get("passport_number") == "PP-123456"

    patch_hired = await client.patch(
        f"/api/v1/candidates/{candidate_id}",
        headers=hr_json,
        json={"stage": "hired"},
    )
    assert patch_hired.status_code == 200, patch_hired.text

    async with async_session_maker() as session:
        assert await _count_employees_for_candidate(session, tenant_id, candidate_id) == 1
        assert await _count_active_documents(session, tenant_id, candidate_id) == n_docs_before

    lst2 = await client.get("/api/v1/workforce/employees", headers=hr_officer_headers)
    assert lst2.status_code == 200, lst2.text
    emp_id_2 = _employee_id_for_candidate(lst2.json(), candidate_id)
    assert emp_id_2 == emp_id


@pytest.mark.asyncio
async def test_hr_review_dossier_plan_includes_data_blocks_and_by_candidate_lookup(
    client: AsyncClient,
    recruiter_headers: Dict[str, str],
    hr_officer_headers: Dict[str, str],
    manager_headers: Dict[str, str],
    candidate_id: str,
    bootstrap: Dict[str, str],
) -> None:
    """P0: HR dossier plan exposes data blocks; residence_card maps to Legal stay; by-candidate API works."""
    company_id = bootstrap["company_id"]
    await _ensure_tenant_link_internal_hr(
        client, manager_headers=manager_headers, tenant_id=bootstrap["tenant_id"], company_id=company_id
    )
    rec_json = {**recruiter_headers, "Content-Type": "application/json"}
    hr_json = {**hr_officer_headers, "Content-Type": "application/json"}

    await client.post(
        f"/api/v1/candidates/{candidate_id}/documents",
        headers=rec_json,
        json={"doc_type": "residence_card", "status": "uploaded"},
    )
    await seed_documents_for_ready_for_handoff(client, manager_headers, candidate_id)

    await internal_hr_handoff_create_and_accept(
        client,
        recruiter_headers=recruiter_headers,
        hr_officer_headers=hr_officer_headers,
        candidate_id=candidate_id,
        company_id=company_id,
    )

    by_cand = await client.get(
        f"/api/v1/workforce/employees/by-candidate/{candidate_id}",
        headers=hr_json,
    )
    assert by_cand.status_code == 200, by_cand.text
    emp_id = by_cand.json()["id"]

    review = await client.get(
        f"/api/v1/workforce/employees/{emp_id}/hr-review",
        headers=hr_json,
    )
    assert review.status_code == 200, review.text
    panel = review.json()
    plan = panel.get("verification_plan") or {}
    slots = plan.get("slots") or panel.get("documents_for_approval") or []
    keys = {str(s.get("document_key") or s.get("label") or "") for s in slots if isinstance(s, dict)}
    if not keys:
        keys = {str(d.get("document_key") or "") for d in panel.get("documents_for_approval") or []}
    assert "Contacts & address" in keys or any("Contacts" in k for k in keys)
    assert "Work experience" in keys or any("experience" in k.lower() for k in keys)

    legal_rows = [
        d for d in (panel.get("documents_for_approval") or [])
        if str(d.get("document_key") or "") == "Legal stay"
    ]
    if legal_rows:
        assert legal_rows[0].get("document_id"), "residence_card should resolve into Legal stay slot"


@pytest.mark.asyncio
async def test_recruiter_cannot_patch_candidate_after_workforce_materialization(
    client: AsyncClient,
    recruiter_headers: Dict[str, str],
    hr_officer_headers: Dict[str, str],
    manager_headers: Dict[str, str],
    candidate_id: str,
    bootstrap: Dict[str, str],
) -> None:
    """After internal HR accept, recruitment must not edit handed-off dossier (recruiter 403; admin OK)."""
    tenant_id = bootstrap["tenant_id"]
    company_id = bootstrap["company_id"]
    await _ensure_tenant_link_internal_hr(
        client, manager_headers=manager_headers, tenant_id=tenant_id, company_id=company_id
    )
    rec_json = {**recruiter_headers, "Content-Type": "application/json"}
    mgr_json = {**manager_headers, "Content-Type": "application/json"}

    await seed_documents_for_ready_for_handoff(client, manager_headers, candidate_id)

    await internal_hr_handoff_create_and_accept(
        client,
        recruiter_headers=recruiter_headers,
        hr_officer_headers=hr_officer_headers,
        candidate_id=candidate_id,
        company_id=company_id,
    )

    async with async_session_maker() as session:
        assert await _count_employees_for_candidate(session, tenant_id, candidate_id) == 1

    locked = await client.patch(
        f"/api/v1/candidates/{candidate_id}",
        headers=rec_json,
        json={"first_name": "RecruiterShouldNotWrite"},
    )
    assert locked.status_code == 403, locked.text

    admin_ok = await client.patch(
        f"/api/v1/candidates/{candidate_id}",
        headers=mgr_json,
        json={
            "first_name": "AdminOverrideOk",
            "override_reason": "Regression test — admin correction while workforce row exists",
        },
    )
    assert admin_ok.status_code == 200, admin_ok.text
    assert admin_ok.json().get("first_name") == "AdminOverrideOk"

    async with async_session_maker() as session:
        await _set_rls_tenant(session, tenant_id)
        log_row = (
            await session.execute(
                select(ActivityLog)
                .where(
                    ActivityLog.tenant_id == tenant_id,
                    ActivityLog.target_id == candidate_id,
                    ActivityLog.action == "recruitment_lock_write_override",
                )
                .order_by(ActivityLog.created_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        assert log_row is not None
        pl = log_row.payload or {}
        assert pl.get("operation") == "candidate_patch"
        assert pl.get("override_reason")
        assert pl.get("lock_reason") in ("application_handed_off", "active_handoff")
        assert "first_name" in (pl.get("updated_fields") or [])


@pytest.mark.asyncio
async def test_recruiter_cannot_post_notes_after_workforce_materialization(
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
    rec_json = {**recruiter_headers, "Content-Type": "application/json"}
    await seed_documents_for_ready_for_handoff(client, manager_headers, candidate_id)

    await internal_hr_handoff_create_and_accept(
        client,
        recruiter_headers=recruiter_headers,
        hr_officer_headers=hr_officer_headers,
        candidate_id=candidate_id,
        company_id=company_id,
    )

    async with async_session_maker() as session:
        assert await _count_employees_for_candidate(session, tenant_id, candidate_id) == 1

    detail = await client.get(f"/api/v1/candidates/{candidate_id}", headers=rec_json)
    assert detail.status_code == 200, detail.text
    body = detail.json()
    assert body.get("can_edit") is False
    perm = body.get("permissions") or {}
    assert perm.get("operational_owner") == "hr"
    assert perm.get("readonly_reason") == "workforce_hr_ownership"

    note = await client.post(
        f"/api/v1/candidates/{candidate_id}/notes",
        headers=rec_json,
        json={"text": "recruiter bypass attempt", "visibility": "internal"},
    )
    assert note.status_code == 403, note.text


@pytest.mark.asyncio
async def test_operational_write_guards_db_hub_tasks_permits_after_workforce_materialization(
    client: AsyncClient,
    recruiter_headers: Dict[str, str],
    hr_officer_headers: Dict[str, str],
    manager_headers: Dict[str, str],
    candidate_id: str,
    bootstrap: Dict[str, str],
) -> None:
    """Document Hub DB API and candidate-linked activities / permits must respect readonly ownership (recruiter 403; admin still writes)."""
    company_id = bootstrap["company_id"]
    await _ensure_tenant_link_internal_hr(
        client, manager_headers=manager_headers, tenant_id=bootstrap["tenant_id"], company_id=company_id
    )
    rec_json = {**recruiter_headers, "Content-Type": "application/json"}
    mgr_json = {**manager_headers, "Content-Type": "application/json"}

    await seed_documents_for_ready_for_handoff(client, manager_headers, candidate_id)

    await internal_hr_handoff_create_and_accept(
        client,
        recruiter_headers=recruiter_headers,
        hr_officer_headers=hr_officer_headers,
        candidate_id=candidate_id,
        company_id=company_id,
    )

    async with async_session_maker() as session:
        assert await _count_employees_for_candidate(session, bootstrap["tenant_id"], candidate_id) == 1

    db_doc = await client.post(
        f"/api/v1/db/candidate/{candidate_id}/documents",
        headers=rec_json,
        json={"doc_type": "driver_license", "status": "requested"},
    )
    assert db_doc.status_code == 403, db_doc.text
    assert db_doc.json().get("detail") == "candidate_readonly"

    admin_db_doc = await client.post(
        f"/api/v1/db/candidate/{candidate_id}/documents",
        headers=mgr_json,
        json={"doc_type": "driver_license", "status": "requested"},
    )
    assert admin_db_doc.status_code == 201, admin_db_doc.text

    task = await client.post(
        "/api/v1/activities",
        headers=rec_json,
        json={
            "title": "grey path",
            "entity_type": "candidate",
            "entity_id": candidate_id,
            "due_at": "2026-05-09T12:00:00Z",
            "type": "custom",
        },
    )
    assert task.status_code == 403, task.text
    assert task.json().get("detail") == "candidate_readonly"

    permit = await client.post(
        f"/api/v1/candidates/{candidate_id}/permits",
        headers=rec_json,
        json={"permit_type": "test_permit", "status": "active"},
    )
    assert permit.status_code == 403, permit.text
    assert permit.json().get("detail") == "candidate_readonly"


@pytest.mark.asyncio
async def test_recruiter_can_ready_for_hr_but_not_hired_when_handoff_enabled(
    client: AsyncClient,
    recruiter_headers: Dict[str, str],
    manager_headers: Dict[str, str],
    candidate_id: str,
    bootstrap: Dict[str, str],
) -> None:
    tenant_id = bootstrap["tenant_id"]
    company_id = bootstrap["company_id"]
    await _ensure_tenant_link_internal_hr(
        client, manager_headers=manager_headers, tenant_id=tenant_id, company_id=company_id
    )
    rec_json = {**recruiter_headers, "Content-Type": "application/json"}

    patch_ok = await client.patch(
        f"/api/v1/candidates/{candidate_id}",
        headers=rec_json,
        json={"stage": "ready_for_hr"},
    )
    assert patch_ok.status_code == 200, patch_ok.text

    patch_forbidden = await client.patch(
        f"/api/v1/candidates/{candidate_id}",
        headers=rec_json,
        json={"stage": "hired"},
    )
    assert patch_forbidden.status_code == 403, patch_forbidden.text
    assert "handoff" in (patch_forbidden.json().get("detail") or "").lower()


@pytest.mark.asyncio
async def test_ready_for_handoff_alone_does_not_materialize_workforce_until_internal_hr_accept(
    client: AsyncClient,
    recruiter_headers: Dict[str, str],
    hr_officer_headers: Dict[str, str],
    manager_headers: Dict[str, str],
    candidate_id: str,
    bootstrap: Dict[str, str],
) -> None:
    """PR-5: ``ready_for_handoff`` stage does not create WorkforceEmployee; internal HR accept does."""
    tenant_id = bootstrap["tenant_id"]
    company_id = bootstrap["company_id"]
    await _ensure_tenant_link_internal_hr(
        client, manager_headers=manager_headers, tenant_id=tenant_id, company_id=company_id
    )
    lst_links = await client.get(f"/api/v1/tenants/{tenant_id}/links", headers=manager_headers)
    assert lst_links.status_code == 200, lst_links.text
    link_id = None
    for row in lst_links.json():
        if str(row.get("client_company_id") or "") == str(company_id):
            link_id = row["id"]
            break
    assert link_id
    patch_link = await client.patch(
        f"/api/v1/tenants/{tenant_id}/links/{link_id}",
        headers=manager_headers,
        json={"handoff_to_client": False},
    )
    assert patch_link.status_code == 200, patch_link.text

    await seed_documents_for_ready_for_handoff(client, manager_headers, candidate_id)

    rec_json = {**recruiter_headers, "Content-Type": "application/json"}
    patch = await client.patch(
        f"/api/v1/candidates/{candidate_id}",
        headers=rec_json,
        json={"stage": "ready_for_handoff"},
    )
    assert patch.status_code == 200, patch.text
    assert str(patch.json().get("stage") or "").lower() == "ready_for_handoff"

    async with async_session_maker() as session:
        assert await _count_employees_for_candidate(session, tenant_id, candidate_id) == 0

    await internal_hr_handoff_create_and_accept(
        client,
        recruiter_headers=recruiter_headers,
        hr_officer_headers=hr_officer_headers,
        candidate_id=candidate_id,
        company_id=company_id,
    )

    async with async_session_maker() as session:
        assert await _count_employees_for_candidate(session, tenant_id, candidate_id) == 1

    lst = await client.get("/api/v1/workforce/employees", headers=hr_officer_headers)
    assert lst.status_code == 200, lst.text
    _employee_id_for_candidate(lst.json(), candidate_id)


@pytest.mark.asyncio
async def test_workforce_handoff_link_flag_does_not_bypass_handoff_accept_for_materialization(
    client: AsyncClient,
    recruiter_headers: Dict[str, str],
    hr_officer_headers: Dict[str, str],
    manager_headers: Dict[str, str],
    candidate_id: str,
    bootstrap: Dict[str, str],
) -> None:
    """Legacy ``workforce_handoff_on_ready_for_handoff_stage`` must not recreate stage-driven workforce (PR-5)."""
    tenant_id = bootstrap["tenant_id"]
    company_id = bootstrap["company_id"]
    await _ensure_tenant_link_internal_hr(
        client, manager_headers=manager_headers, tenant_id=tenant_id, company_id=company_id
    )
    lst_links = await client.get(f"/api/v1/tenants/{tenant_id}/links", headers=manager_headers)
    assert lst_links.status_code == 200, lst_links.text
    link_id = None
    for row in lst_links.json():
        if str(row.get("client_company_id") or "") == str(company_id):
            link_id = row["id"]
            break
    assert link_id
    patch_link = await client.patch(
        f"/api/v1/tenants/{tenant_id}/links/{link_id}",
        headers=manager_headers,
        json={"workforce_handoff_on_ready_for_handoff_stage": True},
    )
    assert patch_link.status_code == 200, patch_link.text

    await seed_documents_for_ready_for_handoff(client, manager_headers, candidate_id)

    rec_json = {**recruiter_headers, "Content-Type": "application/json"}
    patch = await client.patch(
        f"/api/v1/candidates/{candidate_id}",
        headers=rec_json,
        json={"stage": "ready_for_handoff"},
    )
    assert patch.status_code == 200, patch.text

    async with async_session_maker() as session:
        assert await _count_employees_for_candidate(session, tenant_id, candidate_id) == 0

    await internal_hr_handoff_create_and_accept(
        client,
        recruiter_headers=recruiter_headers,
        hr_officer_headers=hr_officer_headers,
        candidate_id=candidate_id,
        company_id=company_id,
    )

    async with async_session_maker() as session:
        assert await _count_employees_for_candidate(session, tenant_id, candidate_id) == 1

    lst = await client.get("/api/v1/workforce/employees", headers=hr_officer_headers)
    assert lst.status_code == 200, lst.text
    _employee_id_for_candidate(lst.json(), candidate_id)
