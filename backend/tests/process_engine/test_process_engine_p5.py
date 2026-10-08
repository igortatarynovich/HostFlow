"""Process Engine P5 — handoff rule registry activation and destination matrix."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from backend.app.process_engine.constants import RECRUITMENT_MODULE
from backend.app.process_engine.evaluator_adapter import TransitionEvaluatorAdapter
from backend.app.process_engine.handoff_evaluator import (
    DESTINATION_CLIENT,
    DESTINATION_INTERNAL_HR,
    HandoffEvaluation,
    _apply_tenant_link_destination_flags,
    _destination_types_for_mode,
    evaluate_handoff_destinations,
    resolve_handoff_mode_from_profile,
)
from backend.app.process_engine import handoff_evaluator as handoff_module
from backend.tests.test_support.repo_paths import read_repo_text


def _tenant_link(*, internal_hr: bool = True, client: bool = True, enabled: bool = True) -> SimpleNamespace:
    return SimpleNamespace(
        get_handoff_enabled=lambda: enabled,
        get_handoff_to_client=lambda: client and enabled,
        get_handoff_to_internal_hr=lambda: internal_hr and enabled,
        get_workforce_handoff_on_ready_for_handoff_stage=lambda: False,
    )


def _profile(*, handoff_mode: str = "both") -> SimpleNamespace:
    return SimpleNamespace(
        config={
            "handoff_mode": handoff_mode,
            "stage_overrides": {
                "ready_for_handoff": {"handoff_mode": handoff_mode},
            },
        }
    )


def test_p5_destination_matrix_both_with_hr_and_link() -> None:
    installed = {RECRUITMENT_MODULE, "hr"}
    pe_types = _destination_types_for_mode("both", installed_modules=installed)
    destinations = _apply_tenant_link_destination_flags(pe_types, _tenant_link())
    assert destinations == [DESTINATION_INTERNAL_HR, DESTINATION_CLIENT]


def test_p5_hr_destination_disabled_when_hr_module_not_installed() -> None:
    installed = {RECRUITMENT_MODULE}
    pe_types = _destination_types_for_mode("both", installed_modules=installed)
    destinations = _apply_tenant_link_destination_flags(pe_types, _tenant_link())
    assert DESTINATION_INTERNAL_HR not in destinations
    assert DESTINATION_CLIENT in destinations


def test_p5_client_portal_works_recruitment_only() -> None:
    installed = {RECRUITMENT_MODULE}
    pe_types = _destination_types_for_mode("client_portal", installed_modules=installed)
    destinations = _apply_tenant_link_destination_flags(pe_types, _tenant_link(internal_hr=False))
    assert destinations == [DESTINATION_CLIENT]


def test_p5_internal_hr_mode_requires_hr_module() -> None:
    installed = {RECRUITMENT_MODULE}
    assert _destination_types_for_mode("internal_hr", installed_modules=installed) == set()
    installed_hr = {RECRUITMENT_MODULE, "hr"}
    assert _destination_types_for_mode("internal_hr", installed_modules=installed_hr) == {
        DESTINATION_INTERNAL_HR
    }


def test_p5_tenant_link_flags_still_gate_destinations() -> None:
    installed = {RECRUITMENT_MODULE, "hr"}
    pe_types = _destination_types_for_mode("both", installed_modules=installed)
    destinations = _apply_tenant_link_destination_flags(
        pe_types,
        _tenant_link(internal_hr=False, client=True),
    )
    assert destinations == [DESTINATION_CLIENT]


def test_p5_resolve_handoff_mode_from_profile_stage_override() -> None:
    profile = _profile(handoff_mode="client_portal")
    assert resolve_handoff_mode_from_profile(profile, system_stage="ready_for_handoff") == "client_portal"


@pytest.mark.anyio
async def test_p5_evaluate_handoff_destinations_uses_pe_rules_and_link(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidate = SimpleNamespace(id="cand-1", company_id="co-1", own_company_id=None)
    link = _tenant_link()
    rules = [
        SimpleNamespace(
            code="handoff_both",
            handoff_mode="both",
            status="active",
            config={
                "enabled_when": {"modules_installed": [RECRUITMENT_MODULE]},
                "source": {"system_stage": "ready_for_handoff"},
            },
        )
    ]

    monkeypatch.setattr(handoff_module, "_resolve_tenant_link_for_candidate", AsyncMock(return_value=link))
    monkeypatch.setattr(handoff_module, "load_handoff_rules", AsyncMock(return_value=rules))
    monkeypatch.setattr(handoff_module, "get_installed_modules", AsyncMock(return_value={RECRUITMENT_MODULE, "hr"}))
    monkeypatch.setattr(
        handoff_module,
        "resolve_effective_process_profile_for_candidate_id",
        AsyncMock(
            return_value=SimpleNamespace(
                profile=_profile(handoff_mode="both"),
                source="tenant_default",
            )
        ),
    )

    result = await evaluate_handoff_destinations(
        db=None,  # type: ignore[arg-type]
        tenant_id="tenant-1",
        candidate=candidate,
    )

    assert isinstance(result, HandoffEvaluation)
    assert result.routing_source == "process_engine_handoff_rules"
    assert result.handoff_mode == "both"
    assert "handoff_both" in result.active_handoff_rules
    assert DESTINATION_CLIENT in result.destinations_allowed
    assert DESTINATION_INTERNAL_HR in result.destinations_allowed


@pytest.mark.anyio
async def test_p5_legacy_fallback_when_no_pe_rules(monkeypatch: pytest.MonkeyPatch) -> None:
    candidate = SimpleNamespace(id="cand-1", company_id=None, own_company_id=None)
    link = _tenant_link(client=True, internal_hr=False)

    monkeypatch.setattr(handoff_module, "_resolve_tenant_link_for_candidate", AsyncMock(return_value=link))
    monkeypatch.setattr(handoff_module, "load_handoff_rules", AsyncMock(return_value=[]))

    result = await evaluate_handoff_destinations(
        db=None,  # type: ignore[arg-type]
        tenant_id="tenant-1",
        candidate=candidate,
    )

    assert result.routing_source == "tenant_link_legacy"
    assert result.destinations_allowed == [DESTINATION_CLIENT]


@pytest.mark.anyio
async def test_p5_adapter_evaluate_handoff_exposes_destinations(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    evaluation = HandoffEvaluation(
        destinations_allowed=[DESTINATION_CLIENT],
        tenant_link=None,
        handoff_mode="client_portal",
        active_handoff_rules=["handoff_client_portal"],
    )
    monkeypatch.setattr(
        "backend.app.process_engine.handoff_evaluator.evaluate_handoff_destinations_for_candidate_id",
        AsyncMock(return_value=evaluation),
    )

    out = await TransitionEvaluatorAdapter.evaluate_handoff(
        db=None,  # type: ignore[arg-type]
        tenant_id="tenant-1",
        candidate_id="cand-1",
    )

    assert out["destinations_allowed"] == [DESTINATION_CLIENT]
    assert out["handoff_create_allowed"] is True
    assert out["handoff_mode"] == "client_portal"


def test_p5_transfer_policy_resolver_uses_handoff_evaluator() -> None:
    source = read_repo_text("backend/app/services/transfer_policy_resolver.py")
    assert "evaluate_handoff_destinations" in source
    assert "_evaluate_handoff_routing" in source
