from __future__ import annotations

from datetime import UTC, datetime, time, timedelta
from typing import Any, Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.v1.platform import schemas as platform_schemas
from backend.app.api.v1.tenants import service as tenant_service
from backend.app.auth.deps import Role, UserCtx, get_current_user, require_roles
from backend.app.constants.spa_paths import (
    SETTINGS_BILLING,
    SETTINGS_BILLING_CHECKOUT_CANCEL,
    SETTINGS_BILLING_CHECKOUT_SUCCESS,
)
from backend.app.core.settings import settings
from backend.app.db.deps import get_db, get_db_with_tenant
from backend.app.models.stripe_webhook_event import StripeWebhookEventLog
from backend.app.models.tenant import Tenant, TenantLicense
from backend.app.services import founder_pricing
from backend.app.services.billing_pack_addons import (
    AUTOMATION_RULES_ENABLED_CAP,
    LEAD_CUSTOM_FIELD_DEFINITIONS_CAP,
    LEAD_FORMS_ACTIVE_CAP,
    MONTHLY_LEADS_CAP,
    merge_pack_addon_into_settings,
    pack_addon_int,
)
from backend.app.services.lead_forms_quota import count_active_tenant_lead_forms, lead_forms_base_cap
from backend.app.services.lead_quota import resolve_monthly_leads_cap
from backend.app.services import portal_candidate_usage
from backend.app.services.plan_feature_gates import plan_allows_team_tier_features
from backend.app.services.operating_company_slots import (
    extract_extra_operating_company_slots,
    get_operating_company_slots,
)
from backend.app.services.stripe_price_catalog import (
    iter_checkout_payment_skus,
    sku_pack_increment,
    sku_price_from_settings,
)
from backend.app.services.system_email import send_system_email

try:  # pragma: no cover - optional dependency
    import stripe
except Exception:  # pragma: no cover - stripe not installed yet
    stripe = None  # type: ignore[assignment]


router = APIRouter(prefix="/billing", tags=["settings-billing"], redirect_slashes=False)

PLAN_CODES: tuple[str, ...] = ("starter", "team", "pro")
CHECKOUT_OUTCOMES: tuple[str, ...] = ("success", "cancel", "error")
# Checkout mode=payment SKUs with webhook + mock apply logic (§2.16).
ADDON_PACK_CHECKOUT_READY: frozenset[str] = frozenset(
    {
        "pack_portal_candidates",
        "pack_client_portal_5",
        "pack_automation_rules_10",
        "pack_automation_rules_25",
        "pack_custom_fields_25",
        "pack_custom_fields_100",
        "pack_lead_forms_5",
        "pack_leads_500",
        "pack_active_records_2000",
        "pack_storage_50gb",
    }
)

# User-facing 400 for POST /addon-pack/checkout when SKU has no EFFECT_READY apply path or plan blocks purchase (§2.16 canon).
ADDON_PACK_CHECKOUT_UNAVAILABLE = (
    "This add-on is not available on your current plan or not yet supported."
)

# §2.16-aligned defaults (internal codes: starter=Solo, team=Team, pro=Business).
# Seat caps: per-role quotas; administrator is not seat-gated — keep non-admin totals ≈ plan seats.
PLAN_LICENSE_LIMITS: dict[str, dict[str, int]] = {
    "starter": {
        "max_recruiters": 0,
        "max_supervisors": 0,
        "max_client_managers": 0,
        "max_viewers": 0,
        "max_storage_gb": 5,
        "max_companies": 1,
        "max_candidates_active": 300,
        "max_vacancies_active": 5,
        "max_documents": 1000,
        "max_public_portal_links": 0,
    },
    "team": {
        "max_recruiters": 2,
        "max_supervisors": 1,
        "max_client_managers": 0,
        "max_viewers": 0,
        "max_storage_gb": 50,
        "max_companies": 1,
        "max_candidates_active": 2000,
        "max_vacancies_active": 50,
        "max_documents": 10000,
        "max_public_portal_links": 3,
    },
    "pro": {
        "max_recruiters": 7,
        "max_supervisors": 3,
        "max_client_managers": 0,
        "max_viewers": 0,
        "max_storage_gb": 200,
        "max_companies": 3,
        "max_candidates_active": 10000,
        "max_vacancies_active": 500,
        "max_documents": 100000,
        "max_public_portal_links": 25,
    },
}

# Seat / portal link extras merged on top of PLAN_LICENSE_LIMITS when applying plan (Stripe sync).
# Deltas are stored under tenant.settings.billing.subscription.license_addon_v1 as
# { "max_recruiters_delta": N, ... } — updated when Platform admin patches the license row.
LICENSE_ADDON_MERGE_FIELDS: tuple[str, ...] = (
    "max_recruiters",
    "max_supervisors",
    "max_client_managers",
    "max_viewers",
    "max_public_portal_links",
    "max_candidates_active",
    "max_storage_gb",
)


