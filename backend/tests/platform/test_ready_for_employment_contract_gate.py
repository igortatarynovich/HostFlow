"""Ready for employment Contract Gate (RSO-1).

Package shape + three acceptance gates. Feat locked for contract.
Not ESO accept policy. Not legacy handoff snapshot cutover. Not Hiring E2E.
"""

from __future__ import annotations

from pathlib import Path

from backend.app.reference.ready_for_employment import (
    ACCEPTANCE_GATE_IDS,
    ARCH_REL,
    CONTRACT_ID,
    ESO_BRIEF_REL,
    FORBIDDEN_TOP_LEVEL_KEYS,
    OPERATOR_QUESTION,
    REQUIRED_TOP_LEVEL_KEYS,
    RSO_BRIEF_REL,
    TRANSFER_OPERATOR_ACTION,
    VALIDATE_API,
    is_valid_ready_for_employment_package_v1,
    validate_ready_for_employment_package_v1,
)

_REPO_ROOT = Path(__file__).resolve().parents[3]
_ARCH = _REPO_ROOT / ARCH_REL
_RSO = _REPO_ROOT / RSO_BRIEF_REL
_ESO = _REPO_ROOT / ESO_BRIEF_REL
_CI = _REPO_ROOT / ".github" / "workflows" / "backend-ci.yml"
_MODULE = _REPO_ROOT / "backend" / "app" / "reference" / "ready_for_employment.py"
_HIRING = _REPO_ROOT / "docs" / "specs" / "tasks" / "hiring-workflow-e2e.md"


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


def test_rfe_gate_filename() -> None:
    assert Path(__file__).name == "test_ready_for_employment_contract_gate.py"


def test_rfe_contract_id_and_shape() -> None:
    assert CONTRACT_ID == "ready_for_employment.v1"
    assert "immutable package" in OPERATOR_QUESTION
    assert TRANSFER_OPERATOR_ACTION == "Передать на трудоустройство"
    assert VALIDATE_API == "validate_ready_for_employment_package_v1"
    assert "def validate_ready_for_employment_package_v1(" in _MODULE.read_text(
        encoding="utf-8"
    )
    assert REQUIRED_TOP_LEVEL_KEYS == (
        "contract_id",
        "tenant_id",
        "person",
        "target_work",
        "recruitment_facts",
        "evidence",
        "fits_decision",
        "context_refs",
    )
    assert FORBIDDEN_TOP_LEVEL_KEYS == frozenset(
        {
            "employee_id",
            "employment_missing",
            "legalization_pathway",
            "zus_journey",
            "create_employee",
            "accept_handoff",
        }
    )
    assert ACCEPTANCE_GATE_IDS == (
        "rso_terminal_is_package",
        "eso_reuses_package_no_reask",
        "operator_does_not_service_boundary",
    )


def test_rfe_validator_accepts_minimal_package() -> None:
    pkg = _minimal_valid_package()
    assert validate_ready_for_employment_package_v1(pkg) == []
    assert is_valid_ready_for_employment_package_v1(pkg)


def test_rfe_validator_rejects_forbidden_and_missing() -> None:
    assert validate_ready_for_employment_package_v1(None) == ["package must be a mapping"]

    bad = _minimal_valid_package()
    bad["employee_id"] = "should-not-be-here"
    bad["employment_missing"] = ["passport"]
    del bad["fits_decision"]
    errs = validate_ready_for_employment_package_v1(bad)
    assert any("forbidden top-level key: employee_id" in e for e in errs)
    assert any("forbidden top-level key: employment_missing" in e for e in errs)
    assert any("missing required key: fits_decision" in e for e in errs)

    no_target = _minimal_valid_package()
    no_target["target_work"] = {}
    assert any(
        "vacancy_id and/or employer_id" in e
        for e in validate_ready_for_employment_package_v1(no_target)
    )

    wrong_decision = _minimal_valid_package()
    wrong_decision["fits_decision"]["decision"] = "maybe"
    assert any(
        "decision must be 'fits'" in e
        for e in validate_ready_for_employment_package_v1(wrong_decision)
    )


def test_rfe_architecture_is_sot() -> None:
    text = _ARCH.read_text(encoding="utf-8")
    assert CONTRACT_ID in text
    assert "Three acceptance gates" in text
    assert "rso_terminal_is_package" in text
    assert "eso_reuses_package_no_reask" in text
    assert "operator_does_not_service_boundary" in text
    assert TRANSFER_OPERATOR_ACTION in text
    assert "does not re-ask" in text.lower() or "reuses" in text.lower()
    assert "employment_missing" in text
    assert "legalization_pathway" in text
    assert "build_handoff_snapshot_payload_v1" in text
    assert "Domain boundary splits" in text or "responsibility" in text.lower()
    assert "**PASS**" in text or "RSO-1" in text


def test_rfe_briefs_name_acceptance_gates() -> None:
    for path in (_RSO, _ESO):
        text = path.read_text(encoding="utf-8")
        assert "Acceptance gates" in text
        assert "ready_for_employment.v1" in text or "ready-for-employment-contract.md" in text
        assert "Передать на трудоустройство" in text
        assert "test_ready_for_employment_contract_gate.py" in text
        lowered = text.lower()
        assert "re-ask" in lowered or "reuses" in lowered or "переиспользу" in lowered
        assert "не знает, как трудоустраивать" in text or "does not know how to employ" in lowered


def test_rfe_hiring_points_at_spines_and_contract() -> None:
    text = _HIRING.read_text(encoding="utf-8")
    assert "recruitment-spine-orchestrator-v1.md" in text
    assert "employment-spine-orchestrator-v1.md" in text
    assert "ready-for-employment-contract.md" in text or CONTRACT_ID in text


def test_rfe_ci_wires_gate() -> None:
    text = _CI.read_text(encoding="utf-8")
    assert "test_ready_for_employment_contract_gate.py" in text
    assert "ready-for-employment-contract.md" in text
    assert "ready_for_employment" in text or "rfe1" in text
