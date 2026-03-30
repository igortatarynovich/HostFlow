"""Stripe Price matrix aligned with docs/SSOT.md §2.16 (EUR, v1).

Each SKU maps to a field on ``backend.app.core.settings.Settings`` (env: same name
SCREAMING_SNAKE_CASE). Create matching **Products / Prices** in Stripe Dashboard, then
paste **Price IDs** (``price_...``) into environment.

**Modes**
- ``subscription_base`` — primary plan (Checkout ``mode=subscription``, one line item).
- ``subscription_addon_quantity`` — same subscription, **quantity** = units (seats, slots, …).
- ``checkout_payment`` — Checkout ``mode=payment`` (packs) or separate invoice; webhook applies add-on.

Operational code paths today: base plans, operating company slots (subscription add-on),
candidate portal pack (payment checkout). Other SKUs may exist in this catalog (**STRIPE_CATALOG**)
before they are **EFFECT_READY**; only the latter set is listed in ``ADDON_PACK_CHECKOUT_READY``
in ``billing.py`` (see **§2.16** «Жизненный цикл SKU add-on checkout»).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

BillingMode = Literal["subscription_base", "subscription_addon_quantity", "checkout_payment"]


@dataclass(frozen=True)
class StripePriceSKU:
    """One sellable unit in Stripe."""

    key: str
    env_var: str
    settings_attr: str
    mode: BillingMode
    ssot_note: str


# Order: base plans → workspace → seats → portals → automation → fields → leads/forms/channels
# → overage packs → founder (optional separate products in Stripe; amounts enforced in app).
STRIPE_PRICE_SKUS: tuple[StripePriceSKU, ...] = (
    StripePriceSKU(
        "plan_starter_monthly",
        "STRIPE_PRICE_STARTER",
        "stripe_price_starter",
        "subscription_base",
        "Solo €29/mo (internal plan_code starter)",
    ),
    StripePriceSKU(
        "plan_starter_yearly",
        "STRIPE_PRICE_STARTER_YEARLY",
        "stripe_price_starter_yearly",
        "subscription_base",
        "Solo yearly (€24/mo equivalent billed annually)",
    ),
    StripePriceSKU(
        "plan_team_monthly",
        "STRIPE_PRICE_TEAM",
        "stripe_price_team",
        "subscription_base",
        "Team €129/mo",
    ),
    StripePriceSKU(
        "plan_team_yearly",
        "STRIPE_PRICE_TEAM_YEARLY",
        "stripe_price_team_yearly",
        "subscription_base",
        "Team yearly (€109/mo equivalent)",
    ),
    StripePriceSKU(
        "plan_business_monthly",
        "STRIPE_PRICE_PRO",
        "stripe_price_pro",
        "subscription_base",
        "Business €249/mo (internal plan_code pro)",
    ),
    StripePriceSKU(
        "plan_business_yearly",
        "STRIPE_PRICE_PRO_YEARLY",
        "stripe_price_pro_yearly",
        "subscription_base",
        "Business yearly (€219/mo equivalent)",
    ),
    StripePriceSKU(
        "addon_operating_company_team",
        "STRIPE_PRICE_OPERATING_COMPANY_SLOT_TEAM",
        "stripe_price_operating_company_slot_team",
        "subscription_addon_quantity",
        "Extra workspace Team +€25/mo each (quantity = extra slots)",
    ),
    StripePriceSKU(
        "addon_operating_company_business",
        "STRIPE_PRICE_OPERATING_COMPANY_SLOT_BUSINESS",
        "stripe_price_operating_company_slot_business",
        "subscription_addon_quantity",
        "Extra workspace Business +€20/mo each",
    ),
    StripePriceSKU(
        "addon_operating_company_legacy",
        "STRIPE_PRICE_OPERATING_COMPANY_SLOT",
        "stripe_price_operating_company_slot",
        "subscription_addon_quantity",
        "Legacy single Price if team/business-specific IDs not set",
    ),
    StripePriceSKU(
        "addon_seat_team",
        "STRIPE_PRICE_SEAT_TEAM",
        "stripe_price_seat_team",
        "subscription_addon_quantity",
        "Extra seat Team +€18/mo",
    ),
    StripePriceSKU(
        "addon_seat_business",
        "STRIPE_PRICE_SEAT_BUSINESS",
        "stripe_price_seat_business",
        "subscription_addon_quantity",
        "Extra seat Business +€15/mo",
    ),
    StripePriceSKU(
        "addon_client_portal_account_team",
        "STRIPE_PRICE_CLIENT_PORTAL_ACCOUNT_TEAM",
        "stripe_price_client_portal_account_team",
        "subscription_addon_quantity",
        "Extra client portal account Team +€7/mo",
    ),
    StripePriceSKU(
        "addon_client_portal_account_business",
        "STRIPE_PRICE_CLIENT_PORTAL_ACCOUNT_BUSINESS",
        "stripe_price_client_portal_account_business",
        "subscription_addon_quantity",
        "Extra client portal account Business +€5/mo",
    ),
    StripePriceSKU(
        "pack_client_portal_5",
        "STRIPE_PRICE_CLIENT_PORTAL_PACK_5",
        "stripe_price_client_portal_pack_5",
        "checkout_payment",
        "Bundle +5 client portal accounts €20/mo (or one-time per product policy)",
    ),
    StripePriceSKU(
        "pack_portal_candidates",
        "STRIPE_PRICE_PORTAL_CANDIDATES_PACK",
        "stripe_price_portal_candidates_pack",
        "checkout_payment",
        "+N active portal candidates / month (PORTAL_CANDIDATES_PACK_INCREMENT default 500)",
    ),
    StripePriceSKU(
        "addon_branded_portal_workspace",
        "STRIPE_PRICE_BRANDED_PORTAL_WORKSPACE",
        "stripe_price_branded_portal_workspace",
        "subscription_addon_quantity",
        "Branded portal +€49/mo per workspace (own_company)",
    ),
    StripePriceSKU(
        "pack_automation_rules_10",
        "STRIPE_PRICE_AUTOMATION_RULES_PACK_10",
        "stripe_price_automation_rules_pack_10",
        "checkout_payment",
        "+10 automation rules €15/mo (AUTOMATION_RULES_PACK_10_INCREMENT)",
    ),
    StripePriceSKU(
        "pack_automation_rules_25",
        "STRIPE_PRICE_AUTOMATION_RULES_PACK_25",
        "stripe_price_automation_rules_pack_25",
        "checkout_payment",
        "+25 automation rules €30/mo (AUTOMATION_RULES_PACK_25_INCREMENT)",
    ),
    StripePriceSKU(
        "pack_custom_fields_25",
        "STRIPE_PRICE_CUSTOM_FIELDS_PACK_25",
        "stripe_price_custom_fields_pack_25",
        "checkout_payment",
        "+25 custom fields €10/mo",
    ),
    StripePriceSKU(
        "pack_custom_fields_100",
        "STRIPE_PRICE_CUSTOM_FIELDS_PACK_100",
        "stripe_price_custom_fields_pack_100",
        "checkout_payment",
        "+100 custom fields €25/mo",
    ),
    StripePriceSKU(
        "addon_lead_source",
        "STRIPE_PRICE_LEAD_SOURCE_EXTRA",
        "stripe_price_lead_source_extra",
        "subscription_addon_quantity",
        "Extra lead source +€10/mo each",
    ),
    StripePriceSKU(
        "pack_lead_forms_5",
        "STRIPE_PRICE_LEAD_FORMS_PACK_5",
        "stripe_price_lead_forms_pack_5",
        "checkout_payment",
        "+5 lead forms €10/mo (LEAD_FORMS_PACK_INCREMENT)",
    ),
    StripePriceSKU(
        "addon_communication_channel",
        "STRIPE_PRICE_COMMUNICATION_CHANNEL_EXTRA",
        "stripe_price_communication_channel_extra",
        "subscription_addon_quantity",
        "Extra comm channel +€8/mo each",
    ),
    StripePriceSKU(
        "pack_leads_500",
        "STRIPE_PRICE_LEADS_PACK_500",
        "stripe_price_leads_pack_500",
        "checkout_payment",
        "+500 leads/mo €15 (LEADS_PACK_500_INCREMENT)",
    ),
    StripePriceSKU(
        "pack_active_records_2000",
        "STRIPE_PRICE_ACTIVE_RECORDS_PACK_2000",
        "stripe_price_active_records_pack_2000",
        "checkout_payment",
        "+2000 active records €20/mo (ACTIVE_RECORDS_PACK_2000_INCREMENT)",
    ),
    StripePriceSKU(
        "pack_storage_50gb",
        "STRIPE_PRICE_STORAGE_PACK_50GB",
        "stripe_price_storage_pack_50gb",
        "checkout_payment",
        "+50 GB €10/mo (STORAGE_PACK_50GB_INCREMENT_GB)",
    ),
)


def stripe_price_skus_by_mode(mode: BillingMode) -> tuple[StripePriceSKU, ...]:
    return tuple(s for s in STRIPE_PRICE_SKUS if s.mode == mode)


def iter_checkout_payment_skus() -> tuple[StripePriceSKU, ...]:
    return tuple(s for s in STRIPE_PRICE_SKUS if s.mode == "checkout_payment")


def sku_price_from_settings(settings_obj: Any, sku_key: str) -> str | None:
    for s in STRIPE_PRICE_SKUS:
        if s.key == sku_key:
            raw = getattr(settings_obj, s.settings_attr, None)
            return (str(raw).strip() if raw is not None else "") or None
    return None


def sku_pack_increment(settings_obj: Any, sku_key: str) -> int | None:
    """Display / metadata increment for one-time checkout packs; None if not applicable."""
    k = (sku_key or "").strip()
    if k == "pack_portal_candidates":
        return max(1, int(getattr(settings_obj, "portal_candidates_pack_increment", 500) or 500))
    if k == "pack_client_portal_5":
        return 5
    if k == "pack_automation_rules_10":
        return max(1, int(getattr(settings_obj, "automation_rules_pack_10_increment", 10) or 10))
    if k == "pack_automation_rules_25":
        return max(1, int(getattr(settings_obj, "automation_rules_pack_25_increment", 25) or 25))
    if k == "pack_custom_fields_25":
        return max(1, int(getattr(settings_obj, "custom_fields_pack_25_increment", 25) or 25))
    if k == "pack_custom_fields_100":
        return max(1, int(getattr(settings_obj, "custom_fields_pack_100_increment", 100) or 100))
    if k == "pack_lead_forms_5":
        return max(1, int(getattr(settings_obj, "lead_forms_pack_increment", 5) or 5))
    if k == "pack_leads_500":
        return max(1, int(getattr(settings_obj, "leads_pack_500_increment", 500) or 500))
    if k == "pack_active_records_2000":
        return max(1, int(getattr(settings_obj, "active_records_pack_2000_increment", 2000) or 2000))
    if k == "pack_storage_50gb":
        return max(1, int(getattr(settings_obj, "storage_pack_50gb_increment_gb", 50) or 50))
    return None
