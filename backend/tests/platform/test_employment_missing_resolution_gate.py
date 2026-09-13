"""Employment Missing / Resolution Gate (ESO-3).

Minimal active path + auto re-eval + no Employee + no universal checklist.
Not Formalize. Not Recruitment Transfer calling resolution.
"""

from __future__ import annotations

import ast
from pathlib import Path

from backend.app.reference.early_employability import (
    DECISION_EMPLOYABLE,
    DECISION_INSUFFICIENT_FACTS,
    PATHWAY_PL_THIRD_COUNTRY,
    evaluate_early_employability_v1,
)
from backend.app.reference.employment_missing_resolution import (
    ARCH_REL,
    EMPLOYABILITY_ARCH_REL,
    ESO_BRIEF_REL,
    FORBIDDEN_UNIVERSAL_CHECKLIST_CODES,
    PLAN_API,
    POLICY_ID,
    RESOLUTION_AWAITING,
    RESOLUTION_DECISIONS,
    RESOLUTION_READY,
    RESOLUTION_REJECTED_PATCH,
    RESOLUTION_STILL_BLOCKED,
    apply_employment_resolution_v1,
    plan_employment_resolution_v1,
)
from backend.app.reference.ready_for_employment import CONTRACT_ID

_REPO_ROOT = Path(__file__).resolve().parents[3]
_ARCH = _REPO_ROOT / ARCH_REL
_ESO = _REPO_ROOT / ESO_BRIEF_REL
_EE = _REPO_ROOT / EMPLOYABILITY_ARCH_REL
_CI = _REPO_ROOT / ".github" / "workflows" / "backend-ci.yml"
_MODULE = _REPO_ROOT / "backend" / "app" / "reference" / "employment_missing_resolution.py"
_ORCH = _REPO_ROOT / "backend" / "app" / "services" / "employment_missing_resolution_orchestrator.py"
_HANDOFFS_API = _REPO_ROOT / "backend" / "app" / "api" / "v1" / "handoffs.py"
_RSO_ORCH = (
    _REPO_ROOT
    / "backend"
    / "app"
    / "modules"
    / "recruitment"
    / "services"
    / "ready_for_employment_orchestrator.py"
)


def _minimal_valid_package(*, citizenship: str | None = "UA", evidence: dict | None = None) -> dict:
    identity: dict = {"first_name": "Ada"}
    if citizenship:
        identity["citizenship"] = citizenship
    return {
        "contract_id": CONTRACT_ID,
        "tenant_id": "11111111-1111-1111-1111-111111111111",
        "person": {
            "person_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            "identity_facts": identity,
        },
        "target_work": {
            "vacancy_id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
            "employer_id": "cccccccc-cccc-cccc-cccc-cccccccccccc",
            "employment_country": "PL",
        },
        "recruitment_facts": {"language_ok": True},
        "evidence": evidence if evidence is not None else {"source": "meta_lead", "document_ids": []},
        "fits_decision": {
            "decision": "fits",
            "decided_at": "2026-09-09T10:00:00+00:00",
            "actor_id": "dddddddd-dddd-dddd-dddd-dddddddddddd",
        },
        "context_refs": {
            "application_id": "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee",
        },
    }


def test_eso3_gate_filename() -> None:
    assert Path(__file__).name == "test_employment_missing_resolution_gate.py"


def test_eso3_policy_id_and_apis() -> None:
    assert POLICY_ID == "employment_missing_resolution.v1"
    assert PLAN_API == "plan_employment_resolution_v1"
    assert "def apply_employment_resolution_v1(" in _MODULE.read_text(encoding="utf-8")
    assert RESOLUTION_DECISIONS == (
        RESOLUTION_READY,
        RESOLUTION_AWAITING,
        RESOLUTION_STILL_BLOCKED,
        RESOLUTION_REJECTED_PATCH,
    )
    assert "full_legalization_checklist" in FORBIDDEN_UNIVERSAL_CHECKLIST_CODES


def test_eso3_plan_surfaces_only_current_gap_not_universal_checklist() -> None:
    emp = evaluate_early_employability_v1(
        package=_minimal_valid_package(citizenship="UA"),
        handoff_status="accepted",
        employment_context={"employment_country": "PL"},
    )
    plan = plan_employment_resolution_v1(emp)
    assert plan["resolution_decision"] == RESOLUTION_AWAITING
    assert plan["universal_checklist_forbidden"] is True
    assert plan["employee_created"] is False
    codes = {i["code"] for i in plan["active_items"]}
    assert "work_authorization_evidence" in codes
    assert "full_legalization_checklist" not in codes
    assert "zezwolenie" not in codes or "work_authorization_evidence" in codes
    # Must not dump a long static shopping list.
    assert len(plan["active_items"]) <= 3
    assert plan["primary_item"]["code"] == "provide_work_authorization_evidence"


