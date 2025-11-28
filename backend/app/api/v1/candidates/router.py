from typing import List, Tuple
from uuid import UUID
from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Response, status, Body
from fastapi import Query
from sqlalchemy.ext.asyncio import AsyncSession

from typing import Optional
from typing import Any, Dict
from pydantic import BaseModel, Field

class BulkStageIn(BaseModel):
    candidate_ids: List[UUID] = Field(default_factory=list)
    stage: str = Field(min_length=1)
    status_reason: Optional[List[str]] = Field(default=None)

class BulkStageItemOut(BaseModel):
    candidate_id: str
    stage: str
    ok: bool
    error: Optional[str] = None

class BulkManagerIn(BaseModel):
    candidate_ids: List[UUID] = Field(default_factory=list)
    manager_id: UUID = Field(description="User id of manager")

class BulkManagerItemOut(BaseModel):
    candidate_id: str
    manager: Optional[str]
    ok: bool
    error: Optional[str] = None

# CreateCandidateIn model
class CreateCandidateIn(BaseModel):
    first_name: str = Field(min_length=1)
    last_name: str = Field(min_length=1)
    email: Optional[str] = None
    phone: Optional[str] = None
    phone_country_code: Optional[str] = None
    languages: Optional[list[str] | str] = None
    country_code: Optional[str] = None
    city: Optional[str] = None
    birth_date: Optional[date | str] = None
    address: Optional[dict] = None
    stage: Optional[str] = None
    manager_id: Optional[UUID] = Field(default=None, description="User id of manager")
    manager: Optional[str] = Field(default=None, description="Alias: same as manager_id")
    company_id: Optional[UUID] = None
    vacancy_id: Optional[UUID] = None

from backend.app.db.deps import get_db_with_tenant
from backend.app.auth.deps import Role, require_roles, get_current_user, UserCtx

from backend.app.api.v1.candidates import service as cand_service
from backend.app.api.v1.candidates import repo as cand_repo
from backend.app.api.v1.candidates.acl import (
    CandidateACL,
    ensure_candidate_access,
    resolve_candidate_acl,
)
from backend.app.services.tenant_visibility import get_tenant_visibility



router = APIRouter()
#
# Роли, которым разрешён доступ к CRUD кандидатов и изменению заметок/статусов
ALLOW_MANAGER_ROLES = (
    Role.manager,
    Role.admin,
    Role.recruiter,
    Role.administrator,  # добавлено: токен с ролью "administrator" теперь проходит
)
ACL_RESTRICTED_ROLES = {
    Role.recruiter.value,
    Role.supervisor.value,
    Role.manager.value,
}

# Helpers to read profile fields from extra
from typing import Any as _Any
import json

def _extra_dict(obj: _Any) -> dict:
    """Safe dict from obj.extra. Supports dict or JSON-encoded string."""
    try:
        extra = getattr(obj, "extra", None)
        # Already a dict
        if isinstance(extra, dict):
            return extra
        # Sometimes JSON is stored as a string in SQLite
        if isinstance(extra, str):
            try:
                import json
                parsed = json.loads(extra)
                if isinstance(parsed, dict):
                    return parsed
            except Exception:
                pass
    except Exception:
        pass
    return {}


def _status_reason_list(value: _Any) -> list[str]:
    """Ensure status_reason is returned as list[str]."""
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return []
        try:
            parsed = json.loads(s)
            if isinstance(parsed, list):
                return [str(v).strip() for v in parsed if str(v).strip()]
        except Exception:
            parts = [p.strip() for p in s.split(",")]
            return [p for p in parts if p]
    return []


def _get_profile_field(obj: _Any, key: str):
    """Get field from extra.profile[key] if present, else None."""
    try:
        extra = _extra_dict(obj)
        profile = extra.get("profile") or {}
        return profile.get(key)
    except Exception:
        return None

