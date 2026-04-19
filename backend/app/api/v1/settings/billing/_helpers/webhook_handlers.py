"""Stripe webhook event handlers + idempotency claim/release.

Extracted from ``backend/app/api/v1/settings/billing/__init__.py`` as part of
the Phase 1 god-module split (step 6/N).

Contents:

* **Idempotency** — ``_stripe_webhook_try_claim_event`` /
  ``_stripe_webhook_release_claim`` (atomic INSERT … ON CONFLICT DO NOTHING
  on ``stripe_webhook_event_log`` so concurrent deliveries of the same
  ``event_id`` do not double-apply side-effects).
* **checkout.session.completed** — ``_handle_checkout_completed`` (top-level
  dispatcher routing to one of three sub-handlers based on
  ``metadata.billing_action``):
    - ``_handle_portal_candidates_pack_checkout_completed``
    - ``_handle_addon_pack_checkout_completed``
    - inline ``plan_change`` branch.
* **invoice.* handlers** — ``_handle_invoice_paid``,
  ``_handle_invoice_finalized``, ``_handle_invoice_payment_failed``.
* **customer.subscription.created/updated/deleted** —
  ``_handle_subscription_event``.

All Stripe SDK references go through ``_get_stripe()`` which late-imports
``billing.stripe`` so test-time patches of ``billing.stripe`` propagate
without holding a stale module reference.
"""

from __future__ import annotations

from typing import Any, Literal
from uuid import uuid4

from sqlalchemy import delete
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.settings import settings
from backend.app.models.stripe_webhook_event import StripeWebhookEventLog
from backend.app.services.operating_company_slots import extract_extra_operating_company_slots
from backend.app.services.stripe_price_catalog import sku_pack_increment, sku_price_from_settings

from .history import _history_entry
from .license_sync import _apply_license_limits
from .packs import (
    _apply_addon_pack_by_sku,
    _apply_portal_candidates_pack_to_tenant,
    _checkout_session_line_items_contain_price,
)
from .plans import (
    ADDON_PACK_CHECKOUT_READY,
    _normalize_plan_code,
    _plan_code_by_price_id,
    _plan_stripe_price_id,
    _portal_candidates_pack_price_id,
    _stripe_obj_to_dict,
    _stripe_ready,
)
from .state import (
    _history_contains,
    _now_utc,
    _set_extra_operating_slots,
    _store_subscription,
    _subscription_payload,
)
from .stripe_extract import (
    _extract_operating_slot_addon_quantity,
    _extract_pending_invoice_details,
    _extract_pending_update,
    _extract_pending_update_plan_code,
    _extract_subscription_billing_interval,
    _extract_subscription_period,
    _extract_subscription_price_id,
    _find_tenant_for_stripe_event,
    _normalize_stripe_subscription_status,
    _send_billing_email,
    _unix_to_iso,
)
from .summary import _maybe_enroll_founder_program


def _get_stripe():
    """Late-bind the parent package's ``stripe`` attribute so test-time patches
    of ``billing.stripe`` (e.g. via ``patch.object(billing, "stripe", mock)``)
    are observed without us holding a stale module reference."""
    from backend.app.api.v1.settings import billing as _billing_pkg
    return _billing_pkg.stripe


