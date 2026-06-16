"""Seed Field Registry defaults for platform catalog and tenants."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.field_registry.manifests.crm import crm_module_manifest
from backend.app.field_registry.manifests.fleet import fleet_module_manifest
from backend.app.field_registry.manifests.hr import hr_module_manifest
from backend.app.field_registry.manifests.platform import platform_module_manifest
from backend.app.field_registry.manifests.recruitment import recruitment_module_manifest
from backend.app.field_registry.registry import FieldRegistry
from backend.app.models.field_registry import PLATFORM_TENANT_SCOPE, FrCanonicalField


def _field_manifests() -> list[dict]:
    return [
        platform_module_manifest(),
        recruitment_module_manifest(),
        crm_module_manifest(),
        hr_module_manifest(),
        fleet_module_manifest(),
    ]


async def _has_all_manifest_fields(db: AsyncSession, tenant_id: str, manifests: list[dict]) -> bool:
    qualified_codes = {
        str(row.get("qualified_code") or "").strip()
        for manifest in manifests
        for row in manifest.get("canonical_fields") or []
        if str(row.get("qualified_code") or "").strip()
    }
    if not qualified_codes:
        return True
    existing_codes = set(
        (
            await db.execute(
                select(FrCanonicalField.qualified_code).where(
                    FrCanonicalField.tenant_id == str(tenant_id),
                    FrCanonicalField.qualified_code.in_(qualified_codes),
                )
            )
        )
        .scalars()
        .all()
    )
    return qualified_codes.issubset(existing_codes)


async def ensure_platform_field_registry_catalog(db: AsyncSession) -> None:
    """Register platform-global field registry manifests (tenant scope = empty string)."""
    for manifest in _field_manifests():
        await FieldRegistry.register_module(db, manifest, tenant_id=PLATFORM_TENANT_SCOPE)


async def ensure_tenant_field_registry_defaults(db: AsyncSession, tenant_id: str) -> dict:
    """Register tenant-scoped field registry rows (P1: mirrors platform baseline)."""
    await ensure_platform_field_registry_catalog(db)

    manifests = _field_manifests()
    had_all_fields = await _has_all_manifest_fields(db, str(tenant_id), manifests)

    results = {
        manifest["module"]: await FieldRegistry.register_module(db, manifest, tenant_id=str(tenant_id))
        for manifest in manifests
    }
    return {
        "tenant_id": str(tenant_id),
        "seeded": not had_all_fields,
        "recruitment_fields": results["recruitment"]["canonical_fields"],
        "crm_fields": results["crm"]["canonical_fields"],
        "hr_fields": results["hr"]["canonical_fields"],
        "fleet_fields": results["fleet"]["canonical_fields"],
    }
