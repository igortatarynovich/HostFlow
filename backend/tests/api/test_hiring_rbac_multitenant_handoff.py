"""RBAC: platform impersonation, cross-tenant headers, client tenant + accepted handoff."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Dict

import pytest
import pytest_asyncio
import sqlalchemy as sa
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.tests.api.test_tenant_isolation import TENANT_2_ID
from backend.tests.conftest import _build_token, _init_data, async_session_maker, hash_password


async def _set_tenant_context(session: AsyncSession, tenant_id: str) -> None:
    try:
        await session.execute(
            text("SELECT set_config('app.tenant_id', :tenant_id, false)"),
            {"tenant_id": tenant_id},
        )
    except Exception:
        pass


@pytest_asyncio.fixture
async def tenant2_isolation_bundle(tenant_id: str) -> Dict[str, str]:
    """Same shape as test_tenant_isolation.tenant2_data (local copy so single-file pytest collects it)."""
    tag = uuid.uuid4().hex[:10]
    user_email = f"admin2-{tag}@tenant2.test"
    short = ("A2" + tag)[:8].upper()

    async with async_session_maker() as session:
        await _set_tenant_context(session, TENANT_2_ID)

        user2_id = str(uuid.uuid4())
        await session.execute(
            text(
                """
                INSERT INTO users (
                    id, email, password_hash, role, tenant_id, short_id, full_name, is_active, preferences
                )
                VALUES (
                    :id, :email, :password_hash, :role, :tenant_id, :short_id, :full_name, :is_active, '{}'::jsonb
                )
                """
            ),
            {
                "id": user2_id,
                "email": user_email,
                "password_hash": "hash",
                "role": "administrator",
                "tenant_id": TENANT_2_ID,
                "short_id": short,
                "full_name": "Tenant 2 Admin",
                "is_active": True,
            },
        )

        company2_id = str(uuid.uuid4())
        await session.execute(
            text(
                """
                INSERT INTO companies (id, tenant_id, name, party_entity_type)
                VALUES (:id, :tenant_id, :name, 'company')
                """
            ),
            {
                "id": company2_id,
                "tenant_id": TENANT_2_ID,
                "name": "Tenant 2 Company",
            },
        )

        candidate2_id = str(uuid.uuid4())
        cand_ts = datetime.now(timezone.utc).replace(tzinfo=None)
        await session.execute(
            text(
                """
                INSERT INTO candidates (
                    id, tenant_id, first_name, last_name, manager, company_id, created_at, updated_at
                )
                VALUES (
                    :id, :tenant_id, :first_name, :last_name, :manager, :company_id, :created_at, :updated_at
                )
                """
            ),
            {
                "id": candidate2_id,
                "tenant_id": TENANT_2_ID,
                "first_name": "Tenant2",
                "last_name": "Candidate",
                "manager": user2_id,
                "company_id": company2_id,
                "created_at": cand_ts,
                "updated_at": cand_ts,
            },
        )

        await session.execute(
            text(
                """
                INSERT INTO user_memberships (id, user_id, tenant_id, role)
                VALUES (:id, :user_id, :tenant_id, :role)
                ON CONFLICT(user_id, tenant_id)
                DO UPDATE SET role = excluded.role
                """
            ),
            {
                "id": str(uuid.uuid4()),
                "user_id": user2_id,
                "tenant_id": TENANT_2_ID,
                "role": "administrator",
            },
        )

        await session.commit()

        return {
            "user_id": user2_id,
            "company_id": company2_id,
            "candidate_id": candidate2_id,
        }

PLATFORM_TENANTS = "/api/v1/platform/tenants"


def _headers(token: str, tenant_id: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "X-Tenant-Id": tenant_id,
        "Content-Type": "application/json",
    }


async def _ensure_agency_tenant_row(tenant_id: str, *, name: str, slug: str) -> None:
    """Second agency tenant must exist for FKs and platform impersonate."""
    async with async_session_maker() as session:
        await session.execute(
            sa.text(
                """
                INSERT INTO tenants (id, name, slug, api_key, is_active, type, status)
                VALUES (:id, :name, :slug, :api_key, true, 'agency', 'active')
                ON CONFLICT (id) DO NOTHING
                """
            ),
            {"id": tenant_id, "name": name, "slug": slug, "api_key": uuid.uuid4().hex[:32]},
        )
        await session.commit()


@pytest.mark.anyio
async def test_superadmin_impersonation_lists_target_tenant_candidates(
    client: AsyncClient,
    tenant2_isolation_bundle: dict[str, str],
) -> None:
    await _ensure_agency_tenant_row(
        TENANT_2_ID,
        name="RBAC isolation tenant 2",
        slug="rbac-tenant-2",
    )
    data = await _init_data()
    sa_token = _build_token(data["admin_id"], data["admin_email"], "superadmin", data["tenant_id"])
    h = {"Authorization": f"Bearer {sa_token}", "Content-Type": "application/json"}

    resp = await client.post(
        f"{PLATFORM_TENANTS}/{TENANT_2_ID}/impersonate",
        headers=h,
        json={"reason": "rbac-handoff-isolation-test"},
    )
    assert resp.status_code == 200, resp.text
    imp = resp.json()["token"]

    resp2 = await client.get(
        "/api/v1/candidates",
        headers=_headers(imp, TENANT_2_ID),
    )
    assert resp2.status_code == 200, resp2.text
    ids = {i["id"] for i in resp2.json().get("items", [])}
    assert tenant2_isolation_bundle["candidate_id"] in ids


@pytest.mark.anyio
async def test_recruiter_jwt_with_foreign_x_tenant_id_no_candidate_leak(
    client: AsyncClient,
    tenant2_isolation_bundle: dict[str, str],
) -> None:
    await _ensure_agency_tenant_row(
        TENANT_2_ID,
        name="RBAC isolation tenant 2",
        slug="rbac-tenant-2",
    )
    data = await _init_data()
    token = _build_token(
        data["recruiter_id"],
        data["recruiter_email"],
        "recruiter",
        data["tenant_id"],
        data.get("supervisor_id"),
    )
    headers = _headers(token, TENANT_2_ID)

    resp = await client.get("/api/v1/candidates", headers=headers)
    assert resp.status_code == 200, resp.text
    ids = {i["id"] for i in resp.json().get("items", [])}
    assert tenant2_isolation_bundle["candidate_id"] not in ids

    detail = await client.get(
        f"/api/v1/candidates/{tenant2_isolation_bundle['candidate_id']}",
        headers=headers,
    )
    assert detail.status_code in (403, 404)


@pytest.mark.anyio
async def test_client_manager_sees_accepted_handoff_candidate(
    client: AsyncClient,
) -> None:
    bootstrap = await _init_data()
    agency_tid = bootstrap["tenant_id"]
    agency_company_id = bootstrap["company_id"]
    admin_id = bootstrap["admin_id"]
    recruiter_id = bootstrap["recruiter_id"]

    client_tid = str(uuid.uuid4())
    suffix = uuid.uuid4().hex[:8]
    cm_id = str(uuid.uuid4())
    cm_email = f"cm-handoff-{suffix}@client.test"
    dedicated_cid = str(uuid.uuid4())
    marker = f"RBACHOF{suffix}"

    async with async_session_maker() as session:
        try:
            await session.execute(
                text("SELECT set_config('app.tenant_id', :tid, false)"),
                {"tid": agency_tid},
            )
        except Exception:
            pass

        await session.execute(
            sa.text(
                """
                INSERT INTO tenants (id, name, slug, api_key, is_active, type, status)
                VALUES (:id, :name, :slug, :api_key, true, 'company', 'active')
                """
            ),
            {
                "id": client_tid,
                "name": f"RBAC Client Co {suffix}",
                "slug": f"rbac-cl-{suffix}",
                "api_key": uuid.uuid4().hex[:32],
            },
        )

        await session.execute(
            sa.text(
                """
                INSERT INTO users (
                    id, email, password_hash, role, tenant_id, short_id, full_name, is_active, preferences
                )
                VALUES (
                    :id, :email, :password_hash, :role, :tenant_id, :short_id, :full_name, :is_active, '{}'::jsonb
                )
                """
            ),
            {
                "id": cm_id,
                "email": cm_email,
                "password_hash": hash_password("Client123!"),
                # Postgres `role` enum may omit client_manager; JWT carries hiring role for ACL.
                "role": "viewer",
                "tenant_id": client_tid,
                "short_id": ("CM" + suffix)[:8].upper(),
                "full_name": "Client Manager RBAC",
                "is_active": True,
            },
        )

        await session.execute(
            sa.text(
                """
                INSERT INTO user_memberships (id, user_id, tenant_id, role)
                VALUES (:id, :user_id, :tenant_id, :role)
                ON CONFLICT(user_id, tenant_id) DO UPDATE SET role = excluded.role
                """
            ),
            {
                "id": str(uuid.uuid4()),
                "user_id": cm_id,
                "tenant_id": client_tid,
                "role": "client_manager",
            },
        )

        link_id = str(uuid.uuid4())
        await session.execute(
            sa.text(
                """
                INSERT INTO tenant_links (
                    id, agency_tenant_id, client_tenant_id, handoff_include_company_id,
                    status, features_json, created_at, updated_at
                )
                VALUES (
                    :id, :agency_tid, :client_tid, :handoff_company,
                    'active', CAST(:features AS jsonb), NOW(), NOW()
                )
                """
            ),
            {
                "id": link_id,
                "agency_tid": agency_tid,
                "client_tid": client_tid,
                "handoff_company": agency_company_id,
                "features": '{"handoff_enabled": true}',
            },
        )

        cand_ts = datetime.now(timezone.utc).replace(tzinfo=None)
        ho_now = datetime.now(timezone.utc)
        await session.execute(
            sa.text(
                """
                INSERT INTO candidates (
                    id, tenant_id, first_name, last_name, manager, company_id, created_at, updated_at
                )
                VALUES (
                    :id, :tenant_id, :first_name, :last_name, :manager, :company_id, :c_at, :u_at
                )
                """
            ),
            {
                "id": dedicated_cid,
                "tenant_id": agency_tid,
                "first_name": marker,
                "last_name": "HandoffProbe",
                "manager": recruiter_id,
                "company_id": agency_company_id,
                "c_at": cand_ts,
                "u_at": cand_ts,
            },
        )

        ho_id = str(uuid.uuid4())
        await session.execute(
            sa.text(
                """
                INSERT INTO candidate_handoffs (
                    id, candidate_id, agency_tenant_id, client_tenant_id,
                    requested_by_user_id, requested_at, status,
                    reviewed_by_user_id, reviewed_at, created_at, updated_at
                )
                VALUES (
                    :id, :cid, :agency_tid, :client_tid,
                    :req_by, :req_at, 'accepted',
                    :rev_by, :rev_at, :req_at, :req_at
                )
                """
            ),
            {
                "id": ho_id,
                "cid": dedicated_cid,
                "agency_tid": agency_tid,
                "client_tid": client_tid,
                "req_by": admin_id,
                "req_at": ho_now,
                "rev_by": admin_id,
                "rev_at": ho_now,
            },
        )

        await session.commit()

    cm_token = _build_token(cm_id, cm_email, "client_manager", client_tid)

    lst = await client.get(
        "/api/v1/candidates",
        headers=_headers(cm_token, client_tid),
        params={"q": marker, "limit": 20},
    )
    assert lst.status_code == 200, lst.text
    listed = {i["id"] for i in lst.json().get("items", [])}
    assert dedicated_cid in listed

    one = await client.get(
        f"/api/v1/candidates/{dedicated_cid}",
        headers=_headers(cm_token, client_tid),
    )
    assert one.status_code == 200, one.text
    assert one.json().get("id") == dedicated_cid
