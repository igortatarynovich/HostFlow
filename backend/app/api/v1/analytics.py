from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, time
from typing import Any, Dict, List, Optional, Counter as TCounter
import json

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased
from uuid import UUID

from backend.app.db.deps import get_db_with_tenant
from backend.app.models import Candidate, Company, Vacancy, User
from backend.app.models.enums import CandidateStage
from backend.app.constants.stages import LABELS as STAGE_LABELS, STATUS_REASON_CHOICES, ORDER as STAGE_ORDER
from backend.app.services.tenant_visibility import TenantVisibility, get_tenant_visibility
from backend.app.services.source_labels import normalize_candidate_source

router = APIRouter(tags=["analytics"])


_REASON_LABELS = {
    stage: {item["code"]: item["label"] for item in items}
    for stage, items in STATUS_REASON_CHOICES.items()
}


def _safe_dict(value: Any) -> Dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            return {}
    return {}


def _status_reason_list(value: Any) -> list[str]:
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
            pass
        return [part.strip() for part in s.split(",") if part and part.strip()]
    return []


def _stage_label(code: Optional[str]) -> str:
    if not code:
        return "—"
    return STAGE_LABELS.get(code, str(code))


_ORDERED_STAGE_LABELS = [_stage_label(code) for code in STAGE_ORDER]


def _candidate_scope_clause(tenant_id: str, visibility: TenantVisibility | None):
    clauses = [Candidate.tenant_id == tenant_id]
    shared_vacancies = getattr(visibility, "shared_vacancy_ids", set()) or set()
    if shared_vacancies:
        clauses.append(Candidate.vacancy_id.in_(shared_vacancies))
    return or_(*clauses)


# ------- helpers -------
def _parse_dt(value: Optional[str], *, end_of_day: bool = False) -> Optional[datetime]:
    if not value:
        return None
    # поддержим и YYYY-MM-DD, и полные ISO-датавремена
    try:
        # полные ISO, например 2025-08-14T10:25:00
        return _with_day_end(datetime.fromisoformat(value), end_of_day=end_of_day)
    except Exception:
        # только дата 2025-08-14
        try:
            return _with_day_end(datetime.fromisoformat(value + "T00:00:00"), end_of_day=end_of_day)
        except Exception:
            return None


def _with_day_end(dt: datetime, *, end_of_day: bool) -> datetime:
    if not end_of_day:
        return dt
    if (
        dt.hour == 0
        and dt.minute == 0
        and dt.second == 0
        and dt.microsecond == 0
    ):
        return dt.replace(hour=23, minute=59, second=59, microsecond=999_999)
    return dt


def _apply_period_filters(
    stmt, date_from: Optional[datetime], date_to: Optional[datetime], by: str
):
    # by=created|updated — выбираем по какому полю фильтровать
    col = Candidate.created_at if by == "created" else Candidate.updated_at
    if date_from:
        stmt = stmt.where(col >= date_from)
    if date_to:
        stmt = stmt.where(col <= date_to)
    return stmt


# ------- /overview (как было, оставим без изменений) -------
@router.get("/analytics/overview")
async def overview(db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant)):
    db, tenant_id = db_tenant
    tenant_id_str = str(tenant_id)
    visibility = get_tenant_visibility(db, tenant_id_str)
    scope_clause = _candidate_scope_clause(tenant_id_str, visibility)

    total_stmt = select(func.count()).select_from(Candidate).where(scope_clause)
    total = (await db.execute(total_stmt)).scalar_one()

    # по стадиям
    rows = (
        await db.execute(
            select(Candidate.stage, func.count())
            .where(scope_clause)
            .group_by(Candidate.stage)
            .order_by(func.count().desc())
        )
    ).all()
    by_stage = {
        (s.value if isinstance(s, CandidateStage) else str(s)): cnt for s, cnt in rows
    }

    # считаем языки без БД-специфичных функций (кросс-БД)
    lang_counter: TCounter[str] = Counter()
    # забираем только колонку languages
    langs_rows = (await db.execute(select(Candidate.languages).where(scope_clause))).all()
    for (langs,) in langs_rows:
        if not langs:
            continue
        # поддержим как список строк, так и строку с запятыми
        if isinstance(langs, (list, tuple)):
            lang_counter.update([str(x or "") for x in langs])
        else:
            # если пришла строка, разбиваем по запятым
            parts = [p.strip() for p in str(langs).split(",")]
            lang_counter.update([p for p in parts if p])
    by_language = dict(sorted(((k, int(v)) for k, v in lang_counter.items()), key=lambda x: -x[1]))

    return {"total": total, "by_stage": by_stage, "by_language": by_language}


