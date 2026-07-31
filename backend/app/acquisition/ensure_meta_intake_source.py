"""Ensure IntakeSourceProfile + binding for a Meta Lead Form (Connect Source discovered)."""

from __future__ import annotations

from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.modules.intake_routing import crud as intake_crud
from backend.app.modules.intake_routing.meta_bridge import (
    meta_external_key,
    meta_external_key_secondary,
    meta_profile_code,
)
from backend.app.modules.intake_routing.reference import normalize_route_intent
from backend.app.models.intake_routing import IntakeSourceProfile


async def ensure_meta_form_intake_source(
    db: AsyncSession,
    *,
    tenant_id: str,
    own_company_id: str,
    form_id: str,
    page_id: Optional[str] = None,
    route_intent: str = "candidate_application",
    display_name: Optional[str] = None,
) -> IntakeSourceProfile:
    """Idempotent create/update meta-form-{id} profile + form_id binding for Connect Source."""
    fid = str(form_id or "").strip()
    if not fid:
        raise ValueError("meta_form_id is required")
    oid = str(own_company_id or "").strip()
    if not oid:
        raise ValueError("own_company_id is required")

    code = meta_profile_code(fid)
    intent = normalize_route_intent(route_intent)
    name = str(display_name or "").strip() or f"Meta form {fid}"

    existing = await intake_crud.get_profile_by_code(
        db, tenant_id=str(tenant_id), code=code
    )
    if existing is not None:
        existing.name = existing.name or name
        existing.provider = "meta"
        existing.channel = "paid"
        existing.own_company_id = oid
        existing.route_intent = intent
        existing.is_active = True
        await db.flush()
        profile = existing
    else:
        profile = await intake_crud.create_profile(
            db,
            tenant_id=str(tenant_id),
            code=code,
            name=name,
            own_company_id=oid,
            provider="meta",
            channel="paid",
            route_intent=intent,
            is_active=True,
        )

    external_key = meta_external_key(fid)
    external_key_secondary = meta_external_key_secondary(page_id)
    binding = await intake_crud.get_binding(
        db,
        tenant_id=str(tenant_id),
        provider="meta",
        external_key=external_key,
        external_key_secondary=external_key_secondary,
    )
    if binding is None and external_key_secondary:
        # Prefer exact page secondary; fall back to empty secondary if that was the SoT key.
        binding = await intake_crud.get_binding(
            db,
            tenant_id=str(tenant_id),
            provider="meta",
            external_key=external_key,
            external_key_secondary="",
        )
    if binding is not None:
        binding.intake_source_profile_id = profile.id
        binding.is_active = True
        if external_key_secondary and not str(binding.external_key_secondary or "").strip():
            binding.external_key_secondary = external_key_secondary
        await db.flush()
    else:
        await intake_crud.create_binding(
            db,
            tenant_id=str(tenant_id),
            intake_source_profile_id=profile.id,
            provider="meta",
            external_key=external_key,
            external_key_secondary=external_key_secondary,
            label=name,
            is_active=True,
        )
    return profile


__all__ = ["ensure_meta_form_intake_source"]
