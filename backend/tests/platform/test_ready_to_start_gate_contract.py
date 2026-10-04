"""Ready to Start Gate Contract aggregates four upstream readings.

The outcome is pass or blocked. The contract does not choose a store
and does not move Employment to active.
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
_RUNTIME = _REPO_ROOT / "backend" / "app" / "reference" / "ready_to_start.py"


def test_ready_to_start_gate_contract_filename() -> None:
    assert Path(__file__).name == "test_ready_to_start_gate_contract.py"


def test_ready_to_start_gate_contract_aggregates_four_readings() -> None:
    text = _CONTRACT.read_text(encoding="utf-8")
    assert "## Ready to Start Gate Contract" in text
    assert "ready_to_start.v1" in text
    assert "**Outcome:** **PASS**." in text
    assert "decision_is_current" in text
    assert "evaluate_employment_terms" in text
    assert "evaluate_pre_employment_requirements" in text
    assert "The person-fact set of Employee Data ownership is complete" in text
    assert "It does not re-decide legal eligibility, person facts, agreed terms, or requirement resolution." in text
    assert "The outcome of this gate is `pass` or `blocked`." in text
    assert "A legal `fail` stays the outcome of the legal gate." in text
    assert "They are not Employment states." in text
    assert "employment_id" in text
    assert "the blocked reasons" in text
    assert "does not decide whether that record is its own table." in text
    assert "makes that `pass` stale." in text
    assert "A stale `pass` is not that permission." in text
    assert "does not perform the transition." in text
    assert "leaves `hr_employments.state` at `preparing`" in text
    assert "Activation Runtime" in text
    assert "This section does not open that slice" in text
    assert "No schema is written." in text
    assert "No runtime module is authorized." in text
    assert "canonical Employment is not yet a table" in text
    assert "does not open a Polish pre-employment sequence" in text
    assert "Schema Gate **PASS**" not in text
    assert "Runtime Gate **PASS**" not in text
    assert not _RUNTIME.exists()

    brief = _BRIEF.read_text(encoding="utf-8")
    current, history = brief.split("## History", 1)
    assert "Ready to Start Gate Contract **PASS** (`ready_to_start.v1`)" in current
    assert "does not perform `preparing → active`" in current
    assert "No schema is written." in current
    assert "Feat locked" in current
    assert "not release-ready" in current
    assert "Ready to Start Gate Contract PASS." in history

    queue = _QUEUE.read_text(encoding="utf-8")
    queue_current = queue.split("## 8. History", 1)[0]
    assert "Ready to Start Gate Contract **PASS** (`ready_to_start.v1`)" in queue_current
    assert "Pre-employment Requirements Runtime **PASS**" in queue_current
    assert "PASS does not move Employment to active" in queue_current
