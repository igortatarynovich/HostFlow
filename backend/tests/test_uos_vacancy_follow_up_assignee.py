"""G-5 Stage B guard — `ensure_vacancy_recruiting_follow_up_task` assigns the
follow-up reminder to the vacancy's *primary recruiter* (resolved through the
canonical helper), not just the raw ``vacancy.manager`` column.

Before Stage B the helper read ``vacancy.manager`` directly and fell back to
``actor_id`` when it was ``NULL`` — a vacancy whose ownership was expressed
through the ``VacancyRecruiter`` m2m pool (and not the legacy ``manager``
field) would end up with its auto-generated pipeline task assigned to whoever
flipped the stage (usually an admin). After Stage B the resolver picks the
pool member first, the manager second, and only falls through to ``actor_id``
when both are empty.

We exercise the service directly (no HTTP) and inspect the created
``Reminder.assignee_id`` for three representative cascade positions.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models import Company, User, Vacancy
from backend.app.models.reminder import Reminder
from backend.app.models.user import Role as UserRole
from backend.app.models.vacancy_recruiter import VacancyRecruiter
from backend.app.services.uos_auto_activities import (
    ensure_vacancy_recruiting_follow_up_task,
)


pytestmark = pytest.mark.anyio


async def _any_company_id(db: AsyncSession, tenant_id: str) -> str:
    cid = await db.scalar(
        select(Company.id).where(Company.tenant_id == tenant_id).limit(1)
    )
    if cid is None:
        cid = str(uuid.uuid4())
        db.add(Company(id=cid, tenant_id=tenant_id, name="UOS Vacancy Follow-up Test Co"))
        await db.flush()
    return str(cid)


async def _seed_recruiter(
    db: AsyncSession,
    *,
    tenant_id: str,
    role: UserRole = UserRole.employee,
) -> str:
    uid = str(uuid.uuid4())
    db.add(
        User(
            id=uid,
            email=f"uos-rec-{uid[:8]}@hostflow.test",
            password_hash="x",
            role=role,
            tenant_id=tenant_id,
            is_active=True,
            full_name=f"Recruiter {uid[:8]}",
        )
    )
    await db.flush()
    return uid


async def _seed_actor_admin(
    db: AsyncSession,
    *,
    tenant_id: str,
) -> str:
    """The user who flips the vacancy into recruiting — the historical
    fallback for ``assignee_id`` when ``vacancy.manager`` was NULL."""
    return await _seed_recruiter(db, tenant_id=tenant_id, role=UserRole.administrator)


async def _seed_open_vacancy(
    db: AsyncSession,
    *,
    tenant_id: str,
    manager: str | None = None,
) -> Vacancy:
    vid = str(uuid.uuid4())
    company_id = await _any_company_id(db, tenant_id)
    vacancy = Vacancy(
        id=vid,
        tenant_id=tenant_id,
        company_id=company_id,
        title=f"UOS Vac {vid[:8]}",
        status="open",
        is_active=True,
        is_archived=False,
        manager=manager,
    )
    db.add(vacancy)
    await db.commit()
    return vacancy


async def _load_follow_up_assignee(
    db: AsyncSession, *, tenant_id: str, vacancy_id: str
) -> str | None:
    row = await db.scalar(
        select(Reminder.assignee_id).where(
            Reminder.tenant_id == tenant_id,
            Reminder.entity_type == "vacancy",
            Reminder.entity_id == vacancy_id,
            Reminder.type == "uos_vacancy_recruiting_follow_up",
        )
    )
    return row


async def test_follow_up_uses_m2m_pool_when_manager_null(
    db: AsyncSession, tenant_id: str
) -> None:
    """Pre-Stage-B bug: with ``manager=NULL`` the helper returned ``act``
    even though the vacancy had a populated recruiter pool. Guard: pool
    member MUST own the auto-task."""
    vacancy = await _seed_open_vacancy(db, tenant_id=tenant_id, manager=None)
    recruiter = await _seed_recruiter(db, tenant_id=tenant_id)
    admin_actor = await _seed_actor_admin(db, tenant_id=tenant_id)
    db.add(
        VacancyRecruiter(
            vacancy_id=vacancy.id,
            user_id=recruiter,
            tenant_id=tenant_id,
            is_active=True,
        )
    )
    await db.commit()

    await ensure_vacancy_recruiting_follow_up_task(
        db,
        tenant_id,
        admin_actor,
        vacancy,
        was_recruiting_before=False,
    )

    assignee = await _load_follow_up_assignee(
        db, tenant_id=tenant_id, vacancy_id=vacancy.id
    )
    assert assignee == recruiter, (
        "Stage B regression: pool member should have won over actor fallback"
    )
    assert assignee != admin_actor


async def test_follow_up_uses_manager_when_no_pool(
    db: AsyncSession, tenant_id: str
) -> None:
    """Second cascade slot — manager wins when pool is empty."""
    manager = await _seed_recruiter(db, tenant_id=tenant_id)
    vacancy = await _seed_open_vacancy(db, tenant_id=tenant_id, manager=manager)
    admin_actor = await _seed_actor_admin(db, tenant_id=tenant_id)

    await ensure_vacancy_recruiting_follow_up_task(
        db,
        tenant_id,
        admin_actor,
        vacancy,
        was_recruiting_before=False,
    )

    assignee = await _load_follow_up_assignee(
        db, tenant_id=tenant_id, vacancy_id=vacancy.id
    )
    assert assignee == manager
    assert assignee != admin_actor


async def test_follow_up_falls_back_to_actor_when_no_owner(
    db: AsyncSession, tenant_id: str
) -> None:
    """Third cascade slot — no pool, no manager → legacy ``act`` fallback
    preserves the historical behaviour so the reminder is never orphaned."""
    vacancy = await _seed_open_vacancy(db, tenant_id=tenant_id, manager=None)
    admin_actor = await _seed_actor_admin(db, tenant_id=tenant_id)

    await ensure_vacancy_recruiting_follow_up_task(
        db,
        tenant_id,
        admin_actor,
        vacancy,
        was_recruiting_before=False,
    )

    assignee = await _load_follow_up_assignee(
        db, tenant_id=tenant_id, vacancy_id=vacancy.id
    )
    assert assignee == admin_actor


async def test_follow_up_pool_beats_manager(
    db: AsyncSession, tenant_id: str
) -> None:
    """Precedence guard — when BOTH the pool and ``vacancy.manager`` are
    set, the m2m pool wins (mirrors :func:`assign_recruiter`'s ``least_load``
    strategy)."""
    manager = await _seed_recruiter(db, tenant_id=tenant_id)
    pool_member = await _seed_recruiter(db, tenant_id=tenant_id)
    vacancy = await _seed_open_vacancy(db, tenant_id=tenant_id, manager=manager)
    admin_actor = await _seed_actor_admin(db, tenant_id=tenant_id)
    db.add(
        VacancyRecruiter(
            vacancy_id=vacancy.id,
            user_id=pool_member,
            tenant_id=tenant_id,
            is_active=True,
        )
    )
    await db.commit()

    await ensure_vacancy_recruiting_follow_up_task(
        db,
        tenant_id,
        admin_actor,
        vacancy,
        was_recruiting_before=False,
    )

    assignee = await _load_follow_up_assignee(
        db, tenant_id=tenant_id, vacancy_id=vacancy.id
    )
    assert assignee == pool_member
    assert assignee != manager
    assert assignee != admin_actor
