"""Sales Service Orders / Lines / Billable Items (ADR-032)."""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.v1.utils.own_company import resolve_own_company_id_for_session
from backend.app.auth.deps import Role, UserCtx, get_current_user, require_roles
from backend.app.db.deps import get_db_with_tenant
from backend.app.models.client_account import ClientAccount
from backend.app.models.company import Company
from backend.app.models.sales_order import BILLING_TRIGGERS, SalesBillableItem, SalesOrder, SalesOrderLine
from backend.app.models.vacancy import Vacancy

router = APIRouter(tags=["sales-orders"], redirect_slashes=False)

_READ = Depends(require_roles(Role.admin, Role.manager, Role.supervisor, Role.recruiter))
_WRITE = Depends(require_roles(Role.admin, Role.manager, Role.supervisor))


class SalesOrderCreate(BaseModel):
    company_id: str
    title: str = Field(..., min_length=1, max_length=255)
    client_account_id: Optional[str] = None
    payer_company_id: Optional[str] = None
    currency: Optional[str] = None
    payment_term_days: Optional[int] = Field(None, ge=0, le=365)
    payment_model: Optional[str] = None
    vat_rate: Optional[Decimal] = None
    guarantee_days: Optional[int] = Field(None, ge=0, le=3650)
    invoice_right_policy: Optional[str] = None
    billing_notes: Optional[str] = None
    commercial_snapshot: Optional[dict[str, Any]] = None
    own_company_id: Optional[str] = None
    status: str = "open"


class SalesOrderUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    status: Optional[str] = None
    currency: Optional[str] = None
    payment_term_days: Optional[int] = Field(None, ge=0, le=365)
    payment_model: Optional[str] = None
    vat_rate: Optional[Decimal] = None
    guarantee_days: Optional[int] = Field(None, ge=0, le=3650)
    invoice_right_policy: Optional[str] = None
    billing_notes: Optional[str] = None
    commercial_snapshot: Optional[dict[str, Any]] = None
    payer_company_id: Optional[str] = None
    client_account_id: Optional[str] = None


class SalesOrderLineCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    quantity_needed: int = Field(..., ge=1, le=9999)
    role_label: Optional[str] = None
    location: Optional[str] = None
    unit_rate: Optional[Decimal] = None
    charge_unit: Optional[str] = None
    billing_trigger: str = "headcount_completed"
    guarantee_days: Optional[int] = Field(None, ge=0, le=3650)
    status: str = "open"
    sort_order: int = 0


class SalesOrderLineUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    quantity_needed: Optional[int] = Field(None, ge=1, le=9999)
    role_label: Optional[str] = None
    location: Optional[str] = None
    unit_rate: Optional[Decimal] = None
    charge_unit: Optional[str] = None
    billing_trigger: Optional[str] = None
    guarantee_days: Optional[int] = Field(None, ge=0, le=3650)
    status: Optional[str] = None
    sort_order: Optional[int] = None


class SalesOrderLineOut(BaseModel):
    id: str
    tenant_id: str
    sales_order_id: str
    title: str
    role_label: Optional[str] = None
    location: Optional[str] = None
    quantity_needed: int
    unit_rate: Optional[Decimal] = None
    charge_unit: Optional[str] = None
    billing_trigger: str
    guarantee_days: Optional[int] = None
    status: str
    sort_order: int
    vacancy_id: Optional[str] = None
    company_id: Optional[str] = None


class SalesOrderOut(BaseModel):
    id: str
    tenant_id: str
    own_company_id: Optional[str] = None
    client_account_id: Optional[str] = None
    company_id: str
    payer_company_id: Optional[str] = None
    title: str
    status: str
    currency: Optional[str] = None
    payment_term_days: Optional[int] = None
    payment_model: Optional[str] = None
    vat_rate: Optional[Decimal] = None
    guarantee_days: Optional[int] = None
    invoice_right_policy: Optional[str] = None
    billing_notes: Optional[str] = None
    commercial_snapshot: Optional[dict[str, Any]] = None
    lines: list[SalesOrderLineOut] = Field(default_factory=list)


class SalesOrderListResponse(BaseModel):
    items: list[SalesOrderOut]
    total: int


class SalesOrderLineListResponse(BaseModel):
    items: list[SalesOrderLineOut]
    total: int


