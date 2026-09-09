"""Early Employability Gate (ESO-2).

Decision shape + unique pathway lock + no Employee create + LLM-OFF.
Not Formalize. Not Recruitment Transfer calling employability.
"""

from __future__ import annotations

import ast
from pathlib import Path

from backend.app.reference.early_employability import (
    ACCEPT_ARCH_REL,
    ARCH_REL,
    DECISION_BLOCKED,
    DECISION_EMPLOYABLE,
    DECISION_INSUFFICIENT_FACTS,
    DECISION_VALUES,
    ESO_BRIEF_REL,
    EVALUATE_API,
    PATHWAY_PL_EU_EEA,
    PATHWAY_PL_THIRD_COUNTRY,
    POLICY_ID,
    derive_unique_legal_pathway,
    evaluate_early_employability_v1,
)
from backend.app.reference.ready_for_employment import CONTRACT_ID

_REPO_ROOT = Path(__file__).resolve().parents[3]
_ARCH = _REPO_ROOT / ARCH_REL
_ESO = _REPO_ROOT / ESO_BRIEF_REL
_ACCEPT = _REPO_ROOT / ACCEPT_ARCH_REL
_CI = _REPO_ROOT / ".github" / "workflows" / "backend-ci.yml"
_MODULE = _REPO_ROOT / "backend" / "app" / "reference" / "early_employability.py"
_ORCH = _REPO_ROOT / "backend" / "app" / "services" / "early_employability_orchestrator.py"
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


def _minimal_valid_package(*, citizenship: str = "UA", evidence: dict | None = None) -> dict:
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
        "context_refs": {
            "application_id": "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee",
        },
    }


def test_eso2_gate_filename() -> None:
    assert Path(__file__).name == "test_early_employability_gate.py"


def test_eso2_policy_id_and_apis() -> None:
    assert POLICY_ID == "early_employability.v1"
    assert EVALUATE_API == "evaluate_early_employability_v1"
    assert "def evaluate_early_employability_v1(" in _MODULE.read_text(encoding="utf-8")
    assert DECISION_VALUES == (
        DECISION_EMPLOYABLE,
        DECISION_BLOCKED,
        DECISION_INSUFFICIENT_FACTS,
    )


def test_eso2_eu_citizen_employable_unique_pathway() -> None:
    out = evaluate_early_employability_v1(
        package=_minimal_valid_package(citizenship="PL"),
        handoff_status="accepted",
        employment_context={"employment_country": "PL"},
    )
    assert out["decision"] == DECISION_EMPLOYABLE
    assert out["employee_created"] is False
    assert out["llm_eligibility"] is False
    assert out["pathway_selection_required"] is False
    assert out["legal_pathway"]["pathway_id"] == PATHWAY_PL_EU_EEA
    assert out["legal_pathway"]["selection_required"] is False
    assert out["next_step"]["code"] == "proceed_to_formalize"
    assert out["requirements"] == []


def test_eso2_third_country_without_evidence_insufficient() -> None:
    out = evaluate_early_employability_v1(
        package=_minimal_valid_package(citizenship="UA"),
        handoff_status="accepted",
        employment_context={"employment_country": "PL", "position_category": "driver"},
    )
    assert out["decision"] == DECISION_INSUFFICIENT_FACTS
    assert out["legal_pathway"]["pathway_id"] == PATHWAY_PL_THIRD_COUNTRY
    assert out["pathway_selection_required"] is False
    assert out["employee_created"] is False
    assert any(r.get("code") == "work_authorization_evidence" for r in out["requirements"])
    assert out["next_step"]["code"] == "provide_work_authorization_evidence"


def test_eso2_third_country_with_evidence_employable() -> None:
    pkg = _minimal_valid_package(
        citizenship="UA",
        evidence={"source": "meta", "work_permit_document_id": "doc-1"},
    )
    out = evaluate_early_employability_v1(
        package=pkg,
        handoff_status="accepted",
        employment_context={"employment_country": "PL"},
    )
    assert out["decision"] == DECISION_EMPLOYABLE
    assert out["legal_pathway"]["pathway_id"] == PATHWAY_PL_THIRD_COUNTRY
    assert out["next_step"]["code"] == "proceed_to_formalize"


def test_eso2_missing_citizenship_asks_minimal_fact_not_pathway_menu() -> None:
    pkg = _minimal_valid_package()
    pkg["person"]["identity_facts"] = {"first_name": "Ada"}
    out = evaluate_early_employability_v1(
        package=pkg,
        handoff_status="accepted",
        employment_context={"employment_country": "PL"},
    )
    assert out["decision"] == DECISION_INSUFFICIENT_FACTS
    assert out["legal_pathway"] is None
    assert out["pathway_selection_required"] is False
    assert out["next_step"]["code"] == "provide_citizenship"
    assert any(r.get("code") == "citizenship" for r in out["requirements"])


def test_eso2_pending_handoff_blocked_before_employability() -> None:
    out = evaluate_early_employability_v1(
        package=_minimal_valid_package(citizenship="PL"),
        handoff_status="pending_review",
        employment_context={"employment_country": "PL"},
    )
    assert out["decision"] == DECISION_BLOCKED
    assert out["handoff_accepted"] is False
    assert any(b.get("code") == "handoff_not_accepted" for b in out["blockers"])
    assert out["next_step"]["code"] == "accept_handoff_first"
    assert out["employee_created"] is False


def test_eso2_unique_pathway_derivation() -> None:
    eu = derive_unique_legal_pathway(employment_country="PL", citizenship="DE")
    assert eu is not None
    assert eu["pathway_id"] == PATHWAY_PL_EU_EEA
    assert eu["selection_required"] is False
    tc = derive_unique_legal_pathway(employment_country="PL", citizenship="UA")
    assert tc is not None
    assert tc["pathway_id"] == PATHWAY_PL_THIRD_COUNTRY
    assert derive_unique_legal_pathway(employment_country="PL", citizenship="") is None


def test_eso2_orchestrator_evaluate_only_no_employee() -> None:
    orch_src = _ORCH.read_text(encoding="utf-8")
    assert "evaluate_early_employability_v1" in orch_src
    assert "Never creates Employee" in orch_src or "Does not persist Employee" in orch_src
    assert "create_employee" not in orch_src.lower()
    tree = ast.parse(orch_src)
    funcs = {n.name for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    assert "evaluate_early_employability_for_handoff" in funcs

    api = _HANDOFFS_API.read_text(encoding="utf-8")
    assert "early-employability" in api
    assert "evaluate_early_employability_for_handoff" in api

    if _RSO_ORCH.exists():
        rso = _RSO_ORCH.read_text(encoding="utf-8")
        assert "evaluate_early_employability" not in rso
        assert "early_employability" not in rso


def test_eso2_docs_and_ci() -> None:
    arch = _ARCH.read_text(encoding="utf-8")
    assert POLICY_ID in arch
    assert "employable" in arch
    assert "insufficient_facts" in arch
    assert "selection_required" in arch
    assert "LLM-OFF" in arch
    assert "Employee" in arch

    eso = _ESO.read_text(encoding="utf-8")
    assert "early-employability.md" in eso or POLICY_ID in eso
    assert "ESO-2" in eso

    accept = _ACCEPT.read_text(encoding="utf-8")
    assert "early-employability" in accept or "ESO-2" in accept

    ci = _CI.read_text(encoding="utf-8")
    assert "test_early_employability_gate.py" in ci
    assert "eso2" in ci or "early-employability" in ci
