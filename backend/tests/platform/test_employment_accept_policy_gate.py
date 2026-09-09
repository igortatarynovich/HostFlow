"""Employment Accept Policy Gate (ESO-1).

Policy shape + gate 2 reuse + auto_accept forbids ritual Accept.
Not ESO-2 employability. Not Recruitment Transfer calling accept.
"""

from __future__ import annotations

import ast
from pathlib import Path

from backend.app.core.audit_events import AuditEventType
from backend.app.reference.employment_accept_policy import (
    ARCH_REL,
    DECISION_AUTO_ACCEPT,
    DECISION_REJECT_INVALID_PACKAGE,
    DECISION_REVIEW_REQUIRED,
    DECISION_VALUES,
    EMPLOYMENT_STARTED_MESSAGE,
    ESO_BRIEF_REL,
    EVALUATE_API,
    PACKAGE_AUTHORITATIVE_FIELD_CODES,
    POLICY_ID,
    RFE_ARCH_REL,
    assert_employment_missing_reuses_package,
    evaluate_employment_accept_policy_v1,
)
from backend.app.reference.ready_for_employment import (
    ACCEPTANCE_GATE_IDS,
    CONTRACT_ID,
    TRANSFER_OPERATOR_ACTION,
)

_REPO_ROOT = Path(__file__).resolve().parents[3]
_ARCH = _REPO_ROOT / ARCH_REL
_ESO = _REPO_ROOT / ESO_BRIEF_REL
_RFE = _REPO_ROOT / RFE_ARCH_REL
_CI = _REPO_ROOT / ".github" / "workflows" / "backend-ci.yml"
_MODULE = _REPO_ROOT / "backend" / "app" / "reference" / "employment_accept_policy.py"
_ORCH = _REPO_ROOT / "backend" / "app" / "services" / "employment_accept_orchestrator.py"
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


def _minimal_valid_package() -> dict:
    return {
        "contract_id": CONTRACT_ID,
        "tenant_id": "11111111-1111-1111-1111-111111111111",
        "person": {
            "person_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            "identity_facts": {"citizenship": "UA", "first_name": "Ada"},
        },
        "target_work": {
            "vacancy_id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
            "employer_id": "cccccccc-cccc-cccc-cccc-cccccccccccc",
        },
        "recruitment_facts": {"language_ok": True},
        "evidence": {"source": "meta_lead", "document_ids": []},
        "fits_decision": {
            "decision": "fits",
            "decided_at": "2026-09-09T10:00:00+00:00",
            "actor_id": "dddddddd-dddd-dddd-dddd-dddddddddddd",
        },
        "context_refs": {
            "application_id": "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee",
        },
    }


def test_eso1_gate_filename() -> None:
    assert Path(__file__).name == "test_employment_accept_policy_gate.py"


def test_eso1_policy_id_and_apis() -> None:
    assert POLICY_ID == "employment_accept_policy.v1"
    assert EVALUATE_API == "evaluate_employment_accept_policy_v1"
    assert "def evaluate_employment_accept_policy_v1(" in _MODULE.read_text(encoding="utf-8")
    assert DECISION_VALUES == (
        DECISION_AUTO_ACCEPT,
        DECISION_REVIEW_REQUIRED,
        DECISION_REJECT_INVALID_PACKAGE,
    )
    assert "citizenship" in PACKAGE_AUTHORITATIVE_FIELD_CODES
    assert "vacancy_id" in PACKAGE_AUTHORITATIVE_FIELD_CODES
    assert AuditEventType.employment_started.value == "employment_started"
    assert EMPLOYMENT_STARTED_MESSAGE == "Employment started"
    assert ACCEPTANCE_GATE_IDS == (
        "rso_terminal_is_package",
        "eso_reuses_package_no_reask",
        "operator_does_not_service_boundary",
    )


