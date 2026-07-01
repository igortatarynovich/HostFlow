"""Regression tests for recruitment RBAC: ACL vs role gates (viewer, hr_officer, mutations)."""

import uuid

import pytest
import sqlalchemy as sa
from httpx import AsyncClient
from sqlalchemy import text

from backend.tests.conftest import _build_token, _init_data, async_session_maker


async def _bind_rls_tenant(session, tenant_id: str) -> None:
    try:
        await session.execute(
            text("SELECT set_config('app.tenant_id', :tid, false)"),
            {"tid": tenant_id},
        )
    except Exception:
        pass


def _headers(token: str, tenant_id: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "X-Tenant-Id": tenant_id,
        "Content-Type": "application/json",
    }


@pytest.mark.anyio
async def test_viewer_candidate_list_is_acl_filtered_not_error(client: AsyncClient) -> None:
    """Viewer may still see rows via shared vacancy/company visibility without user_company_access."""
    data = await _init_data()
    token = _build_token(data["viewer_id"], data["viewer_email"], "viewer", data["tenant_id"])
    resp = await client.get("/api/v1/candidates", headers=_headers(token, data["tenant_id"]))
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert isinstance(body.get("total"), int)
    assert isinstance(body.get("items"), list)


@pytest.mark.anyio
async def test_viewer_cannot_patch_candidate(client: AsyncClient) -> None:
    data = await _init_data()
    async with async_session_maker() as session:
        await _bind_rls_tenant(session, data["tenant_id"])
        await session.execute(
            sa.text(
                """
                INSERT INTO user_company_access (id, tenant_id, user_id, company_id, can_edit)
                VALUES (:id, :tenant_id, :user_id, :company_id, :can_edit)
                ON CONFLICT(tenant_id, user_id, company_id)
                DO UPDATE SET can_edit = excluded.can_edit
                """
            ),
            {
                "id": str(uuid.uuid4()),
                "tenant_id": data["tenant_id"],
                "user_id": data["viewer_id"],
                "company_id": data["company_id"],
                "can_edit": False,
            },
        )
        await session.commit()

    token = _build_token(data["viewer_id"], data["viewer_email"], "viewer", data["tenant_id"])
    resp = await client.patch(
        f"/api/v1/candidates/{data['candidate_id']}",
        headers=_headers(token, data["tenant_id"]),
        json={"first_name": "X"},
    )
    assert resp.status_code == 403


@pytest.mark.anyio
async def test_hr_officer_jwt_blocked_from_candidates_list(client: AsyncClient) -> None:
    data = await _init_data()
    token = _build_token(data["viewer_id"], data["viewer_email"], "hr_officer", data["tenant_id"])
    resp = await client.get("/api/v1/candidates", headers=_headers(token, data["tenant_id"]))
    assert resp.status_code == 403


@pytest.mark.anyio
async def test_superadmin_jwt_can_list_candidates(client: AsyncClient) -> None:
    data = await _init_data()
    token = _build_token(data["admin_id"], data["admin_email"], "superadmin", data["tenant_id"])
    resp = await client.get("/api/v1/candidates", headers=_headers(token, data["tenant_id"]))
    assert resp.status_code == 200, resp.text
    assert resp.json()["total"] >= 1
