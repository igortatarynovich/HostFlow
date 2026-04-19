"""License-row sync between Stripe subscription and ``TenantLicense`` table.

Extracted from ``backend/app/api/v1/settings/billing/__init__.py`` as part of
the Phase 1 god-module split (step 5/N).

Contents:

* ``sync_subscription_license_addon_v1`` — public helper called by the Platform
  admin endpoint when an admin patches the license row, also called from
  ``packs._apply_*`` after a pack increases license caps. Writes the
  per-field deltas (above §2.16 base) into
  ``tenant.settings.billing.subscription.license_addon_v1``.
* ``_apply_license_limits`` — when a plan transition lands (Stripe webhook or
  admin tool), reset ``TenantLicense`` columns to plan baselines + saved
  add-on deltas; called from webhook handlers and the change-plan endpoint.
"""

from __future__ import annotations

from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.tenant import Tenant, TenantLicense

from .plans import (
    LICENSE_ADDON_MERGE_FIELDS,
    PLAN_LICENSE_LIMITS,
    _license_addon_deltas_from_subscription,
    build_license_addon_v1_payload,
)
from .state import _now_utc, _subscription_payload


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
