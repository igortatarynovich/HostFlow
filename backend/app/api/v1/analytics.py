from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, time, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional, Literal, Counter as TCounter
import json

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import func, select, or_, and_, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased, selectinload
from uuid import UUID

from backend.app.core.cache import cache_get, cache_set
from backend.app.db.deps import get_db_with_tenant
from backend.app.auth.deps import UserCtx, get_current_user
from backend.app.models import (
    ActivityLog,
    Candidate,
    CandidateHandoff,
    Company,
    ContactAttempt,
    Document,
    Lead,
    ServiceOrder,
    Tenant,
    User,
    Vacancy,
)
from backend.app.models.additional_service import Service, ServiceItem
from backend.app.models.tenant import TenantLink
from backend.app.services.handoff import is_client_tenant_for_list
from backend.app.models.enums import CandidateStage
from backend.app.constants.stages import (
    LABELS as STAGE_LABELS,
    STATUS_REASON_CHOICES,
    ORDER as STAGE_ORDER,
    STAGE_META as STAGE_META_CONST,
)
from backend.app.services.tenant_visibility import TenantVisibility, get_tenant_visibility
from backend.app.services.source_labels import normalize_candidate_source
from backend.app.services.audit import log_activity
from backend.app.api.v1.candidates import repo as candidates_repo
from backend.app.api.v1.candidates.repo import _candidate_scope_clause as repo_scope_clause

router = APIRouter(tags=["analytics"])


_REASON_LABELS = {
    stage: {item["code"]: item["label"] for item in items}
    for stage, items in STATUS_REASON_CHOICES.items()
}


_CLIENT_KIND_ALIASES = {
    "client",
    "customer",
    "заказчик",
    "клиент",
}

