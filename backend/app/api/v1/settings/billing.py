from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.v1.platform import schemas as platform_schemas
from backend.app.api.v1.tenants import service as tenant_service
from backend.app.auth.deps import Role, UserCtx, get_current_user, require_roles
from backend.app.core.settings import settings
from backend.app.db.deps import get_db, get_db_with_tenant
from backend.app.models.tenant import Tenant, TenantLicense
from backend.app.services.operating_company_slots import get_operating_company_slots
from backend.app.services.system_email import send_system_email

try:  # pragma: no cover - optional dependency
    import stripe
except Exception:  # pragma: no cover - stripe not installed yet
    stripe = None  # type: ignore[assignment]


router = APIRouter(prefix="/billing", tags=["settings-billing"], redirect_slashes=False)

PLAN_CODES: tuple[str, ...] = ("starter", "team", "pro")
CHECKOUT_OUTCOMES: tuple[str, ...] = ("success", "cancel", "error")

PLAN_LICENSE_LIMITS: dict[str, dict[str, int]] = {
    "starter": {
        "max_recruiters": 1,
        "max_supervisors": 1,
        "max_client_managers": 1,
        "max_viewers": 1,
        "max_storage_gb": 5,
        "max_companies": 1,
        "max_candidates_active": 500,
        "max_vacancies_active": 5,
        "max_documents": 1000,
        "max_public_portal_links": 1,
    },
    "team": {
        "max_recruiters": 5,
        "max_supervisors": 2,
        "max_client_managers": 3,
        "max_viewers": 10,
        "max_storage_gb": 20,
        "max_companies": 10,
        "max_candidates_active": 5000,
        "max_vacancies_active": 50,
        "max_documents": 10000,
        "max_public_portal_links": 10,
    },
    "pro": {
        "max_recruiters": 20,
        "max_supervisors": 10,
        "max_client_managers": 15,
        "max_viewers": 50,
        "max_storage_gb": 100,
        "max_companies": 100,
        "max_candidates_active": 50000,
        "max_vacancies_active": 500,
        "max_documents": 100000,
        "max_public_portal_links": 100,
    },
}


class BillingSubscriptionOut(BaseModel):
    provider: Literal["mock", "stripe"] = "mock"
    status: str = "trial"
    plan_code: str = "starter"
    pending_plan_code: str | None = None
    pending_update: bool = False
    pending_invoice_id: str | None = None
    pending_invoice_url: str | None = None
    customer_id: str | None = None
    subscription_id: str | None = None
    checkout_session_id: str | None = None
    current_period_start: datetime | None = None
    current_period_end: datetime | None = None
    activated_at: datetime | None = None
    trial_ends_at: datetime | None = None
    cancel_at_period_end: bool = False
    canceled_at: datetime | None = None
    updated_at: datetime | None = None


class BillingCheckoutCreateIn(BaseModel):
    plan_code: str = Field(..., min_length=2, max_length=32)
    success_url: str | None = Field(default=None, max_length=2000)
    cancel_url: str | None = Field(default=None, max_length=2000)


class BillingCheckoutOut(BaseModel):
    provider: Literal["mock", "stripe"] = "mock"
    mode: Literal["subscription"] = "subscription"
    status: str
    session_id: str
    checkout_url: str


class BillingCheckoutSimulateIn(BaseModel):
    outcome: str = Field(..., min_length=3, max_length=16)


class BillingPortalOut(BaseModel):
    provider: Literal["mock", "stripe"] = "mock"
    url: str


class BillingWebhookOut(BaseModel):
    accepted: bool
    detail: str


class BillingPlanOut(BaseModel):
    code: str
    name: str
    monthly_price_usd: int
    limits: dict[str, int]


class BillingHistoryItemOut(BaseModel):
    id: str
    occurred_at: datetime
    event_type: str
    status: str
    title: str
    description: str | None = None
    source: Literal["app", "stripe"] = "app"
    plan_code: str | None = None
    amount_minor: int | None = None
    currency: str | None = None
    invoice_id: str | None = None
    hosted_invoice_url: str | None = None
    invoice_pdf_url: str | None = None


class BillingInvoiceOut(BaseModel):
    id: str
    number: str | None = None
    status: str
    currency: str | None = None
    total_minor: int | None = None
    amount_paid_minor: int | None = None
    amount_due_minor: int | None = None
    created_at: datetime | None = None
    paid_at: datetime | None = None
    period_start: datetime | None = None
    period_end: datetime | None = None
    hosted_invoice_url: str | None = None
    invoice_pdf_url: str | None = None


class BillingSummaryOut(BaseModel):
    subscription: BillingSubscriptionOut
    license: platform_schemas.TenantLicenseOut | None = None
    usage: platform_schemas.TenantUsageOut
    company_slots: dict[str, int | bool] | None = None
    available_plans: list[BillingPlanOut]
    history: list[BillingHistoryItemOut] = []
    invoices: list[BillingInvoiceOut] = []


