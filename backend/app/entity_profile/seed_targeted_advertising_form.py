"""Seed targeted advertising public intake form + intake source bindings (Stage Sales Intake 1)."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.entity_profile.provision_targeted_advertising import (
    TARGETED_ADVERTISING_FORM_SLUG,
    TARGETED_ADVERTISING_FORM_TITLE,
    recover_targeted_advertising_capability,
)

__all__ = [
    "TARGETED_ADVERTISING_FORM_SLUG",
    "TARGETED_ADVERTISING_FORM_TITLE",
    "ensure_tenant_targeted_advertising_intake_form",
]


async def ensure_tenant_targeted_advertising_intake_form(db: AsyncSession, tenant_id: str) -> None:
    """Lazy recovery for legacy services tenants; does not overwrite tenant-owned form settings."""
    await recover_targeted_advertising_capability(db, tenant_id)
