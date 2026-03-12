from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

from fastapi import HTTPException, status
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.deps import Role, UserCtx
from backend.app.models.access import UserCompanyAccess
from backend.app.models.candidate import Candidate
from backend.app.models.vacancy import Vacancy
from backend.app.models.user import User, Role as UserRole
from backend.app.services.tenant_visibility import get_tenant_visibility
from backend.app.services.handoff import is_client_tenant_for_list
from backend.app.api.v1.candidates.repo import _candidate_scope_clause


@dataclass
class CandidateACL:
    unrestricted: bool
    company_ids: set[str]
    vacancy_ids: set[str]
    manager_ids: set[str]

    @classmethod
    def unrestricted_scope(cls) -> "CandidateACL":
        return cls(True, set(), set(), set())

    @classmethod
    def restricted(
        cls,
        *,
        company_ids: Iterable[str],
        vacancy_ids: Iterable[str],
        manager_ids: Iterable[str],
    ) -> "CandidateACL":
        return cls(False, set(company_ids), set(vacancy_ids), set(manager_ids))

    def is_empty(self) -> bool:
        return not (self.company_ids or self.vacancy_ids or self.manager_ids)


async def resolve_candidate_acl(
    db: AsyncSession,
    tenant_id: str,
    user: UserCtx,
) -> CandidateACL:
    """Return access scope for the current user."""
    role = (user.role or "").strip().lower()
    user_id = (user.sub or "").strip()
    if not user_id:
        return CandidateACL.restricted(company_ids=[], vacancy_ids=[], manager_ids=[])

    # Получаем shared vacancies и companies для тенанта
    visibility = get_tenant_visibility(db, tenant_id)
    shared_vacancy_ids = visibility.shared_vacancy_ids
    shared_company_ids = visibility.shared_company_ids

    if role in (Role.administrator.value, Role.superadmin.value):
        return CandidateACL.unrestricted_scope()

    if role in (Role.supervisor.value, Role.manager.value):
        subordinate_rows = await db.execute(
            select(User.id)
            .where(User.tenant_id == tenant_id)
            .where(User.supervisor_id == user_id)
            .where(User.role == UserRole.recruiter)
            .where(User.deleted_at.is_(None))
            .where(User.is_active.is_(True))
        )
        subordinate_ids = {str(row[0]) for row in subordinate_rows if row[0]}
        manager_ids = subordinate_ids | {user_id}

        company_ids: set[str] = set()
        if manager_ids:
            access_rows = await db.execute(
                select(UserCompanyAccess.company_id)
                .where(UserCompanyAccess.tenant_id == tenant_id)
                .where(UserCompanyAccess.user_id.in_(manager_ids))
            )
            company_ids = {str(row[0]) for row in access_rows if row[0]}

        # Добавляем shared companies
        company_ids.update(shared_company_ids)

        vacancy_ids: set[str] = set()
        if company_ids:
            vacancy_rows = await db.execute(
                select(Vacancy.id)
                .where(Vacancy.tenant_id == tenant_id)
                .where(Vacancy.company_id.in_(company_ids))
            )
            vacancy_ids = {str(row[0]) for row in vacancy_rows if row[0]}

        # Добавляем shared vacancies
        vacancy_ids.update(shared_vacancy_ids)

        return CandidateACL.restricted(
            company_ids=company_ids,
            vacancy_ids=vacancy_ids,
            manager_ids=manager_ids,
        )

    if role in (
        Role.recruiter.value,
        Role.client_manager.value,
        Role.client_processor.value,
        Role.viewer.value,
    ):
        rows = await db.execute(
            select(UserCompanyAccess.company_id)
            .where(UserCompanyAccess.tenant_id == tenant_id)
            .where(UserCompanyAccess.user_id == user_id)
        )
        company_ids = {str(row[0]) for row in rows if row[0]}

        # Добавляем shared companies
        company_ids.update(shared_company_ids)

        vacancy_ids: set[str] = set()
        if company_ids:
            vacancy_rows = await db.execute(
                select(Vacancy.id)
                .where(Vacancy.tenant_id == tenant_id)
                .where(Vacancy.company_id.in_(company_ids))
            )
            vacancy_ids = {str(row[0]) for row in vacancy_rows if row[0]}

        # Добавляем shared vacancies
        vacancy_ids.update(shared_vacancy_ids)

        manager_scope = {user_id} if role == Role.recruiter.value else set()
        return CandidateACL.restricted(
            company_ids=company_ids,
            vacancy_ids=vacancy_ids,
            manager_ids=manager_scope,
        )

    # viewers и прочие без явного доступа получают пустой набор
    # Но все равно добавляем shared vacancies и companies для тенанта
    return CandidateACL.restricted(
        company_ids=list(shared_company_ids),
        vacancy_ids=list(shared_vacancy_ids),
        manager_ids=[],
    )


