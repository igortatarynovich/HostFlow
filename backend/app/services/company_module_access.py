"""Company-level module access layered on tenant subscription modules (ADR-003 / ADR-004)."""

from __future__ import annotations

from typing import Any, Dict, Optional

from backend.app.api.v1.tenants import service as tenant_service
from backend.app.models.company import Company
from backend.app.models.tenant import Tenant

_RECRUITMENT_TRIAD = ("candidates", "leads", "vacancies")


def _raw_tenant_modules(tenant: Tenant) -> Dict[str, Any]:
    settings = tenant.settings if isinstance(tenant.settings, dict) else {}
    raw = settings.get("modules") if isinstance(settings, dict) else None
    return raw if isinstance(raw, dict) else {}


def _tenant_recruitment_enabled(tenant: Tenant, tenant_mods: Dict[str, bool]) -> bool:
    """Derived recruitment product flag (triad unless explicitly stored on tenant)."""
    raw = _raw_tenant_modules(tenant)
    if "recruitment" in raw:
        return bool(raw["recruitment"])
    return all(bool(tenant_mods.get(key, True)) for key in _RECRUITMENT_TRIAD)


def _apply_company_recruitment_override(
    tenant_recruitment_on: bool,
    company_raw: Optional[dict],
) -> bool:
    if not isinstance(company_raw, dict) or not company_raw:
        return bool(tenant_recruitment_on)
    if "recruitment" in company_raw:
        return bool(tenant_recruitment_on) and bool(company_raw["recruitment"])
    triad_overrides = [company_raw[key] for key in _RECRUITMENT_TRIAD if key in company_raw]
    if triad_overrides:
        return bool(tenant_recruitment_on) and all(bool(value) for value in triad_overrides)
    return bool(tenant_recruitment_on)


def get_effective_company_modules(tenant: Tenant, company: Optional[Company]) -> Dict[str, bool]:
    """Effective modules for a company: tenant modules AND company overrides.

    ``company.enabled_modules`` is an optional dict of module_key -> bool.
    Missing keys default to True (company does not restrict relative to tenant).
    ``None`` / empty dict means «all tenant modules apply».
    """
    tenant_mods = tenant_service.get_module_settings_snapshot(tenant)
    tenant_recruitment_on = _tenant_recruitment_enabled(tenant, tenant_mods)
    company_raw = getattr(company, "enabled_modules", None) if company is not None else None
    company_raw = company_raw if isinstance(company_raw, dict) else None

    out: Dict[str, bool] = dict(tenant_mods)
    out["recruitment"] = _apply_company_recruitment_override(tenant_recruitment_on, company_raw)

    if not company_raw:
        return out

    for key, tenant_on in tenant_mods.items():
        out[key] = bool(tenant_on) and bool(company_raw.get(key, True))

    out["recruitment"] = _apply_company_recruitment_override(tenant_recruitment_on, company_raw)

    for key, company_on in company_raw.items():
        if key in tenant_mods or key in _RECRUITMENT_TRIAD or key == "recruitment":
            continue
        out[key] = bool(company_on)

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
