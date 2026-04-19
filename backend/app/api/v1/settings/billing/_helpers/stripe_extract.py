"""Stripe event/invoice extractors + tenant-lookup + email helper.

Extracted from ``backend/app/api/v1/settings/billing/__init__.py`` as part of
the Phase 1 god-module split (step 4/N).

Contents:

* **Invoice serializers** — ``_extract_invoice_period``, ``_stripe_invoice_out``,
  ``_list_stripe_invoices`` (the latter uses late-import of
  ``billing.stripe`` so test-time patches propagate).
* **Tenant lookup for Stripe webhook events** — ``_find_tenant_for_stripe_event``
  (matches by ``tenant_id`` / ``customer_id`` / ``subscription_id`` /
  ``checkout_session_id`` against ``tenant.settings.billing.subscription``).
* **Subscription-payload extractors** — ``_extract_subscription_price_id``,
  ``_extract_subscription_billing_interval``,
  ``_find_subscription_item_by_price_id``, ``_find_operating_slot_addon_item``,
  ``_extract_operating_slot_addon_quantity``, ``_extract_subscription_period``,
  ``_extract_pending_update``, ``_extract_pending_update_plan_code``,
  ``_extract_pending_invoice_details``,
  ``_normalize_stripe_subscription_status``.
* **System email** — ``_send_billing_email`` (best-effort, swallows errors).

Pure module — no DB writes, only DB reads (in ``_find_tenant_for_stripe_event``).
Used by webhook handlers and the GET /summary endpoint.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.settings import settings
from backend.app.models.tenant import Tenant
from backend.app.services.system_email import send_system_email

from ..schemas import BillingInvoiceOut
from .plans import (
    _all_operating_slot_addon_price_ids,
    _plan_code_by_price_id,
    _stripe_obj_to_dict,
    _stripe_ready,
)
from .state import _iso_to_dt, _subscription_payload, _unix_to_iso


def _extract_invoice_period(obj: dict[str, Any]) -> tuple[datetime | None, datetime | None]:
    lines = obj.get("lines") if isinstance(obj.get("lines"), dict) else {}
    line_items = lines.get("data") if isinstance(lines.get("data"), list) else []
    for line in line_items:
        if not isinstance(line, dict):
            continue
        period = line.get("period") if isinstance(line.get("period"), dict) else {}
        return _iso_to_dt(_unix_to_iso(period.get("start"))), _iso_to_dt(_unix_to_iso(period.get("end")))
    return None, None


def _stripe_invoice_out(obj: dict[str, Any]) -> BillingInvoiceOut:
    period_start, period_end = _extract_invoice_period(obj)
    status_raw = str(obj.get("status") or "").strip().lower() or "open"
    return BillingInvoiceOut(
        id=str(obj.get("id") or ""),
        number=str(obj.get("number") or "").strip() or None,
        status="paid" if bool(obj.get("paid")) else status_raw,
        currency=str(obj.get("currency") or "").strip().upper() or None,
        total_minor=int(obj.get("total")) if obj.get("total") is not None else None,
        amount_paid_minor=int(obj.get("amount_paid")) if obj.get("amount_paid") is not None else None,
        amount_due_minor=int(obj.get("amount_due")) if obj.get("amount_due") is not None else None,
        created_at=_iso_to_dt(_unix_to_iso(obj.get("created"))),
        paid_at=_iso_to_dt(_unix_to_iso(obj.get("status_transitions", {}).get("paid_at"))) if isinstance(obj.get("status_transitions"), dict) else None,
        period_start=period_start,
        period_end=period_end,
        hosted_invoice_url=str(obj.get("hosted_invoice_url") or "").strip() or None,
        invoice_pdf_url=str(obj.get("invoice_pdf") or "").strip() or None,
    )


def _list_stripe_invoices(subscription: dict[str, Any]) -> list[BillingInvoiceOut]:
    customer_id = str(subscription.get("customer_id") or "").strip()
    if not (_stripe_ready() and customer_id):
        return []
    # Late-import the parent package's ``stripe`` attribute so test-time patches
    # of ``billing.stripe`` propagate here without holding a stale reference.
    from backend.app.api.v1.settings import billing as _billing_pkg
    stripe_mod = _billing_pkg.stripe
    stripe_mod.api_key = settings.stripe_secret_key
    try:
        result = stripe_mod.Invoice.list(customer=customer_id, limit=12)
    except Exception:
        return []
    result_dict = _stripe_obj_to_dict(result)
    data = result_dict.get("data") if isinstance(result_dict.get("data"), list) else getattr(result, "data", None)
    rows = []
    if isinstance(data, list):
        for item in data:
            item_dict = _stripe_obj_to_dict(item)
            if item_dict:
                rows.append(item_dict)
    return [_stripe_invoice_out(item) for item in rows]


async def _send_billing_email(to_email: str | None, *, subject: str, body: str) -> None:
    to = (to_email or "").strip()
    if not to:
        return
    try:
        await send_system_email(to=to, subject=subject, body=body)
    except Exception:
        return


async def _find_tenant_for_stripe_event(
    db: AsyncSession,
    *,
    tenant_id: str | None = None,
    customer_id: str | None = None,
    subscription_id: str | None = None,
    checkout_session_id: str | None = None,
) -> Tenant | None:
    tid = (tenant_id or "").strip()
    if tid:
        tenant = await db.get(Tenant, tid)
        if tenant is not None:
            return tenant
    cid = (customer_id or "").strip()
    sid = (subscription_id or "").strip()
    csid = (checkout_session_id or "").strip()
    if not (cid or sid or csid):
        return None
    tenants = (await db.execute(select(Tenant))).scalars().all()
    for tenant in tenants:
        payload = _subscription_payload(tenant)
        if sid and str(payload.get("subscription_id") or "").strip() == sid:
            return tenant
        if cid and str(payload.get("customer_id") or "").strip() == cid:
            return tenant
        if csid and str(payload.get("checkout_session_id") or "").strip() == csid:
            return tenant
    return None


def _extract_subscription_price_id(sub_obj: dict[str, Any]) -> str | None:
    items = sub_obj.get("items")
    if not isinstance(items, dict):
        return None
    data = items.get("data")
    if not isinstance(data, list) or not data:
        return None
    first = _stripe_obj_to_dict(data[0])
    price = _stripe_obj_to_dict(first.get("price"))
    if not price:
        return None
    return str(price.get("id") or "").strip() or None


def _extract_subscription_billing_interval(sub_obj: dict[str, Any]) -> Literal["month", "year"]:
    items = sub_obj.get("items")
    if not isinstance(items, dict):
        return "month"
    data = items.get("data")
    if not isinstance(data, list) or not data:
        return "month"
    first = _stripe_obj_to_dict(data[0])
    price = _stripe_obj_to_dict(first.get("price"))
    rec = price.get("recurring") if isinstance(price.get("recurring"), dict) else {}
    iv = str(rec.get("interval") or "month").strip().lower()
    return "year" if iv == "year" else "month"


def _find_subscription_item_by_price_id(sub_obj: dict[str, Any], price_id: str) -> dict[str, Any] | None:
    target = (price_id or "").strip()
    if not target:
        return None
    items = sub_obj.get("items")
    item_data = []
    if isinstance(items, dict) and isinstance(items.get("data"), list):
        item_data = items.get("data") or []
    for item in item_data:
        item_dict = _stripe_obj_to_dict(item)
        price = _stripe_obj_to_dict(item_dict.get("price"))
        if str(price.get("id") or "").strip() == target:
            return item_dict
    return None


def _find_operating_slot_addon_item(sub_obj: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None]:
    for pid in _all_operating_slot_addon_price_ids():
        item = _find_subscription_item_by_price_id(sub_obj, pid)
        if item:
            return item, pid
    return None, None


def _extract_operating_slot_addon_quantity(sub_obj: dict[str, Any]) -> int | None:
    if not _all_operating_slot_addon_price_ids():
        return None
    addon_item, _ = _find_operating_slot_addon_item(sub_obj)
    if addon_item is None:
        return 0
    raw_quantity = addon_item.get("quantity")
    if raw_quantity is None:
        return 1
    try:
        quantity = int(raw_quantity)
    except (TypeError, ValueError):
        return 0
    return max(0, quantity)


def _extract_subscription_period(sub_obj: dict[str, Any]) -> tuple[str | None, str | None]:
    start_iso = _unix_to_iso(sub_obj.get("current_period_start"))
    end_iso = _unix_to_iso(sub_obj.get("current_period_end"))
    if start_iso or end_iso:
        return start_iso, end_iso
    items = sub_obj.get("items")
    if not isinstance(items, dict):
        return None, None
    data = items.get("data")
    if not isinstance(data, list) or not data:
        return None, None
    first = _stripe_obj_to_dict(data[0])
    return _unix_to_iso(first.get("current_period_start")), _unix_to_iso(first.get("current_period_end"))


def _extract_pending_update(sub_obj: dict[str, Any]) -> dict[str, Any]:
    pending = sub_obj.get("pending_update")
    return dict(pending) if isinstance(pending, dict) else {}


def _extract_pending_update_plan_code(sub_obj: dict[str, Any]) -> str | None:
    pending = _extract_pending_update(sub_obj)
    items = pending.get("subscription_items")
    if not isinstance(items, list) or not items:
        return None
    first = _stripe_obj_to_dict(items[0])
    price = _stripe_obj_to_dict(first.get("price"))
    price_id = str(price.get("id") or "").strip() or None
    if not price_id:
        return None
    return _plan_code_by_price_id(price_id)


def _extract_pending_invoice_details(sub_obj: dict[str, Any]) -> tuple[str | None, str | None]:
    pending = _extract_pending_update(sub_obj)
    invoice = _stripe_obj_to_dict(pending.get("invoice"))
    latest_invoice = _stripe_obj_to_dict(sub_obj.get("latest_invoice"))
    invoice_id = str(invoice.get("id") or latest_invoice.get("id") or "").strip() or None
    invoice_url = str(invoice.get("hosted_invoice_url") or latest_invoice.get("hosted_invoice_url") or "").strip() or None
    return invoice_id, invoice_url


def _normalize_stripe_subscription_status(raw: Any) -> str:
    status_raw = str(raw or "").strip().lower()
    mapping = {
        "trialing": "trial",
        "active": "active",
        "past_due": "past_due",
        "canceled": "canceled",
        "unpaid": "past_due",
        "incomplete": "incomplete",
        "incomplete_expired": "canceled",
    }
    return mapping.get(status_raw, "incomplete")
