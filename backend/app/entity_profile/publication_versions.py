"""Immutable Entity Profile publication ledger.

ADR-043 publication runtime.

EpEntityProfile remains the mutable logical head. Publishing atomically freezes
profile metadata and explicit field/document requirement bindings into an
append-only EpEntityProfileVersion decision basis.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.entity_profile.exceptions import EntityProfileNotFoundError
from backend.app.models.entity_profile import (
    EpEntityProfile,
    EpEntityProfileVersion,
    EpEntityProfileVersionDocument,
    EpEntityProfileVersionField,
)
from backend.app.models.field_registry import FrCanonicalField
from backend.app.models.ref_document_type import RefDocumentTypeVersion
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


FIELD_REQUIREMENT_LEVELS = frozenset({"hidden", "optional", "required"})
DOCUMENT_REQUIREMENT_LEVELS = frozenset({"hidden", "preferred", "required"})


async def _validate_field_bindings(
    db: AsyncSession,
    *,
    field_bindings: Sequence[dict[str, Any]],
) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    for raw in field_bindings:
        canonical_field_id = str(raw.get("canonical_field_id") or "").strip()
        qualified_code = str(raw.get("qualified_code") or "").strip()
        requirement_level = str(raw.get("requirement_level") or "").strip().lower()
        sort_order = int(raw.get("sort_order") or 0)

        if not canonical_field_id or not qualified_code:
            raise ValueError(
                "Profile field binding requires canonical_field_id and qualified_code"
            )
        if requirement_level not in FIELD_REQUIREMENT_LEVELS:
            raise ValueError(
                f"Invalid profile field requirement_level: {requirement_level}"
            )
        if canonical_field_id in seen_ids:
            raise ValueError(
                f"Duplicate profile field binding: {canonical_field_id}"
            )
        seen_ids.add(canonical_field_id)

        field = await db.scalar(
            select(FrCanonicalField).where(
                FrCanonicalField.id == canonical_field_id,
            )
        )
        if field is None:
            raise ValueError(
                f"Canonical field not found: {canonical_field_id}"
            )
        if str(field.qualified_code) != qualified_code:
            raise ValueError(
                "Canonical field binding identity mismatch: "
                f"{canonical_field_id} != {qualified_code}"
            )

        normalized.append(
            {
                "canonical_field_id": canonical_field_id,
                "qualified_code": qualified_code,
                "requirement_level": requirement_level,
                "sort_order": sort_order,
            }
        )

    return normalized


async def _validate_document_bindings(
    db: AsyncSession,
    *,
    document_bindings: Sequence[dict[str, Any]],
) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    for raw in document_bindings:
        document_type_version_id = str(
            raw.get("document_type_version_id") or ""
        ).strip()
        requirement_level = str(raw.get("requirement_level") or "").strip().lower()
        sort_order = int(raw.get("sort_order") or 0)

        if not document_type_version_id:
            raise ValueError(
                "Profile document binding requires document_type_version_id"
            )
        if requirement_level not in DOCUMENT_REQUIREMENT_LEVELS:
            raise ValueError(
                f"Invalid profile document requirement_level: {requirement_level}"
            )
        if document_type_version_id in seen_ids:
            raise ValueError(
                f"Duplicate profile document binding: {document_type_version_id}"
            )
        seen_ids.add(document_type_version_id)

        document_version = await db.scalar(
            select(RefDocumentTypeVersion).where(
                RefDocumentTypeVersion.id == document_type_version_id,
            )
        )
        if document_version is None:
            raise ValueError(
                f"Document type version not found: {document_type_version_id}"
            )

        normalized.append(
            {
                "document_type_version_id": document_type_version_id,
                "requirement_level": requirement_level,
                "sort_order": sort_order,
            }
        )

    return normalized


async def publish_entity_profile(
    db: AsyncSession,
    *,
    tenant_id: str,
    entity_profile_id: str,
    field_bindings: Sequence[dict[str, Any]] = (),
    document_bindings: Sequence[dict[str, Any]] = (),
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

    normalized_fields = await _validate_field_bindings(
        db,
        field_bindings=field_bindings,
    )
    normalized_documents = await _validate_document_bindings(
        db,
        document_bindings=document_bindings,
    )

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
        funnel_id=profile.funnel_id,
        process_profile_code=profile.process_profile_code,
        config=dict(profile.config or {}),
        published_at=published_at,
    )
    db.add(row)

    # Materialize the immutable parent identity before attaching its bindings.
    # This remains one transaction; no published version can commit without
    # the complete requirement configuration supplied to this operation.
    await db.flush()

    for binding in normalized_fields:
        db.add(
            EpEntityProfileVersionField(
                entity_profile_version_id=row.id,
                canonical_field_id=binding["canonical_field_id"],
                qualified_code=binding["qualified_code"],
                requirement_level=binding["requirement_level"],
                sort_order=binding["sort_order"],
            )
        )

    for binding in normalized_documents:
        db.add(
            EpEntityProfileVersionDocument(
                entity_profile_version_id=row.id,
                document_type_version_id=binding["document_type_version_id"],
                requirement_level=binding["requirement_level"],
                sort_order=binding["sort_order"],
            )
        )

    profile.published_version = next_version
    profile.published_at = published_at

    await db.flush()
    return row


__all__ = [
    "get_publication_version",
    "list_publication_versions",
    "publish_entity_profile",
]
