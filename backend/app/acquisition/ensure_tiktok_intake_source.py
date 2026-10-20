"""Ensure IntakeSourceProfile + binding for a TikTok Instant Form.

Create-if-missing. An existing profile keeps the operator's company and route intent.
"""

from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.intake_routing import IntakeSourceProfile
from backend.app.modules.intake_routing import crud as intake_crud
from backend.app.modules.intake_routing.meta_bridge import (
    meta_external_key,
    meta_external_key_secondary,
)
from backend.app.modules.intake_routing.reference import normalize_route_intent

logger = logging.getLogger(__name__)


def tiktok_profile_code(form_id: str) -> str:
    fid = str(form_id or "").strip()
    return f"tiktok-form-{fid}" if fid else "tiktok-form-unknown"


async def ensure_tiktok_form_intake_source(
    db: AsyncSession,
    *,
    tenant_id: str,
    own_company_id: str,
    form_id: str,
    route_intent: str = "candidate_application",
    display_name: Optional[str] = None,
) -> Optional[IntakeSourceProfile]:
    """Idempotent TikTok form profile + ``form_id:`` binding. Returns None when the company is unusable."""
    fid = str(form_id or "").strip()
    oid = str(own_company_id or "").strip()
    if not fid or not oid:
        return None

    code = tiktok_profile_code(fid)
    intent = normalize_route_intent(route_intent)
    name = str(display_name or "").strip() or f"TikTok form {fid}"

    existing = await intake_crud.get_profile_by_code(db, tenant_id=str(tenant_id), code=code)
    if existing is not None:
        profile = existing
        if not profile.is_active:
            profile.is_active = True
            await db.flush()
    else:
        try:
            profile = await intake_crud.create_profile(
                db,
                tenant_id=str(tenant_id),
                code=code,
                name=name,
                own_company_id=oid,
                provider="tiktok",
                channel="paid",
                route_intent=intent,
                is_active=True,
            )
        except intake_crud.IntakeRoutingValidationError:
            logger.warning(
                "tiktok_intake_source_skipped tenant=%s form=%s reason=invalid_company",
                tenant_id,
                fid,
            )
            return None

    external_key = meta_external_key(fid)
    external_key_secondary = meta_external_key_secondary(fid)
    binding = await intake_crud.get_binding(
        db,
        tenant_id=str(tenant_id),
        provider="tiktok",
        external_key=external_key,
        external_key_secondary=external_key_secondary,
    )
    if binding is None and external_key_secondary:
        binding = await intake_crud.get_binding(
            db,
            tenant_id=str(tenant_id),
            provider="tiktok",
            external_key=external_key,
            external_key_secondary="",
        )
    if binding is not None:
        if not binding.is_active:
            binding.is_active = True
        binding.intake_source_profile_id = profile.id
        await db.flush()
    else:
        try:
            await intake_crud.create_binding(
                db,
                tenant_id=str(tenant_id),
                intake_source_profile_id=profile.id,
                provider="tiktok",
                external_key=external_key,
                external_key_secondary=external_key_secondary,
                label=name,
                is_active=True,
            )
        except intake_crud.IntakeRoutingValidationError:
            logger.warning(
                "tiktok_intake_binding_skipped tenant=%s form=%s",
                tenant_id,
                fid,
            )
    return profile


__all__ = ["ensure_tiktok_form_intake_source", "tiktok_profile_code"]
