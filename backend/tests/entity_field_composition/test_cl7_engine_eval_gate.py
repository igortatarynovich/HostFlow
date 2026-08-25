"""Entity Field Composition CL7 — Requirement Engine evaluation gate.

Seals evaluate(entity, profile, vacancy, process_point) → ready | not_ready
+ blockers[]. Four kinds. Not a boolean. Not Hub asks. Not Engine v2.
Screening is not required=true. Profile may only ref.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from backend.app.entity_profile.constants import DRIVER_CE_PROFILE_CODE
from backend.app.entity_profile.engine_eval_runtime import (
    CONTRACT_ID,
    ERROR_BOOLEAN_RESULT,
    ERROR_ENGINE_ON_MEMBERSHIP,
    ERROR_ENGINE_V2,
    ERROR_HUB_ASK_WRITE,
    ERROR_R5_POLICY_MERGE,
    ERROR_SCREENING_AS_REQUIRED,
    ERROR_VACANCY_OVERLAY_SOT,
    ERROR_WRITE_TO_EXTRA,
    KIND_DOCUMENT,
    KIND_PRESENCE,
    KIND_PROCESS,
    KIND_VALUE,
    STATUS_NOT_READY,
    STATUS_READY,
    contract_metadata,
    evaluate,
)
from backend.app.entity_profile.flight_map_runtime import (
    CONTRACT_ID as FLIGHT_CONTRACT_ID,
)
from backend.app.entity_profile.layout_runtime import (
    CONTRACT_ID as LAYOUT_CONTRACT_ID,
    FIELD_WIDGET,
    PAGE_TYPE_CANDIDATE_CARD,
    PAGE_TYPE_CATALOG,
)
from backend.app.entity_profile.membership_runtime import (
    CONTRACT_ID as MEMBERSHIP_CONTRACT_ID,
    resolve_membership,
)
from backend.app.entity_profile.qa_runtime import (
    CONTRACT_ID as QA_CONTRACT_ID,
    SOURCE_LEAD_APPLICATION,
)

_REPO_ROOT = Path(__file__).resolve().parents[3]
_BRIEF = _REPO_ROOT / "docs" / "specs" / "tasks" / "entity-field-composition-cl7-engine-eval.md"
_RUNTIME = _REPO_ROOT / "backend" / "app" / "entity_profile" / "engine_eval_runtime.py"
_MEMBERSHIP = _REPO_ROOT / "backend" / "app" / "entity_profile" / "membership_runtime.py"
_GUARD = (
    _REPO_ROOT / "scripts" / "architecture" / "check_entity_profile_engine_eval_boundary.py"
)
_CI = _REPO_ROOT / ".github" / "workflows" / "backend-ci.yml"
_PANEL = (
    _REPO_ROOT
    / "hostflow-frontend"
    / "src"
    / "platform"
    / "entity-workspace"
    / "CandidateEntityWorkspacePanel.tsx"
)
_ZONE = (
    _REPO_ROOT
    / "hostflow-frontend"
    / "src"
    / "platform"
    / "entity-workspace"
    / "CandidateInformationLayout.tsx"
)
_QA = (
    _REPO_ROOT
    / "hostflow-frontend"
    / "src"
    / "platform"
    / "entity-workspace"
    / "CandidateQaPanel.tsx"
)
_FLIGHT = (
    _REPO_ROOT
    / "hostflow-frontend"
    / "src"
    / "platform"
    / "entity-workspace"
    / "CandidateFlightMapPanel.tsx"
)
_ENGINE = (
    _REPO_ROOT
    / "hostflow-frontend"
    / "src"
    / "platform"
    / "entity-workspace"
    / "CandidateEngineEvalPanel.tsx"
)

_PHONE = "recruitment.candidate.contacts.phone"
_YEARS_CE = "recruitment.candidate.experience.years_ce"


def _ready_entity() -> dict:
    return {
        "values": {
            "recruitment.candidate.first_name": "Jan",
            "recruitment.candidate.last_name": "Kowalski",
            _PHONE: "+48 111",
            "recruitment.candidate.contacts.email": "jan@example.com",
            "platform.identity.citizenship": "PL",
            "platform.identity.address": "Warsaw",
            _YEARS_CE: 4,
        },
        "documents": [
            {"document_type_code": "passport"},
            {"document_type_code": "driver_license", "verified": True},
            {"document_type_code": "code95"},
            {"document_type_code": "tacho_card"},
        ],
    }


def _not_ready_entity() -> dict:
    return {
        "values": {
            "recruitment.candidate.first_name": "Jan",
            "recruitment.candidate.last_name": "Kowalski",
            "recruitment.candidate.contacts.email": "jan@example.com",
            "platform.identity.citizenship": "PL",
            "platform.identity.address": "Warsaw",
            _YEARS_CE: 1,
        },
        "documents": [
            {"document_type_code": "driver_license", "verified": False},
            {"document_type_code": "code95"},
            {"document_type_code": "tacho_card"},
        ],
    }


def test_cl7_brief_and_runtime_exist() -> None:
    assert _BRIEF.is_file()
    assert _RUNTIME.is_file()
    brief = _BRIEF.read_text(encoding="utf-8")
    assert "CL7 Gate" in brief
    assert "**Phase class:** platform" in brief
    assert "## Original Goal → Completion Proof" in brief
    assert "D4" in brief
    assert "ready" in brief
    assert "not_ready" in brief
    assert "blockers" in brief


def test_cl7_evaluate_returns_ready_or_not_ready_with_blockers() -> None:
    meta = contract_metadata()
    assert meta["contract_id"] == CONTRACT_ID
    assert CONTRACT_ID == "entity_profile_engine_eval.v1"
    ready = evaluate(
        _ready_entity(),
        DRIVER_CE_PROFILE_CODE,
        vacancy=None,
        process_point="ready_for_handoff",
    )
    assert ready["ok"] is True
    assert ready["contract_id"] == CONTRACT_ID
    assert ready["profile_code"] == DRIVER_CE_PROFILE_CODE
    assert ready["status"] == STATUS_READY
    assert isinstance(ready["status"], str)
    assert ready["status"] not in {True, False, "true", "false"}
    assert ready["blockers"] == []
    assert isinstance(ready["blockers"], list)
    assert "satisfied" not in ready

    blocked = evaluate(
        _not_ready_entity(),
        DRIVER_CE_PROFILE_CODE,
        vacancy=None,
        process_point="ready_for_handoff",
    )
    assert blocked["ok"] is True
    assert blocked["status"] == STATUS_NOT_READY
    assert isinstance(blocked["status"], str)
    assert blocked["blockers"]
    for row in blocked["blockers"]:
        assert set(row) >= {"kind", "code", "owner", "message", "evidence"}
        assert row["kind"] in {KIND_PRESENCE, KIND_VALUE, KIND_DOCUMENT, KIND_PROCESS}

    boolean = evaluate(
        _ready_entity(),
        DRIVER_CE_PROFILE_CODE,
        vacancy={"as_boolean": True},
        process_point="card_save",
    )
    assert boolean["ok"] is False
    assert boolean["error"] == ERROR_BOOLEAN_RESULT


def test_cl7_four_kinds_and_screening_is_not_required_true() -> None:
    blocked = evaluate(
        _not_ready_entity(),
        DRIVER_CE_PROFILE_CODE,
        vacancy=None,
        process_point="ready_for_handoff",
    )
    kinds = {row["kind"] for row in blocked["blockers"]}
    assert KIND_PRESENCE in kinds
    assert KIND_VALUE in kinds
    assert KIND_DOCUMENT in kinds
    assert KIND_PROCESS in kinds
    assert kinds == {KIND_PRESENCE, KIND_VALUE, KIND_DOCUMENT, KIND_PROCESS}

    presence_codes = [row["code"] for row in blocked["blockers"] if row["kind"] == KIND_PRESENCE]
    assert any(_PHONE in code for code in presence_codes)
    value_rows = [row for row in blocked["blockers"] if row["kind"] == KIND_VALUE]
    assert value_rows
    assert all(row["evidence"].get("required") is False for row in value_rows)
    assert all("required=true" not in row["message"] for row in value_rows)

    membership = resolve_membership(DRIVER_CE_PROFILE_CODE)
    assert membership is not None
    years = next(
        row for row in membership["fields"] if row["qualified_code"] == _YEARS_CE
    )
    assert "required" not in years
    assert years["presence"]["card_save"] == "required"
    screening = evaluate(
        _not_ready_entity(),
        DRIVER_CE_PROFILE_CODE,
        vacancy={"screening_as_required": True},
        process_point="ready_for_handoff",
    )
    assert screening["error"] == ERROR_SCREENING_AS_REQUIRED


def test_cl7_profile_refs_engine_and_does_not_implement_it() -> None:
    membership = resolve_membership(DRIVER_CE_PROFILE_CODE)
    assert membership is not None
    assert membership["contract_id"] == MEMBERSHIP_CONTRACT_ID
    refs = membership["refs"]
    assert "document_pack_code" in refs
    assert "screening_pack_code" in refs
    assert "process_profile_code" in refs
    assert "engine" not in refs
    assert CONTRACT_ID not in refs
    membership_src = _MEMBERSHIP.read_text(encoding="utf-8")
    assert "entity_profile_engine_eval" not in membership_src
    assert "def evaluate(" not in membership_src
    on_membership = evaluate(
        _ready_entity(),
        DRIVER_CE_PROFILE_CODE,
        vacancy={"put_on_membership": True},
        process_point="card_save",
    )
    assert on_membership["error"] == ERROR_ENGINE_ON_MEMBERSHIP


def test_cl7_does_not_write_hub_asks_or_merge_r5() -> None:
    asks = evaluate(
        _ready_entity(),
        DRIVER_CE_PROFILE_CODE,
        vacancy={"persist_asks": True},
        process_point="card_save",
    )
    assert asks["error"] == ERROR_HUB_ASK_WRITE
    generated = evaluate(
        _ready_entity(),
        DRIVER_CE_PROFILE_CODE,
        vacancy={"outstanding_asks": [{"doc_type": "passport"}]},
        process_point="card_save",
    )
    assert generated["error"] == ERROR_HUB_ASK_WRITE
    merged = evaluate(
        _ready_entity(),
        DRIVER_CE_PROFILE_CODE,
        vacancy={"tenant_delta": {"relax": ["passport"]}},
        process_point="card_save",
    )
    assert merged["error"] == ERROR_R5_POLICY_MERGE
    overlay = evaluate(
        _ready_entity(),
        DRIVER_CE_PROFILE_CODE,
        vacancy={"mint_overlay": True},
        process_point="card_save",
    )
    assert overlay["error"] == ERROR_VACANCY_OVERLAY_SOT
    v2 = evaluate(
        _ready_entity(),
        DRIVER_CE_PROFILE_CODE,
        vacancy={"engine_v2": True},
        process_point="card_save",
    )
    assert v2["error"] == ERROR_ENGINE_V2
    extra = evaluate(
        _ready_entity(),
        DRIVER_CE_PROFILE_CODE,
        vacancy={"copy_to_extra": True},
        process_point="card_save",
    )
    assert extra["error"] == ERROR_WRITE_TO_EXTRA
    runtime = _RUNTIME.read_text(encoding="utf-8")
    lowered = runtime.lower()
    assert "no alembic" in lowered
    assert "e8" in lowered
    assert "dr1-runtime" in lowered
    assert "engine v2" in lowered
    assert "hub ask" in lowered
    assert "tenant_delta" in lowered
    assert "DROP COLUMN" not in runtime


def test_cl7_d4_places_engine_eval_other_zones_stay() -> None:
    assert _ZONE.is_file()
    assert _QA.is_file()
    assert _FLIGHT.is_file()
    assert _ENGINE.is_file()
    zone = _ZONE.read_text(encoding="utf-8")
    qa = _QA.read_text(encoding="utf-8")
    flight = _FLIGHT.read_text(encoding="utf-8")
    engine = _ENGINE.read_text(encoding="utf-8")
    panel = _PANEL.read_text(encoding="utf-8")
    assert "CandidateInformationLayout" in panel
    assert "CandidateQaPanel" in panel
    assert "CandidateFlightMapPanel" in panel
    assert "CandidateEngineEvalPanel" in panel
    assert LAYOUT_CONTRACT_ID in zone
    assert PAGE_TYPE_CANDIDATE_CARD in zone
    assert 'data-host-region="information"' in zone
    assert CONTRACT_ID not in zone
    assert QA_CONTRACT_ID not in zone
    assert FLIGHT_CONTRACT_ID not in zone
    assert 'data-host-region="engine-eval"' not in zone
    assert QA_CONTRACT_ID in qa
    assert 'data-host-region="qa"' in qa
    assert f'data-source="{SOURCE_LEAD_APPLICATION}"' in qa
    assert FLIGHT_CONTRACT_ID in flight
    assert 'data-host-region="flight-map"' in flight
    assert CONTRACT_ID in engine
    assert 'data-host-region="engine-eval"' in engine
    assert 'data-status-shape="ready|not_ready"' in engine
    assert 'data-boolean="false"' in engine
    assert 'data-hub-asks="false"' in engine
    assert 'data-engine-v2="false"' in engine
    assert 'data-vacancy-overlay-sot="false"' in engine
    assert 'data-layout-widget="false"' in engine
    for spec in PAGE_TYPE_CATALOG.values():
        assert spec["widgets"] == frozenset({FIELD_WIDGET})
        assert "engine" not in spec["widgets"]
        assert "engine_eval" not in spec["widgets"]
        assert "qa" not in spec["widgets"]
        assert "flight_map" not in spec["widgets"]


def test_cl7_engine_eval_boundary_guard() -> None:
    result = subprocess.run(
        [sys.executable, str(_GUARD)],
        cwd=_REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_cl7_named_ci_gate() -> None:
    ci = _CI.read_text(encoding="utf-8")
    assert "CL7 Engine Eval Gate" in ci
    assert "test_cl7_engine_eval_gate.py" in ci


def test_cl7_gate_filename() -> None:
    assert Path(__file__).name == "test_cl7_engine_eval_gate.py"
