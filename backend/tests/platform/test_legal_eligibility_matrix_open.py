"""Legal Eligibility Matrix is opened and not PASS.

The cell key is the contract's closed fact set. visa_d, karta_pobytu,
and empty stay_basis are distinct cells. No outcome id and no document
is assigned. r5_required_set stays the only required-document authority.
"""

from __future__ import annotations

from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
_MATRIX = _REPO_ROOT / "docs" / "specs" / "architecture" / "legal-eligibility-matrix.md"
_CONTRACT = _REPO_ROOT / "docs" / "specs" / "architecture" / "legal-eligibility-contract.md"
_QUEUE = _REPO_ROOT / "docs" / "specs" / "tasks" / "sales-to-comms-sequential-queue.md"
_LEGAL = _REPO_ROOT / "docs" / "specs" / "tasks" / "legal-eligibility-requirement-policy.md"
_HR = _REPO_ROOT / "docs" / "specs" / "tasks" / "recruitment-hr-minimal-handoff.md"
_CI = _REPO_ROOT / ".github" / "workflows" / "backend-ci.yml"


def test_legal_eligibility_matrix_open_filename() -> None:
    assert Path(__file__).name == "test_legal_eligibility_matrix_open.py"


def test_legal_eligibility_matrix_structure_is_opened_not_pass() -> None:
    text = _MATRIX.read_text(encoding="utf-8")
    assert "**Opened**" in text
    assert "Legal Eligibility Matrix Gate **not PASS**" in text
    assert "Legal Eligibility Matrix Gate **PASS**" not in text
    assert "**Accepted**" not in text.split("## Cell", 1)[0]
    order = [
        "1. `stay_basis`",
        "2. `citizenship`",
        "3. `employment_country`",
        "4. `residence_permit_country`",
        "5. `licence_issuing_country`",
        "6. `qualification_jurisdiction`",
    ]
    positions = [text.index(item) for item in order]
    assert positions == sorted(positions)
    assert "exactly these six facts, in this order, and no other key" in text
    assert "`residence_permit_type` is not a key" in text
    assert "does not rewrite `visa_d` as `visa`" in text
    assert "`stay_basis` is never **absent**" in text
    assert "**absent** is not `''`" in text
    assert "| `visa_d` | absent | **unassigned** |" in text
    assert "| `karta_pobytu` | absent | **unassigned** |" in text
    assert "| `''` | absent | **unassigned** |" in text
    assert "matches at most one cell" in text
    assert "does not add a default cell" in text
    assert "It is not an outcome id" in text
    assert "does not receive the required document set" in text
    assert "future outcome schema" in text
    assert "assigned to no cell" in text
    assert "hands RPM nothing" in text
    assert "sole writer of the required set" in text
    assert "require list" in text
    assert "This opening has none" in text
    assert "does not authorize a runtime module" in text
    assert "Feat stays locked" in text
    assert "not scheduled" in text.lower()
    assert "not release-ready" in text.lower()
    assert "No runtime module" in text
    assert not (_REPO_ROOT / "backend" / "app" / "reference" / "legal_eligibility.py").exists()
    contract = _CONTRACT.read_text(encoding="utf-8")
    assert "Legal Eligibility Contract Gate **PASS**" in contract
    assert "**Legal-policy vocabulary**" in contract


def test_legal_eligibility_matrix_open_is_current_and_hr_unscheduled() -> None:
    queue = _QUEUE.read_text(encoding="utf-8")
    current, history = queue.split("## 8. History", 1)
    assert "legal-eligibility-matrix.md" in current
    assert "Legal Eligibility Matrix Gate **not PASS**" in current
    assert "Legal Eligibility Matrix Gate **PASS**" not in current
    assert "Legal Eligibility Contract Gate **PASS**" in current
    assert "Do not assign documents or outcome ids in this opening" in current
    assert "matrix not written" not in current
    assert "not scheduled" in current.lower()
    assert "Legal Eligibility Matrix opened" in history
    assert "Legal Eligibility Contract Gate PASS" in history
    legal = _LEGAL.read_text(encoding="utf-8")
    header = legal.split("## Problem", 1)[0]
    assert "Legal Eligibility Matrix Gate **not PASS**" in header
    assert "Feat locked" in header
    assert "Runtime not authorized" in header
    hr = _HR.read_text(encoding="utf-8")
    hr_header = hr.split("## History", 1)[0] if "## History" in hr else hr
    assert "**QUEUED**" in hr_header
    assert "not scheduled" in hr_header.lower()
    assert "feat locked" in hr_header.lower()
    ci = _CI.read_text(encoding="utf-8")
    assert "test_legal_eligibility_matrix_open.py" in ci
