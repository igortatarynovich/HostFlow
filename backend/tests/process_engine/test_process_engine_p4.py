"""Process Engine P4 — FunnelStage → qualified system stage mapping."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from backend.app.process_engine.constants import RECRUITMENT_MODULE
from backend.app.process_engine.evaluator_adapter import TransitionEvaluatorAdapter
from backend.app.process_engine.manifests.recruitment import DEFAULT_PIPELINE_CODE
from backend.app.process_engine.pipeline_mapping import (
    infer_pe_system_stage_code,
    recruitment_legacy_to_pe_map,
    resolve_qualified_system_stage,
)
from backend.app.process_engine import pipeline_mapping as mapping_module
from backend.tests.test_support.repo_paths import read_repo_text


def test_p4_legacy_docs_wait_maps_to_waiting_documents() -> None:
    assert infer_pe_system_stage_code("docs_wait") == "waiting_documents"


def test_p4_legacy_docs_got_maps_to_documents_received() -> None:
    assert infer_pe_system_stage_code("docs_got") == "documents_received"


def test_p4_ready_for_handoff_maps_to_recruitment_ready_for_handoff() -> None:
    mapping = recruitment_legacy_to_pe_map()
    assert mapping["ready_for_handoff"] == "ready_for_handoff"
    assert infer_pe_system_stage_code("ready_for_handoff") == "ready_for_handoff"


def test_p4_manifest_pipeline_includes_default_stages() -> None:
    mapping = recruitment_legacy_to_pe_map()
    assert mapping["new"] == "new"
    assert mapping["contacted"] == "contacted"
    assert mapping["rejected"] == "rejected"


@pytest.mark.anyio
async def test_p4_funnel_stage_mapping_wins_over_legacy_compat(monkeypatch: pytest.MonkeyPatch) -> None:
    stage_row = SimpleNamespace(
        code="custom_handoff",
        pe_maps_to_module=RECRUITMENT_MODULE,
        pe_maps_to_code="ready_for_handoff",
    )

    class _Result:
        def scalar_one_or_none(self):
            return stage_row

    db = SimpleNamespace(execute=AsyncMock(return_value=_Result()))
    resolved = await resolve_qualified_system_stage(
        db,  # type: ignore[arg-type]
        tenant_id="tenant-1",
        legacy_stage_code="custom_handoff",
        funnel_id="funnel-1",
    )

    assert resolved is not None
    assert resolved.source == "funnel_stage"
    assert resolved.code == "ready_for_handoff"
    assert resolved.qualified == "recruitment.ready_for_handoff"


@pytest.mark.anyio
async def test_p4_evaluator_resolves_legacy_stage_before_transfer_policy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, str | None] = {}

    async def _resolve(db, *, tenant_id, candidate_id, target_stage=None, require_destination=False):
        captured["target_stage"] = target_stage
        return {"transfer_allowed": True, "handoff_create_allowed": True, "blocking_reasons": [], "source_layers": []}

    monkeypatch.setattr(
        "backend.app.process_engine.evaluator_adapter.TransferPolicyResolver.resolve",
        _resolve,
    )
    monkeypatch.setattr(
        "backend.app.requirement_rules.transition_bridge.evaluate_ready_for_handoff_requirement_gate",
        AsyncMock(return_value=None),
    )
    monkeypatch.setattr(
        TransitionEvaluatorAdapter,
        "_resolve_recruitment_target_system_stage",
        AsyncMock(return_value="ready_for_handoff"),
    )

    await TransitionEvaluatorAdapter.assert_transition_allowed(
        db=None,  # type: ignore[arg-type]
        tenant_id="tenant-1",
        module=RECRUITMENT_MODULE,
        entity_type="candidate",
        entity_id="cand-1",
        target_system_stage="docs_got",
        require_destination=False,
    )

    assert captured["target_stage"] == "ready_for_handoff"


@pytest.mark.anyio
async def test_p4_sync_from_pipeline_config_sets_pe_maps(monkeypatch: pytest.MonkeyPatch) -> None:
    stage = SimpleNamespace(
        code="docs_wait",
        pe_maps_to_module=None,
        pe_maps_to_code=None,
    )

    class _StagesResult:
        def scalars(self):
            return self

        def all(self):
            return [stage]

    async def _execute(stmt):
        return _StagesResult()

    db = SimpleNamespace(execute=_execute)
    validate_mock = AsyncMock(return_value=True)
    monkeypatch.setattr(mapping_module, "validate_pe_system_stage", validate_mock)

    pipeline_config = {
        "stages": [
            {
                "legacy_funnel_stage_code": "docs_wait",
                "maps_to_module": RECRUITMENT_MODULE,
                "maps_to_code": "waiting_documents",
            }
        ]
    }
    updated = await mapping_module.sync_funnel_stages_from_pipeline_config(
        db,  # type: ignore[arg-type]
        tenant_id="tenant-1",
        pipeline_config=pipeline_config,
        legacy_funnel_id="funnel-1",
    )

    assert updated == 1
    assert stage.pe_maps_to_module == RECRUITMENT_MODULE
    assert stage.pe_maps_to_code == "waiting_documents"


def test_p4_funnel_stage_model_has_pe_mapping_columns() -> None:
    from backend.app.models.funnel import FunnelStage

    assert hasattr(FunnelStage, "pe_maps_to_module")
    assert hasattr(FunnelStage, "pe_maps_to_code")


def test_p4_funnels_api_enforces_pe_mapping_helper() -> None:
    source = read_repo_text("backend/app/api/v1/funnels.py")
    assert "_require_candidate_funnel_pe_mapping" in source


def test_p4_default_pipeline_code_is_canonical() -> None:
    assert DEFAULT_PIPELINE_CODE == "recruitment_agency_default"
