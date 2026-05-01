"""Stable HostFlow production IDs shared by scripts and platform behavior (single source of truth)."""

# Focus Personnel — operational agency tenant (Meta leads, Poltrakt, etc.).
# Product: plan-gated features and communications defaults are treated as **all-on** for this
# id (``plan_allows_*`` with ``tenant_id``, ``resolve_plan_bucket_for_limits`` → pro, comm settings merge).
# See also: scripts/focus_poltrakt_provision_user.py, migrate_poltrakt_company_to_focus.sql
FOCUS_PERSONNEL_TENANT_ID = "9497fc29-6051-424d-9344-abb4aed9b110"


def is_focus_personnel_tenant(tenant_id: str | None) -> bool:
    return str(tenant_id or "").strip().lower() == FOCUS_PERSONNEL_TENANT_ID
