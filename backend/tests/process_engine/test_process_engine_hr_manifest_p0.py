"""HR Process Engine manifest P0 — stage registration tests."""

from __future__ import annotations

import pytest
from sqlalchemy import func, select

from backend.app.models.process_engine import (
    PeHandoffRule,
    PePipelineTemplate,
    PeProcessProfile,
    PeSystemStage,
    REGISTRY_STATUS_ACTIVE,
)
from backend.app.process_engine.constants import HR_MODULE
from backend.app.process_engine.manifests.hr import (
    HR_INBOUND_HANDOFF_PLACEHOLDER_MODE,
    RECRUITMENT_LEGACY_ANALYTICS_BUCKETS,
    hr_module_manifest,
)
from backend.app.process_engine.pipeline_mapping import validate_pe_system_stage
from backend.app.process_engine.registry import ProcessEngineRegistry
from backend.app.process_engine.seed import ensure_hr_process_engine_stages


def test_hr_manifest_declares_hr_module_stages_only() -> None:
    manifest = hr_module_manifest()
    assert manifest["module"] == HR_MODULE
    assert manifest["pipeline_templates"] == []
    assert manifest["process_profiles"] == []
    assert manifest["transition_rules"] == []
    stage_codes = {row["code"] for row in manifest["system_stages"]}
    assert "received_from_recruitment" in stage_codes
    assert "verification" in stage_codes
    assert "active" in stage_codes
    assert "ready_for_handoff" not in stage_codes


def test_hr_manifest_analytics_buckets_are_hr_specific() -> None:
    manifest = hr_module_manifest()
    buckets = {row["analytics_bucket"] for row in manifest["system_stages"]}
    assert buckets.isdisjoint(RECRUITMENT_LEGACY_ANALYTICS_BUCKETS)
    assert "intake" in buckets
    assert "verification" in buckets
    assert "active" in buckets


def test_hr_manifest_inbound_handoff_placeholder_only() -> None:
    manifest = hr_module_manifest()
    assert len(manifest["handoff_rules"]) == 1
    rule = manifest["handoff_rules"][0]
    assert rule["handoff_mode"] == HR_INBOUND_HANDOFF_PLACEHOLDER_MODE
    assert rule["config"]["entry_system_stage"] == "received_from_recruitment"
    assert rule["config"]["status"] == "placeholder"
    assert "source" not in rule["config"]


@pytest.mark.anyio
async def test_hr_module_registers_system_stages(db) -> None:
    tenant_id = "pe-hr-manifest-tenant"
    try:
        await db.execute(
            select(PeSystemStage).where(PeSystemStage.tenant_id == tenant_id).limit(1)
        )
    except Exception as exc:
        pytest.skip(f"Process Engine tables not available: {exc}")

    manifest = hr_module_manifest()
    await ProcessEngineRegistry.register_module(db, manifest, tenant_id=tenant_id)
    await db.commit()

    stage_count = await db.scalar(
        select(func.count())
        .select_from(PeSystemStage)
        .where(
            PeSystemStage.module == HR_MODULE,
            PeSystemStage.tenant_id == tenant_id,
            PeSystemStage.status == REGISTRY_STATUS_ACTIVE,
        )
    )
    assert stage_count == len(manifest["system_stages"])

    profile_count = await db.scalar(
        select(func.count())
        .select_from(PeProcessProfile)
        .where(PeProcessProfile.module == HR_MODULE, PeProcessProfile.tenant_id == tenant_id)
    )
    pipeline_count = await db.scalar(
        select(func.count())
        .select_from(PePipelineTemplate)
        .where(PePipelineTemplate.module == HR_MODULE, PePipelineTemplate.tenant_id == tenant_id)
    )
    assert profile_count == 0
    assert pipeline_count == 0

    handoff_count = await db.scalar(
        select(func.count())
        .select_from(PeHandoffRule)
        .where(PeHandoffRule.module == HR_MODULE, PeHandoffRule.tenant_id == tenant_id)
    )
    assert handoff_count == 1


@pytest.mark.anyio
async def test_validate_pe_system_stage_finds_hr_received_from_recruitment(db) -> None:
    tenant_id = "pe-hr-validate-tenant"
    try:
        await db.execute(
            select(PeSystemStage).where(PeSystemStage.tenant_id == tenant_id).limit(1)
        )
    except Exception as exc:
        pytest.skip(f"Process Engine tables not available: {exc}")

    await ProcessEngineRegistry.register_module(
        db, hr_module_manifest(), tenant_id=tenant_id
    )
    await db.commit()

    ok = await validate_pe_system_stage(
        db,
        tenant_id=tenant_id,
        module=HR_MODULE,
        code="received_from_recruitment",
    )
    assert ok is True

    bad = await validate_pe_system_stage(
        db,
        tenant_id=tenant_id,
        module=HR_MODULE,
        code="ready_for_handoff",
    )
    assert bad is False


@pytest.mark.anyio
async def test_ensure_hr_process_engine_stages_skips_when_hr_disabled(db, tenant_id: str) -> None:
    try:
        await db.execute(
            select(PeSystemStage).where(PeSystemStage.tenant_id == tenant_id).limit(1)
        )
    except Exception as exc:
        pytest.skip(f"Process Engine tables not available: {exc}")

    result = await ensure_hr_process_engine_stages(db, tenant_id)
    assert result == {}
