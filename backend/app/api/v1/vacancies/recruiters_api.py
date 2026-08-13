"""HTTP surface for the per-vacancy recruiter assignment pool.

``VacancyRecruiter`` m2m drives least-load / round-robin auto-assignment
(``assign_recruiter``). Until this surface existed, the pool was only
writable via SQL/seeds — the vacancy card had no UI.

Mounted as:
  GET  /api/v1/vacancies/{vacancy_id}/recruiters
  PUT  /api/v1/vacancies/{vacancy_id}/recruiters
"""

from __future__ import annotations

from typing import List, Optional, Tuple
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import and_, delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from backend.app.api.v1.utils.access import resolve_restricted_acl
from backend.app.api.v1.vacancies.repo import VacancyRepo
from backend.app.auth.deps import Role, UserCtx, get_current_user
from backend.app.auth.trust_role_deps import require_trust_write
from backend.app.db.deps import get_db_with_tenant
from backend.app.models.user import Role as UserRole
from backend.app.models.user import User
from backend.app.models.vacancy_recruiter import VacancyRecruiter
from backend.app.services.handoff import is_client_tenant_for_list
from backend.app.services.tenant_visibility import get_tenant_visibility

router = APIRouter()


class VacancyRecruiterItemOut(BaseModel):
    user_id: str
    full_name: Optional[str] = None
    email: Optional[str] = None
    weight: int = 1
    is_active: bool = True
    last_assigned_at: Optional[str] = None


class VacancyRecruitersOut(BaseModel):
    vacancy_id: str
    items: List[VacancyRecruiterItemOut] = Field(default_factory=list)


class VacancyRecruiterItemIn(BaseModel):
    user_id: UUID
    weight: int = Field(default=1, ge=1, le=100)
    is_active: bool = True


class VacancyRecruitersPut(BaseModel):
    """Full replace of the vacancy recruiter pool (idempotent)."""

    items: List[VacancyRecruiterItemIn] = Field(default_factory=list)


def _vacancy_allowed(vacancy_id: str, company_id: Optional[str], acl) -> bool:
    if acl is None:
        return True
    allowed_companies = set(acl.company_ids)
    allowed_vacancies = set(acl.vacancy_ids)
    if not allowed_companies and not allowed_vacancies:
        return False
    if company_id and company_id in allowed_companies:
        return True
    if vacancy_id in allowed_vacancies:
        return True
    return False


async def _load_vacancy_or_404(
    db: AsyncSession,
    tenant_id_str: str,
    vacancy_id_str: str,
    *,
    is_client: bool,
):
    vrepo = VacancyRepo(
        db,
        tenant_id_str,
        own_company_id=None,
        visibility=get_tenant_visibility(db, tenant_id_str),
        is_client_tenant=is_client,
    )
    vacancy = await vrepo.get(vacancy_id_str)
    if vacancy is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vacancy not found")
    return vacancy


async def _list_pool_items(
    db: AsyncSession,
    *,
    tenant_id: str,
    vacancy_id: str,
) -> List[VacancyRecruiterItemOut]:
    recruiter_alias = aliased(User)
    rows = await db.execute(
        select(
            VacancyRecruiter.user_id,
            VacancyRecruiter.weight,
            VacancyRecruiter.is_active,
            VacancyRecruiter.last_assigned_at,
            recruiter_alias.full_name,
            recruiter_alias.email,
        )
        .outerjoin(
            recruiter_alias,
            recruiter_alias.id == VacancyRecruiter.user_id,
        )
        .where(
            VacancyRecruiter.vacancy_id == vacancy_id,
            VacancyRecruiter.tenant_id == tenant_id,
        )
        .order_by(recruiter_alias.full_name.asc().nulls_last(), VacancyRecruiter.user_id.asc())
    )
    items: List[VacancyRecruiterItemOut] = []
    for row in rows.all():
        last_at = row.last_assigned_at
        items.append(
            VacancyRecruiterItemOut(
                user_id=str(row.user_id),
                full_name=row.full_name,
                email=row.email,
                weight=int(row.weight or 1),
                is_active=bool(row.is_active),
                last_assigned_at=last_at.isoformat() if last_at is not None else None,
            )
        )
    return items