def build_license_addon_v1_payload(plan_code: str, license_row: TenantLicense) -> dict[str, int]:
    """Non-negative deltas vs §2.16 base for the given plan code (internal codes starter/team/pro)."""
    code = (plan_code or "").strip().lower()
    if code not in PLAN_CODES:
        code = "starter"
    base = PLAN_LICENSE_LIMITS.get(code, PLAN_LICENSE_LIMITS["starter"])
    out: dict[str, int] = {}
    for field in LICENSE_ADDON_MERGE_FIELDS:
        try:
            cur = int(getattr(license_row, field, 0) or 0)
        except (TypeError, ValueError):
            cur = 0
        b = int(base.get(field, 0))
        d = max(0, cur - b)
        if d:
            out[f"{field}_delta"] = d
    return out


def _license_addon_deltas_from_subscription(subscription: dict[str, Any]) -> dict[str, int]:
    raw = subscription.get("license_addon_v1")
    if not isinstance(raw, dict):
        return {}
    out: dict[str, int] = {}
    for field in LICENSE_ADDON_MERGE_FIELDS:
        key = f"{field}_delta"
        if key not in raw:
            continue
        try:
            out[field] = max(0, int(raw[key]))
        except (TypeError, ValueError):
            continue
    return out


async def sync_subscription_license_addon_v1(
    db: AsyncSession,
    *,
    tenant_id: str,
    license_row: TenantLicense,
) -> None:
    """Write license_addon_v1 into billing subscription JSON from absolute TenantLicense caps (Platform / support)."""
    tenant = await db.get(Tenant, tenant_id)
    if tenant is None:
        return
    plan_code = str(license_row.plan or "starter").strip().lower()
    addon_block = build_license_addon_v1_payload(plan_code, license_row)
    settings_payload = dict(tenant.settings or {})
    billing = dict(settings_payload.get("billing") or {})
    sub = dict(billing.get("subscription") or {})
    if addon_block:
        sub["license_addon_v1"] = addon_block
    else:
        sub.pop("license_addon_v1", None)
    billing["subscription"] = sub
    settings_payload["billing"] = billing
    tenant.settings = settings_payload
    tenant.updated_at = _now_utc()
    await db.commit()


class BillingUsageCapsOut(BaseModel):
    """Display caps for billing usage rows; 0 means unlimited (same convention as seat limits)."""

    max_leads_created_per_month: int = 0
    max_candidates_active: int = 0
    max_vacancies_active: int = 0
    max_documents: int = 0
    max_public_portal_links: int = 0


def _plan_code_for_usage_caps(subscription: dict[str, Any], license_entry: TenantLicense | None) -> str:
    status = str(subscription.get("status") or "").strip().lower()
    if status == "trial":
        return "starter"
    raw = str(subscription.get("plan_code") or "").strip().lower()
    if raw in PLAN_CODES:
        return raw
    if license_entry is not None:
        lic = str(getattr(license_entry, "plan", None) or "").strip().lower()
        if lic in PLAN_CODES:
            return lic
    return "starter"


def _tenant_settings_dict(tenant: Tenant | None) -> dict[str, Any] | None:
    if tenant is None:
        return None
    s = tenant.settings
    return dict(s) if isinstance(s, dict) else None


def _billing_usage_caps(
    license_entry: TenantLicense | None,
    subscription: dict[str, Any],
    tenant_settings: dict[str, Any] | None = None,
) -> BillingUsageCapsOut:
    plan = _plan_code_for_usage_caps(subscription, license_entry)
    defaults = PLAN_LICENSE_LIMITS.get(plan, PLAN_LICENSE_LIMITS["starter"])

    def _lim(field: str) -> int:
        if license_entry is not None:
            v = getattr(license_entry, field, None)
            if v is not None:
                return int(v)
        return int(defaults.get(field, 0))

    max_leads = resolve_monthly_leads_cap(subscription, license_entry, tenant_settings)
    return BillingUsageCapsOut(
        max_leads_created_per_month=max_leads,
        max_candidates_active=_lim("max_candidates_active"),
        max_vacancies_active=_lim("max_vacancies_active"),
        max_documents=_lim("max_documents"),
        max_public_portal_links=_lim("max_public_portal_links"),
    )


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


def _addon_purchase_plan_ok_for_offer(sku: str, pc_plan: str) -> tuple[bool, str | None]:
    """Plan gates for EFFECT_READY SKUs; non-ready SKUs return (True, None)."""
    if sku not in ADDON_PACK_CHECKOUT_READY:
        return True, None
    if sku == "pack_lead_forms_5":
        # Solo/starter has a finite base cap; pack extends any paid tier (not Team-gated).
        return True, None
    if sku == "pack_portal_candidates":
        if portal_candidate_usage.monthly_cap_for_plan_code(pc_plan) is None:
            return False, "portal_pack_requires_team_tier"
        return True, None
    if sku in ("pack_custom_fields_25", "pack_custom_fields_100"):
        if plan_allows_team_tier_features(pc_plan):
            return False, "custom_fields_not_on_team_plan"
        return True, None
    if not plan_allows_team_tier_features(pc_plan):
        return False, "requires_team_tier"
    return True, None


