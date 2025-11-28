from typing import List, Optional, Tuple
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from pydantic import BaseModel

from backend.app.auth.deps import Role, require_roles, get_current_user, UserCtx
from backend.app.api.v1.utils.access import resolve_restricted_acl
from backend.app.db.deps import get_db_with_tenant
from backend.app.models.candidate import Candidate
from backend.app.models.vacancy import Vacancy
from backend.app.models.mixins import now_utc as _now_utc
from backend.app.services.pipeline_sync import sync_candidate_links
from backend.app.constants.stages import pipeline_for_stage_code, STAGES_BY_GROUP

from .schemas import VacancyIn, VacancyOut, VacancyPatch
from .repo import VacancyRepo
from .service import VacancyService
from backend.app.services.tenant_visibility import get_tenant_visibility

router = APIRouter(prefix="/vacancies", tags=["vacancies"], redirect_slashes=False)
PIPELINE_ROLES = (Role.manager, Role.admin, Role.recruiter)


def _as_bool(value: Optional[str]) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"0", "false", "no", "off"}:
            return False
        if normalized in {"1", "true", "yes", "on"}:
            return True
    try:
        return bool(int(value))  # type: ignore[arg-type]
    except Exception:
        return bool(value)


def _svc(db_tenant: Tuple[AsyncSession, UUID]) -> VacancyService:
    db, tenant_id = db_tenant
    visibility = get_tenant_visibility(db, str(tenant_id))
    return VacancyService(VacancyRepo(db, str(tenant_id), visibility=visibility))


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

class VacancyCandidateLink(BaseModel):
    candidate_id: UUID

@router.get("/", response_model=List[VacancyOut])
@router.get("", response_model=List[VacancyOut], include_in_schema=False)
async def list_vacancies(
    company_id: Optional[UUID] = Query(None),
    status: Optional[str] = Query(None),
    q: Optional[str] = Query(None, description="search in title"),
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0),
    order_by: Optional[str] = Query("created_at"),
    desc: Optional[str] = Query("1", description="Accepts 1/0 or true/false for sort direction"),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
):
    # debug instrumentation (temporary) to observe incoming values
    logger = getattr(router, "_logger", None)
    if logger is None:
        import logging
        logger = logging.getLogger("backend.app.api.v1.vacancies")
        router._logger = logger  # type: ignore[attr-defined]
    logger.debug("list_vacancies query desc=%r", desc)
    svc = _svc(db_tenant)
    db, tenant_id = db_tenant
    acl = await resolve_restricted_acl(db, str(tenant_id), current_user)
    return await svc.list(
        company_id=str(company_id) if company_id else None,
        status=status,
        search=q,
        limit=limit,
        offset=offset,
        order_by=order_by,
        descending=_as_bool(desc),
        acl=acl,
    )

@router.get("/{vacancy_id}", response_model=VacancyOut)
async def get_vacancy(
    vacancy_id: UUID,
    db_tenant=Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
):
    svc = _svc(db_tenant)
    try:
        vacancy = await svc.get(str(vacancy_id))
    except LookupError:
        raise HTTPException(status_code=404, detail="Vacancy not found")
    db, tenant_id = db_tenant
    acl = await resolve_restricted_acl(db, str(tenant_id), current_user)
    if not _vacancy_allowed(vacancy.id, vacancy.company_id, acl):
        raise HTTPException(status_code=403, detail="Forbidden")
    return vacancy

@router.post("/", response_model=VacancyOut, dependencies=[Depends(require_roles(Role.manager, Role.admin))])
@router.post("", response_model=VacancyOut, dependencies=[Depends(require_roles(Role.manager, Role.admin))], include_in_schema=False)
async def create_vacancy(payload: VacancyIn, db_tenant=Depends(get_db_with_tenant)):
    svc = _svc(db_tenant)
    _db, tenant_id = db_tenant
    return await svc.create(str(tenant_id), payload)

