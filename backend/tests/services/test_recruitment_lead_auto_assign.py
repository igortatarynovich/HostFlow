"""Recruitment auto-assign: company scope + availability (no supervisor/admin fallback)."""

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
from backend.app.models.vacancy import Vacancy
from backend.app.models.vacancy_recruiter import VacancyRecruiter
from backend.app.services.recruiter_assignment import assign_recruiter
from backend.app.services.recruitment_lead_assignee import (
    RECRUITMENT_AUTO_ASSIGN_OBSERVABILITY_SOURCE,
    RECRUITMENT_AUTO_ASSIGN_UNASSIGNED_REASON,
    user_id_eligible_as_available_recruiter_for_company,
)
from backend.tests.conftest import _set_tenant


pytestmark = pytest.mark.anyio


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


async def test_assign_recruiter_unassigned_when_pool_lacks_company_scope(
    tenant_id: str,
) -> None:
    """Recruiter on vacancy but no user_company_access for that company → unassigned."""
    async with async_session_maker() as session:
        await _set_tenant(session, tenant_id)
        lone = User(
            id=str(uuid.uuid4()),
            email=f"scoped-out-{uuid.uuid4().hex[:8]}@hostflow.test",
            password_hash="x",
            role=UserRole.recruiter,
            tenant_id=tenant_id,
            is_active=True,
            full_name="No Company Access",
        )
        session.add(lone)
        await session.flush()
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
                "title": "Scope test",
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
                "user_id": lone.id,
                "tenant_id": tenant_id,
                "weight": 1,
                "is_active": True,
            },
        )
        await session.commit()

    async with async_session_maker() as session:
        await _set_tenant(session, tenant_id)
        d = await assign_recruiter(
            db=session,
            tenant_id=tenant_id,
            vacancy_id=vacancy_id,
        )
        assert d.recruiter_id is None
        assert d.strategy == "unassigned"
        assert d.context.get("ineligibility_breakdown", {}).get("no_company_scope", 0) >= 1


