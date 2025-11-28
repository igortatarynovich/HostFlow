from __future__ import annotations

import textwrap
from uuid import uuid4

import pytest
import sqlalchemy as sa

from backend.app.db.session import async_session_maker
from backend.app.models import Lead
from backend.tests.api.test_leads_meta import _ensure_company, _ensure_vacancy


def _csv_payload(company_id: str, vacancy_id: str) -> str:
    return textwrap.dedent(
        f"""
        first_name,last_name,email,phone,company_id,vacancy_id
        John,Doe,john.doe@example.com,+48123123123,{company_id},{vacancy_id}
        Jane,Doe,jane.doe@example.com,+48123123124,{company_id},{vacancy_id}
        """
    ).strip()


@pytest.mark.anyio
async def test_leads_import_sync_creates_leads(client, manager_headers, tenant_id):
    async with async_session_maker() as session:
        company_id = await _ensure_company(session, tenant_id)
        vacancy_id = await _ensure_vacancy(session, tenant_id, company_id)

    csv_body = _csv_payload(company_id, vacancy_id)
    files = {"file": ("leads.csv", csv_body, "text/csv")}

    response = await client.post(
        "/api/v1/settings/leads/import",
        params={"sync": "true"},
        headers=manager_headers,
        files=files,
    )
    assert response.status_code == 202, response.text
    body = response.json()
    assert body["status"] == "completed"
    assert body["success_rows"] == 2
    assert body["duplicate_rows"] == 0
    assert body["failed_rows"] == 0

    job_id = body["id"]

    job_response = await client.get(
        f"/api/v1/settings/leads/import/{job_id}",
        headers=manager_headers,
    )
    assert job_response.status_code == 200
    job_body = job_response.json()
    assert job_body["id"] == job_id
    assert job_body["processed_rows"] == 2

    async with async_session_maker() as session:
        count = await session.scalar(
            sa.select(sa.func.count())
            .select_from(Lead)
            .where(Lead.tenant_id == tenant_id)
        )
        assert count and count >= 2


@pytest.mark.anyio
async def test_leads_import_sync_idempotent(client, manager_headers, tenant_id):
    async with async_session_maker() as session:
        company_id = await _ensure_company(session, tenant_id)
        vacancy_id = await _ensure_vacancy(session, tenant_id, company_id)

    csv_body = _csv_payload(company_id, vacancy_id)
    files = {"file": ("leads.csv", csv_body, "text/csv")}

    await client.post(
        "/api/v1/settings/leads/import",
        params={"sync": "true"},
        headers=manager_headers,
        files=files,
    )
    files = {"file": ("leads.csv", csv_body, "text/csv")}

    response = await client.post(
        "/api/v1/settings/leads/import",
        params={"sync": "true"},
        headers=manager_headers,
        files=files,
    )
    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "completed"
    assert body["success_rows"] == 0
    assert body["duplicate_rows"] == 2


@pytest.mark.anyio
async def test_leads_import_requires_admin(client, recruiter_headers):
    csv_body = _csv_payload(str(uuid4()), str(uuid4()))
    files = {"file": ("leads.csv", csv_body, "text/csv")}

    response = await client.post(
        "/api/v1/settings/leads/import",
        params={"sync": "true"},
        headers=recruiter_headers,
        files=files,
    )
    assert response.status_code == 403


@pytest.mark.anyio
async def test_leads_import_supervisor_read_only(
    client,
    manager_headers,
    supervisor_headers,
    tenant_id,
):
    async with async_session_maker() as session:
        company_id = await _ensure_company(session, tenant_id)
        vacancy_id = await _ensure_vacancy(session, tenant_id, company_id)

    csv_body = _csv_payload(company_id, vacancy_id)
    files = {"file": ("leads.csv", csv_body, "text/csv")}

    response = await client.post(
        "/api/v1/settings/leads/import",
        params={"sync": "true"},
        headers=manager_headers,
        files=files,
    )
    assert response.status_code == 202
    job_id = response.json()["id"]

    list_resp = await client.get(
        "/api/v1/settings/leads/import",
        headers=supervisor_headers,
    )
    assert list_resp.status_code == 200, list_resp.text
    assert list_resp.json()["items"], list_resp.json()

    job_resp = await client.get(
        f"/api/v1/settings/leads/import/{job_id}",
        headers=supervisor_headers,
    )
    assert job_resp.status_code == 200, job_resp.text


@pytest.mark.anyio
async def test_leads_import_supervisor_cannot_start(
    client,
    supervisor_headers,
    tenant_id,
):
    async with async_session_maker() as session:
        company_id = await _ensure_company(session, tenant_id)
        vacancy_id = await _ensure_vacancy(session, tenant_id, company_id)

    csv_body = _csv_payload(company_id, vacancy_id)
    files = {"file": ("leads.csv", csv_body, "text/csv")}

    response = await client.post(
        "/api/v1/settings/leads/import",
        params={"sync": "true"},
        headers=supervisor_headers,
        files=files,
    )
    assert response.status_code == 403
