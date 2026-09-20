"""Queue amendment named FP-1; Contract Gate then named FP-2.

History still records the 2026-09-20 FP-1 naming amendment.
Current Active Product is FP-4 (feat open; Operator Publish Gate not PASS)
after Public Serve Gate PASS. Hiring / min HR remain queued. Leftover-store
deletion and RS-3 stay unauthorized.
"""

from __future__ import annotations

from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
_INTAKE = _REPO_ROOT / "docs" / "specs" / "tasks" / "external-intake-forms-publish.md"
_QUEUE = _REPO_ROOT / "docs" / "specs" / "tasks" / "sales-to-comms-sequential-queue.md"
_AGENTS = _REPO_ROOT / "AGENTS.md"
_GOAL = _REPO_ROOT / "docs" / "specs" / "gates" / "hostflow-v1-release-goal.md"
_MAPPING = _REPO_ROOT / "docs" / "specs" / "tasks" / "mapping-authority.md"
_HIRING = _REPO_ROOT / "docs" / "specs" / "tasks" / "hiring-workflow-e2e.md"
_HR = _REPO_ROOT / "docs" / "specs" / "tasks" / "recruitment-hr-minimal-handoff.md"
_CI = _REPO_ROOT / ".github" / "workflows" / "backend-ci.yml"


def test_fp1_amendment_filename() -> None:
    assert Path(__file__).name == "test_queue_amendment_fp1.py"


def test_fp1_amendment_history_then_contract_gate() -> None:
    queue = _QUEUE.read_text(encoding="utf-8")
    current = queue.split("## 8. History", 1)[0]
    history = queue.split("## 8. History", 1)[1]
    assert "Queue amendment names FP-1 Active Product" in history
    assert "**Active Product** | **[FP-4](external-intake-forms-publish.md)**" in current
    assert "feat/forms-publish-fp2-publish-action" in queue
    assert "feat/forms-publish-fp3-public-serve" in current
    assert "feat/forms-publish-fp4-operator-surface" in current
    assert "Publish Action Gate **PASS**" in current
    assert "Public Serve Gate **PASS**" in current
    assert "Operator Publish Gate **not PASS**" in current
    assert "Forms Publish Contract Gate **PASS**" in current or "Forms Publish Contract Gate = PASS" in current
    assert "Active (Product):** **[FP-4](external-intake-forms-publish.md)**" in current
    assert "**Active Product** | **DONE**" not in current
    assert "This stamp does not ship operator UI" in current
    intake = _INTAKE.read_text(encoding="utf-8")
    intake_current = intake.split("## History", 1)[0]
    assert "**ACTIVE**" in intake_current
    assert "FP-1" in intake_current
    assert "FP-2" in intake_current
    assert "FP-3" in intake_current
    assert "FP-4" in intake_current
    assert "feat/forms-publish-fp2-publish-action" in intake_current
    assert "feat/forms-publish-fp3-public-serve" in intake_current
    assert "feat/forms-publish-fp4-operator-surface" in intake_current
    assert "Operator Publish Gate **not PASS**" in intake_current
    assert "Public Serve Gate **PASS**" in intake_current
    assert "Forms Publish Contract Gate **PASS**" in intake_current
    agents = _AGENTS.read_text(encoding="utf-8")
    assert "external-intake-forms-publish.md" in agents
    assert "FP-1" in agents
    assert "FP-2" in agents
    assert "Product = DONE" not in agents
    goal = _GOAL.read_text(encoding="utf-8")
    assert "external-intake-forms-publish.md" in goal
    assert "FP-1" in goal
    assert "FP-2" in goal


def test_fp1_leaves_hiring_hr_queued_and_mapping_done() -> None:
    hiring = _HIRING.read_text(encoding="utf-8")
    hr = _HR.read_text(encoding="utf-8")
    for text in (hiring, hr):
        assert "**QUEUED**" in text
        assert "not scheduled" in text.lower()
        assert "external-intake-forms-publish.md" in text
    mapping = _MAPPING.read_text(encoding="utf-8")
    mapping_current = mapping.split("## History", 1)[0]
    assert "**DONE**" in mapping_current
    assert "**ACTIVE**" not in mapping_current
    assert "FP-1" in mapping_current
    queue = _QUEUE.read_text(encoding="utf-8")
    current = queue.split("## 8. History", 1)[0]
    lowered = current.lower()
    assert "leftover-store deletion" in lowered
    assert "hiring" in lowered
    intake = _INTAKE.read_text(encoding="utf-8")
    assert "**QUEUED**" not in intake.split("## History", 1)[0]


def test_fp1_amendment_named_ci() -> None:
    ci = _CI.read_text(encoding="utf-8")
    assert "Queue Amendment FP-1" in ci
    assert "test_queue_amendment_fp1.py" in ci
    assert "fp1" in ci