def _addon_checkout_offers_for_plan(pc_plan: str) -> list[BillingAddonCheckoutOfferOut]:
    out: list[BillingAddonCheckoutOfferOut] = []
    for spec in iter_checkout_payment_skus():
        pid = sku_price_from_settings(settings, spec.key)
        inc = sku_pack_increment(settings, spec.key)
        configured = bool(pid)
        effect_ready = spec.key in ADDON_PACK_CHECKOUT_READY
        plan_ok, plan_reason = _addon_purchase_plan_ok_for_offer(spec.key, pc_plan)
        stripe_ok = configured or not _stripe_ready()
        purchase_allowed = bool(effect_ready and plan_ok and stripe_ok)
        block_reason: str | None = None
        if not effect_ready:
            block_reason = "not_effect_ready"
        elif not plan_ok:
            block_reason = plan_reason or "plan_blocked"
        elif not stripe_ok:
            block_reason = "stripe_price_not_configured"
        out.append(
            BillingAddonCheckoutOfferOut(
                sku=spec.key,
                label=spec.ssot_note,
                configured=configured,
                pack_increment=inc,
                effect_ready=effect_ready,
                checkout_ready=effect_ready,
                purchase_allowed=purchase_allowed,
                purchase_block_reason=None if purchase_allowed else block_reason,
            )
        )
    return out


def _billing_summary_addon_offers(
    license_entry: TenantLicense | None,
    subscription: dict[str, Any],
) -> list[BillingAddonCheckoutOfferOut]:
    pc = _plan_code_for_usage_caps(subscription, license_entry)
    return _addon_checkout_offers_for_plan(pc)


class BillingSummaryOut(BaseModel):
    subscription: BillingSubscriptionOut
    license: platform_schemas.TenantLicenseOut | None = None
    usage: platform_schemas.TenantUsageOut
    usage_caps: BillingUsageCapsOut
    company_slots: BillingCompanySlotsOut | None = None
    portal_candidates: BillingPortalCandidatesUsageOut | None = None
    founder_program: BillingFounderProgramOut | None = None
    lead_forms: BillingLeadFormsUsageOut | None = None
    available_plans: list[BillingPlanOut]
    history: list[BillingHistoryItemOut] = []
    invoices: list[BillingInvoiceOut] = []
    addon_checkout_offers: list[BillingAddonCheckoutOfferOut] = Field(default_factory=list)


async def _company_slots_payload(
    db: AsyncSession,
    *,
    tenant: Tenant,
    license_entry: TenantLicense | None,
) -> BillingCompanySlotsOut:
    slots = await get_operating_company_slots(
        db,
        str(tenant.id),
        preloaded_tenant=tenant,
        preloaded_license=license_entry,
    )
    return BillingCompanySlotsOut(
        included_limit=int(slots.included_limit),
        extra_slots=int(slots.extra_slots),
        effective_limit=int(slots.effective_limit),
        used=int(slots.used),
        available=int(slots.available),
        unlimited=bool(slots.unlimited),
    )


def _portal_candidates_usage_snapshot(
    tenant: Tenant,
    *,
    plan_for_caps: str,
    now_utc: datetime,
) -> BillingPortalCandidatesUsageOut | None:
    base_cap = portal_candidate_usage.monthly_cap_for_plan_code(plan_for_caps)
    if base_cap is None:
        return None
    settings_dict = tenant.settings if isinstance(tenant.settings, dict) else {}
    addon = portal_candidate_usage.portal_monthly_cap_addon(settings_dict)
    cap = base_cap + addon
    used = portal_candidate_usage.count_for_utc_month(settings_dict, at_utc=now_utc)
    warn: Literal["none", "warn_80", "warn_100"] = "none"
    if cap > 0:
        if used >= cap:
            warn = "warn_100"
        elif used >= int(cap * 0.8):
            warn = "warn_80"
    return BillingPortalCandidatesUsageOut(
        used_this_month_utc=used,
        cap=cap,
        base_cap=base_cap,
        pack_addon=addon,
        pack_increment_offer=int(settings.portal_candidates_pack_increment),
        soft_limit=False,
        warning_level=warn,
    )


def _founder_program_snapshot(tenant: Tenant) -> BillingFounderProgramOut:
    st = tenant.settings if isinstance(tenant.settings, dict) else {}
    bill = st.get("billing")
    if not isinstance(bill, dict):
        return BillingFounderProgramOut()
    fp = bill.get("founder_pricing_v1")
    if not isinstance(fp, dict):
        return BillingFounderProgramOut()
    return BillingFounderProgramOut(
        tenant_enrolled=bool(fp.get("enrolled")),
        tenant_revoked=bool(fp.get("revoked")),
    )


