"""API tests for merge document templates + generation."""

from __future__ import annotations

import uuid
from typing import Any, Dict

import pytest
import sqlalchemy as sa
from httpx import AsyncClient

from backend.app.db.session import async_session_maker
from backend.tests.conftest import DEFAULT_TENANT_ID, _set_tenant


@pytest.mark.asyncio
async def test_merge_template_crud_and_generate(
    client: AsyncClient,
    supervisor_headers: Dict[str, str],
    recruiter_headers: Dict[str, str],
    bootstrap: Dict[str, str],
) -> None:
    cid = bootstrap["candidate_id"]

    code = f"contract_snippet_{uuid.uuid4().hex[:8]}"
    create = await client.post(
        "/api/v1/document-merge/templates",
        headers=supervisor_headers,
        json={
            "code": code,
            "name": "Test merge template",
            "body_text": "Hello {{ candidate.first_name }} {{ candidate.last_name }}",
            "variable_bindings": {"signing.city": "Warsaw"},
            "output_filename_pattern": "{{ candidate.last_name }}_merge.txt",
        },
    )
    assert create.status_code == 201, create.text
    tpl = create.json()
    tpl_id = tpl["id"]
    assert tpl["code"] == code

    listed = await client.get("/api/v1/document-merge/templates", headers=supervisor_headers)
    assert listed.status_code == 200, listed.text
    codes = {row["code"] for row in listed.json()}
    assert code in codes

    gen = await client.post(
        "/api/v1/document-merge/generate",
        headers=recruiter_headers,
        json={
            "template_id": tpl_id,
            "candidate_id": cid,
            "variable_bindings": {"extra.line": "OK"},
        },
    )
    assert gen.status_code == 201, gen.text
    body = gen.json()
    assert body["status"] == "success"
    assert body["document_id"]

    patched = await client.patch(
        f"/api/v1/document-merge/templates/{tpl_id}",
        headers=supervisor_headers,
        json={"is_active": False},
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["is_active"] is False

    deleted = await client.delete(
        f"/api/v1/document-merge/templates/{tpl_id}",
        headers=supervisor_headers,
    )
    assert deleted.status_code == 204, deleted.text


@pytest.mark.asyncio
async def test_merge_generate_by_code_with_oc_fallback(
    client: AsyncClient,
    supervisor_headers: Dict[str, str],
    hr_officer_headers: Dict[str, str],
    recruiter_headers: Dict[str, str],
    bootstrap: Dict[str, str],
    candidate_id: str,
) -> None:
    """Scoped template wins over global when employee has own_company_id."""

    oc_id = str(uuid.uuid4())
    async with async_session_maker() as session:
        await _set_tenant(session, DEFAULT_TENANT_ID)
        await session.execute(
            sa.text(
                """
                INSERT INTO own_companies (id, tenant_id, name, created_at, updated_at)
                VALUES (:id, :tenant_id, :name, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """
            ),
            {"id": oc_id, "tenant_id": DEFAULT_TENANT_ID, "name": "Merge Test Sp zoo"},
        )
        await session.commit()

    dup = f"dup_code_{uuid.uuid4().hex[:8]}"
    g = await client.post(
        "/api/v1/document-merge/templates",
        headers=supervisor_headers,
        json={
            "code": dup,
            "name": "Global",
            "body_text": "GLOBAL",
            "own_company_id": None,
        },
    )
    assert g.status_code == 201, g.text

    s = await client.post(
        "/api/v1/document-merge/templates",
        headers=supervisor_headers,
        json={
            "code": dup,
            "name": "Scoped",
            "body_text": "SCOPED_BODY",
            "own_company_id": oc_id,
        },
    )
    assert s.status_code == 201, s.text

    emp = await client.post(
        "/api/v1/workforce/employees",
        headers=hr_officer_headers,
        json={
            "display_name": "Merge OC employee",
            "status": "active",
            "company_id": bootstrap["company_id"],
            "candidate_id": candidate_id,
            "own_company_id": oc_id,
        },
    )
    assert emp.status_code == 201, emp.text
    emp_id = emp.json()["id"]

    gen = await client.post(
        "/api/v1/document-merge/generate",
        headers=recruiter_headers,
        json={
            "template_code": dup,
            "workforce_employee_id": emp_id,
        },
    )
    assert gen.status_code == 201, gen.text

    doc_id = gen.json()["document_id"]
    hdr = {**recruiter_headers, "X-Own-Company-Id": oc_id}
    docs = await client.get(
        f"/api/v1/candidates/candidate/{candidate_id}/documents",
        headers=hdr,
    )
    assert docs.status_code == 200, docs.text
    rows: list[dict[str, Any]] = docs.json()
    hit = next((r for r in rows if r.get("id") == doc_id), None)
    assert hit is not None


@pytest.mark.asyncio
async def test_merge_template_viewer_forbidden(
    client: AsyncClient,
    viewer_headers: Dict[str, str],
) -> None:
    res = await client.get("/api/v1/document-merge/templates", headers=viewer_headers)
    assert res.status_code == 403
