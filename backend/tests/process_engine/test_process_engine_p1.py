"""Process Engine P1 — recruitment manifest and registry tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import func, select, text

from backend.app.models.process_engine import (
    PeHandoffRule,
    PePipelineTemplate,
    PeProcessProfile,
    PeSystemStage,
    PeTransitionRule,
    REGISTRY_STATUS_ACTIVE,
)
from backend.app.process_engine.constants import RECRUITMENT_MODULE
from backend.app.process_engine.evaluator_adapter import TransitionEvaluatorAdapter
from backend.app.process_engine.manifests.recruitment import (
    DEFAULT_PIPELINE_CODE,
    DEFAULT_PROFILE_CODE,
    HANDOFF_MODES,
    recruitment_module_manifest,
)
from backend.app.process_engine.registry import ProcessEngineRegistry
from backend.app.process_engine.seed import ensure_recruitment_process_engine_defaults


def test_recruitment_manifest_declares_core_stages_and_handoff_modes() -> None:
    manifest = recruitment_module_manifest()
    assert manifest["module"] == RECRUITMENT_MODULE
    stage_codes = {row["code"] for row in manifest["system_stages"]}
    assert "ready_for_handoff" in stage_codes
    assert "waiting_documents" in stage_codes
    assert "documents_received" in stage_codes
    handoff_modes = {row["handoff_mode"] for row in manifest["handoff_rules"]}
    assert handoff_modes == HANDOFF_MODES
    assert manifest["process_profiles"][0]["code"] == DEFAULT_PROFILE_CODE
    assert manifest["pipeline_templates"][0]["code"] == DEFAULT_PIPELINE_CODE


@pytest.mark.anyio
async def test_recruitment_module_registers_default_stages_profile_pipeline(db) -> None:
    tenant_id = "pe-test-tenant-1"
    try:
        await db.execute(
            select(PeSystemStage).where(PeSystemStage.tenant_id == tenant_id).limit(1)
        )
    except Exception as exc:
        pytest.skip(f"Process Engine tables not available: {exc}")

    manifest = recruitment_module_manifest()
    await ProcessEngineRegistry.register_module(db, manifest, tenant_id=tenant_id)
    await db.commit()

    stage_count = await db.scalar(
        select(func.count())
        .select_from(PeSystemStage)
        .where(
            PeSystemStage.module == RECRUITMENT_MODULE,
            PeSystemStage.tenant_id == tenant_id,
            PeSystemStage.status == REGISTRY_STATUS_ACTIVE,
        )
    )
    assert stage_count == len(manifest["system_stages"])

    profile = await ProcessEngineRegistry.get_default_process_profile(
        db, module=RECRUITMENT_MODULE, tenant_id=tenant_id
    )
    assert profile is not None
    assert profile.code == DEFAULT_PROFILE_CODE
    assert profile.is_default is True
    assert profile.pipeline_template_id is not None

    pipeline = (
        await db.execute(
            select(PePipelineTemplate).where(PePipelineTemplate.id == profile.pipeline_template_id)
        )
    ).scalar_one()
    assert pipeline.code == DEFAULT_PIPELINE_CODE
    assert len((pipeline.config or {}).get("stages") or []) >= 5

    handoff_count = await db.scalar(
        select(func.count())
        .select_from(PeHandoffRule)
        .where(PeHandoffRule.tenant_id == tenant_id, PeHandoffRule.module == RECRUITMENT_MODULE)
    )
    assert handoff_count == 4

    transition_count = await db.scalar(
        select(func.count())
        .select_from(PeTransitionRule)
        .where(PeTransitionRule.tenant_id == tenant_id, PeTransitionRule.module == RECRUITMENT_MODULE)
    )
    assert transition_count >= 1


@pytest.mark.anyio
async def test_ensure_recruitment_defaults_is_idempotent(db) -> None:
    tenant_id = "pe-test-tenant-2"
    try:
        await db.execute(text("SELECT 1 FROM pe_system_stages LIMIT 1"))
    except Exception as exc:
        pytest.skip(f"Process Engine tables not available: {exc}")

    first = await ensure_recruitment_process_engine_defaults(db, tenant_id)
    await db.commit()
    second = await ensure_recruitment_process_engine_defaults(db, tenant_id)
    await db.commit()

    assert first["module"] == RECRUITMENT_MODULE
    assert second["module"] == RECRUITMENT_MODULE
    stage_count = await db.scalar(
        select(func.count())
        .select_from(PeSystemStage)
        .where(PeSystemStage.tenant_id == tenant_id, PeSystemStage.module == RECRUITMENT_MODULE)
    )
    assert stage_count == len(recruitment_module_manifest()["system_stages"])


@pytest.mark.anyio
async def test_transition_evaluator_adapter_delegates_to_transfer_policy(monkeypatch) -> None:
    expected = {"transfer_allowed": False, "policy_version": "transfer_policy_v1", "blocking_reasons": []}

    with patch(
        "backend.app.process_engine.evaluator_adapter.TransferPolicyResolver.resolve",
        new=AsyncMock(return_value=expected),
    ) as resolve_mock, patch.object(
        TransitionEvaluatorAdapter,
        "_resolve_recruitment_target_system_stage",
        new=AsyncMock(return_value="ready_for_handoff"),
    ), patch(
        "backend.app.requirement_rules.transition_bridge.evaluate_ready_for_handoff_requirement_gate",
        new=AsyncMock(return_value=None),
    ):
        report = await TransitionEvaluatorAdapter.evaluate_transition(
            db=None,  # type: ignore[arg-type]
            tenant_id="tenant-1",
            module=RECRUITMENT_MODULE,
            entity_type="candidate",
            entity_id="cand-1",
            target_system_stage="ready_for_handoff",
            require_destination=False,
        )

    resolve_mock.assert_awaited_once()
    assert report["allowed"] is False
    assert report["evaluator_hook"] == "recruitment.transfer_policy_v1"
