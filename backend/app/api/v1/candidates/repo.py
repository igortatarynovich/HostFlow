"""
Repository layer for Candidate entity.

This module isolates all direct database access for Candidate operations.
Service layer (`service.py`) should use this module exclusively to read/write data.

Responsibilities:
- CRUD operations (create, read, update, delete);
- filtering and pagination queries;
- joining related tables (company, documents, etc.);
- maintaining consistency with multi-tenancy and RLS.
"""

from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
import json
from sqlalchemy import (
    select,
    update,
    and_,
    func,
    or_,
    literal,
    exists,
    case,
    literal_column,
    cast,
    bindparam,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from backend.app.models.candidate import Candidate
from backend.app.models.candidate_stage_history import CandidateStageHistory
from backend.app.models.user import User
from backend.app.models.company import Company
from backend.app.models.vacancy import Vacancy
from backend.app.models.document import Document
from backend.app.models.enums import DocumentStatus
from backend.app.services.tenant_visibility import TenantVisibility


__all__ = [
    "create_candidate",
    "update_candidate",
    "get_candidate",
    "list_candidates",
    "delete_candidate",
    "count_candidates",
    "fetch_candidates_with_labels",
    "get_candidate_with_labels",
    "count_by_stage",
    "count_by_manager",
    "list_candidate_stage_history",
]

READY_STATUSES = (
    DocumentStatus.received,
    DocumentStatus.delivered,
    DocumentStatus.approved,
    DocumentStatus.completed,
)
PROBLEM_STATUSES = (
    DocumentStatus.rejected,
    DocumentStatus.expired,
    DocumentStatus.overdue,
)
AWAITING_REVIEW_STATUSES = (DocumentStatus.submitted,)
IN_PROGRESS_STATUSES = (DocumentStatus.in_progress,)
ORDERED_STATUSES = (DocumentStatus.requested,)

# --- helpers to pack/unpack profile fields into extra ------------------------

def _parse_extra(raw: Any) -> dict:
    """Best-effort parse of JSON stored in Candidate.extra."""
    if not raw:
        return {}
    if isinstance(raw, dict):
        return dict(raw)
    if isinstance(raw, str):
        try:
            return json.loads(raw) if raw.strip() else {}
        except Exception:
            return {}
    return {}


def _normalize_birth_date(val: Any) -> Optional[str]:
    """Normalize birth_date to ISO (YYYY-MM-DD) string or None."""
    if val is None or val == "":
        return None
    if isinstance(val, datetime):
        return val.date().isoformat()
    try:
        # accept date-like object
        from datetime import date as _date
        if isinstance(val, _date):
            return val.isoformat()
    except Exception:
        pass
    if isinstance(val, str):
        # trust frontend to send ISO; fallback to first 10 chars
        try:
            return datetime.fromisoformat(val).date().isoformat()
        except Exception:
            return val[:10]
    return None


def _extract_profile_patch(data: Dict[str, Any]) -> Dict[str, Any]:
    """Pop known profile fields that live inside extra JSON."""
    patch: Dict[str, Any] = {}
    for key in ("country_code", "city", "address", "birth_date"):
        if key in data:
            patch[key] = data.pop(key)
    # normalize date
    if "birth_date" in patch:
        patch["birth_date"] = _normalize_birth_date(patch.get("birth_date"))
    # drop Nones/empty strings
    patch = {k: v for k, v in patch.items() if v not in (None, "")}
    return patch


def _merge_extra(existing: Any, patch: Dict[str, Any]) -> str:
    base = _parse_extra(existing)
    if not patch:
        return json.dumps(base, ensure_ascii=False)
    base.update(patch)
    # drop null-ish values to keep JSON clean
    base = {k: v for k, v in base.items() if v not in (None, "")}
    return json.dumps(base, ensure_ascii=False)


def _normalize_languages(val: Any) -> Optional[list[str]]:
    """
    Приводит поле languages к списку строк.
    Допускает: None, строку (в т.ч. CSV), JSON-строку массива, список/кортеж/множество.
    Пустые элементы удаляются.
    """
    if val is None:
        return None
    if isinstance(val, (list, tuple, set)):
        arr = [str(x).strip() for x in val if str(x).strip()]
        return arr
    if isinstance(val, str):
        s = val.strip()
        if not s:
            return []
        if s.startswith("["):
            try:
                parsed = json.loads(s)
                return [str(x).strip() for x in parsed if str(x).strip()]
            except Exception:
                # падение в CSV
                pass
        return [p.strip() for p in s.split(",") if p.strip()]
    # на всякий случай — любое иное приводим к строке
    s = str(val).strip()
    return [s] if s else []


# --- helpers to protect write payloads ---------------------------------------

def _filter_updatable_fields(data: Dict[str, Any]) -> Dict[str, Any]:
    """Return only known Candidate columns and skip values that are None.

    This prevents accidental wiping of fields when the incoming payload omits
    them or sends nulls for read-only fields coming from the UI.
    """
    if not isinstance(data, dict):
        return {}

    allowed = {c.name for c in Candidate.__table__.columns}
    # never allow id/tenant_id/created_at to be set from the outside
    disallow = {"id", "tenant_id", "created_at", "deleted_at"}
    allowed -= disallow

    cleaned: Dict[str, Any] = {}
    for k, v in data.items():
        if k not in allowed:
            continue
        # Skip None to avoid wiping existing data on partial update
        if v is None:
            continue
        cleaned[k] = v
    # Always update timestamp on write
    cleaned["updated_at"] = func.now()
    return cleaned


async def create_candidate(db: AsyncSession, data: Dict[str, Any]) -> Candidate:
    """Insert a new candidate record."""
    # Split out profile fields that live in extra
    data = dict(data or {})
    # normalize languages to a list
    if "languages" in data:
        data["languages"] = _normalize_languages(data.get("languages"))
    extra_patch = _extract_profile_patch(data)
    payload = _filter_updatable_fields(data)
    if extra_patch:
        payload["extra"] = _merge_extra(payload.get("extra") or data.get("extra"), extra_patch)
    obj = Candidate(**payload)
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


async def update_candidate(db: AsyncSession, candidate_id: str, data: Dict[str, Any]) -> Optional[Candidate]:
    """Update a candidate record by ID.

    Only updates fields explicitly provided and not None. Unknown keys are ignored.
    """
    # Split out profile fields that live in extra
    data = dict(data or {})
    # normalize languages to a list
    if "languages" in data:
        data["languages"] = _normalize_languages(data.get("languages"))
    extra_patch = _extract_profile_patch(data)
    payload = _filter_updatable_fields(data)
    if extra_patch:
        # read current extra to preserve other keys
        cur = await db.execute(select(Candidate.extra).where(Candidate.id == candidate_id))
        current_extra = cur.scalar_one_or_none()
        payload["extra"] = _merge_extra(current_extra, extra_patch)
    if not payload:
        # Nothing to update, just return current state
        q0 = await db.execute(select(Candidate).where(Candidate.id == candidate_id))
        return q0.scalar_one_or_none()

    await db.execute(
        update(Candidate)
        .where(Candidate.id == candidate_id)
        .values(**payload)
    )
    await db.commit()
    q = await db.execute(select(Candidate).where(Candidate.id == candidate_id))
    return q.scalar_one_or_none()


async def get_candidate(
    db: AsyncSession,
    tenant_id: str,
    candidate_id: str,
    visibility: TenantVisibility | None = None,
) -> Optional[Candidate]:
    """Retrieve a single candidate by ID within tenant and not deleted."""
    q = await db.execute(
        select(Candidate).where(
            Candidate.id == candidate_id,
            _candidate_scope_clause(tenant_id, visibility),
            Candidate.deleted_at.is_(None),
        )
    )
    return q.scalar_one_or_none()


async def list_candidate_stage_history(
    db: AsyncSession,
    tenant_id: str,
    candidate_id: str,
) -> List[Tuple[CandidateStageHistory, Optional[User]]]:
    """Return ordered stage history entries with optional actor info."""
    stmt = (
        select(CandidateStageHistory, User)
        .select_from(CandidateStageHistory)
        .outerjoin(
            User,
            and_(
                User.id == CandidateStageHistory.actor,
                or_(User.tenant_id == tenant_id, User.tenant_id.is_(None)),
            ),
        )
        .where(
            CandidateStageHistory.tenant_id == tenant_id,
            CandidateStageHistory.candidate_id == candidate_id,
        )
        .order_by(CandidateStageHistory.at.asc(), CandidateStageHistory.id.asc())
    )
    result = await db.execute(stmt)
    rows = result.all()
    return [(row[0], row[1]) for row in rows]


async def list_candidates(
    db: AsyncSession,
    tenant_id: str,
    filters: Dict[str, Any],
    order_by: str = "created_at",
    desc: bool = True,
    limit: int = 50,
    offset: int = 0,
    visibility: TenantVisibility | None = None,
) -> List[Candidate]:
    """Return a list of candidates matching the given filters, scoped to tenant."""
    conds = _build_conditions(tenant_id, filters, visibility)
    if not hasattr(Candidate, order_by):
        order_by = "created_at"
    col = getattr(Candidate, order_by)
    if desc:
        col = col.desc()
    stmt = (
        select(Candidate)
        .where(and_(*conds))
        .order_by(col)
        .limit(limit)
        .offset(offset)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def delete_candidate(db: AsyncSession, candidate_id: str) -> None:
    """Soft delete (mark as inactive) or permanently delete candidate."""
    # Soft delete pattern — update `deleted_at`
    await db.execute(
        update(Candidate)
        .where(Candidate.id == candidate_id)
        .values(deleted_at=func.now())
    )
    await db.commit()


# Repository helpers and query functions


def _to_list(value: Any) -> list[str]:
    """
    Нормализует значение фильтра в список строк.
    Допускает: None, строку (в т.ч. CSV), список/кортеж строк.
    Пустые элементы игнорируются.
    """
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        items = list(value)
    elif isinstance(value, str):
        # может прийти уже CSV из query-параметра (?stages=a,b,c)
        items = [x.strip() for x in value.split(",")]
    else:
        # на всякий случай приводим к строке
        items = [str(value)]
    return [x for x in (i.strip() for i in items) if x]


def _candidate_scope_clause(tenant_id: str, visibility: TenantVisibility | None):
    clauses = [Candidate.tenant_id == tenant_id]
    if visibility:
        shared_ids = tuple(visibility.shared_vacancy_ids)
        if shared_ids:
            clauses.append(Candidate.vacancy_id.in_(shared_ids))
    return or_(*clauses)


def _build_conditions(tenant_id: str, filters: Dict[str, Any], visibility: TenantVisibility | None = None):
    conds = [Candidate.deleted_at.is_(None), _candidate_scope_clause(tenant_id, visibility)]

    q = (filters.get("q") or "").strip().lower()
    if q:
        like = f"%{q}%"
        conds.append(
            or_(
                func.lower(Candidate.first_name).like(like),
                func.lower(Candidate.last_name).like(like),
                func.lower(Candidate.email).like(like),
                func.lower(Candidate.phone).like(like),
                func.lower(Candidate.short_id).like(like),
            )
        )

    manager = filters.get("manager")
    if manager:
        conds.append(Candidate.manager == manager)

    # --- stage filters (robust to single value, CSV, or list) ---
    stages_acc: list[str] = []

    # primary: `stage`
    stages_acc += _to_list(filters.get("stage"))
    # secondary: `stages`
    stages_acc += _to_list(filters.get("stages"))
    # compatibility: `stage_codes`
    stages_acc += _to_list(filters.get("stage_codes"))

    # deduplicate while preserving order
    seen = set()
    stages_norm = [s for s in stages_acc if not (s in seen or seen.add(s))]
    if stages_norm:
        conds.append(Candidate.stage.in_(stages_norm))

    dt_from: Optional[datetime] = filters.get("dt_from")
    dt_to: Optional[datetime] = filters.get("dt_to")
    if dt_from:
        conds.append(Candidate.created_at >= dt_from)
    if dt_to:
        conds.append(Candidate.created_at <= dt_to)

    company_id = filters.get("company_id")
    if company_id:
        conds.append(Candidate.company_id == company_id)

    vacancy_id = filters.get("vacancy_id")
    if vacancy_id:
        conds.append(Candidate.vacancy_id == vacancy_id)

    allowed_company_ids = _to_list(filters.get("allowed_company_ids"))
    allowed_vacancy_ids = _to_list(filters.get("allowed_vacancy_ids"))
    allowed_manager_ids = _to_list(filters.get("allowed_manager_ids"))
    if allowed_company_ids or allowed_vacancy_ids or allowed_manager_ids:
        acl_conditions = []
        if allowed_manager_ids:
            acl_conditions.append(Candidate.manager.in_(allowed_manager_ids))
        if allowed_company_ids:
            acl_conditions.append(Candidate.company_id.in_(allowed_company_ids))
        if allowed_vacancy_ids:
            acl_conditions.append(Candidate.vacancy_id.in_(allowed_vacancy_ids))
        if acl_conditions:
            conds.append(or_(*acl_conditions))
        else:
            conds.append(literal(False))

    docs_ordered = str(filters.get("documents_ordered") or "").strip().lower()
    if docs_ordered in {"ordered", "not_ordered"}:
        ordered_exists = (
            exists()
            .where(Document.candidate_id == Candidate.id)
            .where(Document.tenant_id == Candidate.tenant_id)
            .where(Document.deleted_at.is_(None))
            .where(
                or_(
                    Document.ordered_at.isnot(None),
                    Document.status.in_(ORDERED_STATUSES),
                )
            )
        )
        if docs_ordered == "ordered":
            conds.append(ordered_exists)
        else:
            conds.append(~ordered_exists)

    status_reason_codes = _to_list(filters.get("status_reason"))
    if status_reason_codes:
        reason_clauses = []
        for idx, code in enumerate(status_reason_codes):
            if not code:
                continue
            if _HAS_JSONB:
                bind = bindparam(
                    f"status_reason_code_{idx}",
                    value=[code],
                    type_=JSONB,
                )
                reason_clauses.append(
                    cast(Candidate.status_reason, JSONB).op("@>")(bind)
                )
            else:  # fallback (e.g. SQLite dev env)
                reason_clauses.append(Candidate.status_reason.like(f'%"{code}"%'))
        if reason_clauses:
            conds.append(or_(*reason_clauses))

    return conds


async def count_candidates(
    db: AsyncSession,
    tenant_id: str,
    filters: Dict[str, Any],
    visibility: TenantVisibility | None = None,
) -> int:
    conds = _build_conditions(tenant_id, filters, visibility)
    base_query = select(Candidate).where(and_(*conds))
    res = await db.execute(select(func.count()).select_from(base_query.subquery()))
    return int(res.scalar_one() or 0)


async def fetch_candidates_with_labels(
    db: AsyncSession,
    tenant_id: str,
    filters: Dict[str, Any],
    order_by: str,
    desc: bool,
    limit: int,
    offset: int,
    visibility: TenantVisibility | None = None,
) -> List[
    Tuple[
        Candidate,
        Optional[str],  # company name
        Optional[str],  # manager raw id
        Optional[str],  # manager name label
        Optional[str],  # vacancy title label
        Optional[str],  # recruiter id
        Optional[str],  # recruiter name label
        Optional[str],  # recruiter short id
    ]
]:
    conds = _build_conditions(tenant_id, filters, visibility)
    if not hasattr(Candidate, order_by):
        order_by = "created_at"
    col = getattr(Candidate, order_by)
    if desc:
        col = col.desc()

    # Build safe label expressions for manager and vacancy columns
    manager_alias = aliased(User)
    recruiter_alias = aliased(User)
    manager_name_expr = func.coalesce(
        func.nullif(manager_alias.full_name, ""),
        func.nullif(manager_alias.email, ""),
        func.nullif(Candidate.manager, "")
    )

    vacancy_title_expr = func.coalesce(
        func.nullif(Vacancy.title, ""),
        func.nullif(getattr(Vacancy, "position", literal("")), ""),
        func.nullif(getattr(Vacancy, "name", literal("")), "")
    )

    recruiter_name_expr = func.coalesce(
        func.nullif(recruiter_alias.full_name, ""),
        func.nullif(recruiter_alias.email, ""),
        func.nullif(Candidate.recruiter_id, ""),
    )

    def _doc_exists(*extra_conditions):
        return (
            exists()
            .where(Document.candidate_id == Candidate.id)
            .where(Document.tenant_id == Candidate.tenant_id)
            .where(Document.deleted_at.is_(None))
            .where(*extra_conditions)
        )

    ready_exists = _doc_exists(Document.status.in_(READY_STATUSES))
    problem_exists = _doc_exists(Document.status.in_(PROBLEM_STATUSES))
    awaiting_exists = _doc_exists(Document.status.in_(AWAITING_REVIEW_STATUSES))
    in_progress_exists = _doc_exists(Document.status.in_(IN_PROGRESS_STATUSES))
    ordered_exists = _doc_exists(
        or_(
            Document.ordered_at.isnot(None),
            Document.status.in_(ORDERED_STATUSES),
        )
    )
    files_condition = or_(
        Document.files.isnot(None),
        func.length(func.coalesce(Document.filename, literal(""))) > 0,
        func.length(func.coalesce(Document.path, literal(""))) > 0,
    )
    has_files_exists = _doc_exists(files_condition)

    readiness_expr = case(
        (problem_exists, literal("problem")),
        (ready_exists, literal("ready")),
        (awaiting_exists, literal("awaiting_review")),
        (in_progress_exists, literal("in_progress")),
        (ordered_exists, literal("ordered")),
        else_=literal("pending"),
    )

    readiness_rank_expr = case(
        (problem_exists, literal(5)),
        (awaiting_exists, literal(4)),
        (in_progress_exists, literal(3)),
        (ordered_exists, literal(2)),
        (ready_exists, literal(1)),
        else_=literal(0),
    )

    docs_last_ordered = (
        select(func.max(Document.ordered_at))
        .where(
            Document.candidate_id == Candidate.id,
            Document.tenant_id == Candidate.tenant_id,
            Document.deleted_at.is_(None),
            Document.ordered_at.isnot(None),
        )
        .scalar_subquery()
    )

    docs_next_valid = (
        select(func.min(Document.valid_from))
        .where(
            Document.candidate_id == Candidate.id,
            Document.tenant_id == Candidate.tenant_id,
            Document.deleted_at.is_(None),
            Document.valid_from.isnot(None),
        )
        .scalar_subquery()
    )

    stmt = (
        select(
            Candidate,
            Company.name.label("company_name"),
            Candidate.manager.label("manager_raw"),
            manager_name_expr.label("manager_name"),
            vacancy_title_expr.label("vacancy"),
            Candidate.recruiter_id.label("recruiter_id"),
            recruiter_name_expr.label("recruiter_name"),
            recruiter_alias.short_id.label("recruiter_short"),
            readiness_expr.label("docs_readiness_state"),
            readiness_rank_expr.label("docs_readiness_rank"),
            docs_last_ordered.label("docs_last_ordered_at"),
            docs_next_valid.label("docs_next_valid_from"),
            has_files_exists.label("docs_has_files"),
        )
        .select_from(Candidate)
        .join(manager_alias, manager_alias.id == Candidate.manager, isouter=True)
        .join(Company, Company.id == Candidate.company_id, isouter=True)
        .join(Vacancy, Vacancy.id == Candidate.vacancy_id, isouter=True)
        .join(recruiter_alias, recruiter_alias.id == Candidate.recruiter_id, isouter=True)
        .where(and_(*conds))
        .order_by(col)
        .limit(limit)
        .offset(offset)
    )
    rows = await db.execute(stmt)
    return [
        (
            r[0],
            r[1],
            r[2],
            r[3],
            r[4],
            r[5],
            r[6],
            r[7],
            r[8],
            r[9],
            r[10],
            r[11],
            r[12],
        )
        for r in rows.all()
    ]


async def get_candidate_with_labels(
    db: AsyncSession,
    tenant_id: str,
    candidate_id: str,
    visibility: TenantVisibility | None = None,
) -> Optional[
    Tuple[
        Candidate,
        Optional[str],
        Optional[str],
        Optional[str],
        Optional[str],
        Optional[str],
        Optional[str],
        Optional[str],
    ]
]:
    # Build safe label expressions for manager and vacancy columns
    manager_alias = aliased(User)
    recruiter_alias = aliased(User)
    manager_name_expr = func.coalesce(
        func.nullif(manager_alias.full_name, ""),
        func.nullif(manager_alias.email, ""),
        func.nullif(Candidate.manager, "")
    )

    vacancy_title_expr = func.coalesce(
        func.nullif(Vacancy.title, ""),
        func.nullif(getattr(Vacancy, "position", literal("")), ""),
        func.nullif(getattr(Vacancy, "name", literal("")), "")
    )

    recruiter_name_expr = func.coalesce(
        func.nullif(recruiter_alias.full_name, ""),
        func.nullif(recruiter_alias.email, ""),
        func.nullif(Candidate.recruiter_id, ""),
    )

    stmt = (
        select(
            Candidate,
            Company.name.label("company_name"),
            Candidate.manager.label("manager_raw"),
            manager_name_expr.label("manager_name"),
            vacancy_title_expr.label("vacancy"),
            Candidate.recruiter_id.label("recruiter_id"),
            recruiter_name_expr.label("recruiter_name"),
            recruiter_alias.short_id.label("recruiter_short"),
        )
        .select_from(Candidate)
        .join(Company, Company.id == Candidate.company_id, isouter=True)
        .join(manager_alias, manager_alias.id == Candidate.manager, isouter=True)
        .join(Vacancy, Vacancy.id == Candidate.vacancy_id, isouter=True)
        .join(recruiter_alias, recruiter_alias.id == Candidate.recruiter_id, isouter=True)
        .where(
            Candidate.id == candidate_id,
            _candidate_scope_clause(tenant_id, visibility),
            Candidate.deleted_at.is_(None),
        )
        .limit(1)
    )
    row = (await db.execute(stmt)).first()
    return tuple(row) if row is not None else None


async def count_by_stage(
    db: AsyncSession,
    tenant_id: str,
    filters: Dict[str, Any],
    visibility: TenantVisibility | None = None,
) -> Dict[str, int]:
    conds = _build_conditions(tenant_id, filters, visibility)
    rows = await db.execute(
        select(Candidate.stage, func.count())
        .where(and_(*conds))
        .group_by(Candidate.stage)
    )
    return { (k or ""): int(v or 0) for k, v in rows.all() }


async def count_by_manager(
    db: AsyncSession,
    tenant_id: str,
    filters: Dict[str, Any],
    visibility: TenantVisibility | None = None,
) -> Dict[str, int]:
    conds = _build_conditions(tenant_id, filters, visibility)
    rows = await db.execute(
        select(Candidate.manager, func.count())
        .where(and_(*conds))
        .group_by(Candidate.manager)
    )
    return { (k or ""): int(v or 0) for k, v in rows.all() }
try:  # pragma: no cover - optional backend
    from sqlalchemy.dialects.postgresql import JSONB
    _HAS_JSONB = True
except Exception:  # pragma: no cover
    JSONB = None  # type: ignore
    _HAS_JSONB = False
