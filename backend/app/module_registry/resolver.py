"""Read-only Module Registry resolver (P1)."""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.v1.tenants import service as tenant_service
from backend.app.models.module_registry import (
    INSTALLATION_STATE_ENABLED,
    INSTALLATION_STATE_INSTALLED,
    MODULE_STATUS_REGISTERED,
    ModuleCapability,
    ModuleDependency,
    ModuleRegistry,
    TenantModuleInstallation,
)
from backend.app.models.tenant import Tenant
from backend.app.module_registry.manifest import BASELINE_MODULE_CODES

_INSTALLED_STATES = {INSTALLATION_STATE_ENABLED, INSTALLATION_STATE_INSTALLED}
_PLATFORM_ALWAYS_ENABLED = {"documents", "process_engine", "field_registry"}


def module_to_dict(module: ModuleRegistry) -> dict[str, Any]:
    return {
        "id": module.id,
        "module_code": module.module_code,
        "kind": module.kind,
        "display_name": module.display_name,
        "owner": module.owner,
        "status": module.status,
        "registry_version": module.registry_version,
        "manifest": dict(module.manifest or {}),
        "is_system": bool(module.is_system),
    }


def capability_to_dict(capability: ModuleCapability) -> dict[str, Any]:
    return {
        "id": capability.id,
        "module_code": capability.module_code,
        "capability_code": capability.capability_code,
        "kind": capability.kind,
        "display_name": capability.display_name,
        "description": capability.description,
        "default_enabled": bool(capability.default_enabled),
        "config": dict(capability.config or {}),
    }


def dependency_to_dict(dependency: ModuleDependency) -> dict[str, Any]:
    return {
        "id": dependency.id,
        "module_code": dependency.module_code,
        "dependency_module_code": dependency.dependency_module_code,
        "dependency_kind": dependency.dependency_kind,
        "capability_code": dependency.capability_code,
        "config": dict(dependency.config or {}),
    }


async def is_module_installed(db: AsyncSession, tenant_id: str, module_code: str) -> bool:
    code = str(module_code or "").strip()
    if not code:
        return False
    row = (
        await db.execute(
            select(TenantModuleInstallation).where(
                TenantModuleInstallation.tenant_id == str(tenant_id),
                TenantModuleInstallation.module_code == code,
            ).limit(1)
        )
    ).scalar_one_or_none()
    if row is not None:
        return bool(row.state in _INSTALLED_STATES)
    return await _legacy_module_installed(db, tenant_id=str(tenant_id), module_code=code)


async def list_available_module_codes(
    db: AsyncSession,
    *,
    tenant_id: str,
    module_codes: list[str] | tuple[str, ...] | set[str],
) -> set[str]:
    """Return installed/enabled module codes, registry-first with legacy fallback."""
    out: set[str] = set()
    for module_code in module_codes:
        code = str(module_code or "").strip()
        if code and await is_module_installed(db, tenant_id=str(tenant_id), module_code=code):
            out.add(code)
    return out


async def _legacy_module_installed(db: AsyncSession, *, tenant_id: str, module_code: str) -> bool:
    if module_code in _PLATFORM_ALWAYS_ENABLED:
        return True
    tenant = await db.get(Tenant, str(tenant_id))
    if tenant is None:
        return False
    settings = tenant.settings if isinstance(tenant.settings, dict) else {}
    raw_modules = settings.get("modules") if isinstance(settings, dict) else {}
    raw_modules = raw_modules if isinstance(raw_modules, dict) else {}
    if module_code == "recruitment":
        if "recruitment" in raw_modules:
            return bool(raw_modules["recruitment"])
        return all(bool(raw_modules.get(key, True)) for key in ("candidates", "leads", "vacancies"))
    if module_code in raw_modules:
        return bool(raw_modules[module_code])
    snapshot = tenant_service.get_module_settings_snapshot(tenant)
    if module_code in snapshot:
        return bool(snapshot[module_code])
    return module_code in BASELINE_MODULE_CODES


async def list_installed_modules(
    db: AsyncSession,
    *,
    tenant_id: str,
    include_capabilities: bool = True,
) -> list[dict[str, Any]]:
    rows = (
        await db.execute(
            select(ModuleRegistry, TenantModuleInstallation)
            .join(
                TenantModuleInstallation,
                TenantModuleInstallation.module_code == ModuleRegistry.module_code,
            )
            .where(
                TenantModuleInstallation.tenant_id == str(tenant_id),
                ModuleRegistry.status == MODULE_STATUS_REGISTERED,
            )
            .order_by(ModuleRegistry.module_code.asc())
        )
    ).all()
    module_codes = [module.module_code for module, _installation in rows]

    capabilities_by_module: dict[str, list[dict[str, Any]]] = {code: [] for code in module_codes}
    dependencies_by_module: dict[str, list[dict[str, Any]]] = {code: [] for code in module_codes}
    if module_codes and include_capabilities:
        capability_rows = (
            await db.execute(
                select(ModuleCapability)
                .where(ModuleCapability.module_code.in_(module_codes))
                .order_by(ModuleCapability.module_code.asc(), ModuleCapability.capability_code.asc())
            )
        ).scalars().all()
        for capability in capability_rows:
            capabilities_by_module.setdefault(capability.module_code, []).append(capability_to_dict(capability))

        dependency_rows = (
            await db.execute(
                select(ModuleDependency)
                .where(ModuleDependency.module_code.in_(module_codes))
                .order_by(ModuleDependency.module_code.asc(), ModuleDependency.dependency_module_code.asc())
            )
        ).scalars().all()
        for dependency in dependency_rows:
            dependencies_by_module.setdefault(dependency.module_code, []).append(dependency_to_dict(dependency))

    out: list[dict[str, Any]] = []
    for module, installation in rows:
        payload = {
            **module_to_dict(module),
            "tenant_id": installation.tenant_id,
            "installation_state": installation.state,
            "installation_source": installation.source,
            "installed": installation.state in _INSTALLED_STATES,
            "settings_json": dict(installation.settings_json or {}),
            "metadata_json": dict(installation.metadata_json or {}),
        }
        if include_capabilities:
            payload["capabilities"] = capabilities_by_module.get(module.module_code, [])
            payload["dependencies"] = dependencies_by_module.get(module.module_code, [])
        out.append(payload)
    return out
