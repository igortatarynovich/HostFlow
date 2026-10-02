"""Legal Eligibility Contract Gate PASS.

Evidence is the corrected contract-open. The gate accepts the closed
fact set, the three vocabularies, and the two unassigned outcome shapes.
It does not open the matrix and it does not unlock feat or runtime.
"""

from __future__ import annotations

from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
_CONTRACT = _REPO_ROOT / "docs" / "specs" / "architecture" / "legal-eligibility-contract.md"
_QUEUE = _REPO_ROOT / "docs" / "specs" / "tasks" / "sales-to-comms-sequential-queue.md"
_LEGAL = _REPO_ROOT / "docs" / "specs" / "tasks" / "legal-eligibility-requirement-policy.md"
_AGENTS = _REPO_ROOT / "AGENTS.md"
_GOAL = _REPO_ROOT / "docs" / "specs" / "gates" / "hostflow-v1-release-goal.md"
_ROADMAP = _REPO_ROOT / "docs" / "specs" / "architecture" / "platform-completion-roadmap.md"
_HR = _REPO_ROOT / "docs" / "specs" / "tasks" / "recruitment-hr-minimal-handoff.md"
_CI = _REPO_ROOT / ".github" / "workflows" / "backend-ci.yml"


def test_legal_eligibility_contract_gate_filename() -> None:
    assert Path(__file__).name == "test_legal_eligibility_contract_gate.py"


def test_legal_eligibility_contract_gate_pass_accepts_closed_contract() -> None:
    text = _CONTRACT.read_text(encoding="utf-8")
    assert "**Status:** **Accepted**" in text
    assert "Legal Eligibility Contract Gate **PASS**" in text
    assert "**not PASS**" not in text
    assert "The list above is closed" in text
    assert "`residence_permit_type` is not a fact key" in text
    assert "**Card vocabulary**" in text
    assert "**Legal-policy vocabulary**" in text
    assert "**Pack tokens**" in text
    assert "They are not aliases of each other" in text
    assert "`visa_d` is not the pack token `visa`" in text
    assert "Empty `stay_basis` (`''` in `POLAND_BASIS_VALUES`) is a recorded state" in text
    assert "exclusively `r5_required_set`" in text
    assert "sole policy write" in text
    assert text.count("to no fact value") >= 2
    assert "not assigned to empty `stay_basis`" in text
    assert "The matrix stays empty and is the next separate stage" in text
    assert "Feat stays locked" in text
    assert "No runtime module" in text
    assert "does not change RPM, eligibility, transfer, `ready_for_employment.v1`, HR, or the database schema" in text
    assert not (_REPO_ROOT / "backend" / "app" / "reference" / "legal_eligibility.py").exists()


def test_legal_eligibility_contract_gate_pass_is_current_canon() -> None:
    queue = _QUEUE.read_text(encoding="utf-8")
    current, history = queue.split("## 8. History", 1)
    assert "Legal Eligibility Contract Gate **PASS**" in current
    assert "Legal Eligibility Contract Gate **not PASS**" not in current
    assert "Matrix stays empty and is the next separate stage" in history
    assert "Legal Eligibility Matrix Gate **not PASS**" in current
    assert "feat locked" in current.lower()
    assert "Do not map `visa_d` onto `visa`" in current
    assert "Decision model amendment" in current
    assert "Evidence rules are not encoded" in current
    assert "Do not assign documents or outcome ids in this opening" in history
    assert "not scheduled" in current.lower()
    assert "Legal Eligibility Contract Gate **not PASS**" in history
    assert "Legal Eligibility Contract Gate PASS" in history
    legal = _LEGAL.read_text(encoding="utf-8")
    header = legal.split("## Problem", 1)[0]
    assert "Legal Eligibility Contract Gate **PASS**" in header
    assert "Feat locked" in header
    assert "Legal Eligibility Matrix Gate **not PASS**" in header
    assert "Runtime not authorized" in header
    for path in (_AGENTS, _GOAL, _ROADMAP):
        body = path.read_text(encoding="utf-8")
        assert "Legal Eligibility Contract Gate **PASS**" in body
    hr = _HR.read_text(encoding="utf-8")
    hr_header = hr.split("## History", 1)[0] if "## History" in hr else hr
    assert "**QUEUED**" in hr_header
    assert "not scheduled" in hr_header.lower()
    assert "feat locked" in hr_header.lower()
    ci = _CI.read_text(encoding="utf-8")
    assert "test_legal_eligibility_contract_gate.py" in ci
