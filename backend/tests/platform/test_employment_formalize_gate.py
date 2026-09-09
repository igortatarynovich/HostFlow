"""Employment Formalize Gate (ESO-4).

Context-derived formal actions + ready_to_create_employee threshold.
No Employee mint. No HR card. No universal checklist. LLM-OFF.
"""

from __future__ import annotations

import ast
from pathlib import Path

from backend.app.reference.early_employability import PATHWAY_PL_EU_EEA, PATHWAY_PL_THIRD_COUNTRY
from backend.app.reference.employment_formalize import (
    ACTION_CONTRACT_BASIS,
    ACTION_IDENTITY_PRESENT,
    ACTION_WORK_AUTH,
    ARCH_REL,
    DECISION_BLOCKED,
    DECISION_COMPLETE,
    DECISION_MISSING,
    DECISION_REJECTED_PATCH,
    DECISION_VALUES,
    ESO_BRIEF_REL,
    EVALUATE_API,
    POLICY_ID,
    READY_TO_CREATE_EMPLOYEE,
    RESOLUTION_ARCH_REL,
    apply_employment_formalize_v1,
    evaluate_employment_formalize_v1,
    required_formal_actions_v1,
)
from backend.app.reference.ready_for_employment import CONTRACT_ID

_REPO_ROOT = Path(__file__).resolve().parents[3]
_ARCH = _REPO_ROOT / ARCH_REL
_ESO = _REPO_ROOT / ESO_BRIEF_REL
_RES = _REPO_ROOT / RESOLUTION_ARCH_REL
_CI = _REPO_ROOT / ".github" / "workflows" / "backend-ci.yml"
_MODULE = _REPO_ROOT / "backend" / "app" / "reference" / "employment_formalize.py"
_ORCH = _REPO_ROOT / "backend" / "app" / "services" / "employment_formalize_orchestrator.py"
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


