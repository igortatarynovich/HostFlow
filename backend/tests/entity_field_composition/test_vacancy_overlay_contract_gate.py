"""Entity Profile — Vacancy Overlay Contract gate.

Seals resolve_overlay(profile, vacancy) + merge(profile, screening_pack,
overlay) as the defined input to CL7 evaluate. Not CL8. Not R5 pack
merge. Not Hub asks. Not vacancy UI. Profile may only ref.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from backend.app.entity_profile.constants import (
    DRIVER_CE_PROFILE_CODE,
    DRIVER_CE_SCREENING_PACK_CODE,
)
from backend.app.entity_profile.engine_eval_runtime import (
    CONTRACT_ID as ENGINE_CONTRACT_ID,
    KIND_DOCUMENT,
    KIND_PRESENCE,
    KIND_PROCESS,
    KIND_VALUE,
    STATUS_NOT_READY,
    STATUS_READY,
    evaluate,
)
from backend.app.entity_profile.flight_map_runtime import (
    CONTRACT_ID as FLIGHT_CONTRACT_ID,
)
from backend.app.entity_profile.layout_runtime import (
    CONTRACT_ID as LAYOUT_CONTRACT_ID,
)
from backend.app.entity_profile.membership_runtime import (
    CONTRACT_ID as MEMBERSHIP_CONTRACT_ID,
    resolve_membership,
)
from backend.app.entity_profile.qa_runtime import CONTRACT_ID as QA_CONTRACT_ID
from backend.app.entity_profile.vacancy_overlay_runtime import (
    CONTRACT_ID,
    ERROR_CL8,
    ERROR_HUB_ASK_WRITE,
    ERROR_OVERLAY_FORK,
    ERROR_OVERLAY_ON_MEMBERSHIP,
    ERROR_OVERLAY_RELAX,
    ERROR_R5_POLICY_MERGE,
    ERROR_VACANCY_UI,
    OP_ADD,
    OP_TIGHTEN,
    contract_metadata,
    merge,
    resolve_overlay,
)

_REPO_ROOT = Path(__file__).resolve().parents[3]
_BRIEF = _REPO_ROOT / "docs" / "specs" / "tasks" / "entity-profile-vacancy-overlay-contract.md"
_RUNTIME = _REPO_ROOT / "backend" / "app" / "entity_profile" / "vacancy_overlay_runtime.py"
_ENGINE = _REPO_ROOT / "backend" / "app" / "entity_profile" / "engine_eval_runtime.py"
_MEMBERSHIP = _REPO_ROOT / "backend" / "app" / "entity_profile" / "membership_runtime.py"
_GUARD = (
    _REPO_ROOT
    / "scripts"
    / "architecture"
    / "check_entity_profile_vacancy_overlay_boundary.py"
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
_ENGINE_PANEL = (
    _REPO_ROOT
    / "hostflow-frontend"
    / "src"
    / "platform"
    / "entity-workspace"
    / "CandidateEngineEvalPanel.tsx"
)

_YEARS_CE = "recruitment.candidate.experience.years_ce"


def _ready_entity() -> dict:
    return {
        "values": {
            "recruitment.candidate.first_name": "Jan",
            "recruitment.candidate.last_name": "Kowalski",
            "recruitment.candidate.contacts.phone": "+48 111",
            "recruitment.candidate.contacts.email": "jan@example.com",
            "platform.identity.citizenship": "PL",
            "platform.identity.address": "Warsaw",
            _YEARS_CE: 4,
        },
        "documents": [
            {"document_type_code": "passport", "verified": True},
            {"document_type_code": "driver_license", "verified": True},
            {"document_type_code": "code95"},
            {"document_type_code": "tacho_card"},
        ],
    }


def _four_kind_vacancy() -> dict:
    return {
        "vacancy_ref": "vac-driver-ce-1",
        "delta": [
            {
                "kind": KIND_VALUE,
                "code": "screening.years_ce.min",
                "owner": "vacancy",
                "op": OP_TIGHTEN,
                "predicate": {
                    "qualified_code": _YEARS_CE,
                    "op": ">=",
                    "value": 5,
                },
            },
            {
                "kind": KIND_DOCUMENT,
                "code": "document.adr.missing",
                "owner": "vacancy",
                "op": OP_ADD,
                "predicate": {"document_type_code": "adr"},
            },
            {
                "kind": KIND_PRESENCE,
                "code": "presence.platform.identity.address",
                "owner": "vacancy",
                "op": OP_ADD,
                "predicate": {
                    "qualified_code": "platform.identity.address",
                    "context": "card_save",
                },
            },
            {
                "kind": KIND_PROCESS,
                "code": "process.handoff.passport_verified",
                "owner": "vacancy",
                "op": OP_ADD,
                "predicate": {
                    "document_type_code": "passport",
                    "verified": True,
                    "process_point": "handoff",
                },
            },
        ],
    }


def test_overlay_brief_and_runtime_exist() -> None:
    assert _BRIEF.is_file()
    assert _RUNTIME.is_file()
    brief = _BRIEF.read_text(encoding="utf-8")
    assert "Vacancy Overlay Gate" in brief
    assert "**Phase class:** platform" in brief
    assert "## Original Goal → Completion Proof" in brief
    assert "entity_profile_vacancy_overlay.v1" in brief
    assert "resolve_overlay" in brief
    assert "not CL8" in brief.lower() or "Not CL8" in brief


def test_overlay_is_sot_delta_over_profile_and_screening_pack() -> None:
    meta = contract_metadata()
    assert meta["contract_id"] == CONTRACT_ID
    assert CONTRACT_ID == "entity_profile_vacancy_overlay.v1"
    overlay = resolve_overlay(DRIVER_CE_PROFILE_CODE, _four_kind_vacancy())
    assert overlay["ok"] is True
    assert overlay["contract_id"] == CONTRACT_ID
    assert overlay["profile_code"] == DRIVER_CE_PROFILE_CODE
    assert overlay["vacancy_ref"] == "vac-driver-ce-1"
    assert overlay["base"] == DRIVER_CE_SCREENING_PACK_CODE
    kinds = {row["kind"] for row in overlay["delta"]}
    assert kinds == {KIND_PRESENCE, KIND_VALUE, KIND_DOCUMENT, KIND_PROCESS}
    assert all(row["op"] in {OP_TIGHTEN, OP_ADD} for row in overlay["delta"])

    mapped = resolve_overlay(
        DRIVER_CE_PROFILE_CODE,
        {"vacancy_ref": "vac-2", "years_ce_min": 5},
    )
    assert mapped["ok"] is True
    assert mapped["delta"]
    assert mapped["delta"][0]["kind"] == KIND_VALUE
    assert mapped["delta"][0]["op"] == OP_TIGHTEN
    assert mapped["delta"][0]["predicate"]["value"] == 5
    runtime = _RUNTIME.read_text(encoding="utf-8")
    assert "years_ce_min is not the contract" in runtime or "Ad-hoc" in runtime


def test_overlay_merge_is_not_fork_and_not_r5() -> None:
    overlay = resolve_overlay(DRIVER_CE_PROFILE_CODE, _four_kind_vacancy())
    effective = merge(
        DRIVER_CE_PROFILE_CODE,
        DRIVER_CE_SCREENING_PACK_CODE,
        overlay,
    )
    assert effective["ok"] is True
    assert effective["fork"] is False
    assert effective["tenant_delta"] is False
    assert effective["years_ce_min"] == 5
    assert effective["years_ce_owner"] == "vacancy"
    assert "adr" in effective["document_types"]
    assert "passport" in effective["document_types"]

    base = merge(
        DRIVER_CE_PROFILE_CODE,
        DRIVER_CE_SCREENING_PACK_CODE,
        resolve_overlay(DRIVER_CE_PROFILE_CODE, None),
    )
    assert base["ok"] is True
    assert base["years_ce_min"] == 2
    assert base["years_ce_owner"] == "screening_pack"

    forked = resolve_overlay(
        DRIVER_CE_PROFILE_CODE,
        {"fork": True, "vacancy_ref": "vac-x"},
    )
    assert forked["error"] == ERROR_OVERLAY_FORK
    relaxed = resolve_overlay(
        DRIVER_CE_PROFILE_CODE,
        {"delta": [{"kind": KIND_VALUE, "op": "relax", "predicate": {"value": 1}}]},
    )
    assert relaxed["error"] == ERROR_OVERLAY_RELAX
    r5 = resolve_overlay(
        DRIVER_CE_PROFILE_CODE,
        {"tenant_delta": {"relax": ["passport"]}},
    )
    assert r5["error"] == ERROR_R5_POLICY_MERGE


def test_cl7_evaluate_consumes_overlay_not_adhoc_years_ce_min() -> None:
    engine = _ENGINE.read_text(encoding="utf-8")
    assert "vacancy.get(\"years_ce_min\")" not in engine
    assert "entity.get(\"years_ce_min\")" not in engine
    assert "resolve_overlay" in engine
    assert "merge_overlay" in engine
    assert CONTRACT_ID in engine

    ready = evaluate(
        _ready_entity(),
        DRIVER_CE_PROFILE_CODE,
        vacancy=None,
        process_point="ready_for_handoff",
    )
    assert ready["ok"] is True
    assert ready["status"] == STATUS_READY
    assert ready["overlay"]["contract_id"] == CONTRACT_ID

    tightened = evaluate(
        _ready_entity(),
        DRIVER_CE_PROFILE_CODE,
        vacancy={"years_ce_min": 5},
        process_point="card_save",
    )
    assert tightened["ok"] is True
    assert tightened["status"] == STATUS_NOT_READY
    value_rows = [row for row in tightened["blockers"] if row["kind"] == KIND_VALUE]
    assert value_rows
    assert value_rows[0]["evidence"]["minimum"] == 5
    assert value_rows[0]["owner"] == "vacancy"
    assert value_rows[0]["evidence"]["overlay_contract_id"] == CONTRACT_ID

    missing_adr = evaluate(
        _ready_entity(),
        DRIVER_CE_PROFILE_CODE,
        vacancy=_four_kind_vacancy(),
        process_point="card_save",
    )
    assert missing_adr["status"] == STATUS_NOT_READY
    doc_codes = [
        row["evidence"].get("document_type_code")
        for row in missing_adr["blockers"]
        if row["kind"] == KIND_DOCUMENT
    ]
    assert "adr" in doc_codes
    assert ENGINE_CONTRACT_ID == missing_adr["contract_id"]


def test_overlay_profile_refs_only_and_rejects_false_closes() -> None:
    membership = resolve_membership(DRIVER_CE_PROFILE_CODE)
    assert membership is not None
    assert membership["contract_id"] == MEMBERSHIP_CONTRACT_ID
    refs = membership["refs"]
    assert "document_pack_code" in refs
    assert "screening_pack_code" in refs
    assert CONTRACT_ID not in refs
    assert "overlay" not in refs
    membership_src = _MEMBERSHIP.read_text(encoding="utf-8")
    assert "entity_profile_vacancy_overlay" not in membership_src
    assert "def resolve_overlay(" not in membership_src
    assert "def merge(" not in membership_src
    on_membership = resolve_overlay(
        DRIVER_CE_PROFILE_CODE,
        {"put_on_membership": True},
    )
    assert on_membership["error"] == ERROR_OVERLAY_ON_MEMBERSHIP
    asks = resolve_overlay(
        DRIVER_CE_PROFILE_CODE,
        {"persist_asks": True},
    )
    assert asks["error"] == ERROR_HUB_ASK_WRITE
    ui = resolve_overlay(
        DRIVER_CE_PROFILE_CODE,
        {"vacancy_ui": True},
    )
    assert ui["error"] == ERROR_VACANCY_UI
    cl8 = resolve_overlay(
        DRIVER_CE_PROFILE_CODE,
        {"cl8": True},
    )
    assert cl8["error"] == ERROR_CL8
    runtime = _RUNTIME.read_text(encoding="utf-8")
    lowered = runtime.lower()
    assert "no alembic" in lowered
    assert "not cl8" in lowered
    assert "hub ask" in lowered
    assert "tenant_delta" in lowered
    assert "vacancy ui" in lowered
    assert "DROP COLUMN" not in runtime


def test_overlay_d4_places_engine_eval_other_zones_stay() -> None:
    assert _ZONE.is_file()
    assert _QA.is_file()
    assert _FLIGHT.is_file()
    assert _ENGINE_PANEL.is_file()
    zone = _ZONE.read_text(encoding="utf-8")
    qa = _QA.read_text(encoding="utf-8")
    flight = _FLIGHT.read_text(encoding="utf-8")
    engine = _ENGINE_PANEL.read_text(encoding="utf-8")
    panel = _PANEL.read_text(encoding="utf-8")
    assert "CandidateInformationLayout" in panel
    assert "CandidateQaPanel" in panel
    assert "CandidateFlightMapPanel" in panel
    assert "CandidateEngineEvalPanel" in panel
    assert LAYOUT_CONTRACT_ID in zone
    assert 'data-host-region="information"' in zone
    assert CONTRACT_ID not in zone
    assert QA_CONTRACT_ID in qa
    assert 'data-host-region="qa"' in qa
    assert FLIGHT_CONTRACT_ID in flight
    assert 'data-host-region="flight-map"' in flight
    assert ENGINE_CONTRACT_ID in engine
    assert CONTRACT_ID in engine
    assert 'data-host-region="engine-eval"' in engine
    assert 'data-overlay-input="defined"' in engine
    assert 'data-vacancy-overlay-sot="false"' in engine
    assert 'data-vacancy-ui="false"' in engine
    assert "VacancyCard" not in engine
    assert "vacancy-workspace" not in engine


def test_overlay_boundary_guard() -> None:
    result = subprocess.run(
        [sys.executable, str(_GUARD)],
        cwd=_REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_overlay_named_ci_gate() -> None:
    ci = _CI.read_text(encoding="utf-8")
    assert "Vacancy Overlay Contract Gate" in ci
    assert "test_vacancy_overlay_contract_gate.py" in ci


def test_overlay_gate_filename() -> None:
    assert Path(__file__).name == "test_vacancy_overlay_contract_gate.py"
