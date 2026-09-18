"""Dual zero-policy preflight gate (ADR-042 §3c) — retry after public-contract PASS.

Consumer-level proof only (does not re-prove Ready composition internals):

  P1 Recruitment: ready_composition_id=empty → recruitment.public.ready → allowed
  P4 Employment:  admit_ruleset_id=empty → employment.public.commands → start_allowed

Minimal fixtures. No document/confirmation/ops stuffing. No kernel/test bypass flags.
Does not mint candidates, open Kernel walk, or PEM-1.
"""

from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from backend.app.modules.employment.public import commands as employment_public
from backend.app.modules.recruitment.public import ready as recruitment_public

_REPO_ROOT = Path(__file__).resolve().parents[3]
_BRIEF = _REPO_ROOT / "docs" / "specs" / "tasks" / "dual-zero-policy-preflight.md"
_ADMIT_MOD = _REPO_ROOT / "backend" / "app" / "reference" / "employment_start_allowed.py"
_READY_POLICY = _REPO_ROOT / "backend" / "app" / "reference" / "recruitment_ready_policy.py"
_CI = _REPO_ROOT / ".github" / "workflows" / "backend-ci.yml"
_GATE = Path(__file__)

# Stable public context vocabulary (not capability lists / not reference imports for evaluate).
_READY_EMPTY_CTX = {recruitment_public.READY_COMPOSITION_ID_KEY: recruitment_public.COMPOSITION_EMPTY}
_ADMIT_EMPTY_CTX = {
    "employment_country": "PL",
    "pathway_id": "pl_eu_eea_free_movement",
    "contract_type": "employment_contract",
    "admit_ruleset_id": "empty",
}


def test_dual_zero_preflight_gate_filename() -> None:
    assert _GATE.name == "test_dual_zero_policy_preflight_gate.py"


def test_dual_zero_preflight_brief_pass() -> None:
    assert _BRIEF.is_file()
    text = _BRIEF.read_text(encoding="utf-8")
    assert "**Status:** **PASS**" in text or "Status:** **PASS**" in text
    assert "P1" in text and "P4" in text
    assert "recruitment.public" in text.lower() or "recruitment.public.ready" in text
    assert "employment.public" in text.lower()
    # Dual PASS does not open Kernel / PEM-1 by itself.
    assert "P1→P6" in text or "P1->P6" in text or "Baseline Kernel" in text


def test_no_bypass_flags_on_ready_and_admit_policy() -> None:
    text = _READY_POLICY.read_text(encoding="utf-8") + _ADMIT_MOD.read_text(encoding="utf-8")
    assert "if kernel_mode" not in text
    assert "kernel_mode =" not in text
    assert "neutral=true" not in text
    assert "neutral = True" not in text
    # skip_requirements must not appear as an executable switch
    assert "skip_requirements" not in text.replace(
        "not a kernel_mode / skip_requirements bypass.", ""
    ).replace("skip_requirements bypass", "")


def _minimal_candidate() -> SimpleNamespace:
    return SimpleNamespace(
        id="cand-dual-p1",
        tenant_id="tenant-1",
        deleted_at=None,
        stage="new",
        company_id=None,
        own_company_id=None,
        vacancy_id=None,
        phone=None,
        email=None,
        _get_extra=lambda: {},
        _get_personal_data=lambda: {},
    )


def _db_for(cand: SimpleNamespace) -> SimpleNamespace:
    class _Result:
        def scalar_one_or_none(self):
            return cand

    return SimpleNamespace(execute=AsyncMock(return_value=_Result()))


@pytest.mark.anyio
async def test_p1_empty_ready_via_recruitment_public(monkeypatch: pytest.MonkeyPatch) -> None:
    """P1: [] → allowed / transfer_allowed via recruitment.public.ready (minimal)."""
    cand = _minimal_candidate()
    db = _db_for(cand)

    async def _boom(*_a, **_k):
        raise AssertionError("policy evaluator invoked under empty Ready composition")

    monkeypatch.setattr(
        "backend.app.api.v1.candidates.pipeline_overrides_service.approved_handoff_relaxed_types",
        AsyncMock(return_value=set()),
    )
    monkeypatch.setattr(
        "backend.app.services.transfer_policy_resolver._resolve_destinations_for_candidate",
        AsyncMock(
            return_value=(
                ["internal_hr"],
                SimpleNamespace(
                    get_handoff_enabled=lambda: True,
                    get_handoff_to_client=lambda: False,
                    get_handoff_to_internal_hr=lambda: True,
                    get_workforce_handoff_on_ready_for_handoff_stage=lambda: False,
                ),
                {},
            )
        ),
    )
    monkeypatch.setattr(
        "backend.app.services.transfer_policy_resolver.resolve_hiring_pipeline_gates",
        AsyncMock(
            return_value=SimpleNamespace(
                stages_without_doc_pipeline_block=frozenset(),
                stages_verify_uploads_block_forward=frozenset(),
                stages_require_vacancy_for_forward=frozenset(),
            )
        ),
    )
    # Empty must not invoke Ready policy capabilities (no stuffing path).
    monkeypatch.setattr(
        "backend.app.services.transfer_policy_resolver.resolve_workforce_eligibility_via_contract",
        _boom,
    )
    monkeypatch.setattr(
        "backend.app.services.recruitment_package_readiness.evaluate_recruitment_package",
        _boom,
    )
    monkeypatch.setattr(
        "backend.app.field_registry.requirement_evaluator.evaluate_field_requirements_for_candidate",
        _boom,
    )
    monkeypatch.setattr(
        "backend.app.services.operational_requirements_service.evaluate_operational_requirements_for_candidate",
        _boom,
    )

    report = await recruitment_public.evaluate_ready_transfer(
        db,
        tenant_id="tenant-1",
        candidate_id=str(cand.id),
        ready_context=_READY_EMPTY_CTX,
    )
    assert report["decision"] == recruitment_public.DECISION_ALLOWED
    assert report["transfer_allowed"] is True
    assert report["composition_id"] == recruitment_public.COMPOSITION_EMPTY