def _pkg(*, citizenship: str = "PL", evidence: dict | None = None) -> dict:
    return {
        "contract_id": CONTRACT_ID,
        "tenant_id": "11111111-1111-1111-1111-111111111111",
        "person": {
            "person_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            "identity_facts": {"citizenship": citizenship, "first_name": "Ada"},
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
        "context_refs": {"application_id": "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee"},
    }


def test_eso4_gate_filename() -> None:
    assert Path(__file__).name == "test_employment_formalize_gate.py"


def test_eso4_policy_id_and_apis() -> None:
    assert POLICY_ID == "employment_formalize.v1"
    assert EVALUATE_API == "evaluate_employment_formalize_v1"
    assert READY_TO_CREATE_EMPLOYEE == "ready_to_create_employee"
    assert "def evaluate_employment_formalize_v1(" in _MODULE.read_text(encoding="utf-8")
    assert DECISION_VALUES == (
        DECISION_COMPLETE,
        DECISION_MISSING,
        DECISION_BLOCKED,
        DECISION_REJECTED_PATCH,
    )


def test_eso4_required_actions_derived_from_pathway_not_universal() -> None:
    eu = required_formal_actions_v1(pathway_id=PATHWAY_PL_EU_EEA)
    codes = {r["code"] for r in eu}
    assert ACTION_CONTRACT_BASIS in codes
    assert ACTION_IDENTITY_PRESENT in codes
    assert ACTION_WORK_AUTH not in codes
    assert "full_legalization_checklist" not in codes
    assert len(eu) <= 3

    tc = required_formal_actions_v1(pathway_id=PATHWAY_PL_THIRD_COUNTRY)
    tc_codes = {r["code"] for r in tc}
    assert ACTION_WORK_AUTH in tc_codes
    assert ACTION_CONTRACT_BASIS in tc_codes
    assert len(tc) <= 3


def test_eso4_eu_missing_contract_confirmation_only() -> None:
    out = evaluate_employment_formalize_v1(
        package=_pkg(citizenship="PL"),
        handoff_status="accepted",
        employment_context={"employment_country": "PL"},
    )
    assert out["ready_to_formalize"] is True
    assert out["decision"] == DECISION_MISSING
    assert out["ready_to_create_employee"] is False
    assert out["employee_created"] is False
    assert out["hr_employee_card"] is False
    missing_codes = {m["code"] for m in out["active_missing"]}
    assert missing_codes == {ACTION_CONTRACT_BASIS}
    # Identity already on package — not re-asked.
    assert ACTION_IDENTITY_PRESENT not in missing_codes


def test_eso4_confirm_contract_emits_ready_to_create_employee() -> None:
    out = apply_employment_formalize_v1(
        package=_pkg(citizenship="DE"),
        handoff_status="accepted",
        employment_context={"employment_country": "PL"},
        formalize_patch={"confirmed_actions": [ACTION_CONTRACT_BASIS]},
    )
    assert out["decision"] == DECISION_COMPLETE
    assert out["ready_to_create_employee"] is True
    assert out["employee_created"] is False
    assert out["active_missing"] == []
    assert out["primary_item"]["code"] == READY_TO_CREATE_EMPLOYEE
    assert out["pathway_id"] == PATHWAY_PL_EU_EEA


def test_eso4_third_country_reuses_work_auth_evidence() -> None:
    pkg = _pkg(
        citizenship="UA",
        evidence={"source": "meta", "work_permit_document_id": "doc-1"},
    )
    out = evaluate_employment_formalize_v1(
        package=pkg,
        handoff_status="accepted",
        employment_context={"employment_country": "PL"},
    )
    assert out["decision"] == DECISION_MISSING
    missing_codes = {m["code"] for m in out["active_missing"]}
    assert ACTION_WORK_AUTH not in missing_codes  # already on package
    assert ACTION_CONTRACT_BASIS in missing_codes


def test_eso4_not_ready_blocked() -> None:
    out = evaluate_employment_formalize_v1(
        package=_pkg(citizenship="UA"),  # no work auth → not employable
        handoff_status="accepted",
        employment_context={"employment_country": "PL"},
    )
    assert out["ready_to_formalize"] is False
    assert out["decision"] == DECISION_BLOCKED
    assert out["ready_to_create_employee"] is False


def test_eso4_empty_patch_rejected_when_required() -> None:
    out = apply_employment_formalize_v1(
        package=_pkg(citizenship="PL"),
        handoff_status="accepted",
        employment_context={"employment_country": "PL"},
        formalize_patch={},
        require_patch_when_missing=True,
    )
    assert out["decision"] == DECISION_REJECTED_PATCH
    assert out["ready_to_create_employee"] is False


def test_eso4_orchestrator_no_employee_mint() -> None:
    orch = _ORCH.read_text(encoding="utf-8")
    assert "apply_employment_formalize_v1" in orch
    assert "Does not mint Employee" in orch or "employee_created" in orch
    assert "workforce_employees" not in orch
    tree = ast.parse(orch)
    funcs = {n.name for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    assert "formalize_employment_for_handoff" in funcs

    api = _HANDOFFS_API.read_text(encoding="utf-8")
    assert "employment-formalize" in api
    assert "formalize_employment_for_handoff" in api

    if _RSO_ORCH.exists():
        rso = _RSO_ORCH.read_text(encoding="utf-8")
        assert "employment_formalize" not in rso
        assert "formalize_employment" not in rso


def test_eso4_docs_and_ci() -> None:
    arch = _ARCH.read_text(encoding="utf-8")
    assert POLICY_ID in arch
    assert "ready_to_create_employee" in arch
    assert "formalization_complete" in arch
    assert "checklist" in arch.lower()
    assert "Employee" in arch

    eso = _ESO.read_text(encoding="utf-8")
    assert "employment-formalize.md" in eso or POLICY_ID in eso
    assert "ESO-4" in eso

    res = _RES.read_text(encoding="utf-8")
    assert "employment-formalize" in res or "ESO-4" in res or "Formalize" in res

    ci = _CI.read_text(encoding="utf-8")
    assert "test_employment_formalize_gate.py" in ci
    assert "eso4" in ci or "formalize" in ci
