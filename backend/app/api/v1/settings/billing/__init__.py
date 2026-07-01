"""Billing API package — Stripe-backed plan / add-on / webhook handling.

This ``__init__`` is intentionally minimal: it owns only

* the shared ``router`` instance,
* the optional ``stripe`` module placeholder (kept on the package so tests
  can patch ``billing.stripe`` and helpers/routes pick it up via
  late-binding), and
* a flat re-export surface — every helper / schema / route handler lives in
  a sub-module (``schemas``, ``routes``, ``_helpers/*``) and is re-exported
  here so the historical ``billing.<name>`` access pattern keeps working
  for ``arq_worker``, ``platform.tenants``, scripts, and tests.

Importing this package as a side effect imports ``.routes`` which triggers
the ``@router.<method>(...)`` decorators that register all 12 endpoints.
"""

from __future__ import annotations

from fastapi import APIRouter

from backend.app.core.settings import settings  # noqa: F401  re-exported for `billing.settings` access patterns (tests patch attrs here)

try:  # pragma: no cover - optional dependency
    import stripe
except Exception:  # pragma: no cover - stripe not installed yet
    stripe = None  # type: ignore[assignment]


# All Pydantic schemas live in ``.schemas``. Re-export at module level so every
# helper / route handler that referenced them as bare ``BillingFooOut`` keeps working
# without churn.
from .schemas import (  # noqa: E402,F401
    BillingUsageCapsOut,
    BillingGateOut,
    BillingSubscriptionOut,
    BillingCheckoutCreateIn,
    BillingCheckoutOut,
    BillingPortalPackCheckoutIn,
    BillingPortalPackCheckoutOut,
    BillingAddonPackCheckoutIn,
    BillingAddonPackCheckoutOut,
    BillingCheckoutSimulateIn,
    BillingPortalOut,
    BillingWebhookOut,
    BillingPlanOut,
    BillingHistoryItemOut,
    BillingInvoiceOut,
    BillingCompanySlotsOut,
    BillingPortalCandidatesUsageOut,
    BillingFounderProgramOut,
    BillingLeadFormsUsageOut,
    BillingAddonCheckoutOfferOut,
    BillingSummaryOut,
    BillingChangePlanIn,
    BillingCancelIn,
    BillingCompanySlotsUpdateIn,
)

# All plan-config + price-ID + addon-offer logic lives in ``._helpers.plans``.
# Re-export at module level so handlers / scripts that use these names as bare
# identifiers (and external test imports) keep working without churn.
from ._helpers.plans import (  # noqa: E402,F401
    ADDON_PACK_CHECKOUT_READY,
    ADDON_PACK_CHECKOUT_UNAVAILABLE,
    CHECKOUT_OUTCOMES,
    LICENSE_ADDON_MERGE_FIELDS,
    PLAN_CODES,
    PLAN_LICENSE_LIMITS,
    _addon_checkout_offers_for_plan,
    _addon_purchase_plan_ok_for_offer,
    _all_operating_slot_addon_price_ids,
    _available_plans,
    _calculate_proration_amount_minor,
    _license_addon_deltas_from_subscription,
    _normalize_plan_code,
    _operating_slot_addon_price_id_for_plan,
    _plan_code_by_price_id,
    _plan_price_id,
    _plan_stripe_price_id,
    _plan_stripe_yearly_price_id_only,
    _portal_candidates_pack_price_id,
    _stripe_obj_to_dict,
    _stripe_price_amount,
    _stripe_ready,
    build_license_addon_v1_payload,
)

# All tenant/subscription/history/time helpers live in ``._helpers.state``.
# Re-export at module level for backward-compat with external callers
# (``scripts/grant_tenant_business_internal.py``, tests, ``arq_worker``).
from ._helpers.state import (  # noqa: E402,F401
    _billing_history,
    _billing_root,
    _ensure_tenant_access,
    _history_contains,
    _iso_to_dt,
    _now_utc,
    _set_extra_operating_slots,
    _store_subscription,
    _subscription_out,
    _subscription_payload,
    _unix_to_iso,
)

# Stripe event/invoice extractors + email helper live in ``._helpers.stripe_extract``.
# Re-export at module level to preserve the historical surface (tests use
# ``billing._extract_operating_slot_addon_quantity`` and similar).
from ._helpers.stripe_extract import (  # noqa: E402,F401
    _extract_invoice_period,
    _extract_operating_slot_addon_quantity,
    _extract_pending_invoice_details,
    _extract_pending_update,
    _extract_pending_update_plan_code,
    _extract_subscription_billing_interval,
    _extract_subscription_period,
    _extract_subscription_price_id,
    _find_operating_slot_addon_item,
    _find_subscription_item_by_price_id,
    _find_tenant_for_stripe_event,
    _list_stripe_invoices,
    _normalize_stripe_subscription_status,
    _send_billing_email,
    _stripe_invoice_out,
)

# History serialization helpers live in ``._helpers.history``.
from ._helpers.history import (  # noqa: E402,F401
    _history_entry,
    _history_out,
    _merge_history_with_invoices,
)

# License-row sync helpers live in ``._helpers.license_sync``.
# Re-exported for ``arq_worker``/``platform.tenants``/``scripts/grant_tenant_business_internal``
# which import these symbols directly from ``billing``.
from ._helpers.license_sync import (  # noqa: E402,F401
    _apply_license_limits,
    sync_subscription_license_addon_v1,
)

# Add-on pack application helpers live in ``._helpers.packs``.
from ._helpers.packs import (  # noqa: E402,F401
    _apply_addon_pack_by_sku,
    _apply_client_portal_pack_5_to_tenant,
    _apply_license_numeric_pack_to_tenant,
    _apply_pack_addon_to_tenant,
    _apply_portal_candidates_pack_to_tenant,
    _checkout_session_line_items_contain_price,
)

# Summary-payload assemblers + founder-program helpers live in ``._helpers.summary``.
from ._helpers.summary import (  # noqa: E402,F401
    _billing_summary_addon_offers,
    _billing_summary_extras,
    _billing_usage_caps,
    _company_slots_payload,
    _founder_program_snapshot,
    _maybe_enroll_founder_program,
    _plan_code_for_usage_caps,
    _portal_candidates_usage_snapshot,
    _tenant_settings_dict,
)

# Stripe webhook event handlers + idempotency claim/release live in
# ``._helpers.webhook_handlers``. Re-exported because external callers
# (``arq_worker._handle_*`` dispatch + tests of ``_stripe_webhook_*`` /
# ``_handle_*``) reach in through the ``billing`` package.
from ._helpers.webhook_handlers import (  # noqa: E402,F401
    _handle_addon_pack_checkout_completed,
    _handle_checkout_completed,
    _handle_invoice_finalized,
    _handle_invoice_paid,
    _handle_invoice_payment_failed,
    _handle_portal_candidates_pack_checkout_completed,
    _handle_subscription_event,
    _stripe_webhook_release_claim,
    _stripe_webhook_try_claim_event,
)

router = APIRouter(prefix="/billing", tags=["settings-billing"], redirect_slashes=False)

# Route handlers live in ``.routes`` — importing the module triggers the
# ``@router.<method>(...)`` decorator side-effects that register all endpoints.
from . import routes  # noqa: E402,F401
