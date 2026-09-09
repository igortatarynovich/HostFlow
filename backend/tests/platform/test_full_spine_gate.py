"""Full Spine Gate — one happy path lead package → Started.

Operator / Zero-choice contract freeze. Named-gate PASS still requires
a new-operator witness (not claimed by this machine suite).
"""

from __future__ import annotations

from pathlib import Path

from backend.app.core.audit_events import AuditEventType
from backend.app.reference.employment_accept_policy import PACKAGE_AUTHORITATIVE_FIELD_CODES
from backend.app.reference.full_spine import (
    ARCH_REL,
    ESO_BRIEF_REL,
    FORBIDDEN_HAPPY_PATH_CONTROLS,
    OPERATOR_VERBS,
    POLICY_ID,
    RSO_BRIEF_REL,
    SPINE_STEPS,
    WALK_API,
    walk_full_spine_happy_path_v1,
)
from backend.app.reference.ready_for_employment import CONTRACT_ID

_REPO_ROOT = Path(__file__).resolve().parents[3]
_ARCH = _REPO_ROOT / ARCH_REL
_RSO = _REPO_ROOT / RSO_BRIEF_REL
_ESO = _REPO_ROOT / ESO_BRIEF_REL
_CI = _REPO_ROOT / ".github" / "workflows" / "backend-ci.yml"
_MODULE = _REPO_ROOT / "backend" / "app" / "reference" / "full_spine.py"
_FE = _REPO_ROOT / "hostflow-frontend" / "src"


def _pkg() -> dict:
    return {
        "contract_id": CONTRACT_ID,
        "tenant_id": "11111111-1111-1111-1111-111111111111",
        "person": {
            "person_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            "identity_facts": {"citizenship": "PL", "first_name": "Ada", "last_name": "Nowak"},
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


def test_full_spine_gate_filename() -> None:
    assert Path(__file__).name == "test_full_spine_gate.py"


def test_full_spine_policy_and_walk_api() -> None:
    assert POLICY_ID == "full_spine.v1"
    assert WALK_API == "walk_full_spine_happy_path_v1"
    assert "def walk_full_spine_happy_path_v1(" in _MODULE.read_text(encoding="utf-8")
    assert SPINE_STEPS == (
        "source",
        "recruitment_fits",
        "handoff_package",
        "employment_accept",
        "employability",
        "missing_resolution",
        "formalize",
        "employee",
        "started",
    )


def test_full_spine_happy_path_package_to_started() -> None:
    out = walk_full_spine_happy_path_v1(package=_pkg())
    assert out["package_valid"] is True
    assert out["accept"]["decision"] == "auto_accept"
    assert out["employability"]["decision"] == "employable"
    assert out["employability"]["pathway_selection_required"] is False
    assert out["pathway_dropdown_required"] is False
    assert out["resolution"]["resolution_decision"] == "ready_to_formalize"
    assert out["formalize"]["ready_to_create_employee"] is True
    assert out["formalize"]["employee_created"] is False
    assert out["started"]["started"] is True
    assert out["started"]["start_event_emitted"] is True
    assert out["started_replay"]["decision"] == "already_started"
    assert out["started_replay"]["start_event_emitted"] is False
    assert out["spine_closed"] is True
    assert out["happy_path"] is True
    assert out["audits_distinct"] is True
    assert out["audit_physical_start"] == "employee_physical_start"
    assert out["audit_employment_case_started"] == AuditEventType.employment_started.value
    assert out["operator_pass_required"] is True
    assert out["operator_pass_recorded"] is False


def test_full_spine_known_facts_not_reasked() -> None:
    out = walk_full_spine_happy_path_v1(
        package=_pkg(),
        employment_missing=[{"field_code": "citizenship", "label": "Citizenship"}],
    )
    assert "citizenship" in out["reuse_violations"]
    assert out["spine_closed"] is False
    assert "citizenship" in PACKAGE_AUTHORITATIVE_FIELD_CODES


def test_full_spine_sot_locks_operator_zero_choice() -> None:
    text = _ARCH.read_text(encoding="utf-8")
    assert POLICY_ID in text
    assert "Employee created" in text or "Employee created ≠ Started" in text
    assert "pathway" in text.lower()
    assert "stage" in text.lower()
    assert "new operator" in text.lower() or "без документации" in text or "without documentation" in text
    assert "Подходит" in text
    assert "Передать на трудоустройство" in text
    assert "Подтвердить выход" in text
    for verb in OPERATOR_VERBS:
        assert verb in text
    for control in (
        "stage_dropdown",
        "status_dropdown",
        "pathway_dropdown",
        "create_candidate_ritual",
    ):
        assert control in FORBIDDEN_HAPPY_PATH_CONTROLS
        assert control in text or control.replace("_", " ") in text.lower() or "dropdown" in text.lower()


def test_full_spine_briefs_and_ci() -> None:
    rso = _RSO.read_text(encoding="utf-8")
    eso = _ESO.read_text(encoding="utf-8")
    assert "full-spine-gate" in rso or "Full Spine Gate" in rso
    assert "full-spine-gate" in eso or "Full Spine Gate" in eso
    assert "ESO-6" not in eso.split("## Next")[-1] or "not ESO-6" in eso.lower() or "Full Spine" in eso

    ci = _CI.read_text(encoding="utf-8")
    assert "test_full_spine_gate.py" in ci
    assert "full-spine-gate" in ci


def test_full_spine_fe_happy_path_has_no_pathway_select() -> None:
    """Zero-choice static audit: spine FE must not ship a pathway <select>."""
    if not _FE.exists():
        return
    hits: list[str] = []
    for path in _FE.rglob("*.tsx"):
        rel = str(path.relative_to(_REPO_ROOT))
        if any(part in rel for part in ("/admin/", "/docs/", "__tests__", ".test.")):
            continue
        text = path.read_text(encoding="utf-8")
        lowered = text.lower()
        if "legal_pathway" in lowered or "legalpathway" in lowered or "pathway_id" in lowered:
            if "<select" in lowered and "pathway" in lowered:
                hits.append(rel)
    assert hits == [], f"pathway dropdown on happy-path surfaces: {hits}"