async def _billing_summary_extras(
    db: AsyncSession,
    tenant: Tenant,
    license_entry: TenantLicense | None,
    sub_payload: dict[str, Any],
) -> tuple[BillingPortalCandidatesUsageOut | None, BillingFounderProgramOut, BillingLeadFormsUsageOut]:
    now = _now_utc()
    pc_plan = _plan_code_for_usage_caps(sub_payload, license_entry)
    portal = _portal_candidates_usage_snapshot(tenant, plan_for_caps=pc_plan, now_utc=now)
    founder = _founder_program_snapshot(tenant)
    st = _tenant_settings_dict(tenant)
    base_lf = lead_forms_base_cap(pc_plan)
    addon_lf = pack_addon_int(st, LEAD_FORMS_ACTIVE_CAP)
    used_lf = await count_active_tenant_lead_forms(db, str(tenant.id))
    lead_forms = BillingLeadFormsUsageOut(
        active_count=used_lf,
        cap=base_lf + addon_lf,
        base_cap=base_lf,
        pack_addon=addon_lf,
        pack_increment_offer=max(1, int(getattr(settings, "lead_forms_pack_increment", 5) or 5)),
    )
    return portal, founder, lead_forms


async def _maybe_enroll_founder_program(db: AsyncSession, tenant_id: str, plan_code: str) -> None:
    tenant = await db.get(Tenant, tenant_id)
    if tenant is None:
        return
    ok = await founder_pricing.try_enroll_if_slot_available(
        db,
        tenant,
        plan_code=_normalize_plan_code(plan_code),
    )
    if ok:
        await db.commit()
        await db.refresh(tenant)


class BillingChangePlanIn(BaseModel):
    plan_code: str = Field(..., min_length=2, max_length=32)
    billing_interval: Literal["month", "year"] | None = None
    success_url: str | None = Field(default=None, max_length=2000)
    cancel_url: str | None = Field(default=None, max_length=2000)


class BillingCancelIn(BaseModel):
    immediate: bool = False


class BillingCompanySlotsUpdateIn(BaseModel):
    extra_slots: int = Field(default=0, ge=0, le=1000)


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


def _plan_stripe_yearly_price_id_only(plan_code: str) -> str | None:
    """Yearly Stripe Price id only (no fallback to monthly)."""
    yearly_attr = {
        "starter": "stripe_price_starter_yearly",
        "team": "stripe_price_team_yearly",
        "pro": "stripe_price_pro_yearly",
    }
    ykey = yearly_attr.get(plan_code)
    if not ykey:
        return None
    return (getattr(settings, ykey, None) or "").strip() or None


def _plan_stripe_price_id(plan_code: str, interval: str = "month") -> str | None:
    """Resolve Stripe Price id for plan + billing interval (monthly default; yearly falls back to monthly if unset)."""
    iv = (interval or "month").strip().lower()
    if iv not in ("month", "year"):
        iv = "month"
    monthly_attr = {
        "starter": "stripe_price_starter",
        "team": "stripe_price_team",
        "pro": "stripe_price_pro",
    }
    mkey = monthly_attr.get(plan_code)
    if not mkey:
        return None
    if iv == "year":
        yid = _plan_stripe_yearly_price_id_only(plan_code)
        if yid:
            return yid
    return (getattr(settings, mkey, None) or "").strip() or None


def _plan_price_id(plan_code: str) -> str | None:
    """Backward-compatible alias: monthly Stripe price."""
    return _plan_stripe_price_id(plan_code, "month")


def _all_operating_slot_addon_price_ids() -> list[str]:
    out: list[str] = []
    for raw in (
        settings.stripe_price_operating_company_slot_team,
        settings.stripe_price_operating_company_slot_business,
        settings.stripe_price_operating_company_slot,
    ):
        s = (raw or "").strip()
        if s and s not in out:
            out.append(s)
    return out


def _operating_slot_addon_price_id_for_plan(plan_code: str) -> str | None:
    pc = _normalize_plan_code(plan_code)
    if pc == "team":
        s = (settings.stripe_price_operating_company_slot_team or "").strip()
        if s:
            return s
    if pc == "pro":
        s = (settings.stripe_price_operating_company_slot_business or "").strip()
        if s:
            return s
    return (settings.stripe_price_operating_company_slot or "").strip() or None


def _portal_candidates_pack_price_id() -> str | None:
    return (settings.stripe_price_portal_candidates_pack or "").strip() or None


def _set_extra_operating_slots(payload: dict[str, Any], extra_slots: int) -> dict[str, Any]:
    value = max(0, int(extra_slots or 0))
    updated = dict(payload)
    updated["extra_operating_company_slots"] = value
    for legacy_key in ("additional_operating_company_slots", "operating_company_addon_slots"):
        if legacy_key in updated:
            del updated[legacy_key]
    return updated


def _plan_code_by_price_id(price_id: str | None) -> str | None:
    pid = (price_id or "").strip()
    if not pid:
        return None
    for code in PLAN_CODES:
        for interval in ("month", "year"):
            configured = _plan_stripe_price_id(code, interval)
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


