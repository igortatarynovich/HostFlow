"""HTTP route handlers for the billing API.

Extracted from ``backend/app/api/v1/settings/billing/__init__.py`` as part of
the Phase 1 god-module split (step 7/N).

All 12 endpoints registered against the shared ``router`` (defined in the
parent package ``__init__``):

* ``GET  /subscription``                            ``get_billing_subscription``
* ``GET  /quota-headroom``                          ``get_billing_quota_headroom``
* ``GET  /summary``                                 ``get_billing_summary``
* ``POST /checkout-session``                        ``create_checkout_session``
* ``POST /portal-candidates-pack/checkout``         ``create_portal_candidates_pack_checkout``
* ``POST /addon-pack/checkout``                     ``create_addon_pack_checkout``
* ``POST /checkout-session/{id}/simulate``          ``simulate_checkout_resolution``
* ``POST /change-plan``                             ``change_plan``
* ``POST /company-slots``                           ``update_company_slots``
* ``POST /cancel``                                  ``cancel_subscription``
* ``POST /reactivate``                              ``reactivate_subscription``
* ``POST /portal``                                  ``create_customer_portal_link``
* ``POST /webhook``                                 ``stripe_webhook``

Stripe SDK calls go through ``_get_stripe()`` so test-time patches of
``billing.stripe`` propagate to handler bodies without holding a stale
reference.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Literal
from uuid import UUID, uuid4

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.v1.platform import schemas as platform_schemas
from backend.app.api.v1.tenants import service as tenant_service
from backend.app.auth.trust_role_deps import require_trust_admin, require_trust_read, require_trust_write
from backend.app.auth.deps import Role, UserCtx, get_current_user
from backend.app.constants.spa_paths import (
    SETTINGS_BILLING,
    SETTINGS_BILLING_CHECKOUT_CANCEL,
    SETTINGS_BILLING_CHECKOUT_SUCCESS,
)
from backend.app.core.settings import settings
from backend.app.db.deps import get_db, get_db_with_tenant
from backend.app.models.tenant import Tenant
from backend.app.services import portal_candidate_usage
from backend.app.services.operating_company_slots import extract_extra_operating_company_slots
from backend.app.services.stripe_price_catalog import sku_pack_increment, sku_price_from_settings

from . import router
from ._helpers.history import _history_entry, _history_out, _merge_history_with_invoices
from ._helpers.license_sync import _apply_license_limits, sync_subscription_license_addon_v1
from ._helpers.packs import _apply_addon_pack_by_sku, _apply_portal_candidates_pack_to_tenant
from ._helpers.plans import (
    ADDON_PACK_CHECKOUT_READY,
    ADDON_PACK_CHECKOUT_UNAVAILABLE,
    CHECKOUT_OUTCOMES,
    PLAN_CODES,
    PUBLIC_CHECKOUT_PLAN_CODES,
    _addon_purchase_plan_ok_for_offer,
    _available_plans,
    _calculate_proration_amount_minor,
    _normalize_plan_code,
    _plan_price_id,
    _plan_stripe_price_id,
    _plan_stripe_yearly_price_id_only,
    _portal_candidates_pack_price_id,
    _stripe_obj_to_dict,
    _stripe_price_amount,
    _stripe_ready,
)
from ._helpers.state import (
    _ensure_tenant_access,
    _history_contains,
    _now_utc,
    _set_extra_operating_slots,
    _store_subscription,
    _subscription_out,
    _subscription_payload,
)
from ._helpers.stripe_extract import (
    _extract_subscription_billing_interval,
    _find_tenant_for_stripe_event,
    _list_stripe_invoices,
    _send_billing_email,
)
from ._helpers.summary import (
    _billing_max_storage_gb,
    _billing_summary_addon_offers,
    _billing_trial_caps,
    _billing_summary_extras,
    _billing_usage_caps,
    _company_slots_payload,
    _maybe_enroll_founder_program,
    _plan_code_for_usage_caps,
    _tenant_settings_dict,
)
from ._helpers.webhook_handlers import (
    _handle_checkout_completed,
    _handle_invoice_finalized,
    _handle_invoice_paid,
    _handle_invoice_payment_failed,
    _handle_subscription_event,
    _stripe_webhook_release_claim,
    _stripe_webhook_try_claim_event,
)
from .schemas import (
    BillingAddonPackCheckoutIn,
    BillingAddonPackCheckoutOut,
    BillingCancelIn,
    BillingChangePlanIn,
    BillingCheckoutCreateIn,
    BillingCheckoutOut,
    BillingCheckoutSimulateIn,
    BillingCompanySlotsUpdateIn,
    BillingPortalOut,
    BillingPortalPackCheckoutIn,
    BillingPortalPackCheckoutOut,
    BillingPlanMatrixFeatureOut,
    BillingPlanMatrixOut,
    BillingQuotaHeadroomOut,
    BillingSubscriptionOut,
    BillingSummaryOut,
    BillingWebhookOut,
)


def _get_stripe():
    """Late-bind the parent package's ``stripe`` attribute so test-time
    patches of ``billing.stripe`` are observed without holding a stale
    module reference."""
    from backend.app.api.v1.settings import billing as _billing_pkg
    return _billing_pkg.stripe



@router.get(
    "/subscription",
    response_model=BillingSubscriptionOut,
    dependencies=[Depends(require_trust_write())],
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
    license_entry = await tenant_service.get_tenant_license(db, tenant_id)
    return _subscription_out(tenant, license_entry=license_entry)


@router.get(
    "/quota-headroom",
    response_model=BillingQuotaHeadroomOut,
)
async def get_billing_quota_headroom(
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> BillingQuotaHeadroomOut:
    """Usage vs plan caps for soft quota banners (all tenant members; SSOT with ``_billing_usage_caps``)."""
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    _ensure_tenant_access(ctx, tenant_id)
    tenant = await db.get(Tenant, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    license_entry = await tenant_service.get_tenant_license(db, tenant_id)
    usage = await tenant_service.get_usage_snapshot(db, tenant_id)
    sub_payload = _subscription_payload(tenant)
    caps = _billing_usage_caps(license_entry, sub_payload, _tenant_settings_dict(tenant))
    max_storage = _billing_max_storage_gb(license_entry, sub_payload)
    return BillingQuotaHeadroomOut(
        leads_created_this_month=int(usage.get("leads_created_this_month") or 0),
        max_leads_created_per_month=int(caps.max_leads_created_per_month),
        candidates_active_count=int(usage.get("candidates_active_count") or 0),
        max_candidates_active=int(caps.max_candidates_active),
        storage_used_gb=float(usage.get("storage_used_gb") or 0.0),
        max_storage_gb=max_storage,
    )


@router.get(
    "/summary",
    response_model=BillingSummaryOut,
    dependencies=[Depends(require_trust_write())],
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
        _get_stripe().api_key = settings.stripe_secret_key
        try:
            live_sub = _stripe_obj_to_dict(_get_stripe().Subscription.retrieve(  # type: ignore[union-attr]
                subscription_id,
                expand=["latest_invoice", "latest_invoice.payment_intent", "items.data.price"],
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
    subscription = _subscription_out(tenant, license_entry=license_entry)
    invoices = _list_stripe_invoices(_subscription_payload(tenant))
    history = _merge_history_with_invoices(_history_out(tenant), invoices)
    company_slots = await _company_slots_payload(db, tenant=tenant, license_entry=license_entry)
    sub_payload = _subscription_payload(tenant)
    portal_candidates, founder_program, lead_forms = await _billing_summary_extras(
        db, tenant, license_entry, sub_payload
    )
    return BillingSummaryOut(
        subscription=subscription,
        license=platform_schemas.TenantLicenseOut.model_validate(license_entry) if license_entry else None,
        usage=platform_schemas.TenantUsageOut(**usage),
        usage_caps=_billing_usage_caps(license_entry, sub_payload, _tenant_settings_dict(tenant)),
        trial_caps=_billing_trial_caps(sub_payload),
        company_slots=company_slots,
        portal_candidates=portal_candidates,
        founder_program=founder_program,
        lead_forms=lead_forms,
        available_plans=_available_plans(),
        history=history,
        invoices=invoices,
        addon_checkout_offers=_billing_summary_addon_offers(license_entry, sub_payload),
    )
@router.get(
    "/plan-matrix",
    response_model=BillingPlanMatrixOut,
    dependencies=[Depends(require_trust_write())],
)
async def get_billing_plan_matrix(
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> BillingPlanMatrixOut:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    _ensure_tenant_access(ctx, tenant_id)
    tenant = await db.get(Tenant, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    license_entry = await tenant_service.get_tenant_license(db, tenant_id)
    current_plan_code = _plan_code_for_usage_caps(_subscription_payload(tenant), license_entry)
    plans = _available_plans()

    def _v(
        starter: int | bool | str | None,
        team: int | bool | str | None,
        pro: int | bool | str | None,
        enterprise: int | bool | str | None,
    ) -> dict[str, int | bool | str | None]:
        return {"starter": starter, "team": team, "pro": pro, "enterprise": enterprise}

    features = [
        BillingPlanMatrixFeatureOut(
            key="max_candidates_active",
            label="Active records",
            unit="count",
            values=_v(300, 2000, 10000, 50000),
        ),
        BillingPlanMatrixFeatureOut(
            key="inbound_leads_monthly",
            label="Inbound leads / month",
            unit="count",
            values=_v(200, 1500, 5000, 5000),
        ),
        BillingPlanMatrixFeatureOut(
            key="lead_sources",
            label="Lead sources",
            unit="count",
            values=_v(1, 3, 10, 10),
        ),
        BillingPlanMatrixFeatureOut(
            key="portal_candidate_shares_monthly",
            label="Portal candidate shares / month",
            unit="count",
            values=_v(None, 300, 2000, 2000),
        ),
        BillingPlanMatrixFeatureOut(
            key="automation_rules_enabled",
            label="Enabled automation rules",
            unit="count",
            values=_v(0, 10, 50, 50),
        ),
        BillingPlanMatrixFeatureOut(
            key="communication_channels",
            label="Communication channels",
            unit="count",
            values=_v(1, 3, 10, 10),
        ),
        BillingPlanMatrixFeatureOut(
            key="custom_funnels",
            label="Custom funnels",
            unit="count",
            values=_v(1, 3, 20, 20),
        ),
        BillingPlanMatrixFeatureOut(
            key="self_serve_checkout",
            label="Self-serve checkout",
            values=_v(True, True, True, False),
            upgrade_checkout_allowed=False,
        ),
        BillingPlanMatrixFeatureOut(
            key="smart_operations",
            label="Intelligent operations (load-aware manager queue, smart routing)",
            values=_v(False, True, True, True),
        ),
    ]
    return BillingPlanMatrixOut(plans=plans, current_plan_code=current_plan_code, features=features)


@router.post(
    "/checkout-session",
    response_model=BillingCheckoutOut,
    dependencies=[Depends(require_trust_admin())],
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
    if plan_code not in PUBLIC_CHECKOUT_PLAN_CODES:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "plan_contact_sales_only",
                "message": f"Plan '{plan_code}' is not available via self-serve checkout. Contact sales.",
                "plan_code": plan_code,
            },
        )
    bill_interval = (payload.billing_interval or "month").strip().lower()
    if bill_interval not in ("month", "year"):
        bill_interval = "month"
    success_url = (payload.success_url or "").strip() or SETTINGS_BILLING_CHECKOUT_SUCCESS
    cancel_url = (payload.cancel_url or "").strip() or SETTINGS_BILLING_CHECKOUT_CANCEL
    session_id = f"cs_{uuid4().hex}"

    current = _subscription_payload(tenant)

    if _stripe_ready():
        price_id = _plan_stripe_price_id(plan_code, bill_interval)
        if not price_id:
            raise HTTPException(
                status_code=400,
                detail=f"Stripe price ID for '{plan_code}' interval '{bill_interval}' is not configured",
            )
        _get_stripe().api_key = settings.stripe_secret_key
        checkout = _get_stripe().checkout.Session.create(  # type: ignore[union-attr]
            mode="subscription",
            line_items=[{"price": price_id, "quantity": 1}],
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={
                "tenant_id": tenant_id,
                "plan_code": plan_code,
                "billing_interval": bill_interval,
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
        "billing_interval": bill_interval,
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
    "/portal-candidates-pack/checkout",
    response_model=BillingPortalPackCheckoutOut,
    dependencies=[Depends(require_trust_admin())],
)
async def create_portal_candidates_pack_checkout(
    payload: BillingPortalPackCheckoutIn,
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> BillingPortalPackCheckoutOut:
    """§2.16: one-time Stripe Checkout (payment) to raise monthly active portal candidate cap."""
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    _ensure_tenant_access(ctx, tenant_id)
    tenant = await db.get(Tenant, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")

    license_entry = await tenant_service.get_tenant_license(db, tenant_id)
    sub_payload = _subscription_payload(tenant)
    pc_plan = _plan_code_for_usage_caps(sub_payload, license_entry)
    if portal_candidate_usage.monthly_cap_for_plan_code(pc_plan) is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Portal candidate packs are available on Team and Business plans only.",
        )

    success_url = (payload.success_url or "").strip() or SETTINGS_BILLING_CHECKOUT_SUCCESS
    cancel_url = (payload.cancel_url or "").strip() or SETTINGS_BILLING_CHECKOUT_CANCEL
    increment = int(settings.portal_candidates_pack_increment)
    pack_price = _portal_candidates_pack_price_id()

    if _stripe_ready() and pack_price:
        customer_id = str(sub_payload.get("customer_id") or "").strip()
        if not customer_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Complete a subscription checkout first so we have a Stripe customer for add-ons.",
            )
        _get_stripe().api_key = settings.stripe_secret_key
        checkout = _get_stripe().checkout.Session.create(  # type: ignore[union-attr]
            mode="payment",
            customer=customer_id,
            line_items=[{"price": pack_price, "quantity": 1}],
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={
                "tenant_id": tenant_id,
                "billing_action": "portal_candidates_pack",
                "pack_increment": str(increment),
                "plan_code": pc_plan,
                "requested_by": ctx.sub,
            },
            client_reference_id=tenant_id,
        )
        session_id = str(checkout.get("id") or f"cs_{uuid4().hex}")
        checkout_url = str(checkout.get("url") or success_url)
        return BillingPortalPackCheckoutOut(
            provider="stripe",
            mode="payment",
            status="open",
            session_id=session_id,
            checkout_url=checkout_url,
            pack_increment=increment,
        )

    if _stripe_ready() and not pack_price:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stripe is configured but STRIPE_PRICE_PORTAL_CANDIDATES_PACK is not set.",
        )

    session_id = f"mock_pp_{uuid4().hex}"
    dedupe_key = f"app:{session_id}:portal_pack_mock"
    await _apply_portal_candidates_pack_to_tenant(
        db,
        tenant,
        increment=increment,
        history_title="Candidate portal pack (mock)",
        history_description=f"Dev/mock billing: +{increment} active portal candidates / month.",
        dedupe_key=dedupe_key,
        plan_code=pc_plan,
        history_source="app",
    )
    return BillingPortalPackCheckoutOut(
        provider="mock",
        mode="payment",
        status="completed",
        session_id=session_id,
        checkout_url=success_url,
        pack_increment=increment,
    )



@router.post(
    "/addon-pack/checkout",
    response_model=BillingAddonPackCheckoutOut,
    dependencies=[Depends(require_trust_admin())],
)
async def create_addon_pack_checkout(
    payload: BillingAddonPackCheckoutIn,
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> BillingAddonPackCheckoutOut:
    """§2.16: generic one-time Checkout for supported `checkout_payment` SKUs (see summary.addon_checkout_offers)."""
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    _ensure_tenant_access(ctx, tenant_id)
    tenant = await db.get(Tenant, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")

    sku = (payload.sku or "").strip()

    license_entry = await tenant_service.get_tenant_license(db, tenant_id)
    sub_payload = _subscription_payload(tenant)
    pc_plan = _plan_code_for_usage_caps(sub_payload, license_entry)

    if sku not in ADDON_PACK_CHECKOUT_READY:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=ADDON_PACK_CHECKOUT_UNAVAILABLE)
    plan_ok, _ = _addon_purchase_plan_ok_for_offer(sku, pc_plan)
    if not plan_ok:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=ADDON_PACK_CHECKOUT_UNAVAILABLE)

    pack_price = sku_price_from_settings(settings, sku)
    increment = sku_pack_increment(settings, sku)
    if increment is None or int(increment) <= 0:
        raise HTTPException(status_code=500, detail="Invalid pack increment configuration for SKU.")

    success_url = (payload.success_url or "").strip() or SETTINGS_BILLING_CHECKOUT_SUCCESS
    cancel_url = (payload.cancel_url or "").strip() or SETTINGS_BILLING_CHECKOUT_CANCEL

    if _stripe_ready() and pack_price:
        customer_id = str(sub_payload.get("customer_id") or "").strip()
        if not customer_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Complete a subscription checkout first so we have a Stripe customer for add-ons.",
            )
        _get_stripe().api_key = settings.stripe_secret_key
        checkout = _get_stripe().checkout.Session.create(  # type: ignore[union-attr]
            mode="payment",
            customer=customer_id,
            line_items=[{"price": pack_price, "quantity": 1}],
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={
                "tenant_id": tenant_id,
                "billing_action": "addon_pack",
                "billing_sku": sku,
                "pack_increment": str(increment),
                "plan_code": pc_plan,
                "requested_by": ctx.sub,
            },
            client_reference_id=tenant_id,
        )
        session_id = str(checkout.get("id") or f"cs_{uuid4().hex}")
        checkout_url = str(checkout.get("url") or success_url)
        return BillingAddonPackCheckoutOut(
            provider="stripe",
            mode="payment",
            status="open",
            session_id=session_id,
            checkout_url=checkout_url,
            sku=sku,
            pack_increment=int(increment),
        )

    if _stripe_ready() and not pack_price:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Stripe is configured but price env for SKU {sku} is not set.",
        )

    session_id = f"mock_ap_{uuid4().hex}"
    dedupe_key = f"app:{session_id}:addon_pack_mock:{sku}"
    await _apply_addon_pack_by_sku(
        db,
        tenant,
        sku=sku,
        increment=int(increment),
        dedupe_key=dedupe_key,
        plan_code=pc_plan,
        history_source="app",
    )
    return BillingAddonPackCheckoutOut(
        provider="mock",
        mode="payment",
        status="completed",
        session_id=session_id,
        checkout_url=success_url,
        sku=sku,
        pack_increment=int(increment),
    )



@router.post(
    "/checkout-session/{session_id}/simulate",
    response_model=BillingSubscriptionOut,
    dependencies=[Depends(require_trust_admin())],
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
    biv = str(current.get("billing_interval") or "month").strip().lower()
    if biv not in ("month", "year"):
        biv = "month"
    now = _now_utc()
    if outcome == "success":
        period_days = 365 if biv == "year" else 30
        updated = {
            **current,
            "provider": "mock" if not _stripe_ready() else str(current.get("provider") or "stripe"),
            "status": "active",
            "plan_code": plan_code,
            "billing_interval": biv,
            "checkout_session_id": session_id,
            "current_period_start": now.isoformat(),
            "current_period_end": (now + timedelta(days=period_days)).isoformat(),
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
        await _maybe_enroll_founder_program(db, tenant_id, plan_code)
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
    dependencies=[Depends(require_trust_admin())],
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
    if plan_code not in PUBLIC_CHECKOUT_PLAN_CODES:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "plan_contact_sales_only",
                "message": f"Plan '{plan_code}' is not available via self-serve checkout. Contact sales.",
                "plan_code": plan_code,
            },
        )
    current = _subscription_payload(tenant)
    now = _now_utc()
    req_iv_from_payload: Literal["month", "year"] | None = None
    if payload.billing_interval is not None:
        r = str(payload.billing_interval).strip().lower()
        if r in ("month", "year"):
            req_iv_from_payload = r  # type: ignore[assignment]
    provider = str(current.get("provider") or "").strip().lower()
    subscription_id = str(current.get("subscription_id") or "").strip()
    customer_id = str(current.get("customer_id") or "").strip()
    if _stripe_ready() and provider == "stripe" and subscription_id and customer_id:
        _get_stripe().api_key = settings.stripe_secret_key
        sub = _stripe_obj_to_dict(
            _get_stripe().Subscription.retrieve(subscription_id, expand=["latest_invoice", "items.data.price"])  # type: ignore[union-attr]
        )
        current_plan_code = _normalize_plan_code(str(current.get("plan_code") or "starter"))
        cur_sub_iv = _extract_subscription_billing_interval(sub)
        bill_interval: Literal["month", "year"] = req_iv_from_payload if req_iv_from_payload is not None else cur_sub_iv
        if plan_code == current_plan_code:
            if req_iv_from_payload is not None and req_iv_from_payload != cur_sub_iv:
                items = sub.get("items", {}).get("data", []) if isinstance(sub, dict) else []
                first_item = _stripe_obj_to_dict(items[0]) if isinstance(items, list) and items else {}
                item_id = str(first_item.get("id") or "").strip()
                switch_price_id = _plan_stripe_price_id(plan_code, req_iv_from_payload)
                if not item_id or not switch_price_id:
                    raise HTTPException(
                        status_code=400,
                        detail=(
                            f"Stripe price ID for '{plan_code}' interval '{req_iv_from_payload}' is not configured"
                        ),
                    )
                updated_stripe = _stripe_obj_to_dict(_get_stripe().Subscription.modify(  # type: ignore[union-attr]
                    subscription_id,
                    items=[{"id": item_id, "price": switch_price_id}],
                    proration_behavior="none",
                ))
                await _handle_subscription_event(db, updated_stripe, deleted=False)
                await _maybe_enroll_founder_program(db, tenant_id, plan_code)
                tenant = await db.get(Tenant, tenant_id)
                if tenant is None:
                    raise HTTPException(status_code=404, detail="Tenant not found")
                license_entry = await tenant_service.get_tenant_license(db, tenant_id)
                usage = await tenant_service.get_usage_snapshot(db, tenant_id)
                company_slots = await _company_slots_payload(db, tenant=tenant, license_entry=license_entry)
                sub_payload = _subscription_payload(tenant)
                portal_candidates, founder_program, lead_forms = await _billing_summary_extras(
                    db, tenant, license_entry, sub_payload
                )
                return BillingSummaryOut(
                    subscription=_subscription_out(tenant),
                    license=platform_schemas.TenantLicenseOut.model_validate(license_entry) if license_entry else None,
                    usage=platform_schemas.TenantUsageOut(**usage),
                    usage_caps=_billing_usage_caps(license_entry, sub_payload, _tenant_settings_dict(tenant)),
                    company_slots=company_slots,
                    portal_candidates=portal_candidates,
                    founder_program=founder_program,
                    lead_forms=lead_forms,
                    available_plans=_available_plans(),
                    history=_merge_history_with_invoices(_history_out(tenant), _list_stripe_invoices(sub_payload)),
                    invoices=_list_stripe_invoices(sub_payload),
                    addon_checkout_offers=_billing_summary_addon_offers(license_entry, sub_payload),
                )
            else:
                license_entry = await tenant_service.get_tenant_license(db, tenant_id)
                usage = await tenant_service.get_usage_snapshot(db, tenant_id)
                company_slots = await _company_slots_payload(db, tenant=tenant, license_entry=license_entry)
                sub_payload = _subscription_payload(tenant)
                portal_candidates, founder_program, lead_forms = await _billing_summary_extras(
                    db, tenant, license_entry, sub_payload
                )
                return BillingSummaryOut(
                    subscription=_subscription_out(tenant),
                    license=platform_schemas.TenantLicenseOut.model_validate(license_entry) if license_entry else None,
                    usage=platform_schemas.TenantUsageOut(**usage),
                    usage_caps=_billing_usage_caps(license_entry, sub_payload, _tenant_settings_dict(tenant)),
                    company_slots=company_slots,
                    portal_candidates=portal_candidates,
                    founder_program=founder_program,
                    lead_forms=lead_forms,
                    available_plans=_available_plans(),
                    history=_history_out(tenant),
                    invoices=_list_stripe_invoices(sub_payload),
                    addon_checkout_offers=_billing_summary_addon_offers(license_entry, sub_payload),
                )
        if plan_code != current_plan_code:
            items = sub.get("items", {}).get("data", []) if isinstance(sub, dict) else []
            first_item = _stripe_obj_to_dict(items[0]) if isinstance(items, list) and items else {}
            if not first_item:
                raise HTTPException(status_code=409, detail="Stripe subscription items are unavailable")
            item_id = str(first_item.get("id") or "").strip()
            if not item_id:
                raise HTTPException(status_code=409, detail="Stripe subscription item is unavailable")
            price_id = _plan_stripe_price_id(plan_code, bill_interval)
            if not price_id:
                raise HTTPException(
                    status_code=400,
                    detail=f"Stripe price ID for '{plan_code}' interval '{bill_interval}' is not configured",
                )
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
                        _get_stripe().Invoice.void_invoice(stale_invoice_id)  # type: ignore[union-attr]
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
                success_url = (payload.success_url or "").strip() or SETTINGS_BILLING_CHECKOUT_SUCCESS
                cancel_url = (payload.cancel_url or "").strip() or SETTINGS_BILLING_CHECKOUT_CANCEL
                checkout = _get_stripe().checkout.Session.create(  # type: ignore[union-attr]
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
                        "billing_interval": bill_interval,
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
                sub_payload = _subscription_payload(tenant)
                portal_candidates, founder_program, lead_forms = await _billing_summary_extras(
                    db, tenant, license_entry, sub_payload
                )
                return BillingSummaryOut(
                    subscription=BillingSubscriptionOut(**response_subscription),
                    license=platform_schemas.TenantLicenseOut.model_validate(license_entry) if license_entry else None,
                    usage=platform_schemas.TenantUsageOut(**usage),
                    usage_caps=_billing_usage_caps(license_entry, sub_payload, _tenant_settings_dict(tenant)),
                    company_slots=company_slots,
                    portal_candidates=portal_candidates,
                    founder_program=founder_program,
                    lead_forms=lead_forms,
                    available_plans=_available_plans(),
                    history=_merge_history_with_invoices(_history_out(tenant), _list_stripe_invoices(sub_payload)),
                    invoices=_list_stripe_invoices(sub_payload),
                    addon_checkout_offers=_billing_summary_addon_offers(license_entry, sub_payload),
                )
            else:
                updated_stripe = _stripe_obj_to_dict(_get_stripe().Subscription.modify(  # type: ignore[union-attr]
                    subscription_id,
                    items=[{"id": item_id, "price": price_id}],
                    proration_behavior="none",
                ))
                await _handle_subscription_event(db, updated_stripe, deleted=False)
                await _maybe_enroll_founder_program(db, tenant_id, plan_code)
    else:
        cur_mock_iv = str(current.get("billing_interval") or "month").strip().lower()
        if cur_mock_iv not in ("month", "year"):
            cur_mock_iv = "month"
        mock_bill_iv: Literal["month", "year"] = (
            req_iv_from_payload if req_iv_from_payload is not None else cur_mock_iv
        )
        current_plan_mock = _normalize_plan_code(str(current.get("plan_code") or "starter"))
        period_days = 365 if mock_bill_iv == "year" else 30
        await _store_subscription(
            db,
            tenant,
            {
                **current,
                "provider": "mock" if not _stripe_ready() else str(current.get("provider") or "stripe"),
                "status": "active",
                "plan_code": plan_code,
                "billing_interval": mock_bill_iv,
                "billing_contact_email": (ctx.email or "").strip() or current.get("billing_contact_email"),
                "cancel_at_period_end": False,
                "canceled_at": None,
                "current_period_start": now.isoformat(),
                "current_period_end": (now + timedelta(days=period_days)).isoformat(),
                "activated_at": str(current.get("activated_at") or "").strip() or now.isoformat(),
                "updated_at": now.isoformat(),
            },
            history_entry=_history_entry(
                event_type="subscription.plan_changed",
                status="success",
                title="Billing interval updated" if plan_code == current_plan_mock else "Plan changed",
                description=(
                    f"Billing interval set to {mock_bill_iv}."
                    if plan_code == current_plan_mock
                    else f"Subscription switched to {plan_code.upper()}."
                ),
                source="app",
                plan_code=plan_code,
                dedupe_key=f"app:{tenant_id}:plan-change:{plan_code}:{mock_bill_iv}:{now.isoformat()}",
            ),
        )
        await _maybe_enroll_founder_program(db, tenant_id, plan_code)
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
    await _maybe_enroll_founder_program(db, tenant_id, effective_subscription.plan_code)
    tenant = await db.get(Tenant, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    license_entry = await tenant_service.get_tenant_license(db, tenant_id)
    usage = await tenant_service.get_usage_snapshot(db, tenant_id)
    company_slots = await _company_slots_payload(db, tenant=tenant, license_entry=license_entry)
    sub_payload = _subscription_payload(tenant)
    portal_candidates, founder_program, lead_forms = await _billing_summary_extras(
        db, tenant, license_entry, sub_payload
    )
    return BillingSummaryOut(
        subscription=_subscription_out(tenant, license_entry=license_entry),
        license=platform_schemas.TenantLicenseOut.model_validate(license_entry) if license_entry else None,
        usage=platform_schemas.TenantUsageOut(**usage),
        usage_caps=_billing_usage_caps(license_entry, sub_payload, _tenant_settings_dict(tenant)),
        company_slots=company_slots,
        portal_candidates=portal_candidates,
        founder_program=founder_program,
        lead_forms=lead_forms,
        available_plans=_available_plans(),
        history=_history_out(tenant),
        invoices=_list_stripe_invoices(sub_payload),
        addon_checkout_offers=_billing_summary_addon_offers(license_entry, sub_payload),
    )



@router.post(
    "/company-slots",
    response_model=BillingSummaryOut,
    dependencies=[Depends(require_trust_admin())],
)
async def update_company_slots(
    payload: BillingCompanySlotsUpdateIn,
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
    old_extra_slots = extract_extra_operating_company_slots(current)
    new_extra_slots = max(0, int(payload.extra_slots or 0))

    provider = str(current.get("provider") or "").strip().lower()
    subscription_id = str(current.get("subscription_id") or "").strip()
    plan_for_slots = str(current.get("plan_code") or "starter")
    addon_price_id = _operating_slot_addon_price_id_for_plan(plan_for_slots)
    if (
        _stripe_ready()
        and provider == "stripe"
        and subscription_id
        and addon_price_id
        and new_extra_slots != old_extra_slots
    ):
        _get_stripe().api_key = settings.stripe_secret_key
        try:
            stripe_sub = _stripe_obj_to_dict(_get_stripe().Subscription.retrieve(subscription_id, expand=["items.data.price"]))  # type: ignore[union-attr]
            existing_addon_item, existing_price_id = _find_operating_slot_addon_item(stripe_sub)
            item_id = str((existing_addon_item or {}).get("id") or "").strip()
            if new_extra_slots <= 0 and item_id:
                updated_stripe = _stripe_obj_to_dict(
                    _get_stripe().Subscription.modify(  # type: ignore[union-attr]
                        subscription_id,
                        items=[{"id": item_id, "deleted": True}],
                    )
                )
                await _handle_subscription_event(db, updated_stripe, deleted=False)
            elif new_extra_slots > 0 and item_id and existing_price_id == addon_price_id:
                updated_stripe = _stripe_obj_to_dict(
                    _get_stripe().Subscription.modify(  # type: ignore[union-attr]
                        subscription_id,
                        items=[{"id": item_id, "quantity": new_extra_slots}],
                    )
                )
                await _handle_subscription_event(db, updated_stripe, deleted=False)
            elif new_extra_slots > 0 and item_id and existing_price_id and existing_price_id != addon_price_id:
                updated_stripe = _stripe_obj_to_dict(
                    _get_stripe().Subscription.modify(  # type: ignore[union-attr]
                        subscription_id,
                        items=[
                            {"id": item_id, "deleted": True},
                            {"price": addon_price_id, "quantity": new_extra_slots},
                        ],
                    )
                )
                await _handle_subscription_event(db, updated_stripe, deleted=False)
            elif new_extra_slots > 0 and not item_id:
                updated_stripe = _stripe_obj_to_dict(
                    _get_stripe().Subscription.modify(  # type: ignore[union-attr]
                        subscription_id,
                        items=[{"price": addon_price_id, "quantity": new_extra_slots}],
                    )
                )
                await _handle_subscription_event(db, updated_stripe, deleted=False)
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=409, detail=f"Failed to update Stripe add-on slots: {exc}") from exc
        tenant = await db.get(Tenant, tenant_id)
        if tenant is None:
            raise HTTPException(status_code=404, detail="Tenant not found")
        current = _subscription_payload(tenant)

    if new_extra_slots != old_extra_slots:
        now = _now_utc()
        await _store_subscription(
            db,
            tenant,
            {
                **_set_extra_operating_slots(current, new_extra_slots),
                "updated_at": now.isoformat(),
            },
            history_entry=_history_entry(
                event_type="subscription.company_slots_updated",
                status="success",
                title="Operating company slots updated",
                description=f"Add-on slots changed from {old_extra_slots} to {new_extra_slots}.",
                source="app",
                plan_code=str(current.get("plan_code") or "starter"),
                dedupe_key=f"app:{tenant_id}:company-slots:{old_extra_slots}:{new_extra_slots}:{now.isoformat()}",
            ),
        )
        tenant = await db.get(Tenant, tenant_id)
        if tenant is None:
            raise HTTPException(status_code=404, detail="Tenant not found")

    license_entry = await tenant_service.get_tenant_license(db, tenant_id)
    usage = await tenant_service.get_usage_snapshot(db, tenant_id)
    company_slots = await _company_slots_payload(db, tenant=tenant, license_entry=license_entry)
    sub_payload = _subscription_payload(tenant)
    portal_candidates, founder_program, lead_forms = await _billing_summary_extras(
        db, tenant, license_entry, sub_payload
    )
    return BillingSummaryOut(
        subscription=_subscription_out(tenant),
        license=platform_schemas.TenantLicenseOut.model_validate(license_entry) if license_entry else None,
        usage=platform_schemas.TenantUsageOut(**usage),
        usage_caps=_billing_usage_caps(license_entry, sub_payload, _tenant_settings_dict(tenant)),
        company_slots=company_slots,
        portal_candidates=portal_candidates,
        founder_program=founder_program,
        lead_forms=lead_forms,
        available_plans=_available_plans(),
        history=_history_out(tenant),
        invoices=_list_stripe_invoices(sub_payload),
        addon_checkout_offers=_billing_summary_addon_offers(license_entry, sub_payload),
    )



@router.post(
    "/cancel",
    response_model=BillingSummaryOut,
    dependencies=[Depends(require_trust_admin())],
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
        _get_stripe().api_key = settings.stripe_secret_key
        if payload.immediate:
            _get_stripe().Subscription.cancel(subscription_id)  # type: ignore[union-attr]
            updated_stripe = _get_stripe().Subscription.retrieve(subscription_id)  # type: ignore[union-attr]
            await _handle_subscription_event(db, updated_stripe if isinstance(updated_stripe, dict) else updated_stripe.to_dict(), deleted=True)
        else:
            updated_stripe = _get_stripe().Subscription.modify(subscription_id, cancel_at_period_end=True)  # type: ignore[union-attr]
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
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    company_slots = await _company_slots_payload(db, tenant=tenant, license_entry=license_entry)
    sub_payload = _subscription_payload(tenant)
    portal_candidates, founder_program, lead_forms = await _billing_summary_extras(
        db, tenant, license_entry, sub_payload
    )
    return BillingSummaryOut(
        subscription=_subscription_out(tenant),
        license=platform_schemas.TenantLicenseOut.model_validate(license_entry) if license_entry else None,
        usage=platform_schemas.TenantUsageOut(**usage),
        usage_caps=_billing_usage_caps(license_entry, sub_payload, _tenant_settings_dict(tenant)),
        company_slots=company_slots,
        portal_candidates=portal_candidates,
        founder_program=founder_program,
        lead_forms=lead_forms,
        available_plans=_available_plans(),
        history=_history_out(tenant),
        invoices=_list_stripe_invoices(sub_payload),
        addon_checkout_offers=_billing_summary_addon_offers(license_entry, sub_payload),
    )



@router.post(
    "/reactivate",
    response_model=BillingSummaryOut,
    dependencies=[Depends(require_trust_admin())],
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
        _get_stripe().api_key = settings.stripe_secret_key
        updated_stripe = _get_stripe().Subscription.modify(subscription_id, cancel_at_period_end=False)  # type: ignore[union-attr]
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
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    company_slots = await _company_slots_payload(db, tenant=tenant, license_entry=license_entry)
    sub_payload = _subscription_payload(tenant)
    portal_candidates, founder_program, lead_forms = await _billing_summary_extras(
        db, tenant, license_entry, sub_payload
    )
    return BillingSummaryOut(
        subscription=_subscription_out(tenant),
        license=platform_schemas.TenantLicenseOut.model_validate(license_entry) if license_entry else None,
        usage=platform_schemas.TenantUsageOut(**usage),
        usage_caps=_billing_usage_caps(license_entry, sub_payload, _tenant_settings_dict(tenant)),
        company_slots=company_slots,
        portal_candidates=portal_candidates,
        founder_program=founder_program,
        lead_forms=lead_forms,
        available_plans=_available_plans(),
        history=_history_out(tenant),
        invoices=_list_stripe_invoices(sub_payload),
        addon_checkout_offers=_billing_summary_addon_offers(license_entry, sub_payload),
    )



@router.post(
    "/portal",
    response_model=BillingPortalOut,
    dependencies=[Depends(require_trust_admin())],
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
    return_url = (settings.stripe_portal_return_url or "").strip() or SETTINGS_BILLING
    if _stripe_ready() and customer_id:
        _get_stripe().api_key = settings.stripe_secret_key
        session = _get_stripe().billing_portal.Session.create(  # type: ignore[union-attr]
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
    if _get_stripe() is None:
        return BillingWebhookOut(accepted=False, detail="Stripe SDK is not installed")
    if not stripe_signature:
        raise HTTPException(status_code=400, detail="Missing Stripe-Signature header")

    try:
        event = _get_stripe().Webhook.construct_event(  # type: ignore[union-attr]
            payload=payload,
            sig_header=stripe_signature,
            secret=webhook_secret,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid Stripe webhook signature: {exc}") from exc

    event_id = str(getattr(event, "id", "") or "").strip()
    if not event_id and hasattr(event, "to_dict"):
        ev_dict = event.to_dict()  # type: ignore[union-attr]
        if isinstance(ev_dict, dict):
            event_id = str(ev_dict.get("id") or "").strip()

    event_type = str(getattr(event, "type", "") or "")
    if event_id:
        claimed = await _stripe_webhook_try_claim_event(db, event_id, event_type)
        if not claimed:
            return BillingWebhookOut(accepted=True, detail=f"Duplicate webhook ignored: {event_id}")

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

    # When ARQ is configured, push the heavy handler to the worker so Stripe
    # gets a fast 2xx and retries fall on our queue retry policy instead of
    # Stripe's tight timeout. The idempotency claim above guarantees we never
    # process the same event twice — on worker failure the job releases it.
    if (
        event_id
        and getattr(settings, "job_queue_stripe_webhook_async", True)
        and str(getattr(settings, "job_queue_backend", "inprocess") or "").strip().lower() == "arq"
    ):
        try:
            from backend.app.core.queue import enqueue_job

            await enqueue_job(
                "stripe_webhook_process",
                job_id=f"stripe:{event_id}",
                event_id=event_id,
                event_type=event_type,
                event_obj=obj,
            )
            return BillingWebhookOut(
                accepted=True,
                detail=f"Queued for async processing: {event_type}",
            )
        except Exception:
            # Fall through to inline handling so we never lose a webhook.
            logger = __import__("logging").getLogger(__name__)
            logger.exception("[stripe_webhook] enqueue failed, falling back to inline handler")

    try:
        if event_type == "checkout.session.completed":
            detail = await _handle_checkout_completed(db, obj)
        elif event_type in ("invoice.paid", "invoice.payment_succeeded"):
            detail = await _handle_invoice_paid(db, obj)
        elif event_type == "invoice.finalized":
            detail = await _handle_invoice_finalized(db, obj)
        elif event_type == "invoice.payment_failed":
            detail = await _handle_invoice_payment_failed(db, obj)
        elif event_type == "customer.subscription.created":
            detail = await _handle_subscription_event(db, obj, deleted=False)
        elif event_type == "customer.subscription.updated":
            detail = await _handle_subscription_event(db, obj, deleted=False)
        elif event_type == "customer.subscription.deleted":
            detail = await _handle_subscription_event(db, obj, deleted=True)
        else:
            detail = f"Ignored: unsupported event type {event_type or '<empty>'}"
    except Exception:
        if event_id:
            await _stripe_webhook_release_claim(db, event_id)
        raise

    return BillingWebhookOut(accepted=True, detail=detail)
