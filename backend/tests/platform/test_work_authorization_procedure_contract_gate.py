"""Work Authorization Procedure Contract Gate PASS.

Evidence is the contract-open. The gate accepts the selector, the
submission-requirement source, and the two package states. It writes
no preset row and it does not unlock feat or runtime.
"""

from __future__ import annotations

from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
_CONTRACT = (
    _REPO_ROOT / "docs" / "specs" / "architecture" / "work-authorization-procedure-contract.md"
)
_BRIEF = _REPO_ROOT / "docs" / "specs" / "tasks" / "work-authorization-procedure.md"
_QUEUE = _REPO_ROOT / "docs" / "specs" / "tasks" / "sales-to-comms-sequential-queue.md"
_AGENTS = _REPO_ROOT / "AGENTS.md"
_GOAL = _REPO_ROOT / "docs" / "specs" / "gates" / "hostflow-v1-release-goal.md"
_ROADMAP = _REPO_ROOT / "docs" / "specs" / "architecture" / "platform-completion-roadmap.md"
_CI = _REPO_ROOT / ".github" / "workflows" / "backend-ci.yml"
_RUNTIME = _REPO_ROOT / "backend" / "app" / "reference" / "work_authorization_procedure.py"


def test_work_authorization_procedure_contract_gate_filename() -> None:
    assert Path(__file__).name == "test_work_authorization_procedure_contract_gate.py"


def test_work_authorization_procedure_contract_gate_pass_accepts_contract() -> None:
    text = _CONTRACT.read_text(encoding="utf-8")
    assert "**Status:** **Accepted**" in text
    assert "Work Authorization Procedure Contract Gate **PASS**" in text
    assert "**not PASS**" not in text
    assert "This slice answers only those two things" in text
    assert "The selector is exactly `country` + `procedure_type` + `kod_zawodu` → one preset." in text
    assert "It is not a document type and it is not an evidence type." in text
    assert "It creates no requirement by itself." in text
    assert "The source of submission requirements is the selected preset, with provenance `work_authorization_submission`." in text
    assert "If no preset matches, this slice adds no submission requirement and does not guess one." in text
    assert "`r5_required_set` stays the sole writer of the final required set." in text
    assert "Existing evidence may satisfy a requirement whatever provenance named it." in text
    assert "There is no duplicate upload." in text
    assert "`waive_requirement` changes effective readiness and does not mutate the policy requirement." in text
    assert "`override_readiness` does not satisfy a requirement and does not waive it." in text
    assert "`submission_ready` and `submission_proceeded_by_override` stay different states." in text
    assert "Readiness means only that the package is ready to submit." in text
    assert "A preset is default policy. The operator keeps an audited override." in text
    assert "This PASS writes no Polish preset row, no document list, no procedure type, and no `kod_zawodu` mapping." in text
    assert "does not change Legal Eligibility, RPM, eligibility, transfer, `ready_for_employment.v1`, HR, or the database schema." in text
    assert "Feat stays locked" in text
    assert "No runtime module." in text
    assert "The Legal Eligibility Matrix Gate is not passed." in text
    assert not _RUNTIME.exists()


def test_work_authorization_procedure_contract_gate_pass_is_current_canon() -> None:
    queue = _QUEUE.read_text(encoding="utf-8")
    current, history = queue.split("## 8. History", 1)
    assert "Work Authorization Procedure Contract Gate **PASS**" in current
    assert "Work Authorization Procedure Contract Gate **not PASS**" not in current
    assert "Work Authorization Procedure Contract Gate **not PASS**" in history
    assert "Legal Eligibility Matrix Gate **not PASS**" in current
    assert "Legal Eligibility Contract Gate **PASS**" in current
    assert "feat locked" in current.lower()
    assert "not scheduled" in current.lower()
    brief = _BRIEF.read_text(encoding="utf-8")
    header, brief_history = brief.split("## History", 1)
    assert "Work Authorization Procedure Contract Gate **PASS**" in header
    assert "Work Authorization Procedure Contract Gate **not PASS**" in brief_history
    assert "No preset row" in header
    assert "Feat locked" in header
    assert "Runtime not authorized" in header
    for path in (_AGENTS, _GOAL, _ROADMAP):
        body = path.read_text(encoding="utf-8")
        assert "Work Authorization Procedure Contract Gate **PASS**" in body
    ci = _CI.read_text(encoding="utf-8")
    assert "test_work_authorization_procedure_contract_gate.py" in ci