@pytest.mark.anyio
async def test_p4_empty_admit_via_employment_public(monkeypatch: pytest.MonkeyPatch) -> None:
    """P4: empty Admit → start_allowed via employment.public.commands (minimal identity)."""
    import backend.app.services.employment_start_allowed_orchestrator as orch

    handoff = SimpleNamespace(
        id="ho-dual-p4",
        agency_tenant_id="tenant-1",
        client_tenant_id="tenant-2",
        candidate_id="cand-dual-p4",
    )
    employee = SimpleNamespace(
        id="e-dual-p4",
        candidate_id="cand-dual-p4",
        company_id=None,
        own_company_id=None,
        hire_date=None,
        meta={},
    )

    async def _get(_model, id_):
        return handoff if str(id_) == "ho-dual-p4" else None

    db = SimpleNamespace(get=AsyncMock(side_effect=_get))

    async def _resolve_employee(_db, *, tenant_id, handoff):  # noqa: ARG001
        return employee

    async def _load_evidence(_db, *, tenant_id, candidate_id):  # noqa: ARG001
        # No contract/medical/bhp stuffing — empty ruleset must allow without evidence.
        return None, None, None

    async def _exceptions(_db, *, tenant_id, employee_id):  # noqa: ARG001
        return []

    monkeypatch.setattr(orch, "resolve_employee_for_handoff", _resolve_employee)
    monkeypatch.setattr(orch, "_load_evidence_views", _load_evidence)
    monkeypatch.setattr(orch, "list_active_exceptions", _exceptions)

    result = await employment_public.evaluate_start_allowed_for_handoff(
        db,
        tenant_id="tenant-1",
        handoff_id="ho-dual-p4",
        employment_context=_ADMIT_EMPTY_CTX,
    )
    assert result["decision"] == "start_allowed"
    assert result["start_allowed"] is True
    assert result["ruleset_id"] == "empty"
    assert result.get("required_actions") == []
    assert result.get("started") is False


def test_p4_admit_evaluate_calls_resolve_ast() -> None:
    """Production Admit evaluate still goes through resolve (not a second path)."""
    tree = ast.parse(_ADMIT_MOD.read_text(encoding="utf-8"))
    evaluate_fn = next(
        n
        for n in tree.body
        if isinstance(n, ast.FunctionDef) and n.name == "evaluate_employment_start_allowed_v1"
    )
    calls: set[str] = set()
    for n in ast.walk(evaluate_fn):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name):
            calls.add(n.func.id)
    assert "resolve_admit_ruleset_v1" in calls


def test_dual_both_points_pass_outcome() -> None:
    """Both consumer proofs green → dual PASS (brief). Kernel not auto-opened."""
    brief = _BRIEF.read_text(encoding="utf-8")
    assert "**Status:** **PASS**" in brief or "Status:** **PASS**" in brief
    assert "P1" in brief and "**PASS**" in brief
    assert "P4" in brief
    lower = brief.lower()
    assert "not opened" in lower or "do not open" in lower or "may open" in lower


def test_ci_wires_dual_zero_gate() -> None:
    text = _CI.read_text(encoding="utf-8")
    assert "dual-zero-policy-preflight-gate" in text
    assert "test_dual_zero_policy_preflight_gate.py" in text


def test_dual_preflight_no_candidate_mint_in_gate() -> None:
    tree = ast.parse(_GATE.read_text(encoding="utf-8"))
    call_names: set[str] = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Call):
            if isinstance(n.func, ast.Name):
                call_names.add(n.func.id)
            elif isinstance(n.func, ast.Attribute):
                call_names.add(n.func.attr)
    assert "create_candidate" not in call_names
    assert "handoff_from_candidate" not in call_names


def test_cold_import_public_surfaces_for_dual() -> None:
    probe = (
        "import importlib\n"
        "r = importlib.import_module('backend.app.modules.recruitment.public.ready')\n"
        "e = importlib.import_module('backend.app.modules.employment.public.commands')\n"
        "assert 'evaluate_ready_transfer' in r.__all__\n"
        "assert 'evaluate_start_allowed_for_handoff' in e.__all__\n"
        "raise SystemExit(0)\n"
    )
    proc = subprocess.run(
        [sys.executable, "-c", probe],
        cwd=str(_REPO_ROOT),
        env={
            **dict(**{k: v for k, v in __import__("os").environ.items()}),
            "PYTHONPATH": f"{_REPO_ROOT}:{_REPO_ROOT / 'backend'}",
        },
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
