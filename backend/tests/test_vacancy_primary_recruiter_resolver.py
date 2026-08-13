"""Coverage for `services.recruiter_assignment.resolve_vacancy_primary_recruiter`.

Phase 2.6.G-5 Stage A guard — the helper replaces the silent dead-read of
``vacancy.recruiter_id`` (column never existed) in lead processing. We lock in
the cascade documented in ``docs/specs/manager-assignment.md`` §2.2:

    1. VacancyRecruiter m2m (active pool, role=recruiter) → least-load pick
    2. vacancy.manager (single primary owner, active user in tenant) → that id
    3. otherwise → ``None`` (caller decides further fallback)

One test per branch + two cross-branch precedence guards (active pool wins over
manager; inactive pool demotes to manager; manager pointing at inactive user
demotes to None). A ``vacancy=None`` smoke test guards the degenerate short
circuit (we call this from lead-processing where vacancy may not resolve).
"""

from __future__ import annotations

import uuid
from typing import Optional

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models import Company, User, Vacancy
from backend.app.models.user import Role as UserRole
from backend.app.models.vacancy_recruiter import VacancyRecruiter
from backend.app.services.recruiter_assignment import resolve_vacancy_primary_recruiter


pytestmark = pytest.mark.anyio


async def _any_company_id(db: AsyncSession, tenant_id: str) -> str:
    cid = await db.scalar(
        select(Company.id).where(Company.tenant_id == tenant_id).limit(1)
    )
    if cid is None:
        cid = str(uuid.uuid4())
        db.add(Company(id=cid, tenant_id=tenant_id, name="Primary Recruiter Test Co"))
        await db.flush()
    return str(cid)


async def _seed_recruiter(
    db: AsyncSession,
    *,
    tenant_id: str,
    is_active: bool = True,
    role: UserRole = UserRole.employee,
) -> str:
    uid = str(uuid.uuid4())
    db.add(
        User(
            id=uid,
            email=f"rec-{uid[:8]}@hostflow.test",
            password_hash="x",
            role=role,
            tenant_id=tenant_id,
            is_active=is_active,
            full_name=f"Recruiter {uid[:8]}",
            preferences={"preset_id": "recruiter"} if role == UserRole.employee else {},
        )
    )
    await db.flush()
    return uid


async def _seed_vacancy(
    db: AsyncSession,
    *,
    tenant_id: str,
    manager: Optional[str] = None,
) -> Vacancy:
    vid = str(uuid.uuid4())
    company_id = await _any_company_id(db, tenant_id)
    vacancy = Vacancy(
        id=vid,
        tenant_id=tenant_id,
        company_id=company_id,
        title=f"Vac {vid[:8]}",
        status="open",
        is_active=True,
        is_archived=False,
        manager=manager,
    )
    db.add(vacancy)
    await db.commit()
    return vacancy


async def _attach_pool_member(
    db: AsyncSession,
    *,
    tenant_id: str,
    vacancy_id: str,
    user_id: str,
    is_active: bool = True,
) -> None:
    db.add(
        VacancyRecruiter(
            vacancy_id=vacancy_id,
            user_id=user_id,
            tenant_id=tenant_id,
            is_active=is_active,
        )
    )
    await db.commit()


async def test_vacancy_none_returns_none(db: AsyncSession, tenant_id: str) -> None:
    """Degenerate input — resolver MUST NOT touch the session."""
    assert await resolve_vacancy_primary_recruiter(db, tenant_id, None) is None


async def test_empty_pool_no_manager_returns_none(
    db: AsyncSession, tenant_id: str
) -> None:
    """Cascade exhausts to None when neither m2m pool nor manager is set."""
    vacancy = await _seed_vacancy(db, tenant_id=tenant_id, manager=None)

    result = await resolve_vacancy_primary_recruiter(db, tenant_id, vacancy)

    assert result is None


async def test_manager_only_resolves_to_manager(
    db: AsyncSession, tenant_id: str
) -> None:
    """Branch 2 — no pool, manager points at active user → manager wins."""
    recruiter = await _seed_recruiter(db, tenant_id=tenant_id)
    vacancy = await _seed_vacancy(db, tenant_id=tenant_id, manager=recruiter)

    result = await resolve_vacancy_primary_recruiter(db, tenant_id, vacancy)

    assert result == recruiter


async def test_active_pool_picks_from_pool(
    db: AsyncSession, tenant_id: str
) -> None:
    """Branch 1 — active pool member exists, no manager → pool pick wins."""
    vacancy = await _seed_vacancy(db, tenant_id=tenant_id, manager=None)
    recruiter = await _seed_recruiter(db, tenant_id=tenant_id)
    await _attach_pool_member(
        db, tenant_id=tenant_id, vacancy_id=vacancy.id, user_id=recruiter
    )

    result = await resolve_vacancy_primary_recruiter(db, tenant_id, vacancy)

    assert result == recruiter


async def test_active_pool_beats_manager(
    db: AsyncSession, tenant_id: str
) -> None:
    """Precedence guard — pool pick trumps manager when both are set."""
    manager = await _seed_recruiter(db, tenant_id=tenant_id)
    pool_member = await _seed_recruiter(db, tenant_id=tenant_id)
    vacancy = await _seed_vacancy(db, tenant_id=tenant_id, manager=manager)
    await _attach_pool_member(
        db, tenant_id=tenant_id, vacancy_id=vacancy.id, user_id=pool_member
    )

    result = await resolve_vacancy_primary_recruiter(db, tenant_id, vacancy)

    assert result == pool_member
    assert result != manager


async def test_inactive_pool_demotes_to_manager(
    db: AsyncSession, tenant_id: str
) -> None:
    """Precedence guard — ``is_active=False`` pool rows are invisible; cascade
    falls through to ``vacancy.manager``."""
    manager = await _seed_recruiter(db, tenant_id=tenant_id)
    pool_member = await _seed_recruiter(db, tenant_id=tenant_id)
    vacancy = await _seed_vacancy(db, tenant_id=tenant_id, manager=manager)
    await _attach_pool_member(
        db,
        tenant_id=tenant_id,
        vacancy_id=vacancy.id,
        user_id=pool_member,
        is_active=False,
    )

    result = await resolve_vacancy_primary_recruiter(db, tenant_id, vacancy)

    assert result == manager


async def test_manager_pointing_at_inactive_user_returns_none(
    db: AsyncSession, tenant_id: str
) -> None:
    """Precedence guard — deactivated manager user MUST NOT be returned."""
    stale_user = await _seed_recruiter(db, tenant_id=tenant_id, is_active=False)
    vacancy = await _seed_vacancy(db, tenant_id=tenant_id, manager=stale_user)

    result = await resolve_vacancy_primary_recruiter(db, tenant_id, vacancy)

    assert result is None


async def test_manager_non_recruiter_role_still_resolves(
    db: AsyncSession, tenant_id: str
) -> None:
    """Manager-branch uses ``_load_active_user`` without role filter — any
    active user in the tenant counts (admin/supervisor can own a vacancy as
    primary-recruiter)."""
    admin = await _seed_recruiter(
        db, tenant_id=tenant_id, role=UserRole.administrator
    )
    vacancy = await _seed_vacancy(db, tenant_id=tenant_id, manager=admin)

    result = await resolve_vacancy_primary_recruiter(db, tenant_id, vacancy)

    assert result == admin
