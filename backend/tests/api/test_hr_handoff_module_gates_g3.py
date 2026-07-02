"""B2-G3 — module gates on handoff create/accept and from-candidate."""

from __future__ import annotations

from typing import Dict
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient
from backend.app.db.deps import bind_tenant_context_to_session
from backend.app.db.session import async_session_maker
from backend.app.models.candidate_handoff import CandidateHandoff
from backend.app.models.company import Company
from backend.tests.test_support.candidate_evidence_helpers import ensure_tenant_link_internal_hr

pytestmark = pytest.mark.anyio


async def _set_company_modules(
    tenant_id: str,
    company_id: str,
    *,
    modules: dict[str, bool] | None,
) -> dict | None:
    async with async_session_maker() as session:
        await bind_tenant_context_to_session(session, UUID(tenant_id))
        company = await session.get(Company, company_id)
        assert company is not None
        prev = company.enabled_modules
        company.enabled_modules = modules
        await session.commit()
        return prev


async def _restore_company_modules(tenant_id: str, company_id: str, prev: dict | None) -> None:
    async with async_session_maker() as session:
        await bind_tenant_context_to_session(session, UUID(tenant_id))
        company = await session.get(Company, company_id)
        if company is not None:
            company.enabled_modules = prev
            await session.commit()


async def test_create_internal_hr_handoff_403_when_hr_disabled(
    client: AsyncClient,
    manager_headers: Dict[str, str],
    recruiter_headers: Dict[str, str],
    bootstrap: Dict[str, str],
    candidate_id: str,
) -> None:
    tenant_id = bootstrap["tenant_id"]
    company_id = bootstrap["company_id"]
    await ensure_tenant_link_internal_hr(
        client,
        manager_headers=manager_headers,
        tenant_id=tenant_id,
        company_id=company_id,
    )
    prev = await _set_company_modules(
        tenant_id,
        company_id,
        modules={"hr": False},
    )
    try:
        resp = await client.post(
            f"/api/v1/handoffs/candidates/{candidate_id}",
            headers=recruiter_headers,
            json={"client_company_id": company_id, "destination": "internal_hr"},
        )
        assert resp.status_code == 403, resp.text
        assert "hr module" in str(resp.json().get("detail") or "").lower()
    finally:
        await _restore_company_modules(tenant_id, company_id, prev)


async def test_create_handoff_403_when_recruitment_disabled(
    client: AsyncClient,
    manager_headers: Dict[str, str],
    recruiter_headers: Dict[str, str],
    bootstrap: Dict[str, str],
    candidate_id: str,
) -> None:
    tenant_id = bootstrap["tenant_id"]
    company_id = bootstrap["company_id"]
    await ensure_tenant_link_internal_hr(
        client, manager_headers=manager_headers, tenant_id=tenant_id, company_id=company_id
    )
    prev = await _set_company_modules(
        tenant_id,
        company_id,
        modules={"hr": True, "recruitment": False},
    )
    try:
        resp = await client.post(
            f"/api/v1/handoffs/candidates/{candidate_id}",
            headers=recruiter_headers,
            json={"client_company_id": company_id, "destination": "client_portal"},
        )
        assert resp.status_code == 403, resp.text
        assert "recruitment module" in str(resp.json().get("detail") or "").lower()
    finally:
        await _restore_company_modules(tenant_id, company_id, prev)


async def test_accept_internal_hr_handoff_403_when_hr_disabled(
    client: AsyncClient,
    manager_headers: Dict[str, str],
    hr_officer_headers: Dict[str, str],
    bootstrap: Dict[str, str],
    candidate_id: str,
) -> None:
    tenant_id = bootstrap["tenant_id"]
    company_id = bootstrap["company_id"]
    handoff_id = str(uuid4())

    async with async_session_maker() as session:
        await bind_tenant_context_to_session(session, UUID(tenant_id))
        session.add(
            CandidateHandoff(
                id=handoff_id,
                candidate_id=candidate_id,
                agency_tenant_id=tenant_id,
                client_company_id=company_id,
                requested_by_user_id=bootstrap["recruiter_id"],
                status="pending_review",
                destination="internal_hr",
                handoff_type="internal_hr",
            )
        )
        await session.commit()

    prev = await _set_company_modules(
        tenant_id,
        company_id,
        modules={"hr": False},
    )
    try:
        resp = await client.post(
            f"/api/v1/handoffs/{handoff_id}/accept",
            headers=hr_officer_headers,
        )
        assert resp.status_code == 403, resp.text
        assert "hr module" in str(resp.json().get("detail") or "").lower()
    finally:
        await _restore_company_modules(tenant_id, company_id, prev)


async def test_from_candidate_403_when_hr_disabled(
    client: AsyncClient,
    manager_headers: Dict[str, str],
    recruiter_headers: Dict[str, str],
    bootstrap: Dict[str, str],
    candidate_id: str,
) -> None:
    tenant_id = bootstrap["tenant_id"]
    company_id = bootstrap["company_id"]
    prev = await _set_company_modules(
        tenant_id,
        company_id,
        modules={"hr": False},
    )
    try:
        resp = await client.post(
            f"/api/v1/workforce/employees/from-candidate/{candidate_id}",
            headers=recruiter_headers,
            json={},
        )
        assert resp.status_code == 403, resp.text
        assert "hr module" in str(resp.json().get("detail") or "").lower()
    finally:
        await _restore_company_modules(tenant_id, company_id, prev)


async def test_from_candidate_403_when_recruitment_disabled(
    client: AsyncClient,
    manager_headers: Dict[str, str],
    recruiter_headers: Dict[str, str],
    bootstrap: Dict[str, str],
    candidate_id: str,
) -> None:
    tenant_id = bootstrap["tenant_id"]
    company_id = bootstrap["company_id"]
    prev = await _set_company_modules(
        tenant_id,
        company_id,
        modules={"hr": True, "recruitment": False},
    )
    try:
        resp = await client.post(
            f"/api/v1/workforce/employees/from-candidate/{candidate_id}",
            headers=recruiter_headers,
            json={},
        )
        assert resp.status_code == 403, resp.text
        assert "recruitment module" in str(resp.json().get("detail") or "").lower()
    finally:
        await _restore_company_modules(tenant_id, company_id, prev)


async def test_client_portal_handoff_allowed_when_hr_disabled(
    client: AsyncClient,
    manager_headers: Dict[str, str],
    recruiter_headers: Dict[str, str],
    bootstrap: Dict[str, str],
    candidate_id: str,
) -> None:
    """Client portal handoff only requires recruitment — HR off must not 403 at module gate."""
    tenant_id = bootstrap["tenant_id"]
    company_id = bootstrap["company_id"]
    await ensure_tenant_link_internal_hr(
        client, manager_headers=manager_headers, tenant_id=tenant_id, company_id=company_id
    )
    prev = await _set_company_modules(
        tenant_id,
        company_id,
        modules={"hr": False},
    )
    try:
        resp = await client.post(
            f"/api/v1/handoffs/candidates/{candidate_id}",
            headers=recruiter_headers,
            json={"client_company_id": company_id, "destination": "client_portal"},
        )
        if resp.status_code == 403:
            detail = str(resp.json().get("detail") or "").lower()
            assert "hr module" not in detail, resp.text
            assert "recruitment module" not in detail, resp.text
    finally:
        await _restore_company_modules(tenant_id, company_id, prev)
