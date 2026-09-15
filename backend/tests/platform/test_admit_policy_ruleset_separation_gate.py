"""Admit policy / ruleset separation gate.

Proves one runtime path: resolve → evaluate → aggregate for three compositions:
  [] → allowed
  PEM-1 + missing evidence → missing
  PEM-1 + satisfied evidence → allowed

Resolver is a separate authority; evaluate must not choose ruleset.
No neutral / kernel_mode / skip_requirements bypass.
"""

from __future__ import annotations

import ast
from pathlib import Path

from backend.app.reference.employment_start_allowed import (
    ADMIT_RULESET_ID_KEY,
    DECISION_MISSING,
    DECISION_START_ALLOWED,
    DECISION_UNSUPPORTED,
    EVALUATE_API,
    POLICY_ID,
    REQ_BHP,
    REQ_CONTRACT,
    REQ_MEDICAL,
    RESOLVE_API,
    RULESET_EMPTY,
    RULESET_PEM1,
    SEPARATION_REL,
    evaluate_employment_start_allowed_v1,
    resolve_admit_ruleset_v1,
)
from backend.app.services.employment_start_allowed_evidence import (
    project_bhp_evidence_view,
    project_contract_evidence_view,
    project_medical_evidence_view,
)

_REPO_ROOT = Path(__file__).resolve().parents[3]
_MODULE = _REPO_ROOT / "backend" / "app" / "reference" / "employment_start_allowed.py"
_BRIEF = _REPO_ROOT / SEPARATION_REL
_CI = _REPO_ROOT / ".github" / "workflows" / "backend-ci.yml"
_GATE = Path(__file__)


def _pem1_ctx(**extra):
    ctx = {
        "employment_country": "PL",
        "pathway_id": "pl_eu_eea_free_movement",
        "contract_type": "employment_contract",
        "employer_id": "cccccccc-cccc-cccc-cccc-cccccccccccc",
        "post_key": "driver_ce",
        "planned_start_date": "2026-10-01",
    }
    ctx.update(extra)
    return ctx


def _ok_contract():
    return project_contract_evidence_view(
        {
            "id": "doc-contract",
            "type": "employment_contract",
            "meta": {
                "signed_at": "2026-09-20",
                "employer_name": "PL Sp. z o.o.",
                "start_at": "2026-10-01",
            },
        }
    )


def _ok_medical():
    return project_medical_evidence_view(
        {
            "id": "doc-med",
            "type": "medical_certificate",
            "meta": {
                "expires_at": "2026-12-01",
                "fit_for_work": True,
                "applies_to_post": "driver_ce",
                "conditions_match": True,
            },
        }
    )


def _ok_bhp():
    return project_bhp_evidence_view(
        {
            "id": "doc-bhp",
            "type": "bhp",
            "meta": {
                "training_date": "2026-09-15",
                "training_kind": "introductory",
                "employer_id": "cccccccc-cccc-cccc-cccc-cccccccccccc",
                "post_key": "driver_ce",
            },
        }
    )


def test_admit_ruleset_separation_gate_filename() -> None:
    assert _GATE.name == "test_admit_policy_ruleset_separation_gate.py"


def test_admit_ruleset_separation_apis_and_brief() -> None:
    assert POLICY_ID == "employment_start_allowed.v1"
    assert RESOLVE_API == "resolve_admit_ruleset_v1"
    assert EVALUATE_API == "evaluate_employment_start_allowed_v1"
    text = _MODULE.read_text(encoding="utf-8")
    assert f"def {RESOLVE_API}(" in text
    assert f"def {EVALUATE_API}(" in text
    assert _BRIEF.is_file()
    brief = _BRIEF.read_text(encoding="utf-8")
    assert "resolver ≠ evaluator" in brief or "resolver != evaluator" in brief or "separate authority" in brief.lower()


def test_resolver_is_separate_authority_ast() -> None:
    """evaluate must call resolve; must not call is_pem1_context for routing."""
    tree = ast.parse(_MODULE.read_text(encoding="utf-8"))
    resolve_fn = None
    evaluate_fn = None
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            if node.name == RESOLVE_API:
                resolve_fn = node
            elif node.name == EVALUATE_API:
                evaluate_fn = node
    assert resolve_fn is not None
    assert evaluate_fn is not None

    def _calls(fn: ast.FunctionDef) -> set[str]:
        names: set[str] = set()
        for n in ast.walk(fn):
            if isinstance(n, ast.Call):
                if isinstance(n.func, ast.Name):
                    names.add(n.func.id)
                elif isinstance(n.func, ast.Attribute):
                    names.add(n.func.attr)
        return names

    resolve_calls = _calls(resolve_fn)
    evaluate_calls = _calls(evaluate_fn)
    assert "is_pem1_context" in resolve_calls
    assert RESOLVE_API in evaluate_calls or "resolve_admit_ruleset_v1" in evaluate_calls
    assert "is_pem1_context" not in evaluate_calls