async def _handle_portal_candidates_pack_checkout_completed(db: AsyncSession, obj: dict[str, Any]) -> str:
    """One-time Checkout (mode=payment) — adds to usage_v1.portal_monthly_cap_addon_v1 (§2.16)."""
    metadata = obj.get("metadata") if isinstance(obj.get("metadata"), dict) else {}
    tenant = await _find_tenant_for_stripe_event(
        db,
        tenant_id=str(metadata.get("tenant_id") or obj.get("client_reference_id") or "").strip() or None,
        checkout_session_id=str(obj.get("id") or "").strip() or None,
        customer_id=str(obj.get("customer") or "").strip() or None,
        subscription_id=None,
    )
    if tenant is None:
        return "Ignored: tenant not found for portal_candidates_pack checkout"
    session_id = str(obj.get("id") or "").strip()
    dedupe_key = f"stripe:{session_id}:portal_candidates_pack"
    if _history_contains(tenant, dedupe_key):
        return "Duplicate portal pack checkout ignored"

    if str(obj.get("mode") or "").strip().lower() != "payment":
        return "Ignored: portal pack checkout is not mode=payment"

    ps = str(obj.get("payment_status") or "").strip().lower()
    if ps not in {"paid", "no_payment_required"}:
        return f"Ignored: portal pack payment_status={ps}"

    expected_price = _portal_candidates_pack_price_id()
    if not expected_price or not _stripe_ready():
        return "Ignored: portal pack Stripe price not configured"

    try:
        increment = int(str(metadata.get("pack_increment") or "").strip() or settings.portal_candidates_pack_increment)
    except (TypeError, ValueError):
        increment = int(settings.portal_candidates_pack_increment)
    if increment <= 0:
        return "Ignored: invalid pack_increment"

    _get_stripe().api_key = settings.stripe_secret_key
    try:
        full = _stripe_obj_to_dict(
            _get_stripe().checkout.Session.retrieve(session_id, expand=["line_items.data.price"])  # type: ignore[union-attr]
        )
    except Exception as exc:  # pragma: no cover - network
        return f"Ignored: could not retrieve checkout session: {exc}"

    if not _checkout_session_line_items_contain_price(full, expected_price):
        return "Ignored: portal pack checkout line item price mismatch"

    sub = _subscription_payload(tenant)
    plan_code = _normalize_plan_code(str(metadata.get("plan_code") or sub.get("plan_code") or "starter"))
    await _apply_portal_candidates_pack_to_tenant(
        db,
        tenant,
        increment=increment,
        history_title="Candidate portal pack purchased",
        history_description=f"+{increment} active portal candidates / month (add-on).",
        dedupe_key=dedupe_key,
        plan_code=plan_code,
        history_source="stripe",
    )
    return f"Applied portal_candidates_pack for tenant={tenant.id} (+{increment})"


async def _handle_addon_pack_checkout_completed(db: AsyncSession, obj: dict[str, Any]) -> str:
    metadata = obj.get("metadata") if isinstance(obj.get("metadata"), dict) else {}
    sku = str(metadata.get("billing_sku") or "").strip()
    if sku not in ADDON_PACK_CHECKOUT_READY:
        return f"Ignored: addon pack SKU not supported ({sku or 'missing'})"
    tenant = await _find_tenant_for_stripe_event(
        db,
        tenant_id=str(metadata.get("tenant_id") or obj.get("client_reference_id") or "").strip() or None,
        checkout_session_id=str(obj.get("id") or "").strip() or None,
        customer_id=str(obj.get("customer") or "").strip() or None,
        subscription_id=None,
    )
    if tenant is None:
        return "Ignored: tenant not found for addon_pack checkout"
    session_id = str(obj.get("id") or "").strip()
    dedupe_key = f"stripe:{session_id}:addon_pack:{sku}"
    if _history_contains(tenant, dedupe_key):
        return "Duplicate addon pack checkout ignored"

    if str(obj.get("mode") or "").strip().lower() != "payment":
        return "Ignored: addon pack checkout is not mode=payment"

    ps = str(obj.get("payment_status") or "").strip().lower()
    if ps not in {"paid", "no_payment_required"}:
        return f"Ignored: addon pack payment_status={ps}"

    expected_price = sku_price_from_settings(settings, sku)
    if not expected_price or not _stripe_ready():
        return "Ignored: addon pack Stripe price not configured"

    base_inc = sku_pack_increment(settings, sku)
    try:
        meta_inc = int(str(metadata.get("pack_increment") or "").strip() or "0")
    except (TypeError, ValueError):
        meta_inc = 0
    increment = meta_inc if meta_inc > 0 else (base_inc or 0)
    if increment <= 0:
        return "Ignored: invalid pack_increment"

    _get_stripe().api_key = settings.stripe_secret_key
    try:
        full = _stripe_obj_to_dict(
            _get_stripe().checkout.Session.retrieve(session_id, expand=["line_items.data.price"])  # type: ignore[union-attr]
        )
    except Exception as exc:  # pragma: no cover - network
        return f"Ignored: could not retrieve checkout session: {exc}"

    if not _checkout_session_line_items_contain_price(full, expected_price):
        return "Ignored: addon pack checkout line item price mismatch"

    sub = _subscription_payload(tenant)
    plan_code = _normalize_plan_code(str(metadata.get("plan_code") or sub.get("plan_code") or "starter"))

    if sku == "pack_portal_candidates":
        if portal_candidate_usage.monthly_cap_for_plan_code(plan_code) is None:
            return "Ignored: portal pack not applicable to plan"
    elif sku in ("pack_custom_fields_25", "pack_custom_fields_100"):
        if plan_allows_team_tier_features(plan_code):
            return "Ignored: lead custom field pack not applicable to Team-tier plan"
    elif not plan_allows_team_tier_features(plan_code):
        return "Ignored: addon pack requires Team-tier plan"

    await _apply_addon_pack_by_sku(
        db,
        tenant,
        sku=sku,
        increment=increment,
        dedupe_key=dedupe_key,
        plan_code=plan_code,
        history_source="stripe",
    )
    return f"Applied addon_pack sku={sku} for tenant={tenant.id}"


