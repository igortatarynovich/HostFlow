"""HR Employee Record Projection names two readings of one fact.

The assigned hierarchy and the Contract Gate live in the gate test.
This file keeps the separation from ownership and from a second store.
"""

from __future__ import annotations

from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
_CONTRACT = (
    _REPO_ROOT
    / "docs"
    / "specs"
    / "architecture"
    / "hr-employee-record-projection.md"
)
_RUNTIME = _REPO_ROOT / "backend" / "app" / "reference" / "hr_employee_record_projection.py"

_ACCEPTANCE = (
    "One canonical fact may have different projections. "
    "Recruitment presents it as an element of a conditional decision flow. "
    "HR presents it as an element of a stable hierarchical employee record. "
    "Neither projection owns the fact. Neither projection determines policy."
)


def test_hr_employee_record_projection_filename() -> None:
    assert Path(__file__).name == "test_hr_employee_record_projection_open.py"


def test_hr_employee_record_projection_keeps_the_fact_shared() -> None:
    text = _CONTRACT.read_text(encoding="utf-8")
    assert "hr_employee_record_projection.v1" in text
    assert _ACCEPTANCE in text
    assert "Canonical Fact Authority is where the fact lives." in text
    assert "Process policy is why the process reads the fact." in text
    assert "Projection is how the module shows the fact." in text
    assert "That question sequence does not determine the HR screen." in text
    assert "This slice does not amend `legal_eligibility.v1`." in text
    assert "This slice does not implement legal evidence." in text
    assert "No schema is written." in text
    assert "No runtime module is authorized." in text
    assert "No `canonical_facts` store is authorized." in text
    assert not _RUNTIME.exists()
