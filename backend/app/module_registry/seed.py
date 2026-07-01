"""Seed Module Registry baseline and tenant installation rows."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.v1.tenants import service as tenant_service
from backend.app.models.module_registry import (
    INSTALLATION_SOURCE_MIGRATION,
    INSTALLATION_SOURCE_SYSTEM,
    INSTALLATION_STATE_ENABLED,
    INSTALLATION_STATE_SUSPENDED,
    MODULE_REGISTRY_VERSION,
    MODULE_STATUS_REGISTERED,
    ModuleCapability,
    ModuleDependency,
    ModuleRegistry,
    TenantModuleInstallation,
)
from backend.app.models.tenant import Tenant
from backend.app.module_registry.manifest import BASELINE_MODULE_CODES, module_registry_manifest

_PLATFORM_ALWAYS_ENABLED = {"documents", "process_engine", "field_registry"}


def _legacy_module_enabled(tenant: Tenant, module_code: str) -> bool:
    settings = tenant.settings if isinstance(tenant.settings, dict) else {}
    raw_modules = settings.get("modules") if isinstance(settings, dict) else {}
    raw_modules = raw_modules if isinstance(raw_modules, dict) else {}

    if module_code in _PLATFORM_ALWAYS_ENABLED:
        return True
    if module_code == "recruitment":
        if "recruitment" in raw_modules:
            return bool(raw_modules["recruitment"])
        triad = ("candidates", "leads", "vacancies")
        return all(bool(raw_modules.get(key, True)) for key in triad)
    if module_code in raw_modules:
        return bool(raw_modules[module_code])

    snapshot = tenant_service.get_module_settings_snapshot(tenant)
    if module_code in snapshot:
        return bool(snapshot[module_code])
    return True


async def ensure_module_registry_baseline(db: AsyncSession) -> dict[str, int]:
    modules = 0
    capabilities = 0
    dependencies = 0
    for row in module_registry_manifest():
        module_code = str(row["module_code"])
        existing = await db.execute(
            select(ModuleRegistry).where(ModuleRegistry.module_code == module_code).limit(1)
        )
        module = existing.scalar_one_or_none()
        if module is None:
            module = ModuleRegistry(id=str(uuid4()), module_code=module_code)
            db.add(module)
        module.kind = str(row["kind"])
        module.display_name = str(row["display_name"])
        module.owner = str(row["owner"])
        module.status = MODULE_STATUS_REGISTERED
        module.registry_version = MODULE_REGISTRY_VERSION
        module.manifest = dict(row.get("manifest") or {})
        module.is_system = True
        modules += 1

        for capability_row in row.get("capabilities") or []:
            capability_code = str(capability_row["capability_code"])
            loaded = await db.execute(
                select(ModuleCapability).where(
                    ModuleCapability.module_code == module_code,
                    ModuleCapability.capability_code == capability_code,
                ).limit(1)
            )
            capability = loaded.scalar_one_or_none()
            if capability is None:
                capability = ModuleCapability(id=str(uuid4()), module_code=module_code, capability_code=capability_code)
                db.add(capability)
            capability.kind = str(capability_row.get("kind") or "route_access")
            capability.display_name = str(capability_row.get("display_name") or capability_code)
            capability.description = capability_row.get("description")
            capability.default_enabled = bool(capability_row.get("default_enabled", True))
            capability.config = dict(capability_row.get("config") or {})
            capabilities += 1

        for dependency_row in row.get("dependencies") or []:
            dependency_module_code = str(dependency_row["dependency_module_code"])
            dependency_kind = str(dependency_row.get("dependency_kind") or "optional")
            loaded = await db.execute(
                select(ModuleDependency).where(
                    ModuleDependency.module_code == module_code,
                    ModuleDependency.dependency_module_code == dependency_module_code,
                    ModuleDependency.dependency_kind == dependency_kind,
                ).limit(1)
            )
            dependency = loaded.scalar_one_or_none()
            if dependency is None:
                dependency = ModuleDependency(
                    id=str(uuid4()),
                    module_code=module_code,
                    dependency_module_code=dependency_module_code,
                    dependency_kind=dependency_kind,
                )
                db.add(dependency)
            dependency.capability_code = dependency_row.get("capability_code")
            dependency.config = dict(dependency_row.get("config") or {})
            dependencies += 1
    await db.flush()
    return {"modules": modules, "capabilities": capabilities, "dependencies": dependencies}


async def ensure_tenant_module_installations(db: AsyncSession, tenant_id: str) -> dict[str, Any]:
    await ensure_module_registry_baseline(db)
    tenant = await db.get(Tenant, str(tenant_id))
    if tenant is None:
        return {"tenant_id": str(tenant_id), "seeded": False, "modules": 0}

    existing_rows = (
        await db.execute(
            select(TenantModuleInstallation).where(TenantModuleInstallation.tenant_id == str(tenant_id))
        )
    ).scalars().all()
    existing_by_code = {row.module_code: row for row in existing_rows}

    created = 0
    for module_code in BASELINE_MODULE_CODES:
        row = existing_by_code.get(module_code)
        enabled = _legacy_module_enabled(tenant, module_code)
        desired_state = INSTALLATION_STATE_ENABLED if enabled else INSTALLATION_STATE_SUSPENDED
        if row is None:
            row = TenantModuleInstallation(
                id=str(uuid4()),
                tenant_id=str(tenant_id),
                module_code=module_code,
                state=desired_state,
                source=INSTALLATION_SOURCE_SYSTEM if module_code in _PLATFORM_ALWAYS_ENABLED else INSTALLATION_SOURCE_MIGRATION,
                metadata_json={"source": "module_registry_p1_seed"},
            )
            db.add(row)
            created += 1
        else:
            if row.state not in {INSTALLATION_STATE_ENABLED, INSTALLATION_STATE_SUSPENDED}:
                continue
            row.state = desired_state
            metadata = dict(row.metadata_json or {})
            metadata.setdefault("source", "module_registry_p1_seed")
            row.metadata_json = metadata
    await db.flush()
    return {"tenant_id": str(tenant_id), "seeded": created > 0, "modules": len(BASELINE_MODULE_CODES)}
