"""Queue amendment opens HE-4 after Eligibility Composition Gate PASS.

Current Active Product is HE-4. Feat is open. Hiring E2E Acceptance Gate
is not PASS. This stamp does not execute RS-7. min HR stays queued.
"""

from __future__ import annotations

from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
_HIRING = _REPO_ROOT / "docs" / "specs" / "tasks" / "hiring-workflow-e2e.md"
_QUEUE = _REPO_ROOT / "docs" / "specs" / "tasks" / "sales-to-comms-sequential-queue.md"
_AGENTS = _REPO_ROOT / "AGENTS.md"
_GOAL = _REPO_ROOT / "docs" / "specs" / "gates" / "hostflow-v1-release-goal.md"
_HR = _REPO_ROOT / "docs" / "specs" / "tasks" / "recruitment-hr-minimal-handoff.md"
_CI = _REPO_ROOT / ".github" / "workflows" / "backend-ci.yml"


def test_he4_amendment_filename() -> None:
    assert Path(__file__).name == "test_queue_amendment_he4.py"


def test_he4_amendment_opens_feat_without_rs7() -> None:
    queue = _QUEUE.read_text(encoding="utf-8")
    current = queue.split("## 8. History", 1)[0]
    history = queue.split("## 8. History", 1)[1]
    assert "HE-4 Acceptance walk feat opened" in history
    assert "Hiring E2E Acceptance Gate **not PASS**" in history
    assert "HE-4 feat locked" in history
    assert "**Active Product** | **[HE-4](hiring-workflow-e2e.md)**" in current
    assert "**Active Product** | **[HE-3](hiring-workflow-e2e.md)**" not in current
    assert "feat/hiring-e2e-he4-acceptance-walk" in current
    assert "Hiring E2E Acceptance Gate **not PASS**" in current
    assert "Hiring E2E Acceptance Gate **PASS**" not in current
    assert "does not execute RS-7" in current
    assert "8d5a9fef" in current
    hiring = _HIRING.read_text(encoding="utf-8")
    hiring_current = hiring.split("## History", 1)[0]
    hiring_history = hiring.split("## History", 1)[1]
    assert "**ACTIVE**" in hiring_current
    assert "feat/hiring-e2e-he4-acceptance-walk" in hiring_current
    assert "Hiring E2E Acceptance Gate **not PASS**" in hiring_current
    assert "seed_documents_for_ready_for_handoff" in hiring_current
    assert "candidate_evidence_helpers" in hiring_current
    assert "GET /transfer-readiness" in hiring_current
    assert "ready_for_employment.v1" in hiring_current
    assert "HE-4 Acceptance walk feat opened" in hiring_history
    agents = _AGENTS.read_text(encoding="utf-8")
    assert "hiring-workflow-e2e.md" in agents
    assert "HE-4" in agents
    assert "feat/hiring-e2e-he4-acceptance-walk" in agents
    goal = _GOAL.read_text(encoding="utf-8")
    assert "HE-4" in goal
    assert "Hiring E2E Acceptance Gate **not PASS**" in goal


def test_he4_leaves_hr_queued_and_program_close_unstarted() -> None:
    hr = _HR.read_text(encoding="utf-8")
    hr_header = hr.split("## History", 1)[0] if "## History" in hr else hr
    assert "**QUEUED**" in hr_header
    assert "not scheduled" in hr_header.lower()
    assert "feat locked" in hr_header.lower()
    queue = _QUEUE.read_text(encoding="utf-8")
    current = queue.split("## 8. History", 1)[0]
    lowered = current.lower()
    assert "min hr" in lowered or "minimal recruitment" in lowered
    assert "feat locked" in lowered
    assert "program close" in lowered
    assert "not inherited" in lowered or "inherited dr1" in lowered
    hiring = _HIRING.read_text(encoding="utf-8")
    hiring_current = hiring.split("## History", 1)[0]
    assert "program close" in hiring_current.lower()
    assert "not** started" in hiring_current.lower() or "not** started here" in hiring_current.lower() or "**not** started" in hiring_current


def test_he4_amendment_named_ci() -> None:
    ci = _CI.read_text(encoding="utf-8")
    assert "Queue Amendment HE-4" in ci
    assert "test_queue_amendment_he4.py" in ci
    assert "he4:" in ci