def _docs_progress_dict(obj: _Any) -> dict:
    """Safe dict from obj.docs_progress (json stored as text)."""
    try:
        docs = getattr(obj, "docs_progress", None)
        if isinstance(docs, dict):
            return docs
        if isinstance(docs, str):
            try:
                parsed = json.loads(docs)
                if isinstance(parsed, dict):
                    return parsed
            except Exception:
                return {}
    except Exception:
        pass
    return {}


def _serialize_candidate_row(row: Tuple[_Any, ...]) -> Dict[str, Any]:
    if not row:
        raise ValueError("Empty candidate row")

    padded = list(row) + [None] * (8 - len(row))
    c = padded[0]
    company_name = padded[1] or getattr(c, "company_id", None)
    manager_raw = padded[2] or getattr(c, "manager", None)
    manager_name = padded[3] or manager_raw
    vacancy_name = padded[4]
    recruiter_id = padded[5] or getattr(c, "recruiter_id", None)
    recruiter_name = padded[6]
    recruiter_short = padded[7]

    label_primary = None
    label_secondary = None
    stage_label = None

    extra_payload = _extra_dict(c)
    personal_data = getattr(c, "personal_data", None)
    if not isinstance(personal_data, dict) or not personal_data:
        personal_data = extra_payload.get("personal_data", {}) if isinstance(extra_payload, dict) else {}
    contacts = getattr(c, "contacts", None)
    if not isinstance(contacts, dict) or not contacts:
        contacts = extra_payload.get("contacts", {}) if isinstance(extra_payload, dict) else {}

    languages = getattr(c, "languages", None) or personal_data.get("languages") or _get_profile_field(c, "languages")
    country_code = personal_data.get("country_code") or getattr(c, "country_code", None) or _get_profile_field(c, "country_code")
    city = personal_data.get("city") or getattr(c, "city", None) or _get_profile_field(c, "city")
    birth_date = personal_data.get("birth_date") or getattr(c, "birth_date", None) or _get_profile_field(c, "birth_date")
    address = personal_data.get("address") or getattr(c, "address", None) or _get_profile_field(c, "address")

    return {
        "id": str(c.id),
        "short_id": getattr(c, "short_id", None),
        "first_name": getattr(c, "first_name", None),
        "last_name": getattr(c, "last_name", None),
        "phone": contacts.get("phone") or getattr(c, "phone", None),
        "phone_country_code": contacts.get("phone_country_code") or getattr(c, "phone_country_code", None),
        "languages": languages,
        "country_code": country_code,
        "city": city,
        "birth_date": birth_date,
        "address": address,
        "email": contacts.get("email") or getattr(c, "email", None),
        "note": getattr(c, "note", None),
        "notes": getattr(c, "note", None),  # alias for legacy consumers
        "stage": getattr(c, "stage", None),
        "status": getattr(c, "status", None) or getattr(c, "stage", None),
        "stage_label": stage_label,
        "status_reason": _status_reason_list(getattr(c, "status_reason", None)),
        "manager": manager_name or manager_raw or "",
        "manager_name": manager_name or manager_raw or "",
        "manager_id": manager_raw,
        "vacancy": vacancy_name or company_name or "",
        "vacancy_name": vacancy_name or company_name or "",
        "vacancy_title": vacancy_name or company_name or "",
        "labels": [x for x in [label_primary, label_secondary] if x],
        "company_id": getattr(c, "company_id", None),
        "company_name": company_name,
        "vacancy_id": getattr(c, "vacancy_id", None),
        "recruiter_id": recruiter_id,
        "recruiter_name": recruiter_name or recruiter_id or "",
        "recruiter_short": recruiter_short or "",
        "source": getattr(c, "source", None),
        "origin": getattr(c, "origin", None),
        "created_at": getattr(c, "created_at", None),
        "updated_at": getattr(c, "updated_at", None),
        "extra": extra_payload,
        "docs_progress": _docs_progress_dict(c),
        "personal_data": personal_data or {},
        "contacts": contacts or {},
    }


