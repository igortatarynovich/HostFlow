"""Mapping Authority program close.

Mapping program DONE. Mapping Consumer Cutover Gate PASS.
Queue amendment names FP-1 Active Product (brief; feat locked).
Does not start leftover-store deletion / Hiring / RS-3.
Architecture stays CLOSED / PASS.
"""

from __future__ import annotations

from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
_BRIEF = _REPO_ROOT / "docs" / "specs" / "tasks" / "mapping-authority.md"
_QUEUE = _REPO_ROOT / "docs" / "specs" / "tasks" / "sales-to-comms-sequential-queue.md"
_AGENTS = _REPO_ROOT / "AGENTS.md"
_GOAL = _REPO_ROOT / "docs" / "specs" / "gates" / "hostflow-v1-release-goal.md"
_HIRING = _REPO_ROOT / "docs" / "specs" / "tasks" / "hiring-workflow-e2e.md"
_INTAKE = _REPO_ROOT / "docs" / "specs" / "tasks" / "external-intake-forms-publish.md"
_HR = _REPO_ROOT / "docs" / "specs" / "tasks" / "recruitment-hr-minimal-handoff.md"
_CI = _REPO_ROOT / ".github" / "workflows" / "backend-ci.yml"


def test_mapping_program_close_filename() -> None:
    assert Path(__file__).name == "test_mapping_authority_program_close.py"


def test_mapping_program_done_records_outcome_and_delta() -> None:
    brief = _BRIEF.read_text(encoding="utf-8")
    current = brief.split("## History", 1)[0]
    assert "**DONE**" in current
    assert "fddadd39" in current
    assert "92206f40" in current
    assert "Program outcome" in current
    assert "Release delta" in current
    assert "four-checks **PASS**" in current or "four-checks PASS" in current
    assert "not** release-ready" in current or "not release-ready" in current.lower()
    assert "Foundation stays" in current
    assert "External Intake" in current
    assert "unlocked" in current.lower()
    assert "leftover-store deletion" in current.lower()
    assert "RS-3" in current
    goal = _GOAL.read_text(encoding="utf-8")
    assert "Mapping Authority (this close)" in goal
    assert "four-checks **PASS**" in goal or "four-checks PASS" in goal
    assert "| **PASS** (RS-3 named)" in goal or "RS-3 named" in goal


def test_mapping_close_product_done_no_named_successor() -> None:
    queue = _QUEUE.read_text(encoding="utf-8")
    current = queue.split("## 8. History", 1)[0]
    history = queue.split("## 8. History", 1)[1]
    assert "Mapping program close recorded" in current or "Mapping program close" in current
    assert "**Active Product** | **[FP-1](external-intake-forms-publish.md)**" in current
    assert "Product **DONE** with no named successor until amendment" in history
    assert "Active (Product):** Mapping program close" not in current
    mapping = _BRIEF.read_text(encoding="utf-8")
    mapping_current = mapping.split("## History", 1)[0]
    assert "**DONE**" in mapping_current
    assert "**ACTIVE**" not in mapping_current
    assert "FP-1" in mapping_current
    agents = _AGENTS.read_text(encoding="utf-8")
    assert "mapping-authority.md" in agents
    assert "FP-1" in agents
    assert "not auto-scheduled" in agents.lower()


def test_mapping_close_leaves_intake_hiring_hr_queued() -> None:
    hiring = _HIRING.read_text(encoding="utf-8")
    hr = _HR.read_text(encoding="utf-8")
    for text in (hiring, hr):
        assert "**QUEUED**" in text
        assert "not scheduled" in text.lower()
    intake = _INTAKE.read_text(encoding="utf-8")
    intake_current = intake.split("## History", 1)[0]
    assert "**ACTIVE**" in intake_current
    assert "FP-1" in intake_current
    queue = _QUEUE.read_text(encoding="utf-8")
    current = queue.split("## 8. History", 1)[0]
    assert "Hiring" in current
    assert "leftover-store deletion" in current.lower()
    mapping = _BRIEF.read_text(encoding="utf-8")
    mapping_current = mapping.split("## History", 1)[0]
    lowered = mapping_current.lower()
    assert "fp-1" in lowered or "external intake" in lowered
    assert "hiring" in lowered
    assert "leftover-store deletion" in lowered
    assert "rs-3" in lowered
    assert "architecture" in lowered


def test_mapping_program_close_named_ci() -> None:
    ci = _CI.read_text(encoding="utf-8")
    assert "Mapping Authority Program Close" in ci
    assert "test_mapping_authority_program_close.py" in ci
    assert "ma_close" in ci or "ma-close" in ci
