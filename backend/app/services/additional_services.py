from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from fastapi import HTTPException
try:
    from sqlalchemy import Select
except ImportError:  # pragma: no cover - SQLAlchemy < 1.4
    from sqlalchemy.sql import Select  # type: ignore

from sqlalchemy import and_, case, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.models.additional_service import (
    Service,
    ServiceAttachment,
    ServiceItem,
    ServiceOrder,
    ServiceSchedule,
    ServiceItemStatus,
    ServiceOrderStatus,
)
from backend.app.models.candidate import Candidate
from backend.app.models.company import Company
from backend.app.models.document import Document
from backend.app.models.vacancy import Vacancy
from backend.app.models.enums import DocumentStatus
from backend.app.services import reminders as reminders_service
from backend.app.services.document_catalog import (
    get_doc_type_defaults,
    normalize_doc_type,
    normalize_status,
)
from backend.app.services.document_workflow import (
    WORKFLOW_DEFINITIONS,
    auto_status as compute_auto_status,
    default_workflow,
    normalize_workflow,
)
from backend.app.modules.documents import crud as documents_crud

READY_DOCUMENT_STATUSES = {
    DocumentStatus.received,
    DocumentStatus.approved,
}

# Backward-compatible input mapping (DB stores canonical values after migration).
_LEGACY_SERVICE_ORDER_STATUS: Dict[str, str] = {
    "quoted": ServiceOrderStatus.confirmed.value,
    "approved": ServiceOrderStatus.confirmed.value,
    "scheduled": ServiceOrderStatus.in_progress.value,
    "delivered": ServiceOrderStatus.completed.value,
    "refunded": ServiceOrderStatus.cancelled.value,
}


def normalize_service_order_status(value: object) -> str:
    raw = str(value or "").strip()
    canon = _LEGACY_SERVICE_ORDER_STATUS.get(raw, raw)
    try:
        return ServiceOrderStatus(canon).value
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"Invalid service order status: {raw}") from exc


def _service_order_scope_where(active_oc: Optional[str]):
    """Filter service orders visible under active own-company (§2.4)."""
    if not active_oc:
        return None
    oc = str(active_oc).strip()
    if not oc:
        return None
    return or_(
        ServiceOrder.own_company_id == oc,
        and_(
            ServiceOrder.own_company_id.is_(None),
            ServiceOrder.candidate_id.is_not(None),
            or_(Candidate.own_company_id == oc, Candidate.own_company_id.is_(None)),
        ),
        and_(
            ServiceOrder.own_company_id.is_(None),
            ServiceOrder.vacancy_id.is_not(None),
            or_(Vacancy.own_company_id == oc, Vacancy.own_company_id.is_(None)),
        ),
        and_(
            ServiceOrder.own_company_id.is_(None),
            ServiceOrder.company_id.is_not(None),
        ),
    )


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _coerce_date(value: object) -> Optional[date]:
    if value is None:
        return None
    if isinstance(value, date):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str) and value:
        try:
            return date.fromisoformat(value[:10])
        except ValueError:
            return None
    return None


def _dec(value: Decimal | float | int | str | None, default: Decimal = Decimal("0")) -> Decimal:
    if value is None:
        return default
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except Exception:
        return default


def _quantize(amount: Decimal) -> Decimal:
    return amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _normalize_cost_status(value: object) -> str:
    normalized = str(value or "").strip().lower()
    if normalized in {"missing", "estimated", "confirmed"}:
        return normalized
    return "missing"