def _format_actor_label(user: _Any | None, raw_actor: Optional[str]) -> Optional[str]:
    """Human-readable label for stage history actors."""
    if user is not None:
        full_name = str(getattr(user, "full_name", "") or "").strip()
        email = str(getattr(user, "email", "") or "").strip()
        short_id = str(getattr(user, "short_id", "") or "").strip()
        if full_name and email:
            return f"{full_name} ({email})"
        if full_name:
            return full_name
        if short_id and email:
            return f"{short_id} ({email})"
        if email:
            return email
        if short_id:
            return short_id
    return str(raw_actor) if raw_actor else None


# Compatibility GET list endpoint for frontend
@router.get("", dependencies=[Depends(require_roles(*ALLOW_MANAGER_ROLES))])
@router.get("/", include_in_schema=False, dependencies=[Depends(require_roles(*ALLOW_MANAGER_ROLES))])
async def list_candidates(
    order_by: str = "created_at",
    desc: bool = True,
    limit: int = 50,
    offset: int = 0,
    # filters
    stage: str | None = None,
    stages: str | None = None,
    status: str | None = None,
    status_reason: Optional[List[str]] = Query(
        default=None,
        description="Коды причин отказа/отклонения (через запятую или повтор param).",
    ),
    manager_id: UUID | None = None,
    vacancy_id: UUID | None = Query(default=None, alias="vacancy_id"),
    vacancy: UUID | None = Query(default=None, alias="vacancy"),
    documents_ordered: str | None = Query(
        default=None,
        description="Filter candidates by presence of ordered documents (`ordered` or `not_ordered`).",
    ),
    q: str | None = Query(default=None, description="Поиск по имени/фамилии/email/телефону"),
    created_from: date | None = None,
    created_to: date | None = None,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
):
    """
    List endpoint с фильтрами и пагинацией. Возвращает: {"total": int, "items": [ ... ]}
    """
    db, tenant_id = db_tenant
    visibility = get_tenant_visibility(db, str(tenant_id))
    filters: dict[str, object] = {}
    visibility = get_tenant_visibility(db, str(tenant_id))
    acl: CandidateACL | None = None
    if current_user.role in ACL_RESTRICTED_ROLES:
        acl = await resolve_candidate_acl(db, str(tenant_id), current_user)
        if acl.is_empty():
            return {"total": 0, "items": []}
        filters["allowed_company_ids"] = list(acl.company_ids)
        filters["allowed_vacancy_ids"] = list(acl.vacancy_ids)
        filters["allowed_manager_ids"] = list(acl.manager_ids)

    if status:
        s = status.strip()
        if s:
            filters["status"] = s
            filters["stage"] = s
            filters["stages"] = [s]
    elif stage:
        s = stage.strip()
        if s:
            filters["status"] = s
            filters["stage"] = s
            filters["stages"] = [s]

    if stages:
        arr = [x.strip() for x in stages.split(",") if x.strip()]
        if arr:
            filters["stages"] = arr

    if status_reason:
        reason_codes: List[str] = []
        for value in status_reason:
            if not value:
                continue
            parts = [part.strip() for part in value.split(",") if part and part.strip()]
            reason_codes.extend(parts)
        if reason_codes:
            unique_codes: List[str] = []
            seen_codes = set()
            for code in reason_codes:
                if code in seen_codes:
                    continue
                unique_codes.append(code)
                seen_codes.add(code)
            if unique_codes:
                filters["status_reason"] = unique_codes

    if manager_id:
        mid = str(manager_id)
        filters["manager"] = mid
        filters["manager_id"] = mid  # compatibility with legacy consumers

    # фильтр по вакансии — поддерживаем оба ключа (vacancy_id и vacancy)
    _vac = vacancy_id or vacancy
    if _vac:
        filters["vacancy_id"] = str(_vac)

    if documents_ordered:
        doc_filter = documents_ordered.strip().lower()
        if doc_filter in {"ordered", "not_ordered"}:
            filters["documents_ordered"] = doc_filter

    if q:
        q = q.strip()
        if q:
            filters["q"] = q

    if created_from:
        filters["dt_from"] = datetime.combine(created_from, datetime.min.time())
    if created_to:
        filters["dt_to"] = datetime.combine(created_to, datetime.max.time())
    total = await cand_repo.count_candidates(
        db,
        tenant_id=str(tenant_id),
        filters=filters,
        visibility=visibility,
    )
    rows = await cand_repo.fetch_candidates_with_labels(
        db,
        tenant_id=str(tenant_id),
        filters=filters,
        limit=limit,
        offset=offset,
        order_by=order_by,
        desc=desc,
        visibility=visibility,
    )

    items = []
    for row in rows:
        # "rows" can come in two shapes depending on repo implementation.
        # Shape A (older): (c, label_primary, label_secondary, stage_label, vacancy_title)
        # Shape B (newer): (c, company_name, manager_raw, manager_name, vacancy_title)
        c = row[0]
        company_name = None
        label_primary = None
        label_secondary = None
        stage_label = None
        manager_name = None
        manager_raw = getattr(c, "manager", None)
        vacancy_name = None

        if len(row) >= 5:
            # Try to detect Shape B by checking if 3rd element looks like UUID (manager_raw)
            possible_mgr_raw = row[2]
            try:
                # if it's a valid UUID, treat as Shape B
                from uuid import UUID as _UUID
                _ = _UUID(str(possible_mgr_raw))
                # Shape B
                manager_raw = str(possible_mgr_raw)
                manager_name = row[3]
                company_name = row[1]
                vacancy_name = row[4]
            except Exception:
                # Shape A
                label_primary = row[1]
                company_name = row[1]
                label_secondary = row[2]
                stage_label = row[3]
                vacancy_name = row[4]
        elif len(row) == 4:
            # very defensive fallback: assume last is vacancy
            vacancy_name = row[3]

        docs_readiness_state = None
        docs_readiness_rank = None
        docs_last_ordered_at = None
        docs_next_valid_from = None
        docs_has_files = None

        if len(row) >= 13:
            docs_readiness_state = row[8]
            docs_readiness_rank = row[9]
            docs_last_ordered_at = row[10]
            docs_next_valid_from = row[11]
            docs_has_files = bool(row[12]) if row[12] is not None else None

        extra_payload = _extra_dict(c)
        docs_progress = _docs_progress_dict(c)

        items.append(
            {
                "id": str(c.id),
                "short_id": getattr(c, "short_id", None),
                "first_name": getattr(c, "first_name", None),
                "last_name": getattr(c, "last_name", None),
                "phone": getattr(c, "phone", None),
                "phone_country_code": getattr(c, "phone_country_code", None),
                "languages": getattr(c, "languages", None) or _get_profile_field(c, "languages"),
                "country_code": getattr(c, "country_code", None) or _get_profile_field(c, "country_code"),
                "city": getattr(c, "city", None) or _get_profile_field(c, "city"),
                "birth_date": getattr(c, "birth_date", None) or _get_profile_field(c, "birth_date"),
                "address": getattr(c, "address", None) or _get_profile_field(c, "address"),
                "email": getattr(c, "email", None),
                "note": getattr(c, "note", None),
                "notes": getattr(c, "note", None),  # alias for legacy consumers
                "stage": getattr(c, "stage", None),
                "stage_label": stage_label,
                # Менеджер: отображаем красивое имя, а сырой id отдаём отдельно
                "manager": manager_name or manager_raw or "",
                "manager_name": manager_name or manager_raw or "",
                "manager_id": manager_raw,
                # Вакансия: человекочитаемое название, fallback to company name
                "vacancy": (vacancy_name or company_name or ""),
                "vacancy_name": (vacancy_name or company_name or ""),
                "vacancy_title": (vacancy_name or company_name or ""),
                "vacancy_id": getattr(c, "vacancy_id", None),
                "company_name": company_name,
                # метки, если есть в Shape A
                "labels": [x for x in [label_primary, label_secondary] if x],
                "status_reason": _status_reason_list(getattr(c, "status_reason", None)),
                "created_at": getattr(c, "created_at", None),
                "updated_at": getattr(c, "updated_at", None),
                "extra": extra_payload,
                "docs_progress": docs_progress,
                "docs_readiness_state": docs_readiness_state,
                "docs_readiness_rank": docs_readiness_rank,
                "docs_last_ordered_at": docs_last_ordered_at.isoformat() if getattr(docs_last_ordered_at, "isoformat", None) else docs_last_ordered_at,
                "docs_next_valid_from": docs_next_valid_from.isoformat() if getattr(docs_next_valid_from, "isoformat", None) else docs_next_valid_from,
                "docs_has_files": docs_has_files,
            }
        )

    return {"total": total, "items": items}

