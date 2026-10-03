"""Employee Record contract is opened and the Contract Gate is not passed.

The contract names Employee, Employment, the internal_hr handoff, and
Active to Ended. It writes no schema, no runtime module, and no HR
document requirement.
"""

from __future__ import annotations

from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
_CONTRACT = (
    _REPO_ROOT
    / "docs"
    / "specs"
    / "architecture"
    / "employee-record-employment-lifecycle-contract.md"
)
_BRIEF = (
    _REPO_ROOT / "docs" / "specs" / "tasks" / "employee-record-employment-lifecycle.md"
)
_RUNTIME = _REPO_ROOT / "backend" / "app" / "reference" / "employee_record.py"


def test_employee_record_contract_filename() -> None:
    assert Path(__file__).name == (
        "test_employee_record_employment_lifecycle_contract_open.py"
    )


def test_employee_record_contract_is_opened_and_not_passed() -> None:
    text = _CONTRACT.read_text(encoding="utf-8")
    current, _history = (
        text.split("## History", 1) if "## History" in text else (text, "")
    )
    assert "**Opened**" in current
    assert "employee_record_employment_lifecycle.v1" in current
    assert (
        "Employee Record & Employment Lifecycle — Contract Gate **not PASS**"
        in current
    )
    assert (
        "Employee Record & Employment Lifecycle — Contract Gate **PASS**"
        not in current
    )
    assert "Candidate" in current
    assert "ready_for_employment.v1" in current
    assert "internal_hr" in current
    assert "WorkforceEmployee" in current
    assert "CandidateEmployment" in current
    assert "One Employee may have more than one over time" in current
    assert "preparing → active → ended" in current
    assert "The Employment exists and is not yet in force" in current
    assert "That Employment is in force" in current
    assert "That Employment has finished" in current
    assert "The Employee remains" in current
    assert "does not turn the Candidate row into an Employee" in current
    assert "HR Legal Eligibility Gate" in current
    assert "Ready to Start Gate" in current
    assert "legal_eligibility.v1" in current
    assert "valid_for_this_employment" in current
    assert "`satisfied`, `waived`, or `blocking`" in current
    assert "does not canonize a Polish pre-employment document list" in current
    assert "kwestionariusz osobowy" in current
    assert "not a second copy of the person" in current
    assert "ZUS registration is a post-start obligation" in current
    assert "another plane" in current
    assert "## Persistence boundary" in current
    assert "canonical Employment is not a persistence entity" in current
    assert "`hire_date` | `workforce_employees` | Employment" in current
    assert "`termination_date` | `workforce_employees` | Employment" in current
    assert "contract-terms satellite" in current
    assert "default `issued`" in current
    assert "HR document policy stays untouched" in current
    assert "One reason:" in current
    assert "This file writes no HR document requirement" in current
    assert "No schema is written." in current
    assert "No runtime module is authorized." in current
    assert "Feat stays locked." in current
    assert not _RUNTIME.exists()

    brief = _BRIEF.read_text(encoding="utf-8")
    brief_current = brief.split("## History", 1)[0]
    assert "employee-record-employment-lifecycle-contract.md" in brief_current
    assert "contract opened" in brief_current
    assert "preparing → active → ended" in brief_current
    assert "Ready to Start Gate" in brief_current
    assert (
        "Employee Record & Employment Lifecycle — Contract Gate **not PASS**"
        in brief_current
    )
    assert (
        "Employee Record & Employment Lifecycle — Contract Gate **PASS**"
        not in brief_current
    )
