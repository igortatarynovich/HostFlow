"""Seed Entity Profile Definition Registry defaults."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.entity_profile.manifests.recruitment import recruitment_module_entity_profiles
from backend.app.entity_profile.manifests.service_sales import service_sales_module_entity_profiles
from backend.app.entity_profile.registry import EntityProfileRegistry
from backend.app.field_registry.seed import ensure_platform_field_registry_catalog, ensure_tenant_field_registry_defaults
from backend.app.models.entity_profile import EpEntityProfile, PLATFORM_TENANT_SCOPE


def _entity_profile_manifests() -> list[dict]:
    return [*recruitment_module_entity_profiles(), *service_sales_module_entity_profiles()]


async def _has_all_manifest_profiles(db: AsyncSession, tenant_id: str, manifests: list[dict]) -> bool:
    profile_codes = {
        str(row.get("profile_code") or "").strip()
        for row in manifests
        if str(row.get("profile_code") or "").strip()
    }
    if not profile_codes:
        return True
    existing_codes = set(
        (
            await db.execute(
                select(EpEntityProfile.profile_code).where(
                    EpEntityProfile.tenant_id == str(tenant_id),
                    EpEntityProfile.profile_code.in_(profile_codes),
                )
            )
        )
        .scalars()
        .all()
    )
    return profile_codes.issubset(existing_codes)


async def ensure_platform_entity_profile_catalog(db: AsyncSession) -> None:
    """Register platform-global Entity Profile manifests (requires Field Registry catalog)."""
    await ensure_platform_field_registry_catalog(db)
    for profile in _entity_profile_manifests():
        await EntityProfileRegistry.register_profile(db, profile, tenant_id=PLATFORM_TENANT_SCOPE)


async def ensure_tenant_entity_profile_defaults(db: AsyncSession, tenant_id: str) -> dict:
    """Register tenant-scoped Entity Profile rows (P1: mirrors platform baseline)."""
    await ensure_tenant_field_registry_defaults(db, tenant_id)

    manifests = _entity_profile_manifests()
    had_all_profiles = await _has_all_manifest_profiles(db, str(tenant_id), manifests)

    results = {
        profile["profile_code"]: await EntityProfileRegistry.register_profile(
            db, profile, tenant_id=str(tenant_id)
        )
        for profile in manifests
    }
    return {
        "tenant_id": str(tenant_id),
        "seeded": not had_all_profiles,
        "profiles": results,
    }
