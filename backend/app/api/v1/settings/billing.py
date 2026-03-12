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
from backend.app.db.deps import get_db_with_tenant
from backend.app.models.tenant import Tenant, TenantLicense

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
    customer_id: str | None = None
    subscription_id: str | None = None
    checkout_session_id: str | None = None
    current_period_end: datetime | None = None
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


class BillingSummaryOut(BaseModel):
    subscription: BillingSubscriptionOut
    license: platform_schemas.TenantLicenseOut | None = None
    usage: platform_schemas.TenantUsageOut
    available_plans: list[BillingPlanOut]


class BillingChangePlanIn(BaseModel):
    plan_code: str = Field(..., min_length=2, max_length=32)


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


def _plan_price_id(plan_code: str) -> str | None:
    mapping = {
        "starter": (settings.stripe_price_starter or "").strip(),
        "team": (settings.stripe_price_team or "").strip(),
        "pro": (settings.stripe_price_pro or "").strip(),
    }
    return mapping.get(plan_code) or None


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
        customer_id=(str(payload.get("customer_id")).strip() if payload.get("customer_id") else None),
        subscription_id=(str(payload.get("subscription_id")).strip() if payload.get("subscription_id") else None),
        checkout_session_id=(str(payload.get("checkout_session_id")).strip() if payload.get("checkout_session_id") else None),
        current_period_end=_iso_to_dt(payload.get("current_period_end")),
        trial_ends_at=_iso_to_dt(payload.get("trial_ends_at")),
        cancel_at_period_end=bool(payload.get("cancel_at_period_end")),
        canceled_at=_iso_to_dt(payload.get("canceled_at")),
        updated_at=_iso_to_dt(payload.get("updated_at")),
    )


def _available_plans() -> list[BillingPlanOut]:
    price_map = {"starter": 29, "team": 99, "pro": 249}
    return [
        BillingPlanOut(
            code=code,
            name=code.capitalize(),
            monthly_price_usd=int(price_map.get(code, 0)),
            limits=PLAN_LICENSE_LIMITS.get(code, {}),
        )
        for code in PLAN_CODES
    ]


async def _store_subscription(db: AsyncSession, tenant: Tenant, payload: dict[str, Any]) -> BillingSubscriptionOut:
    settings_payload = dict(tenant.settings or {})
    billing_payload = dict(settings_payload.get("billing") or {})
    billing_payload["subscription"] = payload
    settings_payload["billing"] = billing_payload
    tenant.settings = settings_payload
    tenant.updated_at = _now_utc()
    await db.commit()
    await db.refresh(tenant)
    return _subscription_out(tenant)


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
    license_entry = await tenant_service.get_tenant_license(db, tenant_id)
    usage = await tenant_service.get_usage_snapshot(db, tenant_id)
    return BillingSummaryOut(
        subscription=_subscription_out(tenant),
        license=platform_schemas.TenantLicenseOut.model_validate(license_entry) if license_entry else None,
        usage=platform_schemas.TenantUsageOut(**usage),
        available_plans=_available_plans(),
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
            metadata={"tenant_id": tenant_id, "plan_code": plan_code, "requested_by": ctx.sub},
            client_reference_id=tenant_id,
        )
        session_id = str(checkout.get("id") or session_id)
        checkout_url = str(checkout.get("url") or success_url)
        provider: Literal["mock", "stripe"] = "stripe"
    else:
        checkout_url = f"{success_url}&simulated_session_id={session_id}&plan={plan_code}"
        provider = "mock"

    pending_payload = {
        "provider": provider,
        "status": "incomplete",
        "plan_code": plan_code,
        "checkout_session_id": session_id,
        "checkout_requested_at": _now_utc().isoformat(),
        "checkout_cancel_url": cancel_url,
        "checkout_success_url": success_url,
        "updated_at": _now_utc().isoformat(),
    }
    await _store_subscription(db, tenant, pending_payload)

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
            "current_period_end": (now + timedelta(days=30)).isoformat(),
            "cancel_at_period_end": False,
            "canceled_at": None,
            "updated_at": now.isoformat(),
        }
        subscription = await _store_subscription(db, tenant, updated)
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
    return await _store_subscription(db, tenant, updated)


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
    await _store_subscription(
        db,
        tenant,
        {
            **current,
            "provider": "mock" if not _stripe_ready() else str(current.get("provider") or "stripe"),
            "status": "active",
            "plan_code": plan_code,
            "cancel_at_period_end": False,
            "canceled_at": None,
            "current_period_end": (now + timedelta(days=30)).isoformat(),
            "updated_at": now.isoformat(),
        },
    )
    await _apply_license_limits(db, tenant_id, plan_code)
    license_entry = await tenant_service.get_tenant_license(db, tenant_id)
    usage = await tenant_service.get_usage_snapshot(db, tenant_id)
    tenant = await db.get(Tenant, tenant_id)
    return BillingSummaryOut(
        subscription=_subscription_out(tenant),
        license=platform_schemas.TenantLicenseOut.model_validate(license_entry) if license_entry else None,
        usage=platform_schemas.TenantUsageOut(**usage),
        available_plans=_available_plans(),
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
    )
    license_entry = await tenant_service.get_tenant_license(db, tenant_id)
    usage = await tenant_service.get_usage_snapshot(db, tenant_id)
    tenant = await db.get(Tenant, tenant_id)
    return BillingSummaryOut(
        subscription=_subscription_out(tenant),
        license=platform_schemas.TenantLicenseOut.model_validate(license_entry) if license_entry else None,
        usage=platform_schemas.TenantUsageOut(**usage),
        available_plans=_available_plans(),
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
    await _store_subscription(
        db,
        tenant,
        {
            **current,
            "status": "active",
            "cancel_at_period_end": False,
            "canceled_at": None,
            "current_period_end": (now + timedelta(days=30)).isoformat(),
            "updated_at": now.isoformat(),
        },
    )
    await _apply_license_limits(db, tenant_id, plan_code)
    license_entry = await tenant_service.get_tenant_license(db, tenant_id)
    usage = await tenant_service.get_usage_snapshot(db, tenant_id)
    tenant = await db.get(Tenant, tenant_id)
    return BillingSummaryOut(
        subscription=_subscription_out(tenant),
        license=platform_schemas.TenantLicenseOut.model_validate(license_entry) if license_entry else None,
        usage=platform_schemas.TenantUsageOut(**usage),
        available_plans=_available_plans(),
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
        stripe.Webhook.construct_event(  # type: ignore[union-attr]
            payload=payload,
            sig_header=stripe_signature,
            secret=webhook_secret,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid Stripe webhook signature: {exc}") from exc

    # Webhook verification is in place. Event persistence/processing is implemented in the next billing iteration.
    return BillingWebhookOut(accepted=True, detail="Webhook signature verified")
