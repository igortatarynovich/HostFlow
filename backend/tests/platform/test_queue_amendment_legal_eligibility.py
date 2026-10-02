"""Queue amendment names Legal Eligibility after Hiring E2E program close.

History keeps the close stamp (Product DONE, no named successor) and
the later naming stamp and the contract-open stamp. Current
state is Legal Eligibility Contract Gate PASS. The matrix
structure is opened and Matrix Gate is not PASS. Documents are
not assigned. Feat stays locked. min HR stays unscheduled.
visa_d is not mapped onto visa.
"""

from __future__ import annotations

from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
_QUEUE = _REPO_ROOT / "docs" / "specs" / "tasks" / "sales-to-comms-sequential-queue.md"
_LEGAL = _REPO_ROOT / "docs" / "specs" / "tasks" / "legal-eligibility-requirement-policy.md"
_HIRING = _REPO_ROOT / "docs" / "specs" / "tasks" / "hiring-workflow-e2e.md"
_HR = _REPO_ROOT / "docs" / "specs" / "tasks" / "recruitment-hr-minimal-handoff.md"
_CI = _REPO_ROOT / ".github" / "workflows" / "backend-ci.yml"

_CELL = "**Active Product** | **[Legal Eligibility](legal-eligibility-requirement-policy.md)**"


def test_legal_eligibility_amendment_filename() -> None:
    assert Path(__file__).name == "test_queue_amendment_legal_eligibility.py"


def test_legal_eligibility_amendment_names_brief_without_rules() -> None:
    queue = _QUEUE.read_text(encoding="utf-8")
    current = queue.split("## 8. History", 1)[0]
    history = queue.split("## 8. History", 1)[1]
    assert "Queue amendment names Legal Eligibility Active Product" in history
    assert "Product **DONE** with no named successor until amendment" in history
    assert "Hiring E2E Acceptance Gate **not PASS**" in history
    assert _CELL in current
    assert "**Active Product** | **DONE**" not in current
    assert "**Active Product** | **[HE-4](hiring-workflow-e2e.md)**" not in current
    assert "feat locked" in current
    assert "brief opened" in current
    assert "Legal Eligibility Contract Gate **PASS**" in current
    assert "contract opened; not accepted" not in current
    assert "Legal Eligibility Contract Gate **not PASS**" not in current
    assert "contract not opened" not in current
    assert "Legal Eligibility Contract Gate PASS" in history
    assert "Legal Eligibility contract opened" in history
    assert "Legal Eligibility Contract Gate **not PASS**" in history
    assert "Contract not opened" in history
    assert "Do not map `visa_d` onto `visa`" in current
    assert "not a join-graph edge" in current.lower()
    assert "Do not assign documents or outcome ids in this opening" in current
    assert "Legal Eligibility Matrix Gate **not PASS**" in current
    assert "Do not write the matrix in this PR" not in current
    assert "Legal Eligibility Matrix opened" in history
    assert "Legal Eligibility brief opened" in history
    assert "Hiring E2E program close recorded" in current
    assert "Hiring E2E Acceptance Gate **PASS** (`315cb710`)" in current
    assert "not scheduled" in current.lower()
    legal = _LEGAL.read_text(encoding="utf-8")
    legal_header, legal_rest = legal.split("## Problem", 1)
    assert "**OPENED**" in legal_header
    assert "**NAMED**" not in legal_header
    assert "Feat locked" in legal_header
    assert "Legal Eligibility Contract Gate **PASS**" in legal_header
    assert "not accepted" not in legal_header
    assert "Contract not opened" not in legal_header
    assert "Legal Eligibility Matrix Gate **not PASS**" in legal_header
    assert "Matrix empty and not opened" not in legal_header
    assert "Runtime not authorized" in legal_header
    assert "Business rules are not written here" in legal_header
    assert "visa_d" in legal_header
    assert "not mapped onto `visa`" in legal_header
    assert "**QUEUED**" not in legal_header
    assert "**NAMED**" in legal_rest
    assert "It is not the matrix" in legal_rest
    assert "Document-type aliases are not this rule" in legal_rest
    hiring = _HIRING.read_text(encoding="utf-8")
    hiring_current = hiring.split("## History", 1)[0]
    assert "**DONE**" in hiring_current
    assert "**ACTIVE**" not in hiring_current
    assert "legal-eligibility-requirement-policy.md" in hiring_current
    hr = _HR.read_text(encoding="utf-8")
    hr_header = hr.split("## History", 1)[0] if "## History" in hr else hr
    assert "**QUEUED**" in hr_header
    assert "not scheduled" in hr_header.lower()
    assert "feat locked" in hr_header.lower()
    assert "legal-eligibility-requirement-policy.md" in hr_header


def test_legal_eligibility_amendment_named_ci() -> None:
    ci = _CI.read_text(encoding="utf-8")
    assert "Queue Amendment Legal Eligibility" in ci
    assert "test_queue_amendment_legal_eligibility.py" in ci
    assert "le:" in ci
