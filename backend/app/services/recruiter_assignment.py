from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from backend.app.constants.stages import TERMINAL_STATUSES
from backend.app.models import Candidate, Vacancy, VacancyRecruiter
from backend.app.models.access import UserCompanyAccess
from backend.app.models.user import Role as UserRole, User


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class AssignmentDecision:
    recruiter_id: Optional[str]
    strategy: str
    context: Dict[str, Any] = field(default_factory=dict)

    @property
    def assigned(self) -> bool:
        return bool(self.recruiter_id)


async def _load_vacancy(
    db: AsyncSession,
    tenant_id: str,
    vacancy_id: Optional[str],
) -> Optional[Vacancy]:
    if not vacancy_id:
        return None
    row = await db.execute(
        select(Vacancy).where(
            Vacancy.id == vacancy_id,
            Vacancy.tenant_id == tenant_id,
        )
    )
    return row.scalar_one_or_none()


async def _load_active_user(
    db: AsyncSession,
    tenant_id: str,
    user_id: Optional[str],
    *,
    allowed_roles: Optional[Sequence[UserRole]] = None,
) -> Optional[User]:
    if not user_id:
        return None
    stmt = select(User).where(
        User.id == user_id,
        User.is_active.is_(True),
        or_(User.tenant_id.is_(None), User.tenant_id == tenant_id),
    )
    if allowed_roles:
        stmt = stmt.where(User.role.in_(list(allowed_roles)))
    row = await db.execute(stmt)
    return row.scalar_one_or_none()


async def _fetch_candidate_loads(
    db: AsyncSession,
    tenant_id: str,
    recruiter_ids: Iterable[str],
) -> Dict[str, int]:
    ids = {rid for rid in recruiter_ids if rid}
    if not ids:
        return {}
    stmt = (
        select(Candidate.recruiter_id, func.count())
        .where(
            Candidate.tenant_id == tenant_id,
            Candidate.recruiter_id.in_(sorted(ids)),
        )
        .group_by(Candidate.recruiter_id)
    )
    if TERMINAL_STATUSES:
        stmt = stmt.where(~Candidate.status.in_(list(TERMINAL_STATUSES)))
    rows = await db.execute(stmt)
    return {str(rid): int(total or 0) for rid, total in rows.all()}


def _choose_by_score(
    pool: Sequence[Dict[str, Any]],
    loads: Dict[str, int],
    *,
    default_weight: int = 1,
) -> Optional[Dict[str, Any]]:
    scored: List[Tuple[float, int, datetime, str, Dict[str, Any]]] = []
    for entry in pool:
        recruiter_id = entry["user_id"]
        weight = entry.get("weight") or default_weight
        load = loads.get(recruiter_id, 0)
        score = weight / max(1, load)
        last_assigned_at: Optional[datetime] = entry.get("last_assigned_at")
        # Treat NULL last_assigned as the earliest possible timestamp
        rotation_marker = last_assigned_at or datetime.fromtimestamp(0, tz=timezone.utc)
        scored.append((score, load, rotation_marker, recruiter_id, entry))

    if not scored:
        return None

    scored.sort(
        key=lambda item: (
            -item[0],             # prefer higher score
            item[1],              # then lower load
            item[2],              # then oldest assignment (round-robin)
            item[3],              # deterministic tie breaker
        )
    )
    return scored[0][-1]


async def _prepare_vacancy_pool(
    db: AsyncSession,
    tenant_id: str,
    vacancy_id: str,
) -> List[Dict[str, Any]]:
    recruiter_alias = aliased(User)
    rows = await db.execute(
        select(
            VacancyRecruiter.user_id,
            VacancyRecruiter.weight,
            VacancyRecruiter.last_assigned_at,
            recruiter_alias.full_name,
            recruiter_alias.short_id,
        )
        .join(
            recruiter_alias,
            and_(
                recruiter_alias.id == VacancyRecruiter.user_id,
                recruiter_alias.is_active.is_(True),
                recruiter_alias.role == UserRole.recruiter,
                or_(
                    recruiter_alias.tenant_id.is_(None),
                    recruiter_alias.tenant_id == tenant_id,
                ),
            ),
        )
        .where(
            VacancyRecruiter.vacancy_id == vacancy_id,
            VacancyRecruiter.tenant_id == tenant_id,
            VacancyRecruiter.is_active.is_(True),
        )
    )
    return [
        {
            "user_id": row.user_id,
            "weight": row.weight,
            "last_assigned_at": row.last_assigned_at,
            "full_name": row.full_name,
            "short_id": row.short_id,
        }
        for row in rows.all()
    ]


