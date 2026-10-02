"""Work Authorization Procedure contract is opened and not passed.

The key is country + procedure type + kod zawodu. No preset row is
written. Effective readiness and evidence reuse stay the Legal
Eligibility default-policy rules. r5_required_set stays the only
writer. Feat stays locked. Runtime is not authorized.
"""

from __future__ import annotations

from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
_CONTRACT = (
    _REPO_ROOT / "docs" / "specs" / "architecture" / "work-authorization-procedure-contract.md"
)
_BRIEF = _REPO_ROOT / "docs" / "specs" / "tasks" / "work-authorization-procedure.md"
_QUEUE = _REPO_ROOT / "docs" / "specs" / "tasks" / "sales-to-comms-sequential-queue.md"
_LE_CONTRACT = _REPO_ROOT / "docs" / "specs" / "architecture" / "legal-eligibility-contract.md"
_MATRIX = _REPO_ROOT / "docs" / "specs" / "architecture" / "legal-eligibility-matrix.md"
_RUNTIME = _REPO_ROOT / "backend" / "app" / "reference" / "work_authorization_procedure.py"
_LE_RUNTIME = _REPO_ROOT / "backend" / "app" / "reference" / "legal_eligibility.py"


def test_work_authorization_procedure_contract_open_filename() -> None:
    assert Path(__file__).name == "test_work_authorization_procedure_contract_open.py"


def test_work_authorization_procedure_names_key_without_preset() -> None:
    text = _CONTRACT.read_text(encoding="utf-8")
    assert "Work Authorization Procedure Contract Gate **PASS**" in text
    assert "**not PASS**" not in text
    assert "country + procedure_type + kod_zawodu" in text
    assert "submission requirements" in text
    assert "Effective submission readiness is required − satisfied − waived." in text
    assert "required − satisfied − waived" in text
    assert "work_authorization_submission" in text
    assert "The procedure adds requirement instances with provenance `work_authorization_submission`." in text
    assert "not an upload slot." in text
    assert "A passport or a driving licence already held as evidence satisfies the new requirement at once." in text
    assert "`procedure_type` is a stable type of procedure." in text
    assert "It is not the name of a document in the package." in text
    assert "Two ways of obtaining the right to work are different procedure types when their submission requirements differ." in text
    assert "`kod_zawodu` is an attribute of this employment and of the vacancy." in text
    assert "`kod_zawodu` is not a source of requirements." in text
    assert "`r5_required_set` then unions those instances" in text
    assert "Union does not create a second evidence object and does not create a second upload slot." in text
    assert "`submission_ready`" in text
    assert "`submission_proceeded_by_override`" in text
    assert "They are not the same state." in text
    assert "It is not a finding that the package is legally sufficient" in text
    assert "A preset is HostFlow default policy. The operator keeps the last decision by an audited override." in text
    assert "If no preset matches this selector, this slice adds no submission requirement." in text
    assert "Polish `country` + `procedure_type` + `kod_zawodu` → requirements is the next slice." in text
    assert "`waive_requirement` lifts one requirement" in text
    assert "`override_readiness` does not mark a requirement satisfied and does not mark it waived" in text
    assert "This file contains no preset row and no Polish document list." in text
    assert "work_authorization_procedure.v1" in text
    assert "No runtime module." in text
    assert "`r5_required_set` stays the sole writer" in text
    assert "Feat stays locked" in text
    assert "Runtime is not authorized" in text
    assert "The Legal Eligibility Matrix Gate is not passed." in text
    assert not _RUNTIME.exists()
    assert not _LE_RUNTIME.exists()


def test_work_authorization_procedure_does_not_extend_legal_eligibility() -> None:
    contract = _LE_CONTRACT.read_text(encoding="utf-8")
    matrix = _MATRIX.read_text(encoding="utf-8")
    assert "It does not take `kod zawodu`." in contract
    assert "Work Authorization Procedure is opened in its own contract and is not defined here." in contract
    assert "Work Authorization Procedure is not opened." not in contract
    assert "Work Authorization Procedure is not opened." not in matrix
    live = matrix.split("## History", 1)[0]
    assert "Legal Eligibility Matrix Gate **not PASS**" in live
    assert "Legal Eligibility Matrix Gate **PASS**" not in live


def test_work_authorization_procedure_is_the_active_product() -> None:
    queue = _QUEUE.read_text(encoding="utf-8")
    current = queue.split("## 8. History", 1)[0]
    history = queue.split("## 8. History", 1)[1]
    assert (
        "**Active Product** | **[Work Authorization Procedure](work-authorization-procedure.md)**"
        in current
    )
    assert (
        "**Active Product** | **[Legal Eligibility](legal-eligibility-requirement-policy.md)**"
        in history
    )
    assert "Work Authorization Procedure Contract Gate **PASS**" in current
    assert "Work Authorization Procedure Contract Gate **not PASS**" not in current
    assert "Work Authorization Procedure Contract Gate **not PASS**" in history
    assert "No preset row" in current
    assert "Legal Eligibility Contract Gate **PASS**" in current
    assert "Legal Eligibility Matrix Gate **not PASS**" in current
    assert "Legal Eligibility Contract Gate **not PASS**" not in current
    assert "feat locked" in current.lower()
    assert "not scheduled" in current.lower()
    brief = _BRIEF.read_text(encoding="utf-8")
    brief_header, brief_history = brief.split("## History", 1)
    assert "**OPENED**" in brief_header
    assert "Work Authorization Procedure Contract Gate **PASS**" in brief_header
    assert "Work Authorization Procedure Contract Gate **not PASS**" not in brief_header
    assert "Work Authorization Procedure Contract Gate **not PASS**" in brief_history
    assert "No preset row" in brief
    assert "country` + `procedure_type` + `kod_zawodu`" in brief
    assert "Feat locked" in brief
    assert "Runtime not authorized" in brief