async def _handle_checkout_completed(db: AsyncSession, obj: dict[str, Any]) -> str:
    metadata = obj.get("metadata") if isinstance(obj.get("metadata"), dict) else {}
    billing_action = str(metadata.get("billing_action") or "new_subscription").strip().lower()
    if billing_action == "portal_candidates_pack":
        return await _handle_portal_candidates_pack_checkout_completed(db, obj)
    if billing_action == "addon_pack":
        return await _handle_addon_pack_checkout_completed(db, obj)
    if billing_action == "plan_change":
        tenant = await _find_tenant_for_stripe_event(
            db,
            tenant_id=str(metadata.get("tenant_id") or obj.get("client_reference_id") or "").strip() or None,
            customer_id=str(obj.get("customer") or metadata.get("customer_id") or "").strip() or None,
            subscription_id=str(metadata.get("subscription_id") or "").strip() or None,
        )
        if tenant is None:
            return "Ignored: tenant not found for checkout.session.completed(plan_change)"
        tenant_id = str(tenant.id)
        target_plan_code = _normalize_plan_code(str(metadata.get("target_plan_code") or metadata.get("plan_code") or "starter"))
        subscription_id = str(metadata.get("subscription_id") or "").strip()
        if not subscription_id:
            return f"Ignored: missing subscription_id for tenant={tenant_id} plan_change checkout"
        _get_stripe().api_key = settings.stripe_secret_key
        sub = _stripe_obj_to_dict(
            _get_stripe().Subscription.retrieve(subscription_id, expand=["items.data.price"])  # type: ignore[union-attr]
        )
        items = sub.get("items", {}).get("data", []) if isinstance(sub, dict) else []
        first_item = _stripe_obj_to_dict(items[0]) if isinstance(items, list) and items else {}
        item_id = str(first_item.get("id") or "").strip()
        meta_biv = str(metadata.get("billing_interval") or "").strip().lower()
        bill_iv: Literal["month", "year"] = (
            meta_biv if meta_biv in ("month", "year") else _extract_subscription_billing_interval(sub)
        )
        target_price_id = _plan_stripe_price_id(target_plan_code, bill_iv)
        if not item_id or not target_price_id:
            return f"Ignored: missing subscription item/price for tenant={tenant_id} plan_change checkout"
        updated_sub = _stripe_obj_to_dict(_get_stripe().Subscription.modify(  # type: ignore[union-attr]
            subscription_id,
            items=[{"id": item_id, "price": target_price_id}],
            proration_behavior="none",
        ))
        detail = await _handle_subscription_event(db, updated_sub, deleted=False)
        current = _subscription_payload(tenant)
        invoice_id = str(obj.get("invoice") or "").strip() or None
        hosted_invoice_url = None
        invoice_pdf_url = None
        if invoice_id:
            try:
                invoice_obj = _stripe_obj_to_dict(_get_stripe().Invoice.retrieve(invoice_id))  # type: ignore[union-attr]
                hosted_invoice_url = str(invoice_obj.get("hosted_invoice_url") or "").strip() or None
                invoice_pdf_url = str(invoice_obj.get("invoice_pdf") or "").strip() or None
            except Exception:
                pass
        now = _now_utc()
        await _store_subscription(
            db,
            tenant,
            {
                **current,
                "provider": "stripe",
                "status": "active",
                "plan_code": target_plan_code,
                "billing_interval": _extract_subscription_billing_interval(updated_sub),
                "pending_plan_code": None,
                "pending_update": False,
                "pending_invoice_id": None,
                "pending_invoice_url": None,
                "checkout_session_id": str(obj.get("id") or current.get("checkout_session_id") or "").strip() or None,
                "customer_id": str(obj.get("customer") or current.get("customer_id") or "").strip() or None,
                "subscription_id": subscription_id,
                "updated_at": now.isoformat(),
            },
            history_entry=_history_entry(
                event_type="checkout.session.completed",
                status="success",
                title="Plan payment confirmed",
                description=f"Stripe confirmed payment for the {target_plan_code.upper()} plan change.",
                source="stripe",
                occurred_at=now,
                plan_code=target_plan_code,
                invoice_id=invoice_id,
                hosted_invoice_url=hosted_invoice_url,
                invoice_pdf_url=invoice_pdf_url,
                dedupe_key=f"stripe:{str(obj.get('id') or '').strip()}:checkout.session.completed:plan_change:{target_plan_code}",
            ),
        )
        await _maybe_enroll_founder_program(db, tenant_id, target_plan_code)
        return f"{detail}; checkout completed for tenant={tenant_id} plan_change={target_plan_code}"
    tenant = await _find_tenant_for_stripe_event(
        db,
        tenant_id=str(metadata.get("tenant_id") or obj.get("client_reference_id") or "").strip() or None,
        checkout_session_id=str(obj.get("id") or "").strip() or None,
        customer_id=str(obj.get("customer") or "").strip() or None,
        subscription_id=str(obj.get("subscription") or "").strip() or None,
    )
    if tenant is None:
        return "Ignored: tenant not found for checkout.session.completed"
    tenant_id = str(tenant.id)
    current = _subscription_payload(tenant)
    plan_code = (
        _normalize_plan_code(str(metadata.get("plan_code") or current.get("plan_code") or "starter"))
    )
    meta_iv = str(metadata.get("billing_interval") or current.get("billing_interval") or "month").strip().lower()
    if meta_iv not in ("month", "year"):
        meta_iv = "month"
    now = _now_utc()
    dedupe_key = f"stripe:{str(obj.get('id') or '').strip()}:checkout.session.completed"
    history_entry = None if _history_contains(tenant, dedupe_key) else _history_entry(
        event_type="checkout.session.completed",
        status="success",
        title="Subscription activated",
        description=f"Plan {plan_code.upper()} is active. Stripe checkout completed successfully.",
        source="stripe",
        occurred_at=now,
        plan_code=plan_code,
        dedupe_key=dedupe_key,
    )
    updated = {
        **current,
        "provider": "stripe",
        "status": "active",
        "plan_code": plan_code,
        "billing_interval": meta_iv,
        "pending_plan_code": None,
        "pending_update": False,
        "pending_invoice_id": None,
        "pending_invoice_url": None,
        "checkout_session_id": str(obj.get("id") or current.get("checkout_session_id") or "").strip() or None,
        "customer_id": str(obj.get("customer") or current.get("customer_id") or "").strip() or None,
        "subscription_id": str(obj.get("subscription") or current.get("subscription_id") or "").strip() or None,
        "cancel_at_period_end": False,
        "canceled_at": None,
        "activated_at": str(current.get("activated_at") or "").strip() or now.isoformat(),
        "billing_contact_email": str(current.get("billing_contact_email") or "").strip() or None,
        "updated_at": now.isoformat(),
    }
    await _store_subscription(db, tenant, updated, history_entry=history_entry)
    await _maybe_enroll_founder_program(db, tenant_id, plan_code)
    await _apply_license_limits(db, tenant_id, plan_code)
    if history_entry:
        await _send_billing_email(
            updated.get("billing_contact_email"),
            subject="Your HostFlow subscription is active",
            body=(
                f"Your HostFlow {plan_code.upper()} subscription is now active.\n\n"
                f"Plan: {plan_code.upper()}\n"
                f"Subscription starts: {updated.get('activated_at') or '-'}\n"
                f"Current period ends: {updated.get('current_period_end') or '-'}\n\n"
                "You can review your plan, invoices and renewal settings in Billing."
            ),
        )
    return f"Processed checkout.session.completed for tenant={tenant_id}"