_COUNTERPARTY_KIND_ALIASES = {
    "counterparty",
    "vendor",
    "supplier",
    "contractor",
    "subcontractor",
    "partner",
    "исполнитель",
    "подрядчик",
    "контрагент",
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


def _tenant_business_type(tenant: Optional[Tenant]) -> str:
    if tenant is None:
        return "agency"
    settings_payload = tenant.settings if isinstance(tenant.settings, dict) else {}
    raw_business_type = settings_payload.get("business_type")
    normalized = str(raw_business_type or "").strip().lower()
    if normalized in {"agency", "employer", "services"}:
        return normalized
    tenant_type = str(getattr(getattr(tenant, "type", None), "value", getattr(tenant, "type", ""))).strip().lower()
    if tenant_type == "company":
        return "employer"
    return "agency"


def _normalize_company_kind(extra_payload: Any) -> str:
    extra = _safe_dict(extra_payload)
    raw_value = (
        extra.get("company_kind")
        or extra.get("company_type")
        or extra.get("kind")
        or extra.get("entity_type")
        or extra.get("segment")
        or extra.get("role")
    )
    normalized = str(raw_value or "").strip().lower()
    if normalized in _COUNTERPARTY_KIND_ALIASES:
        return "counterparty"
    if normalized in _CLIENT_KIND_ALIASES:
        return "client"
    return "unknown"


def _as_float(value: Any) -> float:
    if value is None:
        return 0.0
    if isinstance(value, Decimal):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


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

# Безопасный снимок метаданных стадий (если константа недоступна, используем пустой dict)
STAGE_META: Dict[str, Dict[str, Any]] = dict(STAGE_META_CONST or {})  # type: ignore[arg-type]


def _stage_visible_for_view(code: Optional[str], view: str) -> bool:
    """
    Определяет, должен ли этап участвовать в текущем режиме отображения пайплайна.

    view:
      - "all"    — все стадии без фильтрации
      - "agency" — только стадии, видимые агентству
      - "client" — только стадии, видимые клиенту
    """
    if not code or view == "all":
        return True
    meta = STAGE_META.get(code) or {}
    if view == "agency":
        return bool(meta.get("visible_for_agency", True))
    if view == "client":
        return bool(meta.get("visible_for_client", False))
    return True


# DEPRECATED: Use repo._candidate_scope_clause instead for client tenant support
# Keeping for backward compatibility in export endpoint
def _candidate_scope_clause_legacy(tenant_id: str, visibility: TenantVisibility | None):
    clauses = [Candidate.tenant_id == tenant_id]
    shared_vacancies = getattr(visibility, "shared_vacancy_ids", set()) or set()
    shared_companies = getattr(visibility, "shared_company_ids", set()) or set()
    extra = []
    if shared_vacancies:
        extra.append(Candidate.vacancy_id.in_(shared_vacancies))
    if shared_companies:
        extra.append(Candidate.company_id.in_(shared_companies))
    if extra:
        clauses.append(or_(*extra))
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
async def overview(
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    stage_view: Optional[str] = Query(
        None,
        description="all | agency | client — режим отображения пайплайна по стадиям",
    ),
):
    db, tenant_id = db_tenant
    tenant_id_str = str(tenant_id)
    visibility = get_tenant_visibility(db, tenant_id_str)
    is_client = await is_client_tenant_for_list(db, tenant_id_str)
    effective_stage_view = stage_view or ("client" if is_client else "all")
    scope_clause = repo_scope_clause(tenant_id_str, visibility, is_client_tenant=is_client)

    total_stmt = select(func.count()).select_from(Candidate).where(
        and_(Candidate.deleted_at.is_(None), scope_clause)
    )
    total = (await db.execute(total_stmt)).scalar_one()

    # по стадиям
    rows = (
        await db.execute(
            select(Candidate.stage, func.count())
            .where(and_(Candidate.deleted_at.is_(None), scope_clause))
            .group_by(Candidate.stage)
            .order_by(func.count().desc())
        )
    ).all()
    raw_by_stage = {
        (s.value if isinstance(s, CandidateStage) else str(s)): cnt for s, cnt in rows
    }
    by_stage = {
        code: cnt
        for code, cnt in raw_by_stage.items()
        if _stage_visible_for_view(code, effective_stage_view)
    }

    # считаем языки без БД-специфичных функций (кросс-БД)
    lang_counter: TCounter[str] = Counter()
    # забираем только колонку languages
    langs_rows = (await db.execute(select(Candidate.languages).where(and_(Candidate.deleted_at.is_(None), scope_clause)))).all()
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


@router.get("/analytics/profile-summary")
async def profile_summary(
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
):
    db, tenant_id = db_tenant
    tenant_id_str = str(tenant_id)

    tenant_row = await db.execute(select(Tenant).where(Tenant.id == tenant_id_str).limit(1))
    tenant = tenant_row.scalar_one_or_none()
    business_type = _tenant_business_type(tenant)

    total_companies = int(
        (await db.execute(select(func.count()).select_from(Company).where(Company.tenant_id == tenant_id_str))).scalar_one() or 0
    )
    active_companies = int(
        (
            await db.execute(
                select(func.count()).select_from(Company).where(Company.tenant_id == tenant_id_str, Company.is_archived.is_(False))
            )
        ).scalar_one()
        or 0
    )
    total_candidates = int(
        (
            await db.execute(
                select(func.count()).select_from(Candidate).where(Candidate.tenant_id == tenant_id_str, Candidate.deleted_at.is_(None))
            )
        ).scalar_one()
        or 0
    )
    total_vacancies = int(
        (await db.execute(select(func.count()).select_from(Vacancy).where(Vacancy.tenant_id == tenant_id_str))).scalar_one() or 0
    )
    active_vacancies = int(
        (
            await db.execute(
                select(func.count()).select_from(Vacancy).where(
                    Vacancy.tenant_id == tenant_id_str,
                    Vacancy.is_archived.is_(False),
                )
            )
        ).scalar_one()
        or 0
    )
    total_leads = int(
        (await db.execute(select(func.count()).select_from(Lead).where(Lead.tenant_id == tenant_id_str))).scalar_one() or 0
    )

    service_orders_total = int(
        (
            await db.execute(
                select(func.count()).select_from(ServiceOrder).where(ServiceOrder.tenant_id == tenant_id_str)
            )
        ).scalar_one()
        or 0
    )
    service_orders_rows = (
        await db.execute(
            select(ServiceOrder.status, func.count(), func.coalesce(func.sum(ServiceOrder.total_amount), 0))
            .where(ServiceOrder.tenant_id == tenant_id_str)
            .group_by(ServiceOrder.status)
        )
    ).all()
    service_orders_by_status = {str(status): int(count or 0) for status, count, _sum in service_orders_rows}
    service_revenue_delivered = 0.0
    for status, _count, total_sum in service_orders_rows:
        if str(status) == "delivered":
            service_revenue_delivered = _as_float(total_sum)

    company_rows = (
        await db.execute(select(Company.id, Company.extra).where(Company.tenant_id == tenant_id_str))
    ).all()
    service_owner_company_rows = (
        await db.execute(
            select(ServiceOrder.company_id)
            .where(ServiceOrder.tenant_id == tenant_id_str, ServiceOrder.company_id.is_not(None))
            .distinct()
        )
    ).all()
    client_company_ids = {str(row[0]) for row in service_owner_company_rows if row and row[0]}

    clients_count = 0
    counterparties_count = 0
    unknown_count = 0
    for company_id, extra_payload in company_rows:
        if company_id and str(company_id) in client_company_ids:
            clients_count += 1
            continue
        kind = _normalize_company_kind(extra_payload)
        if kind == "counterparty":
            counterparties_count += 1
        elif kind == "client":
            clients_count += 1
        else:
            unknown_count += 1
            # Для services неизвестный тип считаем клиентом по умолчанию.
            clients_count += 1

    service_in_progress = sum(
        int(service_orders_by_status.get(key, 0))
        for key in ("approved", "scheduled", "in_progress")
    )
    service_delivered = int(service_orders_by_status.get("delivered", 0))

    profile = {
        "business_type": business_type,
        "generated_at": datetime.utcnow().isoformat(),
        "kpis": {},
        "datasets": {},
    }

    if business_type == "services":
        profile["kpis"] = {
            "companies_total": total_companies,
            "companies_active": active_companies,
            "clients_total": clients_count,
            "counterparties_total": counterparties_count,
            "service_orders_total": service_orders_total,
            "service_orders_in_progress": service_in_progress,
            "service_orders_delivered": service_delivered,
            "service_revenue_delivered": round(service_revenue_delivered, 2),
            "leads_total": total_leads,
        }
        profile["datasets"] = {
            "primary_entities": ["clients", "counterparties", "service_orders", "leads"],
            "unknown_company_classification": unknown_count,
        }
    elif business_type == "employer":
        profile["kpis"] = {
            "vacancies_total": total_vacancies,
            "vacancies_active": active_vacancies,
            "candidates_total": total_candidates,
            "leads_total": total_leads,
            "companies_total": total_companies,
        }
        profile["datasets"] = {
            "primary_entities": ["vacancies", "candidates", "team", "communications"],
        }
    else:
        profile["kpis"] = {
            "companies_total": total_companies,
            "vacancies_active": active_vacancies,
            "candidates_total": total_candidates,
            "leads_total": total_leads,
            "service_orders_total": service_orders_total,
        }
        profile["datasets"] = {
            "primary_entities": ["clients", "candidates", "vacancies", "leads", "communications"],
        }

    return profile


@router.get("/analytics/services-overview", response_model=ServicesAnalyticsOverviewOut)
async def services_overview(
    days: int = Query(90, ge=7, le=365),
    trend_bucket: str = Query("month", pattern="^(week|month)$"),
    slice_by: str = Query("client", pattern="^(client|item|status|manager)$"),
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
):
    db, tenant_id = db_tenant
    tenant_id_str = str(tenant_id)
    rows = (
        await db.execute(
            select(ServiceOrder)
            .where(ServiceOrder.tenant_id == tenant_id_str)
            .options(
                selectinload(ServiceOrder.items).selectinload(ServiceItem.service),
                selectinload(ServiceOrder.items).selectinload(ServiceItem.schedules),
                selectinload(ServiceOrder.items).selectinload(ServiceItem.attachments),
            )
            .order_by(ServiceOrder.updated_at.desc())
        )
    ).scalars().all()

    now = datetime.utcnow()
    cutoff = now - timedelta(days=30)
    trends_cutoff = now - timedelta(days=days)

    revenue = 0.0
    estimated_cost = 0.0
    actual_cost = 0.0
    delivered_orders = 0
    cancelled_orders = 0
    confirmed_items = 0
    estimated_items = 0
    missing_items = 0
    status_counter: TCounter[str] = Counter()
    top_items_map: dict[str, dict[str, float | int | str | None]] = {}
    top_clients_map: dict[str, dict[str, float | int | str | None]] = {}
    trend_map: dict[str, dict[str, float | int | str]] = {}
    slice_map: dict[str, dict[str, float | int | str]] = {}
    hot_orders: list[ServicesAnalyticsHotOrderOut] = []
    last30_total = 0
    last30_delivered = 0
    last30_cancelled = 0

    def owner_label_and_kind(order: ServiceOrder) -> tuple[str, str]:
        if order.company_id:
            return (f"Company {str(order.company_id)[:8]}", "company")
        if order.candidate_id:
            return (f"Candidate {str(order.candidate_id)[:8]}", "candidate")
        if order.vacancy_id:
            return (f"Vacancy {str(order.vacancy_id)[:8]}", "vacancy")
        return ("Unknown", "unknown")

    def manager_label(order: ServiceOrder) -> str:
        assigned = str(getattr(order, "assigned_to", "") or "").strip()
        return f"Manager {assigned[:8]}" if assigned else "Unassigned"

    def trend_key(order: ServiceOrder) -> str:
        dt = order.created_at or now
        if trend_bucket == "week":
            iso_year, iso_week, _ = dt.isocalendar()
            return f"{iso_year}-W{iso_week:02d}"
        return dt.strftime("%Y-%m")

    for order in rows:
        status_value = str(order.status)
        status_counter[status_value] += 1
        order_revenue = _as_float(order.total_amount)
        revenue += order_revenue
        if status_value == "delivered":
            delivered_orders += 1
        if status_value in {"cancelled", "refunded"}:
            cancelled_orders += 1
        if order.created_at and order.created_at >= cutoff:
            last30_total += 1
            if status_value == "delivered":
                last30_delivered += 1
            if status_value in {"cancelled", "refunded"}:
                last30_cancelled += 1

        client_label, owner_kind = owner_label_and_kind(order)
        owner_id = str(order.company_id or order.candidate_id or order.vacancy_id or "") or None
        slice_label = (
            client_label
            if slice_by == "client"
            else manager_label(order)
            if slice_by == "manager"
            else status_value
            if slice_by == "status"
            else None
        )
        client_entry = top_clients_map.get(client_label) or {
            "label": client_label,
            "owner_kind": owner_kind,
            "owner_id": owner_id,
            "revenue": 0.0,
            "profit": 0.0,
            "orders": 0,
        }
        client_entry["revenue"] = float(client_entry["revenue"]) + order_revenue
        client_entry["orders"] = int(client_entry["orders"]) + 1

        has_schedule_issue = False
        has_docs_issue = False
        first_item_label = "Unknown"
        order_profit = 0.0
        for item in order.items:
            item_revenue = _as_float(item.amount)
            item_estimated_cost = _as_float(getattr(item, "estimated_cost", 0))
            raw_actual_cost = getattr(item, "actual_cost", None)
            item_actual_cost = _as_float(raw_actual_cost) if raw_actual_cost is not None else 0.0
            estimated_cost += item_estimated_cost
            if raw_actual_cost is not None:
                actual_cost += item_actual_cost
                confirmed_items += 1
            elif str(getattr(item, "cost_status", "missing")) == "estimated" or item_estimated_cost > 0:
                estimated_items += 1
            else:
                missing_items += 1
            item_cost = item_actual_cost if raw_actual_cost is not None else item_estimated_cost
            item_profit = item_revenue - item_cost
            order_profit += item_profit
            client_entry["profit"] = float(client_entry["profit"]) + item_profit

            item_label = (
                str(getattr(getattr(item, "service", None), "name", None) or "")
                or str(getattr(getattr(item, "service", None), "code", None) or "")
                or "Unknown"
            )
            if first_item_label == "Unknown":
                first_item_label = item_label
            item_entry = top_items_map.get(item_label) or {
                "service_id": str(getattr(item, "service_id", "") or "") or None,
                "label": item_label,
                "total": 0,
                "pending": 0,
                "revenue": 0.0,
                "profit": 0.0,
            }
            item_entry["total"] = int(item_entry["total"]) + 1
            if str(item.status) != "delivered":
                item_entry["pending"] = int(item_entry["pending"]) + 1
            item_entry["revenue"] = float(item_entry["revenue"]) + item_revenue
            item_entry["profit"] = float(item_entry["profit"]) + item_profit
            top_items_map[item_label] = item_entry

            if slice_by == "item":
                slice_label = item_label

            has_schedule_issue = has_schedule_issue or len(getattr(item, "schedules", []) or []) == 0
            has_docs_issue = has_docs_issue or (
                bool(getattr(item, "required_documents", None)) and len(getattr(item, "attachments", []) or []) == 0
            )

        top_clients_map[client_label] = client_entry

        if order.created_at and order.created_at >= trends_cutoff:
            trend_entry = trend_map.get(trend_key(order)) or {
                "bucket": trend_key(order),
                "orders": 0,
                "revenue": 0.0,
                "profit": 0.0,
                "delivered": 0,
            }
            trend_entry["orders"] = int(trend_entry["orders"]) + 1
            trend_entry["revenue"] = float(trend_entry["revenue"]) + order_revenue
            trend_entry["profit"] = float(trend_entry["profit"]) + order_profit
            if status_value == "delivered":
                trend_entry["delivered"] = int(trend_entry["delivered"]) + 1
            trend_map[trend_key(order)] = trend_entry

        if slice_label:
            slice_entry = slice_map.get(slice_label) or {
                "label": slice_label,
                "slice_kind": slice_by,
                "slice_value": owner_id if slice_by == "client" else slice_label,
                "owner_kind": owner_kind if slice_by == "client" else None,
                "orders": 0,
                "revenue": 0.0,
                "profit": 0.0,
            }
            slice_entry["orders"] = int(slice_entry["orders"]) + 1
            slice_entry["revenue"] = float(slice_entry["revenue"]) + order_revenue
            slice_entry["profit"] = float(slice_entry["profit"]) + order_profit
            slice_map[slice_label] = slice_entry

        if status_value not in {"delivered", "refunded"} and order.items:
            hot_orders.append(
                ServicesAnalyticsHotOrderOut(
                    order_id=str(order.id),
                    label=first_item_label,
                    reason="documents" if has_docs_issue else "schedule" if has_schedule_issue else "status",
                    owner_kind=owner_kind,
                    status=status_value,
                    updated_at=order.updated_at.isoformat() if order.updated_at else None,
                )
            )

    cost_base = actual_cost or estimated_cost
    gross_profit = revenue - cost_base
    gross_margin = round((gross_profit / revenue) * 100) if revenue > 0 else 0
    total_cost_items = confirmed_items + estimated_items + missing_items
    coverage = round((confirmed_items / total_cost_items) * 100) if total_cost_items else 0
    last30_rate = round((last30_cancelled / last30_total) * 100) if last30_total else 0

    return ServicesAnalyticsOverviewOut(
        generated_at=now.isoformat(),
        totals={
            "orders_total": len(rows),
            "delivered_orders": delivered_orders,
            "cancelled_orders": cancelled_orders,
            "revenue": round(revenue, 2),
            "estimated_cost": round(estimated_cost, 2),
            "actual_cost": round(actual_cost, 2),
            "gross_profit": round(gross_profit, 2),
            "gross_margin": gross_margin,
            "cost_coverage": coverage,
        },
        last30={
            "total": last30_total,
            "delivered": last30_delivered,
            "cancelled": last30_cancelled,
            "cancellation_rate": last30_rate,
        },
        data_quality={
            "confirmed_items": confirmed_items,
            "estimated_items": estimated_items,
            "missing_items": missing_items,
        },
        status_breakdown=[
            ServicesAnalyticsStatusRowOut(status=status, count=count)
            for status, count in sorted(status_counter.items(), key=lambda item: item[1], reverse=True)
        ],
        top_items=[
            ServicesAnalyticsTopItemOut(
                service_id=str(entry["service_id"]) if entry.get("service_id") else None,
                label=str(entry["label"]),
                total=int(entry["total"]),
                pending=int(entry["pending"]),
                revenue=round(float(entry["revenue"]), 2),
                profit=round(float(entry["profit"]), 2),
            )
            for entry in sorted(top_items_map.values(), key=lambda item: (float(item["profit"]), float(item["revenue"])), reverse=True)[:5]
        ],
        top_clients=[
            ServicesAnalyticsTopClientOut(
                owner_kind=str(entry["owner_kind"]),
                owner_id=str(entry["owner_id"]) if entry.get("owner_id") else None,
                label=str(entry["label"]),
                revenue=round(float(entry["revenue"]), 2),
                profit=round(float(entry["profit"]), 2),
                orders=int(entry["orders"]),
            )
            for entry in sorted(top_clients_map.values(), key=lambda item: (float(item["profit"]), float(item["revenue"])), reverse=True)[:5]
        ],
        hot_orders=sorted(hot_orders, key=lambda item: item.updated_at or "", reverse=True)[:5],
        trends=[
            {
                "bucket": str(entry["bucket"]),
                "orders": int(entry["orders"]),
                "delivered": int(entry["delivered"]),
                "revenue": round(float(entry["revenue"]), 2),
                "profit": round(float(entry["profit"]), 2),
            }
            for entry in sorted(trend_map.values(), key=lambda item: str(item["bucket"]))
        ],
        slices=[
            {
                "label": str(entry["label"]),
                "slice_kind": entry.get("slice_kind"),
                "slice_value": entry.get("slice_value"),
                "owner_kind": entry.get("owner_kind"),
                "orders": int(entry["orders"]),
                "revenue": round(float(entry["revenue"]), 2),
                "profit": round(float(entry["profit"]), 2),
            }
            for entry in sorted(slice_map.values(), key=lambda item: (float(item["profit"]), float(item["revenue"])), reverse=True)[:10]
        ],
    )


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
    stage_view: Optional[str] = Query(
        None,
        description="all | agency | client — режим отображения пайплайна по стадиям",
    ),
):
    db, tenant_id = db_tenant
    tenant_id_str = str(tenant_id)
    visibility = get_tenant_visibility(db, tenant_id_str)
    is_client = await is_client_tenant_for_list(db, tenant_id_str)
    scope_clause = repo_scope_clause(tenant_id_str, visibility, is_client_tenant=is_client)
    effective_stage_view = stage_view or ("client" if is_client else "all")
    dfrom = _parse_dt(date_from)
    dto = _parse_dt(date_to, end_of_day=True)

    base = select(Candidate.stage, func.count()).select_from(Candidate).where(and_(Candidate.deleted_at.is_(None), scope_clause))
    base = _apply_period_filters(base, dfrom, dto, by)
    base = base.group_by(Candidate.stage)

    res = (await db.execute(base)).all()
    raw_counters = {
        (s.value if isinstance(s, CandidateStage) else str(s)): cnt for s, cnt in res
    }
    counters = {
        code: cnt
        for code, cnt in raw_counters.items()
        if _stage_visible_for_view(code, effective_stage_view)
    }

    # упорядочим по enum
    stages: List[Dict[str, Any]] = []
    for st in CandidateStage:
        name = st.value
        if not _stage_visible_for_view(name, effective_stage_view):
            continue
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
    stage_view: Optional[str] = Query(
        None,
        description="all | agency | client — режим отображения пайплайна по стадиям",
    ),
):
    db, tenant_id = db_tenant
    tenant_id_str = str(tenant_id)
    visibility = get_tenant_visibility(db, tenant_id_str)
    is_client = await is_client_tenant_for_list(db, tenant_id_str)
    scope_clause = repo_scope_clause(tenant_id_str, visibility, is_client_tenant=is_client)
    effective_stage_view = stage_view or ("client" if is_client else "all")
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
        .where(and_(Candidate.deleted_at.is_(None), scope_clause))
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
        .where(and_(Candidate.deleted_at.is_(None), scope_clause))
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
        if not _stage_visible_for_view(stage_name, effective_stage_view):
            continue
        by_mgr[key]["by_stage"][stage_name] = int(cnt)
        if stage_name == CandidateStage.HIRED.value:
            by_mgr[key]["hired"] = int(cnt)

    # чтобы были все стадии в словаре by_stage (с нулями)
    for v in by_mgr.values():
        for st in CandidateStage:
            if not _stage_visible_for_view(st.value, effective_stage_view):
                continue
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


