"""Employment Terms Contract Gate names the agreed-terms snapshot.

The snapshot belongs to one Employment. Vacancy values are a one-time
default. The contract card may display the snapshot and does not rewrite
it. No column is added.
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


def test_employment_terms_contract_gate_filename() -> None:
    assert Path(__file__).name == "test_employment_terms_contract_gate.py"


def test_employment_terms_contract_gate_defines_the_snapshot() -> None:
    text = _CONTRACT.read_text(encoding="utf-8")
    assert "## Employment Terms Contract Gate" in text
    assert "employment_terms.v1" in text
    assert "Employment Terms Contract Gate" in text
    assert "**Outcome:** **PASS**." in text
    assert "A structured magnitude and unit" in text
    assert "`fixed` or `indefinite`" in text
    assert "An empty `hr_employments.ended_on` does not mean `indefinite`." in text
    assert "Present when duration is `fixed`." in text
    assert "explicit none" in text
    assert "vacancies.title" in text
    assert "vacancies.location" in text
    assert "full_time" in text
    assert "sales_order_lines.unit_rate" in text
    assert "does not write the agreed terms." in text
    assert "independent of the current vacancy and independent of the contract document." in text
    assert "leaves `hr_employments.state` at `preparing`" in text
    assert "No column and no JSON in the current model is this snapshot." in text
    assert "Employment Terms Schema is the indicated next slice." in text
    assert "This section does not open that slice" in text
    assert "No schema is written." in text
    assert "No runtime module is authorized." in text
    assert "canonical Employment is not yet a table" in text
    assert "Schema Gate **PASS**" not in text
    assert "Runtime Gate **PASS**" not in text
    assert not _RUNTIME.exists()

    brief = _BRIEF.read_text(encoding="utf-8")
    current, history = brief.split("## History", 1)
    assert "Employment Terms Contract Gate **PASS**" in current
    assert "employment_terms.v1" in current
    assert "Employment Terms Schema is indicated and is not opened." in current
    assert "No schema is written." in current
    assert "Feat locked" in current
    assert "not release-ready" in current
    assert "Employment Terms Contract Gate PASS." in history

    queue = _QUEUE.read_text(encoding="utf-8")
    queue_current = queue.split("## 8. History", 1)[0]
    assert "Employment Terms Contract Gate **PASS** (`employment_terms.v1`)" in queue_current
    assert "Employment Terms discovery opened" in queue_current
    assert "PASS does not move Employment to active" in queue_current