def test_composition_empty_ruleset_allowed() -> None:
    ctx = _pem1_ctx(**{ADMIT_RULESET_ID_KEY: RULESET_EMPTY})
    resolved = resolve_admit_ruleset_v1(ctx)
    assert resolved["resolved"] is True
    assert resolved["ruleset_id"] == RULESET_EMPTY
    assert resolved["rules"] == []

    r = evaluate_employment_start_allowed_v1(employee_id="e1", employment_context=ctx)
    assert r["decision"] == DECISION_START_ALLOWED
    assert r["start_allowed"] is True
    assert r["ruleset_id"] == RULESET_EMPTY
    assert r["required_actions"] == []
    assert r["active_missing"] == []
    assert r["started"] is False


def test_composition_pem1_missing_evidence() -> None:
    ctx = _pem1_ctx()
    resolved = resolve_admit_ruleset_v1(ctx)
    assert resolved["resolved"] is True
    assert resolved["ruleset_id"] == RULESET_PEM1
    assert {row["code"] for row in resolved["rules"]} == {REQ_CONTRACT, REQ_MEDICAL, REQ_BHP}

    r = evaluate_employment_start_allowed_v1(employee_id="e1", employment_context=ctx)
    assert r["decision"] == DECISION_MISSING
    assert r["start_allowed"] is False
    assert r["ruleset_id"] == RULESET_PEM1
    assert r["primary_item"]["code"] == REQ_CONTRACT
    assert {a["code"] for a in r["required_actions"]} == {REQ_CONTRACT, REQ_MEDICAL, REQ_BHP}


def test_composition_pem1_satisfied_allowed() -> None:
    ctx = _pem1_ctx()
    r = evaluate_employment_start_allowed_v1(
        employee_id="e1",
        employment_context=ctx,
        contract_view=_ok_contract(),
        medical_view=_ok_medical(),
        bhp_view=_ok_bhp(),
    )
    assert r["decision"] == DECISION_START_ALLOWED
    assert r["start_allowed"] is True
    assert r["ruleset_id"] == RULESET_PEM1
    assert r["context_policy"] == "PEM-1"


def test_three_compositions_same_evaluate_api() -> None:
    """Machine proof: one evaluate entrypoint, three compositions."""
    empty = evaluate_employment_start_allowed_v1(
        employee_id="e1",
        employment_context=_pem1_ctx(**{ADMIT_RULESET_ID_KEY: RULESET_EMPTY}),
    )
    missing = evaluate_employment_start_allowed_v1(
        employee_id="e1",
        employment_context=_pem1_ctx(),
    )
    allowed = evaluate_employment_start_allowed_v1(
        employee_id="e1",
        employment_context=_pem1_ctx(),
        contract_view=_ok_contract(),
        medical_view=_ok_medical(),
        bhp_view=_ok_bhp(),
    )
    assert empty["policy_id"] == missing["policy_id"] == allowed["policy_id"] == POLICY_ID
    assert empty["start_allowed"] is True
    assert missing["decision"] == DECISION_MISSING
    assert allowed["start_allowed"] is True
    assert empty["ruleset_id"] == RULESET_EMPTY
    assert missing["ruleset_id"] == allowed["ruleset_id"] == RULESET_PEM1


def test_resolve_failure_unsupported_not_empty() -> None:
    r = evaluate_employment_start_allowed_v1(
        employee_id="e1",
        employment_context=_pem1_ctx(pathway_id="pl_third_country_work_authorization"),
    )
    assert r["decision"] == DECISION_UNSUPPORTED
    assert r["start_allowed"] is False
    assert r["ruleset_id"] is None


def test_no_bypass_flags_in_module() -> None:
    text = _MODULE.read_text(encoding="utf-8")
    assert "kernel_mode" not in text
    assert "skip_requirements" not in text
    assert "neutral=true" not in text
    assert "def _neutral" not in text
    # Override keys may appear only inside rejected-patch handling, never as evaluate short-circuits.
    assert "if patch.get(\"allow_anyway\")" in text or 'patch.get("allow_anyway")' in text


def test_admit_ruleset_separation_ci_job_wired() -> None:
    ci = _CI.read_text(encoding="utf-8")
    assert "admit-policy-ruleset-separation-gate" in ci
    assert "test_admit_policy_ruleset_separation_gate.py" in ci
