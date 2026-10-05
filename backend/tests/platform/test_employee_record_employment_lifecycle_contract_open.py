"""Employee Record contract is accepted and the Contract Gate is passed.

The contract names the handoff as a process transition over the same
person, Employment as the labour relationship, and workforce_employments
as the contract card. It writes no schema and no runtime module.
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


def test_employee_record_contract_is_accepted() -> None:
    text = _CONTRACT.read_text(encoding="utf-8")
    current, _history = (
        text.split("## History", 1) if "## History" in text else (text, "")
    )
    assert "**Accepted**" in current
    assert "employee_record_employment_lifecycle.v1" in current
    assert (
        "Employee Record & Employment Lifecycle — Contract Gate **PASS**"
        in current
    )
    assert (
        "Employee Record & Employment Lifecycle — Contract Gate **not PASS**"
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
    assert "HR process ownership opened for that Person" in current
    assert "does not create a person and it does not copy person or evidence data" in current
    assert "not the canonical meaning of the handoff" in current
    assert "No Person table is authorized" in current
    assert "does not merge Lead, Candidate, and Employee into one table" in current
    assert "existing Employee context" in current
    assert "That path creates no Candidate and no person." in current
    assert "current runtime link" in current
    assert "HR Legal Eligibility Gate" in current
    assert "Ready to Start Gate" in current
    assert "legal_eligibility.v1" in current
    assert "valid_for_this_employment" in current
    assert "`satisfied`, `waived`, or `blocking`" in current
    assert "does not canonize a Polish pre-employment document list" in current
    assert "kwestionariusz osobowy" in current
    assert "not a second copy of the person" in current
    assert "It is not universally pre-start and it is not universally post-start." in current
    assert "Employment Preparation Dependency Amendment" in current
    assert "ZUS registration is a post-start obligation" not in current
    assert "another plane" in current
    assert "## Persistence boundary" in current
    assert "canonical Employment is not yet a table" in current
    assert "## Repository discovery" in current
    assert "ix_workforce_employments_tenant_employee" in current
    assert "The client of this hire" in current
    assert "Employment Persistence Schema" in current
    assert "No reverse edge exists." in current
    assert "`hire_date` does not choose that state." in current
    assert "auto_bundle" in current
    assert "`hire_date` | `workforce_employees` | Employment" in current
    assert "`termination_date` | `workforce_employees` | Employment" in current
    assert "Not `workforce_employments.start_date`" in current
    assert "Employee 1:N Employment 1:N contract/terms records" in current
    assert "not Employment 1:1 `workforce_employments`" in current
    assert "A new contract record does not create a new Employment" in current
    assert "contract-terms satellite" in current
    assert "default `issued`" in current
    assert "HR document policy stays untouched" in current
    assert "This file writes no HR document requirement" in current
    assert "No schema is written." in current
    assert "No runtime module is authorized." in current
    assert "Feat stays locked." in current
    assert not _RUNTIME.exists()

    brief = _BRIEF.read_text(encoding="utf-8")
    brief_current = brief.split("## History", 1)[0]
    assert "employee-record-employment-lifecycle-contract.md" in brief_current
    assert "contract opened" in brief_current
    assert "does not create a person" in brief_current
    assert "HR process ownership opened" in brief_current
    assert "not the canonical meaning of the handoff" in brief_current
    assert "not merged into one table" in brief_current
    assert "preparing → active → ended" in brief_current
    assert "Ready to Start Gate" in brief_current
    assert (
        "Employee Record & Employment Lifecycle — Contract Gate **PASS**"
        in brief_current
    )
    assert (
        "Employee Record & Employment Lifecycle — Contract Gate **not PASS**"
        not in brief_current
    )
    assert "Employment Persistence Schema" in brief_current
    assert "Employee Record & Employment Lifecycle — Contract Gate **not PASS**" in brief.split(
        "## History", 1
    )[1]