async def _handle_invoice_paid(db: AsyncSession, obj: dict[str, Any]) -> str:
    tenant = await _find_tenant_for_stripe_event(
        db,
        customer_id=str(obj.get("customer") or "").strip() or None,
        subscription_id=str(obj.get("subscription") or "").strip() or None,
    )
    if tenant is None:
        return "Ignored: tenant not found for invoice.paid"
    tenant_id = str(tenant.id)
    current = _subscription_payload(tenant)
    plan_code = _normalize_plan_code(str(current.get("plan_code") or "starter"))
    synced_extra_slots: int | None = None
    if _stripe_ready():
        subscription_id_raw = str(obj.get("subscription") or current.get("subscription_id") or "").strip()
        if subscription_id_raw:
            _get_stripe().api_key = settings.stripe_secret_key
            try:
                sub_obj = _stripe_obj_to_dict(_get_stripe().Subscription.retrieve(subscription_id_raw, expand=["items.data.price"]))  # type: ignore[union-attr]
                synced_extra_slots = _extract_operating_slot_addon_quantity(sub_obj)
            except Exception:
                synced_extra_slots = None
    lines = obj.get("lines") if isinstance(obj.get("lines"), dict) else {}
    line_items = lines.get("data") if isinstance(lines.get("data"), list) else []
    period_end: str | None = None
    period_start: str | None = None
    for line in line_items:
        if not isinstance(line, dict):
            continue
        period = line.get("period") if isinstance(line.get("period"), dict) else {}
        period_start = _unix_to_iso(period.get("start"))
        period_end = _unix_to_iso(period.get("end"))
        if period_end:
            break
    now = _now_utc()
    amount_paid = int(obj.get("amount_paid")) if obj.get("amount_paid") is not None else None
    currency = str(obj.get("currency") or "").strip().upper() or None
    invoice_id = str(obj.get("id") or "").strip() or None
    dedupe_key = f"stripe:{invoice_id or uuid4().hex}:invoice.paid"
    history_entry = None if _history_contains(tenant, dedupe_key) else _history_entry(
        event_type="invoice.paid",
        status="success",
        title="Payment received",
        description="Stripe confirmed the invoice payment.",
        source="stripe",
        occurred_at=now,
        plan_code=plan_code,
        amount_minor=amount_paid,
        currency=currency,
        invoice_id=invoice_id,
        hosted_invoice_url=str(obj.get("hosted_invoice_url") or "").strip() or None,
        invoice_pdf_url=str(obj.get("invoice_pdf") or "").strip() or None,
        dedupe_key=dedupe_key,
    )
    updated = {
        **current,
        "provider": "stripe",
        "status": "active",
        "plan_code": plan_code,
        "pending_plan_code": None,
        "pending_update": False,
        "pending_invoice_id": None,
        "pending_invoice_url": None,
        "customer_id": str(obj.get("customer") or current.get("customer_id") or "").strip() or None,
        "subscription_id": str(obj.get("subscription") or current.get("subscription_id") or "").strip() or None,
        "current_period_start": period_start or current.get("current_period_start"),
        "current_period_end": period_end or current.get("current_period_end"),
        "cancel_at_period_end": False,
        "canceled_at": None,
        "updated_at": now.isoformat(),
    }
    if synced_extra_slots is not None:
        updated = _set_extra_operating_slots(updated, synced_extra_slots)
    await _store_subscription(db, tenant, updated, history_entry=history_entry)
    await _apply_license_limits(db, tenant_id, plan_code)
    if history_entry:
        amount_text = f"{(amount_paid or 0) / 100:.2f} {currency or ''}".strip()
        await _send_billing_email(
            updated.get("billing_contact_email"),
            subject="Payment confirmation from HostFlow",
            body=(
                f"We received your payment for the HostFlow {plan_code.upper()} plan.\n\n"
                f"Amount: {amount_text or '-'}\n"
                f"Invoice: {invoice_id or '-'}\n"
                f"Current period ends: {updated.get('current_period_end') or '-'}\n\n"
                "Thank you. You can find your billing history and invoices in Billing."
            ),
        )
    return f"Processed invoice.paid for tenant={tenant_id}"