class BillableItemCreate(BaseModel):
    sales_order_id: str
    sales_order_line_id: Optional[str] = None
    trigger_code: str
    amount: Decimal
    currency: str
    quantity: Decimal = Decimal("1")
    source_entity_type: Optional[str] = None
    source_entity_id: Optional[str] = None
    notes: Optional[str] = None


class BillableItemOut(BaseModel):
    id: str
    tenant_id: str
    sales_order_id: str
    sales_order_line_id: Optional[str] = None
    trigger_code: str
    amount: Decimal
    currency: str
    quantity: Decimal
    source_entity_type: Optional[str] = None
    source_entity_id: Optional[str] = None
    status: str
    invoice_id: Optional[str] = None
    notes: Optional[str] = None


class ComposeInvoiceRequest(BaseModel):
    billable_item_ids: list[str] = Field(..., min_length=1)


class ComposeInvoiceResponse(BaseModel):
    invoice_id: str
    invoice_number: Optional[str] = None
    status: str
    currency: Optional[str] = None
    total_amount: Optional[Decimal] = None
    billable_item_ids: list[str] = Field(default_factory=list)


def _status_ok(st: str) -> bool:
    return st in {"open", "in_progress", "completed", "cancelled"}


def _trigger_ok(tr: str) -> bool:
    return tr in BILLING_TRIGGERS


async def _vacancy_id_for_line(db: AsyncSession, *, tenant_id: str, line_id: str) -> Optional[str]:
    return (
        await db.execute(
            select(Vacancy.id).where(
                Vacancy.tenant_id == tenant_id,
                Vacancy.order_line_id == line_id,
            )
        )
    ).scalar_one_or_none()


def _line_out(
    line: SalesOrderLine,
    *,
    vacancy_id: Optional[str] = None,
    company_id: Optional[str] = None,
) -> SalesOrderLineOut:
    return SalesOrderLineOut(
        id=line.id,
        tenant_id=line.tenant_id,
        sales_order_id=line.sales_order_id,
        title=line.title,
        role_label=line.role_label,
        location=line.location,
        quantity_needed=int(line.quantity_needed),
        unit_rate=line.unit_rate,
        charge_unit=line.charge_unit,
        billing_trigger=line.billing_trigger,
        guarantee_days=line.guarantee_days,
        status=line.status,
        sort_order=int(line.sort_order or 0),
        vacancy_id=vacancy_id,
        company_id=company_id,
    )


def _order_out(order: SalesOrder, lines: list[SalesOrderLineOut]) -> SalesOrderOut:
    return SalesOrderOut(
        id=order.id,
        tenant_id=order.tenant_id,
        own_company_id=order.own_company_id,
        client_account_id=order.client_account_id,
        company_id=order.company_id,
        payer_company_id=order.payer_company_id,
        title=order.title,
        status=order.status,
        currency=order.currency,
        payment_term_days=order.payment_term_days,
        payment_model=order.payment_model,
        vat_rate=order.vat_rate,
        guarantee_days=order.guarantee_days,
        invoice_right_policy=order.invoice_right_policy,
        billing_notes=order.billing_notes,
        commercial_snapshot=order.commercial_snapshot if isinstance(order.commercial_snapshot, dict) else None,
        lines=lines,
    )


async def _load_lines_out(
    db: AsyncSession, *, tenant_id: str, order: SalesOrder
) -> list[SalesOrderLineOut]:
    rows = (
        await db.execute(
            select(SalesOrderLine)
            .where(
                SalesOrderLine.tenant_id == tenant_id,
                SalesOrderLine.sales_order_id == order.id,
            )
            .order_by(SalesOrderLine.sort_order.asc(), SalesOrderLine.created_at.asc())
        )
    ).scalars().all()
    out: list[SalesOrderLineOut] = []
    for line in rows:
        vid = await _vacancy_id_for_line(db, tenant_id=tenant_id, line_id=line.id)
        out.append(_line_out(line, vacancy_id=vid, company_id=order.company_id))
    return out


async def _assert_no_billable_blocks_commercial_edit(
    db: AsyncSession, *, tenant_id: str, order_id: str
) -> None:
    exists = (
        await db.execute(
            select(SalesBillableItem.id)
            .where(
                SalesBillableItem.tenant_id == tenant_id,
                SalesBillableItem.sales_order_id == order_id,
                SalesBillableItem.status != "void",
            )
            .limit(1)
        )
    ).scalar_one_or_none()
    if exists:
        raise HTTPException(
            status_code=409,
            detail="Commercial snapshot locked: billable items exist (amendment required)",
        )


