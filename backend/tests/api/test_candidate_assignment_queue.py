"""Shared unassigned lead queue: assignment_state + claim (recruitment CRM)."""

from __future__ import annotations

import uuid
from unittest.mock import patch

import pytest
import sqlalchemy as sa
from sqlalchemy import desc, select

from backend.app.core.audit_events import AuditEventType
from backend.app.db.session import async_session_maker
from backend.app.models.audit import ActivityLog
from backend.app.models.user import Role as UserRole, User
from backend.tests.conftest import _build_token, _init_data, _set_tenant


async def _ensure_recruiter_company_access(
    session, *, tenant_id: str, recruiter_id: str
) -> str:
    row = await session.scalar(
        sa.text(
            """
            SELECT company_id FROM user_company_access
            WHERE user_id = :uid AND tenant_id = :tid LIMIT 1
            """
        ),
        {"uid": recruiter_id, "tid": tenant_id},
    )
    if row:
        return str(row)
    company_id = await session.scalar(
        sa.text("SELECT id FROM companies WHERE tenant_id = :tid LIMIT 1"),
        {"tid": tenant_id},
    )
    assert company_id is not None
    await session.execute(
        sa.text(
            """
            INSERT INTO user_company_access (id, tenant_id, user_id, company_id, can_edit)
            VALUES (:id, :tenant_id, :user_id, :company_id, TRUE)
            ON CONFLICT (tenant_id, user_id, company_id) DO NOTHING
            """
        ),
        {
            "id": str(uuid.uuid4()),
            "tenant_id": tenant_id,
            "user_id": recruiter_id,
            "company_id": company_id,
        },
    )
    return str(company_id)


@pytest.mark.anyio
async def test_create_company_only_is_unassigned_claim_marks_claimed(
    client,
    manager_headers,
    recruiter_headers,
    tenant_id,
):
    data = await _init_data()
    recruiter_id = str(data["recruiter_id"])
    async with async_session_maker() as session:
        await _set_tenant(session, tenant_id)
        company_id = await _ensure_recruiter_company_access(
            session, tenant_id=tenant_id, recruiter_id=recruiter_id
        )
        await session.commit()

    with patch(
        "backend.app.services.recruitment_lead_assignee.is_within_working_hours",
        return_value=True,
    ):
        resp = await client.post(
            "/api/v1/candidates",
            headers=manager_headers,
            json={
                "first_name": "Queue",
                "last_name": "Lead",
                "company_id": company_id,
            },
        )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body.get("assignment_state") == "unassigned"
    assert body.get("recruiter_id") in (None, "")
    cid = body["id"]

    claim = await client.post(
        f"/api/v1/candidates/{cid}/claim",
        headers=recruiter_headers,
    )
    assert claim.status_code == 200, claim.text
    out = claim.json()
    assert out.get("assignment_state") == "claimed"
    assert out.get("recruiter_id") == recruiter_id

    again = await client.post(
        f"/api/v1/candidates/{cid}/claim",
        headers=recruiter_headers,
    )
    assert again.status_code == 409


@pytest.mark.anyio
async def test_list_filter_assignment_state_unassigned(
    client,
    manager_headers,
    tenant_id,
):
    async with async_session_maker() as session:
        await _set_tenant(session, tenant_id)
        company_id = await session.scalar(
            sa.text("SELECT id FROM companies WHERE tenant_id = :tid LIMIT 1"),
            {"tid": tenant_id},
        )
        assert company_id is not None
        await session.commit()

    with patch(
        "backend.app.services.recruitment_lead_assignee.is_within_working_hours",
        return_value=True,
    ):
        resp = await client.post(
            "/api/v1/candidates",
            headers=manager_headers,
            json={
                "first_name": "Inbox",
                "last_name": "Filter",
                "company_id": str(company_id),
            },
        )
    assert resp.status_code == 200, resp.text
    cid = resp.json()["id"]

    listed = await client.get(
        "/api/v1/candidates",
        headers=manager_headers,
        params={"assignment_state": "unassigned", "limit": 200},
    )
    assert listed.status_code == 200, listed.text
    payload = listed.json()
    rows = payload.get("items") if isinstance(payload, dict) else payload
    ids = {row["id"] for row in rows}
    assert cid in ids


@pytest.mark.anyio
async def test_claim_forbidden_recruiter_outside_company_scope(
    client,
    manager_headers,
    tenant_id,
):
    """Recruiter without user_company_access for candidate company cannot claim."""
    async with async_session_maker() as session:
        await _set_tenant(session, tenant_id)
        outsider = User(
            id=str(uuid.uuid4()),
            email=f"outscope-{uuid.uuid4().hex[:8]}@hostflow.test",
            password_hash="x",
            role=UserRole.recruiter,
            tenant_id=tenant_id,
            is_active=True,
            full_name="Out of scope",
        )
        session.add(outsider)
        await session.flush()
        company_id = await session.scalar(
            sa.text("SELECT id FROM companies WHERE tenant_id = :tid LIMIT 1"),
            {"tid": tenant_id},
        )
        assert company_id is not None
        await session.commit()

    outsider_headers = {
        "Authorization": f"Bearer {_build_token(outsider.id, outsider.email, 'recruiter', tenant_id)}",
        "X-Tenant-Id": tenant_id,
    }

    with patch(
        "backend.app.services.recruitment_lead_assignee.is_within_working_hours",
        return_value=True,
    ):
        resp = await client.post(
            "/api/v1/candidates",
            headers=manager_headers,
            json={
                "first_name": "Scope",
                "last_name": "Wall",
                "company_id": str(company_id),
            },
        )
    assert resp.status_code == 200, resp.text
    cid = resp.json()["id"]

    denied = await client.post(
        f"/api/v1/candidates/{cid}/claim",
        headers=outsider_headers,
    )
    assert denied.status_code == 403, denied.text


@pytest.mark.anyio
async def test_lead_claimed_emits_audit_event(
    client,
    manager_headers,
    recruiter_headers,
    tenant_id,
):
    data = await _init_data()
    recruiter_id = str(data["recruiter_id"])
    async with async_session_maker() as session:
        await _set_tenant(session, tenant_id)
        company_id = await _ensure_recruiter_company_access(
            session, tenant_id=tenant_id, recruiter_id=recruiter_id
        )
        await session.commit()

    with patch(
        "backend.app.services.recruitment_lead_assignee.is_within_working_hours",
        return_value=True,
    ):
        resp = await client.post(
            "/api/v1/candidates",
            headers=manager_headers,
            json={
                "first_name": "Audit",
                "last_name": "Claim",
                "company_id": company_id,
            },
        )
    assert resp.status_code == 200, resp.text
    cid = resp.json()["id"]

    claim = await client.post(f"/api/v1/candidates/{cid}/claim", headers=recruiter_headers)
    assert claim.status_code == 200, claim.text

    async with async_session_maker() as session:
        await _set_tenant(session, tenant_id)
        row = await session.execute(
            select(ActivityLog.payload)
            .where(
                ActivityLog.tenant_id == tenant_id,
                ActivityLog.action == AuditEventType.lead_claimed.value,
                ActivityLog.target_id == cid,
            )
            .order_by(desc(ActivityLog.created_at))
            .limit(1)
        )
        raw = row.scalar_one_or_none()
        assert raw is not None
        pl = dict(raw) if isinstance(raw, dict) else {}
    assert pl.get("claimed_by") == recruiter_id
    assert pl.get("previous_recruiter_id") is None
