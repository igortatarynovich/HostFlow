from typing import List, Optional, Tuple
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func
from pydantic import BaseModel

from backend.app.auth.trust_role_deps import require_trust_admin, require_trust_read, require_trust_write
from backend.app.auth.deps import Role, get_current_user, UserCtx
from backend.app.api.v1.utils.access import resolve_restricted_acl
from backend.app.db.deps import get_db_with_tenant
from backend.app.models.candidate import Candidate
from backend.app.models.vacancy import Vacancy
from backend.app.models.candidate_profile import CandidateProfile
from backend.app.models.mixins import now_utc as _now_utc
from backend.app.services.pipeline_sync import sync_candidate_links
from backend.app.constants.stages import pipeline_for_stage_code, STAGES_BY_GROUP
from backend.app.api.v1.candidate_documents import apply_template_to_candidate_impl

from .schemas import VacancyIn, VacancyOut, VacancyPatch
from .mappers import vacancy_to_out
from backend.app.models.company import Company
from .repo import VacancyRepo
from .service import VacancyService
from backend.app.services import billing_restrictions
from backend.app.services.tenant_visibility import get_tenant_visibility
from backend.app.services.handoff import is_client_tenant_for_list, is_client_tenant, can_client_edit
from backend.app.services.recruitment_handoff_write_guard import require_agency_recruitment_write_allowed
from backend.app.api.v1.utils.own_company import (
    resolve_active_own_company_id,
    resolve_active_own_company_id_optional,
)

router = APIRouter(prefix="/vacancies", tags=["vacancies"], redirect_slashes=False)
from backend.app.auth.trust_role_deps import TRUST_WRITE_ROLES, require_trust_write
PIPELINE_ROLES = TRUST_WRITE_ROLES

# G-8 stage 2.1: per-vacancy "what to do next" CTA. Mounted as a sub-router
# so the implementation lives in a small, single-purpose file. Must be
# included BEFORE the inline `@router.get("/{vacancy_id}")` below — Starlette
# matches in registration order and `/{vacancy_id}` would otherwise swallow
# `/{vacancy_id}/next-action` and force FastAPI to validate the literal
# string `next-action` as a UUID.
from backend.app.api.v1.vacancies import next_action_api as _next_action_api  # noqa: E402
from backend.app.api.v1.vacancies import recruiters_api as _recruiters_api  # noqa: E402

router.include_router(_next_action_api.router)
router.include_router(_recruiters_api.router)

from backend.app.api.v1.vacancies import launch_search_setup_api as _launch_search_setup_api  # noqa: E402
from backend.app.api.v1.vacancies import workspace_api as _workspace_api  # noqa: E402
from backend.app.api.v1.vacancies import acquisition_api as _acquisition_api  # noqa: E402

router.include_router(_launch_search_setup_api.router)
router.include_router(_workspace_api.router)
router.include_router(_acquisition_api.router)


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


def _svc(
    db_tenant: Tuple[AsyncSession, UUID],
    *,
    own_company_id: str | None = None,
    is_client_tenant: bool = False,
) -> VacancyService:
    db, tenant_id = db_tenant
    visibility = get_tenant_visibility(db, str(tenant_id))
    return VacancyService(
        VacancyRepo(
            db,
            str(tenant_id),
            own_company_id=own_company_id,
            visibility=visibility,
            is_client_tenant=is_client_tenant,
        )
    )


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


async def _require_can_reassign_candidate_to_vacancy(
    db: AsyncSession,
    *,
    tenant_id_str: str,
    candidate_id: str,
) -> None:
    """Block vacancy reassignment when recruitment is locked (post-handoff dossier)."""
    if await is_client_tenant(db, tenant_id_str):
        if not await can_client_edit(db, candidate_id, tenant_id_str):
            raise HTTPException(status_code=403, detail="Cannot assign candidate: no accepted handoff")
    else:
        await require_agency_recruitment_write_allowed(
            db,
            agency_tenant_id=tenant_id_str,
            candidate_id=candidate_id,
            bypass=None,
        )