@router.post(
    "/bulk-stage",
    response_model=List[BulkStageItemOut],
    dependencies=[Depends(require_roles(*ALLOW_MANAGER_ROLES))],
)
async def bulk_update_stage(
    payload: BulkStageIn,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
):
    db, tenant_id = db_tenant
    s = (payload.stage or "").strip()
    if not s:
        raise HTTPException(status_code=422, detail="Stage must not be empty")

    acl: CandidateACL | None = None
    if current_user.role in ACL_RESTRICTED_ROLES:
        acl = await resolve_candidate_acl(db, str(tenant_id), current_user)

    results = await cand_service.bulk_update_stage(
        db=db,
        tenant_id=str(tenant_id),
        candidate_ids=[str(cid) for cid in payload.candidate_ids],
        stage=s,
        actor_id=current_user.sub,
        status_reason=payload.status_reason,
        acl=acl,
    )
    return results

@router.post(
    "/bulk-manager",
    response_model=List[BulkManagerItemOut],
    dependencies=[Depends(require_roles(*ALLOW_MANAGER_ROLES))],
)
async def bulk_update_manager(
    payload: BulkManagerIn,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
):
    db, tenant_id = db_tenant
    if not payload.candidate_ids:
        return []

    acl: CandidateACL | None = None
    if current_user.role in ACL_RESTRICTED_ROLES:
        acl = await resolve_candidate_acl(db, str(tenant_id), current_user)

    results = await cand_service.bulk_update_manager(
        db=db,
        tenant_id=str(tenant_id),
        candidate_ids=[str(cid) for cid in payload.candidate_ids],
        manager_id=str(payload.manager_id),
        actor_id=current_user.sub,
        acl=acl,
    )
    return results


