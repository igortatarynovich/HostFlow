"""Founder pricing streak (§2.16): Stripe subscription status is primary; mirror in tenant.settings.

If enrolled in founder program and Stripe-normalized status stays outside active/trial for >14 days,
founder benefit is revoked permanently (no restore).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.tenant import Tenant

# Normalized statuses written by billing._normalize_stripe_subscription_status
_FOUNDER_ACTIVE_STATUSES = frozenset({"active", "trial"})
_INACTIVITY_REVOKE_AFTER = timedelta(days=14)

FOUNDER_MAX_SLOTS = 50


def license_plan_for_founder_eligibility(license_plan: str | None) -> str | None:
    """
    Map DB license.plan (may be legacy strings) to billing plan_code team|pro for founder slots.
    Returns None if treated as Solo / ineligible.
    """
    p = (license_plan or "").strip().lower()
    if not p or p in ("starter", "solo", "trial"):
        return None
    if p in ("team", "pro"):
        return p
    if p in {"agency_basic", "employer_basic", "services_basic"}:
        return "team"
    if p in {"agency_premium", "business", "enterprise"}:
        return "pro"
    return None


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


def apply_stripe_status_to_settings(
    settings: dict[str, Any],
    normalized_stripe_subscription_status: str,
    *,
    now_utc: datetime,
) -> dict[str, Any]:
    """
    Mutates a copy of settings: under billing.founder_pricing_v1 expects:
      enrolled: bool
      revoked: bool (optional; default False)
      inactive_since: ISO timestamp or null
      revoked_at: optional ISO when revoked

    No-op if not enrolled or already revoked.
    """
    out = dict(settings or {})
    billing = dict(out.get("billing") or {})
    raw_fp = billing.get("founder_pricing_v1")
    if not isinstance(raw_fp, dict) or not raw_fp.get("enrolled"):
        return out
    fp = dict(raw_fp)
    if fp.get("revoked"):
        billing["founder_pricing_v1"] = fp
        out["billing"] = billing
        return out

    status = (normalized_stripe_subscription_status or "").strip().lower()
    stripe_active = status in _FOUNDER_ACTIVE_STATUSES

    if stripe_active:
        fp["inactive_since"] = None
    else:
        if not fp.get("inactive_since"):
            fp["inactive_since"] = now_utc.isoformat()
        else:
            started = _parse_iso_datetime(fp.get("inactive_since"))
            if started is not None and (now_utc - started) > _INACTIVITY_REVOKE_AFTER:
                fp["revoked"] = True
                fp["revoked_at"] = now_utc.isoformat()

    billing["founder_pricing_v1"] = fp
    out["billing"] = billing
    return out


def _is_active_founder_enrollment(settings_fragment: dict[str, Any] | None) -> bool:
    if not isinstance(settings_fragment, dict):
        return False
    bill = settings_fragment.get("billing")
    if not isinstance(bill, dict):
        return False
    fp = bill.get("founder_pricing_v1")
    if not isinstance(fp, dict):
        return False
    if not fp.get("enrolled"):
        return False
    if fp.get("revoked"):
        return False
    return True


async def count_active_founder_enrollments(db: AsyncSession) -> int:
    """Tenants with founder_pricing_v1.enrolled and not revoked (settings JSON)."""
    bind = db.get_bind()
    if getattr(bind.dialect, "name", None) == "postgresql":
        q = text(
            """
            SELECT COUNT(*)::int FROM tenants
            WHERE (settings->'billing'->'founder_pricing_v1'->>'enrolled') = 'true'
            AND COALESCE(
                LOWER(TRIM(settings->'billing'->'founder_pricing_v1'->>'revoked')),
                'false'
            ) NOT IN ('true', '1')
            """
        )
        row = await db.execute(q)
        return int(row.scalar() or 0)
    result = await db.execute(select(Tenant.settings))
    n = 0
    for (st,) in result.all():
        if _is_active_founder_enrollment(st if isinstance(st, dict) else {}):
            n += 1
    return n


def merge_enroll_founder_initial(settings: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    """Set enrolled=True for a new founder slot. Returns (new_settings, True) or (settings, False)."""
    root = dict(settings or {})
    bill = dict(root.get("billing") or {})
    fp_raw = bill.get("founder_pricing_v1")
    fp = dict(fp_raw) if isinstance(fp_raw, dict) else {}
    if fp.get("revoked"):
        return root, False
    if fp.get("enrolled"):
        return root, False
    fp.update(
        {
            "enrolled": True,
            "revoked": False,
            "inactive_since": None,
        }
    )
    bill["founder_pricing_v1"] = fp
    root["billing"] = bill
    return root, True


async def try_enroll_if_slot_available(
    db: AsyncSession,
    tenant: Tenant,
    *,
    plan_code: str,
) -> bool:
    """
    First paid Team/Business activation: take a founder slot if any remain (max FOUNDER_MAX_SLOTS).
    No-op for starter, already enrolled, or revoked tenants.
    """
    pc = (plan_code or "").strip().lower()
    if pc == "starter":
        return False
    if pc not in {"team", "pro"}:
        return False
    settings = dict(tenant.settings or {})
    fp = (settings.get("billing") or {}).get("founder_pricing_v1")
    if isinstance(fp, dict) and fp.get("revoked"):
        return False
    if isinstance(fp, dict) and fp.get("enrolled"):
        return False
    used = await count_active_founder_enrollments(db)
    if used >= FOUNDER_MAX_SLOTS:
        return False
    new_settings, ok = merge_enroll_founder_initial(settings)
    if not ok:
        return False
    tenant.settings = new_settings
    return True
