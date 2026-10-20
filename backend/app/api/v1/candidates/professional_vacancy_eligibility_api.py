"""Professional vacancy eligibility for one candidate and one vacancy.

The vacancy is part of the path. The response is not a candidate-level verdict.
"""

from __future__ import annotations

from typing import Any, Tuple
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.v1.candidates.acl import ensure_candidate_access, resolve_candidate_acl
from backend.app.auth.deps import UserCtx, get_current_user
from backend.app.auth.trust_role_deps import require_trust_read
from backend.app.db.deps import get_db_with_tenant
from backend.app.models.vacancy import Vacancy
from backend.app.services.professional_vacancy_eligibility import (
    ProfessionalVacancyEligibilityNotFound,
    load_professional_vacancy_eligibility,
)

router = APIRouter()


def _vacancy_visible(vacancy: Vacancy, acl) -> bool:
    if acl.unrestricted:
        return True
    company_id = str(vacancy.company_id or "")
    if company_id and company_id in acl.company_ids:
        return True
    return str(vacancy.id) in acl.vacancy_ids


@router.get(
    "/{candidate_id}/vacancies/{vacancy_id}/professional-eligibility",
    dependencies=[Depends(require_trust_read())],
    summary="Read professional eligibility for one candidate and one vacancy",
)
async def get_professional_vacancy_eligibility(
    candidate_id: UUID,
    vacancy_id: UUID,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> dict[str, Any]:
    db, tenant_id = db_tenant
    tenant_id_str = str(tenant_id)
    candidate_id_str = str(candidate_id)
    vacancy_id_str = str(vacancy_id)
    await ensure_candidate_access(db, tenant_id_str, candidate_id_str, current_user)
    vacancy = await db.scalar(
        select(Vacancy).where(
            Vacancy.id == vacancy_id_str,
            Vacancy.tenant_id == tenant_id_str,
        )
    )
    if vacancy is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    acl = await resolve_candidate_acl(db, tenant_id_str, current_user)
    if not _vacancy_visible(vacancy, acl):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    try:
        return await load_professional_vacancy_eligibility(
            db,
            tenant_id=tenant_id_str,
            candidate_id=candidate_id_str,
            vacancy_id=vacancy_id_str,
        )
    except ProfessionalVacancyEligibilityNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found") from exc