# ------- /funnel -------
@router.get("/analytics/funnel")
async def funnel(
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    date_from: Optional[str] = Query(
        None, alias="from", description="ISO дата/время начала (включительно)"
    ),
    date_to: Optional[str] = Query(
        None, alias="to", description="ISO дата/время конца (включительно)"
    ),
    by: str = Query(
        "created",
        pattern="^(created|updated)$",
        description="created|updated — по какому полю фильтровать",
    ),
):
    db, tenant_id = db_tenant
    tenant_id_str = str(tenant_id)
    visibility = get_tenant_visibility(db, tenant_id_str)
    scope_clause = _candidate_scope_clause(tenant_id_str, visibility)
    dfrom = _parse_dt(date_from)
    dto = _parse_dt(date_to, end_of_day=True)

    base = select(Candidate.stage, func.count()).select_from(Candidate).where(scope_clause)
    base = _apply_period_filters(base, dfrom, dto, by)
    base = base.group_by(Candidate.stage)

    res = (await db.execute(base)).all()
    counters = {
        (s.value if isinstance(s, CandidateStage) else str(s)): cnt for s, cnt in res
    }

    # упорядочим по enum
    stages: List[Dict[str, Any]] = []
    for st in CandidateStage:
        name = st.value
        stages.append({"name": name, "count": int(counters.get(name, 0))})

    return {
        "period": {
            "from": dfrom.isoformat() if dfrom else None,
            "to": dto.isoformat() if dto else None,
        },
        "by": by,
        "stages": stages,
    }


# ------- /by-manager -------
@router.get("/analytics/by-manager")
async def by_manager(
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    date_from: Optional[str] = Query(None, alias="from"),
    date_to: Optional[str] = Query(None, alias="to"),
    by: str = Query("created", pattern="^(created|updated)$"),
):
    db, tenant_id = db_tenant
    tenant_id_str = str(tenant_id)
    visibility = get_tenant_visibility(db, tenant_id_str)
    scope_clause = _candidate_scope_clause(tenant_id_str, visibility)
    dfrom = _parse_dt(date_from)
    dto = _parse_dt(date_to, end_of_day=True)

    # totals по менеджерам
    recruiter_alias = aliased(User)

    totals_stmt = (
        select(
            Candidate.manager,
            Candidate.recruiter_id,
            recruiter_alias.full_name.label("recruiter_name"),
            recruiter_alias.short_id.label("recruiter_short"),
            recruiter_alias.email.label("recruiter_email"),
            func.count(),
        )
        .select_from(Candidate)
        .join(recruiter_alias, recruiter_alias.id == Candidate.recruiter_id, isouter=True)
        .where(scope_clause)
    )
    totals_stmt = _apply_period_filters(totals_stmt, dfrom, dto, by).group_by(
        Candidate.manager,
        Candidate.recruiter_id,
        recruiter_alias.full_name,
        recruiter_alias.short_id,
        recruiter_alias.email,
    )
    totals = (await db.execute(totals_stmt)).all()

    # распределение по стадиям на менеджера
    dist_stmt = (
        select(
            Candidate.manager,
            Candidate.recruiter_id,
            Candidate.stage,
            func.count(),
        )
        .select_from(Candidate)
        .where(scope_clause)
    )
    dist_stmt = _apply_period_filters(dist_stmt, dfrom, dto, by).group_by(
        Candidate.manager, Candidate.recruiter_id, Candidate.stage
    )
    dist = (await db.execute(dist_stmt)).all()

    by_mgr: Dict[str, Dict[str, Any]] = {}

    by_mgr: Dict[str, Dict[str, Any]] = {}

    def _resolve_label(
        manager_raw: Optional[str],
        recruiter_full: Optional[str],
        recruiter_short: Optional[str],
        recruiter_email: Optional[str],
        recruiter_id: Optional[str],
    ) -> str:
        if manager_raw:
            return manager_raw
        for val in (recruiter_full, recruiter_short, recruiter_email, recruiter_id):
            if val and str(val).strip():
                return str(val).strip()
        return "—"

    def _key(manager_raw: Optional[str], recruiter_id: Optional[str]) -> str:
        return manager_raw or recruiter_id or "—"

    for mgr, recruiter_id, recruiter_name, recruiter_short, recruiter_email, cnt in totals:
        key = _key(mgr, recruiter_id)
        label = _resolve_label(mgr, recruiter_name, recruiter_short, recruiter_email, recruiter_id)
        by_mgr[key] = {"manager": label, "total": int(cnt), "by_stage": {}, "hired": 0}

    for mgr, recruiter_id, stage, cnt in dist:
        key = _key(mgr, recruiter_id)
        if key not in by_mgr:
            label = _resolve_label(mgr, None, None, None, recruiter_id)
            by_mgr[key] = {"manager": label, "total": 0, "by_stage": {}, "hired": 0}
        stage_name = stage.value if isinstance(stage, CandidateStage) else str(stage)
        by_mgr[key]["by_stage"][stage_name] = int(cnt)
        if stage_name == CandidateStage.HIRED.value:
            by_mgr[key]["hired"] = int(cnt)

    # чтобы были все стадии в словаре by_stage (с нулями)
    for v in by_mgr.values():
        for st in CandidateStage:
            v["by_stage"].setdefault(st.value, 0)

    items = sorted(by_mgr.values(), key=lambda x: (-x["total"], x["manager"]))
    return {
        "period": {
            "from": dfrom.isoformat() if dfrom else None,
            "to": dto.isoformat() if dto else None,
        },
        "by": by,
        "items": items,
    }


