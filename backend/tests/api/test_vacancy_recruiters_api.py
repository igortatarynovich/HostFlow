"""API tests for GET/PUT /vacancies/{id}/recruiters."""

from __future__ import annotations

import uuid

import pytest
import sqlalchemy as sa

from backend.app.db.session import async_session_maker
from backend.app.models.user import Role as UserRole, User


@pytest.mark.anyio
async def test_vacancy_recruiters_get_put_roundtrip(
    client,
    manager_headers,
    tenant_id,
):
    async with async_session_maker() as session:
        recruiter_ids = (
            await session.execute(
                sa.select(User.id)
                .where(
                    User.email == "recruiter@work-host.com",
                    User.is_active.is_(True),
                    User.deleted_at.is_(None),
                    sa.or_(User.tenant_id.is_(None), User.tenant_id == str(tenant_id)),
                )
                .limit(2)
            )
        ).scalars().all()
        assert len(recruiter_ids) >= 1
        company_id = await session.scalar(
            sa.text("SELECT id FROM companies WHERE tenant_id = :tid LIMIT 1"),
            {"tid": str(tenant_id)},
        )
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
                "title": "Pool UI vacancy",
            },
        )
        await session.commit()

    empty = await client.get(
        f"/api/v1/vacancies/{vacancy_id}/recruiters",
        headers=manager_headers,
    )
    assert empty.status_code == 200, empty.text
    assert empty.json()["items"] == []

    payload = {
        "items": [
            {"user_id": recruiter_ids[0], "weight": 2, "is_active": True},
        ]
    }
    if len(recruiter_ids) > 1:
        payload["items"].append(
            {"user_id": recruiter_ids[1], "weight": 1, "is_active": True}
        )

    put = await client.put(
        f"/api/v1/vacancies/{vacancy_id}/recruiters",
        headers=manager_headers,
        json=payload,
    )
    assert put.status_code == 200, put.text
    body = put.json()
    assert body["vacancy_id"] == vacancy_id
    assert len(body["items"]) == len(payload["items"])
    by_id = {item["user_id"]: item for item in body["items"]}
    assert by_id[recruiter_ids[0]]["weight"] == 2

    got = await client.get(
        f"/api/v1/vacancies/{vacancy_id}/recruiters",
        headers=manager_headers,
    )
    assert got.status_code == 200
    assert len(got.json()["items"]) == len(payload["items"])

    # Clear pool
    cleared = await client.put(
        f"/api/v1/vacancies/{vacancy_id}/recruiters",
        headers=manager_headers,
        json={"items": []},
    )
    assert cleared.status_code == 200
    assert cleared.json()["items"] == []


@pytest.mark.anyio
async def test_vacancy_recruiters_rejects_non_recruiter(
    client,
    manager_headers,
    tenant_id,
):
    async with async_session_maker() as session:
        admin_id = await session.scalar(
            sa.select(User.id)
            .where(
                User.role == UserRole.administrator,
                User.is_active.is_(True),
                User.deleted_at.is_(None),
                sa.or_(User.tenant_id.is_(None), User.tenant_id == str(tenant_id)),
            )
            .limit(1)
        )
        assert admin_id is not None
        company_id = await session.scalar(
            sa.text("SELECT id FROM companies WHERE tenant_id = :tid LIMIT 1"),
            {"tid": str(tenant_id)},
        )
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
                "title": "Reject admin in pool",
            },
        )
        await session.commit()

    resp = await client.put(
        f"/api/v1/vacancies/{vacancy_id}/recruiters",
        headers=manager_headers,
        json={"items": [{"user_id": admin_id, "weight": 1, "is_active": True}]},
    )
    assert resp.status_code == 422, resp.text
