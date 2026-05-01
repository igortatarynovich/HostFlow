"""Pydantic schemas for the billing API.

Extracted from ``backend/app/api/v1/settings/billing.py`` as part of
the Phase 1 god-module split (step 1/N).

All 24 ``Billing*`` Pydantic models live here. They import only stdlib
+ pydantic + ``platform.schemas`` (for ``TenantLicenseOut`` / ``TenantUsageOut``
referenced by ``BillingSummaryOut``).
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from backend.app.api.v1.platform import schemas as platform_schemas


class BillingUsageCapsOut(BaseModel):
    """Display caps for billing usage rows; 0 means unlimited (same convention as seat limits)."""

    max_leads_created_per_month: int = 0
    max_candidates_active: int = 0
    max_vacancies_active: int = 0
    max_documents: int = 0
    max_public_portal_links: int = 0


class BillingQuotaHeadroomOut(BaseModel):
    """Minimal usage vs caps for module quota banners (any tenant member; SSOT with ``_billing_usage_caps``)."""

    leads_created_this_month: int = 0
    max_leads_created_per_month: int = 0
    candidates_active_count: int = 0
    max_candidates_active: int = 0
    storage_used_gb: float = 0.0
    max_storage_gb: int = 0


class BillingTrialCapsOut(BaseModel):
    """SSOT trial-limits snapshot shown in billing summary."""

    leads_monthly: int = 50
    conversion_actions: int = 20
    portal_shares: int = 2
    automation_runs: int = 5


class BillingGateOut(BaseModel):
    """Derived billing/trial state for UI (Dashboard banners, §2.18)."""

    side_effects_blocked: bool = False
    block_reason: Literal["past_due", "trial_expired"] | None = None
    trial_active: bool = False
    trial_grace_active: bool = False
    trial_hours_remaining: float | None = None
    trial_urgent: bool = False
    side_effect_grace_hours_remaining: float | None = None


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
    billing_interval: Literal["month", "year"] | None = None
    current_period_start: datetime | None = None
    current_period_end: datetime | None = None
    activated_at: datetime | None = None
    trial_ends_at: datetime | None = None
    cancel_at_period_end: bool = False
    canceled_at: datetime | None = None
    updated_at: datetime | None = None
    gate: BillingGateOut = Field(default_factory=BillingGateOut)


class BillingCheckoutCreateIn(BaseModel):
    plan_code: str = Field(..., min_length=2, max_length=32)
    billing_interval: Literal["month", "year"] = "month"
    success_url: str | None = Field(default=None, max_length=2000)
    cancel_url: str | None = Field(default=None, max_length=2000)


class BillingCheckoutOut(BaseModel):
    provider: Literal["mock", "stripe"] = "mock"
    mode: Literal["subscription"] = "subscription"
    status: str
    session_id: str
    checkout_url: str


class BillingPortalPackCheckoutIn(BaseModel):
    success_url: str | None = Field(default=None, max_length=2000)
    cancel_url: str | None = Field(default=None, max_length=2000)


class BillingPortalPackCheckoutOut(BaseModel):
    provider: Literal["mock", "stripe"] = "mock"
    mode: Literal["payment"] = "payment"
    status: str
    session_id: str
    checkout_url: str
    pack_increment: int


class BillingAddonPackCheckoutIn(BaseModel):
    sku: str = Field(..., min_length=4, max_length=64)
    success_url: str | None = Field(default=None, max_length=2000)
    cancel_url: str | None = Field(default=None, max_length=2000)


class BillingAddonPackCheckoutOut(BaseModel):
    provider: Literal["mock", "stripe"] = "mock"
    mode: Literal["payment"] = "payment"
    status: str
    session_id: str
    checkout_url: str
    sku: str
    pack_increment: int


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
    currency: str = "EUR"
    # Legacy field name (API compat): whole currency units for monthly list price (§2.16).
    monthly_price_usd: int
    yearly_equivalent_monthly_eur: int | None = None
    limits: dict[str, int]
    # Whether Stripe Price IDs are set in env for this plan (UI: enable month/year checkout).
    stripe_month_configured: bool = True
    stripe_year_configured: bool = False


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


class BillingCompanySlotsOut(BaseModel):
    included_limit: int
    extra_slots: int
    effective_limit: int
    used: int
    available: int
    unlimited: bool


class BillingPortalCandidatesUsageOut(BaseModel):
    """§2.16 active portal candidates / calendar month (UTC); soft limit until hard enforcement."""

    used_this_month_utc: int = 0
    cap: int | None = None
    base_cap: int | None = None
    pack_addon: int = 0
    pack_increment_offer: int = 0
    soft_limit: bool = True
    warning_level: Literal["none", "warn_80", "warn_100"] = "none"


class BillingFounderProgramOut(BaseModel):
    tenant_enrolled: bool = False
    tenant_revoked: bool = False


class BillingLeadFormsUsageOut(BaseModel):
    """§2.16 active lead forms (Solo 1 / Team 3 / Business 20 + pack_addons_v1)."""

    active_count: int = 0
    cap: int = 1
    base_cap: int = 1
    pack_addon: int = 0
    pack_increment_offer: int = 5


class BillingAddonCheckoutOfferOut(BaseModel):
    """§2.16 checkout_payment SKU row for billing summary (plan-aware).

    Canon v1: ``configured`` ≈ STRIPE_CATALOG (price id in env); ``effect_ready`` = SKU in
    ``ADDON_PACK_CHECKOUT_READY`` (product limit + webhook/mock apply); ``purchase_allowed`` =
    user can complete POST /addon-pack/checkout (effect + plan gates + Stripe price when Stripe mode).
    ``checkout_ready`` is a legacy alias of ``effect_ready`` for API consumers.
    """

    sku: str
    label: str
    configured: bool = False
    pack_increment: int | None = None
    effect_ready: bool = False
    checkout_ready: bool = False
    purchase_allowed: bool = False
    purchase_block_reason: str | None = None


class BillingSummaryOut(BaseModel):
    subscription: BillingSubscriptionOut
    license: platform_schemas.TenantLicenseOut | None = None
    usage: platform_schemas.TenantUsageOut
    usage_caps: BillingUsageCapsOut
    trial_caps: BillingTrialCapsOut | None = None
    company_slots: BillingCompanySlotsOut | None = None
    portal_candidates: BillingPortalCandidatesUsageOut | None = None
    founder_program: BillingFounderProgramOut | None = None
    lead_forms: BillingLeadFormsUsageOut | None = None
    available_plans: list[BillingPlanOut]
    history: list[BillingHistoryItemOut] = []
    invoices: list[BillingInvoiceOut] = []
    addon_checkout_offers: list[BillingAddonCheckoutOfferOut] = Field(default_factory=list)


class BillingPlanMatrixFeatureOut(BaseModel):
    key: str
    label: str
    unit: str | None = None
    values: dict[str, int | bool | str | None]
    upgrade_checkout_allowed: bool = True


class BillingPlanMatrixOut(BaseModel):
    plans: list[BillingPlanOut]
    current_plan_code: str
    features: list[BillingPlanMatrixFeatureOut]


class BillingChangePlanIn(BaseModel):
    plan_code: str = Field(..., min_length=2, max_length=32)
    billing_interval: Literal["month", "year"] | None = None
    success_url: str | None = Field(default=None, max_length=2000)
    cancel_url: str | None = Field(default=None, max_length=2000)


class BillingCancelIn(BaseModel):
    immediate: bool = False


class BillingCompanySlotsUpdateIn(BaseModel):
    extra_slots: int = Field(default=0, ge=0, le=1000)
