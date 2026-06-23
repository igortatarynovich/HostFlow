"""Process Engine P2 — evaluator facade wiring and import guard."""

from __future__ import annotations

import inspect
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from backend.app.process_engine.constants import RECRUITMENT_MODULE
from backend.app.process_engine.evaluator_adapter import TransitionEvaluatorAdapter

_BACKEND_ROOT = Path(__file__).resolve().parents[2] / "app"

# API/service layers must route through TransitionEvaluatorAdapter (P2).
_FACADE_GUARD_PATHS = (
    _BACKEND_ROOT / "api" / "v1" / "candidates" / "service.py",
    _BACKEND_ROOT / "api" / "v1" / "candidates" / "router.py",
    _BACKEND_ROOT / "services" / "recruitment_package_readiness.py",
)


def test_p2_api_service_layer_does_not_import_transfer_policy_resolver_directly() -> None:
    for path in _FACADE_GUARD_PATHS:
        source = path.read_text(encoding="utf-8")
        assert "TransferPolicyResolver" not in source, (
            f"{path.relative_to(_BACKEND_ROOT.parent)} must use TransitionEvaluatorAdapter, "
            "not TransferPolicyResolver"
        )
        assert "TransitionEvaluatorAdapter" in source, (
            f"{path.relative_to(_BACKEND_ROOT.parent)} must call TransitionEvaluatorAdapter"
        )


def test_p2_evaluator_adapter_is_only_runtime_caller_of_resolver() -> None:
    adapter_source = inspect.getsource(TransitionEvaluatorAdapter)
    assert "TransferPolicyResolver" in adapter_source
    assert "Compatibility" in adapter_source


@pytest.mark.anyio
async def test_p2_assert_transition_allowed_preserves_require_destination_semantics(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, bool] = {}

    async def _resolve(db, *, tenant_id, candidate_id, target_stage=None, require_destination=False):
        captured["require_destination"] = require_destination
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
        target_system_stage="ready_for_handoff",
        require_destination=True,
    )
    assert captured["require_destination"] is True
