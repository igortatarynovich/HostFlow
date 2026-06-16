"""Process Engine P6 — profile-scoped hiring pipeline gates via pe_transition_rules."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from backend.app.process_engine.evaluator_adapter import TransitionEvaluatorAdapter
from backend.app.process_engine.manifests.recruitment import RECRUITMENT_PIPELINE_GATES_RULE_CODE
from backend.app.process_engine.transition_rules_adapter import (
    RULE_KIND_HIRING_PIPELINE_GATES,
    gates_from_transition_rule_config,
    hiring_pipeline_gates_config_from_gates,
    resolve_hiring_pipeline_gates_for_candidate,
    resolve_hiring_pipeline_gates_from_process_profile,
)
from backend.app.process_engine import transition_rules_adapter as adapter_module
from backend.app.services.hiring_pipeline_gates import (
    SETTINGS_KEY,
    HiringPipelineGates,
    default_hiring_pipeline_gates,
    merge_hiring_pipeline_gates,
)


def _custom_gates(*, contact_stages: frozenset[str] | None = None) -> HiringPipelineGates:
    base = default_hiring_pipeline_gates()
    return HiringPipelineGates(
        stages_without_doc_pipeline_block=base.stages_without_doc_pipeline_block,
        stages_verify_uploads_block_forward=base.stages_verify_uploads_block_forward,
        stages_require_vacancy_for_forward=base.stages_require_vacancy_for_forward,
        contact_attempt_gate_stages=contact_stages or frozenset({"new", "no_answer"}),
        stages_doc_block_soft_only=base.stages_doc_block_soft_only,
        non_overridable_doc_types_extra=base.non_overridable_doc_types_extra,
    )


def test_p6_gates_from_transition_rule_config_parses_pe_rule() -> None:
    custom = _custom_gates()
    config = hiring_pipeline_gates_config_from_gates(custom)
    assert config["rule_kind"] == RULE_KIND_HIRING_PIPELINE_GATES
    assert config["legacy_settings_key"] == SETTINGS_KEY

    parsed = gates_from_transition_rule_config(config)
    assert parsed is not None
    assert parsed.contact_attempt_gate_stages == custom.contact_attempt_gate_stages


def test_p6_gates_from_transition_rule_config_rejects_unknown_kind() -> None:
    assert gates_from_transition_rule_config({"rule_kind": "other", "gates": {}}) is None


@pytest.mark.anyio
async def test_p6_resolve_from_process_profile_uses_pe_rule(monkeypatch: pytest.MonkeyPatch) -> None:
    custom = _custom_gates(contact_stages=frozenset({"contacted"}))
    rule = SimpleNamespace(
        id="rule-1",
        code=RECRUITMENT_PIPELINE_GATES_RULE_CODE,
        config=hiring_pipeline_gates_config_from_gates(custom),
    )
    monkeypatch.setattr(adapter_module, "load_hiring_pipeline_gates_rule", AsyncMock(return_value=rule))

    gates, meta = await resolve_hiring_pipeline_gates_from_process_profile(
        db=None,  # type: ignore[arg-type]
        tenant_id="tenant-1",
        process_profile_id="profile-1",
    )

    assert meta["source"] == "pe_transition_rules"
    assert meta["transition_rule_code"] == RECRUITMENT_PIPELINE_GATES_RULE_CODE
    assert gates is not None
    assert gates.contact_attempt_gate_stages == frozenset({"contacted"})


@pytest.mark.anyio
async def test_p6_resolve_for_candidate_prefers_pe_over_tenant_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pe_gates = _custom_gates(contact_stages=frozenset({"questionnaire_submitted"}))
    tenant_gates = merge_hiring_pipeline_gates({"contact_attempt_gate_stages": ["new"]})

    monkeypatch.setattr(
        adapter_module,
        "resolve_effective_process_profile_for_candidate_id",
        AsyncMock(
            return_value=SimpleNamespace(
                profile_id="profile-pe",
                profile_code="recruitment_default",
                source="vacancy",
            )
        ),
    )
    monkeypatch.setattr(
        adapter_module,
        "resolve_hiring_pipeline_gates_from_process_profile",
        AsyncMock(
            return_value=(
                pe_gates,
                {"source": "pe_transition_rules", "transition_rule_code": RECRUITMENT_PIPELINE_GATES_RULE_CODE},
            )
        ),
    )
    tenant_mock = AsyncMock(
        return_value=SimpleNamespace(settings={SETTINGS_KEY: {"contact_attempt_gate_stages": ["new"]}})
    )
    monkeypatch.setattr("backend.app.api.v1.tenants.service.get_tenant", tenant_mock)

    gates, meta = await resolve_hiring_pipeline_gates_for_candidate(
        db=None,  # type: ignore[arg-type]
        tenant_id="tenant-1",
        candidate_id="cand-1",
    )

    assert meta["source"] == "pe_transition_rules"
    assert gates.contact_attempt_gate_stages == pe_gates.contact_attempt_gate_stages
    assert gates.contact_attempt_gate_stages != tenant_gates.contact_attempt_gate_stages
    tenant_mock.assert_not_called()


@pytest.mark.anyio
async def test_p6_resolve_for_candidate_falls_back_to_tenant_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        adapter_module,
        "resolve_effective_process_profile_for_candidate_id",
        AsyncMock(
            return_value=SimpleNamespace(
                profile_id="profile-pe",
                profile_code="recruitment_default",
                source="tenant_default",
            )
        ),
    )
    monkeypatch.setattr(
        adapter_module,
        "resolve_hiring_pipeline_gates_from_process_profile",
        AsyncMock(return_value=(None, {"source": "tenant_settings_fallback"})),
    )
    tenant_mock = AsyncMock(
        return_value=SimpleNamespace(
            settings={SETTINGS_KEY: {"contact_attempt_gate_stages": ["contacted"]}}
        )
    )
    monkeypatch.setattr("backend.app.api.v1.tenants.service.get_tenant", tenant_mock)

    gates, meta = await resolve_hiring_pipeline_gates_for_candidate(
        db=None,  # type: ignore[arg-type]
        tenant_id="tenant-1",
        candidate_id="cand-1",
    )

    assert meta["source"] == "tenant_settings_fallback"
    assert meta["deprecated_settings_key"] == SETTINGS_KEY
    assert gates.contact_attempt_gate_stages == frozenset({"contacted"})


@pytest.mark.anyio
async def test_p6_different_profiles_can_have_different_gates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    profile_a_gates = _custom_gates(contact_stages=frozenset({"new"}))
    profile_b_gates = _custom_gates(contact_stages=frozenset({"contacted"}))

    async def _resolve_from_profile(
        db,
        *,
        tenant_id: str,
        process_profile_id: str,
    ):
        if process_profile_id == "profile-a":
            return profile_a_gates, {"source": "pe_transition_rules"}
        if process_profile_id == "profile-b":
            return profile_b_gates, {"source": "pe_transition_rules"}
        return None, {"source": "tenant_settings_fallback"}

    monkeypatch.setattr(
        adapter_module,
        "resolve_hiring_pipeline_gates_from_process_profile",
        AsyncMock(side_effect=_resolve_from_profile),
    )

    async def _effective_profile(
        db,
        *,
        tenant_id: str,
        candidate_id: str,
        module=None,
    ):
        profile_id = "profile-a" if candidate_id == "cand-a" else "profile-b"
        return SimpleNamespace(
            profile_id=profile_id,
            profile_code="custom",
            source="vacancy",
        )

    monkeypatch.setattr(
        adapter_module,
        "resolve_effective_process_profile_for_candidate_id",
        AsyncMock(side_effect=_effective_profile),
    )

    gates_a, meta_a = await resolve_hiring_pipeline_gates_for_candidate(
        db=None,  # type: ignore[arg-type]
        tenant_id="t1",
        candidate_id="cand-a",
    )
    gates_b, meta_b = await resolve_hiring_pipeline_gates_for_candidate(
        db=None,  # type: ignore[arg-type]
        tenant_id="t1",
        candidate_id="cand-b",
    )

    assert meta_a["source"] == "pe_transition_rules"
    assert meta_b["source"] == "pe_transition_rules"
    assert gates_a.contact_attempt_gate_stages == frozenset({"new"})
    assert gates_b.contact_attempt_gate_stages == frozenset({"contacted"})


@pytest.mark.anyio
async def test_p6_evaluator_adapter_resolve_hiring_pipeline_gates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pe_gates = _custom_gates(contact_stages=frozenset({"no_answer"}))
    monkeypatch.setattr(
        adapter_module,
        "resolve_hiring_pipeline_gates_for_candidate",
        AsyncMock(
            return_value=(
                pe_gates,
                {
                    "source": "pe_transition_rules",
                    "process_profile_code": "recruitment_default",
                },
            )
        ),
    )

    payload = await TransitionEvaluatorAdapter.resolve_hiring_pipeline_gates(
        db=None,  # type: ignore[arg-type]
        tenant_id="tenant-1",
        candidate_id="cand-1",
    )

    assert payload["resolution"]["source"] == "pe_transition_rules"
    assert payload["contact_attempt_gate_stages"] == sorted(pe_gates.contact_attempt_gate_stages)
    assert payload["deprecated_tenant_settings_key"] == SETTINGS_KEY