@router.get("/", response_model=List[VacancyOut])
@router.get("", response_model=List[VacancyOut], include_in_schema=False)
async def list_vacancies(
    company_id: Optional[UUID] = Query(None),
    status: Optional[str] = Query(None),
    candidate_profile_id: Optional[UUID] = Query(None, description="Filter by candidate profile ID"),
    q: Optional[str] = Query(None, description="search in title"),
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0),
    order_by: Optional[str] = Query("created_at"),
    desc: Optional[str] = Query("1", description="Accepts 1/0 or true/false for sort direction"),
    include_archived: Optional[str] = Query(
        None,
        description="When true, include archived vacancies (e.g. with status filters cleared).",
    ),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
    own_company_id: Optional[str] = Depends(resolve_active_own_company_id_optional),
):
    # debug instrumentation (temporary) to observe incoming values
    logger = getattr(router, "_logger", None)
    if logger is None:
        import logging
        logger = logging.getLogger("backend.app.api.v1.vacancies")
        router._logger = logger  # type: ignore[attr-defined]
    logger.debug("list_vacancies query desc=%r", desc)
    # When caller explicitly scopes by company_id (e.g. client profile page),
    # we must not hide vacancies by active own-company workspace context.
    # Otherwise the same client shows "0 vacancies" depending on current
    # own-company selection in UI.
    effective_own_company_id = None if company_id else own_company_id
    db, tenant_id = db_tenant
    is_client = await is_client_tenant_for_list(db, str(tenant_id))
    svc = _svc(
        db_tenant,
        own_company_id=effective_own_company_id,
        is_client_tenant=is_client,
    )
    user_role = (getattr(current_user, "role", "") or "").strip().lower()
    inc_arch = _as_bool(include_archived) if include_archived is not None else (user_role == Role.superadmin.value)
    if user_role == Role.superadmin.value:
        last_cand_activity_sq = (
            select(func.max(Candidate.updated_at))
            .where(
                Candidate.vacancy_id == Vacancy.id,
                Candidate.deleted_at.is_(None),
            )
            .correlate(Vacancy)
            .scalar_subquery()
        )
        stmt = (
            select(
                Vacancy,
                Company.name.label("company_name"),
                CandidateProfile.id.label("candidate_profile_id"),
                CandidateProfile.name.label("candidate_profile_name"),
                func.count(Candidate.id).label("candidate_count"),
                last_cand_activity_sq.label("last_candidate_activity_at"),
            )
            .join(Company, Company.id == Vacancy.company_id, isouter=True)
            .join(
                CandidateProfile,
                CandidateProfile.id == Vacancy.candidate_profile_id,
                isouter=True,
            )
            .join(
                Candidate,
                (Candidate.vacancy_id == Vacancy.id) & (Candidate.deleted_at.is_(None)),
                isouter=True,
            )
            .group_by(Vacancy.id, Company.name, CandidateProfile.id, CandidateProfile.name)
        )
        if company_id:
            stmt = stmt.where(Vacancy.company_id == str(company_id))
        normalized_status = (status or "").strip().lower() if status else None
        if normalized_status == "archived":
            stmt = stmt.where(Vacancy.is_archived.is_(True))
        elif status:
            stmt = stmt.where(Vacancy.status == status)
        if candidate_profile_id:
            stmt = stmt.where(Vacancy.candidate_profile_id == str(candidate_profile_id))
        if q:
            like = f"%{q}%"
            stmt = stmt.where(Vacancy.title.ilike(like))
        if not inc_arch and normalized_status != "archived":
            stmt = stmt.where(Vacancy.is_archived.is_(False))

        order_key = (order_by or "created_at").strip().lower()
        order_col = {
            "created_at": Vacancy.created_at,
            "updated_at": Vacancy.updated_at,
            "title": Vacancy.title,
            "status": Vacancy.status,
        }.get(order_key, Vacancy.created_at)
        stmt = stmt.order_by(order_col.desc() if _as_bool(desc) else order_col.asc()).offset(offset).limit(limit)
        rows = await db.execute(stmt)
        return [
            vacancy_to_out(
                v,
                company_name=company_name,
                candidate_profile_id=str(profile_id) if profile_id else None,
                candidate_profile_name=profile_name,
                candidate_count=int(cand_count or 0),
                last_candidate_activity_at=last_act,
            )
            for (v, company_name, profile_id, profile_name, cand_count, last_act) in rows.all()
        ]

    acl = await resolve_restricted_acl(db, str(tenant_id), current_user)
    if is_client:
        # Candidate list for clients does not apply UserCompanyAccess SQL; keep parity so
        # linked agency vacancies (handoff / TenantLink) stay visible.
        acl = None
    return await svc.list(
        company_id=str(company_id) if company_id else None,
        status=status,
        search=q,
        candidate_profile_id=str(candidate_profile_id) if candidate_profile_id else None,
        limit=limit,
        offset=offset,
        order_by=order_by,
        descending=_as_bool(desc),
        acl=acl,
        include_archived=inc_arch,
    )