@router.post(
    "/{vacancy_id}/candidates",
    dependencies=[Depends(require_roles(Role.manager, Role.admin))],
)
async def attach_candidate(
    vacancy_id: UUID,
    payload: VacancyCandidateLink,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
):
    db, tenant_id = db_tenant

    vacancy_row = await db.execute(
        select(Vacancy).where(Vacancy.id == str(vacancy_id), Vacancy.tenant_id == str(tenant_id))
    )
    vacancy = vacancy_row.scalar_one_or_none()
    if vacancy is None:
        raise HTTPException(status_code=404, detail="Vacancy not found")

    candidate_row = await db.execute(
        select(Candidate).where(
            Candidate.id == str(payload.candidate_id),
            Candidate.tenant_id == str(tenant_id),
            Candidate.deleted_at.is_(None),
        )
    )
    candidate = candidate_row.scalar_one_or_none()
    if candidate is None:
        raise HTTPException(status_code=404, detail="Candidate not found")

    await db.execute(
        update(Candidate)
        .where(Candidate.id == str(payload.candidate_id), Candidate.tenant_id == str(tenant_id))
        .values(
            vacancy_id=str(vacancy.id),
            company_id=str(getattr(vacancy, "company_id", None)) if getattr(vacancy, "company_id", None) else None,
            updated_at=_now_utc(),
        )
    )
    await db.commit()

    await sync_candidate_links(
        db=db,
        tenant_id=tenant_id,
        candidate_id=payload.candidate_id,
        candidate_stage=getattr(candidate, "stage", None),
    )

    return {
        "ok": True,
        "candidate_id": str(payload.candidate_id),
        "vacancy_id": str(vacancy.id),
        "company_id": str(getattr(vacancy, "company_id", "")) if getattr(vacancy, "company_id", None) else None,
    }

@router.get(
    "/{vacancy_id}/pipeline",
    dependencies=[Depends(require_roles(*PIPELINE_ROLES))],
)
async def get_vacancy_pipeline(
    vacancy_id: UUID,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
):
    db, tenant_id = db_tenant

    vacancy_row = await db.execute(
        select(Vacancy).where(Vacancy.id == str(vacancy_id), Vacancy.tenant_id == str(tenant_id))
    )
    vacancy = vacancy_row.scalar_one_or_none()
    if vacancy is None:
        raise HTTPException(status_code=404, detail="Vacancy not found")

    acl = await resolve_restricted_acl(db, str(tenant_id), current_user)
    if not _vacancy_allowed(str(vacancy.id), getattr(vacancy, "company_id", None), acl):
        raise HTTPException(status_code=403, detail="Forbidden")

    candidates = await db.execute(
        select(Candidate).where(
            Candidate.tenant_id == str(tenant_id),
            Candidate.vacancy_id == str(vacancy_id),
            Candidate.deleted_at.is_(None),
        )
    )
    rows = candidates.scalars().all()

    columns: dict[str, List[dict]] = {group: [] for group in STAGES_BY_GROUP.keys()}

    for cand in rows:
        stage_code = getattr(cand, "stage", None) or "new"
        column_key = pipeline_for_stage_code(stage_code)
        columns.setdefault(column_key, []).append(
            {
                "candidate_id": str(cand.id),
                "short_id": getattr(cand, "short_id", None),
                "name": f"{getattr(cand, 'first_name', '')} {getattr(cand, 'last_name', '')}".strip(),
                "email": getattr(cand, "email", None),
                "stage": stage_code,
            }
        )

    return {
        "vacancy_id": str(vacancy.id),
        "statuses": list(columns.keys()),
        "columns": columns,
    }

@router.patch("/{vacancy_id}", response_model=VacancyOut, dependencies=[Depends(require_roles(Role.manager, Role.admin))])
async def update_vacancy(vacancy_id: UUID, payload: VacancyPatch, db_tenant=Depends(get_db_with_tenant)):
    svc = _svc(db_tenant)
    try:
        return await svc.patch(str(vacancy_id), payload)
    except LookupError:
        raise HTTPException(status_code=404, detail="Vacancy not found")
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))

@router.delete("/{vacancy_id}", dependencies=[Depends(require_roles(Role.manager, Role.admin))])
async def delete_vacancy(vacancy_id: UUID, db_tenant=Depends(get_db_with_tenant)) -> Response:
    svc = _svc(db_tenant)
    try:
        await svc.delete(str(vacancy_id))
    except LookupError:
        raise HTTPException(status_code=404, detail="Vacancy not found")
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return Response(status_code=status.HTTP_204_NO_CONTENT)