async def _company_slots_payload(
    db: AsyncSession,
    *,
    tenant: Tenant,
    license_entry: TenantLicense | None,
) -> dict[str, int | bool]:
    slots = await get_operating_company_slots(
        db,
        str(tenant.id),
        preloaded_tenant=tenant,
        preloaded_license=license_entry,
    )
    return {
        "included_limit": int(slots.included_limit),
        "extra_slots": int(slots.extra_slots),
        "effective_limit": int(slots.effective_limit),
        "used": int(slots.used),
        "available": int(slots.available),
        "unlimited": bool(slots.unlimited),
    }


class BillingChangePlanIn(BaseModel):
    plan_code: str = Field(..., min_length=2, max_length=32)
    success_url: str | None = Field(default=None, max_length=2000)
    cancel_url: str | None = Field(default=None, max_length=2000)


class BillingCancelIn(BaseModel):
    immediate: bool = False


def _now_utc() -> datetime:
    return datetime.now(UTC)


def _iso_to_dt(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            return None
        if raw.endswith("Z"):
            raw = raw[:-1] + "+00:00"
        try:
            return datetime.fromisoformat(raw)
        except ValueError:
            return None
    return None


def _unix_to_iso(value: Any) -> str | None:
    if value is None:
        return None
    try:
        return datetime.fromtimestamp(int(value), tz=UTC).isoformat()
    except Exception:
        return None


def _ensure_tenant_access(ctx: UserCtx, tenant_id: str) -> None:
    if (ctx.role or "").strip().lower() == Role.superadmin.value:
        return
    token_tenant = (ctx.tenant_id or "").strip()
    if token_tenant and token_tenant != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden for tenant")


def _normalize_plan_code(raw: str) -> str:
    plan = (raw or "").strip().lower()
    if plan not in PLAN_CODES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unsupported plan_code: {plan or raw}",
        )
    return plan


def _billing_root(tenant: Tenant) -> dict[str, Any]:
    settings_payload = tenant.settings if isinstance(tenant.settings, dict) else {}
    billing = settings_payload.get("billing") if isinstance(settings_payload.get("billing"), dict) else {}
    return dict(billing)


def _subscription_payload(tenant: Tenant) -> dict[str, Any]:
    billing = _billing_root(tenant)
    subscription = billing.get("subscription")
    if isinstance(subscription, dict):
        return dict(subscription)
    return {}


def _billing_history(tenant: Tenant) -> list[dict[str, Any]]:
    billing = _billing_root(tenant)
    history = billing.get("history")
    if isinstance(history, list):
        return [dict(item) for item in history if isinstance(item, dict)]
    return []


def _history_contains(tenant: Tenant, dedupe_key: str | None) -> bool:
    key = (dedupe_key or "").strip()
    if not key:
        return False
    return any(str(item.get("dedupe_key") or "").strip() == key for item in _billing_history(tenant))


def _plan_price_id(plan_code: str) -> str | None:
    mapping = {
        "starter": (settings.stripe_price_starter or "").strip(),
        "team": (settings.stripe_price_team or "").strip(),
        "pro": (settings.stripe_price_pro or "").strip(),
    }
    return mapping.get(plan_code) or None


def _plan_code_by_price_id(price_id: str | None) -> str | None:
    pid = (price_id or "").strip()
    if not pid:
        return None
    for code in PLAN_CODES:
        configured = _plan_price_id(code)
        if configured and configured == pid:
            return code
    return None


def _stripe_price_amount(price_id: str | None) -> tuple[int | None, str | None]:
    pid = (price_id or "").strip()
    if not (_stripe_ready() and pid):
        return None, None
    stripe.api_key = settings.stripe_secret_key
    try:
        price = _stripe_obj_to_dict(stripe.Price.retrieve(pid))  # type: ignore[union-attr]
    except Exception:
        return None, None
    amount = int(price.get("unit_amount")) if price.get("unit_amount") is not None else None
    currency = str(price.get("currency") or "").strip().upper() or None
    return amount, currency


def _calculate_proration_amount_minor(
    *,
    current_amount_minor: int,
    target_amount_minor: int,
    period_start: datetime | None,
    period_end: datetime | None,
    now: datetime,
) -> int:
    diff = max(0, target_amount_minor - current_amount_minor)
    if diff <= 0:
        return 0
    if period_start is None or period_end is None:
        return diff
    total_seconds = max((period_end - period_start).total_seconds(), 0)
    remaining_seconds = max((period_end - now).total_seconds(), 0)
    if total_seconds <= 0:
        return diff
    prorated = diff * (remaining_seconds / total_seconds)
    return max(1, int(round(prorated)))


def _stripe_ready() -> bool:
    return bool((settings.stripe_secret_key or "").strip()) and stripe is not None