# Create candidate
@router.post(
    "",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_roles(*ALLOW_MANAGER_ROLES))],
    summary="Create candidate",
)
@router.post(
    "/",
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
    dependencies=[Depends(require_roles(*ALLOW_MANAGER_ROLES))],
)
async def create_candidate(
    payload: CreateCandidateIn,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
):
    db, tenant_id = db_tenant

    data: Dict[str, Any] = payload.model_dump(exclude_none=True)

    data["first_name"] = payload.first_name.strip()
    data["last_name"] = payload.last_name.strip()

    for key in ("phone", "email", "phone_country_code", "stage", "status"):
        if key in data and isinstance(data[key], str):
            stripped = data[key].strip()
            data[key] = stripped or None

    langs_value = data.get("languages")
    if isinstance(langs_value, str):
        data["languages"] = [p.strip() for p in langs_value.split(",") if p.strip()]

    birth_date_val = data.get("birth_date")
    if isinstance(birth_date_val, str) and birth_date_val:
        try:
            data["birth_date"] = date.fromisoformat(birth_date_val)
        except Exception:
            data["birth_date"] = None

    if data.get("manager_id"):
        data["manager"] = str(data.pop("manager_id"))
    elif data.get("manager"):
        data["manager"] = str(data["manager"]).strip()

    for fk in ("company_id", "vacancy_id"):
        if data.get(fk) is not None:
            data[fk] = str(data[fk])

    acl: CandidateACL | None = None
    if current_user.role in ACL_RESTRICTED_ROLES:
        acl = await resolve_candidate_acl(db, str(tenant_id), current_user)

    created = await cand_service.create_candidate_full(
        db=db,
        tenant_id=str(tenant_id),
        payload=data,
        actor_id=current_user.sub,
        acl=acl,
    )

    row = await cand_repo.get_candidate_with_labels(
        db,
        tenant_id=str(tenant_id),
        candidate_id=str(created.id),
        visibility=visibility,
    )
    if row is None:
        return {
            "id": str(created.id),
            "first_name": created.first_name,
            "last_name": created.last_name,
            "email": created.email,
            "phone": created.phone,
            "phone_country_code": created.phone_country_code,
            "languages": data.get("languages"),
            "stage": created.stage,
            "status": created.stage,
            "manager_id": data.get("manager"),
            "company_id": data.get("company_id"),
            "company_name": data.get("company_name"),
            "vacancy_id": data.get("vacancy_id"),
            "recruiter_id": getattr(created, "recruiter_id", None),
            "recruiter_name": "",
            "recruiter_short": "",
            "source": data.get("source"),
            "origin": data.get("origin"),
            "extra": _extra_dict(created),
            "docs_progress": _docs_progress_dict(created),
            "personal_data": data.get("personal_data") or {},
            "contacts": data.get("contacts") or {},
        }

    return _serialize_candidate_row(row)


