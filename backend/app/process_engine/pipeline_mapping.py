"""Process Engine pipeline mapping (P4) — FunnelStage → qualified system stage."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.candidate import Candidate
from backend.app.models.funnel import Funnel, FunnelStage
from backend.app.models.process_engine import (
    PLATFORM_TENANT_SCOPE,
    REGISTRY_STATUS_ACTIVE,
    PeSystemStage,
)
from backend.app.process_engine.constants import RECRUITMENT_MODULE
from backend.app.process_engine.manifests.recruitment import (
    RECRUITMENT_MODULE as MANIFEST_RECRUITMENT_MODULE,
    recruitment_module_manifest,
)

MappingSource = Literal[
    "funnel_stage",
    "pipeline_template",
    "legacy_compat",
    "identity",
]


@dataclass(frozen=True)
class QualifiedSystemStage:
    module: str
    code: str
    legacy_stage_code: str
    source: MappingSource

    @property
    def qualified(self) -> str:
        return f"{self.module}.{self.code}"


def recruitment_legacy_to_pe_map() -> dict[str, str]:
    """Build legacy funnel stage code → PE system stage code (compat + manifest)."""
    manifest = recruitment_module_manifest()
    mapping: dict[str, str] = {}

    for row in manifest.get("system_stages") or []:
        code = str(row.get("code") or "").strip()
        if not code:
            continue
        mapping[code] = code
        alias = str((row.get("config") or {}).get("alias_of") or "").strip()
        if alias:
            mapping[alias] = code

    for pipeline in manifest.get("pipeline_templates") or []:
        for stage in (pipeline.get("config") or {}).get("stages") or []:
            pe_code = str(stage.get("maps_to_code") or "").strip()
            legacy_code = str(stage.get("legacy_funnel_stage_code") or "").strip()
            if legacy_code and pe_code:
                mapping[legacy_code] = pe_code

    mapping.update(_EXTENDED_LEGACY_PE_COMPAT)
    return mapping


# Legacy driver / recruitment funnel codes without 1:1 PE registry rows (compat only).
_EXTENDED_LEGACY_PE_COMPAT: dict[str, str] = {
    "docs_submitted_permit": "processing_by_client",
    "permit_ordered": "processing_by_client",
    "permit_received": "processing_by_client",
    "visa": "processing_by_client",
    "red_paper": "processing_by_client",
    "trip_plan": "processing_by_client",
    "at_client": "processing_by_client",
    "employment_pending": "processing_by_client",
    "on_trip": "employed",
    "handoff_returned": "processing_by_client",
    "ready_for_hr": "ready_for_handoff",
    "probation_ok": "employed",
}


def infer_pe_system_stage_code(legacy_stage_code: str) -> Optional[str]:
    code = str(legacy_stage_code or "").strip().lower()
    if not code:
        return None
    return recruitment_legacy_to_pe_map().get(code)


def infer_pe_mapping(legacy_stage_code: str) -> Optional[tuple[str, str]]:
    pe_code = infer_pe_system_stage_code(legacy_stage_code)
    if not pe_code:
        return None
    return MANIFEST_RECRUITMENT_MODULE, pe_code


async def validate_pe_system_stage(
    db: AsyncSession,
    *,
    tenant_id: str,
    module: str,
    code: str,
) -> bool:
    stmt = (
        select(PeSystemStage.id)
        .where(
            PeSystemStage.module == module,
            PeSystemStage.code == code,
            PeSystemStage.status == REGISTRY_STATUS_ACTIVE,
            PeSystemStage.tenant_id.in_([str(tenant_id), PLATFORM_TENANT_SCOPE]),
        )
        .limit(1)
    )
    return (await db.execute(stmt)).scalar_one_or_none() is not None


async def apply_pe_mapping_to_funnel_stage(
    db: AsyncSession,
    stage: FunnelStage,
    *,
    tenant_id: str,
    module: str,
    code: str,
    source: MappingSource = "pipeline_template",
) -> bool:
    module = str(module or RECRUITMENT_MODULE).strip()
    code = str(code or "").strip()
    if not code:
        return False
    if not await validate_pe_system_stage(db, tenant_id=tenant_id, module=module, code=code):
        return False
    changed = stage.pe_maps_to_module != module or stage.pe_maps_to_code != code
    stage.pe_maps_to_module = module
    stage.pe_maps_to_code = code
    return changed


async def ensure_funnel_stage_pe_mapping(
    db: AsyncSession,
    stage: FunnelStage,
    *,
    tenant_id: str,
    module: str = RECRUITMENT_MODULE,
) -> bool:
    """Ensure a candidate funnel stage has valid PE mapping; infer from legacy code when missing."""
    existing_module = str(getattr(stage, "pe_maps_to_module", None) or "").strip()
    existing_code = str(getattr(stage, "pe_maps_to_code", None) or "").strip()
    if existing_module and existing_code:
        if await validate_pe_system_stage(
            db, tenant_id=tenant_id, module=existing_module, code=existing_code
        ):
            return False

    inferred = infer_pe_mapping(str(stage.code or ""))
    if inferred is None:
        return False
    mod, pe_code = inferred
    return await apply_pe_mapping_to_funnel_stage(
        db,
        stage,
        tenant_id=tenant_id,
        module=mod,
        code=pe_code,
        source="legacy_compat",
    )


async def sync_funnel_stages_from_pipeline_config(
    db: AsyncSession,
    *,
    tenant_id: str,
    pipeline_config: dict[str, Any],
    legacy_funnel_id: str | None = None,
    module: str = RECRUITMENT_MODULE,
) -> int:
    """Map FunnelStage rows from pipeline template config (manifest source of truth)."""
    stages_cfg = list((pipeline_config or {}).get("stages") or [])
    if not stages_cfg:
        return 0

    legacy_by_code: dict[str, dict[str, Any]] = {}
    for stage in stages_cfg:
        legacy_code = str(stage.get("legacy_funnel_stage_code") or "").strip()
        pe_code = str(stage.get("maps_to_code") or "").strip()
        if legacy_code:
            legacy_by_code[legacy_code] = stage
        if pe_code:
            legacy_by_code.setdefault(pe_code, stage)

    funnel_id = legacy_funnel_id
    if not funnel_id:
        funnel = (
            await db.execute(
                select(Funnel).where(
                    Funnel.tenant_id == tenant_id,
                    Funnel.type == "candidate",
                    Funnel.is_default.is_(True),
                ).limit(1)
            )
        ).scalar_one_or_none()
        funnel_id = funnel.id if funnel else None
    if not funnel_id:
        return 0

    funnel_stages = (
        await db.execute(select(FunnelStage).where(FunnelStage.funnel_id == funnel_id))
    ).scalars().all()
    updated = 0
    for fs in funnel_stages:
        stage_code = str(fs.code or "").strip()
        mapping = legacy_by_code.get(stage_code)
        if mapping:
            mod = str(mapping.get("maps_to_module") or module).strip()
            code = str(mapping.get("maps_to_code") or "").strip()
            if code and await apply_pe_mapping_to_funnel_stage(
                db,
                fs,
                tenant_id=tenant_id,
                module=mod,
                code=code,
                source="pipeline_template",
            ):
                updated += 1
                continue
        if await ensure_funnel_stage_pe_mapping(db, fs, tenant_id=tenant_id, module=module):
            updated += 1
    return updated


async def ensure_recruitment_funnel_stages_mapped(
    db: AsyncSession,
    *,
    tenant_id: str,
    funnel_id: str | None = None,
) -> int:
    """Backfill PE mapping for all stages in tenant candidate funnels."""
    stmt = select(Funnel).where(
        Funnel.tenant_id == str(tenant_id),
        Funnel.type == "candidate",
    )
    if funnel_id:
        stmt = stmt.where(Funnel.id == funnel_id)
    funnels = list((await db.execute(stmt)).scalars().all())
    updated = 0
    for funnel in funnels:
        stages = (
            await db.execute(select(FunnelStage).where(FunnelStage.funnel_id == funnel.id))
        ).scalars().all()
        for stage in stages:
            if await ensure_funnel_stage_pe_mapping(
                db, stage, tenant_id=str(tenant_id), module=RECRUITMENT_MODULE
            ):
                updated += 1
    return updated


async def _resolve_candidate_funnel_id(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate: Candidate,
) -> Optional[str]:
    from backend.app.services.recruitment_funnel_assignment import (
        resolve_candidate_funnel_id_for_runtime,
    )

    return await resolve_candidate_funnel_id_for_runtime(
        db, tenant_id=str(tenant_id), candidate=candidate
    )


async def resolve_qualified_system_stage(
    db: AsyncSession,
    *,
    tenant_id: str,
    legacy_stage_code: str,
    funnel_id: str | None = None,
    module: str = RECRUITMENT_MODULE,
) -> Optional[QualifiedSystemStage]:
    legacy = str(legacy_stage_code or "").strip().lower()
    if not legacy:
        return None

    if funnel_id:
        stage_row = (
            await db.execute(
                select(FunnelStage).where(
                    FunnelStage.funnel_id == funnel_id,
                    FunnelStage.code == legacy,
                ).limit(1)
            )
        ).scalar_one_or_none()
        if stage_row is not None:
            pe_module = str(getattr(stage_row, "pe_maps_to_module", None) or "").strip()
            pe_code = str(getattr(stage_row, "pe_maps_to_code", None) or "").strip()
            if pe_module and pe_code:
                return QualifiedSystemStage(
                    module=pe_module,
                    code=pe_code,
                    legacy_stage_code=legacy,
                    source="funnel_stage",
                )

    inferred = infer_pe_mapping(legacy)
    if inferred is None:
        return None
    mod, pe_code = inferred
    source: MappingSource = "identity" if legacy == pe_code else "legacy_compat"
    return QualifiedSystemStage(
        module=mod,
        code=pe_code,
        legacy_stage_code=legacy,
        source=source,
    )


async def resolve_qualified_system_stage_for_candidate(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate_id: str,
    legacy_stage_code: str,
    module: str = RECRUITMENT_MODULE,
) -> Optional[QualifiedSystemStage]:
    candidate = (
        await db.execute(
            select(Candidate).where(
                Candidate.id == candidate_id,
                Candidate.tenant_id == str(tenant_id),
            )
        )
    ).scalar_one_or_none()
    if candidate is None:
        return None
    funnel_id = await _resolve_candidate_funnel_id(db, tenant_id=str(tenant_id), candidate=candidate)
    return await resolve_qualified_system_stage(
        db,
        tenant_id=str(tenant_id),
        legacy_stage_code=legacy_stage_code,
        funnel_id=funnel_id,
        module=module,
    )


def qualified_system_stage_to_dict(stage: QualifiedSystemStage) -> dict[str, str]:
    return {
        "qualified_system_stage": stage.qualified,
        "system_stage_module": stage.module,
        "system_stage_code": stage.code,
        "legacy_stage_code": stage.legacy_stage_code,
        "mapping_source": stage.source,
    }