@router.get(
    "/{vacancy_id}/recruiters",
    response_model=VacancyRecruitersOut,
    summary="List recruiters assigned to a vacancy (auto-assign pool)",
)
async def get_vacancy_recruiters(
    vacancy_id: UUID,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> VacancyRecruitersOut:
    db, tenant_id = db_tenant
    tenant_id_str = str(tenant_id)
    vacancy_id_str = str(vacancy_id)
    is_client = await is_client_tenant_for_list(db, tenant_id_str)
    vacancy = await _load_vacancy_or_404(db, tenant_id_str, vacancy_id_str, is_client=is_client)
    acl = await resolve_restricted_acl(db, tenant_id_str, current_user)
    if not is_client and not _vacancy_allowed(vacancy_id_str, getattr(vacancy, "company_id", None), acl):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    items = await _list_pool_items(db, tenant_id=tenant_id_str, vacancy_id=vacancy_id_str)
    return VacancyRecruitersOut(vacancy_id=vacancy_id_str, items=items)


@router.put(
    "/{vacancy_id}/recruiters",
    response_model=VacancyRecruitersOut,
    summary="Replace the vacancy recruiter auto-assign pool",
    dependencies=[Depends(require_trust_write())],
)
async def put_vacancy_recruiters(
    vacancy_id: UUID,
    payload: VacancyRecruitersPut,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> VacancyRecruitersOut:
    db, tenant_id = db_tenant
    tenant_id_str = str(tenant_id)
    vacancy_id_str = str(vacancy_id)
    is_client = await is_client_tenant_for_list(db, tenant_id_str)
    vacancy = await _load_vacancy_or_404(db, tenant_id_str, vacancy_id_str, is_client=is_client)
    acl = await resolve_restricted_acl(db, tenant_id_str, current_user)
    if not is_client and not _vacancy_allowed(vacancy_id_str, getattr(vacancy, "company_id", None), acl):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    # Deduplicate by user_id (last wins).
    by_user: dict[str, VacancyRecruiterItemIn] = {}
    for item in payload.items:
        by_user[str(item.user_id)] = item
    user_ids = sorted(by_user.keys())

    if user_ids:
        rows = await db.execute(
            select(User.id, User.role, User.is_active).where(
                User.id.in_(user_ids),
                User.is_active.is_(True),
                User.deleted_at.is_(None),
                User.role == UserRole.employee,
                or_(User.tenant_id.is_(None), User.tenant_id == tenant_id_str),
            )
        )
        valid_ids = {str(r.id) for r in rows.all()}
        missing = [uid for uid in user_ids if uid not in valid_ids]
        if missing:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    "Pool members must be active users with role=employee in this tenant. "
                    f"Invalid: {', '.join(missing)}"
                ),
            )

    # Preserve last_assigned_at for users that remain in the pool.
    existing_last: dict[str, object] = {}
    if user_ids:
        prev = await db.execute(
            select(VacancyRecruiter.user_id, VacancyRecruiter.last_assigned_at).where(
                VacancyRecruiter.vacancy_id == vacancy_id_str,
                VacancyRecruiter.tenant_id == tenant_id_str,
                VacancyRecruiter.user_id.in_(user_ids),
            )
        )
        existing_last = {str(r.user_id): r.last_assigned_at for r in prev.all()}

    await db.execute(
        delete(VacancyRecruiter).where(
            and_(
                VacancyRecruiter.vacancy_id == vacancy_id_str,
                VacancyRecruiter.tenant_id == tenant_id_str,
            )
        )
    )

    for uid, item in by_user.items():
        db.add(
            VacancyRecruiter(
                vacancy_id=vacancy_id_str,
                user_id=uid,
                tenant_id=tenant_id_str,
                weight=int(item.weight or 1),
                is_active=bool(item.is_active),
                last_assigned_at=existing_last.get(uid),  # type: ignore[arg-type]
            )
        )

    await db.commit()
    items = await _list_pool_items(db, tenant_id=tenant_id_str, vacancy_id=vacancy_id_str)
    return VacancyRecruitersOut(vacancy_id=vacancy_id_str, items=items)