async def _handle_invoice_finalized(db: AsyncSession, obj: dict[str, Any]) -> str:
    """Stripe invoice.finalized — PDF/hosted URL available; subscription unchanged (§2.18)."""
    tenant = await _find_tenant_for_stripe_event(
        db,
        customer_id=str(obj.get("customer") or "").strip() or None,
        subscription_id=str(obj.get("subscription") or "").strip() or None,
    )
    if tenant is None:
        return "Ignored: tenant not found for invoice.finalized"
    tenant_id = str(tenant.id)
    current = _subscription_payload(tenant)
    plan_code = _normalize_plan_code(str(current.get("plan_code") or "starter"))
    now = _now_utc()
    invoice_id = str(obj.get("id") or "").strip() or None
    amount_due = int(obj.get("amount_due")) if obj.get("amount_due") is not None else None
    currency = str(obj.get("currency") or "").strip().upper() or None
    dedupe_key = f"stripe:{invoice_id or 'unknown'}:invoice.finalized"
    if _history_contains(tenant, dedupe_key):
        return f"Skipped duplicate invoice.finalized for tenant={tenant_id}"
    amount_text = f"{(amount_due or 0) / 100:.2f} {currency or ''}".strip()
    history_entry = _history_entry(
        event_type="invoice.finalized",
        status="info",
        title="Invoice ready",
        description=(
            f"Stripe finalized invoice ({amount_text or 'open balance'}). "
            "Hosted invoice and PDF are available in Billing."
        ),
        source="stripe",
        occurred_at=now,
        plan_code=plan_code,
        amount_minor=amount_due,
        currency=currency,
        invoice_id=invoice_id,
        hosted_invoice_url=str(obj.get("hosted_invoice_url") or "").strip() or None,
        invoice_pdf_url=str(obj.get("invoice_pdf") or "").strip() or None,
        dedupe_key=dedupe_key,
    )
    await _store_subscription(db, tenant, current, history_entry=history_entry)
    return f"Processed invoice.finalized for tenant={tenant_id}"


