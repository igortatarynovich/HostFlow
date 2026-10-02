"""Queue amendment opened HE-4. The acceptance gate is PASS.

History keeps the opening stamp (gate not PASS, RS-7 not executed)
and the later program-close stamp. Current Active Product is Legal
Eligibility. min HR stays queued.
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
    assert "**Active Product** | **[Work Authorization Procedure](work-authorization-procedure.md)**" in current
    assert "**Active Product** | **[Legal Eligibility](legal-eligibility-requirement-policy.md)**" in history
    assert "**Active Product** | **[HE-3](hiring-workflow-e2e.md)**" not in current
    assert "**Active Product** | **[HE-4](hiring-workflow-e2e.md)**" not in current
    assert "Hiring E2E program close recorded" in current
    assert "feat/hiring-e2e-he4-acceptance-walk" in current
    assert "Hiring E2E Acceptance Gate **not PASS**" not in current
    assert "Hiring E2E Acceptance Gate **PASS** (`315cb710`)" in current
    assert "RS-7 **PASS** (`315cb710`)" in current
    assert "8d5a9fef" in current
    hiring = _HIRING.read_text(encoding="utf-8")
    hiring_current = hiring.split("## History", 1)[0]
    hiring_history = hiring.split("## History", 1)[1]
    assert "Hiring E2E program close recorded" in hiring_current or "program close recorded" in hiring_current.lower()
    assert "feat/hiring-e2e-he4-acceptance-walk" in hiring_current
    assert "Hiring E2E Acceptance Gate **not PASS**" not in hiring_current
    assert "Hiring E2E Acceptance Gate **PASS**" in hiring_current
    assert "315cb710" in hiring_current
    assert "legal-eligibility-requirement-policy.md" in hiring_current
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
    assert "Hiring E2E Acceptance Gate **PASS** (`315cb710`)" in goal
    assert "Hiring E2E Acceptance Gate **not PASS**" not in goal


def test_he4_program_close_leaves_hr_unscheduled() -> None:
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
    assert "hiring e2e program close recorded" in lowered
    assert "not scheduled" in lowered
    assert "not inherited" in lowered or "inherited dr1" in lowered
    hiring = _HIRING.read_text(encoding="utf-8")
    hiring_current = hiring.split("## History", 1)[0]
    assert "Goal Completion Gate" in hiring_current
    assert "Outcome: PASS" in hiring_current
    assert "legal-eligibility-requirement-policy.md" in hiring_current
    assert "not** scheduled" in hiring_current.lower() or "**not** scheduled" in hiring_current or "not scheduled" in hiring_current.lower()


def test_he4_amendment_named_ci() -> None:
    ci = _CI.read_text(encoding="utf-8")
    assert "Queue Amendment HE-4" in ci
    assert "test_queue_amendment_he4.py" in ci
    assert "he4:" in ci
