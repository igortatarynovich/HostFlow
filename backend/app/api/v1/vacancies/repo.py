from typing import Optional, Dict, Any
from sqlalchemy import select, delete, update, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.models import Candidate, Vacancy
from backend.app.models.company import Company, CandidateVacancy
from backend.app.models.candidate_profile import CandidateProfile
from backend.app.services.tenant_visibility import TenantVisibility

class VacancyRepo:
    def __init__(
        self,
        db: AsyncSession,
        tenant_id: str,
        *,
        own_company_id: str | None = None,
        visibility: TenantVisibility | None = None,
    ) -> None:
        self.db = db
        self.tenant_id = tenant_id
        self.own_company_id = own_company_id
        self.visibility = visibility or TenantVisibility(tenant_id=tenant_id)

    def _scope_clause(self):
        clauses = [Vacancy.tenant_id == self.tenant_id]
        shared_ids = getattr(self.visibility, "shared_vacancy_ids", set())
        if shared_ids:
            clauses.append(Vacancy.id.in_(shared_ids))
        return or_(*clauses)

    async def get(self, vacancy_id: str):
        # For single vacancy, we also load related data
        stmt = (
            select(
                Vacancy,
                Company.name.label("company_name"),
                CandidateProfile.id.label("candidate_profile_id"),
                CandidateProfile.name.label("candidate_profile_name"),
            )
            .where(
                Vacancy.id == vacancy_id,
                self._scope_clause(),
            )
            .join(Company, Company.id == Vacancy.company_id, isouter=True)
            .join(
                CandidateProfile,
                CandidateProfile.id == Vacancy.candidate_profile_id,
                isouter=True,
            )
        )
        if self.own_company_id:
            stmt = stmt.where(Vacancy.own_company_id == self.own_company_id)
        res = await self.db.execute(stmt)
        row = res.first()
        if row is None:
            return None
        # Return tuple for compatibility with service layer
        return row  # (Vacancy, company_name, candidate_profile_id, candidate_profile_name)

    async def list(
        self,
        *,
        company_id: Optional[str],
        status: Optional[str],
        search: Optional[str],
        candidate_profile_id: Optional[str] = None,
        limit: int,
        offset: int,
        order_by: Optional[str],
        descending: bool,
        allowed_company_ids: set[str] | None = None,
        allowed_vacancy_ids: set[str] | None = None,
    ):
        stmt = (
            select(
                Vacancy,
                Company.name.label("company_name"),
                CandidateProfile.id.label("candidate_profile_id"),
                CandidateProfile.name.label("candidate_profile_name"),
                func.count(Candidate.id).label("candidate_count"),
            )
            .where(self._scope_clause())
            .join(Company, Company.id == Vacancy.company_id, isouter=True)
            .join(
                CandidateProfile,
                CandidateProfile.id == Vacancy.candidate_profile_id,
                isouter=True,
            )
            .join(
                Candidate,
                (Candidate.vacancy_id == Vacancy.id)
                & (Candidate.deleted_at.is_(None)),
                isouter=True,
            )
            .group_by(Vacancy.id, Company.name, CandidateProfile.id, CandidateProfile.name)
        )
        if self.own_company_id:
            stmt = stmt.where(Vacancy.own_company_id == self.own_company_id)
        if company_id:
            stmt = stmt.where(Vacancy.company_id == company_id)
        if status:
            stmt = stmt.where(Vacancy.status == status)
        if search:
            stmt = stmt.where(Vacancy.title.ilike(f"%{search}%"))
        if candidate_profile_id:
            stmt = stmt.where(Vacancy.candidate_profile_id == candidate_profile_id)
        if allowed_company_ids is not None or allowed_vacancy_ids is not None:
            filters = []
            if allowed_company_ids:
                filters.append(Vacancy.company_id.in_(allowed_company_ids))
            if allowed_vacancy_ids:
                filters.append(Vacancy.id.in_(allowed_vacancy_ids))
            if not filters:
                return []
            stmt = stmt.where(or_(*filters))

        order_key = (order_by or "created_at").strip().lower()
        order_columns = {
            "created_at": Vacancy.created_at,
            "updated_at": Vacancy.updated_at,
            "title": Vacancy.title,
            "status": Vacancy.status,
        }
        order_column = order_columns.get(order_key, Vacancy.created_at)
        stmt = stmt.order_by(order_column.desc() if descending else order_column.asc())
        stmt = stmt.limit(limit).offset(offset)

        res = await self.db.execute(stmt)
        return res.all()  # [(Vacancy, company_name, candidate_profile_id, candidate_profile_name, candidate_count)]

    async def create(self, values: Dict[str, Any]) -> Vacancy:
        obj = Vacancy(**values)
        self.db.add(obj)
        await self.db.commit()
        await self.db.refresh(obj)
        return obj

    async def update(self, obj: Vacancy, values: Dict[str, Any]) -> Vacancy:
        await self.db.execute(
            update(Vacancy).where(Vacancy.id == obj.id).values(**values)
        )
        await self.db.commit()
        await self.db.refresh(obj)
        return obj

    async def delete(self, obj: Vacancy) -> None:
        await self.db.execute(delete(Vacancy).where(Vacancy.id == obj.id))
        await self.db.commit()

    async def has_linked_candidates(self, vacancy_id: str) -> bool:
        res = await self.db.execute(
            select(CandidateVacancy.id).where(
                CandidateVacancy.vacancy_id == vacancy_id,
                CandidateVacancy.tenant_id == self.tenant_id,
            ).limit(1)
        )
        return res.scalar_one_or_none() is not None
