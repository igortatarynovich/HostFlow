import uuid
from datetime import datetime, timezone

import pytest
import sqlalchemy as sa
from httpx import AsyncClient

from backend.tests.conftest import _init_data, _build_token, async_session_maker


def _recruiter_headers(data: dict[str, str]) -> dict[str, str]:
    token = _build_token(
        data["recruiter_id"],
        data["recruiter_email"],
        "recruiter",
        data["tenant_id"],
        data.get("supervisor_id"),
    )
    return {
        "Authorization": f"Bearer {token}",
        "X-Tenant-Id": data["tenant_id"],
        "Content-Type": "application/json",
    }


def _admin_headers(data: dict[str, str]) -> dict[str, str]:
    token = _build_token(data["admin_id"], data["admin_email"], "administrator", data["tenant_id"])
    return {
        "Authorization": f"Bearer {token}",
        "X-Tenant-Id": data["tenant_id"],
        "Content-Type": "application/json",
    }


@pytest.mark.anyio
async def test_recruiter_can_list_candidates(client: AsyncClient) -> None:
    data = await _init_data()
    headers = _recruiter_headers(data)
    resp = await client.get("/api/v1/candidates", headers=headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["total"] >= 1
    assert any(item["id"] == data["candidate_id"] for item in body["items"])


@pytest.mark.anyio
async def test_recruiter_cannot_access_foreign_candidate(client: AsyncClient) -> None:
    data = await _init_data()
    async with async_session_maker() as session:
        other_company = str(uuid.uuid4())
        await session.execute(
            sa.text(
                "INSERT INTO companies (id, tenant_id, name) VALUES (:id, :tenant_id, :name)"
            ),
            {"id": other_company, "tenant_id": data["tenant_id"], "name": "Other Logistics"},
        )
        other_candidate = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        await session.execute(
            sa.text(
                """
                INSERT INTO candidates (id, tenant_id, first_name, last_name, company_id, created_at, updated_at)
                VALUES (:id, :tenant_id, :first_name, :last_name, :company_id, :created_at, :updated_at)
                """
            ),
            {
                "id": other_candidate,
                "tenant_id": data["tenant_id"],
                "first_name": "Anna",
                "last_name": "Nowak",
                "company_id": other_company,
                "created_at": now,
                "updated_at": now,
            },
        )
        await session.commit()

    headers = _recruiter_headers(data)
    resp = await client.get(f"/api/v1/candidates/{other_candidate}", headers=headers)
    assert resp.status_code == 403


@pytest.mark.anyio
async def test_recruiter_can_create_candidate_in_accessible_company(client: AsyncClient) -> None:
    data = await _init_data()
    headers = _recruiter_headers(data)
    payload = {
        "first_name": "Adam",
        "last_name": "Kowalski",
        "company_id": data["company_id"],
        "email": "adam.kowalski@example.com",
    }
    resp = await client.post("/api/v1/candidates", headers=headers, json=payload)
    assert resp.status_code == 200, resp.text
    created = resp.json()
    assert created["company_id"] == data["company_id"]
    assert created["manager_id"] == data["recruiter_id"]


@pytest.mark.anyio
async def test_recruiter_cannot_create_candidate_in_foreign_company(client: AsyncClient) -> None:
    data = await _init_data()
    headers = _recruiter_headers(data)
    async with async_session_maker() as session:
        other_company = str(uuid.uuid4())
        await session.execute(
            sa.text(
                "INSERT INTO companies (id, tenant_id, name) VALUES (:id, :tenant_id, :name)"
            ),
            {"id": other_company, "tenant_id": data["tenant_id"], "name": "Blocked Company"},
        )
        await session.commit()
    payload = {
        "first_name": "Blocked",
        "last_name": "User",
        "company_id": other_company,
    }
    resp = await client.post("/api/v1/candidates", headers=headers, json=payload)
    assert resp.status_code == 403


@pytest.mark.anyio
async def test_recruiter_can_update_stage(client: AsyncClient) -> None:
    data = await _init_data()
    headers = _recruiter_headers(data)
    resp = await client.patch(
        f"/api/v1/candidates/{data['candidate_id']}",
        headers=headers,
        json={"stage": "contacted"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["stage"] == "contacted"


@pytest.mark.anyio
async def test_recruiter_document_crud(client: AsyncClient) -> None:
    data = await _init_data()
    headers = _recruiter_headers(data)
    payload = {
        "doc_type": "passport",
        "status": "pending_validation",
        "title": "Passport",
        "number": "ABC123456",
    }
    resp = await client.post(
        f"/candidates/{data['candidate_id']}/documents",
        headers=headers,
        json=payload,
    )
    assert resp.status_code == 201, resp.text
    doc = resp.json()
    doc_id = doc["id"]

    update_resp = await client.patch(
        f"/candidates/{data['candidate_id']}/documents/{doc_id}",
        headers=headers,
        json={"status": "verified"},
    )
    assert update_resp.status_code == 200


@pytest.mark.anyio
async def test_recruiter_can_view_pipeline(client: AsyncClient) -> None:
    data = await _init_data()
    # создаём вакансию для доступной компании
    vacancy_id: str
    payload = {
        "title": "Driver",
        "company_id": data["company_id"],
        "status": "open",
    }
    admin_headers = _admin_headers(data)
    resp = await client.post("/api/v1/vacancies", headers=admin_headers, json=payload)
    assert resp.status_code == 200, resp.text
    vacancy_id = resp.json()["id"]

    # Привязываем кандидата к вакансии, чтобы пайплайн не был пустым
    attach_resp = await client.post(
        f"/api/v1/vacancies/{vacancy_id}/candidates",
        headers=admin_headers,
        json={"candidate_id": data["candidate_id"]},
    )
    assert attach_resp.status_code == 200, attach_resp.text

    headers = _recruiter_headers(data)
    pipeline_resp = await client.get(f"/api/v1/vacancies/{vacancy_id}/pipeline", headers=headers)
    assert pipeline_resp.status_code == 200, pipeline_resp.text
    body = pipeline_resp.json()
    assert body["vacancy_id"] == vacancy_id