# ------- /analytics/handoff-stats -------
@router.get("/analytics/handoff-stats")
async def handoff_stats(
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    date_from: Optional[str] = Query(None, alias="from"),
    date_to: Optional[str] = Query(None, alias="to"),
):
    """Aggregate handoff stats: for agency by agency_tenant_id, for client by client_tenant_id / client_company_id (requested_at in period)."""
    db, tenant_id = db_tenant
    tenant_id_str = str(tenant_id)
    dfrom = _parse_dt(date_from)
    dto = _parse_dt(date_to, end_of_day=True)

    is_client = await is_client_tenant_for_list(db, tenant_id_str)
    if is_client:
        client_company_subq = select(TenantLink.handoff_include_company_id).where(
            TenantLink.client_tenant_id == tenant_id_str,
            TenantLink.handoff_include_company_id.isnot(None),
        )
        base = select(CandidateHandoff).where(
            or_(
                CandidateHandoff.client_tenant_id == tenant_id_str,
                CandidateHandoff.client_company_id.in_(client_company_subq),
            )
        )
    else:
        base = select(CandidateHandoff).where(
            CandidateHandoff.agency_tenant_id == tenant_id_str,
        )
    if dfrom:
        base = base.where(CandidateHandoff.requested_at >= dfrom)
    if dto:
        base = base.where(CandidateHandoff.requested_at <= dto)

    rows = (await db.execute(base)).scalars().all()

    total_requested = len(rows)
    total_accepted = sum(1 for h in rows if h.status == "accepted")
    total_rejected = sum(1 for h in rows if h.status == "rejected")
    total_returned = sum(1 for h in rows if h.status == "returned")

    by_client: Dict[str, Dict[str, int]] = {}
    for h in rows:
        key = h.client_tenant_id or h.client_company_id or "unknown"
        if key not in by_client:
            by_client[key] = {"requested": 0, "accepted": 0, "rejected": 0, "returned": 0}
        by_client[key]["requested"] += 1
        if h.status == "accepted":
            by_client[key]["accepted"] += 1
        elif h.status == "rejected":
            by_client[key]["rejected"] += 1
        elif h.status == "returned":
            by_client[key]["returned"] += 1

    return {
        "total_requested": total_requested,
        "total_accepted": total_accepted,
        "total_rejected": total_rejected,
        "total_returned": total_returned,
        "by_client": [{"client_id": k, **v} for k, v in by_client.items()],
        "period": {
            "from": dfrom.isoformat() if dfrom else None,
            "to": dto.isoformat() if dto else None,
        },
    }


