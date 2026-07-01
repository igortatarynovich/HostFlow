"""Tenant / subscription / history / time helpers for the billing API.

Extracted from ``backend/app/api/v1/settings/billing/__init__.py`` as part of
the Phase 1 god-module split (step 3/N).

Contents:

* **Time helpers** — ``_now_utc``, ``_iso_to_dt``, ``_unix_to_iso``.
* **Tenant access** — ``_ensure_tenant_access`` (raises 403 if non-superadmin
  token mismatches target tenant).
* **Tenant.settings.billing readers** — ``_billing_root``,
  ``_subscription_payload``, ``_billing_history``, ``_history_contains``.
* **Slots writer** — ``_set_extra_operating_slots`` (normalises legacy keys
  in tenant settings payload).
* **Subscription serializer** — ``_subscription_out`` (builds
  ``BillingSubscriptionOut`` from tenant + license, including
  ``BillingGateOut`` snapshot from ``billing_restrictions``).
* **Mutator** — ``_store_subscription`` (writes subscription + history into
  tenant settings, applies founder-pricing transition, commits).
"""

from __future__ import annotations

from datetime import UTC, datetime, time
from typing import Any, Literal

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.deps import Role, UserCtx
from backend.app.models.tenant import Tenant, TenantLicense
from backend.app.services import billing_restrictions, founder_pricing

from ..schemas import BillingGateOut, BillingSubscriptionOut
from .plans import PLAN_CODES


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


def _set_extra_operating_slots(payload: dict[str, Any], extra_slots: int) -> dict[str, Any]:
    value = max(0, int(extra_slots or 0))
    updated = dict(payload)
    updated["extra_operating_company_slots"] = value
    for legacy_key in ("additional_operating_company_slots", "operating_company_addon_slots"):
        if legacy_key in updated:
            del updated[legacy_key]
    return updated


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
    gate_snap = billing_restrictions.compute_billing_gate_snapshot(tenant, license_entry)
    gate_out = BillingGateOut(
        side_effects_blocked=gate_snap.side_effects_blocked,
        block_reason=gate_snap.block_reason,
        trial_active=gate_snap.trial_active,
        trial_grace_active=gate_snap.trial_grace_active,
        trial_hours_remaining=gate_snap.trial_hours_remaining,
        trial_urgent=gate_snap.trial_urgent,
        side_effect_grace_hours_remaining=gate_snap.side_effect_grace_hours_remaining,
    )
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
        gate=gate_out,
    )


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