def _subscription_out(tenant: Tenant, *, license_entry: TenantLicense | None = None) -> BillingSubscriptionOut:
    payload = _subscription_payload(tenant)
    provider = "stripe" if str(payload.get("provider") or "").strip().lower() == "stripe" else "mock"
    plan_code = str(payload.get("plan_code") or "starter").strip().lower()
    if plan_code not in PLAN_CODES:
        plan_code = "starter"
    trial_ends_at = _iso_to_dt(payload.get("trial_ends_at"))
    if trial_ends_at is None and license_entry is not None:
        lp = str(license_entry.plan or "").strip().lower()
        exp = license_entry.expires_at
        if lp == "trial" and exp is not None:
            trial_ends_at = datetime.combine(exp, time(23, 59, 59, tzinfo=UTC))
    bi_raw = str(payload.get("billing_interval") or "").strip().lower()
    billing_interval: Literal["month", "year"] | None
    if bi_raw == "year":
        billing_interval = "year"
    elif bi_raw == "month":
        billing_interval = "month"
    else:
        billing_interval = None
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
        billing_interval=billing_interval,
        current_period_start=_iso_to_dt(payload.get("current_period_start")),
        current_period_end=_iso_to_dt(payload.get("current_period_end")),
        activated_at=_iso_to_dt(payload.get("activated_at")),
        trial_ends_at=trial_ends_at,
        cancel_at_period_end=bool(payload.get("cancel_at_period_end")),
        canceled_at=_iso_to_dt(payload.get("canceled_at")),
        updated_at=_iso_to_dt(payload.get("updated_at")),
    )


def _available_plans() -> list[BillingPlanOut]:
    # monthly_price_usd: legacy key — whole EUR units (§2.16 list prices), not USD.
    display_names = {"starter": "Solo", "team": "Team", "pro": "Business"}
    catalog = {"starter": (29, 24), "team": (129, 109), "pro": (249, 219)}
    out: list[BillingPlanOut] = []
    for code in PLAN_CODES:
        month_id = _plan_stripe_price_id(code, "month")
        year_explicit = _plan_stripe_yearly_price_id_only(code)
        out.append(
            BillingPlanOut(
                code=code,
                name=display_names.get(code, code.capitalize()),
                currency="EUR",
                monthly_price_usd=int(catalog.get(code, (0, 0))[0]),
                yearly_equivalent_monthly_eur=int(catalog.get(code, (0, 0))[1]),
                limits=PLAN_LICENSE_LIMITS.get(code, {}),
                stripe_month_configured=bool(month_id),
                stripe_year_configured=bool(year_explicit),
            )
        )
    return out


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
    settings_payload = founder_pricing.apply_stripe_status_to_settings(
        settings_payload,
        str(payload.get("status") or "").strip().lower(),
        now_utc=_now_utc(),
    )
    tenant.settings = settings_payload
    tenant.updated_at = _now_utc()
    await db.commit()
    await db.refresh(tenant)
    return _subscription_out(tenant)


async def _apply_portal_candidates_pack_to_tenant(
    db: AsyncSession,
    tenant: Tenant,
    *,
    increment: int,
    history_title: str,
    history_description: str,
    dedupe_key: str,
    plan_code: str | None = None,
    history_source: Literal["app", "stripe"] = "stripe",
) -> None:
    if _history_contains(tenant, dedupe_key):
        return
    st = dict(tenant.settings or {})
    st = portal_candidate_usage.merge_increment_portal_monthly_cap_addon(st, increment)
    billing = dict(st.get("billing") or {})
    history = billing.get("history")
    history_list = [dict(item) for item in history] if isinstance(history, list) else []
    history_list.insert(
        0,
        _history_entry(
            event_type="portal_candidates.pack_purchased",
            status="success",
            title=history_title,
            description=history_description,
            source=history_source,
            plan_code=plan_code,
            dedupe_key=dedupe_key,
        ),
    )
    billing["history"] = history_list[:40]
    st["billing"] = billing
    tenant.settings = st
    tenant.updated_at = _now_utc()
    await db.commit()
    await db.refresh(tenant)


async def _apply_client_portal_pack_5_to_tenant(
    db: AsyncSession,
    tenant: Tenant,
    *,
    dedupe_key: str,
    plan_code: str | None = None,
    history_source: Literal["app", "stripe"] = "stripe",
) -> None:
    if _history_contains(tenant, dedupe_key):
        return
    tenant_id = str(tenant.id)
    license_row = (
        await db.execute(select(TenantLicense).where(TenantLicense.tenant_id == tenant_id).limit(1))
    ).scalar_one_or_none()
    if license_row is None:
        license_row = TenantLicense(tenant_id=tenant_id, plan="team", auto_renew=True, notes="billing-managed")
        db.add(license_row)
        await db.flush()
    license_row.max_public_portal_links = int(getattr(license_row, "max_public_portal_links", 0) or 0) + 5
    await db.commit()
    await db.refresh(license_row)
    await sync_subscription_license_addon_v1(db, tenant_id=tenant_id, license_row=license_row)
    tenant = await db.get(Tenant, tenant_id)
    if tenant is None:
        return
    st = dict(tenant.settings or {})
    billing = dict(st.get("billing") or {})
    history = billing.get("history")
    history_list = [dict(item) for item in history] if isinstance(history, list) else []
    history_list.insert(
        0,
        _history_entry(
            event_type="addon_pack.purchased",
            status="success",
            title="Client portal pack purchased",
            description="+5 client portal link slots (add-on).",
            source=history_source,
            plan_code=plan_code,
            dedupe_key=dedupe_key,
        ),
    )
    billing["history"] = history_list[:40]
    st["billing"] = billing
    tenant.settings = st
    tenant.updated_at = _now_utc()
    await db.commit()
    await db.refresh(tenant)


