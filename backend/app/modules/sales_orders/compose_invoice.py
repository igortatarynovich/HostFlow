"""Compose Finance Invoice from pending Sales billable items (ADR-032)."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Any, Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.v1.invoices import crud as invoice_crud
from backend.app.models.invoice import Invoice, InvoiceStatus
from backend.app.models.sales_order import SalesBillableItem, SalesOrder, SalesOrderLine


class ComposeInvoiceError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


def _dec(value: object | None, default: str = "0") -> Decimal:
    if value is None:
        return Decimal(default)
    try:
        return Decimal(str(value))
    except Exception:
        return Decimal(default)


def _line_description(line: Optional[SalesOrderLine], billable: SalesBillableItem) -> str:
    title = (line.title if line else None) or billable.trigger_code
    trigger = str(billable.trigger_code or "").replace("_", " ")
    base = f"{title} · {trigger}"
    if billable.notes:
        return f"{base} ({billable.notes})"
    return base


async def compose_invoice_from_billables(
    db: AsyncSession,
    *,
    tenant_id: str,
    sales_order_id: str,
    billable_item_ids: Sequence[str],
    actor_user_id: Optional[str],
    own_company_id: Optional[str] = None,
) -> Invoice:
    """Create draft Invoice from selected pending billables; mark them invoiced.

    Partial selection is allowed. Idempotent when all IDs already share one invoice_id.
    """
    tid = str(tenant_id).strip()
    oid = str(sales_order_id).strip()
    ids = [str(x).strip() for x in billable_item_ids if str(x).strip()]
    if not ids:
        raise ComposeInvoiceError("empty", "billable_item_ids required")

    order = await db.get(SalesOrder, oid)
    if order is None or str(order.tenant_id) != tid:
        raise ComposeInvoiceError("not_found", "Sales order not found")

    rows = (
        await db.execute(
            select(SalesBillableItem).where(
                SalesBillableItem.tenant_id == tid,
                SalesBillableItem.sales_order_id == oid,
                SalesBillableItem.id.in_(ids),
            )
        )
    ).scalars().all()
    by_id = {r.id: r for r in rows}
    missing = [i for i in ids if i not in by_id]
    if missing:
        raise ComposeInvoiceError("not_found", f"Billable items not found: {', '.join(missing[:5])}")

    selected = [by_id[i] for i in ids]
    invoiced = [r for r in selected if r.status == "invoiced" and r.invoice_id]
    pending = [r for r in selected if r.status == "pending"]
    voided = [r for r in selected if r.status == "void"]
    if voided:
        raise ComposeInvoiceError("void", "Cannot invoice void billable items")
    if invoiced and not pending:
        inv_ids = {str(r.invoice_id) for r in invoiced}
        if len(inv_ids) == 1:
            existing = await db.get(Invoice, next(iter(inv_ids)))
            if existing is not None and str(existing.tenant_id) == tid:
                return existing
        raise ComposeInvoiceError("conflict", "Selected billables already on different invoices")
    if invoiced and pending:
        raise ComposeInvoiceError("conflict", "Mix of pending and already-invoiced billables")
    if not pending:
        raise ComposeInvoiceError("empty", "No pending billables to invoice")

    currencies = {(str(r.currency or "").strip().upper() or "PLN") for r in pending}
    if len(currencies) > 1:
        raise ComposeInvoiceError("currency", "Mixed currencies in selection")
    currency = next(iter(currencies))
    order_currency = (str(order.currency or "").strip().upper() or currency)
    if order_currency and order_currency != currency:
        # Prefer billable currency if it differs (accrual is SoT for amount currency).
        pass

    line_ids = {str(r.sales_order_line_id) for r in pending if r.sales_order_line_id}
    lines_by_id: dict[str, SalesOrderLine] = {}
    if line_ids:
        line_rows = (
            await db.execute(
                select(SalesOrderLine).where(
                    SalesOrderLine.tenant_id == tid,
                    SalesOrderLine.id.in_(list(line_ids)),
                )
            )
        ).scalars().all()
        lines_by_id = {r.id: r for r in line_rows}

    vat_rate = _dec(order.vat_rate, "23")
    items_payload: list[dict[str, Any]] = []
    for idx, billable in enumerate(pending, start=1):
        qty = _dec(billable.quantity, "1")
        if qty <= 0:
            qty = Decimal("1")
        amount = _dec(billable.amount)
        unit_price = (amount / qty) if qty else amount
        line = lines_by_id.get(str(billable.sales_order_line_id)) if billable.sales_order_line_id else None
        items_payload.append(
            {
                "line_no": idx,
                "description": _line_description(line, billable),
                "qty": qty,
                "unit_price": unit_price,
                "vat_rate": vat_rate,
            }
        )

    issue_date = date.today()
    term_days = int(order.payment_term_days) if order.payment_term_days is not None else 14
    due_date = issue_date + timedelta(days=max(0, term_days))
    payer_id = str(order.payer_company_id or order.company_id)

    invoice = await invoice_crud.create_invoice(
        db,
        tid,
        {
            "own_company_id": own_company_id,
            "company_id": payer_id,
            "order_id": order.id,
            "issue_date": issue_date,
            "due_date": due_date,
            "currency": currency,
            "status": InvoiceStatus.draft.value,
            "items": items_payload,
            "notes": order.billing_notes,
            "billing_details": {
                "payment_terms_days": term_days,
                "sales_order_id": order.id,
                "source": "sales_billable_items",
            },
        },
        created_by=actor_user_id,
    )

    for billable in pending:
        billable.status = "invoiced"
        billable.invoice_id = invoice.id

    await db.flush()
    return invoice
