"""Dual zero-policy preflight gate (ADR-042 §3c).

P4 Admit: empty ruleset via production resolver → allowed (must PASS).
P1 Ready: full surface zero-composition → transfer_allowed (witness STOP if not).

Does not mint candidates, upload evidence, forge verdicts, or open Kernel walk.
"""

from __future__ import annotations

import ast
from pathlib import Path

from backend.app.reference.employment_start_allowed import (
    ADMIT_RULESET_ID_KEY,
    DECISION_START_ALLOWED,
    DECISION_UNSUPPORTED,
    RULESET_EMPTY,
    evaluate_employment_start_allowed_v1,
    resolve_admit_ruleset_v1,
)
from backend.app.reference.requirement_policy_consumer_parity import (
    preview_context,
    r5_required_set,
)

_REPO_ROOT = Path(__file__).resolve().parents[3]
_BRIEF = _REPO_ROOT / "docs" / "specs" / "tasks" / "dual-zero-policy-preflight.md"
_ADMIT_MOD = _REPO_ROOT / "backend" / "app" / "reference" / "employment_start_allowed.py"
_TRANSFER = _REPO_ROOT / "backend" / "app" / "services" / "transfer_policy_resolver.py"
_PACKAGE = _REPO_ROOT / "backend" / "app" / "services" / "recruitment_package_readiness.py"
_SLOTS = _REPO_ROOT / "backend" / "app" / "services" / "hr_verification_plan.py"
_CI = _REPO_ROOT / ".github" / "workflows" / "backend-ci.yml"
_GATE = Path(__file__)

# Full remove covering pack defaults + residency / vacancy requires that can appear.
_R5_FULL_REMOVE = [
    "driver_license",
    "driver_qualification_card",
    "tachograph_card",
    "passport",
    "national_identity_card",
    "visa",
    "residence_card",
    "work_permit",
    "driver_attestation",
]

# Layers that participate in Ready but are NOT emptied by R5∅ alone.
_P1_NON_COMPOSITION_LAYERS = (
    "recruitment_package",
    "recruiter_confirmation",
    "field_requirements",
    "requirement_engine",
    "operational_requirements",
)


def _r5_empty_delta() -> dict:
    return {"candidate": {"overrides": [{"when": {}, "remove": list(_R5_FULL_REMOVE)}]}}


def test_dual_zero_preflight_gate_filename() -> None:
    assert _GATE.name == "test_dual_zero_policy_preflight_gate.py"


def test_dual_zero_preflight_brief_exists() -> None:
    assert _BRIEF.is_file()
    text = _BRIEF.read_text(encoding="utf-8")
    assert "dual zero-policy" in text.lower() or "Dual zero-policy" in text
    assert "STOP" in text
    assert "Kernel" in text


# ----- P4 Admit (must be green) -----


def test_p4_admit_resolver_selects_empty_composition() -> None:
    ctx = {
        "employment_country": "PL",
        "pathway_id": "pl_eu_eea_free_movement",
        "contract_type": "employment_contract",
        ADMIT_RULESET_ID_KEY: RULESET_EMPTY,
    }
    resolution = resolve_admit_ruleset_v1(ctx)
    assert resolution["resolved"] is True
    assert resolution["ruleset_id"] == RULESET_EMPTY
    assert resolution["rules"] == []


def test_p4_admit_empty_pipeline_allowed() -> None:
    ctx = {
        "employment_country": "PL",
        "pathway_id": "pl_eu_eea_free_movement",
        "contract_type": "employment_contract",
        "employer_id": "cccccccc-cccc-cccc-cccc-cccccccccccc",
        "post_key": "warehouse",
        ADMIT_RULESET_ID_KEY: RULESET_EMPTY,
    }
    result = evaluate_employment_start_allowed_v1(employee_id="e-preflight", employment_context=ctx)
    assert result["decision"] == DECISION_START_ALLOWED
    assert result["start_allowed"] is True
    assert result["ruleset_id"] == RULESET_EMPTY
    assert result["required_actions"] == []
    assert result["started"] is False


def test_p4_admit_empty_uses_resolve_not_bypass_ast() -> None:
    tree = ast.parse(_ADMIT_MOD.read_text(encoding="utf-8"))
    evaluate_fn = next(
        n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "evaluate_employment_start_allowed_v1"
    )
    calls: set[str] = set()
    for n in ast.walk(evaluate_fn):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name):
            calls.add(n.func.id)
    assert "resolve_admit_ruleset_v1" in calls
    text = _ADMIT_MOD.read_text(encoding="utf-8")
    assert "kernel_mode" not in text
    assert "skip_requirements" not in text
    assert "neutral=true" not in text


