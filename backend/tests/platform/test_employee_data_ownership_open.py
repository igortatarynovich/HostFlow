"""Employee Data ownership is named and no runtime module is created.

Person facts keep the stores that already hold them. The kwestionariusz
is a view. A sufficient set leaves Employment preparing.
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
_QUEUE = _REPO_ROOT / "docs" / "specs" / "tasks" / "sales-to-comms-sequential-queue.md"
_RUNTIME = _REPO_ROOT / "backend" / "app" / "reference" / "employee_data.py"


def test_employee_data_ownership_filename() -> None:
    assert Path(__file__).name == "test_employee_data_ownership_open.py"


def test_employee_data_names_one_owner_and_no_runtime() -> None:
    text = _CONTRACT.read_text(encoding="utf-8")
    assert "## Employee Data ownership" in text
    assert "A person fact has one live owner." in text
    assert "candidates.personal_data.birth_date" in text
    assert "candidates.personal_data.citizenship" in text
    assert "candidates.personal_data.pesel" in text
    assert "platform.identity.address" in text
    assert "WorkforceEmployee.display_name" in text
    assert "not a stored questionnaire" in text
    assert "CandidateHandoffSnapshot.payload" in text
    assert "workforce_hr_verified_fields.verified_value" in text
    assert "candidate_evidence" in text
    assert "`documents` row" in text
    assert "legal_eligibility.v1" in text
    assert "started_on` and `ended_on` stay empty" in text
    assert "is the person-fact set sufficient to continue the HR process" in text
    assert "does not move the Employment to `active`" in text
    assert "It is not the Ready to Start Gate." in text
    assert "Polish document policy are not the source of truth." in text
    assert "No Person table is authorized." in text
    assert "No schema is written." in text
    assert "No runtime module is authorized." in text
    assert "canonical Employment is not yet a table" in text
    assert "Schema Gate **PASS**" not in text
    assert "Runtime Gate **PASS**" not in text
    assert not _RUNTIME.exists()

    brief = _BRIEF.read_text(encoding="utf-8")
    current, history = brief.split("## History", 1)
    assert "Employee Data / kwestionariusz ownership opened" in current
    assert "one live owner per person fact" in current
    assert "The kwestionariusz is a view" in current
    assert "No schema is written." in current
    assert "Feat locked" in current
    assert "not release-ready" in current
    assert "Employee Data ownership opened." in history

    queue = _QUEUE.read_text(encoding="utf-8")
    queue_current = queue.split("## 8. History", 1)[0]
    assert "Employee Data / kwestionariusz ownership opened" in queue_current
    assert "HR Legal Eligibility Gate opened on Employment(preparing)" in queue_current
    assert "PASS does not move Employment to active" in queue_current
