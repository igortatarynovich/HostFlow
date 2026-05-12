"""ADR-003 P1b: company-level recruitment gate on candidate API."""

from __future__ import annotations

from typing import Dict
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient
from backend.app.db.deps import bind_tenant_context_to_session
from backend.app.db.session import async_session_maker
from backend.app.models.company import Company

pytestmark = pytest.mark.anyio


async def test_post_candidate_403_when_company_disables_recruitment(
    client: AsyncClient,
    manager_headers: Dict[str, str],
    bootstrap: Dict[str, str],
) -> None:
    tid = bootstrap["tenant_id"]
    cid = bootstrap["company_id"]
    async with async_session_maker() as session:
        await bind_tenant_context_to_session(session, UUID(tid))
        company = await session.get(Company, cid)
        assert company is not None
        prev = company.enabled_modules
        company.enabled_modules = {"recruitment": False}
        await session.commit()

    try:
        r = await client.post(
            "/api/v1/candidates",
            headers=manager_headers,
            json={
                "first_name": "Gate",
                "last_name": "Test",
                "company_id": cid,
            },
        )
        assert r.status_code == 403, r.text
        assert "disabled" in r.json().get("detail", "").lower()
    finally:
        async with async_session_maker() as session:
            await bind_tenant_context_to_session(session, UUID(tid))
            company = await session.get(Company, cid)
            if company is not None:
                company.enabled_modules = prev
                await session.commit()


async def test_get_candidate_403_when_company_disables_recruitment(
    client: AsyncClient,
    manager_headers: Dict[str, str],
    bootstrap: Dict[str, str],
    candidate_id: str,
) -> None:
    tid = bootstrap["tenant_id"]
    cid = bootstrap["company_id"]
    async with async_session_maker() as session:
        await bind_tenant_context_to_session(session, UUID(tid))
        company = await session.get(Company, cid)
        assert company is not None
        prev = company.enabled_modules
        company.enabled_modules = {"recruitment": False}
        await session.commit()

    try:
        r = await client.get(f"/api/v1/candidates/{candidate_id}", headers=manager_headers)
        assert r.status_code == 403, r.text
    finally:
        async with async_session_maker() as session:
            await bind_tenant_context_to_session(session, UUID(tid))
            company = await session.get(Company, cid)
            if company is not None:
                company.enabled_modules = prev
                await session.commit()


async def test_patch_candidate_company_reassignment_blocked_when_recruitment_off(
    client: AsyncClient,
    manager_headers: Dict[str, str],
    bootstrap: Dict[str, str],
    candidate_id: str,
) -> None:
    """Second company with recruitment disabled — PATCH company_id must fail."""
    tid = bootstrap["tenant_id"]
    second_id = str(uuid4())
    async with async_session_maker() as session:
        await bind_tenant_context_to_session(session, UUID(tid))
        c2 = Company(
            id=second_id,
            tenant_id=tid,
            name="No Recruitment Co",
            enabled_modules={"recruitment": False},
        )
        session.add(c2)
        await session.commit()

    try:
        r = await client.patch(
            f"/api/v1/candidates/{candidate_id}",
            headers=manager_headers,
            json={
                "company_id": second_id,
                "override_reason": "test company module gate",
            },
        )
        assert r.status_code == 403, r.text
    finally:
        async with async_session_maker() as session:
            await bind_tenant_context_to_session(session, UUID(tid))
            row = await session.get(Company, second_id)
            if row is not None:
                await session.delete(row)
                await session.commit()


async def test_list_candidates_excludes_company_when_recruitment_disabled(
    client: AsyncClient,
    manager_headers: Dict[str, str],
    bootstrap: Dict[str, str],
    candidate_id: str,
) -> None:
    tid = bootstrap["tenant_id"]
    cid = bootstrap["company_id"]
    async with async_session_maker() as session:
        await bind_tenant_context_to_session(session, UUID(tid))
        company = await session.get(Company, cid)
        assert company is not None
        prev = company.enabled_modules
        company.enabled_modules = {"recruitment": False}
        await session.commit()

    try:
        r = await client.get(
            "/api/v1/candidates",
            headers=manager_headers,
            params={"limit": 200, "offset": 0},
        )
        assert r.status_code == 200, r.text
        ids = {item.get("id") for item in r.json().get("items", [])}
        assert candidate_id not in ids
    finally:
        async with async_session_maker() as session:
            await bind_tenant_context_to_session(session, UUID(tid))
            company = await session.get(Company, cid)
            if company is not None:
                company.enabled_modules = prev
                await session.commit()


async def test_bulk_stage_fails_per_row_when_recruitment_disabled(
    client: AsyncClient,
    manager_headers: Dict[str, str],
    bootstrap: Dict[str, str],
    candidate_id: str,
) -> None:
    tid = bootstrap["tenant_id"]
    cid = bootstrap["company_id"]
    async with async_session_maker() as session:
        await bind_tenant_context_to_session(session, UUID(tid))
        company = await session.get(Company, cid)
        assert company is not None
        prev = company.enabled_modules
        company.enabled_modules = {"recruitment": False}
        await session.commit()

    try:
        r = await client.post(
            "/api/v1/candidates/bulk-stage",
            headers=manager_headers,
            json={"candidate_ids": [candidate_id], "stage": "new"},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert len(body) == 1
        assert body[0].get("ok") is False
    finally:
        async with async_session_maker() as session:
            await bind_tenant_context_to_session(session, UUID(tid))
            company = await session.get(Company, cid)
            if company is not None:
                company.enabled_modules = prev
                await session.commit()
