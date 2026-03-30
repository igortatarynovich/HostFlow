"""Billing state gates (§2.18 / §2.16): past_due and expired trial block new leads and outbound comms.

Side-effect-heavy actions (stage change, automation, new portal access, etc.) should use the same
gate until a finer allowlist is implemented — see SSOT §2.16 «Post-trial / past_due — редактирование без side-effects».
"""

from __future__ import annotations

from datetime import UTC, datetime, time, timedelta
from typing import Any, Literal

from fastapi import HTTPException, status

from backend.app.models.tenant import Tenant, TenantLicense

_TRIAL_SIDE_EFFECT_GRACE = timedelta(days=3)


def _subscription_payload(tenant: Tenant | None) -> dict[str, Any]:
    if tenant is None:
        return {}
    settings_payload = tenant.settings if isinstance(tenant.settings, dict) else {}
    billing = settings_payload.get("billing") if isinstance(settings_payload.get("billing"), dict) else {}
    sub = billing.get("subscription") if isinstance(billing.get("subscription"), dict) else {}
    return dict(sub)


def tenant_subscription_status(tenant: Tenant | None) -> str:
    return str(_subscription_payload(tenant).get("status") or "").strip().lower()


def _parse_iso_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        dt = value
        if dt.tzinfo is None:
            return dt.replace(tzinfo=UTC)
        return dt.astimezone(UTC)
    s = str(value).strip()
    if not s:
        return None
    try:
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt.astimezone(UTC)
    except ValueError:
        return None


def billing_write_block_reason(
    tenant: Tenant | None,
    license_row: TenantLicense | None = None,
) -> Literal["past_due", "trial_expired"] | None:
    """
    Returns a gate reason if the tenant must not create leads or send outbound comms.

    - past_due: Stripe payment failed.
    - trial_expired: trial ended and the §2.16 **3-day grace** for side effects has passed (Stripe `trial_ends_at`
      and/or license `expires_at` calendar trial).
    Paid active subscriptions are never blocked here.
    """
    if tenant is None:
        return None
    now = datetime.now(UTC)
    status = tenant_subscription_status(tenant)
    if status == "past_due":
        return "past_due"
    if status == "active":
        return None
    sub = _subscription_payload(tenant)
    stripe_trial_end = _parse_iso_datetime(sub.get("trial_ends_at")) if status == "trial" else None
    lic_trial_end: datetime | None = None
    if license_row is not None:
        plan = str(license_row.plan or "").strip().lower()
        exp = license_row.expires_at
        if plan == "trial" and exp is not None:
            lic_trial_end = datetime.combine(exp + timedelta(days=1), time.min, tzinfo=UTC)

    if status == "trial" and stripe_trial_end is not None:
        if now < stripe_trial_end:
            return None
        if now < stripe_trial_end + _TRIAL_SIDE_EFFECT_GRACE:
            return None
        return "trial_expired"

    if lic_trial_end is not None:
        if now < lic_trial_end:
            return None
        if now < lic_trial_end + _TRIAL_SIDE_EFFECT_GRACE:
            return None
        return "trial_expired"

    return None


def tenant_billing_blocks_new_leads(tenant: Tenant | None, license_row: TenantLicense | None = None) -> bool:
    return billing_write_block_reason(tenant, license_row) is not None


def tenant_billing_blocks_outbound_comms(tenant: Tenant | None, license_row: TenantLicense | None = None) -> bool:
    return billing_write_block_reason(tenant, license_row) is not None


def tenant_billing_blocks_side_effect_writes(
    tenant: Tenant | None, license_row: TenantLicense | None = None
) -> bool:
    """True when post-trial / past_due policy blocks process/comms/automation (not the field-edit allowlist)."""
    return billing_write_block_reason(tenant, license_row) is not None


def ensure_billing_allows_side_effects(
    tenant: Tenant | None, license_row: TenantLicense | None = None
) -> None:
    """403 when §2.16 blocks stage changes, distribution, etc. (same gate as new leads / outbound comms)."""
    reason = billing_write_block_reason(tenant, license_row)
    if reason is None:
        return
    code = "billing_trial_expired" if reason == "trial_expired" else "billing_past_due"
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={"code": code, "message": "billing_side_effects_forbidden"},
    )
