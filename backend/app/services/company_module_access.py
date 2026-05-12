"""Company-level module access layered on tenant subscription modules (ADR-003 / ADR-004)."""

from __future__ import annotations

from typing import Any, Dict, Optional

from backend.app.api.v1.tenants import service as tenant_service
from backend.app.models.company import Company
from backend.app.models.tenant import Tenant


def get_effective_company_modules(tenant: Tenant, company: Optional[Company]) -> Dict[str, bool]:
    """Effective modules for a company: tenant modules AND company overrides.

    ``company.enabled_modules`` is an optional dict of module_key -> bool.
    Missing keys default to True (company does not restrict relative to tenant).
    ``None`` / empty dict means «all tenant modules apply».
    """
    tenant_mods = tenant_service.get_module_settings_snapshot(tenant)
    if company is None:
        return dict(tenant_mods)
    raw = getattr(company, "enabled_modules", None)
    if not isinstance(raw, dict) or not raw:
        return dict(tenant_mods)
    out: Dict[str, bool] = {}
    for key, tenant_on in tenant_mods.items():
        company_on = bool(raw.get(key, True))
        out[key] = bool(tenant_on) and company_on
    return out


def company_allows_module(tenant: Tenant, company: Optional[Company], module_key: str) -> bool:
    return bool(get_effective_company_modules(tenant, company).get(module_key, False))


def normalize_company_enabled_modules_payload(value: Any) -> Optional[Dict[str, bool]]:
    """Accept partial dict from API; return None to clear override."""
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ValueError("enabled_modules must be a dict or null")
    out: Dict[str, bool] = {}
    for k, v in value.items():
        key = str(k or "").strip()
        if not key:
            continue
        out[key] = bool(v)
    return out
