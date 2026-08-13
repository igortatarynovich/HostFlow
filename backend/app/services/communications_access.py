from __future__ import annotations

from typing import Any, Dict, Iterable, Literal, Set

from fastapi import HTTPException, status

from backend.app.auth.deps import Role, UserCtx
from backend.app.auth.trust_roles import (
    TrustRole,
    actor_satisfies_role_allowlist,
    is_team_lead_org_actor,
    normalize_trust_role,
)
from backend.app.models.tenant import Tenant

CommFeature = Literal[
    "messages",
    "email",
    "calendar",
    "planner",
    "teamAvailability",
    "myAvailability",
    "timeOffRequests",
    "communicationsAdmin",
]


_ROLE_ALIASES: Dict[str, str] = {
    "admin": "administrator",
    "owner": "administrator",
    "superadmin": "superadmin",
    "manager": "supervisor",
    "hr": "recruiter",
    "user": "viewer",
    "processor": "client_processor",
}

_FEATURE_TO_MODULE: Dict[CommFeature, str] = {
    "messages": "messages",
    "email": "email",
    "calendar": "calendar",
    "planner": "planner",
    "teamAvailability": "availability",
    "myAvailability": "availability",
    "timeOffRequests": "timeOff",
    "communicationsAdmin": "communicationsAdmin",
}

_FEATURE_TO_ROLE_KEY: Dict[CommFeature, str] = {
    "messages": "messages",
    "email": "email",
    "calendar": "calendar",
    "planner": "planner",
    "teamAvailability": "teamAvailability",
    "myAvailability": "myAvailability",
    "timeOffRequests": "timeOffRequests",
    "communicationsAdmin": "communicationsAdmin",
}

# Privileged: trust admin / team_lead only (do not treat every employee as allowed).
_LEAD_SCOPED_FEATURES: frozenset[str] = frozenset({"teamAvailability", "communicationsAdmin"})

# Keep aligned with frontend DEFAULT_COMMUNICATIONS_SETTINGS.access.roles.
# Canonical trust roles + legacy aliases for stored tenant overrides.
_DEFAULT_ROLE_ACCESS: Dict[str, list[str]] = {
    "messages": [
        "administrator",
        "employee",
        "viewer",
        "supervisor",
        "recruiter",
        "client_manager",
        "client_processor",
    ],
    "email": [
        "administrator",
        "employee",
        "viewer",
        "supervisor",
        "recruiter",
        "client_manager",
    ],
    "calendar": [
        "administrator",
        "employee",
        "viewer",
        "supervisor",
        "recruiter",
        "client_manager",
    ],
    "planner": [
        "administrator",
        "employee",
        "viewer",
        "supervisor",
        "recruiter",
        "client_manager",
    ],
    "teamAvailability": ["administrator", "supervisor"],
    "myAvailability": [
        "administrator",
        "employee",
        "viewer",
        "supervisor",
        "recruiter",
        "client_manager",
        "client_processor",
    ],
    "timeOffRequests": [
        "administrator",
        "employee",
        "viewer",
        "supervisor",
        "recruiter",
        "client_manager",
        "client_processor",
    ],
    "communicationsAdmin": ["administrator", "supervisor"],
}


def _norm_role(value: str | None) -> str:
    role = str(value or "").strip().lower()
    if not role:
        return "viewer"
    return _ROLE_ALIASES.get(role, role)


def _user_keys(ctx: UserCtx) -> Set[str]:
    raw_payload = getattr(ctx, "raw", None)
    raw_payload = raw_payload if isinstance(raw_payload, dict) else {}
    keys: Set[str] = set()
    for raw in (
        getattr(ctx, "sub", None),
        getattr(ctx, "email", None),
        raw_payload.get("user_id"),
        raw_payload.get("id"),
    ):
        v = str(raw or "").strip()
        if v:
            keys.add(v)
    return keys


def _iter_allowed_roles(value: Any) -> Iterable[str]:
    if not isinstance(value, list):
        return []
    return [_norm_role(str(v or "")) for v in value if str(v or "").strip()]


def _extract_comm_settings(tenant: Tenant | None) -> Dict[str, Any]:
    if tenant is None:
        return {}
    root = tenant.settings if isinstance(getattr(tenant, "settings", None), dict) else {}
    comm = root.get("communications")
    return comm if isinstance(comm, dict) else {}


def _feature_role_allowed(
    *,
    current_user: UserCtx,
    feature: CommFeature,
    allowed: list[str],
) -> bool:
    role = getattr(current_user, "role", None)
    trust = normalize_trust_role(role)
    if trust in {TrustRole.superadmin.value, TrustRole.administrator.value}:
        return True
    preset_id = getattr(current_user, "preset_id", None)
    access_context = getattr(current_user, "access_context", None)
    if feature in _LEAD_SCOPED_FEATURES:
        return is_team_lead_org_actor(role, preset_id)
    if not allowed:
        return True
    return actor_satisfies_role_allowlist(
        role=role,
        allowed=set(allowed),
        access_context=access_context,
    )


def assert_comm_feature_access(
    *,
    tenant: Tenant | None,
    current_user: UserCtx,
    feature: CommFeature,
    tenant_id: str | None = None,
) -> None:
    role = _norm_role(getattr(current_user, "role", None))
    # Platform superadmin bypass.
    if role == Role.superadmin.value or normalize_trust_role(role) == TrustRole.superadmin.value:
        return

    # Enforce tenant context consistency for non-superadmin users.
    token_tenant = str(getattr(current_user, "tenant_id", "") or "").strip()
    if tenant_id and token_tenant and token_tenant != str(tenant_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden for tenant")

    comm = _extract_comm_settings(tenant)

    module_key = _FEATURE_TO_MODULE[feature]
    role_key = _FEATURE_TO_ROLE_KEY[feature]

    modules = comm.get("entitlements", {}).get("modules", {}) if isinstance(comm.get("entitlements"), dict) else {}
    module_cfg = modules.get(module_key) if isinstance(modules, dict) else None
    if isinstance(module_cfg, dict):
        if module_cfg.get("enabled") is False:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Communications feature disabled: {module_key}",
            )

    # User override has priority over role access.
    access = comm.get("access") if isinstance(comm.get("access"), dict) else {}
    overrides = access.get("usersOverrides") if isinstance(access.get("usersOverrides"), dict) else {}
    for key in _user_keys(current_user):
        row = overrides.get(key)
        if isinstance(row, dict) and role_key in row:
            if bool(row.get(role_key)):
                return
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied by user override: {role_key}",
            )

    roles = access.get("roles") if isinstance(access.get("roles"), dict) else {}
    allowed = list(_iter_allowed_roles(roles.get(role_key))) if isinstance(roles, dict) else []
    if not allowed:
        allowed = list(_iter_allowed_roles(_DEFAULT_ROLE_ACCESS.get(role_key, [])))
    if not _feature_role_allowed(current_user=current_user, feature=feature, allowed=allowed):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied for role: {role_key}",
        )