# ------- /analytics/contact-attempt-stats -------
@router.get("/analytics/contact-attempt-stats")
async def contact_attempt_stats(
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    date_from: Optional[str] = Query(None, alias="from"),
    date_to: Optional[str] = Query(None, alias="to"),
):
    """Aggregate contact attempt stats for candidates in tenant (filter by candidate created_at)."""
    db, tenant_id = db_tenant
    tenant_id_str = str(tenant_id)
    visibility = get_tenant_visibility(db, tenant_id_str)
    is_client = await is_client_tenant_for_list(db, tenant_id_str)
    scope_clause = repo_scope_clause(tenant_id_str, visibility, is_client_tenant=is_client)
    dfrom = _parse_dt(date_from)
    dto = _parse_dt(date_to, end_of_day=True)

    cand_subq = (
        select(Candidate.id)
        .where(and_(Candidate.deleted_at.is_(None), scope_clause))
    )
    if dfrom:
        cand_subq = cand_subq.where(Candidate.created_at >= dfrom)
    if dto:
        cand_subq = cand_subq.where(Candidate.created_at <= dto)

    attempts_stmt = (
        select(ContactAttempt.candidate_id, ContactAttempt.result, func.count())
        .where(ContactAttempt.candidate_id.in_(cand_subq.scalar_subquery()))
        .group_by(ContactAttempt.candidate_id, ContactAttempt.result)
    )
    attempt_rows = (await db.execute(attempts_stmt)).all()

    total_attempts = sum(cnt for _, _, cnt in attempt_rows)
    by_result: Dict[str, int] = {}
    cand_attempt_counts: Dict[str, int] = {}
    for cand_id, result, cnt in attempt_rows:
        by_result[result] = by_result.get(result, 0) + cnt
        cand_attempt_counts[cand_id] = cand_attempt_counts.get(cand_id, 0) + cnt

    candidates_with_attempts = len(cand_attempt_counts)
    avg_per_candidate = (
        total_attempts / candidates_with_attempts if candidates_with_attempts else 0
    )
    limit_reached_count = sum(1 for c in cand_attempt_counts.values() if c >= 3)

    return {
        "total_attempts": total_attempts,
        "candidates_with_attempts": candidates_with_attempts,
        "avg_per_candidate": round(avg_per_candidate, 2),
        "limit_reached_count": limit_reached_count,
        "by_result": by_result,
        "period": {
            "from": dfrom.isoformat() if dfrom else None,
            "to": dto.isoformat() if dto else None,
        },
    }


