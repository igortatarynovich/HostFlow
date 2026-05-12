"""Company-level effective modules (tenant AND company)."""

from __future__ import annotations

from types import SimpleNamespace

from backend.app.services.company_module_access import get_effective_company_modules


def test_effective_modules_all_tenant_when_company_override_empty() -> None:
    tenant = SimpleNamespace(settings={})
    company = SimpleNamespace(enabled_modules=None)
    eff = get_effective_company_modules(tenant, company)  # type: ignore[arg-type]
    assert eff["fleet"] is True
    assert eff["finance"] is True


def test_company_can_disable_module() -> None:
    tenant = SimpleNamespace(settings={})
    company = SimpleNamespace(enabled_modules={"fleet": False, "finance": False})
    eff = get_effective_company_modules(tenant, company)  # type: ignore[arg-type]
    assert eff["fleet"] is False
    assert eff["finance"] is False
    assert eff["hr"] is True


def test_tenant_off_company_cannot_enable() -> None:
    tenant = SimpleNamespace(settings={"modules": {"fleet": False}})
    company = SimpleNamespace(enabled_modules={"fleet": True})
    eff = get_effective_company_modules(tenant, company)  # type: ignore[arg-type]
    assert eff["fleet"] is False