# ------- /analytics/export (оставим простой CSV-дашьборд) -------
@router.get("/analytics/export")
async def analytics_export(db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant)):
    db, tenant_id = db_tenant
    import csv
    import io

    tenant_id_str = str(tenant_id)
    visibility = get_tenant_visibility(db, tenant_id_str)
    scope_clause = _candidate_scope_clause(tenant_id_str, visibility)

    total = (await db.execute(select(func.count()).select_from(Candidate).where(scope_clause))).scalar_one()
    stage_rows = (
        await db.execute(
            select(Candidate.stage, func.count()).where(scope_clause).group_by(Candidate.stage)
        )
    ).all()

    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["total", total])
    w.writerow([])
    w.writerow(["stage", "count"])
    for s, cnt in stage_rows:
        name = s.value if isinstance(s, CandidateStage) else str(s)
        w.writerow([name, int(cnt)])

    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=analytics.csv"},
    )


# ------- /analytics/candidate-slices -------
@router.get("/analytics/candidate-slices")
async def candidate_slices(
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    date_from: Optional[str] = Query(None, alias="from"),
    date_to: Optional[str] = Query(None, alias="to"),
    by: str = Query(
        "created",
        pattern="^(created|updated)$",
        description="created|updated — по какому полю фильтровать",
    ),
    stages: Optional[List[str]] = Query(
        None,
        description="Список стадий через запятую/повтор параметра (codes).",
    ),
    vacancy_id: Optional[List[str]] = Query(
        None,
        alias="vacancy_id",
        description="ID вакансии (можно несколько: повторить параметр или передать через запятую).",
    ),
    limit: int = Query(
        20,
        ge=5,
        le=200,
        description="Максимальное число строк в агрегированных таблицах.",
    ),
):
    db, tenant_id = db_tenant
    tenant_id_str = str(tenant_id)
    visibility = get_tenant_visibility(db, tenant_id_str)
    scope_clause = _candidate_scope_clause(tenant_id_str, visibility)
    dfrom = _parse_dt(date_from)
    dto = _parse_dt(date_to, end_of_day=True)

    manager_alias = aliased(User)
    recruiter_alias = aliased(User)

    stmt = (
        select(
            Candidate.id,
            Candidate.stage,
            Candidate.status_reason,
            Candidate.source,
            Candidate.extra,
            Candidate.personal_data,
            Candidate.origin,
            Candidate.manager,
            Candidate.recruiter_id,
            Candidate.created_at,
            Candidate.updated_at,
            Company.name.label("company_name"),
            Vacancy.title.label("vacancy_title"),
            recruiter_alias.full_name.label("recruiter_name"),
            recruiter_alias.short_id.label("recruiter_short"),
            recruiter_alias.email.label("recruiter_email"),
            manager_alias.full_name.label("manager_full"),
            manager_alias.short_id.label("manager_short"),
            manager_alias.email.label("manager_email"),
        )
        .select_from(Candidate)
        .outerjoin(Company, Candidate.company_id == Company.id)
        .outerjoin(Vacancy, Candidate.vacancy_id == Vacancy.id)
        .outerjoin(recruiter_alias, recruiter_alias.id == Candidate.recruiter_id)
        .outerjoin(manager_alias, manager_alias.id == Candidate.manager)
        .where(scope_clause)
        .where(Candidate.deleted_at.is_(None))
    )
    stmt = _apply_period_filters(stmt, dfrom, dto, by)

    stage_filters: list[str] = []
    if stages:
        for value in stages:
            if not value:
                continue
            parts = [p.strip() for p in value.split(",") if p and p.strip()]
            stage_filters.extend(parts)
    if stage_filters:
        stmt = stmt.where(Candidate.stage.in_(stage_filters))

    vacancy_filters: list[str] = []
    if vacancy_id:
        for value in vacancy_id:
            if not value:
                continue
            parts = [p.strip() for p in value.split(",") if p and p.strip()]
            vacancy_filters.extend(parts)
    if vacancy_filters:
        stmt = stmt.where(Candidate.vacancy_id.in_(vacancy_filters))

    rows = (await db.execute(stmt)).all()

    stage_counter: Counter[str] = Counter()
    company_counter: Counter[str] = Counter()
    vacancy_counter: Counter[str] = Counter()
    source_counter: Counter[str] = Counter()
    citizenship_counter: Counter[str] = Counter()
    country_counter: Counter[str] = Counter()
    company_stage_breakdown: Dict[str, Counter[str]] = defaultdict(Counter)
    vacancy_stage_breakdown: Dict[str, Counter[str]] = defaultdict(Counter)
    reason_counters: Dict[str, Counter[str]] = {
        "rejected": Counter(),
        "declined": Counter(),
    }

    snapshot: List[Dict[str, Any]] = []

    def _label(value: Optional[str]) -> str:
        return str(value).strip() if value else "—"

    def _source_label(value: Optional[str]) -> str:
        normalized = normalize_candidate_source(value)
        if normalized:
            return normalized
        return _label(value)

    def _maybe(value: Optional[str]) -> Optional[str]:
        lbl = _label(value)
        return lbl if lbl != "—" else None

    allowed_reason_stages = {"rejected", "declined"}

    for row in rows:
        (
            candidate_id,
            stage_code,
            status_reason_raw,
            source,
            extra_raw,
            personal_data_raw,
            origin_raw,
            manager_raw,
            recruiter_id,
            created_at,
            updated_at,
            company_name,
            vacancy_title,
            recruiter_name,
            recruiter_short,
            recruiter_email,
            manager_full,
            manager_short,
            manager_email,
        ) = row

        stage_code = stage_code or None
        stage_label = _stage_label(stage_code)
        stage_counter[stage_label] += 1

        company_label = _label(company_name)
        vacancy_label = _label(vacancy_title or company_name)
        origin_payload = _safe_dict(origin_raw)
        origin_hint = None
        if isinstance(origin_payload.get("source"), str):
            origin_hint = origin_payload["source"]
        elif origin_payload:
            origin_hint = next(iter(origin_payload.keys()), None)
        normalized_source = normalize_candidate_source(source or origin_hint)
        source_label = normalized_source or (_label(source) if source else "—")

        company_counter[company_label] += 1
        vacancy_counter[vacancy_label] += 1
        source_counter[source_label] += 1

        company_stage_breakdown[company_label][stage_label] += 1
        vacancy_stage_breakdown[vacancy_label][stage_label] += 1

        extra_payload = _safe_dict(extra_raw)
        personal_data = _safe_dict(personal_data_raw)

        citizenship = personal_data.get("citizenship") or extra_payload.get("citizenship")
        country = (
            personal_data.get("country")
            or personal_data.get("country_code")
            or extra_payload.get("country")
            or extra_payload.get("country_code")
        )

        citizenship_counter[_label(citizenship)] += 1
        country_counter[_label(country)] += 1

        reason_codes = _status_reason_list(status_reason_raw)
        reason_stage = stage_code if stage_code in allowed_reason_stages else None
        reason_labels: list[str] = []
        if reason_stage:
            label_map = _REASON_LABELS.get(reason_stage, {})
            dedup = []
            seen_codes = set()
            for code in reason_codes:
                if code in seen_codes:
                    continue
                seen_codes.add(code)
                label = label_map.get(code, code)
                dedup.append((code, label))
            if dedup:
                reason_labels = [label for _, label in dedup]
                for _, label in dedup:
                    reason_counters[reason_stage][label] += 1
            else:
                placeholder = "Без причины"
                reason_labels = [placeholder]
                reason_counters[reason_stage][placeholder] += 1

        manager_preferred = manager_full or manager_short or manager_email or manager_raw
        recruiter_preferred = recruiter_name or recruiter_short or recruiter_email or recruiter_id
        final_manager_label = manager_preferred or recruiter_preferred

        snapshot.append(
            {
                "id": str(candidate_id),
                "stage": stage_code,
                "stage_label": stage_label,
                "company": _maybe(company_name),
                "vacancy": _maybe(vacancy_title or company_name),
                "source": source_label if source_label != "—" else None,
                "manager": final_manager_label or None,
                "manager_name": manager_full or None,
                "manager_short": manager_short or None,
                "manager_email": manager_email or None,
                "manager_id": manager_raw,
                "recruiter_id": recruiter_id,
                "recruiter_name": recruiter_name or None,
                "recruiter_short": recruiter_short or None,
                "recruiter_email": recruiter_email or None,
                "citizenship": _maybe(citizenship),
                "country": _maybe(country),
                "status_reason_codes": reason_codes,
                "status_reason_labels": reason_labels,
                "reason_stage": reason_stage,
                "reason_stage_label": _stage_label(reason_stage) if reason_stage else None,
                "created_at": created_at.isoformat() if hasattr(created_at, "isoformat") else created_at,
                "updated_at": updated_at.isoformat() if hasattr(updated_at, "isoformat") else updated_at,
            }
        )

    def _top(counter: Counter[str], top_limit: int) -> List[Dict[str, Any]]:
        items = sorted(counter.items(), key=lambda kv: (-kv[1], kv[0]))
        return [
            {"key": key, "label": key, "count": int(count)}
            for key, count in items[:top_limit]
        ]

    def _grouped(counter: Counter[str], breakdowns: Dict[str, Counter[str]], top_limit: int):
        items = sorted(counter.items(), key=lambda kv: (-kv[1], kv[0]))[:top_limit]
        result: List[Dict[str, Any]] = []
        for key, total in items:
            stage_counts = breakdowns.get(key, {})
            breakdown = {
                stage: int(stage_counts.get(stage, 0))
                for stage in _ORDERED_STAGE_LABELS
                if stage_counts.get(stage)
            }
            result.append(
                {
                    "key": key,
                    "label": key,
                    "count": int(total),
                    "by_stage": breakdown,
                }
            )
        return result

    top_limit = max(5, min(limit, 200))
    list_limit = max(10, min(limit * 2, 200))

    ordered_stage_set = set(_ORDERED_STAGE_LABELS)
    stage_rows: List[Dict[str, Any]] = []
    for label in _ORDERED_STAGE_LABELS:
        count = int(stage_counter.get(label, 0))
        if count:
            stage_rows.append({"key": label, "label": label, "count": count})
    extra_stages = [
        (label, count)
        for label, count in stage_counter.items()
        if label not in ordered_stage_set
    ]
    stage_rows.extend(
        {"key": label, "label": label, "count": int(count)}
        for label, count in sorted(extra_stages, key=lambda kv: (-kv[1], kv[0]))
    )

    return {
        "period": {
            "from": dfrom.isoformat() if dfrom else None,
            "to": dto.isoformat() if dto else None,
        },
        "by": by,
        "total": len(snapshot),
        "stages": stage_rows,
        "companies": _grouped(company_counter, company_stage_breakdown, top_limit),
        "vacancies": _grouped(vacancy_counter, vacancy_stage_breakdown, top_limit),
        "sources": _top(source_counter, list_limit),
        "citizenships": _top(citizenship_counter, list_limit),
        "countries": _top(country_counter, list_limit),
        "reasons": {
            key: _top(counter, list_limit)
            for key, counter in reason_counters.items()
        },
        "snapshot": snapshot,
    }
