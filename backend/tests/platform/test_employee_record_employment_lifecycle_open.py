"""Employee Record & Employment Lifecycle brief is opened and the contract is passed.

The chain is Person and Candidate context to Employment to Active to
Ended. No schema and no runtime are authorized. The next slice is
Employment Persistence Schema. The minimal HR brief is superseded.
"""

from __future__ import annotations

from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
_BRIEF = (
    _REPO_ROOT / "docs" / "specs" / "tasks" / "employee-record-employment-lifecycle.md"
)
_HR = _REPO_ROOT / "docs" / "specs" / "tasks" / "recruitment-hr-minimal-handoff.md"
_QUEUE = _REPO_ROOT / "docs" / "specs" / "tasks" / "sales-to-comms-sequential-queue.md"
_RUNTIME = _REPO_ROOT / "backend" / "app" / "reference" / "employee_record.py"


def test_employee_record_employment_lifecycle_filename() -> None:
    assert Path(__file__).name == "test_employee_record_employment_lifecycle_open.py"


def test_employee_record_brief_names_the_chain_without_runtime() -> None:
    text = _BRIEF.read_text(encoding="utf-8")
    current, history = text.split("## History", 1)
    assert "**OPENED**" in current
    assert "Employee Record & Employment Lifecycle — Contract Gate **PASS**" in current
    assert "Employee Record & Employment Lifecycle — Contract Gate **not PASS**" not in current
    assert "Employment Persistence Schema" in current
    assert "Candidate" in current
    assert "ready_for_employment" in current
    assert "HR handoff" in current
    assert "Employee" in current
    assert "Employment" in current
    assert "Active" in current
    assert "Ended" in current
    assert "does not turn the Candidate row into an Employee" in current
    assert "one Employee may have more than one over time" in current
    assert "existing evidence model" in current
    assert "umowa" in current
    assert "świadectwo pracy" in current
    assert "They are not fields of this domain." in current
    assert "second legalization engine" in current
    assert "The Employee and the evidence remain" in current
    assert "No schema is written." in current
    assert "Feat locked" in current
    assert "not release-ready" in current
    assert "**SUPERSEDED**" in current
    assert "Brief opened" in history
    assert not _RUNTIME.exists()
    hr = _HR.read_text(encoding="utf-8")
    hr_header = hr.split("## History", 1)[0] if "## History" in hr else hr
    assert "**SUPERSEDED**" in hr_header
    assert "employee-record-employment-lifecycle.md" in hr_header
    assert "**QUEUED**" not in hr_header
    assert "not scheduled" in hr_header.lower()
    assert "feat locked" in hr_header.lower()


def test_employee_record_is_the_active_product() -> None:
    queue = _QUEUE.read_text(encoding="utf-8")
    current, history = queue.split("## 8. History", 1)
    assert (
        "**Active Product** | **[Employee Record & Employment Lifecycle](employee-record-employment-lifecycle.md)**"
        in current
    )
    assert (
        "**Active Product** | **[Poland Work Authorization Presets](poland-work-authorization-presets.md)**"
        in history
    )
    assert "Employee Record & Employment Lifecycle — Contract Gate **PASS**" in current
    assert "Employee Record & Employment Lifecycle — Contract Gate **not PASS**" not in current
    assert "Employee Record & Employment Lifecycle — Contract Gate **not PASS**" in history
    assert "Employment Persistence Schema opened" in current
    assert "Employment Runtime opened" in current
    assert "accepted internal_hr handoff creates Employment(preparing)" in current
    assert "HR Legal Eligibility Gate opened on Employment(preparing)" in current
    assert "PASS does not move Employment to active" in current
    assert "superseded" in current.lower()
    assert "Poland Work Authorization Presets Gate **PASS**" in current
    assert "Poland Work Authorization Presets Gate **not PASS**" not in current
    assert "Queue amendment names Employee Record & Employment Lifecycle Active Product." in history
    assert "Feat locked" in _BRIEF.read_text(encoding="utf-8")