def test_p4_admit_resolve_failure_not_confused_with_empty() -> None:
    r = evaluate_employment_start_allowed_v1(
        employee_id="e-preflight",
        employment_context={
            "employment_country": "PL",
            "pathway_id": "pl_third_country_work_authorization",
            "contract_type": "employment_contract",
        },
    )
    assert r["decision"] == DECISION_UNSUPPORTED
    assert r["start_allowed"] is False


# ----- P1 Ready (witness composition gap) -----


def test_p1_r5_empty_expressible_via_overlay() -> None:
    required = r5_required_set(preview_context(), _r5_empty_delta())
    assert required == frozenset()


def test_p1_r5_empty_is_not_full_ready_corollary() -> None:
    """Inventory lock: r5=∅ alone ≠ neutral Recruitment Ready."""
    brief = _BRIEF.read_text(encoding="utf-8")
    assert "r5_required_set" in brief or "R5" in brief
    assert "not sufficient" in brief.lower() or "≠" in brief or "False" in brief


def test_p1_no_ready_empty_composition_selector() -> None:
    transfer = _TRANSFER.read_text(encoding="utf-8")
    assert "admit_ruleset_id" not in transfer
    assert "ruleset_id=empty" not in transfer
    assert "zero_requirement" not in transfer
    assert "kernel_mode" not in transfer
    assert "skip_requirements" not in transfer
    # No Ready-side empty composition API analogous to Admit resolver.
    assert "resolve_admit_ruleset" not in transfer
    assert "resolve_ready_ruleset" not in transfer
    assert "empty_ruleset" not in transfer


def test_p1_transfer_allowed_formula_includes_non_r5_layers() -> None:
    transfer = _TRANSFER.read_text(encoding="utf-8")
    assert "transfer_allowed =" in transfer or "transfer_allowed=" in transfer
    for layer in _P1_NON_COMPOSITION_LAYERS:
        assert layer in transfer, f"expected source_layer {layer} in TransferPolicyResolver"
    # Formula conjuncts beyond docs_ready / R5
    assert "required_confirmations" in transfer
    assert "ops_ready" in transfer
    assert "pkg.get(\"ready\")" in transfer or "package_ready" in transfer


def test_p1_recruitment_package_hardwires_dossier_topology() -> None:
    package = _PACKAGE.read_text(encoding="utf-8")
    slots = _SLOTS.read_text(encoding="utf-8")
    assert "VERIFICATION_SLOT_DEFS" in package
    assert "VERIFICATION_SLOT_DEFS" in slots
    assert "_HANDOFF_REQUIRED_DATA_BLOCKS" in package
    assert "Contacts & address" in package
    # Hardwired slots are not driven by R5 overlay membership.
    assert "r5_required_set" not in package


def test_p1_layer_classification_recorded_in_brief() -> None:
    brief = _BRIEF.read_text(encoding="utf-8")
    assert "policy → topology leak" in brief or "policy→topology" in brief
    for layer in ("recruitment_package", "recruiter_confirmation", "field_requirements", "operational_requirements"):
        assert layer in brief


# ----- Dual outcome + negatives -----


def test_dual_preflight_outcome_is_stop_until_ready_composable() -> None:
    """Both must be allowed for PASS. Admit is; Ready is not → STOP."""
    admit_ok = True  # proved by test_p4_admit_empty_pipeline_allowed
    ready_full_zero_expressible = False  # proved by absence of Ready empty selector
    r5_empty_ok = r5_required_set(preview_context(), _r5_empty_delta()) == frozenset()
    assert admit_ok is True
    assert r5_empty_ok is True
    assert ready_full_zero_expressible is False
    dual_pass = admit_ok and ready_full_zero_expressible
    assert dual_pass is False
    brief = _BRIEF.read_text(encoding="utf-8")
    assert "**STOP**" in brief
    assert "NOT opened" in brief or "not opened" in brief.lower() or "Do not** open Kernel" in brief


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
    assert "evaluate_transition" not in call_names  # no live Ready evaluate with stuffed person
    # Gate is structural/classification only — no DB session parameter on any test fn.
    for n in tree.body:
        if isinstance(n, ast.FunctionDef) and n.name.startswith("test_"):
            arg_names = {a.arg for a in n.args.args}
            assert "db" not in arg_names


def test_dual_preflight_ci_job_wired() -> None:
    ci = _CI.read_text(encoding="utf-8")
    assert "dual-zero-policy-preflight-gate" in ci
    assert "test_dual_zero_policy_preflight_gate.py" in ci