@router.get("/{vacancy_id}", response_model=VacancyOut)
async def get_vacancy(
    vacancy_id: UUID,
    db_tenant=Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
):
    # Single-vacancy reads must not hide rows by the active workspace own-company
    # (same policy as list_vacancies with company_id unset). Otherwise recruiters see
    # the candidate but GET /vacancies/{id} returns 404 when the vacancy belongs to
    # another legal entity under the same tenant. ACL below still enforces access.
    db, tenant_id = db_tenant
    is_client = await is_client_tenant_for_list(db, str(tenant_id))
    svc = _svc(db_tenant, own_company_id=None, is_client_tenant=is_client)
    try:
        vacancy = await svc.get(str(vacancy_id))
    except LookupError:
        raise HTTPException(status_code=404, detail="Vacancy not found")
    acl = await resolve_restricted_acl(db, str(tenant_id), current_user)
    if not is_client and not _vacancy_allowed(vacancy.id, vacancy.company_id, acl):
        raise HTTPException(status_code=403, detail="Forbidden")
    return vacancy

@router.post("/", response_model=VacancyOut, dependencies=[Depends(require_trust_write())])
@router.post("", response_model=VacancyOut, dependencies=[Depends(require_trust_write())], include_in_schema=False)
async def create_vacancy(
    payload: VacancyIn,
    db_tenant=Depends(get_db_with_tenant),
    own_company_id: str = Depends(resolve_active_own_company_id),
    current_user: UserCtx = Depends(get_current_user),
):
    svc = _svc(db_tenant, own_company_id=own_company_id)
    _db, tenant_id = db_tenant
    await billing_restrictions.ensure_billing_allows_side_effects_for_tenant_id(_db, str(tenant_id))
    try:
        return await svc.create(
            str(tenant_id),
            payload,
            own_company_id=own_company_id,
            actor_user_id=str(current_user.sub) if getattr(current_user, "sub", None) else None,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

@router.post(
    "/{vacancy_id}/candidates",
    dependencies=[Depends(require_trust_write())],
)
async def attach_candidate(
    vacancy_id: UUID,
    payload: VacancyCandidateLink,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
):
    db, tenant_id = db_tenant
    tenant_id_str = str(tenant_id)
    await billing_restrictions.ensure_billing_allows_side_effects_for_tenant_id(db, tenant_id_str)

    vacancy_row = await db.execute(
        select(Vacancy).where(Vacancy.id == str(vacancy_id), Vacancy.tenant_id == str(tenant_id))
    )
    vacancy = vacancy_row.scalar_one_or_none()
    if vacancy is None:
        raise HTTPException(status_code=404, detail="Vacancy not found")

    candidate_row = await db.execute(
        select(Candidate).where(
            Candidate.id == str(payload.candidate_id),
            Candidate.tenant_id == tenant_id_str,
            Candidate.deleted_at.is_(None),
        )
    )
    candidate = candidate_row.scalar_one_or_none()
    if candidate is None:
        raise HTTPException(status_code=404, detail="Candidate not found")

    await _require_can_reassign_candidate_to_vacancy(
        db,
        tenant_id_str=tenant_id_str,
        candidate_id=str(payload.candidate_id),
    )

    await db.execute(
        update(Candidate)
        .where(Candidate.id == str(payload.candidate_id), Candidate.tenant_id == tenant_id_str)
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

    template_id = getattr(vacancy, "required_documents_template_id", None)
    if template_id:
        await apply_template_to_candidate_impl(
            db,
            str(tenant_id),
            str(payload.candidate_id),
            template_id=template_id,
            own_company_id=str(getattr(vacancy, "own_company_id", None) or "").strip() or None,
        )

    return {
        "ok": True,
        "candidate_id": str(payload.candidate_id),
        "vacancy_id": str(vacancy.id),
        "company_id": str(getattr(vacancy, "company_id", "")) if getattr(vacancy, "company_id", None) else None,
    }

@router.get(
    "/{vacancy_id}/pipeline",
    dependencies=[Depends(require_trust_write())],
)
async def get_vacancy_pipeline(
    vacancy_id: UUID,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
):
    db, tenant_id = db_tenant
    tid = str(tenant_id)
    is_client = await is_client_tenant_for_list(db, tid)
    vrepo = VacancyRepo(
        db,
        tid,
        own_company_id=None,
        visibility=get_tenant_visibility(db, tid),
        is_client_tenant=is_client,
    )
    vrow = await vrepo.get(str(vacancy_id))
    if vrow is None:
        raise HTTPException(status_code=404, detail="Vacancy not found")
    vacancy = vrow[0]

    acl = await resolve_restricted_acl(db, tid, current_user)
    if not is_client and not _vacancy_allowed(str(vacancy.id), getattr(vacancy, "company_id", None), acl):
        raise HTTPException(status_code=403, detail="Forbidden")

    candidates = await db.execute(
        select(Candidate).where(
            Candidate.tenant_id == str(tenant_id),
            Candidate.vacancy_id == str(vacancy_id),
            Candidate.deleted_at.is_(None),
        )
    )
    rows = candidates.scalars().all()

    # Profile/Vacancy-specific stages (Vacancy.funnel_id first — ADR-035 §12)
    profile_stages: dict | None = None
    stage_columns_map: dict[str, list[str]] = {}
    stage_codes_order: list[str] = []
    stage_labels: dict[str, dict[str, str]] = {}

    from backend.app.services.recruitment_funnel_assignment import resolve_funnel_id_for_vacancy

    funnel_id = await resolve_funnel_id_for_vacancy(
        db, tenant_id=str(tenant_id), vacancy=vacancy
    )
    if funnel_id:
        from backend.app.models.funnel import Funnel, FunnelStage

        funnel_row = await db.execute(
            select(Funnel).where(
                Funnel.id == funnel_id,
                Funnel.tenant_id.in_([str(tenant_id), "default"]),
            )
        )
        funnel = funnel_row.scalar_one_or_none()
        if funnel:
            stages_row = await db.execute(
                select(FunnelStage)
                .where(FunnelStage.funnel_id == funnel.id)
                .order_by(FunnelStage.order, FunnelStage.code)
            )
            funnel_stages = list(stages_row.scalars().all())
            if funnel_stages:
                # ADR-035 §12: one kanban column per vacancy funnel stage (not aggregated legacy groups).
                stage_codes_order = [s.code for s in funnel_stages]
                stage_columns_map = {s.code: [s.code] for s in funnel_stages}
                stage_labels = {s.code: {s.code: s.label} for s in funnel_stages}
                stage_labels_i18n = {
                    s.code: (
                        {
                            str(k).strip().lower(): str(v).strip()
                            for k, v in (s.labels_i18n or {}).items()
                            if str(k or "").strip() and str(v or "").strip()
                        }
                        if isinstance(getattr(s, "labels_i18n", None), dict)
                        else {}
                    )
                    for s in funnel_stages
                }
                column_order_list = list(stage_codes_order)
                profile_stages = {
                    "stage_codes": stage_codes_order,
                    "stage_labels": stage_labels,
                    "stage_labels_i18n": stage_labels_i18n,
                    "stage_columns": stage_columns_map,
                    "column_order": column_order_list,
                }
    elif getattr(vacancy, "candidate_profile_id", None):
        profile_row = await db.execute(
            select(CandidateProfile).where(
                CandidateProfile.id == vacancy.candidate_profile_id,
                CandidateProfile.tenant_id == str(tenant_id),
            )
        )
        profile = profile_row.scalar_one_or_none()
        if profile and profile.config:
            cfg = profile.config or {}
            stage_codes = cfg.get("stage_codes")
            if isinstance(stage_codes, list) and stage_codes:
                stage_codes_order = [str(c) for c in stage_codes if c]
                sc_map = cfg.get("stage_columns")
                if isinstance(sc_map, dict):
                    stage_columns_map = {
                        str(k): [str(s) for s in v] if isinstance(v, list) else []
                        for k, v in sc_map.items()
                    }
                stage_labels_raw = cfg.get("stage_labels")
                if isinstance(stage_labels_raw, dict):
                    stage_labels = {
                        str(k): v if isinstance(v, dict) else {}
                        for k, v in stage_labels_raw.items()
                    }
                if stage_columns_map:
                    col_order = cfg.get("column_order")
                    if isinstance(col_order, list) and col_order:
                        column_order_list = [str(c) for c in col_order if c]
                    else:
                        column_order_list = list(stage_columns_map.keys())
                    profile_stages = {
                        "stage_codes": stage_codes_order,
                        "stage_labels": stage_labels,
                        "stage_columns": stage_columns_map,
                        "column_order": column_order_list,
                    }

    # Build column_key -> stage_code mapping
    def _stage_to_column(sc: str) -> str:
        if stage_columns_map:
            for col, codes in stage_columns_map.items():
                if sc in codes:
                    return col
        return pipeline_for_stage_code(sc)

    column_keys = list(stage_columns_map.keys()) if stage_columns_map else list(STAGES_BY_GROUP.keys())
    columns: dict[str, List[dict]] = {k: [] for k in column_keys}

    for cand in rows:
        stage_code = getattr(cand, "stage", None) or "new"
        column_key = _stage_to_column(stage_code)
        columns.setdefault(column_key, []).append(
            {
                "candidate_id": str(cand.id),
                "short_id": getattr(cand, "short_id", None),
                "name": f"{getattr(cand, 'first_name', '')} {getattr(cand, 'last_name', '')}".strip(),
                "email": getattr(cand, "email", None),
                "stage": stage_code,
            }
        )

    result: dict = {
        "vacancy_id": str(vacancy.id),
        "statuses": list(columns.keys()),
        "columns": columns,
    }
    if profile_stages:
        result["profile_stages"] = profile_stages
    return result

@router.patch("/{vacancy_id}", response_model=VacancyOut, dependencies=[Depends(require_trust_write())])
async def update_vacancy(
    vacancy_id: UUID,
    payload: VacancyPatch,
    db_tenant=Depends(get_db_with_tenant),
    own_company_id: str = Depends(resolve_active_own_company_id),
    current_user: UserCtx = Depends(get_current_user),
):
    svc = _svc(db_tenant, own_company_id=own_company_id)
    try:
        return await svc.patch(
            str(vacancy_id),
            payload,
            actor_user_id=str(current_user.sub) if getattr(current_user, "sub", None) else None,
        )
    except LookupError:
        raise HTTPException(status_code=404, detail="Vacancy not found")
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))

@router.delete("/{vacancy_id}", dependencies=[Depends(require_trust_write())])
async def delete_vacancy(
    vacancy_id: UUID,
    db_tenant=Depends(get_db_with_tenant),
    own_company_id: str = Depends(resolve_active_own_company_id),
) -> Response:
    svc = _svc(db_tenant, own_company_id=own_company_id)
    try:
        await svc.delete(str(vacancy_id))
    except LookupError:
        raise HTTPException(status_code=404, detail="Vacancy not found")
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return Response(status_code=status.HTTP_204_NO_CONTENT)
