"""Billing state gates (§2.18 / §2.16): past_due and expired trial block new leads and outbound comms.

Side-effect-heavy actions (stage change, automation, new portal access, etc.) should use the same
gate until a finer allowlist is implemented — see SSOT §2.16 «Post-trial / past_due — редактирование без side-effects».
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, time, timedelta
from typing import Any, Literal

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.tenant import Tenant, TenantLicense

_TRIAL_SIDE_EFFECT_GRACE = timedelta(days=3)
BillingAction = Literal[
    "side_effect_write",
    "task_complete",
    "candidate_close",
    "data_export",
    "billing_payment",
]
_PAST_DUE_ALLOWED_ACTIONS: frozenset[BillingAction] = frozenset(
    {"task_complete", "candidate_close", "data_export", "billing_payment"}
)


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
    stripe_trial_end = _parse_iso_datetime(sub.get("trial_ends_at")) if status in ("trial", "trialing") else None
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


def ensure_billing_allows_action(
    tenant: Tenant | None,
    license_row: TenantLicense | None = None,
    *,
    action: BillingAction = "side_effect_write",
) -> None:
    """
    Fine-grained allowlist for `past_due` (SSOT §2.16):
    - complete current tasks
    - close existing candidates
    - export data
    - pay
    """
    reason = billing_write_block_reason(tenant, license_row)
    if reason is None:
        return
    if reason == "past_due" and action in _PAST_DUE_ALLOWED_ACTIONS:
        return
    code = "billing_trial_expired" if reason == "trial_expired" else "billing_past_due"
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={
            "code": code,
            "message": "billing_action_forbidden",
            "action": action,
        },
    )


async def ensure_billing_allows_side_effects_for_tenant_id(db: AsyncSession, tenant_id: str) -> None:
    tid = (tenant_id or "").strip()
    if not tid:
        return
    tenant_row = await db.get(Tenant, tid)
    lic_row = (
        await db.execute(select(TenantLicense).where(TenantLicense.tenant_id == tid).limit(1))
    ).scalar_one_or_none()
    ensure_billing_allows_side_effects(tenant_row, lic_row)


async def ensure_billing_allows_action_for_tenant_id(
    db: AsyncSession, tenant_id: str, *, action: BillingAction = "side_effect_write"
) -> None:
    tid = (tenant_id or "").strip()
    if not tid:
        return
    tenant_row = await db.get(Tenant, tid)
    lic_row = (
        await db.execute(select(TenantLicense).where(TenantLicense.tenant_id == tid).limit(1))
    ).scalar_one_or_none()
    ensure_billing_allows_action(tenant_row, lic_row, action=action)


@dataclass(frozen=True)
class BillingGateSnapshot:
    side_effects_blocked: bool
    block_reason: Literal["past_due", "trial_expired"] | None
    trial_active: bool
    trial_grace_active: bool
    trial_hours_remaining: float | None
    trial_urgent: bool
    side_effect_grace_hours_remaining: float | None


def compute_billing_gate_snapshot(
    tenant: Tenant | None, license_row: TenantLicense | None = None
) -> BillingGateSnapshot:
    """UI + API: trial countdown, post-trial grace, hard blocks (§2.16 / §2.18)."""
    now = datetime.now(UTC)
    reason = billing_write_block_reason(tenant, license_row)
    sub = _subscription_payload(tenant)
    stripe_status = str(sub.get("status") or "").strip().lower()

    stripe_trial_end: datetime | None = None
    if stripe_status in ("trial", "trialing"):
        stripe_trial_end = _parse_iso_datetime(sub.get("trial_ends_at"))

    lic_trial_end: datetime | None = None
    if license_row is not None:
        plan = str(license_row.plan or "").strip().lower()
        exp = license_row.expires_at
        if plan == "trial" and exp is not None:
            lic_trial_end = datetime.combine(exp + timedelta(days=1), time.min, tzinfo=UTC)

    trial_end_effective = stripe_trial_end or lic_trial_end

    trial_active = False
    trial_grace_active = False
    trial_hours_remaining: float | None = None
    trial_urgent = False
    side_effect_grace_hrs: float | None = None

    if trial_end_effective is not None and reason is None:
        grace_end = trial_end_effective + _TRIAL_SIDE_EFFECT_GRACE
        if now < trial_end_effective:
            trial_active = True
            trial_hours_remaining = round((trial_end_effective - now).total_seconds() / 3600.0, 2)
            trial_urgent = bool(trial_hours_remaining is not None and trial_hours_remaining <= 48.0)
        elif now < grace_end:
            trial_grace_active = True
            side_effect_grace_hrs = round((grace_end - now).total_seconds() / 3600.0, 2)

    return BillingGateSnapshot(
        side_effects_blocked=reason is not None,
        block_reason=reason,
        trial_active=trial_active,
        trial_grace_active=trial_grace_active,
        trial_hours_remaining=trial_hours_remaining,
        trial_urgent=trial_urgent,
        side_effect_grace_hours_remaining=side_effect_grace_hrs,
    )
