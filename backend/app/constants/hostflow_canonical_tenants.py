"""Stable HostFlow production IDs shared by scripts and platform behavior (single source of truth)."""

# Focus Personnel — operational agency tenant (Meta leads, Poltrakt, etc.).
# Product: plan-gated features and communications defaults are treated as **all-on** for this
# id (``plan_allows_*`` with ``tenant_id``, ``resolve_plan_bucket_for_limits`` → pro, comm settings merge).
# See also: scripts/focus_poltrakt_provision_user.py, migrate_poltrakt_company_to_focus.sql
FOCUS_PERSONNEL_TENANT_ID = "9497fc29-6051-424d-9344-abb4aed9b110"

# Client company POLTRAKT under Focus (sales.hostflow.cc/app/clients/…).
FOCUS_POLTRAKT_COMPANY_ID = "2b1ca966-e77d-4a45-9fa6-33ef4c7c2cd5"

# OwnCompany used by Focus Acquisition campaigns (Kierowca C+E Poltrakt, etc.).
FOCUS_OWN_COMPANY_ID = "4f91ce01-f909-4d79-8a83-679c9eae1b78"


def is_focus_personnel_tenant(tenant_id: str | None) -> bool:
    return str(tenant_id or "").strip().lower() == FOCUS_PERSONNEL_TENANT_ID
