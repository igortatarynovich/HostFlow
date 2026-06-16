"""Process Engine transition rules adapter (P6 — profile-scoped hiring pipeline gates)."""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.process_engine import (
    REGISTRY_STATUS_ACTIVE,
    PeProcessProfile,
    PeTransitionRule,
)
from backend.app.process_engine.constants import RECRUITMENT_MODULE
from backend.app.process_engine.manifests.recruitment import (
    DEFAULT_PROFILE_CODE,
    RECRUITMENT_PIPELINE_GATES_RULE_CODE,
)
from backend.app.process_engine.profile_resolver import (
    EffectiveProcessProfile,
    resolve_effective_process_profile_for_candidate_id,
)
from backend.app.services.hiring_pipeline_gates import (
    SETTINGS_KEY,
    HiringPipelineGates,
    default_hiring_pipeline_gates,
    hiring_gates_from_tenant_settings,
    merge_hiring_pipeline_gates,
    serialize_gates_public,
)

RULE_KIND_HIRING_PIPELINE_GATES = "hiring_pipeline_gates"

_GATE_CONFIG_KEYS = (
    "stages_without_doc_pipeline_block",
    "stages_verify_uploads_block_forward",
    "stages_require_vacancy_for_forward",
    "contact_attempt_gate_stages",
    "stages_doc_block_soft_only",
    "non_overridable_doc_types_extra",
)


def hiring_pipeline_gates_config_from_gates(gates: HiringPipelineGates) -> dict[str, Any]:
    public = serialize_gates_public(gates)
    return {
        "rule_kind": RULE_KIND_HIRING_PIPELINE_GATES,
        "version": public.get("version", 1),
        "legacy_settings_key": SETTINGS_KEY,
        "gates": {key: public[key] for key in _GATE_CONFIG_KEYS},
    }


def default_hiring_pipeline_gates_rule_config() -> dict[str, Any]:
    return hiring_pipeline_gates_config_from_gates(default_hiring_pipeline_gates())


def gates_from_transition_rule_config(config: dict[str, Any] | None) -> HiringPipelineGates | None:
    if not config or not isinstance(config, dict):
        return None
    if str(config.get("rule_kind") or "").strip() != RULE_KIND_HIRING_PIPELINE_GATES:
        return None
    gates_raw = config.get("gates")
    if not isinstance(gates_raw, dict):
        return None
    return merge_hiring_pipeline_gates(gates_raw)


async def load_hiring_pipeline_gates_rule(
    db: AsyncSession,
    *,
    tenant_id: str,
    process_profile_id: str,
    rule_code: str = RECRUITMENT_PIPELINE_GATES_RULE_CODE,
) -> PeTransitionRule | None:
    return (
        await db.execute(
            select(PeTransitionRule)
            .where(
                PeTransitionRule.tenant_id == str(tenant_id),
                PeTransitionRule.module == RECRUITMENT_MODULE,
                PeTransitionRule.process_profile_id == str(process_profile_id),
                PeTransitionRule.code == rule_code,
                PeTransitionRule.status == REGISTRY_STATUS_ACTIVE,
            )
            .limit(1)
        )
    ).scalar_one_or_none()


async def resolve_hiring_pipeline_gates_from_process_profile(
    db: AsyncSession,
    *,
    tenant_id: str,
    process_profile_id: str,
) -> tuple[HiringPipelineGates | None, dict[str, Any]]:
    rule = await load_hiring_pipeline_gates_rule(
        db,
        tenant_id=str(tenant_id),
        process_profile_id=str(process_profile_id),
    )
    if rule is None:
        return None, {"source": "tenant_settings_fallback", "process_profile_id": process_profile_id}
    gates = gates_from_transition_rule_config(dict(rule.config or {}))
    if gates is None:
        return None, {
            "source": "tenant_settings_fallback",
            "process_profile_id": process_profile_id,
            "transition_rule_code": rule.code,
        }
    return gates, {
        "source": "pe_transition_rules",
        "process_profile_id": process_profile_id,
        "transition_rule_code": rule.code,
        "transition_rule_id": rule.id,
    }


