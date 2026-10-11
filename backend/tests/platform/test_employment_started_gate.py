"""Employment Started Gate (ESO-5).

Physical first day at work. Employee created ≠ Started.
Formalize complete ≠ Started. Explicit date + context. Idempotent audit.
"""

from __future__ import annotations

import ast
from pathlib import Path

from backend.app.core.audit_events import AuditEventType
from backend.app.reference.employment_started import (
    ACTION_CONFIRM,
    ARCH_REL,
    AUDIT_EVENT_PHYSICAL_START,
    DECISION_ALREADY_STARTED,
    DECISION_BLOCKED,
    DECISION_NOT_STARTED,
    DECISION_REJECTED_CONFIRM,
    DECISION_STARTED,
    DECISION_VALUES,
    ESO_BRIEF_REL,
    EVALUATE_API,
    FACT_START_DATE,
    FORMALIZE_ARCH_REL,
    POLICY_ID,
    apply_employment_started_v1,
    evaluate_employment_started_v1,
)
from backend.app.reference.ready_for_employment import CONTRACT_ID

_REPO_ROOT = Path(__file__).resolve().parents[3]
_ARCH = _REPO_ROOT / ARCH_REL
_ESO = _REPO_ROOT / ESO_BRIEF_REL
_FORM = _REPO_ROOT / FORMALIZE_ARCH_REL
_CI = _REPO_ROOT / ".github" / "workflows" / "backend-ci.yml"
_MODULE = _REPO_ROOT / "backend" / "app" / "reference" / "employment_started.py"
_ORCH = _REPO_ROOT / "backend" / "app" / "services" / "employment_started_orchestrator.py"
_HANDOFFS_API = _REPO_ROOT / "backend" / "app" / "api" / "v1" / "handoffs.py"
_RSO_ORCH = (
    _REPO_ROOT
    / "backend"
    / "app"
    / "modules"
    / "recruitment"
    / "services"
    / "ready_for_employment_orchestrator.py"
)


def _pkg(*, start_date: str | None = "2026-09-15", extra_target: dict | None = None) -> dict:
    target = {
        "vacancy_id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
        "employer_id": "cccccccc-cccc-cccc-cccc-cccccccccccc",
        "employment_country": "PL",
    }
    if start_date:
        target["start_date"] = start_date
    if extra_target:
        target.update(extra_target)
    return {
        "contract_id": CONTRACT_ID,
        "tenant_id": "11111111-1111-1111-1111-111111111111",
        "person": {
            "person_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            "identity_facts": {"citizenship": "PL", "first_name": "Ada"},
        },
        "target_work": target,
        "recruitment_facts": {"language_ok": True},
        "evidence": {"source": "meta_lead", "document_ids": []},
        "fits_decision": {
            "decision": "fits",
            "decided_at": "2026-09-09T10:00:00+00:00",
            "actor_id": "dddddddd-dddd-dddd-dddd-dddddddddddd",
        },
        "context_refs": {"application_id": "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee"},
    }


def test_eso5_gate_filename() -> None:
    assert Path(__file__).name == "test_employment_started_gate.py"


def test_eso5_policy_id_and_apis() -> None:
    assert POLICY_ID == "employment_started.v1"
    assert EVALUATE_API == "evaluate_employment_started_v1"
    assert AUDIT_EVENT_PHYSICAL_START == "employee_physical_start"
    assert AuditEventType.employee_physical_start.value == AUDIT_EVENT_PHYSICAL_START
    assert AuditEventType.employment_started.value == "employment_started"
    assert AUDIT_EVENT_PHYSICAL_START != AuditEventType.employment_started.value
    assert "def evaluate_employment_started_v1(" in _MODULE.read_text(encoding="utf-8")
    assert DECISION_VALUES == (
        DECISION_STARTED,
        DECISION_ALREADY_STARTED,
        DECISION_NOT_STARTED,
        DECISION_BLOCKED,
        DECISION_REJECTED_CONFIRM,
    )


def test_eso5_employee_created_does_not_imply_started() -> None:
    out = evaluate_employment_started_v1(
        package=_pkg(),
        handoff_status="accepted",
        employee_id="emp-1",
        ready_to_create_employee=True,
    )
    assert out["employee_created"] is True
    assert out["started"] is False
    assert out["decision"] == DECISION_NOT_STARTED
    assert out["employee_created_implies_started"] is False
    missing = {m["code"] for m in out["active_missing"]}
    assert ACTION_CONFIRM in missing
    assert FACT_START_DATE not in missing  # known from package — do not re-ask


def test_eso5_formalize_complete_does_not_auto_start() -> None:
    out = evaluate_employment_started_v1(
        package=_pkg(),
        handoff_status="accepted",
        ready_to_create_employee=True,
    )
    assert out["ready_to_create_employee"] is True
    assert out["mint_employee"] is True
    assert out["started"] is False
    assert out["start_event_emitted"] is False
    assert out["formalization_complete_implies_started"] is False
    assert out["decision"] == DECISION_NOT_STARTED


def test_eso5_explicit_confirm_emits_started_and_event() -> None:
    out = apply_employment_started_v1(
        package=_pkg(),
        handoff_status="accepted",
        employee_id="emp-1",
        ready_to_create_employee=True,
        start_confirmation={"confirmed": True},
    )
    assert out["decision"] == DECISION_STARTED
    assert out["started"] is True
    assert out["start_date"] == "2026-09-15"
    assert out["employment_context"]["employment_country"] == "PL"
    assert out["start_event_emitted"] is True
    assert out["idempotent_replay"] is False
    assert out["active_missing"] == []
    assert out["audit_event_type"] == AUDIT_EVENT_PHYSICAL_START