# ------- /analytics/document-stats -------
@router.get("/analytics/document-stats")
async def document_stats(
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    date_from: Optional[str] = Query(None, alias="from"),
    date_to: Optional[str] = Query(None, alias="to"),
):
    """Aggregate document stats for candidates in tenant (filter by candidate created_at)."""
    db, tenant_id = db_tenant
    tenant_id_str = str(tenant_id)
    visibility = get_tenant_visibility(db, tenant_id_str)
    is_client = await is_client_tenant_for_list(db, tenant_id_str)
    scope_clause = repo_scope_clause(tenant_id_str, visibility, is_client_tenant=is_client)
    dfrom = _parse_dt(date_from)
    dto = _parse_dt(date_to, end_of_day=True)

    cand_subq = (
        select(Candidate.id)
        .where(and_(Candidate.deleted_at.is_(None), scope_clause))
    )
    if dfrom:
        cand_subq = cand_subq.where(Candidate.created_at >= dfrom)
    if dto:
        cand_subq = cand_subq.where(Candidate.created_at <= dto)

    docs_stmt = (
        select(Document.status, Document.kind, Document.candidate_id)
        .where(Document.tenant_id == tenant_id_str)
        .where(Document.candidate_id.in_(cand_subq.scalar_subquery()))
        .where(Document.deleted_at.is_(None))
    )
    doc_rows = (await db.execute(docs_stmt)).all()

    by_status: Dict[str, int] = {}
    by_kind: Dict[str, int] = {}
    total_docs = 0
    ready_statuses = {"completed", "approved", "received", "delivered", "verified"}
    candidates_with_complete: set[str] = set()
    cand_doc_statuses: Dict[str, set[str]] = {}

    for status, kind, cand_id in doc_rows:
        s = str(status.value) if hasattr(status, "value") else str(status)
        k = str(kind.value) if hasattr(kind, "value") else str(kind)
        by_status[s] = by_status.get(s, 0) + 1
        by_kind[k] = by_kind.get(k, 0) + 1
        total_docs += 1
        if cand_id not in cand_doc_statuses:
            cand_doc_statuses[cand_id] = set()
        cand_doc_statuses[cand_id].add(s)

    for cand_id, statuses in cand_doc_statuses.items():
        if any(st in ready_statuses for st in statuses):
            candidates_with_complete.add(cand_id)

    return {
        "total_docs": total_docs,
        "by_status": by_status,
        "by_kind": by_kind,
        "candidates_with_complete_docs": len(candidates_with_complete),
        "period": {
            "from": dfrom.isoformat() if dfrom else None,
            "to": dto.isoformat() if dto else None,
        },
    }


