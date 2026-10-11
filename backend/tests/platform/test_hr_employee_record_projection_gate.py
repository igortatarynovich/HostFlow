"""HR Employee Record Projection Contract Gate assigns the record hierarchy.

The hierarchy is where HR looks. Current Process is the other view.
Neither view owns the fact.
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
_BRIEF = (
    _REPO_ROOT / "docs" / "specs" / "tasks" / "employee-record-employment-lifecycle.md"
)
_RUNTIME = _REPO_ROOT / "backend" / "app" / "reference" / "hr_employee_record_projection.py"

_GROUPS = (
    "Dane osobowe",
    "Legalizacja / Prawo do pracy",
    "Kwalifikacje i uprawnienia",
    "Badania i zdolność do pracy",
    "Zatrudnienie",
    "Formalności",
    "Dokumenty",
    "Historia",
)


def test_hr_employee_record_projection_gate_filename() -> None:
    assert Path(__file__).name == "test_hr_employee_record_projection_gate.py"


def test_hr_employee_record_projection_contract_gate_pass() -> None:
    text = _CONTRACT.read_text(encoding="utf-8")
    assert "## HR Employee Record Projection Contract Gate" in text
    assert "**Outcome:** **PASS**." in text
    assert "HR Employee Record Projection Contract Gate **PASS**" in text
    assert "The Contract Gate is not passed." not in text
    assert "It is not a workflow." in text
    assert "The hierarchy is assigned from the nature of the fact." in text
    assert "It is not taken from Recruitment." in text
    assert "It is not taken from `#hr-verification`." in text
    assert "The group order below is an illustration." not in text
    order = text.index("Dane osobowe")
    for group in _GROUPS:
        found = text.index(group)
        assert found >= order
        order = found
    assert "A missing A1 does not become the question Czy ma A1." in text
    assert "The group shows no applicable element, or it shows the status of that process." in text
    assert "Label → canonical value → status → evidence → permitted actions" in text
    assert "Obywatelstwo | Białoruś | Verified | Paszport | Edytuj" in text
    assert "Kod 95 | ważny do 12.06.2028 | Verified | Prawo jazdy | Unieważnij" in text
    assert "The projection does not choose the button." in text
    assert "Employee Record answers what is known about this person and this Employment." in text
    assert "The process surface answers what to do now." in text
    assert "They are two views of the same facts. They are not two data systems." in text
    assert "Verification is not placed inside Dane osobowe or Legalizacja / Prawo do pracy." in text
    assert "`Next action: Verify legal stay → Open`" in text
    assert "that opens the fact in the group that holds it." in text
    assert "A later product rebuilds HR as Employee Record plus Current Process. That rebuild is not this gate." in text
    assert "the HR screen displays every Recruitment question." in text
    assert "Dane osobowe adds no column." in text
    assert "Dokumenty does not copy a document." in text
    assert "The HR Driver Operator Surface is not rewritten." in text
    assert not _RUNTIME.exists()

    brief = _BRIEF.read_text(encoding="utf-8")
    current = brief.split("## History", 1)[0]
    assert "HR Employee Record Projection Contract Gate **PASS**" in current
    assert "hr_employee_record_projection.v1" in current
    assert "The Contract Gate is not passed." not in current
    assert "Not the Legal Eligibility vertical." in current
