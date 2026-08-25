"""Entity Field Composition CL6 — Flight mapping gate.

Seals Map execute: raw → member qualified_code, snapshot on Binding.
qa_only absent. ignore dropped. Dest = Profile, not Flight entity.
Not Zapier UX. Not Meta admin SoT. No extra copy. No minted fields.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from backend.app.entity_profile.constants import DRIVER_CE_PROFILE_CODE
from backend.app.entity_profile.flight_map_runtime import (
    CONTRACT_ID,
    ERROR_DEST_IS_FLIGHT,
    ERROR_META_ADMIN_SOT,
    ERROR_MINTED_FIELD_SEMANTICS,
    ERROR_MISSING_BINDING,
    ERROR_NON_MEMBER_DEST,
    ERROR_QA_IN_SNAPSHOT,
    ERROR_WRITE_TO_EXTRA,
    ERROR_ZAPIER_UX,
    SNAPSHOT_ON_BINDING,
    apply_map,
    contract_metadata,
)
from backend.app.entity_profile.layout_runtime import (
    CONTRACT_ID as LAYOUT_CONTRACT_ID,
    FIELD_WIDGET,
    PAGE_TYPE_CANDIDATE_CARD,
    PAGE_TYPE_CATALOG,
)
from backend.app.entity_profile.membership_runtime import is_field_member
from backend.app.entity_profile.qa_runtime import (
    CONTRACT_ID as QA_CONTRACT_ID,
    DISPOSITION_IGNORE,
    DISPOSITION_MAP,
    DISPOSITION_QA_ONLY,
    SOURCE_LEAD_APPLICATION,
)

_REPO_ROOT = Path(__file__).resolve().parents[3]
_BRIEF = _REPO_ROOT / "docs" / "specs" / "tasks" / "entity-field-composition-cl6-flight-map.md"
_RUNTIME = _REPO_ROOT / "backend" / "app" / "entity_profile" / "flight_map_runtime.py"
_GUARD = (
    _REPO_ROOT / "scripts" / "architecture" / "check_entity_profile_flight_map_boundary.py"
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

_PHONE = "recruitment.candidate.contacts.phone"
_BINDING = {"binding_ref": "flight.binding.demo"}


def _answers():
    return [
        {
            "source_key": "lead.answers.phone",
            "question_label": "Telefon?",
            "answer": "+48 111",
            "disposition": DISPOSITION_MAP,
            "qualified_code": _PHONE,
        },
        {
            "source_key": "lead.answers.start",
            "question_label": "When can you start?",
            "answer": "Monday",
            "disposition": DISPOSITION_QA_ONLY,
        },
        {
            "source_key": "lead.answers.utm",
            "question_label": "How did you hear about us?",
            "answer": "Facebook",
            "disposition": DISPOSITION_IGNORE,
        },
    ]


def test_cl6_brief_and_runtime_exist() -> None:
    assert _BRIEF.is_file()
    assert _RUNTIME.is_file()
    brief = _BRIEF.read_text(encoding="utf-8")
    assert "CL6 Gate" in brief
    assert "**Phase class:** platform" in brief
    assert "## Original Goal → Completion Proof" in brief
    assert "D4" in brief
    assert "binding" in brief.lower()
    assert "qualified_code" in brief


def test_cl6_map_executes_onto_binding_snapshot() -> None:
    meta = contract_metadata()
    assert meta["contract_id"] == CONTRACT_ID
    assert CONTRACT_ID == "entity_profile_flight_map.v1"
    assert meta["snapshot_on"] == SNAPSHOT_ON_BINDING
    missing = apply_map(DRIVER_CE_PROFILE_CODE, _answers(), binding=None)
    assert missing["ok"] is False
    assert missing["error"] == ERROR_MISSING_BINDING
    result = apply_map(DRIVER_CE_PROFILE_CODE, _answers(), _BINDING)
    assert result["ok"] is True
    assert result["contract_id"] == CONTRACT_ID
    assert result["profile_code"] == DRIVER_CE_PROFILE_CODE
    assert result["binding_ref"] == "flight.binding.demo"
    assert result["snapshot_on"] == SNAPSHOT_ON_BINDING
    assert result["snapshot"] == [
        {
            "source_key": "lead.answers.phone",
            "qualified_code": _PHONE,
            "value": "+48 111",
        }
    ]
    assert is_field_member(DRIVER_CE_PROFILE_CODE, result["snapshot"][0]["qualified_code"])


def test_cl6_qa_only_absent_ignore_dropped() -> None:
    result = apply_map(DRIVER_CE_PROFILE_CODE, _answers(), _BINDING)
    assert result["ok"] is True
    keys = [item["source_key"] for item in result["snapshot"]]
    assert "lead.answers.start" not in keys
    assert "lead.answers.utm" not in keys
    dumped = str(result["snapshot"])
    assert "qa_only" not in dumped
    assert DISPOSITION_QA_ONLY not in dumped
    assert DISPOSITION_IGNORE not in dumped
    for item in result["snapshot"]:
        assert "disposition" not in item
        assert "question_label" not in item
    forced = apply_map(
        DRIVER_CE_PROFILE_CODE,
        {"answers": _answers(), "include_qa_only": True},
        _BINDING,
    )
    assert forced["error"] == ERROR_QA_IN_SNAPSHOT


def test_cl6_dest_is_member_not_question_text_or_extra() -> None:
    minted = apply_map(
        DRIVER_CE_PROFILE_CODE,
        [
            {
                "source_key": "Telefon?",
                "question_label": "Telefon?",
                "answer": "+48",
                "disposition": DISPOSITION_MAP,
                "qualified_code": "phone",
            }
        ],
        _BINDING,
    )
    assert minted["ok"] is False
    assert minted["error"] == ERROR_MINTED_FIELD_SEMANTICS

    extra = apply_map(
        DRIVER_CE_PROFILE_CODE,
        {"answers": _answers(), "write_to": "extra"},
        _BINDING,
    )
    assert extra["error"] == ERROR_WRITE_TO_EXTRA
    copied = apply_map(
        DRIVER_CE_PROFILE_CODE,
        {"answers": _answers(), "copy_to_extra": True},
        _BINDING,
    )
    assert copied["error"] == ERROR_WRITE_TO_EXTRA

    unknown = apply_map(
        DRIVER_CE_PROFILE_CODE,
        [
            {
                "source_key": "lead.answers.other",
                "question_label": "Other",
                "answer": "x",
                "disposition": DISPOSITION_MAP,
                "qualified_code": "recruitment.candidate.not_a_member",
            }
        ],
        _BINDING,
    )
    assert unknown["error"] == ERROR_NON_MEMBER_DEST
    assert not is_field_member(
        DRIVER_CE_PROFILE_CODE, "recruitment.candidate.not_a_member"
    )


def test_cl6_dest_is_profile_not_flight_zapier_or_meta_admin() -> None:
    flight_dest = apply_map(
        DRIVER_CE_PROFILE_CODE,
        [
            {
                "source_key": "lead.answers.phone",
                "question_label": "Telefon?",
                "answer": "+48",
                "disposition": DISPOSITION_MAP,
                "qualified_code": _PHONE,
                "dest": "flight",
            }
        ],
        _BINDING,
    )
    assert flight_dest["error"] == ERROR_DEST_IS_FLIGHT

    zapier = apply_map(
        DRIVER_CE_PROFILE_CODE,
        {"answers": _answers(), "zapier_ux": True},
        _BINDING,
    )
    assert zapier["error"] == ERROR_ZAPIER_UX

    meta = apply_map(
        DRIVER_CE_PROFILE_CODE,
        {"answers": _answers(), "mapping_sot": "meta_admin"},
        _BINDING,
    )
    assert meta["error"] == ERROR_META_ADMIN_SOT
    runtime = _RUNTIME.read_text(encoding="utf-8")
    lowered = runtime.lower()
    assert "zapier" in lowered
    assert "meta" in lowered
    assert "flight entity" in lowered or "flight_entity" in lowered
    assert "mapping_write" in lowered


def test_cl6_d4_places_flight_map_qa_and_information_stay() -> None:
    assert _ZONE.is_file()
    assert _QA.is_file()
    assert _FLIGHT.is_file()
    zone = _ZONE.read_text(encoding="utf-8")
    qa = _QA.read_text(encoding="utf-8")
    flight = _FLIGHT.read_text(encoding="utf-8")
    panel = _PANEL.read_text(encoding="utf-8")
    assert "CandidateInformationLayout" in panel
    assert "CandidateQaPanel" in panel
    assert "CandidateFlightMapPanel" in panel
    assert LAYOUT_CONTRACT_ID in zone
    assert PAGE_TYPE_CANDIDATE_CARD in zone
    assert 'data-host-region="information"' in zone
    assert "intake.form" not in zone
    assert CONTRACT_ID not in zone
    assert QA_CONTRACT_ID not in zone
    assert 'data-host-region="qa"' not in zone
    assert 'data-host-region="flight-map"' not in zone
    assert QA_CONTRACT_ID in qa
    assert 'data-host-region="qa"' in qa
    assert f'data-source="{SOURCE_LEAD_APPLICATION}"' in qa
    assert 'data-survives-convert="true"' in qa
    assert CONTRACT_ID in flight
    assert 'data-host-region="flight-map"' in flight
    assert 'data-snapshot-on="binding"' in flight
    assert 'data-dest="profile"' in flight
    assert 'data-layout-widget="false"' in flight
    assert 'data-writes-to-extra="false"' in flight
    assert 'data-zapier-ux="false"' in flight
    assert 'data-meta-admin-sot="false"' in flight
    assert 'data-flight-entity-dest="false"' in flight
    for spec in PAGE_TYPE_CATALOG.values():
        assert spec["widgets"] == frozenset({FIELD_WIDGET})
        assert "map" not in spec["widgets"]
        assert "flight_map" not in spec["widgets"]
        assert "qa" not in spec["widgets"]


def test_cl6_does_not_ship_stage4_e8_or_drop_columns() -> None:
    runtime = _RUNTIME.read_text(encoding="utf-8")
    lowered = runtime.lower()
    assert "no db column drop" in lowered
    assert "stage 4" in lowered
    assert "DROP COLUMN" not in runtime
    assert "alembic" in lowered
    assert "No alembic" in runtime or "no alembic" in lowered
    assert "e8" in lowered
    assert "dr1-runtime" in lowered or "DR1-runtime" in runtime
    assert "mapping_write" in lowered


def test_cl6_flight_map_boundary_guard() -> None:
    result = subprocess.run(
        [sys.executable, str(_GUARD)],
        cwd=_REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_cl6_named_ci_gate() -> None:
    ci = _CI.read_text(encoding="utf-8")
    assert "CL6 Flight Map Gate" in ci
    assert "test_cl6_flight_map_gate.py" in ci


def test_cl6_gate_filename() -> None:
    assert Path(__file__).name == "test_cl6_flight_map_gate.py"