# ------- /analytics/export (оставим простой CSV-дашьборд) -------
@router.get("/analytics/export")
async def analytics_export(
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    stage_view: Optional[str] = Query(
        None,
        description="all | agency | client — режим отображения пайплайна по стадиям",
    ),
):
    db, tenant_id = db_tenant
    import csv
    import io

    tenant_id_str = str(tenant_id)
    visibility = get_tenant_visibility(db, tenant_id_str)
    is_client = await is_client_tenant_for_list(db, tenant_id_str)
    scope_clause = repo_scope_clause(tenant_id_str, visibility, is_client_tenant=is_client)
    effective_stage_view = stage_view or ("client" if is_client else "all")

    total = (await db.execute(select(func.count()).select_from(Candidate).where(and_(Candidate.deleted_at.is_(None), scope_clause)))).scalar_one()
    stage_rows = (
        await db.execute(
            select(Candidate.stage, func.count()).where(and_(Candidate.deleted_at.is_(None), scope_clause)).group_by(Candidate.stage)
        )
    ).all()

    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["total", total])
    w.writerow([])
    w.writerow(["stage", "count"])
    for s, cnt in stage_rows:
        name = s.value if isinstance(s, CandidateStage) else str(s)
        if not _stage_visible_for_view(name, effective_stage_view):
            continue
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
    company_id: Optional[List[str]] = Query(
        None,
        alias="company_id",
        description="ID компании (можно несколько).",
    ),
    manager_id: Optional[List[str]] = Query(
        None,
        alias="manager_id",
        description="ID менеджера (user_id или manager field, можно несколько).",
    ),
    limit: int = Query(
        20,
        ge=5,
        le=200,
        description="Максимальное число строк в агрегированных таблицах.",
    ),
    scope_tenant_id: Optional[UUID] = Query(
        None,
        description="Scope to this tenant (same as list); uses X-Tenant-Id if not set.",
    ),
    stage_view: Optional[str] = Query(
        None,
        description="all | agency | client — режим отображения пайплайна по стадиям",
    ),
):
    db, tenant_id = db_tenant
    tenant_id_str = str(tenant_id)
    scope_tenant = str(scope_tenant_id) if scope_tenant_id else tenant_id_str

    stage_filters: list[str] = []
    if stages:
        for value in stages:
            if not value:
                continue
            parts = [p.strip() for p in value.split(",") if p and p.strip()]
            stage_filters.extend(parts)
    vacancy_filters: list[str] = []
    if vacancy_id:
        for value in vacancy_id:
            if not value:
                continue
            parts = [p.strip() for p in value.split(",") if p and p.strip()]
            vacancy_filters.extend(parts)
    company_filters: list[str] = []
    if company_id:
        for value in company_id:
            if not value:
                continue
            parts = [p.strip() for p in value.split(",") if p and p.strip()]
            company_filters.extend(parts)
    manager_filters: list[str] = []
    if manager_id:
        for value in manager_id:
            if not value:
                continue
            parts = [p.strip() for p in value.split(",") if p and p.strip()]
            manager_filters.extend(parts)

    cache_params = {
        "from": date_from,
        "to": date_to,
        "by": by,
        "scope_tenant": scope_tenant,
        "stages": ",".join(sorted(stage_filters)) if stage_filters else "",
        "vacancy_id": ",".join(sorted(vacancy_filters)) if vacancy_filters else "",
        "company_id": ",".join(sorted(company_filters)) if company_filters else "",
        "manager_id": ",".join(sorted(manager_filters)) if manager_filters else "",
        "limit": limit,
    }
    cached = await cache_get("candidate-slices", scope_tenant, cache_params)
    if cached is not None:
        return cached

    try:
        await db.execute(
            text("SELECT set_config('app.tenant_id', :tid, true)"),
            {"tid": scope_tenant},
        )
    except Exception:
        pass
    visibility = get_tenant_visibility(db, scope_tenant)
    client_tenant = await is_client_tenant_for_list(db, scope_tenant)
    scope_clause = repo_scope_clause(scope_tenant, visibility, is_client_tenant=client_tenant)
    effective_stage_view = stage_view or ("client" if client_tenant else "all")
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
            Candidate.company_id,
            Company.name.label("company_name"),
            Candidate.vacancy_id,
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
        .where(and_(Candidate.deleted_at.is_(None), scope_clause))
    )
    
    # Фильтрация тестовых данных: исключаем компании и вакансии с "test", "тест", "demo" в названии
    test_patterns = ["test", "тест", "demo", "демо"]
    test_filters = []
    for pattern in test_patterns:
        test_filters.append(func.lower(Company.name).like(f"%{pattern}%"))
        test_filters.append(func.lower(Vacancy.title).like(f"%{pattern}%"))
    if test_filters:
        from sqlalchemy import not_ as sql_not
        test_condition = sql_not(or_(*test_filters))
        stmt = stmt.where(test_condition)
    
    stmt = _apply_period_filters(stmt, dfrom, dto, by)

    if stage_filters:
        stmt = stmt.where(Candidate.stage.in_(stage_filters))
    if vacancy_filters:
        stmt = stmt.where(Candidate.vacancy_id.in_(vacancy_filters))
    if company_filters:
        stmt = stmt.where(Candidate.company_id.in_(company_filters))
    if manager_filters:
        stmt = stmt.where(
            or_(
                Candidate.manager.in_(manager_filters),
                Candidate.recruiter_id.in_(manager_filters),
            )
        )

    rows = (await db.execute(stmt)).all()

    # Счётчики стадий считаем по коду, а не по русской метке,
    # чтобы фронтенд мог тянуть переводы из i18n (app.candidates.stage_labels).
    stage_counter: Counter[str] = Counter()
    company_counter: Counter[str] = Counter()
    vacancy_counter: Counter[str] = Counter()
    company_labels: Dict[str, str] = {}
    vacancy_labels: Dict[str, str] = {}
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
            company_id,
            company_name,
            vacancy_id,
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
        if not _stage_visible_for_view(stage_code, effective_stage_view):
            # всё равно добавляем snapshot, но не учитываем в стадийных агрегациях
            snapshot.append(
                {
                    "id": str(candidate_id),
                    "stage": stage_code,
                    "stage_label": stage_label,
                    "company": _maybe(company_name),
                    "company_id": str(company_id) if company_id else None,
                    "vacancy": _maybe(vacancy_title or company_name),
                    "vacancy_id": str(vacancy_id) if vacancy_id else None,
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
            continue

        # Считаем по коду; если кода нет, используем метку как "сырой" ключ.
        counter_key = str(stage_code) if stage_code else stage_label
        stage_counter[counter_key] += 1

        company_label = _label(company_name)
        company_key = str(company_id) if company_id else f"label::{company_label}"
        vacancy_label = _label(vacancy_title or company_name)
        vacancy_key = str(vacancy_id) if vacancy_id else f"label::{vacancy_label}"
        origin_payload = _safe_dict(origin_raw)
        origin_hint = None
        if isinstance(origin_payload.get("source"), str):
            origin_hint = origin_payload["source"]
        elif origin_payload:
            origin_hint = next(iter(origin_payload.keys()), None)
        normalized_source = normalize_candidate_source(source or origin_hint)
        source_label = normalized_source or (_label(source) if source else "—")

        company_counter[company_key] += 1
        vacancy_counter[vacancy_key] += 1
        company_labels[company_key] = company_label
        vacancy_labels[vacancy_key] = vacancy_label
        source_counter[source_label] += 1

        # Для разбивки по компаниям/вакансиям тоже храним по коду.
        company_stage_breakdown[company_key][counter_key] += 1
        vacancy_stage_breakdown[vacancy_key][counter_key] += 1

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
        # Если у кандидата нет менеджера, не подставляем рекрутера – отображаем пустое значение.
        final_manager_label = manager_preferred or None

        snapshot.append(
            {
                "id": str(candidate_id),
                "stage": stage_code,
                "stage_label": stage_label,
                "company": _maybe(company_name),
                "company_id": str(company_id) if company_id else None,
                "vacancy": _maybe(vacancy_title or company_name),
                "vacancy_id": str(vacancy_id) if vacancy_id else None,
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

    def _grouped(
        counter: Counter[str],
        breakdowns: Dict[str, Counter[str]],
        labels: Dict[str, str],
        top_limit: int,
    ):
        items = sorted(counter.items(), key=lambda kv: (-kv[1], kv[0]))[:top_limit]
        result: List[Dict[str, Any]] = []
        for key, total in items:
            stage_counts = breakdowns.get(key, {})
            breakdown = {
                _stage_label(stage_code): int(stage_counts.get(stage_code, 0))
                for stage_code in STAGE_ORDER
                if stage_counts.get(stage_code)
            }
            result.append(
                {
                    "key": key,
                    "label": labels.get(key, key),
                    "count": int(total),
                    "by_stage": breakdown,
                }
            )
        return result

    top_limit = max(5, min(limit, 200))
    list_limit = max(10, min(limit * 2, 200))

    ordered_stage_set = set(STAGE_ORDER)
    stage_rows: List[Dict[str, Any]] = []
    for code in STAGE_ORDER:
        if not _stage_visible_for_view(code, effective_stage_view):
            continue
        count = int(stage_counter.get(code, 0))
        if count:
            stage_rows.append({"key": code, "label": _stage_label(code), "count": count})
    extra_stages = [
        (code, count)
        for code, count in stage_counter.items()
        if code not in ordered_stage_set
    ]
    stage_rows.extend(
        {"key": code, "label": _stage_label(code), "count": int(count)}
        for code, count in sorted(extra_stages, key=lambda kv: (-kv[1], kv[0]))
    )

    result = {
        "period": {
            "from": dfrom.isoformat() if dfrom else None,
            "to": dto.isoformat() if dto else None,
        },
        "by": by,
        "total": len(snapshot),
        "stages": stage_rows,
        "companies_total": len(company_counter),
        "vacancies_total": len(vacancy_counter),
        "companies": _grouped(company_counter, company_stage_breakdown, company_labels, top_limit),
        "vacancies": _grouped(vacancy_counter, vacancy_stage_breakdown, vacancy_labels, top_limit),
        "sources": _top(source_counter, list_limit),
        "citizenships": _top(citizenship_counter, list_limit),
        "countries": _top(country_counter, list_limit),
        "reasons": {
            key: _top(counter, list_limit)
            for key, counter in reason_counters.items()
        },
        "snapshot": snapshot,
    }
    await cache_set("candidate-slices", scope_tenant, cache_params, result, ttl_sec=300)
    return result


class AnalyticsEventIn(BaseModel):
    event: Literal["trial_retention_nudge"]
    action: Literal["impression", "cta_click", "dismiss"]
    day_bucket: Literal["d1", "d2", "d3", "d7"]
    step_key: Optional[str] = None
    target_href: Optional[str] = None
    activation_done: Optional[bool] = None


class TrialRetentionBucketOut(BaseModel):
    day_bucket: str
    impression: int
    cta_click: int
    dismiss: int
    ctr_percent: float
    dismiss_percent: float


class TrialRetentionReportOut(BaseModel):
    period: dict[str, Optional[str]]
    totals: dict[str, float | int]
    buckets: list[TrialRetentionBucketOut]


class ServicesAnalyticsStatusRowOut(BaseModel):
    status: str
    count: int


class ServicesAnalyticsTopItemOut(BaseModel):
    service_id: Optional[str] = None
    label: str
    total: int
    pending: int
    revenue: float
    profit: float


class ServicesAnalyticsTopClientOut(BaseModel):
    owner_kind: str
    owner_id: Optional[str] = None
    label: str
    revenue: float
    profit: float
    orders: int


class ServicesAnalyticsHotOrderOut(BaseModel):
    order_id: str
    label: str
    reason: str
    owner_kind: str
    status: str
    updated_at: Optional[str] = None


class ServicesAnalyticsOverviewOut(BaseModel):
    generated_at: str
    totals: dict[str, float | int]
    last30: dict[str, int]
    data_quality: dict[str, int]
    status_breakdown: list[ServicesAnalyticsStatusRowOut]
    top_items: list[ServicesAnalyticsTopItemOut]
    top_clients: list[ServicesAnalyticsTopClientOut]
    hot_orders: list[ServicesAnalyticsHotOrderOut]
    trends: list[dict[str, float | int | str]]
    slices: list[dict[str, float | int | str | None]]


@router.post("/analytics/events")
async def post_analytics_event(
    payload: AnalyticsEventIn,
    user: UserCtx = Depends(get_current_user),
    db_tenant=Depends(get_db_with_tenant),
):
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    if str(user.tenant_id or "").strip() != tenant_id:
        return {"ok": False, "reason": "tenant_mismatch"}
    await log_activity(
        db,
        tenant_id=tenant_id,
        actor_id=str(user.sub or "").strip() or None,
        action=f"analytics.{payload.event}.{payload.action}",
        target_type="analytics",
        payload={
            "event": payload.event,
            "action": payload.action,
            "day_bucket": payload.day_bucket,
            "step_key": payload.step_key,
            "target_href": payload.target_href,
            "activation_done": payload.activation_done,
        },
    )
    await db.commit()
    return {"ok": True}


@router.get("/analytics/trial-retention", response_model=TrialRetentionReportOut)
async def get_trial_retention_report(
    days: int = Query(30, ge=1, le=180),
    db_tenant=Depends(get_db_with_tenant),
):
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    now = datetime.utcnow()
    since = now - timedelta(days=days)
    actions = [
        "analytics.trial_retention_nudge.impression",
        "analytics.trial_retention_nudge.cta_click",
        "analytics.trial_retention_nudge.dismiss",
    ]
    rows = (
        await db.execute(
            select(ActivityLog.action, ActivityLog.payload, ActivityLog.created_at)
            .where(
                ActivityLog.tenant_id == tenant_id,
                ActivityLog.action.in_(actions),
                ActivityLog.created_at >= since,
            )
            .order_by(ActivityLog.created_at.desc())
        )
    ).all()

    counters: dict[str, Counter[str]] = {
        "d1": Counter(),
        "d2": Counter(),
        "d3": Counter(),
        "d7": Counter(),
    }
    valid_days = set(counters.keys())
    for action, raw_payload, _created_at in rows:
        payload_dict = _safe_dict(raw_payload)
        day_bucket = str(payload_dict.get("day_bucket") or "").strip().lower()
        if day_bucket not in valid_days:
            continue
        event_action = str(payload_dict.get("action") or "").strip().lower()
        if event_action not in {"impression", "cta_click", "dismiss"}:
            action_str = str(action or "").strip().lower()
            if action_str.endswith(".impression"):
                event_action = "impression"
            elif action_str.endswith(".cta_click"):
                event_action = "cta_click"
            elif action_str.endswith(".dismiss"):
                event_action = "dismiss"
        if event_action not in {"impression", "cta_click", "dismiss"}:
            continue
        counters[day_bucket][event_action] += 1

    buckets: list[TrialRetentionBucketOut] = []
    total_impression = 0
    total_cta = 0
    total_dismiss = 0
    for day_bucket in ("d1", "d2", "d3", "d7"):
        row = counters[day_bucket]
        impression = int(row.get("impression", 0))
        cta_click = int(row.get("cta_click", 0))
        dismiss = int(row.get("dismiss", 0))
        total_impression += impression
        total_cta += cta_click
        total_dismiss += dismiss
        ctr_percent = round((cta_click / impression) * 100.0, 2) if impression > 0 else 0.0
        dismiss_percent = round((dismiss / impression) * 100.0, 2) if impression > 0 else 0.0
        buckets.append(
            TrialRetentionBucketOut(
                day_bucket=day_bucket,
                impression=impression,
                cta_click=cta_click,
                dismiss=dismiss,
                ctr_percent=ctr_percent,
                dismiss_percent=dismiss_percent,
            )
        )

    totals_ctr = round((total_cta / total_impression) * 100.0, 2) if total_impression > 0 else 0.0
    return TrialRetentionReportOut(
        period={
            "from": since.isoformat(),
            "to": now.isoformat(),
        },
        totals={
            "impression": total_impression,
            "cta_click": total_cta,
            "dismiss": total_dismiss,
            "ctr_percent": totals_ctr,
        },
        buckets=buckets,
    )