async def _prepare_company_supervisors(
    db: AsyncSession,
    tenant_id: str,
    company_id: Optional[str],
) -> List[Dict[str, Any]]:
    if not company_id:
        return []
    user_alias = aliased(User)
    rows = await db.execute(
        select(
            user_alias.id,
            user_alias.full_name,
            user_alias.short_id,
            user_alias.role,
        )
        .join(
            UserCompanyAccess,
            and_(
                UserCompanyAccess.user_id == user_alias.id,
                UserCompanyAccess.company_id == company_id,
                UserCompanyAccess.tenant_id == tenant_id,
            ),
        )
        .where(
            user_alias.is_active.is_(True),
            user_alias.role.in_([UserRole.supervisor, UserRole.administrator]),
            or_(
                user_alias.tenant_id.is_(None),
                user_alias.tenant_id == tenant_id,
            ),
        )
    )
    return [
        {
            "user_id": row.id,
            "full_name": row.full_name,
            "short_id": row.short_id,
            "role": row.role.value if hasattr(row.role, "value") else str(row.role),
        }
        for row in rows.all()
    ]


async def _prepare_tenant_admins(db: AsyncSession, tenant_id: str) -> List[Dict[str, Any]]:
    rows = await db.execute(
        select(User.id, User.full_name, User.short_id)
        .where(
            User.tenant_id == tenant_id,
            User.role == UserRole.administrator,
            User.is_active.is_(True),
        )
    )
    return [
        {
            "user_id": row.id,
            "full_name": row.full_name,
            "short_id": row.short_id,
        }
        for row in rows.all()
    ]


async def assign_recruiter(
    db: AsyncSession,
    *,
    tenant_id: str,
    vacancy_id: Optional[str] = None,
    company_id: Optional[str] = None,
) -> AssignmentDecision:
    decision_context: Dict[str, Any] = {}
    vacancy = await _load_vacancy(db, tenant_id, vacancy_id)
    if vacancy:
        decision_context["vacancy_id"] = vacancy.id
        company_id = vacancy.company_id or company_id
    if company_id:
        decision_context["company_id"] = company_id

    if vacancy_id:
        pool = await _prepare_vacancy_pool(db, tenant_id, vacancy_id)
        decision_context["pool_size"] = len(pool)
        if pool:
            loads = await _fetch_candidate_loads(db, tenant_id, (p["user_id"] for p in pool))
            choice = _choose_by_score(pool, loads)
            if choice:
                await db.execute(
                    update(VacancyRecruiter)
                    .where(
                        VacancyRecruiter.vacancy_id == vacancy_id,
                        VacancyRecruiter.user_id == choice["user_id"],
                        VacancyRecruiter.tenant_id == tenant_id,
                    )
                    .values(last_assigned_at=_now_utc())
                )
                decision_context["strategy"] = "least_load"
                decision_context["loads"] = loads
                decision_context["selected"] = choice
                return AssignmentDecision(
                    recruiter_id=choice["user_id"],
                    strategy="least_load",
                    context=decision_context,
                )

    owner = await _load_active_user(db, tenant_id, getattr(vacancy, "manager", None))
    if owner:
        decision_context["strategy"] = "vacancy_owner"
        decision_context["selected"] = {"user_id": owner.id}
        return AssignmentDecision(
            recruiter_id=owner.id,
            strategy="vacancy_owner",
            context=decision_context,
        )

    supervisors = await _prepare_company_supervisors(db, tenant_id, company_id)
    if supervisors:
        loads = await _fetch_candidate_loads(db, tenant_id, (s["user_id"] for s in supervisors))
        choice = _choose_by_score(supervisors, loads)
        if choice:
            decision_context["strategy"] = "company_supervisor"
            decision_context["loads"] = loads
            decision_context["selected"] = choice
            return AssignmentDecision(
                recruiter_id=choice["user_id"],
                strategy="company_supervisor",
                context=decision_context,
            )

    admins = await _prepare_tenant_admins(db, tenant_id)
    if admins:
        loads = await _fetch_candidate_loads(db, tenant_id, (a["user_id"] for a in admins))
        choice = _choose_by_score(admins, loads)
        if choice:
            decision_context["strategy"] = "tenant_admin"
            decision_context["loads"] = loads
            decision_context["selected"] = choice
            return AssignmentDecision(
                recruiter_id=choice["user_id"],
                strategy="tenant_admin",
                context=decision_context,
            )

    decision_context["strategy"] = "unassigned"
    return AssignmentDecision(
        recruiter_id=None,
        strategy="unassigned",
        context=decision_context,
    )
