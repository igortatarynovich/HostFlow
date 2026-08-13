"""Tenant-config readers for the communications module.

Pure pluck-from-``tenant.settings`` helpers — no DB access, no side effects.
Centralised here so RBAC / SLA / escalation logic can be reused across
per-topic route modules without import cycles. Extracted in Phase 1
god-module split, step 3/N. Re-exported from
``backend.app.api.v1.communications`` for backward compatibility.
"""

from __future__ import annotations

from typing import Any, Dict

from backend.app.models.tenant import Tenant

__all__ = [
    "_comm_settings_channels",
    "_comm_settings_root",
    "_tenant_sla_escalation_targets",
    "_tenant_comm_allowed_roles",
    "_canonical_membership_role_for_escalation",
]


def _comm_settings_channels(tenant: Tenant | None) -> Dict[str, Any]:
    if tenant is None:
        return {}
    root = tenant.settings if isinstance(getattr(tenant, "settings", None), dict) else {}
    comm = root.get("communications")
    comm = comm if isinstance(comm, dict) else {}
    channels = comm.get("channels")
    return channels if isinstance(channels, dict) else {}


def _comm_settings_root(tenant: Tenant | None) -> Dict[str, Any]:
    if tenant is None:
        return {}
    root = tenant.settings if isinstance(getattr(tenant, "settings", None), dict) else {}
    comm = root.get("communications")
    return comm if isinstance(comm, dict) else {}


def _tenant_sla_escalation_targets(tenant: Tenant | None) -> set[str]:
    comm = _comm_settings_root(tenant)
    sla = comm.get("sla")
    sla = sla if isinstance(sla, dict) else {}
    raw = sla.get("escalationTargets")
    if not isinstance(raw, list):
        return set()
    out: set[str] = set()
    for item in raw:
        value = str(item or "").strip()
        if value:
            out.add(value)
    return out


def _tenant_comm_allowed_roles(tenant: Tenant | None) -> set[str]:
    comm = _comm_settings_root(tenant)
    access = comm.get("access")
    access = access if isinstance(access, dict) else {}
    roles = access.get("roles")
    roles = roles if isinstance(roles, dict) else {}
    out: set[str] = set()
    for _, value in roles.items():
        if not isinstance(value, list):
            continue
        for role in value:
            normalized = str(role or "").strip().lower()
            if normalized:
                out.add(normalized)
    return out


def _canonical_membership_role_for_escalation(role_key: str) -> str:
    k = str(role_key or "").strip().lower()
    if not k:
        return ""
    aliases = {
        "admin": "administrator",
        "owner": "administrator",
        "manager": "team_lead",
        "supervisor": "team_lead",
        "lead": "team_lead",
        "hr": "hr",
        "hr_officer": "hr",
        "recruiter": "employee",
        "client": "viewer",
        "processor": "viewer",
        "client_manager": "viewer",
        "client_processor": "viewer",
    }
    return aliases.get(k, k)