async def _apply_pack_addon_to_tenant(
    db: AsyncSession,
    tenant: Tenant,
    *,
    field: str,
    increment: int,
    history_title: str,
    history_description: str,
    dedupe_key: str,
    plan_code: str | None = None,
    history_source: Literal["app", "stripe"] = "stripe",
) -> None:
    if _history_contains(tenant, dedupe_key):
        return
    st = dict(tenant.settings or {})
    st = merge_pack_addon_into_settings(st, field, int(increment))
    billing = dict(st.get("billing") or {})
    history = billing.get("history")
    history_list = [dict(item) for item in history] if isinstance(history, list) else []
    history_list.insert(
        0,
        _history_entry(
            event_type="addon_pack.purchased",
            status="success",
            title=history_title,
            description=history_description,
            source=history_source,
            plan_code=plan_code,
            dedupe_key=dedupe_key,
        ),
    )
    billing["history"] = history_list[:40]
    st["billing"] = billing
    tenant.settings = st
    tenant.updated_at = _now_utc()
    await db.commit()
    await db.refresh(tenant)


async def _apply_license_numeric_pack_to_tenant(
    db: AsyncSession,
    tenant: Tenant,
    *,
    attr_name: str,
    increment: int,
    history_title: str,
    history_description: str,
    dedupe_key: str,
    plan_code: str | None = None,
    history_source: Literal["app", "stripe"] = "stripe",
) -> None:
    if _history_contains(tenant, dedupe_key):
        return
    tenant_id = str(tenant.id)
    license_row = (
        await db.execute(select(TenantLicense).where(TenantLicense.tenant_id == tenant_id).limit(1))
    ).scalar_one_or_none()
    if license_row is None:
        license_row = TenantLicense(tenant_id=tenant_id, plan="team", auto_renew=True, notes="billing-managed")
        db.add(license_row)
        await db.flush()
    cur = int(getattr(license_row, attr_name, 0) or 0)
    setattr(license_row, attr_name, cur + max(0, int(increment)))
    await db.commit()
    await db.refresh(license_row)
    await sync_subscription_license_addon_v1(db, tenant_id=tenant_id, license_row=license_row)
    tenant = await db.get(Tenant, tenant_id)
    if tenant is None:
        return
    st = dict(tenant.settings or {})
    billing = dict(st.get("billing") or {})
    history = billing.get("history")
    history_list = [dict(item) for item in history] if isinstance(history, list) else []
    history_list.insert(
        0,
        _history_entry(
            event_type="addon_pack.purchased",
            status="success",
            title=history_title,
            description=history_description,
            source=history_source,
            plan_code=plan_code,
            dedupe_key=dedupe_key,
        ),
    )
    billing["history"] = history_list[:40]
    st["billing"] = billing
    tenant.settings = st
    tenant.updated_at = _now_utc()
    await db.commit()
    await db.refresh(tenant)


