"""Monthly inbound leads cap (§2.16 / billing); keep resolve logic aligned with settings billing usage_caps."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.constants.hostflow_canonical_tenants import is_focus_personnel_tenant
from backend.app.intake_platform.operational_scope import OPERATIONAL_EXCLUDED_LEAD_STAGES
from backend.app.models.lead import Lead
from backend.app.models.tenant import Tenant, TenantLicense
from backend.app.services.billing_pack_addons import MONTHLY_LEADS_CAP, pack_addon_int
from backend.app.services.plan_feature_gates import TRIAL_LEADS_MONTHLY_CAP

PLAN_CODES: tuple[str, ...] = ("starter", "team", "pro", "enterprise")

# Canonical monthly inbound leads cap; billing summary imports resolve_monthly_leads_cap from here.
PLAN_LEADS_MONTHLY_LIMIT: dict[str, int] = {
    "starter": 200,
    "team": 1500,
    "pro": 5000,
    "enterprise": 5000,
}


def subscription_dict_from_tenant(tenant: Tenant | None) -> dict[str, Any]:
    if tenant is None:
        return {}
    settings_payload = tenant.settings if isinstance(tenant.settings, dict) else {}
    billing = settings_payload.get("billing") if isinstance(settings_payload.get("billing"), dict) else {}
    sub = billing.get("subscription") if isinstance(billing.get("subscription"), dict) else {}
    return dict(sub)


def resolve_monthly_leads_cap(
    subscription: dict[str, Any],
    license_entry: TenantLicense | None,
    tenant_settings: dict[str, Any] | None = None,
) -> int:
    status = str(subscription.get("status") or "").strip().lower()
    if status == "trial":
        leads_plan = "trial"
    else:
        raw = str(subscription.get("plan_code") or "").strip().lower()
        if raw in PLAN_CODES:
            leads_plan = raw
        elif license_entry is not None:
            lp = str(getattr(license_entry, "plan", None) or "").strip().lower()
            leads_plan = lp if lp in PLAN_CODES else "starter"
        else:
            leads_plan = "starter"
    if leads_plan == "trial":
        base = TRIAL_LEADS_MONTHLY_CAP
    else:
        base = int(PLAN_LEADS_MONTHLY_LIMIT.get(leads_plan, PLAN_LEADS_MONTHLY_LIMIT["starter"]))
    addon = pack_addon_int(tenant_settings, MONTHLY_LEADS_CAP) if tenant_settings else 0
    return base + addon


async def count_leads_created_this_month_utc(db: AsyncSession, tenant_id: str) -> int:
    now = datetime.now(timezone.utc)
    month_start = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
    stmt = select(func.count()).select_from(Lead).where(
        Lead.tenant_id == tenant_id,
        Lead.created_at >= month_start,
        func.lower(func.coalesce(Lead.stage, "")).notin_(tuple(OPERATIONAL_EXCLUDED_LEAD_STAGES)),
    )
    return int((await db.execute(stmt)).scalar_one() or 0)


async def ensure_monthly_lead_creation_allowed(db: AsyncSession, tenant_id: str) -> None:
    if is_focus_personnel_tenant(tenant_id):
        return
    tenant = await db.get(Tenant, tenant_id)
    sub = subscription_dict_from_tenant(tenant)
    lic_row = (
        await db.execute(select(TenantLicense).where(TenantLicense.tenant_id == tenant_id).limit(1))
    ).scalar_one_or_none()
    st = tenant.settings if tenant is not None and isinstance(tenant.settings, dict) else None
    cap = resolve_monthly_leads_cap(sub, lic_row, st)
    if cap <= 0:
        return
    current = await count_leads_created_this_month_utc(db, tenant_id)
    if current >= cap:
        raise HTTPException(
            status_code=402,
            detail={
                "code": "monthly_leads_limit_reached",
                "limit": cap,
                "current": current,
            },
        )
