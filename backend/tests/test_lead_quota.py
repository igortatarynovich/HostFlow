"""Unit tests for monthly leads cap resolution (shared billing + enforcement)."""

from __future__ import annotations

from backend.app.models.tenant import TenantLicense
from backend.app.services.lead_quota import resolve_monthly_leads_cap


def test_resolve_monthly_leads_trial_uses_trial_cap() -> None:
    cap = resolve_monthly_leads_cap({"status": "trial", "plan_code": "pro"}, None)
    assert cap == 50


def test_resolve_monthly_leads_active_uses_plan_code() -> None:
    cap = resolve_monthly_leads_cap({"status": "active", "plan_code": "pro"}, None)
    assert cap == 5000


def test_resolve_monthly_leads_falls_back_to_license_plan() -> None:
    lic = TenantLicense(tenant_id="t1", plan="team")  # type: ignore[arg-type]
    cap = resolve_monthly_leads_cap({}, lic)
    assert cap == 1500


def test_resolve_monthly_leads_includes_pack_addon() -> None:
    lic = TenantLicense(tenant_id="t1", plan="team")  # type: ignore[arg-type]
    st = {"usage_v1": {"pack_addons_v1": {"monthly_leads_cap": 500}}}
    cap = resolve_monthly_leads_cap({"status": "active", "plan_code": "team"}, lic, st)
    assert cap == 2000