def test_eso3_patch_evidence_auto_reeval_ready_to_formalize() -> None:
    out = apply_employment_resolution_v1(
        package=_minimal_valid_package(citizenship="UA"),
        handoff_status="accepted",
        employment_context={"employment_country": "PL"},
        resolution_patch={"evidence": {"work_permit_document_id": "doc-9"}},
    )
    assert out["resolution_decision"] == RESOLUTION_READY
    assert out["package_merged"] is True
    assert out["employee_created"] is False
    assert out["employability"]["decision"] == DECISION_EMPLOYABLE
    assert out["employability"]["legal_pathway"]["pathway_id"] == PATHWAY_PL_THIRD_COUNTRY
    assert out["active_items"] == []
    assert out["primary_item"]["code"] == "proceed_to_formalize"


def test_eso3_citizenship_patch_then_still_awaits_evidence() -> None:
    pkg = _minimal_valid_package(citizenship=None)
    out = apply_employment_resolution_v1(
        package=pkg,
        handoff_status="accepted",
        employment_context={"employment_country": "PL"},
        resolution_patch={"facts": {"citizenship": "UA"}},
    )
    assert out["resolution_decision"] == RESOLUTION_AWAITING
    assert out["employability"]["decision"] == DECISION_INSUFFICIENT_FACTS
    assert out["employability"]["legal_pathway"]["pathway_id"] == PATHWAY_PL_THIRD_COUNTRY
    assert any(i["code"] == "work_authorization_evidence" for i in out["active_items"])
    assert out["primary_item"]["code"] == "provide_work_authorization_evidence"


def test_eso3_empty_patch_rejected_when_required() -> None:
    out = apply_employment_resolution_v1(
        package=_minimal_valid_package(citizenship="UA"),
        handoff_status="accepted",
        employment_context={"employment_country": "PL"},
        resolution_patch={},
        require_patch_when_not_ready=True,
    )
    assert out["resolution_decision"] == RESOLUTION_REJECTED_PATCH
    assert out["rejection_reason"] == "patch_required_for_current_blocker"
    assert out["employee_created"] is False


def test_eso3_already_employable_plans_ready_without_checklist() -> None:
    emp = evaluate_early_employability_v1(
        package=_minimal_valid_package(citizenship="PL"),
        handoff_status="accepted",
        employment_context={"employment_country": "PL"},
    )
    plan = plan_employment_resolution_v1(emp)
    assert plan["resolution_decision"] == RESOLUTION_READY
    assert plan["active_items"] == []
    assert plan["primary_item"]["code"] == "proceed_to_formalize"


def test_eso3_pending_handoff_still_blocked_via_reeval() -> None:
    out = apply_employment_resolution_v1(
        package=_minimal_valid_package(citizenship="PL"),
        handoff_status="pending_review",
        employment_context={"employment_country": "PL"},
        resolution_patch={"facts": {"citizenship": "PL"}},
    )
    assert out["resolution_decision"] == RESOLUTION_STILL_BLOCKED
    assert out["employee_created"] is False
    assert any(b.get("code") == "handoff_not_accepted" for b in out["employability"]["blockers"])


def test_eso3_orchestrator_no_employee_no_recruitment() -> None:
    orch_src = _ORCH.read_text(encoding="utf-8")
    assert "apply_employment_resolution_v1" in orch_src
    assert "Does not persist Employee" in orch_src or "Never creates Employee" in orch_src
    assert "create_employee" not in orch_src.lower()
    tree = ast.parse(orch_src)
    funcs = {n.name for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    assert "resolve_employment_missing_for_handoff" in funcs

    api = _HANDOFFS_API.read_text(encoding="utf-8")
    assert "employment-missing-resolution" in api
    assert "resolve_employment_missing_for_handoff" in api

    if _RSO_ORCH.exists():
        rso = _RSO_ORCH.read_text(encoding="utf-8")
        assert "employment_missing_resolution" not in rso
        assert "resolve_employment_missing" not in rso


def test_eso3_docs_and_ci() -> None:
    arch = _ARCH.read_text(encoding="utf-8")
    assert POLICY_ID in arch
    assert "ready_to_formalize" in arch
    assert "checklist" in arch.lower()
    assert "re-evaluate" in arch.lower() or "re-eval" in arch.lower()
    assert "Employee" in arch

    eso = _ESO.read_text(encoding="utf-8")
    assert "employment-missing-resolution.md" in eso or POLICY_ID in eso
    assert "ESO-3" in eso

    ee = _EE.read_text(encoding="utf-8")
    assert "employment-missing-resolution" in ee or "ESO-3" in ee

    ci = _CI.read_text(encoding="utf-8")
    assert "test_employment_missing_resolution_gate.py" in ci
    assert "eso3" in ci or "employment-missing" in ci
