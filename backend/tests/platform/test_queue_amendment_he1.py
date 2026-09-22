"""Queue amendment named HE-1 after External Intake program close.

History records the stamp: Active Product HE-1, contract gate NOT PASS.
Current Active Product is still HE-1. Hiring Acceptance Contract Gate is PASS.
min HR / leftover-store deletion / RS-3 stay unauthorized.
FP-5 PASS is not Release Acceptance PASS.
"""

from __future__ import annotations

from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
_HIRING = _REPO_ROOT / "docs" / "specs" / "tasks" / "hiring-workflow-e2e.md"
_QUEUE = _REPO_ROOT / "docs" / "specs" / "tasks" / "sales-to-comms-sequential-queue.md"
_AGENTS = _REPO_ROOT / "AGENTS.md"
_GOAL = _REPO_ROOT / "docs" / "specs" / "gates" / "hostflow-v1-release-goal.md"
_INTAKE = _REPO_ROOT / "docs" / "specs" / "tasks" / "external-intake-forms-publish.md"
_HR = _REPO_ROOT / "docs" / "specs" / "tasks" / "recruitment-hr-minimal-handoff.md"
_MAPPING = _REPO_ROOT / "docs" / "specs" / "tasks" / "mapping-authority.md"
_CI = _REPO_ROOT / ".github" / "workflows" / "backend-ci.yml"


def test_he1_amendment_filename() -> None:
    assert Path(__file__).name == "test_queue_amendment_he1.py"


def test_he1_amendment_history_then_current() -> None:
    queue = _QUEUE.read_text(encoding="utf-8")
    current = queue.split("## 8. History", 1)[0]
    history = queue.split("## 8. History", 1)[1]
    assert "Queue amendment names HE-1 Active Product" in history
    assert "Hiring Acceptance Contract Gate **not PASS**" in history
    assert "Do not open HE-1 contract seal" in history
    assert "**Active Product** | **[HE-1](hiring-workflow-e2e.md)**" in history or (
        "Active Product stays **[HE-1]" in history
    )
    assert "**Active Product** | **DONE**" not in current
    assert "Active (Product):** **DONE**" not in current
    assert "Hiring Acceptance Contract Gate **PASS**" in current
    assert "Hiring Acceptance Contract Gate **not PASS**" not in current
    assert "Do not open HE-1 contract seal" not in current
    hiring = _HIRING.read_text(encoding="utf-8")
    hiring_current = hiring.split("## History", 1)[0]
    hiring_history = hiring.split("## History", 1)[1]
    assert "**ACTIVE**" in hiring_current
    assert hiring_current.split("**Status:**", 1)[1].split("\n", 1)[0].count("**QUEUED**") == 0
    assert "Hiring Acceptance Contract Gate **PASS**" in hiring_current
    assert "Hiring Acceptance Contract Gate **not PASS**" not in hiring_current
    assert "Do not open HE-1 contract seal" not in hiring_current
    assert "Do not open HE-1 contract seal" in hiring_history
    agents = _AGENTS.read_text(encoding="utf-8")
    assert "hiring-workflow-e2e.md" in agents
    assert "HE-1" in agents
    assert "HE-2" in agents
    goal = _GOAL.read_text(encoding="utf-8")
    assert "hiring-workflow-e2e.md" in goal
    assert "HE-1" in goal


def test_he1_leaves_hr_queued_and_intake_mapping_done() -> None:
    hr = _HR.read_text(encoding="utf-8")
    hr_header = hr.split("## History", 1)[0] if "## History" in hr else hr
    assert "**QUEUED**" in hr_header
    assert "not scheduled" in hr_header.lower()
    intake = _INTAKE.read_text(encoding="utf-8")
    intake_current = intake.split("## History", 1)[0]
    assert "**DONE**" in intake_current
    assert "**ACTIVE**" not in intake_current
    mapping = _MAPPING.read_text(encoding="utf-8")
    mapping_current = mapping.split("## History", 1)[0]
    assert "**DONE**" in mapping_current
    assert "**ACTIVE**" not in mapping_current
    queue = _QUEUE.read_text(encoding="utf-8")
    current = queue.split("## 8. History", 1)[0]
    lowered = current.lower()
    assert "leftover-store deletion" in lowered
    assert "min hr" in lowered or "minimal recruitment" in lowered
    assert "release acceptance" in lowered or "rs-2" in lowered


def test_he1_amendment_named_ci() -> None:
    ci = _CI.read_text(encoding="utf-8")
    assert "Queue Amendment HE-1" in ci
    assert "test_queue_amendment_he1.py" in ci
    assert "he1" in ci
