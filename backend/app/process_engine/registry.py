"""Register module manifests into Process Engine registry tables."""

from __future__ import annotations

from typing import Any, Optional
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.process_engine import (
    PLATFORM_TENANT_SCOPE,
    REGISTRY_STATUS_ACTIVE,
    PeDocumentRequirement,
    PeFieldRequirement,
    PeHandoffRule,
    PeOverrideRule,
    PePipelineTemplate,
    PeProcessProfile,
    PeStageTemplate,
    PeSystemStage,
    PeTransitionRule,
)


class ProcessEngineRegistry:
    """Upsert platform/module registry rows from a manifest dict."""

    @classmethod
    async def register_module(
        cls,
        db: AsyncSession,
        manifest: dict[str, Any],
        *,
        tenant_id: str = PLATFORM_TENANT_SCOPE,
        link_legacy: bool = False,
    ) -> dict[str, Any]:
        module = str(manifest.get("module") or "").strip()
        if not module:
            raise ValueError("manifest.module is required")

        registry_version = str(manifest.get("registry_version") or "process_engine_v1")
        tenant_scope = str(tenant_id or PLATFORM_TENANT_SCOPE)

        stage_ids = await cls._upsert_system_stages(
            db, module, tenant_scope, registry_version, manifest.get("system_stages") or []
        )
        await cls._upsert_stage_templates(
            db, module, tenant_scope, registry_version, manifest.get("stage_templates") or []
        )
        pipeline_ids = await cls._upsert_pipeline_templates(
            db, module, tenant_scope, registry_version, manifest.get("pipeline_templates") or []
        )
        profile_ids = await cls._upsert_process_profiles(
            db,
            module,
            tenant_scope,
            registry_version,
            manifest.get("process_profiles") or [],
            pipeline_ids,
            link_legacy=link_legacy,
        )
        await cls._upsert_transition_rules(
            db,
            module,
            tenant_scope,
            registry_version,
            manifest.get("transition_rules") or [],
            profile_ids,
        )
        await cls._upsert_handoff_rules(
            db, module, tenant_scope, registry_version, manifest.get("handoff_rules") or []
        )
        await cls._upsert_field_requirements(
            db, module, tenant_scope, registry_version, manifest.get("field_requirements") or []
        )
        await cls._upsert_document_requirements(
            db, module, tenant_scope, registry_version, manifest.get("document_requirements") or []
        )
        await cls._upsert_override_rules(
            db, module, tenant_scope, registry_version, manifest.get("override_rules") or []
        )

        await db.flush()
        return {
            "module": module,
            "tenant_id": tenant_scope,
            "system_stages": len(stage_ids),
            "process_profiles": list(profile_ids.values()),
            "pipeline_templates": list(pipeline_ids.values()),
        }

    @classmethod
    async def list_system_stages(
        cls,
        db: AsyncSession,
        *,
        module: str,
        tenant_id: str = PLATFORM_TENANT_SCOPE,
    ) -> list[PeSystemStage]:
        stmt = (
            select(PeSystemStage)
            .where(
                PeSystemStage.module == module,
                PeSystemStage.tenant_id == tenant_id,
                PeSystemStage.status == REGISTRY_STATUS_ACTIVE,
            )
            .order_by(PeSystemStage.code.asc())
        )
        return list((await db.execute(stmt)).scalars().all())

    @classmethod
    async def get_default_process_profile(
        cls,
        db: AsyncSession,
        *,
        module: str,
        tenant_id: str,
    ) -> Optional[PeProcessProfile]:
        stmt = (
            select(PeProcessProfile)
            .where(
                PeProcessProfile.module == module,
                PeProcessProfile.tenant_id == tenant_id,
                PeProcessProfile.is_default.is_(True),
                PeProcessProfile.status == REGISTRY_STATUS_ACTIVE,
            )
            .limit(1)
        )
        return (await db.execute(stmt)).scalar_one_or_none()

    @staticmethod
    async def _upsert_system_stages(
        db: AsyncSession,
        module: str,
        tenant_id: str,
        registry_version: str,
        rows: list[dict[str, Any]],
    ) -> dict[str, str]:
        out: dict[str, str] = {}
        for row in rows:
            code = str(row.get("code") or "").strip()
            if not code:
                continue
            existing = await db.execute(
                select(PeSystemStage).where(
                    PeSystemStage.module == module,
                    PeSystemStage.tenant_id == tenant_id,
                    PeSystemStage.code == code,
                )
            )
            entity = existing.scalar_one_or_none()
            if entity is None:
                entity = PeSystemStage(
                    id=str(uuid4()),
                    module=module,
                    tenant_id=tenant_id,
                    code=code,
                )
                db.add(entity)
            entity.registry_version = registry_version
            entity.status = REGISTRY_STATUS_ACTIVE
            entity.name = str(row.get("name") or code)
            entity.description = row.get("description")
            entity.template_code = row.get("template_code")
            entity.terminal = bool(row.get("terminal"))
            entity.analytics_bucket = row.get("analytics_bucket")
            entity.config = dict(row.get("config") or {})
            entity.is_system = True
            out[code] = entity.id
        return out

    @staticmethod
    async def _upsert_stage_templates(
        db: AsyncSession,
        module: str,
        tenant_id: str,
        registry_version: str,
        rows: list[dict[str, Any]],
    ) -> None:
        for row in rows:
            code = str(row.get("code") or "").strip()
            if not code:
                continue
            existing = await db.execute(
                select(PeStageTemplate).where(
                    PeStageTemplate.module == module,
                    PeStageTemplate.tenant_id == tenant_id,
                    PeStageTemplate.code == code,
                )
            )
            entity = existing.scalar_one_or_none()
            if entity is None:
                entity = PeStageTemplate(
                    id=str(uuid4()),
                    module=module,
                    tenant_id=tenant_id,
                    code=code,
                )
                db.add(entity)
            entity.registry_version = registry_version
            entity.status = REGISTRY_STATUS_ACTIVE
            entity.name = str(row.get("name") or code)
            entity.config = dict(row.get("config") or {})
            entity.is_system = True

    @staticmethod
    async def _upsert_pipeline_templates(
        db: AsyncSession,
        module: str,
        tenant_id: str,
        registry_version: str,
        rows: list[dict[str, Any]],
    ) -> dict[str, str]:
        out: dict[str, str] = {}
        for row in rows:
            code = str(row.get("code") or "").strip()
            if not code:
                continue
            existing = await db.execute(
                select(PePipelineTemplate).where(
                    PePipelineTemplate.module == module,
                    PePipelineTemplate.tenant_id == tenant_id,
                    PePipelineTemplate.code == code,
                )
            )
            entity = existing.scalar_one_or_none()
            if entity is None:
                entity = PePipelineTemplate(
                    id=str(uuid4()),
                    module=module,
                    tenant_id=tenant_id,
                    code=code,
                )
                db.add(entity)
            entity.registry_version = registry_version
            entity.status = REGISTRY_STATUS_ACTIVE
            entity.name = str(row.get("name") or code)
            entity.config = dict(row.get("config") or {})
            entity.is_system = True
            out[code] = entity.id
        return out

    @classmethod
    async def _upsert_process_profiles(
        cls,
        db: AsyncSession,
        module: str,
        tenant_id: str,
        registry_version: str,
        rows: list[dict[str, Any]],
        pipeline_ids: dict[str, str],
        *,
        link_legacy: bool,
    ) -> dict[str, str]:
        out: dict[str, str] = {}
        for row in rows:
            code = str(row.get("code") or "").strip()
            if not code:
                continue
            pipeline_code = str(row.get("pipeline_code") or "").strip()
            pipeline_id = pipeline_ids.get(pipeline_code) if pipeline_code else None

            existing = await db.execute(
                select(PeProcessProfile).where(
                    PeProcessProfile.module == module,
                    PeProcessProfile.tenant_id == tenant_id,
                    PeProcessProfile.code == code,
                )
            )
            entity = existing.scalar_one_or_none()
            if entity is None:
                entity = PeProcessProfile(
                    id=str(uuid4()),
                    module=module,
                    tenant_id=tenant_id,
                    code=code,
                )
                db.add(entity)
            entity.registry_version = registry_version
            entity.status = REGISTRY_STATUS_ACTIVE
            entity.name = str(row.get("name") or code)
            entity.config = dict(row.get("config") or {})
            entity.is_default = bool(row.get("is_default"))
            entity.pipeline_template_id = pipeline_id
            entity.is_system = True

            if link_legacy:
                from backend.app.process_engine.legacy_mapping import link_process_profile_to_candidate_profile

                await link_process_profile_to_candidate_profile(db, entity=entity, tenant_id=tenant_id)

            out[code] = entity.id
        return out

    @staticmethod
    async def _upsert_transition_rules(
        db: AsyncSession,
        module: str,
        tenant_id: str,
        registry_version: str,
        rows: list[dict[str, Any]],
        profile_ids: dict[str, str],
    ) -> None:
        default_profile_id = next(iter(profile_ids.values()), None) if profile_ids else None
        for row in rows:
            code = str(row.get("code") or "").strip()
            if not code:
                continue
            existing = await db.execute(
                select(PeTransitionRule).where(
                    PeTransitionRule.module == module,
                    PeTransitionRule.tenant_id == tenant_id,
                    PeTransitionRule.code == code,
                )
            )
            entity = existing.scalar_one_or_none()
            if entity is None:
                entity = PeTransitionRule(
                    id=str(uuid4()),
                    module=module,
                    tenant_id=tenant_id,
                    code=code,
                )
                db.add(entity)
            entity.registry_version = registry_version
            entity.status = REGISTRY_STATUS_ACTIVE
            entity.name = str(row.get("name") or code)
            entity.config = dict(row.get("config") or {})
            entity.priority = int(row.get("priority") or 100)
            entity.process_profile_id = profile_ids.get(
                str(row.get("process_profile_code") or "").strip(),
                default_profile_id,
            )
            entity.is_system = True

    @staticmethod
    async def _upsert_handoff_rules(
        db: AsyncSession,
        module: str,
        tenant_id: str,
        registry_version: str,
        rows: list[dict[str, Any]],
    ) -> None:
        for row in rows:
            code = str(row.get("code") or "").strip()
            handoff_mode = str(row.get("handoff_mode") or "").strip()
            if not code or not handoff_mode:
                continue
            existing = await db.execute(
                select(PeHandoffRule).where(
                    PeHandoffRule.module == module,
                    PeHandoffRule.tenant_id == tenant_id,
                    PeHandoffRule.code == code,
                )
            )
            entity = existing.scalar_one_or_none()
            if entity is None:
                entity = PeHandoffRule(
                    id=str(uuid4()),
                    module=module,
                    tenant_id=tenant_id,
                    code=code,
                    handoff_mode=handoff_mode,
                )
                db.add(entity)
            entity.registry_version = registry_version
            entity.status = REGISTRY_STATUS_ACTIVE
            entity.name = str(row.get("name") or code)
            entity.config = dict(row.get("config") or {})
            entity.handoff_mode = handoff_mode
            entity.is_system = True

    @staticmethod
    async def _upsert_field_requirements(
        db: AsyncSession,
        module: str,
        tenant_id: str,
        registry_version: str,
        rows: list[dict[str, Any]],
    ) -> None:
        for row in rows:
            code = str(row.get("code") or "").strip()
            entity_type = str(row.get("entity_type") or "").strip()
            if not code or not entity_type:
                continue
            existing = await db.execute(
                select(PeFieldRequirement).where(
                    PeFieldRequirement.module == module,
                    PeFieldRequirement.tenant_id == tenant_id,
                    PeFieldRequirement.code == code,
                )
            )
            entity = existing.scalar_one_or_none()
            if entity is None:
                entity = PeFieldRequirement(
                    id=str(uuid4()),
                    module=module,
                    tenant_id=tenant_id,
                    code=code,
                    entity_type=entity_type,
                )
                db.add(entity)
            entity.registry_version = registry_version
            entity.status = REGISTRY_STATUS_ACTIVE
            entity.name = str(row.get("name") or code)
            entity.config = dict(row.get("config") or {})
            entity.entity_type = entity_type
            entity.is_system = True

    @staticmethod
    async def _upsert_document_requirements(
        db: AsyncSession,
        module: str,
        tenant_id: str,
        registry_version: str,
        rows: list[dict[str, Any]],
    ) -> None:
        for row in rows:
            code = str(row.get("code") or "").strip()
            entity_type = str(row.get("entity_type") or "").strip()
            if not code or not entity_type:
                continue
            existing = await db.execute(
                select(PeDocumentRequirement).where(
                    PeDocumentRequirement.module == module,
                    PeDocumentRequirement.tenant_id == tenant_id,
                    PeDocumentRequirement.code == code,
                )
            )
            entity = existing.scalar_one_or_none()
            if entity is None:
                entity = PeDocumentRequirement(
                    id=str(uuid4()),
                    module=module,
                    tenant_id=tenant_id,
                    code=code,
                    entity_type=entity_type,
                )
                db.add(entity)
            entity.registry_version = registry_version
            entity.status = REGISTRY_STATUS_ACTIVE
            entity.name = str(row.get("name") or code)
            entity.config = dict(row.get("config") or {})
            entity.entity_type = entity_type
            entity.is_system = True

    @staticmethod
    async def _upsert_override_rules(
        db: AsyncSession,
        module: str,
        tenant_id: str,
        registry_version: str,
        rows: list[dict[str, Any]],
    ) -> None:
        for row in rows:
            code = str(row.get("code") or "").strip()
            if not code:
                continue
            scope = str(row.get("scope") or "both")
            existing = await db.execute(
                select(PeOverrideRule).where(
                    PeOverrideRule.module == module,
                    PeOverrideRule.tenant_id == tenant_id,
                    PeOverrideRule.code == code,
                )
            )
            entity = existing.scalar_one_or_none()
            if entity is None:
                entity = PeOverrideRule(
                    id=str(uuid4()),
                    module=module,
                    tenant_id=tenant_id,
                    code=code,
                    scope=scope,
                )
                db.add(entity)
            entity.registry_version = registry_version
            entity.status = REGISTRY_STATUS_ACTIVE
            entity.name = str(row.get("name") or code)
            entity.config = dict(row.get("config") or {})
            entity.scope = scope
            entity.is_system = True
