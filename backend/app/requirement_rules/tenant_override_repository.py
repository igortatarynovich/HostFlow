"""Tenant requirement override persistence (P3B)."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.tenant_requirement_override import TenantRequirementOverride
from backend.app.requirement_rules.constants import OVERRIDE_STATUS_ACTIVE
from backend.app.requirement_rules.tenant_override_source import tenant_override_row_to_dict


async def list_active_tenant_requirement_overrides(
    db: AsyncSession,
    *,
    tenant_id: str,
    entity_profile_code: str,
    context: str,
    stage_code: str | None = None,
) -> list[dict[str, Any]]:
    tid = str(tenant_id).strip()
    profile_code = str(entity_profile_code or "").strip()
    ctx = str(context or "").strip().lower()
    rows = (
        await db.execute(
            select(TenantRequirementOverride).where(
                TenantRequirementOverride.tenant_id == tid,
                TenantRequirementOverride.status == OVERRIDE_STATUS_ACTIVE,
            )
        )
    ).scalars().all()
    out: list[dict[str, Any]] = []
    for row in rows:
        payload = tenant_override_row_to_dict(row)
        profile = str(payload.get("entity_profile_code") or "").strip()
        if profile and profile != profile_code:
            continue
        row_ctx = str(payload.get("context") or "").strip().lower()
        if row_ctx and row_ctx != ctx:
            continue
        row_stage = str(payload.get("stage_code") or "").strip().lower()
        if row_stage and row_stage != str(stage_code or "").strip().lower():
            continue
        out.append(payload)
    return out