async def ensure_candidate_access(
    db: AsyncSession,
    tenant_id: str,
    candidate_id: str,
    user: UserCtx,
) -> None:
    """
    Raise 403 if the given user has no access to the candidate.

    ВАЖНО:
    - Для агентских тенантов сохраняем старую логику (Candidate.tenant_id == tenant_id + ACL),
      чтобы не расширять доступ сверх необходимого.
    - Для клиентских тенантов (company-tenant / tenant в TenantLink) используем тот же
      scope, что и списки/аналитика (_candidate_scope_clause с is_client_tenant=True),
      плюс при наличии ACL (UserCompanyAccess) дополняем условие company_id/vacancy_id.
      Это позволяет клиентским ролям (client_manager / client_processor) видеть тех же
      кандидатов, что и в списке, в т.ч. кандидатов агентства, переданных по handoff.
    """
    acl = await resolve_candidate_acl(db, tenant_id, user)
    if acl.unrestricted:
        return

    # Собираем ACL-условия
    ors = []
    if acl.manager_ids:
        ors.append(Candidate.manager.in_(acl.manager_ids))
    if acl.company_ids:
        ors.append(Candidate.company_id.in_(acl.company_ids))
    if acl.vacancy_ids:
        ors.append(Candidate.vacancy_id.in_(acl.vacancy_ids))

    # Определяем, является ли tenant клиентским (company / client_tenant в TenantLink)
    visibility = get_tenant_visibility(db, tenant_id)
    is_client = await is_client_tenant_for_list(db, tenant_id)

    if not is_client:
        # Агентский путь: сохраняем прежнюю модель безопасности — кандидат должен
        # принадлежать tenant'у и попадать под ACL.
        if not ors:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden for recruiter",
            )
        condition = ors[0] if len(ors) == 1 else or_(*ors)
        result = await db.execute(
            select(Candidate.id).where(
                and_(
                    Candidate.id == candidate_id,
                    Candidate.tenant_id == tenant_id,
                    Candidate.deleted_at.is_(None),
                    condition,
                )
            )
        )
        if result.scalar_one_or_none() is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden for recruiter",
            )
        return

    # Клиентский путь: базовый scope через _candidate_scope_clause, чтобы увидеть
    # тех же кандидатов, что и в списке (handoff + client-вакансии + own-tenant).
    scope_clause = _candidate_scope_clause(
        tenant_id,
        visibility,
        is_client_tenant=True,
    )

    conditions = [
        Candidate.id == candidate_id,
        Candidate.deleted_at.is_(None),
        scope_clause,
    ]

    # Если у пользователя есть явный ACL по компаниям/вакансиям — усиливаем условие.
    if ors:
        acl_condition = ors[0] if len(ors) == 1 else or_(*ors)
        conditions.append(acl_condition)

    result = await db.execute(
        select(Candidate.id).where(and_(*conditions))
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden for recruiter",
        )
