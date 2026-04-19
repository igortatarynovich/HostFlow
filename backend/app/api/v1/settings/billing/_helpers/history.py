"""Billing-history serialization helpers.

Extracted from ``backend/app/api/v1/settings/billing/__init__.py`` as part of
the Phase 1 god-module split (step 5/N).

Contents:

* ``_history_entry`` — build a normalized dict-row for ``tenant.settings.billing.history``.
* ``_history_out`` — render the ``history`` list as ``BillingHistoryItemOut`` rows
  (sorted, capped to 20).
* ``_merge_history_with_invoices`` — merge in Stripe invoice rows that don't
  already appear in the tenant's local history.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import uuid4

from backend.app.models.tenant import Tenant

from ..schemas import BillingHistoryItemOut, BillingInvoiceOut
from .state import _billing_history, _iso_to_dt, _now_utc


def _history_entry(
    *,
    event_type: str,
    status: str,
    title: str,
    description: str | None = None,
    source: Literal["app", "stripe"] = "app",
    occurred_at: datetime | None = None,
    plan_code: str | None = None,
    amount_minor: int | None = None,
    currency: str | None = None,
    invoice_id: str | None = None,
    hosted_invoice_url: str | None = None,
    invoice_pdf_url: str | None = None,
    dedupe_key: str | None = None,
) -> dict[str, Any]:
    ts = occurred_at or _now_utc()
    return {
        "id": uuid4().hex,
        "occurred_at": ts.isoformat(),
        "event_type": event_type,
        "status": status,
        "title": title,
        "description": description,
        "source": source,
        "plan_code": plan_code,
        "amount_minor": amount_minor,
        "currency": currency,
        "invoice_id": invoice_id,
        "hosted_invoice_url": hosted_invoice_url,
        "invoice_pdf_url": invoice_pdf_url,
        "dedupe_key": (dedupe_key or "").strip() or None,
    }


def _history_out(tenant: Tenant) -> list[BillingHistoryItemOut]:
    rows: list[BillingHistoryItemOut] = []
    for item in _billing_history(tenant):
        occurred_at = _iso_to_dt(item.get("occurred_at")) or _now_utc()
        rows.append(
            BillingHistoryItemOut(
                id=str(item.get("id") or uuid4().hex),
                occurred_at=occurred_at,
                event_type=str(item.get("event_type") or "unknown"),
                status=str(item.get("status") or "info"),
                title=str(item.get("title") or "Billing event"),
                description=str(item.get("description") or "").strip() or None,
                source="stripe" if str(item.get("source") or "").strip().lower() == "stripe" else "app",
                plan_code=str(item.get("plan_code") or "").strip() or None,
                amount_minor=int(item.get("amount_minor")) if item.get("amount_minor") is not None else None,
                currency=str(item.get("currency") or "").strip().upper() or None,
                invoice_id=str(item.get("invoice_id") or "").strip() or None,
                hosted_invoice_url=str(item.get("hosted_invoice_url") or "").strip() or None,
                invoice_pdf_url=str(item.get("invoice_pdf_url") or "").strip() or None,
            )
        )
    rows.sort(key=lambda item: item.occurred_at, reverse=True)
    return rows[:20]


def _merge_history_with_invoices(
    history: list[BillingHistoryItemOut],
    invoices: list[BillingInvoiceOut],
) -> list[BillingHistoryItemOut]:
    seen_invoice_ids = {str(item.invoice_id or "").strip() for item in history if str(item.invoice_id or "").strip()}
    merged = list(history)
    for invoice in invoices:
        invoice_id = str(invoice.id or "").strip()
        if not invoice_id or invoice_id in seen_invoice_ids:
            continue
        status_value = str(invoice.status or "open").strip().lower()
        merged.append(
            BillingHistoryItemOut(
                id=f"invoice-{invoice_id}",
                occurred_at=invoice.paid_at or invoice.created_at or _now_utc(),
                event_type="invoice.paid" if status_value == "paid" else "invoice.updated",
                status="success" if status_value == "paid" else ("warning" if status_value in {"open", "uncollectible"} else "info"),
                title="Payment received" if status_value == "paid" else "Invoice updated",
                description="Stripe invoice is available in billing history.",
                source="stripe",
                plan_code=None,
                amount_minor=invoice.amount_paid_minor if status_value == "paid" else invoice.total_minor,
                currency=invoice.currency,
                invoice_id=invoice.id,
                hosted_invoice_url=invoice.hosted_invoice_url,
                invoice_pdf_url=invoice.invoice_pdf_url,
            )
        )
    merged.sort(key=lambda item: item.occurred_at, reverse=True)
    return merged[:20]
