"""ADR-036 four trust roles: normalize, ceilings, presets, access_context.

Canonical trust roles: superadmin | administrator | employee | viewer.
Legacy job-title / portal strings are aliases until inventory rows are removed.
"""
from __future__ import annotations

from enum import Enum
from typing import Final

# --- Canonical trust roles (architectural invariant) ---


class TrustRole(str, Enum):
    superadmin = "superadmin"
    administrator = "administrator"
    employee = "employee"
    viewer = "viewer"


CANONICAL_TRUST_ROLES: Final[frozenset[str]] = frozenset(r.value for r in TrustRole)

# Legacy / synonym → canonical trust role (ADR-036 migration map)
TRUST_ROLE_NORMALIZE: Final[dict[str, str]] = {
    "superadmin": TrustRole.superadmin.value,
    "super_admin": TrustRole.superadmin.value,
    "administrator": TrustRole.administrator.value,
    "admin": TrustRole.administrator.value,
    "owner": TrustRole.administrator.value,
    "employee": TrustRole.employee.value,
    "recruiter": TrustRole.employee.value,
    "supervisor": TrustRole.employee.value,
    "manager": TrustRole.employee.value,
    "lead": TrustRole.employee.value,
    "hr": TrustRole.employee.value,
    "hr_officer": TrustRole.employee.value,
    "people_ops": TrustRole.employee.value,
    "compliance_officer": TrustRole.employee.value,
    "compliance": TrustRole.employee.value,
    "docs_officer": TrustRole.employee.value,
    "viewer": TrustRole.viewer.value,
    "user": TrustRole.viewer.value,
    "client_manager": TrustRole.viewer.value,
    "client_processor": TrustRole.viewer.value,
    "client": TrustRole.viewer.value,
    "processor": TrustRole.viewer.value,
}

# Suggested preset when normalizing a legacy job/portal string
LEGACY_TO_PRESET: Final[dict[str, str]] = {
    "recruiter": "recruiter",
    "hr": "hr",
    "hr_officer": "hr",
    "people_ops": "hr",
    "supervisor": "team_lead",
    "manager": "team_lead",
    "lead": "team_lead",
    "compliance_officer": "compliance",
    "compliance": "compliance",
    "docs_officer": "compliance",
    "client_manager": "portal_guest",
    "client_processor": "portal_guest",
    "client": "portal_guest",
    "processor": "portal_guest",
}

PORTAL_LEGACY_ROLES: Final[frozenset[str]] = frozenset(
    {"client_manager", "client_processor", "client", "processor"}
)

JOB_PROXY_ROLES: Final[frozenset[str]] = frozenset(
    {
        "recruiter",
        "supervisor",
        "manager",
        "lead",
        "hr",
        "hr_officer",
        "people_ops",
        "compliance_officer",
        "compliance",
        "docs_officer",
    }
)

AccessContext = str  # "tenant" | "portal"


def normalize_trust_role(role: str | None) -> str:
    raw = str(role or "").strip().lower()
    if not raw:
        return TrustRole.viewer.value
    return TRUST_ROLE_NORMALIZE.get(raw, TrustRole.viewer.value)


def infer_access_context(role: str | None, explicit: str | None = None) -> AccessContext:
    """role ⊥ access_context. Explicit wins; legacy client_* implies portal."""
    if explicit in ("tenant", "portal"):
        return explicit
    raw = str(role or "").strip().lower()
    if raw in PORTAL_LEGACY_ROLES:
        return "portal"
    return "tenant"


def infer_preset_id(role: str | None) -> str | None:
    raw = str(role or "").strip().lower()
    return LEGACY_TO_PRESET.get(raw)


# Capabilities that Employee/Viewer must never receive (trust ceilings)
ADMIN_LOCKED_CAPABILITIES: Final[frozenset[str]] = frozenset(
    {
        "platform.tenants",
        "tenant.settings",
        "users.roles_access",
        "billing.subscription",
    }
)

# Module matrix: administrator is not limited; employee/viewer cannot be given
# "admin-equivalent" by turning every module editable — ceilings are capability-level.
# For module matrix PATCH we still allow operational visible/editable tweaks for
# employee/viewer; we reject patches that target administrator→downgrade via
# empty payload abuse is N/A. Hard reject: granting matrix edits that try to
# set role key outside editable set for tenant admins configuring only employee/viewer.
#
# Tenant admin may edit: employee, viewer, and legacy job/portal columns (migration).
# May not use matrix to grant platform.tenants (not in module matrix anyway).

MATRIX_EDITABLE_BY_TENANT_ADMIN: Final[frozenset[str]] = frozenset(
    {
        "employee",
        "viewer",
        # legacy columns until Phase 3 cleanup
        "recruiter",
        "supervisor",
        "client_manager",
        "client_processor",
        "compliance_officer",
        "hr_officer",
    }
)

