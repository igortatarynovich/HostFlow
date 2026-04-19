"""Summary-payload assemblers + founder-program helpers.

Extracted from ``backend/app/api/v1/settings/billing/__init__.py`` as part of
the Phase 1 god-module split (step 6/N).

Contents:

* **Plan-code resolver** — ``_plan_code_for_usage_caps`` (subscription status
  ``trial`` always maps to ``starter`` even if the saved plan was higher).
* **Tenant settings reader** — ``_tenant_settings_dict``.
* **Usage caps** — ``_billing_usage_caps`` (combines license-row caps +
  ``resolve_monthly_leads_cap`` to produce ``BillingUsageCapsOut``).
* **Add-on offers** — ``_billing_summary_addon_offers``.
* **Snapshots** — ``_company_slots_payload``,
  ``_portal_candidates_usage_snapshot``, ``_founder_program_snapshot``.
* **Combined extras** — ``_billing_summary_extras`` returns the
  ``(portal, founder, lead_forms)`` triple consumed by ``GET /summary``.
* **Founder enrollment** — ``_maybe_enroll_founder_program`` (called from
  webhook handlers when a plan transition lands; idempotent).

Pure rendering / read-only DB helpers — no Stripe interaction here.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.settings import settings
from backend.app.models.tenant import Tenant, TenantLicense
from backend.app.services import founder_pricing, portal_candidate_usage
from backend.app.services.billing_pack_addons import LEAD_FORMS_ACTIVE_CAP, pack_addon_int
from backend.app.services.lead_forms_quota import count_active_tenant_lead_forms, lead_forms_base_cap
from backend.app.services.lead_quota import resolve_monthly_leads_cap
from backend.app.services.operating_company_slots import get_operating_company_slots

from ..schemas import (
    BillingAddonCheckoutOfferOut,
    BillingCompanySlotsOut,
    BillingFounderProgramOut,
    BillingLeadFormsUsageOut,
    BillingPortalCandidatesUsageOut,
    BillingUsageCapsOut,
)
from .plans import (
    PLAN_CODES,
    PLAN_LICENSE_LIMITS,
    _addon_checkout_offers_for_plan,
    _normalize_plan_code,
)
from .state import _now_utc


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


def _billing_summary_addon_offers(
    license_entry: TenantLicense | None,
    subscription: dict[str, Any],
) -> list[BillingAddonCheckoutOfferOut]:
    pc = _plan_code_for_usage_caps(subscription, license_entry)
    return _addon_checkout_offers_for_plan(pc)


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
