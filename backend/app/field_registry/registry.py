"""Register module manifests into Field Registry tables."""

from __future__ import annotations

from typing import Any, Optional
from uuid import uuid4

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.field_registry import (
    PLATFORM_TENANT_SCOPE,
    REGISTRY_STATUS_ACTIVE,
    FrCanonicalField,
    FrCardLayoutField,
    FrCardLayoutProfile,
)


class FieldRegistry:
    @classmethod
    async def register_module(
        cls,
        db: AsyncSession,
        manifest: dict[str, Any],
        *,
        tenant_id: str = PLATFORM_TENANT_SCOPE,
    ) -> dict[str, Any]:
        module = str(manifest.get("module") or "").strip()
        if not module:
            raise ValueError("manifest.module is required")

        registry_version = str(manifest.get("registry_version") or "field_registry_v1")
        tenant_scope = str(tenant_id or PLATFORM_TENANT_SCOPE)

        field_ids = await cls._upsert_canonical_fields(
            db,
            module,
            tenant_scope,
            registry_version,
            manifest.get("canonical_fields") or [],
        )
        layout_count = await cls._upsert_card_layouts(
            db,
            module,
            tenant_scope,
            registry_version,
            manifest.get("card_layouts") or [],
            field_ids,
        )
        await db.flush()
        return {
            "module": module,
            "tenant_id": tenant_scope,
            "canonical_fields": len(field_ids),
            "card_layouts": layout_count,
        }

    @classmethod
    async def _upsert_canonical_fields(
        cls,
        db: AsyncSession,
        module: str,
        tenant_id: str,
        registry_version: str,
        rows: list[dict[str, Any]],
    ) -> dict[str, str]:
        out: dict[str, str] = {}
        for row in rows:
            qualified_code = str(row.get("qualified_code") or "").strip()
            if not qualified_code:
                continue
            existing = await db.execute(
                select(FrCanonicalField).where(
                    FrCanonicalField.tenant_id == tenant_id,
                    FrCanonicalField.qualified_code == qualified_code,
                )
            )
            entity = existing.scalar_one_or_none()
            if entity is None:
                entity = FrCanonicalField(
                    id=str(uuid4()),
                    module=module,
                    tenant_id=tenant_id,
                    code=str(row.get("code") or qualified_code.split(".")[-1]),
                    qualified_code=qualified_code,
                )
                db.add(entity)
            entity.registry_version = registry_version
            entity.status = REGISTRY_STATUS_ACTIVE
            entity.name = str(row.get("name") or qualified_code)
            entity.description = row.get("description")
            entity.entity_type = str(row.get("entity_type") or "")
            entity.field_type = str(row.get("field_type") or "text")
            entity.label_key = row.get("label_key")
            entity.ownership = str(row.get("ownership") or module)
            entity.reference_domain = row.get("reference_domain")
            entity.pii_class = row.get("pii_class")
            entity.is_system = True
            config = dict(entity.config or {})
            if row.get("storage"):
                config["storage"] = dict(row["storage"])
            if row.get("legacy_aliases"):
                config["legacy_aliases"] = list(row["legacy_aliases"])
            if row.get("default_section"):
                config["default_section"] = row["default_section"]
            entity.config = config
            out[qualified_code] = entity.id
        return out

    @classmethod
    async def _upsert_card_layouts(
        cls,
        db: AsyncSession,
        module: str,
        tenant_id: str,
        registry_version: str,
        rows: list[dict[str, Any]],
        field_ids: dict[str, str],
    ) -> int:
        count = 0
        for row in rows:
            code = str(row.get("code") or "").strip()
            if not code:
                continue
            existing = await db.execute(
                select(FrCardLayoutProfile).where(
                    FrCardLayoutProfile.tenant_id == tenant_id,
                    FrCardLayoutProfile.module == module,
                    FrCardLayoutProfile.code == code,
                )
            )
            profile = existing.scalar_one_or_none()
            if profile is None:
                profile = FrCardLayoutProfile(
                    id=str(uuid4()),
                    module=module,
                    tenant_id=tenant_id,
                    code=code,
                )
                db.add(profile)
            profile.registry_version = registry_version
            profile.status = REGISTRY_STATUS_ACTIVE
            profile.name = str(row.get("name") or code)
            profile.entity_type = str(row.get("entity_type") or "")
            profile.is_default = bool(row.get("is_default"))
            profile.is_system = True
            profile.config = dict(row.get("config") or {})

            await db.flush()
            await db.execute(
                delete(FrCardLayoutField).where(FrCardLayoutField.layout_profile_id == profile.id)
            )

            for field_row in row.get("fields") or []:
                qualified = str(field_row.get("qualified_code") or "").strip()
                field_id = field_ids.get(qualified)
                if not field_id:
                    loaded = await db.execute(
                        select(FrCanonicalField).where(
                            FrCanonicalField.tenant_id == tenant_id,
                            FrCanonicalField.qualified_code == qualified,
                        )
                    )
                    found = loaded.scalar_one_or_none()
                    field_id = found.id if found else None
                if not field_id:
                    continue
                db.add(
                    FrCardLayoutField(
                        id=str(uuid4()),
                        layout_profile_id=profile.id,
                        canonical_field_id=field_id,
                        section_code=str(field_row.get("section_code") or "general"),
                        sort_order=int(field_row.get("sort_order") or 0),
                        visible=bool(field_row.get("visible", True)),
                        required=bool(field_row.get("required", False)),
                        label_override=field_row.get("label_override"),
                    )
                )
            count += 1
        return count

    @classmethod
    async def get_canonical_field(
        cls,
        db: AsyncSession,
        *,
        tenant_id: str,
        qualified_code: str,
    ) -> Optional[FrCanonicalField]:
        code = str(qualified_code or "").strip()
        if not code:
            return None
        tenant_scope = str(tenant_id).strip()
        tenant_field = (
            await db.execute(
                select(FrCanonicalField).where(
                    FrCanonicalField.tenant_id == tenant_scope,
                    FrCanonicalField.qualified_code == code,
                    FrCanonicalField.status == REGISTRY_STATUS_ACTIVE,
                ).limit(1)
            )
        ).scalar_one_or_none()
        if tenant_field is not None:
            return tenant_field
        return (
            await db.execute(
                select(FrCanonicalField).where(
                    FrCanonicalField.tenant_id == PLATFORM_TENANT_SCOPE,
                    FrCanonicalField.qualified_code == code,
                    FrCanonicalField.status == REGISTRY_STATUS_ACTIVE,
                ).limit(1)
            )
        ).scalar_one_or_none()

    @classmethod
    async def list_canonical_fields(
        cls,
        db: AsyncSession,
        *,
        tenant_id: str = PLATFORM_TENANT_SCOPE,
        entity_type: Optional[str] = None,
        module: Optional[str] = None,
    ) -> list[FrCanonicalField]:
        stmt = select(FrCanonicalField).where(
            FrCanonicalField.tenant_id == tenant_id,
            FrCanonicalField.status == REGISTRY_STATUS_ACTIVE,
        )
        if entity_type:
            stmt = stmt.where(FrCanonicalField.entity_type == entity_type)
        if module:
            stmt = stmt.where(FrCanonicalField.module == module)
        stmt = stmt.order_by(FrCanonicalField.qualified_code.asc())
        return list((await db.execute(stmt)).scalars().all())

    @classmethod
    async def get_layout_profile(
        cls,
        db: AsyncSession,
        *,
        tenant_id: str,
        layout_code: str,
        module: Optional[str] = None,
    ) -> Optional[FrCardLayoutProfile]:
        stmt = select(FrCardLayoutProfile).where(
            FrCardLayoutProfile.tenant_id == tenant_id,
            FrCardLayoutProfile.code == layout_code,
            FrCardLayoutProfile.status == REGISTRY_STATUS_ACTIVE,
        )
        if module:
            stmt = stmt.where(FrCardLayoutProfile.module == module)
        return (await db.execute(stmt.limit(1))).scalar_one_or_none()

    @classmethod
    async def get_default_layout_profile(
        cls,
        db: AsyncSession,
        *,
        tenant_id: str,
        entity_type: str,
        module: Optional[str] = None,
    ) -> Optional[FrCardLayoutProfile]:
        stmt = select(FrCardLayoutProfile).where(
            FrCardLayoutProfile.tenant_id == tenant_id,
            FrCardLayoutProfile.entity_type == entity_type,
            FrCardLayoutProfile.is_default.is_(True),
            FrCardLayoutProfile.status == REGISTRY_STATUS_ACTIVE,
        )
        if module:
            stmt = stmt.where(FrCardLayoutProfile.module == module)
        return (await db.execute(stmt.limit(1))).scalar_one_or_none()