async def test_assign_recruiter_unassigned_when_outside_working_hours(
    tenant_id: str,
) -> None:
    async with async_session_maker() as session:
        await _set_tenant(session, tenant_id)
        recruiter_id = await session.scalar(
            select(User.id).where(
                User.role == UserRole.recruiter,
                User.tenant_id == tenant_id,
                User.is_active.is_(True),
            ).limit(1)
        )
        assert recruiter_id is not None
        company_id = await _ensure_recruiter_company_access(
            session, tenant_id=tenant_id, recruiter_id=recruiter_id
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
                "title": "WH test",
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

    with patch(
        "backend.app.services.recruitment_lead_assignee.is_within_working_hours",
        return_value=False,
    ):
        async with async_session_maker() as session:
            await _set_tenant(session, tenant_id)
            d = await assign_recruiter(
                db=session,
                tenant_id=tenant_id,
                vacancy_id=vacancy_id,
            )
    assert d.recruiter_id is None
    assert d.strategy == "unassigned"


async def test_assign_recruiter_unassigned_when_canonical_paused(
    tenant_id: str,
) -> None:
    """Canonical ``recruiter_availability_states`` blocks auto-assign before working hours."""
    async with async_session_maker() as session:
        await _set_tenant(session, tenant_id)
        recruiter_id = await session.scalar(
            select(User.id).where(
                User.role == UserRole.recruiter,
                User.tenant_id == tenant_id,
                User.is_active.is_(True),
            ).limit(1)
        )
        assert recruiter_id is not None
        company_id = await _ensure_recruiter_company_access(
            session, tenant_id=tenant_id, recruiter_id=recruiter_id
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
                "title": "Availability state test",
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
        await session.execute(
            sa.text(
                """
                INSERT INTO recruiter_availability_states (id, tenant_id, user_id, state)
                VALUES (:id, :tenant_id, :user_id, 'paused')
                ON CONFLICT (tenant_id, user_id) DO UPDATE SET state = excluded.state
                """
            ),
            {
                "id": str(uuid.uuid4()),
                "tenant_id": tenant_id,
                "user_id": recruiter_id,
            },
        )
        await session.commit()

    with patch(
        "backend.app.services.recruitment_lead_assignee.is_within_working_hours",
        return_value=True,
    ):
        async with async_session_maker() as session:
            await _set_tenant(session, tenant_id)
            d = await assign_recruiter(
                db=session,
                tenant_id=tenant_id,
                vacancy_id=vacancy_id,
            )
    assert d.recruiter_id is None
    assert d.strategy == "unassigned"
    samples = d.context.get("ineligibility_samples") or []
    assert any(s.get("reason") == "availability_paused" for s in samples)


async def test_fallback_eligible_rejects_user_without_company_access(
    tenant_id: str,
) -> None:
    async with async_session_maker() as session:
        await _set_tenant(session, tenant_id)
        lone = User(
            id=str(uuid.uuid4()),
            email=f"fb-{uuid.uuid4().hex[:8]}@hostflow.test",
            password_hash="x",
            role=UserRole.recruiter,
            tenant_id=tenant_id,
            is_active=True,
            full_name="Fallback no scope",
        )
        session.add(lone)
        company_id = await session.scalar(sa.text("SELECT id FROM companies LIMIT 1"))
        await session.commit()

        ok, reason = await user_id_eligible_as_available_recruiter_for_company(
            session,
            tenant_id=tenant_id,
            company_id=str(company_id),
            user_id=lone.id,
        )
        assert ok is False
        assert reason == "no_company_scope"


@pytest.mark.anyio
async def test_candidate_create_unassigned_audit_payload(
    client,
    manager_headers,
    tenant_id: str,
) -> None:
    """No eligible recruiter → unassigned candidate + structured audit (operational decision)."""
    vacancy_id = str(uuid.uuid4())
    async with async_session_maker() as session:
        await _set_tenant(session, tenant_id)
        lone = User(
            id=str(uuid.uuid4()),
            email=f"audit-unassigned-{uuid.uuid4().hex[:8]}@hostflow.test",
            password_hash="x",
            role=UserRole.recruiter,
            tenant_id=tenant_id,
            is_active=True,
            full_name="Audit unassigned pool",
        )
        session.add(lone)
        await session.flush()
        company_id = await session.scalar(
            sa.text("SELECT id FROM companies WHERE tenant_id = :tid LIMIT 1"),
            {"tid": tenant_id},
        )
        assert company_id is not None
        session.add(
            Vacancy(
                id=vacancy_id,
                tenant_id=tenant_id,
                company_id=str(company_id),
                title="Audit unassigned vacancy",
                status="open",
                is_active=True,
                is_archived=False,
            )
        )
        session.add(
            VacancyRecruiter(
                vacancy_id=vacancy_id,
                user_id=str(lone.id),
                tenant_id=tenant_id,
                weight=1,
                is_active=True,
            )
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
                "first_name": "No",
                "last_name": "Assignee",
                "vacancy_id": vacancy_id,
            },
        )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body.get("recruiter_id") in (None, "")
    cand_id = str(body["id"])

    async with async_session_maker() as session:
        await _set_tenant(session, tenant_id)
        pl_row = await session.execute(
            select(ActivityLog.payload)
            .where(
                ActivityLog.tenant_id == tenant_id,
                ActivityLog.action == AuditEventType.recruitment_auto_assign_unassigned.value,
                ActivityLog.target_id == cand_id,
            )
            .order_by(desc(ActivityLog.created_at))
            .limit(1)
        )
        raw = pl_row.scalar_one_or_none()
        assert raw is not None
        pl = dict(raw) if isinstance(raw, dict) else {}

    assert pl.get("candidate_id") == cand_id
    assert pl.get("tenant_id") == tenant_id
    assert pl.get("vacancy_id") == vacancy_id
    assert pl.get("company_id") == str(company_id)
    assert pl.get("reason") == RECRUITMENT_AUTO_ASSIGN_UNASSIGNED_REASON
    assert pl.get("source") == RECRUITMENT_AUTO_ASSIGN_OBSERVABILITY_SOURCE
