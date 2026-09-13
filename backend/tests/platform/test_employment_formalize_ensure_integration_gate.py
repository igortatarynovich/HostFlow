"""ESO-4 Formalize → ESA2 ensure integration parity gate.

Proves real Formalize orchestrator wiring:
- authoritative apply + ready → ensure mints linked Employee
- evaluate/read + ready → no write / no mint
- handoff linkage (meta.internal_hr_handoff_id) preserved

Not slice 3. Not Full Spine. Not ESO-5 enforcement.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from backend.app.services.employment_formalize_orchestrator import (
    formalize_employment_for_handoff,
    formalize_request_is_authoritative_apply,
)

_REPO_ROOT = Path(__file__).resolve().parents[3]
_ORCH = _REPO_ROOT / "backend" / "app" / "services" / "employment_formalize_orchestrator.py"
_API = _REPO_ROOT / "backend" / "app" / "api" / "v1" / "handoffs.py"
_ENSURE = _REPO_ROOT / "backend" / "app" / "services" / "employment_formalize_employee_ensure.py"
_CI = _REPO_ROOT / ".github" / "workflows" / "backend-ci.yml"
_BRIEF = _REPO_ROOT / "docs" / "specs" / "tasks" / "employment-start-allowed-mint-cutover.md"


def test_integration_parity_gate_filename() -> None:
    assert Path(__file__).name == "test_employment_formalize_ensure_integration_gate.py"


def test_formalize_orchestrator_calls_ensure_seam() -> None:
    orch = _ORCH.read_text(encoding="utf-8")
    assert "ensure_employee_after_formalize_apply" in orch
    assert "formalize_request_is_authoritative_apply" in orch
    assert "create_employee(" not in orch
    api = _API.read_text(encoding="utf-8")
    assert "employment-formalize" in api
    assert "authoritative_apply" in api
    assert "ensure_employee_after_formalize_apply" in _ENSURE.read_text(encoding="utf-8")
    ci = _CI.read_text(encoding="utf-8")
    assert "test_employment_formalize_ensure_integration_gate.py" in ci
    assert "integration parity" in _BRIEF.read_text(encoding="utf-8").lower()


def test_authoritative_apply_detection() -> None:
    assert not formalize_request_is_authoritative_apply()
    assert not formalize_request_is_authoritative_apply(formalize_patch={}, confirmed_actions=[])
    assert formalize_request_is_authoritative_apply(
        confirmed_actions=["confirm_employment_contract_basis"]
    )
    assert formalize_request_is_authoritative_apply(
        formalize_patch={"confirm_employment_contract_basis": True}
    )


@pytest.mark.anyio
async def test_evaluate_ready_does_not_write_via_orchestrator() -> None:
    handoff = SimpleNamespace(
        id="h1",
        candidate_id="c1",
        agency_tenant_id="t1",
        client_tenant_id="t1",
        status="accepted",
    )
    db = AsyncMock()
    db.get = AsyncMock(return_value=handoff)

    formalize_result = {
        "decision": "formalization_complete",
        "ready_to_create_employee": True,
        "employee_created": False,
        "confirmed_actions": ["confirm_employment_contract_basis"],
    }
    ensure_result = SimpleNamespace(
        employee_id=None,
        employee_created=False,
        wrote=False,
        skipped_reason="evaluate_or_read",
        linked_handoff_id=None,
    )

    with (
        patch(
            "backend.app.services.employment_formalize_orchestrator.resolve_ready_for_employment_package",
            new=AsyncMock(return_value={"contract_id": "ready_for_employment.v1"}),
        ),
        patch(
            "backend.app.services.employment_formalize_orchestrator.apply_employment_formalize_v1",
            return_value=formalize_result,
        ),
        patch(
            "backend.app.services.employment_formalize_orchestrator.ensure_employee_after_formalize_apply",
            new=AsyncMock(return_value=ensure_result),
        ) as ensure,
    ):
        out = await formalize_employment_for_handoff(
            db,
            tenant_id="t1",
            handoff_id="h1",
            # empty evaluate/read — no patch / confirmed write intent
            authoritative_apply=False,
        )

    ensure.assert_awaited_once()
    kwargs = ensure.await_args.kwargs
    assert kwargs["authoritative_apply"] is False
    assert kwargs["ready_to_create_employee"] is True
    assert out["employee_ensure_wrote"] is False
    assert out["employee_id"] is None
    assert out["authoritative_apply"] is False


@pytest.mark.anyio
async def test_apply_ready_mints_linked_employee_via_orchestrator() -> None:
    handoff = SimpleNamespace(
        id="h-apply",
        candidate_id="c1",
        agency_tenant_id="t1",
        client_tenant_id="t1",
        status="accepted",
    )
    db = AsyncMock()
    db.get = AsyncMock(return_value=handoff)

    formalize_result = {
        "decision": "formalization_complete",
        "ready_to_create_employee": True,
        "confirmed_actions": ["confirm_employment_contract_basis"],
    }
    ensure_result = SimpleNamespace(
        employee_id="e-linked",
        employee_created=True,
        wrote=True,
        skipped_reason=None,
        linked_handoff_id="h-apply",
    )

    with (
        patch(
            "backend.app.services.employment_formalize_orchestrator.resolve_ready_for_employment_package",
            new=AsyncMock(return_value={"contract_id": "ready_for_employment.v1"}),
        ),
        patch(
            "backend.app.services.employment_formalize_orchestrator.apply_employment_formalize_v1",
            return_value=formalize_result,
        ),
        patch(
            "backend.app.services.employment_formalize_orchestrator.ensure_employee_after_formalize_apply",
            new=AsyncMock(return_value=ensure_result),
        ) as ensure,
    ):
        out = await formalize_employment_for_handoff(
            db,
            tenant_id="t1",
            handoff_id="h-apply",
            confirmed_actions=["confirm_employment_contract_basis"],
            actor_user_id="u1",
        )

    ensure.assert_awaited_once()
    kwargs = ensure.await_args.kwargs
    assert kwargs["authoritative_apply"] is True
    assert kwargs["ready_to_create_employee"] is True
    assert kwargs["handoff_id"] == "h-apply"
    assert out["employee_id"] == "e-linked"
    assert out["employee_created"] is True
    assert out["employee_ensure_wrote"] is True
    assert out["employee_linked_handoff_id"] == "h-apply"
    assert out["authoritative_apply"] is True


@pytest.mark.anyio
async def test_repeat_apply_preserves_same_linked_employee() -> None:
    handoff = SimpleNamespace(
        id="h1",
        candidate_id="c1",
        agency_tenant_id="t1",
        client_tenant_id="t1",
        status="accepted",
    )
    db = AsyncMock()
    db.get = AsyncMock(return_value=handoff)
    formalize_result = {"ready_to_create_employee": True, "decision": "formalization_complete"}
    ensure_result = SimpleNamespace(
        employee_id="e1",
        employee_created=False,
        wrote=True,
        skipped_reason=None,
        linked_handoff_id="h1",
    )

    with (
        patch(
            "backend.app.services.employment_formalize_orchestrator.resolve_ready_for_employment_package",
            new=AsyncMock(return_value={}),
        ),
        patch(
            "backend.app.services.employment_formalize_orchestrator.apply_employment_formalize_v1",
            return_value=formalize_result,
        ),
        patch(
            "backend.app.services.employment_formalize_orchestrator.ensure_employee_after_formalize_apply",
            new=AsyncMock(return_value=ensure_result),
        ),
    ):
        first = await formalize_employment_for_handoff(
            db,
            tenant_id="t1",
            handoff_id="h1",
            formalize_patch={"confirm_employment_contract_basis": True},
        )
        second = await formalize_employment_for_handoff(
            db,
            tenant_id="t1",
            handoff_id="h1",
            formalize_patch={"confirm_employment_contract_basis": True},
        )

    assert first["employee_id"] == second["employee_id"] == "e1"
    assert first["employee_linked_handoff_id"] == second["employee_linked_handoff_id"] == "h1"