@router.get("/sales-orders", response_model=SalesOrderListResponse, dependencies=[_READ])
@router.get("/sales-orders/", response_model=SalesOrderListResponse, include_in_schema=False, dependencies=[_READ])
async def list_sales_orders(
    company_id: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    limit: int = Query(100, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db_tenant=Depends(get_db_with_tenant),
) -> SalesOrderListResponse:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    filters = [SalesOrder.tenant_id == tenant_id]
    if company_id:
        filters.append(SalesOrder.company_id == str(company_id).strip())
    if status_filter:
        filters.append(SalesOrder.status == str(status_filter).strip().lower())
    rows = (
        await db.execute(
            select(SalesOrder)
            .where(*filters)
            .order_by(SalesOrder.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
    ).scalars().all()
    items = []
    for order in rows:
        items.append(_order_out(order, await _load_lines_out(db, tenant_id=tenant_id, order=order)))
    return SalesOrderListResponse(items=items, total=len(items))


@router.post("/sales-orders", response_model=SalesOrderOut, status_code=201, dependencies=[_WRITE])
@router.post("/sales-orders/", response_model=SalesOrderOut, status_code=201, include_in_schema=False, dependencies=[_WRITE])
async def create_sales_order(
    payload: SalesOrderCreate,
    db_tenant=Depends(get_db_with_tenant),
    ctx: UserCtx = Depends(get_current_user),
) -> SalesOrderOut:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    st = str(payload.status or "open").strip().lower()
    if not _status_ok(st):
        raise HTTPException(status_code=422, detail="Invalid status")
    company = await db.get(Company, str(payload.company_id).strip())
    if company is None or str(company.tenant_id) != tenant_id:
        raise HTTPException(status_code=404, detail="Company not found")
    if payload.client_account_id:
        ca = await db.get(ClientAccount, str(payload.client_account_id).strip())
        if ca is None or str(ca.tenant_id) != tenant_id:
            raise HTTPException(status_code=404, detail="Client account not found")
    own_company_id = await resolve_own_company_id_for_session(
        db, tenant_id, ctx, payload.own_company_id
    )
    # Snapshot: freeze submitted commercial fields on create.
    snapshot = dict(payload.commercial_snapshot or {})
    snapshot.setdefault("currency", payload.currency)
    snapshot.setdefault("payment_term_days", payload.payment_term_days)
    snapshot.setdefault("payment_model", payload.payment_model)
    snapshot.setdefault("vat_rate", str(payload.vat_rate) if payload.vat_rate is not None else None)
    snapshot.setdefault("guarantee_days", payload.guarantee_days)
    snapshot.setdefault("invoice_right_policy", payload.invoice_right_policy)
    order = SalesOrder(
        id=str(uuid4()),
        tenant_id=tenant_id,
        own_company_id=own_company_id,
        client_account_id=(str(payload.client_account_id).strip() or None) if payload.client_account_id else None,
        company_id=str(company.id),
        payer_company_id=(str(payload.payer_company_id).strip() or None) if payload.payer_company_id else None,
        title=str(payload.title).strip(),
        status=st,
        currency=(str(payload.currency).strip().upper() or None) if payload.currency else None,
        payment_term_days=payload.payment_term_days,
        payment_model=(str(payload.payment_model).strip() or None) if payload.payment_model else None,
        vat_rate=payload.vat_rate,
        guarantee_days=payload.guarantee_days,
        invoice_right_policy=(str(payload.invoice_right_policy).strip() or None)
        if payload.invoice_right_policy
        else None,
        billing_notes=(str(payload.billing_notes).strip() or None) if payload.billing_notes else None,
        commercial_snapshot=snapshot,
    )
    db.add(order)
    await db.commit()
    await db.refresh(order)
    return _order_out(order, [])


@router.get("/sales-orders/{order_id}", response_model=SalesOrderOut, dependencies=[_READ])
async def get_sales_order(order_id: str, db_tenant=Depends(get_db_with_tenant)) -> SalesOrderOut:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    order = await db.get(SalesOrder, str(order_id).strip())
    if order is None or str(order.tenant_id) != tenant_id:
        raise HTTPException(status_code=404, detail="Sales order not found")
    return _order_out(order, await _load_lines_out(db, tenant_id=tenant_id, order=order))


@router.patch("/sales-orders/{order_id}", response_model=SalesOrderOut, dependencies=[_WRITE])
async def patch_sales_order(
    order_id: str,
    payload: SalesOrderUpdate,
    db_tenant=Depends(get_db_with_tenant),
) -> SalesOrderOut:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    order = await db.get(SalesOrder, str(order_id).strip())
    if order is None or str(order.tenant_id) != tenant_id:
        raise HTTPException(status_code=404, detail="Sales order not found")
    data = payload.model_dump(exclude_unset=True)
    commercial_keys = {
        "currency",
        "payment_term_days",
        "payment_model",
        "vat_rate",
        "guarantee_days",
        "invoice_right_policy",
        "commercial_snapshot",
        "payer_company_id",
    }
    if commercial_keys & set(data.keys()):
        await _assert_no_billable_blocks_commercial_edit(db, tenant_id=tenant_id, order_id=order.id)
    if "status" in data and data["status"] is not None:
        st = str(data["status"]).strip().lower()
        if not _status_ok(st):
            raise HTTPException(status_code=422, detail="Invalid status")
        order.status = st
    if "title" in data and data["title"] is not None:
        order.title = str(data["title"]).strip()
    for field in (
        "currency",
        "payment_term_days",
        "payment_model",
        "vat_rate",
        "guarantee_days",
        "invoice_right_policy",
        "billing_notes",
        "commercial_snapshot",
        "payer_company_id",
        "client_account_id",
    ):
        if field in data:
            val = data[field]
            if field == "currency" and val is not None:
                val = str(val).strip().upper() or None
            setattr(order, field, val)
    await db.commit()
    await db.refresh(order)
    return _order_out(order, await _load_lines_out(db, tenant_id=tenant_id, order=order))


@router.post(
    "/sales-orders/{order_id}/lines",
    response_model=SalesOrderLineOut,
    status_code=201,
    dependencies=[_WRITE],
)
async def create_order_line(
    order_id: str,
    payload: SalesOrderLineCreate,
    db_tenant=Depends(get_db_with_tenant),
) -> SalesOrderLineOut:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    order = await db.get(SalesOrder, str(order_id).strip())
    if order is None or str(order.tenant_id) != tenant_id:
        raise HTTPException(status_code=404, detail="Sales order not found")
    tr = str(payload.billing_trigger or "headcount_completed").strip().lower()
    if not _trigger_ok(tr):
        raise HTTPException(status_code=422, detail="Invalid billing_trigger")
    st = str(payload.status or "open").strip().lower()
    if not _status_ok(st):
        raise HTTPException(status_code=422, detail="Invalid status")
    line = SalesOrderLine(
        id=str(uuid4()),
        tenant_id=tenant_id,
        sales_order_id=order.id,
        title=str(payload.title).strip(),
        role_label=(str(payload.role_label).strip() or None) if payload.role_label else None,
        location=(str(payload.location).strip() or None) if payload.location else None,
        quantity_needed=int(payload.quantity_needed),
        unit_rate=payload.unit_rate,
        charge_unit=(str(payload.charge_unit).strip() or None) if payload.charge_unit else None,
        billing_trigger=tr,
        guarantee_days=payload.guarantee_days,
        status=st,
        sort_order=int(payload.sort_order or 0),
    )
    db.add(line)
    await db.commit()
    await db.refresh(line)
    return _line_out(line, company_id=order.company_id)


@router.get("/sales-order-lines", response_model=SalesOrderLineListResponse, dependencies=[_READ])
@router.get("/sales-order-lines/", response_model=SalesOrderLineListResponse, include_in_schema=False, dependencies=[_READ])
async def list_order_lines(
    company_id: Optional[str] = Query(None),
    sales_order_id: Optional[str] = Query(None),
    unlinked: bool = Query(False),
    status_filter: Optional[str] = Query(None, alias="status"),
    limit: int = Query(100, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db_tenant=Depends(get_db_with_tenant),
) -> SalesOrderLineListResponse:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    stmt = (
        select(SalesOrderLine, SalesOrder)
        .join(SalesOrder, SalesOrder.id == SalesOrderLine.sales_order_id)
        .where(SalesOrderLine.tenant_id == tenant_id)
        .order_by(SalesOrderLine.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    if company_id:
        stmt = stmt.where(SalesOrder.company_id == str(company_id).strip())
    if sales_order_id:
        stmt = stmt.where(SalesOrderLine.sales_order_id == str(sales_order_id).strip())
    if status_filter:
        stmt = stmt.where(SalesOrderLine.status == str(status_filter).strip().lower())
    pairs = (await db.execute(stmt)).all()
    items: list[SalesOrderLineOut] = []
    for line, order in pairs:
        vid = await _vacancy_id_for_line(db, tenant_id=tenant_id, line_id=line.id)
        if unlinked and vid:
            continue
        items.append(_line_out(line, vacancy_id=vid, company_id=order.company_id))
    return SalesOrderLineListResponse(items=items, total=len(items))


@router.patch("/sales-order-lines/{line_id}", response_model=SalesOrderLineOut, dependencies=[_WRITE])
async def patch_order_line(
    line_id: str,
    payload: SalesOrderLineUpdate,
    db_tenant=Depends(get_db_with_tenant),
) -> SalesOrderLineOut:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    line = await db.get(SalesOrderLine, str(line_id).strip())
    if line is None or str(line.tenant_id) != tenant_id:
        raise HTTPException(status_code=404, detail="Order line not found")
    order = await db.get(SalesOrder, line.sales_order_id)
    data = payload.model_dump(exclude_unset=True)
    if "billing_trigger" in data and data["billing_trigger"] is not None:
        tr = str(data["billing_trigger"]).strip().lower()
        if not _trigger_ok(tr):
            raise HTTPException(status_code=422, detail="Invalid billing_trigger")
        await _assert_no_billable_blocks_commercial_edit(
            db, tenant_id=tenant_id, order_id=line.sales_order_id
        )
        line.billing_trigger = tr
    if "unit_rate" in data:
        await _assert_no_billable_blocks_commercial_edit(
            db, tenant_id=tenant_id, order_id=line.sales_order_id
        )
        line.unit_rate = data["unit_rate"]
    if "status" in data and data["status"] is not None:
        st = str(data["status"]).strip().lower()
        if not _status_ok(st):
            raise HTTPException(status_code=422, detail="Invalid status")
        line.status = st
    if "title" in data and data["title"] is not None:
        line.title = str(data["title"]).strip()
    if "quantity_needed" in data and data["quantity_needed"] is not None:
        line.quantity_needed = int(data["quantity_needed"])
        vac = (
            await db.execute(
                select(Vacancy).where(
                    Vacancy.tenant_id == tenant_id,
                    Vacancy.order_line_id == line.id,
                )
            )
        ).scalar_one_or_none()
        if vac is not None:
            vac.headcount_target = int(line.quantity_needed)
    for field in ("role_label", "location", "charge_unit", "guarantee_days", "sort_order"):
        if field in data:
            setattr(line, field, data[field])
    await db.commit()
    await db.refresh(line)
    vid = await _vacancy_id_for_line(db, tenant_id=tenant_id, line_id=line.id)
    return _line_out(line, vacancy_id=vid, company_id=order.company_id if order else None)


@router.get("/sales-billable-items", response_model=list[BillableItemOut], dependencies=[_READ])
async def list_billable_items(
    sales_order_id: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    limit: int = Query(100, ge=1, le=200),
    db_tenant=Depends(get_db_with_tenant),
) -> list[BillableItemOut]:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    stmt = (
        select(SalesBillableItem)
        .where(SalesBillableItem.tenant_id == tenant_id)
        .order_by(SalesBillableItem.created_at.desc())
        .limit(limit)
    )
    if sales_order_id:
        stmt = stmt.where(SalesBillableItem.sales_order_id == str(sales_order_id).strip())
    if status_filter:
        st = str(status_filter).strip().lower()
        if st not in {"pending", "invoiced", "void"}:
            raise HTTPException(status_code=422, detail="Invalid status")
        stmt = stmt.where(SalesBillableItem.status == st)
    rows = (await db.execute(stmt)).scalars().all()
    return [
        BillableItemOut(
            id=r.id,
            tenant_id=r.tenant_id,
            sales_order_id=r.sales_order_id,
            sales_order_line_id=r.sales_order_line_id,
            trigger_code=r.trigger_code,
            amount=r.amount,
            currency=r.currency,
            quantity=r.quantity,
            source_entity_type=r.source_entity_type,
            source_entity_id=r.source_entity_id,
            status=r.status,
            invoice_id=r.invoice_id,
            notes=r.notes,
        )
        for r in rows
    ]


@router.post(
    "/sales-orders/{order_id}/invoices",
    response_model=ComposeInvoiceResponse,
    status_code=201,
    dependencies=[_WRITE],
)
async def compose_invoice_for_sales_order(
    order_id: str,
    payload: ComposeInvoiceRequest,
    db_tenant=Depends(get_db_with_tenant),
    ctx: UserCtx = Depends(get_current_user),
) -> ComposeInvoiceResponse:
    """ADR-032: assemble draft Invoice from selected pending billables."""
    from backend.app.modules.sales_orders.compose_invoice import (
        ComposeInvoiceError,
        compose_invoice_from_billables,
    )

    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    own_company_id = await resolve_own_company_id_for_session(db, tenant_id, ctx, None)
    try:
        invoice = await compose_invoice_from_billables(
            db,
            tenant_id=tenant_id,
            sales_order_id=order_id,
            billable_item_ids=payload.billable_item_ids,
            actor_user_id=ctx.sub,
            own_company_id=own_company_id,
        )
        await db.commit()
        await db.refresh(invoice)
    except ComposeInvoiceError as exc:
        await db.rollback()
        code_map = {
            "not_found": status.HTTP_404_NOT_FOUND,
            "empty": status.HTTP_422_UNPROCESSABLE_ENTITY,
            "void": status.HTTP_422_UNPROCESSABLE_ENTITY,
            "currency": status.HTTP_422_UNPROCESSABLE_ENTITY,
            "conflict": status.HTTP_409_CONFLICT,
        }
        raise HTTPException(status_code=code_map.get(exc.code, 400), detail=exc.message) from exc
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return ComposeInvoiceResponse(
        invoice_id=str(invoice.id),
        invoice_number=getattr(invoice, "invoice_number", None),
        status=str(getattr(invoice, "status", "") or ""),
        currency=getattr(invoice, "currency", None),
        total_amount=getattr(invoice, "total_amount", None),
        billable_item_ids=list(payload.billable_item_ids),
    )


@router.post("/sales-billable-items", response_model=BillableItemOut, status_code=201, dependencies=[_WRITE])
async def create_billable_item(
    payload: BillableItemCreate,
    db_tenant=Depends(get_db_with_tenant),
) -> BillableItemOut:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    order = await db.get(SalesOrder, str(payload.sales_order_id).strip())
    if order is None or str(order.tenant_id) != tenant_id:
        raise HTTPException(status_code=404, detail="Sales order not found")
    tr = str(payload.trigger_code).strip().lower()
    if not _trigger_ok(tr):
        raise HTTPException(status_code=422, detail="Invalid trigger_code")
    if payload.sales_order_line_id:
        line = await db.get(SalesOrderLine, str(payload.sales_order_line_id).strip())
        if line is None or str(line.tenant_id) != tenant_id or line.sales_order_id != order.id:
            raise HTTPException(status_code=404, detail="Order line not found")
    item = SalesBillableItem(
        id=str(uuid4()),
        tenant_id=tenant_id,
        sales_order_id=order.id,
        sales_order_line_id=(str(payload.sales_order_line_id).strip() or None)
        if payload.sales_order_line_id
        else None,
        trigger_code=tr,
        amount=payload.amount,
        currency=str(payload.currency).strip().upper(),
        quantity=payload.quantity,
        source_entity_type=(str(payload.source_entity_type).strip() or None)
        if payload.source_entity_type
        else None,
        source_entity_id=(str(payload.source_entity_id).strip() or None)
        if payload.source_entity_id
        else None,
        status="pending",
        notes=(str(payload.notes).strip() or None) if payload.notes else None,
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return BillableItemOut(
        id=item.id,
        tenant_id=item.tenant_id,
        sales_order_id=item.sales_order_id,
        sales_order_line_id=item.sales_order_line_id,
        trigger_code=item.trigger_code,
        amount=item.amount,
        currency=item.currency,
        quantity=item.quantity,
        source_entity_type=item.source_entity_type,
        source_entity_id=item.source_entity_id,
        status=item.status,
        invoice_id=item.invoice_id,
        notes=item.notes,
    )
