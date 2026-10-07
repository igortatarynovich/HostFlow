"""Immutable Entity Profile publication ledger.

ADR-043 Slice 1.

EpEntityProfile remains the mutable logical head. Publishing freezes the
profile-level metadata into an append-only EpEntityProfileVersion row.
Field/document bindings are intentionally outside this slice.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.entity_profile.exceptions import EntityProfileNotFoundError
from backend.app.models.entity_profile import EpEntityProfile, EpEntityProfileVersion
from backend.app.models.mixins import now_utc


async def get_publication_version(
    db: AsyncSession,
    *,
    tenant_id: str,
    entity_profile_id: str,
    version: int,
) -> EpEntityProfileVersion | None:
    return await db.scalar(
        select(EpEntityProfileVersion).where(
            EpEntityProfileVersion.tenant_id == str(tenant_id),
            EpEntityProfileVersion.entity_profile_id == str(entity_profile_id),
            EpEntityProfileVersion.version == int(version),
        )
    )


async def list_publication_versions(
    db: AsyncSession,
    *,
    tenant_id: str,
    entity_profile_id: str,
) -> list[EpEntityProfileVersion]:
    rows = await db.scalars(
        select(EpEntityProfileVersion)
        .where(
            EpEntityProfileVersion.tenant_id == str(tenant_id),
            EpEntityProfileVersion.entity_profile_id == str(entity_profile_id),
        )
        .order_by(EpEntityProfileVersion.version.asc())
    )
    return list(rows.all())


async def publish_entity_profile(
    db: AsyncSession,
    *,
    tenant_id: str,
    entity_profile_id: str,
) -> EpEntityProfileVersion:
    profile = await db.scalar(
        select(EpEntityProfile)
        .where(
            EpEntityProfile.id == str(entity_profile_id),
            EpEntityProfile.tenant_id == str(tenant_id),
        )
        .with_for_update()
    )
    if profile is None:
        raise EntityProfileNotFoundError(str(entity_profile_id))

    next_version = int(profile.published_version or 0) + 1
    published_at = now_utc()

    row = EpEntityProfileVersion(
        tenant_id=str(profile.tenant_id),
        entity_profile_id=str(profile.id),
        version=next_version,
        registry_version=str(profile.registry_version),
        status=str(profile.status),
        name=str(profile.name),
        description=profile.description,
        is_system=bool(profile.is_system),
        entity_type=str(profile.entity_type),
        module_owner=str(profile.module_owner),
        default_layout_code=profile.default_layout_code,
        process_profile_code=profile.process_profile_code,
        config=dict(profile.config or {}),
        published_at=published_at,
    )
    db.add(row)

    profile.published_version = next_version
    profile.published_at = published_at

    await db.flush()
    return row


__all__ = [
    "get_publication_version",
    "list_publication_versions",
    "publish_entity_profile",
]