def test_eso1_auto_accept_when_package_valid_and_pending() -> None:
    out = evaluate_employment_accept_policy_v1(
        package=_minimal_valid_package(),
        handoff_status="pending_review",
        employment_missing=[],
        destination="internal_hr",
        handoff_enabled=True,
    )
    assert out["decision"] == DECISION_AUTO_ACCEPT
    assert out["ritual_accept_forbidden"] is True
    assert out["package_valid"] is True
    assert out["blockers"] == []
    assert out["reuse_violations"] == []


def test_eso1_rejects_invalid_package() -> None:
    bad = _minimal_valid_package()
    del bad["fits_decision"]
    out = evaluate_employment_accept_policy_v1(
        package=bad,
        handoff_status="pending_review",
        employment_missing=[],
    )
    assert out["decision"] == DECISION_REJECT_INVALID_PACKAGE
    assert out["package_valid"] is False


def test_eso1_gate2_blocks_reasking_package_facts() -> None:
    missing = [
        {"field_code": "citizenship", "label": "Citizenship again"},
        {"field_code": "zezwolenie", "label": "Work permit"},
    ]
    violations = assert_employment_missing_reuses_package(
        missing, package=_minimal_valid_package()
    )
    assert "citizenship" in violations
    assert "zezwolenie" not in violations

    out = evaluate_employment_accept_policy_v1(
        package=_minimal_valid_package(),
        handoff_status="pending_review",
        employment_missing=missing,
    )
    assert out["decision"] == DECISION_REVIEW_REQUIRED
    assert "citizenship" in out["reuse_violations"]
    assert any(b.get("code") == "package_fact_reask" for b in out["blockers"])


def test_eso1_conflict_reason_allows_authoritative_reask() -> None:
    missing = [
        {
            "field_code": "citizenship",
            "label": "Citizenship",
            "conflict_reason": "package says UA; passport scan shows PL",
        }
    ]
    assert assert_employment_missing_reuses_package(missing, package=_minimal_valid_package()) == []
    out = evaluate_employment_accept_policy_v1(
        package=_minimal_valid_package(),
        handoff_status="pending_review",
        employment_missing=missing,
    )
    # Still review_required because employment_missing is non-empty, but not reuse violation.
    assert out["reuse_violations"] == []
    assert out["decision"] == DECISION_REVIEW_REQUIRED


def test_eso1_orchestrator_uses_accept_handoff_not_recruitment() -> None:
    orch_src = _ORCH.read_text(encoding="utf-8")
    assert "accept_handoff" in orch_src
    assert "employment_started" in orch_src
    assert "Recruitment Transfer must never" in orch_src or "must never call" in orch_src.lower()
    tree = ast.parse(orch_src)
    funcs = {n.name for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    assert "apply_employment_accept_policy" in funcs

    api = _HANDOFFS_API.read_text(encoding="utf-8")
    assert "employment-accept-policy" in api
    assert "apply_employment_accept_policy" in api

    # Recruitment orchestrator (if present on branch) must not call employment accept apply.
    if _RSO_ORCH.exists():
        rso = _RSO_ORCH.read_text(encoding="utf-8")
        assert "apply_employment_accept_policy" not in rso
        assert "employment_accept_policy" not in rso


def test_eso1_docs_and_ci() -> None:
    arch = _ARCH.read_text(encoding="utf-8")
    assert POLICY_ID in arch
    assert "auto_accept" in arch
    assert "conflict_reason" in arch
    assert TRANSFER_OPERATOR_ACTION in arch or "Передать на трудоустройство" in arch
    assert "Employment started" in arch
    assert "ritual Accept" in arch or "Ritual Accept" in arch

    eso = _ESO.read_text(encoding="utf-8")
    assert "employment-accept-policy.md" in eso or POLICY_ID in eso
    assert "ESO-1" in eso

    rfe = _RFE.read_text(encoding="utf-8")
    assert "employment-accept-policy" in rfe or "ESO-1" in rfe

    ci = _CI.read_text(encoding="utf-8")
    assert "test_employment_accept_policy_gate.py" in ci
    assert "eso1" in ci or "employment-accept" in ci