# Get candidate by id
@router.get(
    "/{candidate_id}",
    dependencies=[Depends(require_roles(*ALLOW_MANAGER_ROLES))],
    summary="Get candidate by id",
)
async def get_candidate(
    candidate_id: UUID,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
):
    db, tenant_id = db_tenant
    visibility = get_tenant_visibility(db, str(tenant_id))
    if current_user.role in ACL_RESTRICTED_ROLES:
        await ensure_candidate_access(
            db,
            str(tenant_id),
            str(candidate_id),
            current_user,
        )
    row = await cand_repo.get_candidate_with_labels(
        db,
        tenant_id=str(tenant_id),
        candidate_id=str(candidate_id),
        visibility=visibility,
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Candidate not found")

    return _serialize_candidate_row(row)


# Stage history
@router.get(
    "/{candidate_id}/stage-history",
    dependencies=[Depends(require_roles(*ALLOW_MANAGER_ROLES))],
    summary="Get candidate stage history",
)
async def get_candidate_stage_history(
    candidate_id: UUID,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> List[Dict[str, Any]]:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    visibility = get_tenant_visibility(db, tenant_id)
    candidate_str = str(candidate_id)

    if current_user.role in ACL_RESTRICTED_ROLES:
        await ensure_candidate_access(
            db,
            tenant_id,
            candidate_str,
            current_user,
        )

    candidate = await cand_repo.get_candidate(db, tenant_id, candidate_str, visibility=visibility)
    if candidate is None:
        raise HTTPException(status_code=404, detail="Candidate not found")

    history_tenant_id = getattr(candidate, "tenant_id", tenant_id)
    entries = await cand_repo.list_candidate_stage_history(db, history_tenant_id, candidate_str)
    history: List[Dict[str, Any]] = []
    for entry, actor_user in entries:
        history.append(
            {
                "id": entry.id,
                "from_code": entry.from_code,
                "to_code": entry.to_code,
                "reason": entry.reason,
                "actor": _format_actor_label(actor_user, entry.actor),
                "at": entry.at.isoformat() if entry.at else None,
            }
        )
    return history


# Partially update candidate
@router.patch(
    "/{candidate_id}",
    dependencies=[Depends(require_roles(*ALLOW_MANAGER_ROLES))],
    summary="Partially update candidate",
)
async def patch_candidate(
    candidate_id: UUID,
    payload: Dict[str, Any] = Body(...),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
):
    db, tenant_id = db_tenant
    visibility = get_tenant_visibility(db, str(tenant_id))
    acl: CandidateACL | None = None
    if current_user.role in ACL_RESTRICTED_ROLES:
        await ensure_candidate_access(
            db,
            str(tenant_id),
            str(candidate_id),
            current_user,
        )
        acl = await resolve_candidate_acl(db, str(tenant_id), current_user)

    # Allow only known fields to be updated to avoid accidental overwrites
    allowed_fields = {
        "first_name",
        "last_name",
        "email",
        "phone",
        "phone_country_code",
        "languages",
        "country_code",
        "city",
        "birth_date",
        "address",
        "stage",
        "status",
        "status_reason",
        "company_id",
        "vacancy_id",
        # accept both "manager" (DB column) and "manager_id" (frontend alias)
        "manager",
        "manager_id",
        "notes",
        "note",
        "extra",
        "personal_data",
        "contacts",
    }

    # Start with only allowed keys
    raw: Dict[str, Any] = {k: v for k, v in payload.items() if k in allowed_fields}

    # Map aliases
    if "manager_id" in raw and raw.get("manager_id"):
        raw["manager"] = raw.pop("manager_id")
    if "notes" in raw:
        raw["note"] = raw.pop("notes")

    # Normalize/clean values; ignore empty strings so we don't wipe seeded data
    data: Dict[str, Any] = {}
    for k, v in raw.items():
        # Treat blank strings as "no change"
        if isinstance(v, str):
            v = v.strip()
            if v == "":
                continue

        # birth_date can come as string "YYYY-MM-DD" — convert to date if possible
        if k == "birth_date" and isinstance(v, str):
            try:
                v = date.fromisoformat(v)
            except Exception:
                # if parsing fails, skip updating this field
                continue

        # languages can be a comma-separated string from UI
        if k == "languages" and isinstance(v, str):
            parts = [p.strip() for p in v.split(",") if p.strip()]
            v = parts

        if k in {"stage", "status", "status_reason"} and isinstance(v, str):
            v = v.strip()

        # address — skip completely empty dicts
        if k == "address" and isinstance(v, dict):
            if not any(bool(x) for x in v.values()):
                continue

        data[k] = v

    if not data:
        raise HTTPException(status_code=400, detail="No valid fields to update")

    updated = await cand_service.update_candidate_full(
        db,
        tenant_id=str(tenant_id),
        candidate_id=str(candidate_id),
        payload=data,
        actor_id=current_user.sub,
        acl=acl,
    )

    # Return the same enriched view as GET /{id}
    row = await cand_repo.get_candidate_with_labels(
        db,
        tenant_id=str(tenant_id),
        candidate_id=str(candidate_id),
        visibility=visibility,
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Candidate not found")

    return _serialize_candidate_row(row)


@router.delete(
    "/{candidate_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
@router.delete(
    "/{candidate_id}/",
    status_code=status.HTTP_204_NO_CONTENT,
    include_in_schema=False,
)
async def delete_candidate(
    candidate_id: UUID,
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> Response:
    if ctx.role == Role.recruiter.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Recruiter cannot delete candidates. Create a delete-request instead.",
        )
    if ctx.role not in (
        Role.administrator.value,
        Role.supervisor.value,
        Role.superadmin.value,
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    db, tenant_id = db_tenant
    await cand_service.delete_candidate_full(db, str(tenant_id), str(candidate_id))
    return Response(status_code=status.HTTP_204_NO_CONTENT)