async def _handle_invoice_payment_failed(db: AsyncSession, obj: dict[str, Any]) -> str:
    tenant = await _find_tenant_for_stripe_event(
        db,
        customer_id=str(obj.get("customer") or "").strip() or None,
        subscription_id=str(obj.get("subscription") or "").strip() or None,
    )
    if tenant is None:
        return "Ignored: tenant not found for invoice.payment_failed"
    tenant_id = str(tenant.id)
    current = _subscription_payload(tenant)
    plan_code = _normalize_plan_code(str(current.get("plan_code") or "starter"))
    now = _now_utc()
    invoice_id = str(obj.get("id") or "").strip() or None
    dedupe_key = f"stripe:{invoice_id or 'unknown'}:invoice.payment_failed"
    history_entry = None if _history_contains(tenant, dedupe_key) else _history_entry(
        event_type="invoice.payment_failed",
        status="warning",
        title="Payment failed",
        description="Stripe could not collect the invoice payment. Update your payment method in Billing.",
        source="stripe",
        occurred_at=now,
        plan_code=plan_code,
        invoice_id=invoice_id,
        hosted_invoice_url=str(obj.get("hosted_invoice_url") or "").strip() or None,
        invoice_pdf_url=str(obj.get("invoice_pdf") or "").strip() or None,
        dedupe_key=dedupe_key,
    )
    updated = {
        **current,
        "provider": "stripe",
        "status": "past_due",
        "plan_code": plan_code,
        "customer_id": str(obj.get("customer") or current.get("customer_id") or "").strip() or None,
        "subscription_id": str(obj.get("subscription") or current.get("subscription_id") or "").strip() or None,
        "updated_at": now.isoformat(),
    }
    await _store_subscription(db, tenant, updated, history_entry=history_entry)
    if history_entry:
        await _send_billing_email(
            updated.get("billing_contact_email"),
            subject="HostFlow billing: payment failed",
            body=(
                "We could not process your latest HostFlow subscription payment.\n\n"
                f"Plan: {plan_code.upper()}\n"
                f"Invoice: {invoice_id or '-'}\n\n"
                "Please open Billing and update your payment method, or use the Stripe customer portal.\n"
            ),
        )
    return f"Processed invoice.payment_failed for tenant={tenant_id}"


