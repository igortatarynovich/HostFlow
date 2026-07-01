"""Tenant-level HR feature flags (settings JSON)."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.tenant import Tenant


def delayed_hr_workforce_creation_from_settings(settings: object | None) -> bool:
    if not isinstance(settings, dict):
        return False
    return bool(settings.get("delayed_hr_workforce_creation"))


async def delayed_hr_workforce_creation_enabled(db: AsyncSession, tenant_id: str) -> bool:
    tenant = await db.get(Tenant, str(tenant_id).strip())
    if not tenant:
        return False
    return delayed_hr_workforce_creation_from_settings(tenant.settings)
