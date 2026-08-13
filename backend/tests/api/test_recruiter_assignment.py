import uuid

import pytest
import sqlalchemy as sa

from backend.app.db.session import async_session_maker
from backend.app.models.user import Role as UserRole, User


@pytest.mark.anyio
async def test_candidate_assignment_uses_vacancy_pool(
    client,
    manager_headers,
    tenant_id,
):
    async with async_session_maker() as session:
        recruiter_id = await session.scalar(
            sa.select(User.id).where(User.email == "recruiter@work-host.com").limit(1)
        )
        assert recruiter_id is not None
        company_id = await session.scalar(sa.text("SELECT id FROM companies LIMIT 1"))
        assert company_id is not None

        vacancy_id = str(uuid.uuid4())
        await session.execute(
            sa.text(
                """
                INSERT INTO vacancies (id, tenant_id, company_id, title)
                VALUES (:id, :tenant_id, :company_id, :title)
                """
            ),
            {
                "id": vacancy_id,
                "tenant_id": tenant_id,
                "company_id": company_id,
                "title": "Linehaul Driver",
            },
        )
        await session.execute(
            sa.text(
                """
                INSERT INTO vacancy_recruiters (vacancy_id, user_id, tenant_id, weight, is_active)
                VALUES (:vacancy_id, :user_id, :tenant_id, :weight, :is_active)
                """
            ),
            {
                "vacancy_id": vacancy_id,
                "user_id": recruiter_id,
                "tenant_id": tenant_id,
                "weight": 1,
                "is_active": True,
            },
        )
        await session.commit()

    payload = {
        "first_name": "Auto",
        "last_name": "Assigned",
        "vacancy_id": vacancy_id,
    }
    resp = await client.post("/api/v1/candidates", headers=manager_headers, json=payload)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["recruiter_id"] == recruiter_id


@pytest.mark.anyio
async def test_candidate_assignment_falls_back_to_vacancy_owner(
    client,
    manager_headers,
    tenant_id,
):
    async with async_session_maker() as session:
        supervisor_id = await session.scalar(
            sa.select(User.id).where(User.email == "supervisor@work-host.com").limit(1)
        )
        assert supervisor_id is not None
        company_id = await session.scalar(sa.text("SELECT id FROM companies LIMIT 1"))
        vacancy_id = str(uuid.uuid4())
        await session.execute(
            sa.text(
                """
                INSERT INTO vacancies (id, tenant_id, company_id, title, manager)
                VALUES (:id, :tenant_id, :company_id, :title, :manager)
                """
            ),
            {
                "id": vacancy_id,
                "tenant_id": tenant_id,
                "company_id": company_id,
                "title": "Local Driver",
                "manager": supervisor_id,
            },
        )
        await session.commit()

    payload = {
        "first_name": "Owner",
        "last_name": "Fallback",
        "vacancy_id": vacancy_id,
    }
    resp = await client.post("/api/v1/candidates", headers=manager_headers, json=payload)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["recruiter_id"] == supervisor_id


@pytest.mark.anyio
async def test_recruiter_assign_endpoint_returns_context(
    client,
    manager_headers,
    tenant_id,
):
    async with async_session_maker() as session:
        recruiter_id = await session.scalar(
            sa.select(User.id).where(User.email == "recruiter@work-host.com").limit(1)
        )
        company_id = await session.scalar(sa.text("SELECT id FROM companies LIMIT 1"))
        vacancy_id = str(uuid.uuid4())
        await session.execute(
            sa.text(
                """
                INSERT INTO vacancies (id, tenant_id, company_id, title)
                VALUES (:id, :tenant_id, :company_id, :title)
                """
            ),
            {
                "id": vacancy_id,
                "tenant_id": tenant_id,
                "company_id": company_id,
                "title": "Linehaul Team",
            },
        )
        await session.execute(
            sa.text(
                """
                INSERT INTO vacancy_recruiters (vacancy_id, user_id, tenant_id, weight, is_active)
                VALUES (:vacancy_id, :user_id, :tenant_id, :weight, :is_active)
                """
            ),
            {
                "vacancy_id": vacancy_id,
                "user_id": recruiter_id,
                "tenant_id": tenant_id,
                "weight": 1,
                "is_active": True,
            },
        )
        await session.commit()

    resp = await client.post(
        "/api/v1/recruiters/assign",
        headers=manager_headers,
        json={"vacancy_id": vacancy_id},
    )
    assert resp.status_code == 200, resp.text
    payload = resp.json()
    assert payload["recruiter_id"] == recruiter_id
    assert payload["strategy"] == "least_load"
    assert payload["context"].get("vacancy_id") == vacancy_id
