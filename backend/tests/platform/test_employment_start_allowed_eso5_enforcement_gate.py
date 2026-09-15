"""Slice 4 gate: ESO-5 Confirm requires start_allowed; no mint-on-confirm.

Named gate: employment-start-allowed-eso5-enforcement-gate
"""

from __future__ import annotations

import ast
from pathlib import Path

from backend.app.reference.employment_started import (
    DECISION_ALREADY_STARTED,
    DECISION_BLOCKED,
    DECISION_STARTED,
    apply_employment_started_v1,
    evaluate_employment_started_v1,
)
from backend.app.reference.ready_for_employment import CONTRACT_ID

_REPO_ROOT = Path(__file__).resolve().parents[3]
_BRIEF = _REPO_ROOT / "docs" / "specs" / "tasks" / "employment-start-allowed-eso5-enforcement.md"
_STARTED = _REPO_ROOT / "backend" / "app" / "reference" / "employment_started.py"
_ORCH = _REPO_ROOT / "backend" / "app" / "services" / "employment_started_orchestrator.py"
_API = _REPO_ROOT / "backend" / "app" / "api" / "v1" / "handoffs.py"
_CI = _REPO_ROOT / ".github" / "workflows" / "backend-ci.yml"
_ARCH_SA = _REPO_ROOT / "docs" / "specs" / "architecture" / "employment-start-allowed.md"


def _pkg() -> dict:
    return {
        "contract_id": CONTRACT_ID,
        "tenant_id": "11111111-1111-1111-1111-111111111111",
        "person": {
            "person_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            "identity_facts": {"citizenship": "PL", "first_name": "Ada"},
        },
        "target_work": {
            "vacancy_id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
            "employer_id": "cccccccc-cccc-cccc-cccc-cccccccccccc",
            "employment_country": "PL",
            "start_date": "2026-09-15",
        },
        "recruitment_facts": {"language_ok": True},
        "evidence": {"source": "meta_lead", "document_ids": []},
        "fits_decision": {
            "decision": "fits",
            "decided_at": "2026-09-09T10:00:00+00:00",
            "actor_id": "dddddddd-dddd-dddd-dddd-dddddddddddd",
        },
        "context_refs": {"application_id": "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee"},
    }


def test_slice4_gate_filename() -> None:
    assert Path(__file__).name == "test_employment_start_allowed_eso5_enforcement_gate.py"


def test_slice4_brief_locks_decision() -> None:
    text = _BRIEF.read_text(encoding="utf-8")
    assert "Slice 4" in text
    assert "start_allowed=true" in text
    assert "Full Spine" in text
    assert "mint-on-confirm" in text.lower() or "Mint-on-confirm" in text


def test_confirm_blocked_without_start_allowed() -> None:
    out = apply_employment_started_v1(
        package=_pkg(),
        handoff_status="accepted",
        employee_id="emp-1",
        start_confirmation={"confirmed": True},
        start_allowed=False,
    )
    assert out["decision"] == DECISION_BLOCKED
    assert out["started"] is False
    assert any(b["code"] == "start_allowed_required" for b in out["blockers"])


def test_confirm_allowed_when_start_allowed_true() -> None:
    out = apply_employment_started_v1(
        package=_pkg(),
        handoff_status="accepted",
        employee_id="emp-1",
        start_confirmation={"confirmed": True},
        start_allowed=True,
    )
    assert out["decision"] == DECISION_STARTED
    assert out["started"] is True
    assert out["mint_employee"] is False


def test_already_started_replay_without_admit() -> None:
    prior = {
        "start_date": "2026-09-15",
        "employment_context": {
            "employment_country": "PL",
            "employer_id": "cccccccc-cccc-cccc-cccc-cccccccccccc",
            "vacancy_id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
        },
        "event_id": "evt-1",
    }
    out = apply_employment_started_v1(
        package=_pkg(),
        handoff_status="accepted",
        employee_id="emp-1",
        prior_start=prior,
        start_confirmation={"confirmed": True},
        start_allowed=False,
    )
    assert out["decision"] == DECISION_ALREADY_STARTED
    assert out["idempotent_replay"] is True
    assert out["start_event_emitted"] is False


def test_no_employee_blocked_not_mint() -> None:
    out = evaluate_employment_started_v1(
        package=_pkg(),
        handoff_status="accepted",
        ready_to_create_employee=True,
        start_allowed=True,
        start_confirmation={"confirmed": True},
    )
    assert out["decision"] == DECISION_BLOCKED
    assert out["mint_employee"] is False
    assert any(b["code"] == "employee_required" for b in out["blockers"])


def test_orchestrator_no_mint_and_uses_admit() -> None:
    orch = _ORCH.read_text(encoding="utf-8")
    assert "handoff_from_candidate" not in orch
    assert "evaluate_start_allowed_for_handoff" in orch
    assert "mint_on_confirm_forbidden" in orch
    tree = ast.parse(orch)
    # No Call to handoff_from_candidate
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr == "handoff_from_candidate":
            raise AssertionError("orchestrator must not reference handoff_from_candidate")


def test_api_route_present() -> None:
    api = _API.read_text(encoding="utf-8")
    assert '"/{{handoff_id}}/employment-started"' in api or "/{handoff_id}/employment-started" in api
    assert "ensure_employee" in api


def test_architecture_requires_start_allowed() -> None:
    text = _ARCH_SA.read_text(encoding="utf-8")
    assert "ESO-5 requires" in text or "requires `start_allowed`" in text


def test_ci_registers_enforcement_gate() -> None:
    ci = _CI.read_text(encoding="utf-8")
    assert "employment-start-allowed-eso5-enforcement-gate" in ci
    assert "test_employment_start_allowed_eso5_enforcement_gate.py" in ci
    assert "test_employment_started_gate.py" in ci