async def _stripe_webhook_try_claim_event(db: AsyncSession, event_id: str, event_type: str) -> bool:
    """Atomically reserve this Stripe event_id. Returns True if this worker should process it.

    Uses INSERT … ON CONFLICT DO NOTHING so concurrent deliveries of the same event do not
    double-apply side effects. On handler failure, call `_stripe_webhook_release_claim` so
    Stripe retries can succeed.
    """
    eid = (event_id or "").strip()
    if not eid:
        return True
    stmt = (
        pg_insert(StripeWebhookEventLog)
        .values(
            event_id=eid[:255],
            event_type=(event_type or "")[:128],
        )
        .on_conflict_do_nothing(index_elements=["event_id"])
        .returning(StripeWebhookEventLog.event_id)
    )
    res = await db.execute(stmt)
    row = res.fetchone()
    await db.commit()
    return row is not None


async def _stripe_webhook_release_claim(db: AsyncSession, event_id: str) -> None:
    """Remove claim so a failed handler can be retried by Stripe."""
    eid = (event_id or "").strip()
    if not eid:
        return
    await db.execute(delete(StripeWebhookEventLog).where(StripeWebhookEventLog.event_id == eid[:255]))
    await db.commit()


async def _handle_subscription_event(db: AsyncSession, obj: dict[str, Any], *, deleted: bool) -> str:
    tenant = await _find_tenant_for_stripe_event(
        db,
        customer_id=str(obj.get("customer") or "").strip() or None,
        subscription_id=str(obj.get("id") or "").strip() or None,
    )
    if tenant is None:
        return "Ignored: tenant not found for customer.subscription event"
    tenant_id = str(tenant.id)
    current = _subscription_payload(tenant)
    current_plan_code = str(current.get("plan_code") or "starter")
    current_extra_slots = extract_extra_operating_company_slots(current)
    price_id = _extract_subscription_price_id(obj)
    plan_code = _normalize_plan_code(_plan_code_by_price_id(price_id) or current_plan_code)
    next_extra_slots = _extract_operating_slot_addon_quantity(obj)
    pending_plan_code = _extract_pending_update_plan_code(obj)
    pending_invoice_id, pending_invoice_url = _extract_pending_invoice_details(obj)
    has_pending_update = bool(_extract_pending_update(obj)) and pending_plan_code is not None and pending_plan_code != plan_code
    period_start_iso, period_end_iso = _extract_subscription_period(obj)
    activated_at_iso = _unix_to_iso(obj.get("start_date")) or _unix_to_iso(obj.get("created")) or current.get("activated_at")
    now = _now_utc()
    status_value = "canceled" if deleted else _normalize_stripe_subscription_status(obj.get("status"))
    cancel_at_period_end = bool(obj.get("cancel_at_period_end"))
    dedupe_key = (
        f"stripe:{str(obj.get('id') or '').strip()}:"
        f"{'customer.subscription.deleted' if deleted else 'customer.subscription.updated'}:"
        f"{status_value}:{int(cancel_at_period_end)}:{pending_plan_code or '-'}:"
        f"slots:{next_extra_slots if next_extra_slots is not None else 'na'}"
    )
    history_title = "Subscription updated"
    history_status = "info"
    history_description = f"Plan {plan_code.upper()} remains active."
    if deleted or status_value == "canceled":
        history_title = "Subscription canceled"
        history_status = "warning"
        history_description = "The subscription was canceled in Stripe."
    elif has_pending_update:
        history_title = "Plan change awaiting payment"
        history_status = "warning"
        history_description = f"Your current plan remains {plan_code.upper()} until payment for {pending_plan_code.upper()} is completed."
    elif cancel_at_period_end:
        history_title = "Cancellation scheduled"
        history_status = "warning"
        history_description = "The subscription will end at the close of the current billing period."
    elif plan_code != current_plan_code:
        history_title = "Plan changed"
        history_description = f"Subscription moved from {current_plan_code.upper()} to {plan_code.upper()}."
    elif next_extra_slots is not None and next_extra_slots != current_extra_slots:
        history_title = "Operating company slots updated"
        history_description = f"Add-on operating company slots changed from {current_extra_slots} to {next_extra_slots}."
    history_entry = None if _history_contains(tenant, dedupe_key) else _history_entry(
        event_type="customer.subscription.deleted" if deleted else "customer.subscription.updated",
        status=history_status,
        title=history_title,
        description=history_description,
        source="stripe",
        occurred_at=now,
        plan_code=plan_code,
        dedupe_key=dedupe_key,
    )
    updated = {
        **current,
        "provider": "stripe",
        "status": status_value,
        "plan_code": plan_code,
        "billing_interval": _extract_subscription_billing_interval(obj),
        "pending_plan_code": pending_plan_code if has_pending_update else None,
        "pending_update": has_pending_update,
        "pending_invoice_id": pending_invoice_id if has_pending_update else None,
        "pending_invoice_url": pending_invoice_url if has_pending_update else None,
        "customer_id": str(obj.get("customer") or current.get("customer_id") or "").strip() or None,
        "subscription_id": str(obj.get("id") or current.get("subscription_id") or "").strip() or None,
        "current_period_start": period_start_iso or current.get("current_period_start"),
        "current_period_end": period_end_iso or current.get("current_period_end"),
        "activated_at": activated_at_iso,
        "cancel_at_period_end": cancel_at_period_end,
        "canceled_at": _unix_to_iso(obj.get("canceled_at")) if (deleted or obj.get("canceled_at")) else None,
        "updated_at": now.isoformat(),
    }
    if next_extra_slots is not None:
        updated = _set_extra_operating_slots(updated, next_extra_slots)
    await _store_subscription(db, tenant, updated, history_entry=history_entry)
    if status_value in {"active", "trial"}:
        await _apply_license_limits(db, tenant_id, plan_code)
    if history_entry:
        await _send_billing_email(
            updated.get("billing_contact_email"),
            subject=f"HostFlow subscription update: {history_title.lower()}",
            body=(
                f"{history_title}\n\n"
                f"{history_description}\n"
                f"Plan: {plan_code.upper()}\n"
                f"Status: {status_value}\n"
                f"Current period ends: {updated.get('current_period_end') or '-'}\n\n"
                "You can review the latest status in Billing."
            ),
        )
    return f"Processed customer.subscription event for tenant={tenant_id} status={status_value}"