async def _apply_addon_pack_by_sku(
    db: AsyncSession,
    tenant: Tenant,
    *,
    sku: str,
    increment: int,
    dedupe_key: str,
    plan_code: str | None,
    history_source: Literal["app", "stripe"],
) -> None:
    if sku == "pack_portal_candidates":
        await _apply_portal_candidates_pack_to_tenant(
            db,
            tenant,
            increment=int(increment),
            history_title="Candidate portal pack purchased",
            history_description=f"+{increment} active portal candidates / month (add-on).",
            dedupe_key=dedupe_key,
            plan_code=plan_code,
            history_source=history_source,
        )
        return
    if sku == "pack_client_portal_5":
        await _apply_client_portal_pack_5_to_tenant(
            db,
            tenant,
            dedupe_key=dedupe_key,
            plan_code=plan_code,
            history_source=history_source,
        )
        return
    if sku == "pack_leads_500":
        await _apply_pack_addon_to_tenant(
            db,
            tenant,
            field=MONTHLY_LEADS_CAP,
            increment=int(increment),
            history_title="Leads pack purchased",
            history_description=f"+{increment} inbound leads / month (add-on).",
            dedupe_key=dedupe_key,
            plan_code=plan_code,
            history_source=history_source,
        )
        return
    if sku in ("pack_automation_rules_10", "pack_automation_rules_25"):
        await _apply_pack_addon_to_tenant(
            db,
            tenant,
            field=AUTOMATION_RULES_ENABLED_CAP,
            increment=int(increment),
            history_title="Automation rules pack purchased",
            history_description=f"+{increment} enabled automation rules capacity (add-on).",
            dedupe_key=dedupe_key,
            plan_code=plan_code,
            history_source=history_source,
        )
        return
    if sku in ("pack_custom_fields_25", "pack_custom_fields_100"):
        await _apply_pack_addon_to_tenant(
            db,
            tenant,
            field=LEAD_CUSTOM_FIELD_DEFINITIONS_CAP,
            increment=int(increment),
            history_title="Lead custom fields pack purchased",
            history_description=f"+{increment} lead custom field definitions on starter-tier cap (add-on).",
            dedupe_key=dedupe_key,
            plan_code=plan_code,
            history_source=history_source,
        )
        return
    if sku == "pack_active_records_2000":
        await _apply_license_numeric_pack_to_tenant(
            db,
            tenant,
            attr_name="max_candidates_active",
            increment=int(increment),
            history_title="Active records pack purchased",
            history_description=f"+{increment} active candidate records (add-on).",
            dedupe_key=dedupe_key,
            plan_code=plan_code,
            history_source=history_source,
        )
        return
    if sku == "pack_storage_50gb":
        await _apply_license_numeric_pack_to_tenant(
            db,
            tenant,
            attr_name="max_storage_gb",
            increment=int(increment),
            history_title="Storage pack purchased",
            history_description=f"+{increment} GB storage (add-on).",
            dedupe_key=dedupe_key,
            plan_code=plan_code,
            history_source=history_source,
        )
        return
    if sku == "pack_lead_forms_5":
        await _apply_pack_addon_to_tenant(
            db,
            tenant,
            field=LEAD_FORMS_ACTIVE_CAP,
            increment=int(increment),
            history_title="Lead forms pack purchased",
            history_description=f"+{increment} active lead form slots (add-on).",
            dedupe_key=dedupe_key,
            plan_code=plan_code,
            history_source=history_source,
        )
        return
    raise ValueError(f"Add-on SKU apply not implemented: {sku}")