MATRIX_LOCKED_ROLES: Final[frozenset[str]] = frozenset(
    {
        "administrator",  # always full ops; not freely reduced to lock admin out of self
        "superadmin",
    }
)


def assert_matrix_role_editable(role: str, *, actor_is_superadmin: bool = False) -> None:
    """Raise ValueError if tenant admin must not edit this role column."""
    r = str(role or "").strip().lower()
    if actor_is_superadmin:
        return
    if r in MATRIX_LOCKED_ROLES:
        raise ValueError(f"trust_ceiling:role_locked:{r}")
    if r not in MATRIX_EDITABLE_BY_TENANT_ADMIN and normalize_trust_role(r) == TrustRole.administrator.value:
        raise ValueError(f"trust_ceiling:role_locked:{r}")


def expand_allowed_roles_for_trust(allowed: set[str]) -> set[str]:
    """Bridge: employee satisfies job-proxy require_roles; viewer does not auto-satisfy portal."""
    out = {str(x).strip().lower() for x in allowed if str(x).strip()}
    if out & JOB_PROXY_ROLES:
        out.add(TrustRole.employee.value)
    return out


def is_portal_actor(role: str | None, access_context: str | None = None) -> bool:
    """True when the actor is in portal context (explicit or legacy client_*)."""
    return infer_access_context(role, access_context) == "portal"


def is_hr_workspace_actor(role: str | None) -> bool:
    """HR operational lane still keyed by legacy role / hr preset (not all employees)."""
    raw = str(role or "").strip().lower()
    if raw in {"hr_officer", "hr", "people_ops"}:
        return True
    return infer_preset_id(raw) == "hr"


def is_team_lead_org_actor(role: str | None) -> bool:
    """Org-proxy supervisors: legacy supervisor/manager or team_lead preset."""
    raw = str(role or "").strip().lower()
    if raw in {"supervisor", "manager", "lead"}:
        return True
    return infer_preset_id(raw) == "team_lead"


def actor_satisfies_role_allowlist(
    *,
    role: str | None,
    allowed: set[str],
    access_context: str | None = None,
) -> bool:
    """True if actor role may pass a require_roles-style allowlist (ADR-036 bridges).

    - Admins are not handled here (callers short-circuit).
    - JOB_PROXY allowlists accept canonical ``employee``.
    - When ``viewer`` is explicitly allowed, any trust-viewer (incl. legacy client_*)
      matches; portal-only endpoints must also use ``require_portal_context``.
    - PORTAL_LEGACY-only allowlists (no ``viewer``) accept ``viewer`` only when
      ``access_context=portal`` (tenant viewers do not inherit portal).
    """
    ur = str(role or "").strip().lower()
    if not ur:
        return False
    allowed_values = expand_allowed_roles_for_trust(allowed)
    if ur in allowed_values:
        return True

    trust = normalize_trust_role(ur)
    if trust == TrustRole.employee.value and TrustRole.employee.value in allowed_values:
        return True

    if trust == TrustRole.viewer.value and TrustRole.viewer.value in allowed_values:
        return True

    if allowed_values & PORTAL_LEGACY_ROLES:
        if trust == TrustRole.viewer.value and is_portal_actor(ur, access_context):
            return True
        if ur in PORTAL_LEGACY_ROLES:
            return True

    return False


# Named presets (starter packs) — module visible/editable defaults for apply
PERMISSION_PRESETS: Final[dict[str, dict[str, dict[str, bool]]]] = {
    "recruiter": {
        "candidates": {"visible": True, "editable": True},
        "companies": {"visible": True, "editable": False},
        "vacancies": {"visible": True, "editable": False},
        "documents": {"visible": True, "editable": True},
        "leads": {"visible": True, "editable": False},
        "services": {"visible": True, "editable": True},
        "client_portal": {"visible": False, "editable": False},
        "hr": {"visible": False, "editable": False},
    },
    "team_lead": {
        "candidates": {"visible": True, "editable": True},
        "companies": {"visible": True, "editable": True},
        "vacancies": {"visible": True, "editable": True},
        "documents": {"visible": True, "editable": True},
        "leads": {"visible": True, "editable": True},
        "services": {"visible": True, "editable": True},
        "client_portal": {"visible": True, "editable": False},
        "hr": {"visible": True, "editable": True},
    },
    "hr": {
        "candidates": {"visible": False, "editable": False},
        "companies": {"visible": False, "editable": False},
        "vacancies": {"visible": False, "editable": False},
        "documents": {"visible": False, "editable": False},
        "leads": {"visible": False, "editable": False},
        "services": {"visible": False, "editable": False},
        "client_portal": {"visible": False, "editable": False},
        "hr": {"visible": True, "editable": True},
    },
    "compliance": {
        "candidates": {"visible": True, "editable": True},
        "companies": {"visible": True, "editable": False},
        "vacancies": {"visible": True, "editable": False},
        "documents": {"visible": True, "editable": True},
        "leads": {"visible": True, "editable": False},
        "services": {"visible": True, "editable": True},
        "client_portal": {"visible": False, "editable": False},
        "hr": {"visible": False, "editable": False},
    },
    "portal_guest": {
        "candidates": {"visible": True, "editable": False},
        "companies": {"visible": True, "editable": False},
        "vacancies": {"visible": True, "editable": False},
        "documents": {"visible": True, "editable": True},
        "leads": {"visible": False, "editable": False},
        "services": {"visible": False, "editable": False},
        "client_portal": {"visible": True, "editable": False},
        "hr": {"visible": False, "editable": False},
    },
}