async def resolve_hiring_pipeline_gates_for_candidate(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate_id: str,
) -> tuple[HiringPipelineGates, dict[str, Any]]:
    """Resolve gates for candidate via effective process profile; tenant blob is fallback."""
    from backend.app.api.v1.tenants import service as tenant_service

    effective = await resolve_effective_process_profile_for_candidate_id(
        db,
        tenant_id=str(tenant_id),
        candidate_id=str(candidate_id),
    )
    if effective is not None:
        pe_gates, meta = await resolve_hiring_pipeline_gates_from_process_profile(
            db,
            tenant_id=str(tenant_id),
            process_profile_id=effective.profile_id,
        )
        if pe_gates is not None:
            meta["process_profile_source"] = effective.source
            meta["process_profile_code"] = effective.profile_code
            return pe_gates, meta

    tenant = await tenant_service.get_tenant(db, str(tenant_id))
    tenant_gates = hiring_gates_from_tenant_settings(
        tenant.settings if tenant and isinstance(tenant.settings, dict) else None
    )
    return tenant_gates, {
        "source": "tenant_settings_fallback",
        "deprecated_settings_key": SETTINGS_KEY,
        "process_profile_source": effective.source if effective else None,
    }


async def upsert_hiring_pipeline_gates_transition_rule(
    db: AsyncSession,
    *,
    tenant_id: str,
    process_profile_id: str,
    gates: HiringPipelineGates,
    rule_code: str = RECRUITMENT_PIPELINE_GATES_RULE_CODE,
) -> PeTransitionRule:
    rule = await load_hiring_pipeline_gates_rule(
        db,
        tenant_id=str(tenant_id),
        process_profile_id=str(process_profile_id),
        rule_code=rule_code,
    )
    if rule is None:
        from uuid import uuid4

        rule = PeTransitionRule(
            id=str(uuid4()),
            tenant_id=str(tenant_id),
            module=RECRUITMENT_MODULE,
            code=rule_code,
            name="Recruitment pipeline stage gates",
            process_profile_id=str(process_profile_id),
        )
        db.add(rule)
    rule.status = REGISTRY_STATUS_ACTIVE
    rule.registry_version = "process_engine_v1"
    rule.is_system = True
    rule.priority = 100
    rule.config = hiring_pipeline_gates_config_from_gates(gates)
    await db.flush()
    return rule


async def sync_tenant_hiring_gates_to_default_profile_rule(
    db: AsyncSession,
    *,
    tenant_id: str,
    profile_code: str = DEFAULT_PROFILE_CODE,
) -> bool:
    """Migrate tenant.settings hiring_stage_gates_v1 into default profile PE transition rule."""
    from backend.app.api.v1.tenants import service as tenant_service

    tenant = await tenant_service.get_tenant(db, str(tenant_id))
    if tenant is None:
        return False
    settings = tenant.settings if isinstance(tenant.settings, dict) else None
    raw = (settings or {}).get(SETTINGS_KEY) if settings else None

    profile = (
        await db.execute(
            select(PeProcessProfile).where(
                PeProcessProfile.tenant_id == str(tenant_id),
                PeProcessProfile.module == RECRUITMENT_MODULE,
                PeProcessProfile.code == profile_code,
            ).limit(1)
        )
    ).scalar_one_or_none()
    if profile is None:
        return False

    if isinstance(raw, dict) and raw:
        gates = merge_hiring_pipeline_gates(raw)
    else:
        gates = default_hiring_pipeline_gates()

    await upsert_hiring_pipeline_gates_transition_rule(
        db,
        tenant_id=str(tenant_id),
        process_profile_id=str(profile.id),
        gates=gates,
    )
    return True


async def sync_hiring_gates_to_default_profile_from_tenant_settings(
    db: AsyncSession,
    *,
    tenant_id: str,
    gates: HiringPipelineGates,
) -> None:
    """Dual-write helper: legacy Settings editor → default profile transition rule."""
    profile = (
        await db.execute(
            select(PeProcessProfile).where(
                PeProcessProfile.tenant_id == str(tenant_id),
                PeProcessProfile.module == RECRUITMENT_MODULE,
                PeProcessProfile.code == DEFAULT_PROFILE_CODE,
            ).limit(1)
        )
    ).scalar_one_or_none()
    if profile is None:
        return
    await upsert_hiring_pipeline_gates_transition_rule(
        db,
        tenant_id=str(tenant_id),
        process_profile_id=str(profile.id),
        gates=gates,
    )
