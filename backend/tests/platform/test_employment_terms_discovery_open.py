"""Employment Terms discovery names current owners and adds no column.

Agreed terms belong to one Employment. The contract card represents
them. Vacancy values are the offer. Complete and incomplete leave
Employment preparing.
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
_RUNTIME = _REPO_ROOT / "backend" / "app" / "reference" / "employment_terms.py"


def test_employment_terms_discovery_filename() -> None:
    assert Path(__file__).name == "test_employment_terms_discovery_open.py"


def test_employment_terms_discovery_names_owners_without_schema() -> None:
    text = _CONTRACT.read_text(encoding="utf-8")
    assert "## Employment Terms discovery" in text
    assert "hr_employments.client_company_id" in text
    assert "There is no `hr_employments.company_id`." in text
    assert "workforce_employees.own_company_id" in text
    assert "hr_employments.vacancy_id" in text
    assert "hr_employments.started_on" in text
    assert "hr_employments.ended_on" in text
    assert "workforce_employments.contract_type" in text
    assert "workforce_employments.schedule" in text
    assert "workforce_employments.rate_model" in text
    assert "workforce_employments.probation_end" in text
    assert "vacancies.title" in text
    assert "vacancies.location" in text
    assert "vacancies.salary_from" in text
    assert "sales_order_lines.unit_rate" in text
    assert "are the terms of this Employment defined enough to continue to pre-employment requirements?" in text
    assert "both leave `hr_employments.state` at `preparing`" in text
    assert "Neither moves the Employment to `active`." in text
    assert "This section adds no position column" in text
    assert "This section adds no FTE column" in text
    assert "This section adds no workplace column" in text
    assert "This section adds no salary column" in text
    assert "No schema is written." in text
    assert "No runtime module is authorized." in text
    assert "canonical Employment is not yet a table" in text
    assert "Schema Gate **PASS**" not in text
    assert "Runtime Gate **PASS**" not in text
    assert not _RUNTIME.exists()

    brief = _BRIEF.read_text(encoding="utf-8")
    current, history = brief.split("## History", 1)
    assert "Employment Terms discovery opened" in current
    assert "client_company_id" in current
    assert "No schema is written." in current
    assert "Feat locked" in current
    assert "not release-ready" in current
    assert "Employment Terms discovery opened." in history

    queue = _QUEUE.read_text(encoding="utf-8")
    queue_current = queue.split("## 8. History", 1)[0]
    assert "Employment Terms discovery opened" in queue_current
    assert "Employee Data / kwestionariusz ownership opened" in queue_current
    assert "PASS does not move Employment to active" in queue_current
