"""Billing state gates (§2.18): past_due and expired trial block new leads and outbound comms."""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any, Literal

from backend.app.models.tenant import Tenant, TenantLicense


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


def _utc_today() -> date:
    return datetime.now(UTC).date()


def billing_write_block_reason(
    tenant: Tenant | None,
    license_row: TenantLicense | None = None,
) -> Literal["past_due", "trial_expired"] | None:
    """
    Returns a gate reason if the tenant must not create leads or send outbound comms.

    - past_due: Stripe payment failed.
    - trial_expired: self-service trial license date passed, or Stripe trial window ended (subscription still "trial").
    Paid active subscriptions are never blocked here.
    """
    if tenant is None:
        return None
    status = tenant_subscription_status(tenant)
    if status == "past_due":
        return "past_due"
    if status == "active":
        return None
    sub = _subscription_payload(tenant)
    trial_end_dt = _parse_iso_datetime(sub.get("trial_ends_at"))
    if status == "trial" and trial_end_dt is not None and datetime.now(UTC) > trial_end_dt:
        return "trial_expired"
    if license_row is not None:
        plan = str(license_row.plan or "").strip().lower()
        exp = license_row.expires_at
        if plan == "trial" and exp is not None and exp < _utc_today():
            return "trial_expired"
    return None


def tenant_billing_blocks_new_leads(tenant: Tenant | None, license_row: TenantLicense | None = None) -> bool:
    return billing_write_block_reason(tenant, license_row) is not None


def tenant_billing_blocks_outbound_comms(tenant: Tenant | None, license_row: TenantLicense | None = None) -> bool:
    return billing_write_block_reason(tenant, license_row) is not None
