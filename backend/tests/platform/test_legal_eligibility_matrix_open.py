"""Legal Eligibility Matrix stays not PASS.

The live geometry is the decision chain. The six-tuple opening remains
history. No evidence list is assigned.
"""

from __future__ import annotations

from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
_MATRIX = _REPO_ROOT / "docs" / "specs" / "architecture" / "legal-eligibility-matrix.md"
_CONTRACT = _REPO_ROOT / "docs" / "specs" / "architecture" / "legal-eligibility-contract.md"
_QUEUE = _REPO_ROOT / "docs" / "specs" / "tasks" / "sales-to-comms-sequential-queue.md"
_LEGAL = _REPO_ROOT / "docs" / "specs" / "tasks" / "legal-eligibility-requirement-policy.md"
_HR = _REPO_ROOT / "docs" / "specs" / "tasks" / "recruitment-hr-minimal-handoff.md"
_CI = _REPO_ROOT / ".github" / "workflows" / "backend-ci.yml"


def test_legal_eligibility_matrix_open_filename() -> None:
    assert Path(__file__).name == "test_legal_eligibility_matrix_open.py"


def test_legal_eligibility_matrix_structure_is_opened_not_pass() -> None:
    text = _MATRIX.read_text(encoding="utf-8")
    live, history = text.split("## History", 1)
    assert "**Decision model**" in live
    assert "Legal Eligibility Matrix Gate **not PASS**" in live
    assert "Legal Eligibility Matrix Gate **PASS**" not in text
    assert "**Accepted**" not in live
    assert "`citizenship_class`" in live
    assert "`work_authorization_basis`" in live
    assert "`valid_for_this_employment`" in live
    assert "There is no six-tuple cell and no default cell." in live
    assert "are not steps" in live
    assert "An operator hold is not an outcome id" in live
    assert "does not receive the required document set" in live or "not a required document set" in live
    assert "future outcome schema" in live
    assert "assigned to no chain result" in live
    assert "hands RPM nothing" in live
    assert "sole writer of the required set" in live
    assert "This amendment has none" in live
    assert "does not authorize a runtime module" in live
    assert "Feat stays locked" in live
    assert "not scheduled" in live.lower()
    assert "not release-ready" in live.lower()
    assert "No runtime module" in live
    assert "exactly these six facts, in this order, and no other key" in history
    assert "That geometry is not live." in history
    assert not (_REPO_ROOT / "backend" / "app" / "reference" / "legal_eligibility.py").exists()
    contract = _CONTRACT.read_text(encoding="utf-8")
    assert "Legal Eligibility Contract Gate **PASS**" in contract
    assert "**Legal-policy vocabulary**" in contract


def test_legal_eligibility_matrix_open_is_current_and_hr_unscheduled() -> None:
    queue = _QUEUE.read_text(encoding="utf-8")
    current, history = queue.split("## 8. History", 1)
    assert "legal-eligibility-matrix.md" in current
    assert "Legal Eligibility Matrix Gate **not PASS**" in current
    assert "Legal Eligibility Matrix Gate **PASS**" not in current
    assert "Legal Eligibility Contract Gate **PASS**" in current
    assert "Decision model amendment" in current
    assert "Evidence rules are not encoded" in current
    assert "Do not assign documents or outcome ids in this opening" in history
    assert "matrix not written" not in current
    assert "not scheduled" in current.lower()
    assert "Legal Eligibility Matrix opened" in history
    assert "Legal Eligibility Contract Gate PASS" in history
    legal = _LEGAL.read_text(encoding="utf-8")
    header = legal.split("## Problem", 1)[0]
    assert "Legal Eligibility Matrix Gate **not PASS**" in header
    assert "Feat locked" in header
    assert "Runtime not authorized" in header
    hr = _HR.read_text(encoding="utf-8")
    hr_header = hr.split("## History", 1)[0] if "## History" in hr else hr
    assert "**SUPERSEDED**" in hr_header
    assert "not scheduled" in hr_header.lower()
    assert "feat locked" in hr_header.lower()
    ci = _CI.read_text(encoding="utf-8")
    assert "test_legal_eligibility_matrix_open.py" in ci
