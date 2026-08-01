"""CRUD helpers for intake_source_profiles and intake_source_bindings."""

from __future__ import annotations

import uuid
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.intake_routing import IntakeSourceBinding, IntakeSourceProfile
from backend.app.models.own_company import OwnCompany
from backend.app.modules.intake_routing.reference import (
    normalize_channel,
    normalize_external_key_secondary,
    normalize_provider,
    normalize_route_intent,
)


class IntakeRoutingValidationError(ValueError):
    """Invalid intake routing payload."""


async def get_profile_by_id(
    db: AsyncSession,
    *,
    tenant_id: str,
    profile_id: str,
) -> Optional[IntakeSourceProfile]:
    pid = str(profile_id or "").strip()
    if not pid:
        return None
    stmt = select(IntakeSourceProfile).where(
        IntakeSourceProfile.tenant_id == tenant_id,
        IntakeSourceProfile.id == pid,
    )
    return (await db.execute(stmt)).scalar_one_or_none()


async def get_profile_by_code(
    db: AsyncSession,
    *,
    tenant_id: str,
    code: str,
) -> Optional[IntakeSourceProfile]:
    c = str(code or "").strip()
    if not c:
        return None
    stmt = select(IntakeSourceProfile).where(
        IntakeSourceProfile.tenant_id == tenant_id,
        IntakeSourceProfile.code == c,
    )
    return (await db.execute(stmt)).scalar_one_or_none()


async def list_profiles(
    db: AsyncSession,
    *,
    tenant_id: str,
    active_only: bool = False,
) -> list[IntakeSourceProfile]:
    stmt = select(IntakeSourceProfile).where(IntakeSourceProfile.tenant_id == tenant_id)
    if active_only:
        stmt = stmt.where(IntakeSourceProfile.is_active.is_(True))
    stmt = stmt.order_by(IntakeSourceProfile.code.asc())
    return list((await db.execute(stmt)).scalars().all())


async def _validate_own_company(db: AsyncSession, *, tenant_id: str, own_company_id: str) -> None:
    oc = str(own_company_id or "").strip()
    if not oc:
        raise IntakeRoutingValidationError("own_company_id is required")
    row = (
        await db.execute(
            select(OwnCompany.id).where(
                OwnCompany.id == oc,
                OwnCompany.tenant_id == tenant_id,
                OwnCompany.is_archived.is_(False),
            )
        )
    ).scalar_one_or_none()
    if row is None:
        raise IntakeRoutingValidationError("own_company_id is invalid for tenant")


async def _validate_profile_for_binding(
    db: AsyncSession,
    *,
    tenant_id: str,
    profile_id: str,
) -> IntakeSourceProfile:
    profile = await get_profile_by_id(db, tenant_id=tenant_id, profile_id=profile_id)
    if profile is None:
        raise IntakeRoutingValidationError("intake_source_profile_id not found")
    return profile


async def create_profile(
    db: AsyncSession,
    *,
    tenant_id: str,
    code: str,
    name: str,
    own_company_id: str,
    provider: str = "unknown",
    channel: str = "unknown",
    route_intent: str = "unknown",
    pipeline_preset: Optional[str] = None,
    public_slug: Optional[str] = None,
    form_type: Optional[str] = None,
    lead_type: Optional[str] = None,
    lead_target_type: Optional[str] = None,
    entity_profile_code: Optional[str] = None,
    source: Optional[str] = None,
    default_assignee_id: Optional[str] = None,
    default_language: Optional[str] = None,
    supported_languages: Optional[str] = None,
    is_active: bool = True,
    notes: Optional[str] = None,
) -> IntakeSourceProfile:
    c = str(code or "").strip()
    n = str(name or "").strip()
    if not c:
        raise IntakeRoutingValidationError("code is required")
    if not n:
        raise IntakeRoutingValidationError("name is required")
    await _validate_own_company(db, tenant_id=tenant_id, own_company_id=own_company_id)
    if is_active and not str(own_company_id or "").strip():
        raise IntakeRoutingValidationError("active profile requires own_company_id")

    entry = IntakeSourceProfile(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        code=c,
        name=n,
        provider=normalize_provider(provider),
        channel=normalize_channel(channel),
        own_company_id=str(own_company_id).strip(),
        route_intent=normalize_route_intent(route_intent),
        pipeline_preset=str(pipeline_preset).strip() if pipeline_preset else None,
        public_slug=str(public_slug).strip() if public_slug else None,
        form_type=str(form_type).strip() if form_type else None,
        lead_type=str(lead_type).strip() if lead_type else None,
        lead_target_type=str(lead_target_type).strip() if lead_target_type else None,
        entity_profile_code=str(entity_profile_code).strip() if entity_profile_code else None,
        source=str(source).strip() if source else None,
        default_assignee_id=str(default_assignee_id).strip() if default_assignee_id else None,
        default_language=str(default_language).strip() if default_language else None,
        supported_languages=str(supported_languages).strip() if supported_languages else None,
        is_active=bool(is_active),
        notes=str(notes).strip() if notes else None,
    )
    db.add(entry)
    try:
        await db.flush()
    except IntegrityError as exc:
        await db.rollback()
        raise IntakeRoutingValidationError("profile code must be unique per tenant") from exc
    return entry