def test_eso5_confirm_without_row_still_closes_spine_via_mint() -> None:
    out = apply_employment_started_v1(
        package=_pkg(),
        handoff_status="accepted",
        ready_to_create_employee=True,
        start_confirmation={"confirmed": True},
    )
    assert out["decision"] == DECISION_STARTED
    assert out["mint_employee"] is True
    assert out["employee_created"] is True
    assert out["started"] is True
    assert out["start_event_emitted"] is True


def test_eso5_replay_does_not_emit_second_event() -> None:
    prior = {
        "start_date": "2026-09-15",
        "employment_context": {
            "employment_country": "PL",
            "employer_id": "cccccccc-cccc-cccc-cccc-cccccccccccc",
            "vacancy_id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
        },
        "event_id": "evt-1",
    }
    first = apply_employment_started_v1(
        package=_pkg(),
        handoff_status="accepted",
        employee_id="emp-1",
        ready_to_create_employee=True,
        prior_start=prior,
        start_confirmation={"confirmed": True},
    )
    assert first["decision"] == DECISION_ALREADY_STARTED
    assert first["started"] is True
    assert first["start_event_emitted"] is False
    assert first["idempotent_replay"] is True

    second = apply_employment_started_v1(
        package=_pkg(),
        handoff_status="accepted",
        employee_id="emp-1",
        ready_to_create_employee=True,
        prior_start=prior,
        start_confirmation={"confirmed": True, "start_date": "2026-09-15"},
    )
    assert second["decision"] == DECISION_ALREADY_STARTED
    assert second["start_event_emitted"] is False


def test_eso5_conflict_blocks_second_start() -> None:
    prior = {
        "start_date": "2026-09-15",
        "employment_context": {"employment_country": "PL", "employer_id": "cccccccc-cccc-cccc-cccc-cccccccccccc"},
        "event_id": "evt-1",
    }
    out = apply_employment_started_v1(
        package=_pkg(),
        handoff_status="accepted",
        employee_id="emp-1",
        ready_to_create_employee=True,
        prior_start=prior,
        start_confirmation={"confirmed": True, "start_date": "2026-09-20"},
    )
    assert out["decision"] == DECISION_BLOCKED
    assert out["started"] is False
    assert out["start_event_emitted"] is False
    assert any(b.get("code") == "start_fact_conflict" for b in out["blockers"])


def test_eso5_missing_date_asked_once_then_not_reasked_when_known() -> None:
    pkg = _pkg(start_date=None)
    missing = evaluate_employment_started_v1(
        package=pkg,
        handoff_status="accepted",
        employee_id="emp-1",
        ready_to_create_employee=True,
        employment_context={"employment_country": "PL", "employer_id": "cccccccc-cccc-cccc-cccc-cccccccccccc"},
    )
    codes = {m["code"] for m in missing["active_missing"]}
    assert FACT_START_DATE in codes

    known = evaluate_employment_started_v1(
        package=pkg,
        handoff_status="accepted",
        employee_id="emp-1",
        ready_to_create_employee=True,
        known_start_date="2026-09-16",
        employment_context={"employment_country": "PL", "employer_id": "cccccccc-cccc-cccc-cccc-cccccccccccc"},
    )
    known_codes = {m["code"] for m in known["active_missing"]}
    assert FACT_START_DATE not in known_codes
    assert ACTION_CONFIRM in known_codes


def test_eso5_empty_confirm_rejected_when_required() -> None:
    out = apply_employment_started_v1(
        package=_pkg(),
        handoff_status="accepted",
        employee_id="emp-1",
        ready_to_create_employee=True,
        start_confirmation={},
        require_confirm_when_not_started=True,
    )
    assert out["decision"] == DECISION_REJECTED_CONFIRM
    assert out["started"] is False
    assert out["start_event_emitted"] is False


def test_eso5_no_employee_and_not_ready_blocked() -> None:
    out = evaluate_employment_started_v1(
        package=_pkg(),
        handoff_status="accepted",
        ready_to_create_employee=False,
    )
    assert out["decision"] == DECISION_BLOCKED
    assert out["started"] is False
    assert out["employee_created"] is False


def test_eso5_orchestrator_audit_and_no_auto_start() -> None:
    orch = _ORCH.read_text(encoding="utf-8")
    assert "apply_employment_started_v1" in orch
    assert "Does not auto-start" in orch or "employee_created" in orch
    assert "log_audit_event" in orch
    assert "employee_physical_start" in orch
    tree = ast.parse(orch)
    funcs = {n.name for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    assert "confirm_employment_started_for_handoff" in funcs

    api = _HANDOFFS_API.read_text(encoding="utf-8")
    assert "employment-started" in api
    assert "confirm_employment_started_for_handoff" in api

    if _RSO_ORCH.exists():
        rso = _RSO_ORCH.read_text(encoding="utf-8")
        assert "employment_started" not in rso
        assert "confirm_employment_started" not in rso


def test_eso5_docs_and_ci() -> None:
    arch = _ARCH.read_text(encoding="utf-8")
    assert POLICY_ID in arch
    assert "Employee created ≠ Started" in arch or "Employee created" in arch
    assert "idempotent" in arch.lower()
    assert "employee_physical_start" in arch
    assert "formalization" in arch.lower() or "Formalize" in arch

    eso = _ESO.read_text(encoding="utf-8")
    assert "employment-started.md" in eso or POLICY_ID in eso
    assert "ESO-5" in eso

    form = _FORM.read_text(encoding="utf-8")
    assert "employment-started" in form or "ESO-5" in form

    ci = _CI.read_text(encoding="utf-8")
    assert "test_employment_started_gate.py" in ci
    assert "eso5" in ci
