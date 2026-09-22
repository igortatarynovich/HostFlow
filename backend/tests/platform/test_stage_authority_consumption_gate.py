"""Stage Authority Consumption Gate (HE-2).

Hiring-path existence consumes LI-1. Occupancy stays Candidate.stage.
Transition-order rule is production. Not HE-3. Not RS-7. Not min HR.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
from fastapi import HTTPException

from backend.app.reference.hiring_acceptance import (
    CONTRACT_ID as HE1_CONTRACT_ID,
    WALK_STEPS,
)
from backend.app.reference.hiring_stage_authority import (
    CONTRACT_ID,
    EXISTENCE_API,
    FORBIDDEN_IMPLEMENTATION,
    HIRING_PATH_EXISTENCE_CONSUMERS,
    OCCUPANCY_AUTHORITY,
    PARENT_CONTRACT_ID,
    TRANSITION_ORDER,
    TRANSITION_RULE,
    assert_hiring_stage_transition,
    classify_hiring_transition,
    hiring_stage_exists,
    leftover_existence_codes,
    normalize_hiring_stage_key,
    resolve_hiring_stage_key,
)

_REPO_ROOT = Path(__file__).resolve().parents[3]
_BRIEF = _REPO_ROOT / "docs" / "specs" / "tasks" / "hiring-workflow-e2e.md"
_ARCH = _REPO_ROOT / "docs" / "specs" / "architecture" / "hiring-stage-authority-consumption.md"
_PARENT = _REPO_ROOT / "docs" / "specs" / "architecture" / "hiring-acceptance-contract.md"
_QUEUE = _REPO_ROOT / "docs" / "specs" / "tasks" / "sales-to-comms-sequential-queue.md"
_AGENTS = _REPO_ROOT / "AGENTS.md"
_GUARD = _REPO_ROOT / "scripts" / "architecture" / "check_hiring_stage_authority_boundary.py"
_CI = _REPO_ROOT / ".github" / "workflows" / "backend-ci.yml"
_HR = _REPO_ROOT / "docs" / "specs" / "tasks" / "recruitment-hr-minimal-handoff.md"
_HELPERS = _REPO_ROOT / "backend" / "app" / "api" / "v1" / "candidates" / "helpers.py"
_ADR037 = _REPO_ROOT / "docs" / "specs" / "architecture" / "ADR-037-lifecycle-identity-canon.md"


def test_he2_gate_filename() -> None:
    assert Path(__file__).name == "test_stage_authority_consumption_gate.py"


def test_he2_contract_consumes_li1_and_he1() -> None:
    assert CONTRACT_ID == "hiring_stage_authority.v1"
    assert PARENT_CONTRACT_ID == HE1_CONTRACT_ID == "hiring_acceptance.v1"
    assert EXISTENCE_API == "is_stage_registered"
    assert OCCUPANCY_AUTHORITY == "candidate_stage"
    assert TRANSITION_RULE == "forward_moves_guarded_jumps_rejected"
    assert leftover_existence_codes() == (
        "static_new_to_hired_list",
        "tenant_candidate_stages_dictionary",
        "funnel_stages_as_existence",
    )
    assert "he3_collapse_in_this_pr" in FORBIDDEN_IMPLEMENTATION
    assert "rs7_execution" in FORBIDDEN_IMPLEMENTATION
    assert "min_hr_handoff" in FORBIDDEN_IMPLEMENTATION
    assert "new_stage_machine" in FORBIDDEN_IMPLEMENTATION
    step_by_code = {step.code: step for step in WALK_STEPS}
    assert step_by_code["stage_existence"].authority_role == "authority"
    assert step_by_code["stage_occupancy"].authority_role == "authority"
    assert step_by_code["stage_transition"].authority_role == "authority"
    assert step_by_code["stage_transition"].later_slice == "none"
    assert step_by_code["eligibility_decision"].authority_role == "compose_later"
    assert len(TRANSITION_ORDER) == len(set(TRANSITION_ORDER))
    assert all(hiring_stage_exists(key) for key in TRANSITION_ORDER)


def test_he2_registered_keys_exist_leftovers_do_not() -> None:
    assert hiring_stage_exists("new")
    assert hiring_stage_exists("ready_for_handoff")
    assert normalize_hiring_stage_key("contacted") == "contacted"
    assert normalize_hiring_stage_key("interview") == "contacted"
    assert normalize_hiring_stage_key("skontaktowac__sie_pozniej") is None
    assert normalize_hiring_stage_key("offer") is None
    assert resolve_hiring_stage_key("new") == "new"
    with pytest.raises(HTTPException) as unknown:
        resolve_hiring_stage_key("skontaktowac__sie_pozniej")
    assert unknown.value.status_code == 422
    with pytest.raises(HTTPException) as short_list:
        resolve_hiring_stage_key("offer")
    assert short_list.value.status_code == 422


def test_he2_transition_order_rule() -> None:
    assert classify_hiring_transition("new", "new") == "same"
    assert classify_hiring_transition("new", "contacted") == "forward"
    assert classify_hiring_transition("contacted", "new") == "backward"
    assert classify_hiring_transition("new", "skontaktowac__sie_pozniej") == "jump"
    assert classify_hiring_transition("funnel_local", "contacted") == "forward"
    assert assert_hiring_stage_transition("new", "docs_got") == "forward"
    with pytest.raises(HTTPException) as jumped:
        assert_hiring_stage_transition("new", "not_a_registered_stage")
    assert jumped.value.status_code == 422


def test_he2_hiring_path_does_not_ask_leftovers() -> None:
    helpers = _HELPERS.read_text(encoding="utf-8")
    assert "FunnelStage" not in helpers
    assert "resolve_hiring_stage_key" in helpers
    assert "assert_hiring_stage_transition" in helpers
    for rel in HIRING_PATH_EXISTENCE_CONSUMERS:
        assert (_REPO_ROOT / rel).is_file()


def test_he2_architecture_is_sot() -> None:
    text = _ARCH.read_text(encoding="utf-8")
    assert "Stage Authority Consumption Gate" in text
    assert CONTRACT_ID in text
    assert EXISTENCE_API in text
    assert "Candidate.stage" in text
    assert TRANSITION_RULE in text
    assert "forward_moves_guarded_jumps_rejected" in text
    assert "not a new hiring product" in text.lower()
    assert "Funnel" in text
    parent = _PARENT.read_text(encoding="utf-8")
    assert "hiring-stage-authority-consumption.md" in parent
    assert CONTRACT_ID in parent or "Stage Authority Consumption" in parent
    adr = _ADR037.read_text(encoding="utf-8")
    assert "hiring-stage-authority-consumption.md" in adr


def test_he2_brief_gate_pass() -> None:
    text = _BRIEF.read_text(encoding="utf-8")
    current = text.split("## History", 1)[0]
    assert "Stage Authority Consumption Gate" in current
    assert "**PASS**" in current
    assert "hiring-stage-authority-consumption.md" in current
    assert CONTRACT_ID in current or "hiring_stage_authority.v1" in current
    assert "feat locked" in current.lower()
    assert "HE-3" in current
    assert "HE-3 runtime" not in current.lower() or "not he-3" in current.lower()
    assert "min HR" in current or "minimal" in current.lower()
    assert "not a new hiring product" in current.lower()


def test_he2_queue_names_he2_active_he3_locked() -> None:
    text = _QUEUE.read_text(encoding="utf-8")
    current = text.split("## 8. History", 1)[0]
    history = text.split("## 8. History", 1)[1]
    assert "Stage Authority Consumption Gate **PASS**" in current
    assert "**Active Product** | **[HE-2](hiring-workflow-e2e.md)**" in current or (
        "**Active Product** | **[HE-2]" in current
    )
    assert "Active (Product):** **[HE-2](hiring-workflow-e2e.md)**" in current
    assert "Hiring Acceptance Contract Gate **PASS**" in current
    assert "Do not start HE-3" in current or "HE-3 feat locked" in current.lower()
    assert "Active Product stays **[HE-1]" in history or "Do not start HE-2" in history
    agents = _AGENTS.read_text(encoding="utf-8")
    assert "hiring-workflow-e2e.md" in agents
    assert "HE-2" in agents
    assert "Stage Authority Consumption" in agents or "hiring_stage_authority" in agents.lower()
    assert "CL8" in current
    lowered = current.lower()
    assert "min hr" in lowered or "minimal recruitment" in lowered


def test_he2_leaves_hr_queued() -> None:
    text = _HR.read_text(encoding="utf-8")
    header = text.split("## History", 1)[0] if "## History" in text else text
    assert "**QUEUED**" in header
    assert "not scheduled" in header.lower()
    assert "hiring-workflow-e2e.md" in header


def test_he2_boundary_guard() -> None:
    result = subprocess.run(
        [sys.executable, str(_GUARD)],
        cwd=_REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_he2_named_ci_gate() -> None:
    ci = _CI.read_text(encoding="utf-8")
    assert "Stage Authority Consumption Gate" in ci
    assert "test_stage_authority_consumption_gate.py" in ci
    assert "docs/specs/architecture/hiring-stage-authority-consumption.md" in ci
