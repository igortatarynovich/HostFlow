"""Requirement Policy program close / Mapping Authority schedule.

RPM program DONE. Active Product = MA-1 (brief; feat locked).
Does not open Mapping feat. External Intake / Hiring / min HR remain queued.
"""

from __future__ import annotations

from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
_BRIEF = _REPO_ROOT / "docs" / "specs" / "tasks" / "requirement-policy-management.md"
_MAPPING = _REPO_ROOT / "docs" / "specs" / "tasks" / "mapping-authority.md"
_QUEUE = _REPO_ROOT / "docs" / "specs" / "tasks" / "sales-to-comms-sequential-queue.md"
_AGENTS = _REPO_ROOT / "AGENTS.md"
_GOAL = _REPO_ROOT / "docs" / "specs" / "gates" / "hostflow-v1-release-goal.md"
_HIRING = _REPO_ROOT / "docs" / "specs" / "tasks" / "hiring-workflow-e2e.md"
_INTAKE = _REPO_ROOT / "docs" / "specs" / "tasks" / "external-intake-forms-publish.md"
_HR = _REPO_ROOT / "docs" / "specs" / "tasks" / "recruitment-hr-minimal-handoff.md"
_CI = _REPO_ROOT / ".github" / "workflows" / "backend-ci.yml"


def test_rpm_program_close_filename() -> None:
    assert Path(__file__).name == "test_requirement_policy_program_close.py"


def test_rpm_program_done_records_outcome_and_delta() -> None:
    brief = _BRIEF.read_text(encoding="utf-8")
    assert "**DONE**" in brief
    assert "918274d1" in brief
    assert "Program outcome" in brief
    assert "Release delta" in brief
    assert "four-checks **PASS**" in brief or "four-checks PASS" in brief
    assert "not** release-ready" in brief or "not release-ready" in brief.lower()
    assert "Foundation stays" in brief
    assert "Hiring E2E" in brief
    assert "unlocked" in brief.lower()
    goal = _GOAL.read_text(encoding="utf-8")
    assert "Requirement Policy Management (this close)" in goal
    assert "four-checks **PASS**" in goal or "four-checks PASS" in goal


def test_rpm_close_names_ma1_active_feat_locked() -> None:
    queue = _QUEUE.read_text(encoding="utf-8")
    assert "**Active Product** | **[MA-1](mapping-authority.md)**" in queue
    assert "Active (Product):** **[MA-1](mapping-authority.md)**" in queue
    assert "feat locked this PR" in queue
    assert "Active (Product):** **Consumer Cutover Gate" not in queue
    mapping = _MAPPING.read_text(encoding="utf-8")
    assert "**ACTIVE**" in mapping
    assert "MA-1" in mapping
    assert "feat locked" in mapping.lower()
    assert "Contract Gate not PASS" in mapping or "does **not** mark the Contract Gate PASS" in mapping
    agents = _AGENTS.read_text(encoding="utf-8")
    assert "mapping-authority.md" in agents
    assert "MA-1" in agents


def test_rpm_close_leaves_intake_hiring_hr_queued() -> None:
    hiring = _HIRING.read_text(encoding="utf-8")
    intake = _INTAKE.read_text(encoding="utf-8")
    hr = _HR.read_text(encoding="utf-8")
    for text in (hiring, intake, hr):
        assert "**QUEUED**" in text
        assert "not scheduled" in text.lower()
        assert "MA-1" in text
    queue = _QUEUE.read_text(encoding="utf-8")
    assert "unlocked, **not** scheduled" in queue or "unlocked, not scheduled" in queue.lower()
    assert "External Intake" in queue
    mapping = _MAPPING.read_text(encoding="utf-8")
    assert "feat/mapping-authority" in mapping
    assert "none — feat locked" in mapping or "Feat not opened" in mapping


def test_rpm_program_close_named_ci() -> None:
    ci = _CI.read_text(encoding="utf-8")
    assert "Requirement Policy Program Close" in ci
    assert "test_requirement_policy_program_close.py" in ci
    assert "rpm_close" in ci or "rpm-close" in ci