def _subscription_out(tenant: Tenant) -> BillingSubscriptionOut:
    payload = _subscription_payload(tenant)
    provider = "stripe" if str(payload.get("provider") or "").strip().lower() == "stripe" else "mock"
    plan_code = str(payload.get("plan_code") or "starter").strip().lower()
    if plan_code not in PLAN_CODES:
        plan_code = "starter"
    return BillingSubscriptionOut(
        provider=provider,
        status=str(payload.get("status") or "trial"),
        plan_code=plan_code,
        pending_plan_code=(str(payload.get("pending_plan_code")).strip().lower() if payload.get("pending_plan_code") else None),
        pending_update=bool(payload.get("pending_update")),
        pending_invoice_id=(str(payload.get("pending_invoice_id")).strip() if payload.get("pending_invoice_id") else None),
        pending_invoice_url=(str(payload.get("pending_invoice_url")).strip() if payload.get("pending_invoice_url") else None),
        customer_id=(str(payload.get("customer_id")).strip() if payload.get("customer_id") else None),
        subscription_id=(str(payload.get("subscription_id")).strip() if payload.get("subscription_id") else None),
        checkout_session_id=(str(payload.get("checkout_session_id")).strip() if payload.get("checkout_session_id") else None),
        current_period_start=_iso_to_dt(payload.get("current_period_start")),
        current_period_end=_iso_to_dt(payload.get("current_period_end")),
        activated_at=_iso_to_dt(payload.get("activated_at")),
        trial_ends_at=_iso_to_dt(payload.get("trial_ends_at")),
        cancel_at_period_end=bool(payload.get("cancel_at_period_end")),
        canceled_at=_iso_to_dt(payload.get("canceled_at")),
        updated_at=_iso_to_dt(payload.get("updated_at")),
    )


def _available_plans() -> list[BillingPlanOut]:
    # Legacy field name kept for API compatibility; values now mirror live Stripe EUR pricing.
    price_map = {"starter": 39, "team": 99, "pro": 199}
    return [
        BillingPlanOut(
            code=code,
            name=code.capitalize(),
            monthly_price_usd=int(price_map.get(code, 0)),
            limits=PLAN_LICENSE_LIMITS.get(code, {}),
        )
        for code in PLAN_CODES
    ]


async def _store_subscription(
    db: AsyncSession,
    tenant: Tenant,
    payload: dict[str, Any],
    *,
    history_entry: dict[str, Any] | None = None,
) -> BillingSubscriptionOut:
    settings_payload = dict(tenant.settings or {})
    billing_payload = dict(settings_payload.get("billing") or {})
    billing_payload["subscription"] = payload
    history = billing_payload.get("history")
    history_list = [dict(item) for item in history] if isinstance(history, list) else []
    if history_entry:
        dedupe_key = str(history_entry.get("dedupe_key") or "").strip()
        if not dedupe_key or not any(str(item.get("dedupe_key") or "").strip() == dedupe_key for item in history_list):
            history_list.insert(0, history_entry)
            billing_payload["history"] = history_list[:40]
    settings_payload["billing"] = billing_payload
    tenant.settings = settings_payload
    tenant.updated_at = _now_utc()
    await db.commit()
    await db.refresh(tenant)
    return _subscription_out(tenant)


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


def _stripe_obj_to_dict(obj: Any) -> dict[str, Any]:
    if isinstance(obj, dict):
        return obj
    if hasattr(obj, "to_dict_recursive"):
        maybe = obj.to_dict_recursive()
        if isinstance(maybe, dict):
            return maybe
    if hasattr(obj, "to_dict"):
        maybe = obj.to_dict()
        if isinstance(maybe, dict):
            return maybe
    return {}


def _list_stripe_invoices(subscription: dict[str, Any]) -> list[BillingInvoiceOut]:
    customer_id = str(subscription.get("customer_id") or "").strip()
    if not (_stripe_ready() and customer_id):
        return []
    stripe.api_key = settings.stripe_secret_key
    try:
        result = stripe.Invoice.list(customer=customer_id, limit=12)  # type: ignore[union-attr]
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


async def _apply_license_limits(db: AsyncSession, tenant_id: str, plan_code: str) -> None:
    limits = PLAN_LICENSE_LIMITS.get(plan_code)
    if not limits:
        return
    license_row = (
        await db.execute(select(TenantLicense).where(TenantLicense.tenant_id == tenant_id).limit(1))
    ).scalar_one_or_none()
    if license_row is None:
        license_row = TenantLicense(tenant_id=tenant_id, plan=plan_code, auto_renew=True, notes="billing-managed")
        db.add(license_row)
    license_row.plan = plan_code
    license_row.auto_renew = True
    license_row.expires_at = (_now_utc() + timedelta(days=30)).date()
    for field, value in limits.items():
        setattr(license_row, field, int(value))
    await db.commit()


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


