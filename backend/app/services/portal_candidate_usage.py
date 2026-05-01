"""Monthly active portal candidate usage (§2.16) — idempotent counter in tenant.settings.

Canonical metric: unique candidate_id per calendar month (UTC) when portal access is enabled.
v1 implementation: record on candidate public link ensure path (proxy for portal_access) — see SSOT.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException, status

from backend.app.constants.spa_paths import SETTINGS_BILLING
from backend.app.models.tenant import Tenant
from backend.app.services.plan_feature_gates import TRIAL_PORTAL_SHARES_CAP

_USAGE_ROOT = "usage_v1"
_MONTH_BUCKET_KEY = "portal_active_candidates_by_month_v1"
# Purchased add-on to monthly portal candidate cap (§2.16 pack via Checkout); summed with plan base cap.
_PORTAL_MONTHLY_CAP_ADDON_KEY = "portal_monthly_cap_addon_v1"


def utc_year_month(at_utc: datetime) -> str:
    return at_utc.astimezone(UTC).strftime("%Y-%m")


def merge_record_into_settings(
    settings: dict[str, Any],
    candidate_id: str,
    *,
    at_utc: datetime,
) -> dict[str, Any]:
    cid = (candidate_id or "").strip()
    if not cid:
        return settings
    ym = utc_year_month(at_utc)
    root = dict(settings or {})
    usage = dict(root.get(_USAGE_ROOT) or {})
    months: dict[str, Any] = dict(usage.get(_MONTH_BUCKET_KEY) or {})
    ids: list[str] = list(months.get(ym) or [])
    if cid not in ids:
        ids.append(cid)
    months[ym] = ids
    usage[_MONTH_BUCKET_KEY] = months
    root[_USAGE_ROOT] = usage
    return root


def count_for_utc_month(settings: dict[str, Any] | None, *, at_utc: datetime) -> int:
    ym = utc_year_month(at_utc)
    root = settings or {}
    usage = root.get(_USAGE_ROOT) if isinstance(root.get(_USAGE_ROOT), dict) else {}
    months = usage.get(_MONTH_BUCKET_KEY) if isinstance(usage.get(_MONTH_BUCKET_KEY), dict) else {}
    raw = months.get(ym)
    if isinstance(raw, list):
        return len(raw)
    return 0


def candidate_id_in_month_bucket(settings: dict[str, Any] | None, candidate_id: str, *, at_utc: datetime) -> bool:
    cid = (candidate_id or "").strip()
    if not cid:
        return False
    ym = utc_year_month(at_utc)
    root = settings or {}
    usage = root.get(_USAGE_ROOT) if isinstance(root.get(_USAGE_ROOT), dict) else {}
    months = usage.get(_MONTH_BUCKET_KEY) if isinstance(usage.get(_MONTH_BUCKET_KEY), dict) else {}
    raw = months.get(ym)
    if isinstance(raw, list):
        return cid in raw
    return False


def subscription_dict_from_tenant_settings(tenant: Tenant) -> dict[str, Any]:
    st = tenant.settings if isinstance(tenant.settings, dict) else {}
    bill = st.get("billing")
    if not isinstance(bill, dict):
        return {}
    sub = bill.get("subscription")
    return dict(sub) if isinstance(sub, dict) else {}


def resolve_plan_code_for_portal_cap(subscription: dict[str, Any] | None, license_row: Any | None) -> str:
    """Align with billing._plan_code_for_usage_caps."""
    sub = subscription if isinstance(subscription, dict) else {}
    st = str(sub.get("status") or "").strip().lower()
    if st == "trial":
        return "trial"
    raw = str(sub.get("plan_code") or "").strip().lower()
    if raw in ("starter", "team", "pro", "enterprise"):
        return raw
    if license_row is not None:
        lic = str(getattr(license_row, "plan", None) or "").strip().lower()
        if lic in ("starter", "team", "pro", "enterprise"):
            return lic
    return "starter"


def monthly_cap_for_plan_code(plan_code: str) -> int | None:
    p = (plan_code or "").strip().lower()
    if p == "trial":
        return TRIAL_PORTAL_SHARES_CAP
    if p == "starter":
        return None
    if p == "team":
        return 300
    if p == "pro":
        return 2000
    if p == "enterprise":
        return 2000
    return None


def portal_monthly_cap_addon(settings: dict[str, Any] | None) -> int:
    root = settings or {}
    usage = root.get(_USAGE_ROOT) if isinstance(root.get(_USAGE_ROOT), dict) else {}
    v = usage.get(_PORTAL_MONTHLY_CAP_ADDON_KEY)
    try:
        return max(0, int(v))
    except (TypeError, ValueError):
        return 0


def effective_monthly_portal_cap(plan_code: str, settings: dict[str, Any] | None) -> int | None:
    base = monthly_cap_for_plan_code(plan_code)
    if base is None:
        return None
    return base + portal_monthly_cap_addon(settings)


def merge_increment_portal_monthly_cap_addon(settings: dict[str, Any], delta: int) -> dict[str, Any]:
    d = max(0, int(delta))
    root = dict(settings or {})
    usage = dict(root.get(_USAGE_ROOT) or {})
    cur = portal_monthly_cap_addon(root)
    usage[_PORTAL_MONTHLY_CAP_ADDON_KEY] = cur + d
    root[_USAGE_ROOT] = usage
    return root


def ensure_can_add_portal_candidate_month(
    tenant: Tenant,
    candidate_id: str,
    *,
    at_utc: datetime,
    plan_code: str,
) -> None:
    """
    Hard cap (§2.16): block recording a *new* candidate_id for the UTC month when at plan cap.
    Idempotent: already-counted candidates for the month are always allowed (e.g. refresh links).
    """
    st = dict(tenant.settings or {})
    cap = effective_monthly_portal_cap(plan_code, st)
    if cap is None:
        return
    cid = (candidate_id or "").strip()
    if not cid:
        return
    if candidate_id_in_month_bucket(st, cid, at_utc=at_utc):
        return
    if count_for_utc_month(st, at_utc=at_utc) >= cap:
        base = monthly_cap_for_plan_code(plan_code)
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail={
                "code": "portal_active_candidates_limit_reached",
                "message": "Monthly active portal candidate limit reached for this plan",
                "cap": cap,
                "base_cap": base,
                "pack_addon": portal_monthly_cap_addon(st),
                "billing_path": SETTINGS_BILLING,
            },
        )


def record_active_portal_candidate_month(tenant: Tenant, candidate_id: str, *, at_utc: datetime) -> None:
    """Idempotent: same candidate_id in the same UTC month is counted once."""
    tenant.settings = merge_record_into_settings(dict(tenant.settings or {}), candidate_id, at_utc=at_utc)