def list_permission_preset_ids() -> tuple[str, ...]:
    return tuple(PERMISSION_PRESETS.keys())


def get_permission_preset(preset_id: str) -> dict[str, dict[str, bool]]:
    key = str(preset_id or "").strip().lower()
    preset = PERMISSION_PRESETS.get(key)
    if preset is None:
        raise ValueError(f"unknown_permission_preset:{key}")
    return {mod: dict(cell) for mod, cell in preset.items()}


def trust_role_for_preset(preset_id: str) -> str:
    """Presets never invent system roles — portal_guest → viewer, else employee."""
    key = str(preset_id or "").strip().lower()
    if key == "portal_guest":
        return TrustRole.viewer.value
    if key in PERMISSION_PRESETS:
        return TrustRole.employee.value
    raise ValueError(f"unknown_permission_preset:{key}")


# --- Seat / license buckets (ADR-036 §4 monetization) ---
# License columns keep historical names; semantics map to trust seats:
#   max_supervisors → administrator seats
#   max_recruiters  → employee seats
#   max_viewers     → tenant viewer seats
#   max_client_managers → unused for gates (portal guests are non-billable)

BILLABLE_SEAT_QUOTA_ATTR: Final[dict[str, str]] = {
    TrustRole.administrator.value: "max_supervisors",
    TrustRole.employee.value: "max_recruiters",
    TrustRole.viewer.value: "max_viewers",
}

ADMINISTRATOR_SEAT_ROLES: Final[frozenset[str]] = frozenset(
    {
        TrustRole.administrator.value,
        TrustRole.superadmin.value,
        "admin",
        "owner",
    }
)

EMPLOYEE_SEAT_ROLES: Final[frozenset[str]] = frozenset(
    {
        TrustRole.employee.value,
        *JOB_PROXY_ROLES,
        "supervisor",
        "recruiter",
        "hr_officer",
        "compliance_officer",
    }
)

TENANT_VIEWER_SEAT_ROLES: Final[frozenset[str]] = frozenset(
    {
        TrustRole.viewer.value,
        "user",
    }
)


def is_non_billable_portal_seat(
    role: str | None,
    *,
    access_context: str | None = None,
    preset_id: str | None = None,
) -> bool:
    """Portal guests do not consume Admin/Employee/Viewer CRM seats."""
    if str(preset_id or "").strip().lower() == "portal_guest":
        return True
    return is_portal_actor(role, access_context)


def billable_seat_bucket(
    role: str | None,
    *,
    access_context: str | None = None,
    preset_id: str | None = None,
) -> str | None:
    """Return administrator|employee|viewer for seat gates, or None if non-billable."""
    if is_non_billable_portal_seat(
        role, access_context=access_context, preset_id=preset_id
    ):
        return None
    trust = normalize_trust_role(role)
    if trust == TrustRole.superadmin.value:
        return TrustRole.administrator.value
    if trust in BILLABLE_SEAT_QUOTA_ATTR:
        return trust
    return None


def seat_quota_attr_for_role(
    role: str | None,
    *,
    access_context: str | None = None,
    preset_id: str | None = None,
) -> str | None:
    bucket = billable_seat_bucket(
        role, access_context=access_context, preset_id=preset_id
    )
    if bucket is None:
        return None
    return BILLABLE_SEAT_QUOTA_ATTR.get(bucket)


def membership_roles_for_seat_bucket(bucket: str) -> frozenset[str]:
    """Legacy + trust membership.role strings that consume a billable bucket."""
    key = str(bucket or "").strip().lower()
    if key == TrustRole.administrator.value:
        return ADMINISTRATOR_SEAT_ROLES
    if key == TrustRole.employee.value:
        return EMPLOYEE_SEAT_ROLES
    if key == TrustRole.viewer.value:
        return TENANT_VIEWER_SEAT_ROLES
    return frozenset()
