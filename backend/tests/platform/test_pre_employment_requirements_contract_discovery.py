"""Pre-employment Requirements discovery and Contract Gate.

A definition comes from policy. An instance belongs to one Employment.
Resolution is a separate axis from applicability. No physical enum is
fixed, and no runtime module is created.
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
_RUNTIME = _REPO_ROOT / "backend" / "app" / "reference" / "pre_employment_requirements.py"


def test_pre_employment_requirements_contract_discovery_filename() -> None:
    assert Path(__file__).name == "test_pre_employment_requirements_contract_discovery.py"


def test_pre_employment_requirements_names_three_readings_without_an_enum() -> None:
    text = _CONTRACT.read_text(encoding="utf-8")
    assert "## Pre-employment Requirements discovery" in text
    assert "## Pre-employment Requirements Contract Gate" in text
    assert "pre_employment_requirements.v1" in text
    assert "**Outcome:** **PASS**." in text
    assert "r5_required_set" in text
    assert "RequirementEvaluationStatus" in text
    assert "RequirementApplicability" in text
    assert "candidate_evidence" in text
    assert "`candidate_evidence` has no `employment_id`." in text
    assert "workforce_onboarding_tasks" in text
    assert "workforce_compliance_states" in text
    assert "workforce_hr_document_control_tasks" in text
    assert "hr_legal_eligibility_gate_decisions" in text
    assert "automation_rules" in text
    assert (
        "is the applicable set of pre-employment requirements defined, "
        "and is every requirement that blocks Ready to Start resolved?"
    ) in text
    assert "Not yet resolved is not `blocking`" in text
    assert (
        "HR Legal Eligibility PASS, Employee Data complete, and Employment Terms complete"
        in text
    )
    assert "They are not three requirements inside it." in text
    assert "does not mark a new Employment's instance `satisfied`." in text
    assert "leaves `hr_employments.state` at `preparing`" in text
    assert "does not move the Employment to `active`." in text
    assert "does not open a Polish pre-employment sequence" in text
    assert "does not fix a physical enum" in text
    assert "This section does not open that slice" in text
    assert "No schema is written." in text
    assert "No runtime module is authorized." in text
    assert "canonical Employment is not yet a table" in text
    assert "Schema Gate **PASS**" not in text
    assert "Runtime Gate **PASS**" not in text
    assert not _RUNTIME.exists()

    brief = _BRIEF.read_text(encoding="utf-8")
    current, history = brief.split("## History", 1)
    assert "Pre-employment Requirements discovery opened" in current
    assert "Pre-employment Requirements Contract Gate **PASS**" in current
    assert "pre_employment_requirements.v1" in current
    assert "No schema is written." in current
    assert "Feat locked" in current
    assert "not release-ready" in current
    assert "Pre-employment Requirements discovery opened." in history

    queue = _QUEUE.read_text(encoding="utf-8")
    queue_current = queue.split("## 8. History", 1)[0]
    assert (
        "Pre-employment Requirements Contract Gate **PASS** (`pre_employment_requirements.v1`)"
        in queue_current
    )
    assert "Employment Terms Runtime **PASS**" in queue_current
    assert "PASS does not move Employment to active" in queue_current
