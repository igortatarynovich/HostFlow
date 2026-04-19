"""Plan-config + Stripe price-ID resolvers + addon-offer logic.

Extracted from ``backend/app/api/v1/settings/billing/__init__.py`` as part
of the Phase 1 god-module split (step 2/N).

Contents:

* **Constants** — ``PLAN_CODES`` / ``PLAN_LICENSE_LIMITS`` / ``LICENSE_ADDON_MERGE_FIELDS``,
  ``CHECKOUT_OUTCOMES``, ``ADDON_PACK_CHECKOUT_READY``, ``ADDON_PACK_CHECKOUT_UNAVAILABLE``.
* **License-addon math** — ``build_license_addon_v1_payload``,
  ``_license_addon_deltas_from_subscription``.
* **Plan validation** — ``_normalize_plan_code`` (raises 422 on unknown plan).
* **Stripe price-ID resolvers** — ``_plan_stripe_*``, ``_all_operating_slot_addon_price_ids``,
  ``_operating_slot_addon_price_id_for_plan``, ``_portal_candidates_pack_price_id``,
  ``_plan_code_by_price_id``.
* **Stripe runtime probes** — ``_stripe_ready``, ``_stripe_obj_to_dict``,
  ``_stripe_price_amount``.
* **Pricing math** — ``_calculate_proration_amount_minor``.
* **Plan catalog** — ``_available_plans`` (used by ``GET /summary``).
* **Add-on offers** — ``_addon_purchase_plan_ok_for_offer``,
  ``_addon_checkout_offers_for_plan`` (used by ``GET /summary`` and
  ``POST /addon-pack/checkout``).

Pure module — no DB or HTTP dependencies beyond ``HTTPException`` for plan
validation. Imports only ``settings``, the ``stripe`` SDK (optional), the
shared SKU catalog services, and the relevant Pydantic schemas.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import HTTPException, status

from backend.app.core.settings import settings
from backend.app.models.tenant import TenantLicense
from backend.app.services import portal_candidate_usage
from backend.app.services.plan_feature_gates import plan_allows_team_tier_features
from backend.app.services.stripe_price_catalog import (
    iter_checkout_payment_skus,
    sku_pack_increment,
    sku_price_from_settings,
)

from ..schemas import BillingAddonCheckoutOfferOut, BillingPlanOut


PLAN_CODES: tuple[str, ...] = ("starter", "team", "pro")


CHECKOUT_OUTCOMES: tuple[str, ...] = ("success", "cancel", "error")


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


ADDON_PACK_CHECKOUT_UNAVAILABLE = (
    "This add-on is not available on your current plan or not yet supported."
)


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


def _normalize_plan_code(raw: str) -> str:
    plan = (raw or "").strip().lower()
    if plan not in PLAN_CODES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unsupported plan_code: {plan or raw}",
        )
    return plan


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
    # Late-import the parent package's ``stripe`` attribute so test-time patches
    # of ``billing.stripe`` (e.g. via ``patch.object(billing, "stripe", ...)``)
    # propagate here without us holding a stale module reference.
    from backend.app.api.v1.settings import billing as _billing_pkg
    stripe_mod = _billing_pkg.stripe
    stripe_mod.api_key = settings.stripe_secret_key
    try:
        price = _stripe_obj_to_dict(stripe_mod.Price.retrieve(pid))
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
    # Late-import the parent package's ``stripe`` attribute so test-time patches
    # of ``billing.stripe`` (e.g. via ``patch.object(billing, "stripe", ...)``)
    # propagate here without us holding a stale module reference.
    from backend.app.api.v1.settings import billing as _billing_pkg
    return bool((settings.stripe_secret_key or "").strip()) and _billing_pkg.stripe is not None


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