async def get_binding(
    db: AsyncSession,
    *,
    tenant_id: str,
    provider: str,
    external_key: str,
    external_key_secondary: str = "",
) -> Optional[IntakeSourceBinding]:
    prov = normalize_provider(provider)
    ek = str(external_key or "").strip()
    if not ek:
        return None
    sec = normalize_external_key_secondary(external_key_secondary)
    stmt = select(IntakeSourceBinding).where(
        IntakeSourceBinding.tenant_id == tenant_id,
        IntakeSourceBinding.provider == prov,
        IntakeSourceBinding.external_key == ek,
        IntakeSourceBinding.external_key_secondary == sec,
    )
    return (await db.execute(stmt)).scalar_one_or_none()


async def list_bindings_for_profile(
    db: AsyncSession,
    *,
    tenant_id: str,
    profile_id: str,
) -> list[IntakeSourceBinding]:
    pid = str(profile_id or "").strip()
    if not pid:
        return []
    stmt = (
        select(IntakeSourceBinding)
        .where(
            IntakeSourceBinding.tenant_id == tenant_id,
            IntakeSourceBinding.intake_source_profile_id == pid,
        )
        .order_by(IntakeSourceBinding.priority.desc(), IntakeSourceBinding.external_key.asc())
    )
    return list((await db.execute(stmt)).scalars().all())


async def create_binding(
    db: AsyncSession,
    *,
    tenant_id: str,
    intake_source_profile_id: str,
    provider: str,
    external_key: str,
    external_key_secondary: str = "",
    label: Optional[str] = None,
    is_active: bool = True,
    priority: int = 0,
) -> IntakeSourceBinding:
    profile = await _validate_profile_for_binding(
        db, tenant_id=tenant_id, profile_id=intake_source_profile_id
    )
    ek = str(external_key or "").strip()
    if not ek:
        raise IntakeRoutingValidationError("external_key is required")

    entry = IntakeSourceBinding(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        intake_source_profile_id=profile.id,
        provider=normalize_provider(provider),
        external_key=ek,
        external_key_secondary=normalize_external_key_secondary(external_key_secondary),
        label=str(label).strip() if label else None,
        is_active=bool(is_active),
        priority=int(priority or 0),
    )
    try:
        async with db.begin_nested():
            db.add(entry)
            await db.flush()
    except IntegrityError as exc:
        raise IntakeRoutingValidationError(
            "binding must be unique per tenant, provider, and external_key"
        ) from exc
    return entry


async def create_profile_with_binding(
    db: AsyncSession,
    *,
    tenant_id: str,
    profile: dict[str, Any],
    binding: dict[str, Any],
) -> tuple[IntakeSourceProfile, IntakeSourceBinding]:
    prof = await create_profile(db, tenant_id=tenant_id, **profile)
    bind = await create_binding(
        db,
        tenant_id=tenant_id,
        intake_source_profile_id=prof.id,
        **binding,
    )
    return prof, bind
