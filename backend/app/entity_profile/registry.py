"""Register Entity Profile manifests into registry tables."""

from __future__ import annotations

from typing import Any, Optional
from uuid import uuid4

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.field_registry.registry import FieldRegistry
from backend.app.models.entity_profile import (
    PLATFORM_TENANT_SCOPE,
    EpEntityProfile,
    EpEntityProfileField,
    EpIntakePresentation,
)
from backend.app.models.field_registry import PLATFORM_TENANT_SCOPE as FR_PLATFORM_SCOPE


class UnknownCanonicalFieldError(ValueError):
    """Raised when an Entity Profile references a field absent from Field Registry."""


class EntityProfileRegistry:
    @classmethod
    async def register_profile(
        cls,
        db: AsyncSession,
        profile: dict[str, Any],
        *,
        tenant_id: str = PLATFORM_TENANT_SCOPE,
        registry_version: str = "entity_profile_v1",
    ) -> dict[str, Any]:
        profile_code = str(profile.get("profile_code") or "").strip()
        if not profile_code:
            raise ValueError("profile.profile_code is required")

        tenant_scope = str(tenant_id or PLATFORM_TENANT_SCOPE)
        await cls._validate_fields_exist(db, tenant_scope=tenant_scope, profile=profile)

        entity = await cls._upsert_entity_profile(
            db,
            profile,
            tenant_scope=tenant_scope,
            registry_version=registry_version,
        )
        field_count = await cls._upsert_profile_fields(db, entity, profile.get("fields") or [])
        presentation_count = await cls._upsert_intake_presentations(
            db,
            entity,
            tenant_scope=tenant_scope,
            presentations=profile.get("intake_presentations") or [],
        )
        await db.flush()
        return {
            "profile_code": profile_code,
            "tenant_id": tenant_scope,
            "field_count": field_count,
            "presentation_count": presentation_count,
        }

    @classmethod
    async def _validate_fields_exist(
        cls,
        db: AsyncSession,
        *,
        tenant_scope: str,
        profile: dict[str, Any],
    ) -> None:
        unknown: list[str] = []
        for row in profile.get("fields") or []:
            qualified_code = str(row.get("qualified_code") or "").strip()
            if not qualified_code:
                continue
            canonical = await FieldRegistry.get_canonical_field(
                db,
                tenant_id=tenant_scope,
                qualified_code=qualified_code,
            )
            if canonical is None and tenant_scope != FR_PLATFORM_SCOPE:
                canonical = await FieldRegistry.get_canonical_field(
                    db,
                    tenant_id=FR_PLATFORM_SCOPE,
                    qualified_code=qualified_code,
                )
            if canonical is None:
                unknown.append(qualified_code)
        for presentation in profile.get("intake_presentations") or []:
            for qualified_code in presentation.get("field_subset") or []:
                code = str(qualified_code or "").strip()
                if not code:
                    continue
                if any(
                    str(f.get("qualified_code") or "").strip() == code
                    for f in profile.get("fields") or []
                ):
                    continue
                unknown.append(code)
        if unknown:
            raise UnknownCanonicalFieldError(
                f"Entity profile {profile.get('profile_code')} references unknown Field Registry codes: "
                + ", ".join(sorted(set(unknown)))
            )

    @classmethod
    async def _upsert_entity_profile(
        cls,
        db: AsyncSession,
        profile: dict[str, Any],
        *,
        tenant_scope: str,
        registry_version: str,
    ) -> EpEntityProfile:
        profile_code = str(profile["profile_code"]).strip()
        existing = (
            await db.execute(
                select(EpEntityProfile).where(
                    EpEntityProfile.tenant_id == tenant_scope,
                    EpEntityProfile.profile_code == profile_code,
                )
            )
        ).scalar_one_or_none()
        if existing is None:
            existing = EpEntityProfile(
                id=str(uuid4()),
                tenant_id=tenant_scope,
                profile_code=profile_code,
            )
            db.add(existing)
        existing.registry_version = registry_version
        existing.status = "active"
        existing.name = str(profile.get("name") or profile_code)
        existing.description = profile.get("description")
        existing.entity_type = str(profile.get("entity_type") or "")
        existing.module_owner = str(profile.get("module_owner") or "")
        existing.default_layout_code = profile.get("default_layout_code")
        existing.document_pack_code = profile.get("document_pack_code")
        existing.process_profile_code = profile.get("process_profile_code")
        existing.is_system = True
        existing.config = dict(profile.get("config") or {})
        return existing

    @classmethod
    async def _upsert_profile_fields(
        cls,
        db: AsyncSession,
        entity: EpEntityProfile,
        rows: list[dict[str, Any]],
    ) -> int:
        await db.execute(
            delete(EpEntityProfileField).where(EpEntityProfileField.entity_profile_id == entity.id)
        )
        count = 0
        for row in rows:
            qualified_code = str(row.get("qualified_code") or "").strip()
            if not qualified_code:
                continue
            canonical = await FieldRegistry.get_canonical_field(
                db,
                tenant_id=entity.tenant_id,
                qualified_code=qualified_code,
            )
            if canonical is None:
                canonical = await FieldRegistry.get_canonical_field(
                    db,
                    tenant_id=FR_PLATFORM_SCOPE,
                    qualified_code=qualified_code,
                )
            db.add(
                EpEntityProfileField(
                    id=str(uuid4()),
                    entity_profile_id=entity.id,
                    qualified_code=qualified_code,
                    canonical_field_id=canonical.id if canonical else None,
                    sort_order=int(row.get("sort_order") or 0),
                    intake_level=str(row.get("intake_level") or "optional"),
                    card_save_level=str(row.get("card_save_level") or "optional"),
                    transition_level=str(row.get("transition_level") or "optional"),
                    is_active=bool(row.get("is_active", True)),
                )
            )
            count += 1
        return count

    @classmethod
    async def _upsert_intake_presentations(
        cls,
        db: AsyncSession,
        entity: EpEntityProfile,
        *,
        tenant_scope: str,
        presentations: list[dict[str, Any]],
    ) -> int:
        await db.execute(
            delete(EpIntakePresentation).where(
                EpIntakePresentation.entity_profile_id == entity.id,
                EpIntakePresentation.tenant_id == tenant_scope,
            )
        )
        count = 0
        for row in presentations:
            code = str(row.get("presentation_code") or "").strip()
            if not code:
                continue
            db.add(
                EpIntakePresentation(
                    id=str(uuid4()),
                    tenant_id=tenant_scope,
                    entity_profile_id=entity.id,
                    intake_source_binding_id=row.get("intake_source_binding_id"),
                    presentation_code=code,
                    field_subset=list(row.get("field_subset") or []),
                    presentation_overrides=dict(row.get("presentation_overrides") or {}),
                    is_active=bool(row.get("is_active", True)),
                )
            )
            count += 1
        return count

    @classmethod
    async def get_entity_profile(
        cls,
        db: AsyncSession,
        *,
        tenant_id: str,
        profile_code: str,
    ) -> Optional[EpEntityProfile]:
        code = str(profile_code or "").strip()
        if not code:
            return None
        tenant_scope = str(tenant_id).strip()
        tenant_row = (
            await db.execute(
                select(EpEntityProfile).where(
                    EpEntityProfile.tenant_id == tenant_scope,
                    EpEntityProfile.profile_code == code,
                    EpEntityProfile.status == "active",
                ).limit(1)
            )
        ).scalar_one_or_none()
        if tenant_row is not None:
            return tenant_row
        return (
            await db.execute(
                select(EpEntityProfile).where(
                    EpEntityProfile.tenant_id == PLATFORM_TENANT_SCOPE,
                    EpEntityProfile.profile_code == code,
                    EpEntityProfile.status == "active",
                ).limit(1)
            )
        ).scalar_one_or_none()