class AdditionalServicesService:
    def __init__(self, db: AsyncSession, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id

    async def ensure_order_own_company_scope(
        self,
        order: ServiceOrder,
        active_own_company_id: Optional[str],
    ) -> None:
        if not active_own_company_id:
            return
        oc = str(active_own_company_id).strip()
        if not oc:
            return
        row_oc = str(getattr(order, "own_company_id", None) or "").strip()
        if row_oc:
            if row_oc != oc:
                raise HTTPException(status_code=404, detail="Service order not found")
            return
        if order.candidate_id:
            res = await self.db.execute(
                select(Candidate.own_company_id).where(
                    Candidate.id == order.candidate_id,
                    Candidate.tenant_id == self.tenant_id,
                    Candidate.deleted_at.is_(None),
                )
            )
            c_oc = res.scalar_one_or_none()
            c_oc_s = str(c_oc or "").strip()
            if c_oc_s and c_oc_s != oc:
                raise HTTPException(status_code=404, detail="Service order not found")
            return
        if order.vacancy_id:
            res = await self.db.execute(
                select(Vacancy.own_company_id).where(
                    Vacancy.id == order.vacancy_id,
                    Vacancy.tenant_id == self.tenant_id,
                )
            )
            v_oc = res.scalar_one_or_none()
            v_oc_s = str(v_oc or "").strip()
            if v_oc_s and v_oc_s != oc:
                raise HTTPException(status_code=404, detail="Service order not found")
            return
        if order.company_id:
            return

    async def resolve_new_order_own_company_id(
        self,
        *,
        candidate_id: Optional[str],
        vacancy_id: Optional[str],
        company_id: Optional[str],
        active_own_company_id: Optional[str],
    ) -> Optional[str]:
        active = str(active_own_company_id or "").strip() or None

        if candidate_id:
            row = await self.db.execute(
                select(Candidate).where(
                    Candidate.id == candidate_id,
                    Candidate.tenant_id == self.tenant_id,
                    Candidate.deleted_at.is_(None),
                )
            )
            cand = row.scalar_one_or_none()
            if not cand:
                raise HTTPException(status_code=404, detail="Candidate not found")
            c_set = str(getattr(cand, "own_company_id", None) or "").strip()
            if active and c_set and c_set != active:
                raise HTTPException(status_code=404, detail="Candidate not found")
            return c_set or active

        if vacancy_id:
            row = await self.db.execute(
                select(Vacancy).where(
                    Vacancy.id == vacancy_id,
                    Vacancy.tenant_id == self.tenant_id,
                )
            )
            vac = row.scalar_one_or_none()
            if not vac:
                raise HTTPException(status_code=404, detail="Vacancy not found")
            v_set = str(getattr(vac, "own_company_id", None) or "").strip()
            if active and v_set and v_set != active:
                raise HTTPException(status_code=404, detail="Vacancy not found")
            return v_set or active

        if company_id:
            row = await self.db.execute(
                select(Company).where(
                    Company.id == company_id,
                    Company.tenant_id == self.tenant_id,
                )
            )
            if row.scalar_one_or_none() is None:
                raise HTTPException(status_code=404, detail="Company not found")
            return active

        return active

    async def ensure_item_branch_scope(
        self,
        item_id: str,
        active_own_company_id: Optional[str],
    ) -> None:
        if not active_own_company_id:
            return
        oid = (
            await self.db.execute(
                select(ServiceItem.order_id).where(
                    ServiceItem.id == item_id,
                    ServiceItem.tenant_id == self.tenant_id,
                )
            )
        ).scalar_one_or_none()
        if not oid:
            raise HTTPException(status_code=404, detail="Service item not found")
        order = await self.get_order(str(oid), with_items=False)
        await self.ensure_order_own_company_scope(order, active_own_company_id)

    async def ensure_schedule_branch_scope(
        self,
        schedule_id: str,
        active_own_company_id: Optional[str],
    ) -> None:
        if not active_own_company_id:
            return
        iid = (
            await self.db.execute(
                select(ServiceSchedule.item_id).where(
                    ServiceSchedule.id == schedule_id,
                    ServiceSchedule.tenant_id == self.tenant_id,
                )
            )
        ).scalar_one_or_none()
        if not iid:
            raise HTTPException(status_code=404, detail="Service schedule not found")
        await self.ensure_item_branch_scope(str(iid), active_own_company_id)

    # --- Catalog helpers -------------------------------------------------
    async def list_services(self, *, include_inactive: bool = False) -> List[Service]:
        stmt = (
            select(Service)
            .where(Service.tenant_id == self.tenant_id)
            .order_by(Service.name.asc())
        )
        if not include_inactive:
            stmt = stmt.where(Service.is_active.is_(True))
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def catalog_usage_metrics_map(
        self,
        *,
        own_company_scope: Optional[str] = None,
    ) -> Dict[str, Tuple[int, Decimal]]:
        """Per catalog service_id: (distinct active orders count, revenue on completed orders)."""
        cancelled_o = ServiceOrderStatus.cancelled.value
        cancelled_i = ServiceItemStatus.cancelled.value
        completed_o = ServiceOrderStatus.completed.value

        orders_expr = func.count(
            func.distinct(
                case(
                    (
                        and_(
                            ServiceOrder.status != cancelled_o,
                            ServiceItem.status != cancelled_i,
                        ),
                        ServiceItem.order_id,
                    ),
                )
            )
        )
        revenue_expr = func.coalesce(
            func.sum(
                case(
                    (
                        and_(
                            ServiceOrder.status == completed_o,
                            ServiceItem.status != cancelled_i,
                        ),
                        ServiceItem.amount,
                    ),
                    else_=0,
                )
            ),
            0,
        )

        stmt = (
            select(
                ServiceItem.service_id,
                orders_expr.label("orders_count"),
                revenue_expr.label("revenue_completed"),
            )
            .join(ServiceOrder, ServiceOrder.id == ServiceItem.order_id)
            .outerjoin(Candidate, ServiceOrder.candidate_id == Candidate.id)
            .outerjoin(Vacancy, ServiceOrder.vacancy_id == Vacancy.id)
            .where(
                ServiceItem.tenant_id == self.tenant_id,
                ServiceOrder.tenant_id == self.tenant_id,
            )
        )
        scope = _service_order_scope_where(own_company_scope)
        if scope is not None:
            stmt = stmt.where(scope)
        stmt = stmt.group_by(ServiceItem.service_id)
        res = await self.db.execute(stmt)
        out: Dict[str, Tuple[int, Decimal]] = {}
        for sid, oc, rev in res.all():
            rev_d = rev if isinstance(rev, Decimal) else Decimal(str(rev or 0))
            out[str(sid)] = (int(oc or 0), rev_d.quantize(Decimal("0.01")))
        return out

    async def get_service(self, service_id: str) -> Service:
        stmt = select(Service).where(
            Service.id == service_id,
            Service.tenant_id == self.tenant_id,
        )
        row = await self.db.execute(stmt)
        obj = row.scalar_one_or_none()
        if not obj:
            raise HTTPException(status_code=404, detail="Service not found")
        return obj

    async def get_service_by_code(self, code: str) -> Service:
        stmt = select(Service).where(
            Service.code == code,
            Service.tenant_id == self.tenant_id,
        )
        row = await self.db.execute(stmt)
        obj = row.scalar_one_or_none()
        if not obj:
            raise HTTPException(status_code=404, detail="Service not found")
        return obj

    async def create_service(self, payload: Dict[str, object]) -> Service:
        service = Service(tenant_id=self.tenant_id, **payload)
        self.db.add(service)
        await self.db.flush()
        return service

    async def update_service(self, service: Service, payload: Dict[str, object]) -> Service:
        for key, value in payload.items():
            setattr(service, key, value)
        await self.db.flush()
        return service

    # --- Orders ----------------------------------------------------------
    async def get_order(
        self,
        order_id: str,
        *,
        with_items: bool = True,
    ) -> ServiceOrder:
        stmt: Select[Tuple[ServiceOrder]] = select(ServiceOrder).where(
            ServiceOrder.id == order_id,
            ServiceOrder.tenant_id == self.tenant_id,
        )
        if with_items:
            stmt = stmt.options(
                selectinload(ServiceOrder.items)
                .selectinload(ServiceItem.service),
                selectinload(ServiceOrder.items)
                .selectinload(ServiceItem.schedules),
                selectinload(ServiceOrder.items)
                .selectinload(ServiceItem.attachments),
            )
        row = await self.db.execute(stmt)
        obj = row.scalar_one_or_none()
        if not obj:
            raise HTTPException(status_code=404, detail="Service order not found")
        return obj

    async def get_item(
        self,
        item_id: str,
        *,
        with_relations: bool = True,
    ) -> ServiceItem:
        stmt: Select[Tuple[ServiceItem]] = select(ServiceItem).where(
            ServiceItem.id == item_id,
            ServiceItem.tenant_id == self.tenant_id,
        )
        if with_relations:
            stmt = stmt.options(
                selectinload(ServiceItem.service),
                selectinload(ServiceItem.order).selectinload(ServiceOrder.items),
                selectinload(ServiceItem.schedules),
                selectinload(ServiceItem.attachments),
            )
        row = await self.db.execute(stmt)
        obj = row.scalar_one_or_none()
        if not obj:
            raise HTTPException(status_code=404, detail="Service item not found")
        return obj

    async def get_schedule(self, schedule_id: str) -> ServiceSchedule:
        stmt = select(ServiceSchedule).where(
            ServiceSchedule.id == schedule_id,
            ServiceSchedule.tenant_id == self.tenant_id,
        )
        row = await self.db.execute(stmt)
        obj = row.scalar_one_or_none()
        if not obj:
            raise HTTPException(status_code=404, detail="Service schedule not found")
        return obj

    async def list_orders(
        self,
        *,
        candidate_id: Optional[str] = None,
        vacancy_id: Optional[str] = None,
        company_id: Optional[str] = None,
        status: Optional[Sequence[str]] = None,
        q: Optional[str] = None,
        limit: Optional[int] = None,
        own_company_scope: Optional[str] = None,
    ) -> List[ServiceOrder]:
        stmt = select(ServiceOrder).where(ServiceOrder.tenant_id == self.tenant_id)
        scope = _service_order_scope_where(own_company_scope)
        if scope is not None:
            stmt = (
                stmt.outerjoin(Candidate, ServiceOrder.candidate_id == Candidate.id)
                .outerjoin(Vacancy, ServiceOrder.vacancy_id == Vacancy.id)
                .where(scope)
            )
        stmt = (
            stmt.options(
                selectinload(ServiceOrder.items)
                .selectinload(ServiceItem.service),
                selectinload(ServiceOrder.items)
                .selectinload(ServiceItem.schedules),
                selectinload(ServiceOrder.items)
                .selectinload(ServiceItem.attachments),
            )
            .order_by(ServiceOrder.created_at.desc())
        )
        if candidate_id:
            stmt = stmt.where(ServiceOrder.candidate_id == candidate_id)
        if vacancy_id:
            stmt = stmt.where(ServiceOrder.vacancy_id == vacancy_id)
        if company_id:
            stmt = stmt.where(ServiceOrder.company_id == company_id)
        if status:
            stmt = stmt.where(ServiceOrder.status.in_(status))
        q_norm = (q or "").strip()
        if q_norm:
            like = f"%{q_norm}%"
            stmt = stmt.where(
                or_(
                    ServiceOrder.id.ilike(like),
                    ServiceOrder.notes.ilike(like),
                )
            )
        if limit is not None:
            stmt = stmt.limit(int(limit))

        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def create_order(
        self,
        payload: Dict[str, object],
        items_payload: Sequence[Dict[str, object]],
    ) -> ServiceOrder:
        order = ServiceOrder(tenant_id=self.tenant_id, **payload)
        self.db.add(order)
        await self.db.flush()

        items: List[ServiceItem] = []
        for idx, item_payload in enumerate(items_payload):
            service = await self._resolve_service(item_payload)
            if service.requires_candidate and not order.candidate_id:
                raise HTTPException(
                    status_code=422,
                    detail=f"Service '{service.code}' requires candidate context",
                )
            qty = _dec(item_payload.get("qty"), Decimal("1"))
            unit_price = _dec(
                item_payload.get("unit_price"),
                _dec(service.base_price, Decimal("0")),
            )
            estimated_cost = _dec(
                item_payload.get("estimated_cost"),
                _quantize(qty * _dec(service.estimated_cost, Decimal("0"))),
            )
            actual_cost = item_payload.get("actual_cost")
            actual_cost_dec = _quantize(_dec(actual_cost)) if actual_cost is not None else None
            cost_currency = str(
                item_payload.get("cost_currency")
                or getattr(service, "cost_currency", None)
                or service.currency
                or payload.get("currency")
                or "PLN"
            )
            cost_status = _normalize_cost_status(item_payload.get("cost_status"))
            if actual_cost_dec is not None:
                cost_status = "confirmed"
            elif estimated_cost > 0 and cost_status == "missing":
                cost_status = "estimated"
            vat_rate = _dec(
                item_payload.get("vat_rate"),
                _dec(service.vat_rate, Decimal("0")),
            )

            service_required = (
                list(service.requires_documents or [])
                if service.requires_documents
                else None
            )
            required_docs = item_payload.get("required_documents")
            if required_docs is None:
                required_docs = service_required

            result_doc_type = item_payload.get("result_document_type")
            if result_doc_type is None:
                result_doc_type = service.result_document_type

            meta = item_payload.get("meta") or {}
            item = ServiceItem(
                tenant_id=self.tenant_id,
                order_id=order.id,
                service_id=service.id,
                qty=qty,
                unit_price=unit_price,
                estimated_cost=estimated_cost,
                actual_cost=actual_cost_dec,
                cost_currency=cost_currency,
                cost_source=str(item_payload.get("cost_source") or "service_catalog"),
                cost_status=cost_status,
                vat_rate=vat_rate,
                amount=_quantize(qty * unit_price),
                required_documents=required_docs,
                result_document_type=result_doc_type,
                meta=meta or None,
            )
            self.db.add(item)
            items.append(item)

        await self.db.flush()
        await self._recalculate_order_totals(order.id)
        await self.db.refresh(order)
        return order

    async def add_item(
        self,
        order: ServiceOrder,
        item_payload: Dict[str, object],
    ) -> ServiceItem:
        service = await self._resolve_service(item_payload)
        if service.requires_candidate and not order.candidate_id:
            raise HTTPException(
                status_code=422,
                detail=f"Service '{service.code}' requires candidate context",
            )
        qty = _dec(item_payload.get("qty"), Decimal("1"))
        unit_price = _dec(
            item_payload.get("unit_price"),
            _dec(service.base_price, Decimal("0")),
        )
        estimated_cost = _dec(
            item_payload.get("estimated_cost"),
            _quantize(qty * _dec(service.estimated_cost, Decimal("0"))),
        )
        actual_cost = item_payload.get("actual_cost")
        actual_cost_dec = _quantize(_dec(actual_cost)) if actual_cost is not None else None
        cost_currency = str(
            item_payload.get("cost_currency")
            or getattr(service, "cost_currency", None)
            or service.currency
            or order.currency
            or "PLN"
        )
        cost_status = _normalize_cost_status(item_payload.get("cost_status"))
        if actual_cost_dec is not None:
            cost_status = "confirmed"
        elif estimated_cost > 0 and cost_status == "missing":
            cost_status = "estimated"
        vat_rate = _dec(
            item_payload.get("vat_rate"),
            _dec(service.vat_rate, Decimal("0")),
        )
        required_docs = item_payload.get("required_documents")
        if required_docs is None and service.requires_documents:
            required_docs = list(service.requires_documents)
        result_doc_type = item_payload.get("result_document_type")
        if result_doc_type is None:
            result_doc_type = service.result_document_type

        item = ServiceItem(
            tenant_id=self.tenant_id,
            order_id=order.id,
            service_id=service.id,
            qty=qty,
            unit_price=unit_price,
            estimated_cost=estimated_cost,
            actual_cost=actual_cost_dec,
            cost_currency=cost_currency,
            cost_source=str(item_payload.get("cost_source") or "service_catalog"),
            cost_status=cost_status,
            vat_rate=vat_rate,
            amount=_quantize(qty * unit_price),
            required_documents=required_docs,
            result_document_type=result_doc_type,
            meta=item_payload.get("meta") or None,
        )
        self.db.add(item)
        await self.db.flush()
        await self._recalculate_order_totals(order.id)
        await self.db.refresh(order)
        return item

    async def update_order(
        self,
        order: ServiceOrder,
        payload: Dict[str, object],
    ) -> ServiceOrder:
        for key, value in payload.items():
            setattr(order, key, value)
        await self.db.flush()
        await self._recalculate_order_totals(order.id)
        await self.db.refresh(order)
        return order

    async def set_order_status(
        self,
        order: ServiceOrder,
        status: str,
    ) -> ServiceOrder:
        status_enum = ServiceOrderStatus(normalize_service_order_status(status))
        current = normalize_service_order_status(order.status)
        if current == ServiceOrderStatus.draft.value and status_enum == ServiceOrderStatus.confirmed:
            await self._freeze_prices(order)

        if status_enum in (
            ServiceOrderStatus.in_progress,
            ServiceOrderStatus.completed,
        ):
            await self._ensure_required_documents(order)

        order.status = status_enum.value
        await self.db.flush()
        await self._recalculate_order_totals(order.id)
        await self.db.refresh(order)
        return order

    async def mark_item_status(
        self,
        item: ServiceItem,
        status: str,
    ) -> ServiceItem:
        item.status = ServiceItemStatus(status).value
        await self.db.flush()
        await self._recalculate_order_totals(item.order_id)
        await self.db.refresh(item)
        order = getattr(item, "order", None)
        if order is None:
            try:
                order = await self.get_order(item.order_id, with_items=False)
            except Exception:
                order = None
        if order is not None:
            try:
                await self.db.refresh(order)
            except Exception:
                pass
        return item

    async def add_schedule(
        self,
        item: ServiceItem,
        payload: Dict[str, object],
    ) -> ServiceSchedule:
        schedule = ServiceSchedule(
            tenant_id=self.tenant_id,
            item_id=item.id,
            **payload,
        )
        self.db.add(schedule)
        if item.status == ServiceItemStatus.pending.value:
            item.status = ServiceItemStatus.scheduled.value
        await self.db.flush()
        await self.db.refresh(schedule)
        await self.db.refresh(item)
        await self._recalculate_order_totals(item.order_id)
        return schedule

    async def update_schedule(
        self,
        schedule: ServiceSchedule,
        payload: Dict[str, object],
    ) -> ServiceSchedule:
        for key, value in payload.items():
            setattr(schedule, key, value)
        await self.db.flush()
        await self.db.refresh(schedule)
        item = getattr(schedule, "item", None)
        if item is None:
            try:
                await self.db.refresh(schedule, attribute_names=["item"])
                item = getattr(schedule, "item", None)
            except Exception:
                item = None
        if item is not None:
            await self._recalculate_order_totals(item.order_id)
        return schedule

    async def add_attachment(
        self,
        item: ServiceItem,
        payload: Dict[str, object],
    ) -> ServiceAttachment:
        attachment = ServiceAttachment(
            tenant_id=self.tenant_id,
            item_id=item.id,
            **payload,
        )
        self.db.add(attachment)
        await self.db.flush()
        await self.db.refresh(attachment)
        return attachment

    async def deliver_item(
        self,
        item: ServiceItem,
        *,
        status: Optional[str] = None,
        result_document: Optional[Dict[str, object]] = None,
        attachments: Optional[Sequence[Dict[str, object]]] = None,
        meta: Optional[Dict[str, object]] = None,
    ) -> ServiceItem:
        order = getattr(item, "order", None)
        if order is None:
            try:
                await self.db.refresh(item, attribute_names=["order"])
                order = getattr(item, "order", None)
            except Exception:
                order = None
        if order is None:
            order = await self.get_order(item.order_id)

        await self._ensure_required_documents(order)

        if status:
            item.status = ServiceItemStatus(status).value
        else:
            item.status = ServiceItemStatus.delivered.value

        if meta is not None:
            item.meta = {**(item.meta or {}), **meta} if meta else item.meta

        if attachments:
            for attachment_payload in attachments:
                attachment = ServiceAttachment(
                    tenant_id=self.tenant_id,
                    item_id=item.id,
                    **attachment_payload,
                )
                self.db.add(attachment)

        if result_document and order.candidate_id and item.result_document_type:
            await self._create_or_update_document(
                candidate_id=order.candidate_id,
                doc_type=item.result_document_type,
                payload=result_document,
                own_company_id=str(getattr(order, "own_company_id", None) or "").strip() or None,
            )

        await self.db.flush()
        await self._recalculate_order_totals(item.order_id)
        await self.db.refresh(item)
        return item

    async def summary_for_order(self, order: ServiceOrder) -> Dict[str, object]:
        try:
            await self.db.refresh(order, attribute_names=["items"])
        except Exception:
            pass

        blocking = []
        for item in order.items:
            meta = item.meta or {}
            blocking_flag = bool(meta.get("blocking") or (item.service and (item.service.meta or {}).get("blocking")))
            if blocking_flag and item.status != ServiceItemStatus.delivered.value:
                blocking.append(item)

        missing_by_item: Dict[str, List[str]] = {}
        if order.candidate_id:
            for item in order.items:
                if not item.required_documents:
                    continue
                missing = await self._missing_documents(order.candidate_id, item.required_documents)
                if missing:
                    missing_by_item[item.id] = missing

        return {
            "order": order,
            "blocking_items": blocking,
            "missing_documents": missing_by_item,
        }

    # --- Internals -------------------------------------------------------
    async def _freeze_prices(self, order: ServiceOrder) -> None:
        statement = (
            update(ServiceItem)
            .where(
                ServiceItem.order_id == order.id,
                ServiceItem.tenant_id == self.tenant_id,
            )
            .values(
                unit_price=ServiceItem.unit_price,
                vat_rate=ServiceItem.vat_rate,
                amount=ServiceItem.amount,
            )
        )
        await self.db.execute(statement)

    async def _recalculate_order_totals(self, order_id: str) -> None:
        stmt = (
            select(
                func.coalesce(func.sum(ServiceItem.amount), 0),
                func.coalesce(
                    func.sum(ServiceItem.amount * (ServiceItem.vat_rate / 100)),
                    0,
                ),
            )
            .where(
                ServiceItem.order_id == order_id,
                ServiceItem.tenant_id == self.tenant_id,
            )
        )
        total_amount, vat_total = (await self.db.execute(stmt)).one()
        await self.db.execute(
            update(ServiceOrder)
            .where(
                ServiceOrder.id == order_id,
                ServiceOrder.tenant_id == self.tenant_id,
            )
            .values(
                total_amount=_quantize(_dec(total_amount)),
                vat_total=_quantize(_dec(vat_total)),
            )
        )

    async def _resolve_service(self, payload: Dict[str, object]) -> Service:
        if payload.get("service_id"):
            return await self.get_service(payload["service_id"])
        if payload.get("service_code"):
            return await self.get_service_by_code(payload["service_code"])
        raise HTTPException(status_code=422, detail="Service identifier is required")

    async def _ensure_required_documents(self, order: ServiceOrder) -> None:
        if not order.candidate_id:
            return
        try:
            await self.db.refresh(order, attribute_names=["items"])
        except Exception:
            pass
        missing_all: List[str] = []
        for item in order.items:
            if not item.required_documents:
                continue
            missing = await self._missing_documents(
                order.candidate_id,
                item.required_documents,
            )
            missing_all.extend(missing)
        if missing_all:
            raise HTTPException(
                status_code=409,
                detail={
                    "reason": "documents_missing",
                    "missing": missing_all,
                },
            )

    async def _missing_documents(
        self,
        candidate_id: str,
        required: Iterable[str],
    ) -> List[str]:
        doc_codes = [normalize_doc_type(code) for code in required if code]
        if not doc_codes:
            return []
        stmt = select(Document.doc_type, Document.status).where(
            Document.tenant_id == self.tenant_id,
            Document.candidate_id == candidate_id,
            Document.doc_type.in_(doc_codes),
            Document.deleted_at.is_(None),
        )
        rows = await self.db.execute(stmt)
        status_by_code: Dict[str, DocumentStatus] = {}
        for doc_type_value, status_value in rows.all():
            if isinstance(status_value, DocumentStatus):
                status_by_code[doc_type_value] = status_value
            else:
                try:
                    status_by_code[doc_type_value] = normalize_status(status_value)
                except ValueError:
                    status_by_code[doc_type_value] = DocumentStatus.missing

        missing: List[str] = []
        for code in doc_codes:
            status = status_by_code.get(code)
            if status is None or status not in READY_DOCUMENT_STATUSES:
                missing.append(code)
        return missing

    async def _create_or_update_document(
        self,
        *,
        candidate_id: str,
        doc_type: str,
        payload: Dict[str, object],
        own_company_id: Optional[str] = None,
    ) -> None:
        canonical_type = normalize_doc_type(doc_type)
        defaults = get_doc_type_defaults(canonical_type)

        stmt = select(Document).where(
            Document.tenant_id == self.tenant_id,
            Document.candidate_id == candidate_id,
            Document.doc_type == canonical_type,
            Document.deleted_at.is_(None),
        ).limit(1)
        row = await self.db.execute(stmt)
        doc = row.scalar_one_or_none()

        issue_date = _coerce_date(payload.get("issued_at"))
        expire_date = _coerce_date(payload.get("expires_at"))

        meta_payload: Dict[str, object] = dict(payload.get("extra") or {})
        meta_payload.setdefault("doc_type", canonical_type)
        original_type = payload.get("document_type") or payload.get("doc_type")
        if isinstance(original_type, str) and original_type and original_type != canonical_type:
            meta_payload.setdefault("submitted_doc_type", original_type)
        if payload.get("number"):
            meta_payload.setdefault("number", payload["number"])
        if payload.get("file_id"):
            meta_payload["file_id"] = payload["file_id"]
            if payload.get("label"):
                meta_payload["file_label"] = payload["label"]
        if payload.get("source"):
            meta_payload.setdefault("source", payload["source"])

        reminder_raw = payload.get("reminder_days_before")
        try:
            reminder_days = int(reminder_raw) if reminder_raw is not None else 30
        except (TypeError, ValueError):
            reminder_days = 30

        raw_status = payload.get("status") or DocumentStatus.approved.value
        try:
            status_enum = normalize_status(raw_status)
        except ValueError:
            status_enum = DocumentStatus.approved

        existing_workflow = getattr(doc, "workflow", None) if doc else None
        workflow_payload = payload.get("workflow")
        normalized_workflow = normalize_workflow(
            defaults.process_type,
            workflow_payload,
            existing_workflow=existing_workflow,
        )
        if normalized_workflow is None and defaults.process_type in WORKFLOW_DEFINITIONS:
            normalized_workflow = default_workflow(defaults.process_type)

        has_files = bool(
            payload.get("file_id")
            or payload.get("files")
            or (doc and getattr(doc, "files", None))
        )
        workflow_for_status = normalized_workflow or existing_workflow
        auto_status_value = compute_auto_status(
            status_enum,
            process_type=defaults.process_type,
            workflow=workflow_for_status,
            has_files=has_files,
            expire_date=expire_date,
        )
        if status_enum in (DocumentStatus.rejected, DocumentStatus.expired):
            auto_status_value = status_enum

        if doc:
            doc.status = auto_status_value
            doc.issue_date = issue_date
            doc.expire_date = expire_date
            if payload.get("number"):
                doc.number = payload["number"]
            doc.workflow = normalized_workflow or existing_workflow
            doc.meta = {**(doc.meta or {}), **meta_payload} if meta_payload else (doc.meta or None)
            doc.kind = doc.kind or defaults.kind
            doc.requested_from = doc.requested_from or defaults.requested_from
            doc.process_type = doc.process_type or defaults.process_type
            doc.reminder_days_before = reminder_days
            if auto_status_value == DocumentStatus.approved and getattr(doc, "verified_at", None) is None:
                doc.verified_at = _now_utc()
            doc.updated_at = _now_utc()
        else:
            await documents_crud.ensure_document_type(self.db, self.tenant_id, canonical_type)
            doc_own = str(own_company_id or "").strip() or None
            doc = Document(
                id=str(uuid.uuid4()),
                tenant_id=self.tenant_id,
                candidate_id=candidate_id,
                own_company_id=doc_own,
                owner_type="candidate",
                owner_id=candidate_id,
                kind=defaults.kind,
                requested_from=defaults.requested_from,
                process_type=defaults.process_type,
                doc_type=canonical_type,
                status=auto_status_value,
                issue_date=issue_date,
                expire_date=expire_date,
                number=payload.get("number"),
                workflow=normalized_workflow,
                meta=meta_payload or None,
                reminder_days_before=reminder_days,
            )
            if auto_status_value == DocumentStatus.approved:
                doc.verified_at = _now_utc()
            self.db.add(doc)
            doc.updated_at = _now_utc()

        await self.db.flush()
        await reminders_service.schedule_document_expiry_reminders(
            self.db,
            self.tenant_id,
            doc,
        )
