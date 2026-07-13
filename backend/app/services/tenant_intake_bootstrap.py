"""Tenant provisioning for intake entity profiles and launch-search role defaults."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def ensure_tenant_entity_profiles_ready(db: AsyncSession, *, tenant_id: str) -> dict[str, Any]:
    """Idempotent: field registry + entity profile manifests for a tenant."""
    from backend.app.entity_profile.seed import ensure_tenant_entity_profile_defaults

    result = await ensure_tenant_entity_profile_defaults(db, str(tenant_id))
    await db.flush()
    return result


async def ensure_tenant_intake_bootstrap_defaults(
    db: AsyncSession,
    *,
    tenant_id: str,
) -> dict[str, Any]:
    """
    Provision intake-related tenant defaults (registration, trial activation, onboarding).

    Safe to call multiple times; each step is idempotent.
    Caller is responsible for commit/rollback.
    """
    tid = str(tenant_id)
    results: dict[str, Any] = {"tenant_id": tid}

    try:
        from backend.app.field_registry.seed import ensure_tenant_field_registry_defaults

        await ensure_tenant_field_registry_defaults(db, tid)
        results["field_registry"] = "ok"
    except Exception as exc:
        logger.warning("[tenant_intake_bootstrap] field registry failed tenant=%s: %s", tid, exc)
        results["field_registry"] = f"error: {exc}"

    try:
        results["entity_profiles"] = await ensure_tenant_entity_profiles_ready(db, tenant_id=tid)
    except Exception as exc:
        logger.warning("[tenant_intake_bootstrap] entity profiles failed tenant=%s: %s", tid, exc)
        results["entity_profiles"] = f"error: {exc}"

    try:
        from backend.app.seed_candidate_profiles import ensure_driver_ce_default_profile

        await ensure_driver_ce_default_profile(db, tid)
        results["driver_ce_profile"] = "ok"
    except Exception as exc:
        logger.warning("[tenant_intake_bootstrap] driver_ce profile failed tenant=%s: %s", tid, exc)
        results["driver_ce_profile"] = f"error: {exc}"

    try:
        from backend.app.services.launch_search_role_defaults import ensure_launch_search_role_defaults

        results["launch_search"] = await ensure_launch_search_role_defaults(db, tid)
    except Exception as exc:
        logger.warning("[tenant_intake_bootstrap] launch-search defaults failed tenant=%s: %s", tid, exc)
        results["launch_search"] = f"error: {exc}"

    return results
