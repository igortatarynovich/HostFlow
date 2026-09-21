"""External Intake program close.

External Intake program DONE. External Intake Acceptance Gate PASS.
Product DONE with no named successor until amendment.
Does not start Hiring / leftover-store deletion / RS-3.
FP-5 PASS is not Release Acceptance PASS.
"""

from __future__ import annotations

from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
_BRIEF = _REPO_ROOT / "docs" / "specs" / "tasks" / "external-intake-forms-publish.md"
_QUEUE = _REPO_ROOT / "docs" / "specs" / "tasks" / "sales-to-comms-sequential-queue.md"
_AGENTS = _REPO_ROOT / "AGENTS.md"
_GOAL = _REPO_ROOT / "docs" / "specs" / "gates" / "hostflow-v1-release-goal.md"
_HIRING = _REPO_ROOT / "docs" / "specs" / "tasks" / "hiring-workflow-e2e.md"
_HR = _REPO_ROOT / "docs" / "specs" / "tasks" / "recruitment-hr-minimal-handoff.md"
_MAPPING = _REPO_ROOT / "docs" / "specs" / "tasks" / "mapping-authority.md"
_CI = _REPO_ROOT / ".github" / "workflows" / "backend-ci.yml"


def test_external_intake_program_close_filename() -> None:
    assert Path(__file__).name == "test_external_intake_program_close.py"


def test_external_intake_program_done_records_outcome_and_delta() -> None:
    brief = _BRIEF.read_text(encoding="utf-8")
    current = brief.split("## History", 1)[0]
    assert "**DONE**" in current
    assert "4f454556" in current
    assert "Program outcome" in current
    assert "Release delta" in current
    assert "live public URL" in current.lower() or "live url" in current.lower()
    assert "stranger" in current.lower()
    assert "without auth" in current.lower() or "no auth" in current.lower()
    assert "production" in current.lower()
    assert "workspace" in current.lower()
    assert "not** release-ready" in current or "not release-ready" in current.lower()
    assert "Foundation stays" in current
    assert "Hiring E2E" in current
    assert "not** Release Acceptance PASS" in current or "not Release Acceptance PASS" in current
    assert "RS-2" in current
    goal = _GOAL.read_text(encoding="utf-8")
    assert "External Intake / Forms Publish (this close)" in goal
    assert "not** Release Acceptance PASS" in goal or "Not** Release Acceptance PASS" in goal
    assert "4f454556" in goal


def test_external_intake_close_product_done_no_named_successor() -> None:
    queue = _QUEUE.read_text(encoding="utf-8")
    current = queue.split("## 8. History", 1)[0]
    history = queue.split("## 8. History", 1)[1]
    assert "External Intake program close" in current
    assert "**Active Product** | **DONE**" in current
    assert "no named successor until amendment" in current.lower()
    assert "External Intake program close." in history or "External Intake program close**" in history
    assert "Active (Product):** **DONE**" in current
    assert "**Active Product** | External Intake program close" not in current
    intake = _BRIEF.read_text(encoding="utf-8")
    intake_current = intake.split("## History", 1)[0]
    assert "**DONE**" in intake_current
    assert "**ACTIVE**" not in intake_current
    agents = _AGENTS.read_text(encoding="utf-8")
    assert "external-intake-forms-publish.md" in agents
    assert "Product = DONE" in agents
    assert "no named successor" in agents.lower()


def test_external_intake_close_leaves_hiring_hr_queued() -> None:
    hiring = _HIRING.read_text(encoding="utf-8")
    hr = _HR.read_text(encoding="utf-8")
    for text in (hiring, hr):
        header = text.split("## History", 1)[0] if "## History" in text else text
        assert "**QUEUED**" in header
        assert "not scheduled" in header.lower()
        assert "Hiring" in hiring
    mapping = _MAPPING.read_text(encoding="utf-8")
    mapping_current = mapping.split("## History", 1)[0]
    assert "**DONE**" in mapping_current
    queue = _QUEUE.read_text(encoding="utf-8")
    current = queue.split("## 8. History", 1)[0]
    lowered = current.lower()
    assert "hiring" in lowered
    assert "leftover-store deletion" in lowered
    assert "release acceptance" in lowered or "rs-2" in lowered


def test_external_intake_program_close_named_ci() -> None:
    ci = _CI.read_text(encoding="utf-8")
    assert "External Intake Program Close" in ci
    assert "test_external_intake_program_close.py" in ci
    assert "fp_close" in ci or "fp-close" in ci