async def _handle_checkout_completed(db: AsyncSession, obj: dict[str, Any]) -> str:
    metadata = obj.get("metadata") if isinstance(obj.get("metadata"), dict) else {}
    billing_action = str(metadata.get("billing_action") or "new_subscription").strip().lower()
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
        stripe.api_key = settings.stripe_secret_key
        sub = _stripe_obj_to_dict(stripe.Subscription.retrieve(subscription_id))  # type: ignore[union-attr]
        items = sub.get("items", {}).get("data", []) if isinstance(sub, dict) else []
        first_item = _stripe_obj_to_dict(items[0]) if isinstance(items, list) and items else {}
        item_id = str(first_item.get("id") or "").strip()
        target_price_id = _plan_price_id(target_plan_code)
        if not item_id or not target_price_id:
            return f"Ignored: missing subscription item/price for tenant={tenant_id} plan_change checkout"
        updated_sub = _stripe_obj_to_dict(stripe.Subscription.modify(  # type: ignore[union-attr]
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
                invoice_obj = _stripe_obj_to_dict(stripe.Invoice.retrieve(invoice_id))  # type: ignore[union-attr]
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
    price_id = _extract_subscription_price_id(obj)
    plan_code = _normalize_plan_code(_plan_code_by_price_id(price_id) or current_plan_code)
    pending_plan_code = _extract_pending_update_plan_code(obj)
    pending_invoice_id, pending_invoice_url = _extract_pending_invoice_details(obj)
    has_pending_update = bool(_extract_pending_update(obj)) and pending_plan_code is not None and pending_plan_code != plan_code
    period_start_iso, period_end_iso = _extract_subscription_period(obj)
    activated_at_iso = _unix_to_iso(obj.get("start_date")) or _unix_to_iso(obj.get("created")) or current.get("activated_at")
    now = _now_utc()
    status_value = "canceled" if deleted else _normalize_stripe_subscription_status(obj.get("status"))
    cancel_at_period_end = bool(obj.get("cancel_at_period_end"))
    dedupe_key = f"stripe:{str(obj.get('id') or '').strip()}:{'customer.subscription.deleted' if deleted else 'customer.subscription.updated'}:{status_value}:{int(cancel_at_period_end)}:{pending_plan_code or '-'}"
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


@router.get(
    "/subscription",
    response_model=BillingSubscriptionOut,
    dependencies=[Depends(require_roles(Role.administrator, Role.supervisor))],
)
async def get_billing_subscription(
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> BillingSubscriptionOut:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    _ensure_tenant_access(ctx, tenant_id)
    tenant = await db.get(Tenant, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return _subscription_out(tenant)


@router.get(
    "/summary",
    response_model=BillingSummaryOut,
    dependencies=[Depends(require_roles(Role.administrator, Role.supervisor))],
)
async def get_billing_summary(
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> BillingSummaryOut:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    _ensure_tenant_access(ctx, tenant_id)
    tenant = await db.get(Tenant, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    raw_subscription = _subscription_payload(tenant)
    provider = str(raw_subscription.get("provider") or "").strip().lower()
    subscription_id = str(raw_subscription.get("subscription_id") or "").strip()
    if _stripe_ready() and provider == "stripe" and subscription_id:
        stripe.api_key = settings.stripe_secret_key
        try:
            live_sub = _stripe_obj_to_dict(stripe.Subscription.retrieve(  # type: ignore[union-attr]
                subscription_id,
                expand=["latest_invoice", "latest_invoice.payment_intent"],
            ))
            if live_sub:
                await _handle_subscription_event(db, live_sub, deleted=False)
                tenant = await db.get(Tenant, tenant_id)
                if tenant is None:
                    raise HTTPException(status_code=404, detail="Tenant not found")
        except Exception:
            pass
    license_entry = await tenant_service.get_tenant_license(db, tenant_id)
    usage = await tenant_service.get_usage_snapshot(db, tenant_id)
    subscription = _subscription_out(tenant)
    invoices = _list_stripe_invoices(_subscription_payload(tenant))
    history = _merge_history_with_invoices(_history_out(tenant), invoices)
    company_slots = await _company_slots_payload(db, tenant=tenant, license_entry=license_entry)
    return BillingSummaryOut(
        subscription=subscription,
        license=platform_schemas.TenantLicenseOut.model_validate(license_entry) if license_entry else None,
        usage=platform_schemas.TenantUsageOut(**usage),
        company_slots=company_slots,
        available_plans=_available_plans(),
        history=history,
        invoices=invoices,
    )


@router.post(
    "/checkout-session",
    response_model=BillingCheckoutOut,
    dependencies=[Depends(require_roles(Role.administrator))],
)
async def create_checkout_session(
    payload: BillingCheckoutCreateIn,
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> BillingCheckoutOut:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    _ensure_tenant_access(ctx, tenant_id)
    tenant = await db.get(Tenant, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")

    plan_code = _normalize_plan_code(payload.plan_code)
    success_url = (payload.success_url or "").strip() or "/app/settings/billing?checkout=success"
    cancel_url = (payload.cancel_url or "").strip() or "/app/settings/billing?checkout=cancel"
    session_id = f"cs_{uuid4().hex}"

    if _stripe_ready():
        price_id = _plan_price_id(plan_code)
        if not price_id:
            raise HTTPException(status_code=400, detail=f"Stripe price ID for '{plan_code}' is not configured")
        stripe.api_key = settings.stripe_secret_key
        checkout = stripe.checkout.Session.create(  # type: ignore[union-attr]
            mode="subscription",
            line_items=[{"price": price_id, "quantity": 1}],
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={
                "tenant_id": tenant_id,
                "plan_code": plan_code,
                "requested_by": ctx.sub,
                "billing_action": "new_subscription",
            },
            client_reference_id=tenant_id,
        )
        session_id = str(checkout.get("id") or session_id)
        checkout_url = str(checkout.get("url") or success_url)
        provider: Literal["mock", "stripe"] = "stripe"
    else:
        checkout_url = f"{success_url}&simulated_session_id={session_id}&plan={plan_code}"
        provider = "mock"

    pending_payload = {
        **current,
        "provider": provider,
        "status": "incomplete",
        "plan_code": plan_code,
        "checkout_session_id": session_id,
        "billing_contact_email": (ctx.email or "").strip() or current.get("billing_contact_email"),
        "checkout_requested_at": _now_utc().isoformat(),
        "checkout_cancel_url": cancel_url,
        "checkout_success_url": success_url,
        "updated_at": _now_utc().isoformat(),
    }
    await _store_subscription(
        db,
        tenant,
        pending_payload,
        history_entry=_history_entry(
            event_type="checkout.session.started",
            status="info",
            title="Checkout started",
            description=f"Started Stripe checkout for the {plan_code.upper()} plan.",
            source="app",
            plan_code=plan_code,
            dedupe_key=f"app:{session_id}:checkout-started",
        ),
    )

    return BillingCheckoutOut(
        provider=provider,
        mode="subscription",
        status="incomplete",
        session_id=session_id,
        checkout_url=checkout_url,
    )


@router.post(
    "/checkout-session/{session_id}/simulate",
    response_model=BillingSubscriptionOut,
    dependencies=[Depends(require_roles(Role.administrator))],
)
async def simulate_checkout_resolution(
    session_id: str,
    payload: BillingCheckoutSimulateIn,
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> BillingSubscriptionOut:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    _ensure_tenant_access(ctx, tenant_id)
    tenant = await db.get(Tenant, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    outcome = (payload.outcome or "").strip().lower()
    if outcome not in CHECKOUT_OUTCOMES:
        raise HTTPException(status_code=422, detail=f"Unsupported outcome: {payload.outcome}")

    current = _subscription_payload(tenant)
    current_session_id = str(current.get("checkout_session_id") or "").strip()
    if current_session_id and current_session_id != session_id:
        raise HTTPException(status_code=409, detail="Checkout session mismatch")

    plan_code = _normalize_plan_code(str(current.get("plan_code") or "starter"))
    now = _now_utc()
    if outcome == "success":
        updated = {
            **current,
            "provider": "mock" if not _stripe_ready() else str(current.get("provider") or "stripe"),
            "status": "active",
            "plan_code": plan_code,
            "checkout_session_id": session_id,
            "current_period_start": now.isoformat(),
            "current_period_end": (now + timedelta(days=30)).isoformat(),
            "activated_at": str(current.get("activated_at") or "").strip() or now.isoformat(),
            "cancel_at_period_end": False,
            "canceled_at": None,
            "updated_at": now.isoformat(),
        }
        subscription = await _store_subscription(
            db,
            tenant,
            updated,
            history_entry=_history_entry(
                event_type="checkout.session.simulated",
                status="success",
                title="Simulated payment success",
                description=f"Mock checkout activated the {plan_code.upper()} plan.",
                source="app",
                plan_code=plan_code,
                dedupe_key=f"app:{session_id}:simulate-success",
            ),
        )
        await _apply_license_limits(db, tenant_id, plan_code)
        return subscription

    status_value = "canceled" if outcome == "cancel" else "past_due"
    updated = {
        **current,
        "status": status_value,
        "cancel_at_period_end": outcome == "cancel",
        "canceled_at": now.isoformat() if outcome == "cancel" else current.get("canceled_at"),
        "checkout_session_id": session_id,
        "updated_at": now.isoformat(),
    }
    return await _store_subscription(
        db,
        tenant,
        updated,
        history_entry=_history_entry(
            event_type="checkout.session.simulated",
            status="warning" if outcome == "cancel" else "error",
            title="Simulated checkout canceled" if outcome == "cancel" else "Simulated payment error",
            description="Mock billing state updated from simulation controls.",
            source="app",
            plan_code=plan_code,
            dedupe_key=f"app:{session_id}:simulate-{outcome}",
        ),
    )


@router.post(
    "/change-plan",
    response_model=BillingSummaryOut,
    dependencies=[Depends(require_roles(Role.administrator))],
)
async def change_plan(
    payload: BillingChangePlanIn,
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> BillingSummaryOut:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    _ensure_tenant_access(ctx, tenant_id)
    tenant = await db.get(Tenant, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    plan_code = _normalize_plan_code(payload.plan_code)
    current = _subscription_payload(tenant)
    now = _now_utc()
    provider = str(current.get("provider") or "").strip().lower()
    subscription_id = str(current.get("subscription_id") or "").strip()
    customer_id = str(current.get("customer_id") or "").strip()
    if _stripe_ready() and provider == "stripe" and subscription_id and customer_id:
        stripe.api_key = settings.stripe_secret_key
        sub = _stripe_obj_to_dict(stripe.Subscription.retrieve(subscription_id, expand=["latest_invoice"]))  # type: ignore[union-attr]
        current_plan_code = _normalize_plan_code(str(current.get("plan_code") or "starter"))
        if plan_code == current_plan_code:
            license_entry = await tenant_service.get_tenant_license(db, tenant_id)
            usage = await tenant_service.get_usage_snapshot(db, tenant_id)
            company_slots = await _company_slots_payload(db, tenant=tenant, license_entry=license_entry)
            return BillingSummaryOut(
                subscription=_subscription_out(tenant),
                license=platform_schemas.TenantLicenseOut.model_validate(license_entry) if license_entry else None,
                usage=platform_schemas.TenantUsageOut(**usage),
                company_slots=company_slots,
                available_plans=_available_plans(),
                history=_history_out(tenant),
                invoices=_list_stripe_invoices(_subscription_payload(tenant)),
            )
        items = sub.get("items", {}).get("data", []) if isinstance(sub, dict) else []
        first_item = _stripe_obj_to_dict(items[0]) if isinstance(items, list) and items else {}
        if not first_item:
            raise HTTPException(status_code=409, detail="Stripe subscription items are unavailable")
        item_id = str(first_item.get("id") or "").strip()
        if not item_id:
            raise HTTPException(status_code=409, detail="Stripe subscription item is unavailable")
        price_id = _plan_price_id(plan_code)
        if not price_id:
            raise HTTPException(status_code=400, detail=f"Stripe price ID for '{plan_code}' is not configured")
        current_price_id = _extract_subscription_price_id(sub)
        current_amount_minor, currency = _stripe_price_amount(current_price_id)
        target_amount_minor, target_currency = _stripe_price_amount(price_id)
        if current_amount_minor is None or target_amount_minor is None:
            raise HTTPException(status_code=409, detail="Stripe price amounts are unavailable")
        if target_amount_minor > current_amount_minor:
            pending_update = _extract_pending_update(sub)
            latest_invoice_dict = _stripe_obj_to_dict(sub.get("latest_invoice"))
            stale_invoice_id = str(
                pending_update.get("invoice")
                or latest_invoice_dict.get("id")
                or ""
            ).strip() or None
            stale_invoice_status = str(latest_invoice_dict.get("status") or "").strip().lower()
            if stale_invoice_id and stale_invoice_status in {"draft", "open", "uncollectible"}:
                try:
                    stripe.Invoice.void_invoice(stale_invoice_id)  # type: ignore[union-attr]
                except Exception:
                    pass
            current_period_start = _iso_to_dt(_unix_to_iso(sub.get("current_period_start"))) or _iso_to_dt(current.get("current_period_start"))
            current_period_end = _iso_to_dt(_unix_to_iso(sub.get("current_period_end"))) or _iso_to_dt(current.get("current_period_end"))
            amount_minor = _calculate_proration_amount_minor(
                current_amount_minor=current_amount_minor,
                target_amount_minor=target_amount_minor,
                period_start=current_period_start,
                period_end=current_period_end,
                now=now,
            )
            success_url = (payload.success_url or "").strip() or "/app/settings/billing?checkout=success"
            cancel_url = (payload.cancel_url or "").strip() or "/app/settings/billing?checkout=cancel"
            checkout = stripe.checkout.Session.create(  # type: ignore[union-attr]
                mode="payment",
                customer=customer_id,
                success_url=success_url,
                cancel_url=cancel_url,
                line_items=[{
                    "price_data": {
                        "currency": (target_currency or currency or "EUR").lower(),
                        "unit_amount": amount_minor,
                        "product_data": {
                            "name": f"HostFlow upgrade to {plan_code.upper()}",
                            "description": f"Upgrade from {current_plan_code.upper()} to {plan_code.upper()} for the current billing period.",
                        },
                    },
                    "quantity": 1,
                }],
                invoice_creation={"enabled": True},
                metadata={
                    "tenant_id": tenant_id,
                    "billing_action": "plan_change",
                    "target_plan_code": plan_code,
                    "current_plan_code": current_plan_code,
                    "subscription_id": subscription_id,
                    "customer_id": customer_id,
                    "requested_by": ctx.sub,
                },
                client_reference_id=tenant_id,
            )
            checkout_url = str(checkout.get("url") or "").strip() or None
            response_subscription = _subscription_out(tenant).model_dump()
            response_subscription.update(
                {
                    "pending_plan_code": plan_code,
                    "pending_update": True,
                    "pending_invoice_id": None,
                    "pending_invoice_url": checkout_url,
                    "checkout_session_id": str(checkout.get("id") or "").strip() or response_subscription.get("checkout_session_id"),
                }
            )
            license_entry = await tenant_service.get_tenant_license(db, tenant_id)
            usage = await tenant_service.get_usage_snapshot(db, tenant_id)
            company_slots = await _company_slots_payload(db, tenant=tenant, license_entry=license_entry)
            return BillingSummaryOut(
                subscription=BillingSubscriptionOut(**response_subscription),
                license=platform_schemas.TenantLicenseOut.model_validate(license_entry) if license_entry else None,
                usage=platform_schemas.TenantUsageOut(**usage),
                company_slots=company_slots,
                available_plans=_available_plans(),
                history=_merge_history_with_invoices(_history_out(tenant), _list_stripe_invoices(_subscription_payload(tenant))),
                invoices=_list_stripe_invoices(_subscription_payload(tenant)),
            )
        else:
            updated_stripe = _stripe_obj_to_dict(stripe.Subscription.modify(  # type: ignore[union-attr]
                subscription_id,
                items=[{"id": item_id, "price": price_id}],
                proration_behavior="none",
            ))
            await _handle_subscription_event(db, updated_stripe, deleted=False)
    else:
        await _store_subscription(
            db,
            tenant,
            {
                **current,
                "provider": "mock" if not _stripe_ready() else str(current.get("provider") or "stripe"),
                "status": "active",
                "plan_code": plan_code,
                "billing_contact_email": (ctx.email or "").strip() or current.get("billing_contact_email"),
                "cancel_at_period_end": False,
                "canceled_at": None,
                "current_period_start": now.isoformat(),
                "current_period_end": (now + timedelta(days=30)).isoformat(),
                "activated_at": str(current.get("activated_at") or "").strip() or now.isoformat(),
                "updated_at": now.isoformat(),
            },
            history_entry=_history_entry(
                event_type="subscription.plan_changed",
                status="success",
                title="Plan changed",
                description=f"Subscription switched to {plan_code.upper()}.",
                source="app",
                plan_code=plan_code,
                dedupe_key=f"app:{tenant_id}:plan-change:{plan_code}:{now.isoformat()}",
            ),
        )
    tenant = await db.get(Tenant, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    effective_subscription = _subscription_out(tenant)
    if effective_subscription.status in {"active", "trial"}:
        await _apply_license_limits(db, tenant_id, effective_subscription.plan_code)
        tenant = await db.get(Tenant, tenant_id)
        if tenant is None:
            raise HTTPException(status_code=404, detail="Tenant not found")
        effective_subscription = _subscription_out(tenant)
    license_entry = await tenant_service.get_tenant_license(db, tenant_id)
    usage = await tenant_service.get_usage_snapshot(db, tenant_id)
    company_slots = await _company_slots_payload(db, tenant=tenant, license_entry=license_entry)
    return BillingSummaryOut(
        subscription=effective_subscription,
        license=platform_schemas.TenantLicenseOut.model_validate(license_entry) if license_entry else None,
        usage=platform_schemas.TenantUsageOut(**usage),
        company_slots=company_slots,
        available_plans=_available_plans(),
        history=_history_out(tenant),
        invoices=_list_stripe_invoices(_subscription_payload(tenant)),
    )


@router.post(
    "/cancel",
    response_model=BillingSummaryOut,
    dependencies=[Depends(require_roles(Role.administrator))],
)
async def cancel_subscription(
    payload: BillingCancelIn,
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> BillingSummaryOut:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    _ensure_tenant_access(ctx, tenant_id)
    tenant = await db.get(Tenant, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    current = _subscription_payload(tenant)
    now = _now_utc()
    current_period_end = _iso_to_dt(current.get("current_period_end")) or (now + timedelta(days=30))
    provider = str(current.get("provider") or "").strip().lower()
    subscription_id = str(current.get("subscription_id") or "").strip()
    if _stripe_ready() and provider == "stripe" and subscription_id:
        stripe.api_key = settings.stripe_secret_key
        if payload.immediate:
            stripe.Subscription.cancel(subscription_id)  # type: ignore[union-attr]
            updated_stripe = stripe.Subscription.retrieve(subscription_id)  # type: ignore[union-attr]
            await _handle_subscription_event(db, updated_stripe if isinstance(updated_stripe, dict) else updated_stripe.to_dict(), deleted=True)
        else:
            updated_stripe = stripe.Subscription.modify(subscription_id, cancel_at_period_end=True)  # type: ignore[union-attr]
            await _handle_subscription_event(db, updated_stripe if isinstance(updated_stripe, dict) else updated_stripe.to_dict(), deleted=False)
    else:
        status_value = "canceled" if payload.immediate else "active"
        await _store_subscription(
            db,
            tenant,
            {
                **current,
                "status": status_value,
                "cancel_at_period_end": True,
                "canceled_at": now.isoformat(),
                "current_period_end": current_period_end.isoformat(),
                "updated_at": now.isoformat(),
            },
            history_entry=_history_entry(
                event_type="subscription.canceled",
                status="warning",
                title="Cancellation scheduled" if not payload.immediate else "Subscription canceled",
                description="Subscription will remain active until the period end." if not payload.immediate else "Subscription access was ended immediately.",
                source="app",
                plan_code=str(current.get("plan_code") or "starter"),
                dedupe_key=f"app:{tenant_id}:cancel:{int(payload.immediate)}:{now.isoformat()}",
            ),
        )
    license_entry = await tenant_service.get_tenant_license(db, tenant_id)
    usage = await tenant_service.get_usage_snapshot(db, tenant_id)
    tenant = await db.get(Tenant, tenant_id)
    company_slots = await _company_slots_payload(db, tenant=tenant, license_entry=license_entry)
    return BillingSummaryOut(
        subscription=_subscription_out(tenant),
        license=platform_schemas.TenantLicenseOut.model_validate(license_entry) if license_entry else None,
        usage=platform_schemas.TenantUsageOut(**usage),
        company_slots=company_slots,
        available_plans=_available_plans(),
        history=_history_out(tenant),
        invoices=_list_stripe_invoices(_subscription_payload(tenant)),
    )


@router.post(
    "/reactivate",
    response_model=BillingSummaryOut,
    dependencies=[Depends(require_roles(Role.administrator))],
)
async def reactivate_subscription(
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> BillingSummaryOut:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    _ensure_tenant_access(ctx, tenant_id)
    tenant = await db.get(Tenant, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    current = _subscription_payload(tenant)
    now = _now_utc()
    plan_code = _normalize_plan_code(str(current.get("plan_code") or "starter"))
    provider = str(current.get("provider") or "").strip().lower()
    subscription_id = str(current.get("subscription_id") or "").strip()
    if _stripe_ready() and provider == "stripe" and subscription_id:
        stripe.api_key = settings.stripe_secret_key
        updated_stripe = stripe.Subscription.modify(subscription_id, cancel_at_period_end=False)  # type: ignore[union-attr]
        await _handle_subscription_event(db, updated_stripe if isinstance(updated_stripe, dict) else updated_stripe.to_dict(), deleted=False)
    else:
        await _store_subscription(
            db,
            tenant,
            {
                **current,
                "status": "active",
                "cancel_at_period_end": False,
                "canceled_at": None,
                "current_period_start": current.get("current_period_start") or now.isoformat(),
                "current_period_end": (now + timedelta(days=30)).isoformat(),
                "updated_at": now.isoformat(),
            },
            history_entry=_history_entry(
                event_type="subscription.reactivated",
                status="success",
                title="Subscription resumed",
                description="Auto-renew has been restored.",
                source="app",
                plan_code=plan_code,
                dedupe_key=f"app:{tenant_id}:reactivate:{now.isoformat()}",
            ),
        )
    await _apply_license_limits(db, tenant_id, plan_code)
    license_entry = await tenant_service.get_tenant_license(db, tenant_id)
    usage = await tenant_service.get_usage_snapshot(db, tenant_id)
    tenant = await db.get(Tenant, tenant_id)
    company_slots = await _company_slots_payload(db, tenant=tenant, license_entry=license_entry)
    return BillingSummaryOut(
        subscription=_subscription_out(tenant),
        license=platform_schemas.TenantLicenseOut.model_validate(license_entry) if license_entry else None,
        usage=platform_schemas.TenantUsageOut(**usage),
        company_slots=company_slots,
        available_plans=_available_plans(),
        history=_history_out(tenant),
        invoices=_list_stripe_invoices(_subscription_payload(tenant)),
    )


@router.post(
    "/portal",
    response_model=BillingPortalOut,
    dependencies=[Depends(require_roles(Role.administrator))],
)
async def create_customer_portal_link(
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> BillingPortalOut:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    _ensure_tenant_access(ctx, tenant_id)
    tenant = await db.get(Tenant, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")

    subscription = _subscription_payload(tenant)
    customer_id = str(subscription.get("customer_id") or "").strip()
    return_url = (settings.stripe_portal_return_url or "").strip() or "/app/settings/billing"
    if _stripe_ready() and customer_id:
        stripe.api_key = settings.stripe_secret_key
        session = stripe.billing_portal.Session.create(  # type: ignore[union-attr]
            customer=customer_id,
            return_url=return_url,
        )
        return BillingPortalOut(provider="stripe", url=str(session.get("url") or return_url))
    return BillingPortalOut(provider="mock", url=return_url)


@router.post("/webhook", response_model=BillingWebhookOut, include_in_schema=True)
async def stripe_webhook(
    request: Request,
    stripe_signature: str | None = Header(default=None, alias="Stripe-Signature"),
    db: AsyncSession = Depends(get_db),
) -> BillingWebhookOut:
    webhook_secret = (settings.stripe_webhook_secret or "").strip()
    payload = await request.body()

    if not _stripe_ready() or not webhook_secret:
        return BillingWebhookOut(accepted=False, detail="Stripe webhook is not configured")
    if stripe is None:
        return BillingWebhookOut(accepted=False, detail="Stripe SDK is not installed")
    if not stripe_signature:
        raise HTTPException(status_code=400, detail="Missing Stripe-Signature header")

    try:
        event = stripe.Webhook.construct_event(  # type: ignore[union-attr]
            payload=payload,
            sig_header=stripe_signature,
            secret=webhook_secret,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid Stripe webhook signature: {exc}") from exc

    event_type = str(getattr(event, "type", "") or "")
    data = getattr(event, "data", None)
    obj = {}
    if isinstance(data, dict):
        obj = data.get("object") if isinstance(data.get("object"), dict) else {}
    else:
        obj = getattr(data, "object", None)
        if obj is None and hasattr(event, "to_dict"):
            event_dict = event.to_dict()  # type: ignore[union-attr]
            obj = (event_dict.get("data") or {}).get("object") if isinstance(event_dict, dict) else None
        if not isinstance(obj, dict):
            obj = {}

    if event_type == "checkout.session.completed":
        detail = await _handle_checkout_completed(db, obj)
    elif event_type == "invoice.paid":
        detail = await _handle_invoice_paid(db, obj)
    elif event_type == "customer.subscription.updated":
        detail = await _handle_subscription_event(db, obj, deleted=False)
    elif event_type == "customer.subscription.deleted":
        detail = await _handle_subscription_event(db, obj, deleted=True)
    else:
        detail = f"Ignored: unsupported event type {event_type or '<empty>'}"

    return BillingWebhookOut(accepted=True, detail=detail)