def _checkout_session_line_items_contain_price(session_full: dict[str, Any], expected_price_id: str) -> bool:
    exp = (expected_price_id or "").strip()
    if not exp:
        return False
    li_container = session_full.get("line_items") if isinstance(session_full.get("line_items"), dict) else {}
    lines = li_container.get("data") if isinstance(li_container.get("data"), list) else []
    for line in lines:
        if not isinstance(line, dict):
            continue
        price_obj = line.get("price")
        if isinstance(price_obj, dict):
            pid = str(price_obj.get("id") or "").strip()
            if pid == exp:
                return True
    return False


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
    tenant = await db.get(Tenant, tenant_id)
    if tenant is None:
        return
    license_row = (
        await db.execute(select(TenantLicense).where(TenantLicense.tenant_id == tenant_id).limit(1))
    ).scalar_one_or_none()
    prev_plan = str(license_row.plan or "").strip().lower() if license_row else ""
    plan_changed = bool(prev_plan) and prev_plan != plan_code
    subscription = _subscription_payload(tenant)
    addon_by_field: dict[str, int] = {} if plan_changed else _license_addon_deltas_from_subscription(subscription)

    if license_row is None:
        license_row = TenantLicense(tenant_id=tenant_id, plan=plan_code, auto_renew=True, notes="billing-managed")
        db.add(license_row)
    license_row.plan = plan_code
    license_row.auto_renew = True
    license_row.expires_at = (_now_utc() + timedelta(days=30)).date()
    for field, value in limits.items():
        base_v = int(value)
        if field in LICENSE_ADDON_MERGE_FIELDS:
            delta = int(addon_by_field.get(field, 0))
            setattr(license_row, field, base_v + delta)
        else:
            setattr(license_row, field, base_v)
    await db.commit()
    await db.refresh(license_row)
    if plan_changed:
        await sync_subscription_license_addon_v1(db, tenant_id=tenant_id, license_row=license_row)


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

    stripe.api_key = settings.stripe_secret_key
    try:
        full = _stripe_obj_to_dict(
            stripe.checkout.Session.retrieve(session_id, expand=["line_items.data.price"])  # type: ignore[union-attr]
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

    stripe.api_key = settings.stripe_secret_key
    try:
        full = _stripe_obj_to_dict(
            stripe.checkout.Session.retrieve(session_id, expand=["line_items.data.price"])  # type: ignore[union-attr]
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
        stripe.api_key = settings.stripe_secret_key
        sub = _stripe_obj_to_dict(
            stripe.Subscription.retrieve(subscription_id, expand=["items.data.price"])  # type: ignore[union-attr]
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
            stripe.api_key = settings.stripe_secret_key
            try:
                sub_obj = _stripe_obj_to_dict(stripe.Subscription.retrieve(subscription_id_raw, expand=["items.data.price"]))  # type: ignore[union-attr]
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


async def _stripe_webhook_event_already_processed(db: AsyncSession, event_id: str) -> bool:
    eid = (event_id or "").strip()
    if not eid:
        return False
    row = (
        await db.execute(select(StripeWebhookEventLog.event_id).where(StripeWebhookEventLog.event_id == eid).limit(1))
    ).scalar_one_or_none()
    return row is not None


async def _stripe_webhook_event_record_processed(db: AsyncSession, event_id: str, event_type: str) -> None:
    eid = (event_id or "").strip()
    if not eid:
        return
    db.add(
        StripeWebhookEventLog(
            event_id=eid[:255],
            event_type=(event_type or "")[:128],
        )
    )
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()


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
    license_entry = await tenant_service.get_tenant_license(db, tenant_id)
    return _subscription_out(tenant, license_entry=license_entry)


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
        company_slots=company_slots,
        portal_candidates=portal_candidates,
        founder_program=founder_program,
        lead_forms=lead_forms,
        available_plans=_available_plans(),
        history=history,
        invoices=invoices,
        addon_checkout_offers=_billing_summary_addon_offers(license_entry, sub_payload),
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
        stripe.api_key = settings.stripe_secret_key
        checkout = stripe.checkout.Session.create(  # type: ignore[union-attr]
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
    dependencies=[Depends(require_roles(Role.administrator))],
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
        stripe.api_key = settings.stripe_secret_key
        checkout = stripe.checkout.Session.create(  # type: ignore[union-attr]
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
    dependencies=[Depends(require_roles(Role.administrator))],
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
        stripe.api_key = settings.stripe_secret_key
        checkout = stripe.checkout.Session.create(  # type: ignore[union-attr]
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
    req_iv_from_payload: Literal["month", "year"] | None = None
    if payload.billing_interval is not None:
        r = str(payload.billing_interval).strip().lower()
        if r in ("month", "year"):
            req_iv_from_payload = r  # type: ignore[assignment]
    provider = str(current.get("provider") or "").strip().lower()
    subscription_id = str(current.get("subscription_id") or "").strip()
    customer_id = str(current.get("customer_id") or "").strip()
    if _stripe_ready() and provider == "stripe" and subscription_id and customer_id:
        stripe.api_key = settings.stripe_secret_key
        sub = _stripe_obj_to_dict(
            stripe.Subscription.retrieve(subscription_id, expand=["latest_invoice", "items.data.price"])  # type: ignore[union-attr]
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
                updated_stripe = _stripe_obj_to_dict(stripe.Subscription.modify(  # type: ignore[union-attr]
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
                success_url = (payload.success_url or "").strip() or SETTINGS_BILLING_CHECKOUT_SUCCESS
                cancel_url = (payload.cancel_url or "").strip() or SETTINGS_BILLING_CHECKOUT_CANCEL
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
                updated_stripe = _stripe_obj_to_dict(stripe.Subscription.modify(  # type: ignore[union-attr]
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
    dependencies=[Depends(require_roles(Role.administrator))],
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
        stripe.api_key = settings.stripe_secret_key
        try:
            stripe_sub = _stripe_obj_to_dict(stripe.Subscription.retrieve(subscription_id, expand=["items.data.price"]))  # type: ignore[union-attr]
            existing_addon_item, existing_price_id = _find_operating_slot_addon_item(stripe_sub)
            item_id = str((existing_addon_item or {}).get("id") or "").strip()
            if new_extra_slots <= 0 and item_id:
                updated_stripe = _stripe_obj_to_dict(
                    stripe.Subscription.modify(  # type: ignore[union-attr]
                        subscription_id,
                        items=[{"id": item_id, "deleted": True}],
                    )
                )
                await _handle_subscription_event(db, updated_stripe, deleted=False)
            elif new_extra_slots > 0 and item_id and existing_price_id == addon_price_id:
                updated_stripe = _stripe_obj_to_dict(
                    stripe.Subscription.modify(  # type: ignore[union-attr]
                        subscription_id,
                        items=[{"id": item_id, "quantity": new_extra_slots}],
                    )
                )
                await _handle_subscription_event(db, updated_stripe, deleted=False)
            elif new_extra_slots > 0 and item_id and existing_price_id and existing_price_id != addon_price_id:
                updated_stripe = _stripe_obj_to_dict(
                    stripe.Subscription.modify(  # type: ignore[union-attr]
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
                    stripe.Subscription.modify(  # type: ignore[union-attr]
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
    return_url = (settings.stripe_portal_return_url or "").strip() or SETTINGS_BILLING
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

    event_id = str(getattr(event, "id", "") or "").strip()
    if not event_id and hasattr(event, "to_dict"):
        ev_dict = event.to_dict()  # type: ignore[union-attr]
        if isinstance(ev_dict, dict):
            event_id = str(ev_dict.get("id") or "").strip()

    event_type = str(getattr(event, "type", "") or "")
    if event_id and await _stripe_webhook_event_already_processed(db, event_id):
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

    if event_type == "checkout.session.completed":
        detail = await _handle_checkout_completed(db, obj)
    elif event_type in ("invoice.paid", "invoice.payment_succeeded"):
        detail = await _handle_invoice_paid(db, obj)
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

    if event_id:
        await _stripe_webhook_event_record_processed(db, event_id, event_type)

    return BillingWebhookOut(accepted=True, detail=detail)
