"""Legal Eligibility contract-open constraints survive Contract Gate PASS.

The opening stamp stays in history. Current state is PASS.
No fact, token, outcome, or document rule was added for the gate.
"""

from __future__ import annotations

from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
_CONTRACT = _REPO_ROOT / "docs" / "specs" / "architecture" / "legal-eligibility-contract.md"
_QUEUE = _REPO_ROOT / "docs" / "specs" / "tasks" / "sales-to-comms-sequential-queue.md"
_LEGAL = _REPO_ROOT / "docs" / "specs" / "tasks" / "legal-eligibility-requirement-policy.md"


def test_legal_eligibility_contract_open_filename() -> None:
    assert Path(__file__).name == "test_legal_eligibility_contract_open.py"


def test_legal_eligibility_contract_names_four_sections_without_matrix() -> None:
    text = _CONTRACT.read_text(encoding="utf-8")
    assert "**Accepted**" in text
    assert "Legal Eligibility Contract Gate **PASS**" in text
    assert "Legal Eligibility Contract Gate **not PASS**" not in text
    assert "`legal_eligibility.v1`" in text
    assert "No runtime module" in text
    assert "## Facts" in text
    assert "## Vocabulary" in text
    assert "## Authority" in text
    assert "## Expected policy outcomes" in text
    assert "The list above is closed" in text
    assert "`residence_permit_type` is not a fact key" in text
    assert "this contract does not add that column" in text
    assert "**Card vocabulary**" in text
    assert "**Legal-policy vocabulary**" in text
    assert "**Pack tokens**" in text
    assert "They are not aliases of each other" in text
    assert "`stay_basis`" in text
    assert "`visa_d`" in text
    assert "not the pack token `visa`" in text
    assert "`karta_pobytu` is not `card`" in text
    assert "Empty `stay_basis` (`''` in `POLAND_BASIS_VALUES`) is a recorded state" in text
    assert "not a second authority for required documents" in text
    assert "exclusively `r5_required_set`" in text
    assert "sole policy write" in text
    assert "`required_set_override`" in text
    assert "`candidate_default`" in text
    assert "to no fact value" in text
    assert "not assigned to empty `stay_basis`" in text
    assert "`visa_d` vs `karta_pobytu`" in text
    assert "`visa_d` vs empty `stay_basis`" in text
    assert "That pairing is the matrix" in text
    assert "Eligibility, transfer, and `ready_for_employment.v1` are unchanged" in text
    assert "No runtime module" in text
    assert "Feat stays locked" in text
    assert "Minimal Recruitment → HR stays not scheduled" in text
    assert "not release-ready" in text
    assert "`visa_d` is not mapped onto `visa`" in text


def test_legal_eligibility_contract_is_current_and_unaccepted() -> None:
    queue = _QUEUE.read_text(encoding="utf-8")
    current = queue.split("## 8. History", 1)[0]
    assert "legal-eligibility-contract.md" in current
    assert "Legal Eligibility Contract Gate **PASS**" in current
    assert "Legal Eligibility Contract Gate **not PASS**" not in current
    assert "contract opened; not accepted" not in current
    assert "Matrix stays empty" in current or "matrix not written" in current.lower() or "Do not write the matrix" in current
    assert "Runtime not authorized" in current or "runtime not authorized" in current.lower()
    assert "feat locked" in current.lower() or "Feat stays locked" in current
    assert "not scheduled" in current.lower()
    legal = _LEGAL.read_text(encoding="utf-8")
    assert "legal-eligibility-contract.md" in legal
    assert "Not accepted" in legal
    assert "Matrix not written" in legal or "not written" in legal
