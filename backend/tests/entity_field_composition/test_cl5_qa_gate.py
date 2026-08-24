"""Entity Field Composition CL5 — Recruiter Q&A gate.

Seals qa_only as a named artifact from Lead / Application.
Map is recognized, not executed (CL6). Ignore dropped.
No extra copy. No minted fields from question text. No column drop.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from backend.app.entity_profile.constants import DRIVER_CE_PROFILE_CODE
from backend.app.entity_profile.layout_runtime import (
    CONTRACT_ID as LAYOUT_CONTRACT_ID,
    FIELD_WIDGET,
    PAGE_TYPE_CANDIDATE_CARD,
    PAGE_TYPE_CATALOG,
)
from backend.app.entity_profile.membership_runtime import is_field_member
from backend.app.entity_profile.qa_runtime import (
    CONTRACT_ID,
    DISPOSITION_IGNORE,
    DISPOSITION_MAP,
    DISPOSITION_QA_ONLY,
    ERROR_HIDDEN_AFTER_CONVERT,
    ERROR_MAP_IS_CL6,
    ERROR_MINTED_FIELD_SEMANTICS,
    ERROR_QA_ON_MEMBERSHIP,
    ERROR_UNKNOWN_DISPOSITION,
    ERROR_WRITE_TO_EXTRA,
    SOURCE_LEAD_APPLICATION,
    contract_metadata,
    list_qa_dispositions,
    resolve_qa,
)

_REPO_ROOT = Path(__file__).resolve().parents[3]
_BRIEF = _REPO_ROOT / "docs" / "specs" / "tasks" / "entity-field-composition-cl5-qa.md"
_RUNTIME = _REPO_ROOT / "backend" / "app" / "entity_profile" / "qa_runtime.py"
_GUARD = _REPO_ROOT / "scripts" / "architecture" / "check_entity_profile_qa_boundary.py"
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

_PHONE = "recruitment.candidate.contacts.phone"


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


def test_cl5_brief_and_runtime_exist() -> None:
    assert _BRIEF.is_file()
    assert _RUNTIME.is_file()
    brief = _BRIEF.read_text(encoding="utf-8")
    assert "CL5 Gate" in brief
    assert "**Phase class:** platform" in brief
    assert "## Original Goal → Completion Proof" in brief
    assert "D4" in brief
    assert "lead_application" in brief or "Lead / Application" in brief


def test_cl5_two_plus_dispositions_resolve_emits_only_qa_only() -> None:
    meta = contract_metadata()
    assert meta["contract_id"] == CONTRACT_ID
    assert CONTRACT_ID == "entity_profile_qa.v1"
    catalogued = list_qa_dispositions()
    assert len(catalogued) >= 2
    assert catalogued == (DISPOSITION_MAP, DISPOSITION_QA_ONLY, DISPOSITION_IGNORE)
    result = resolve_qa(DRIVER_CE_PROFILE_CODE, _answers())
    assert result["ok"] is True
    assert result["contract_id"] == CONTRACT_ID
    assert result["profile_code"] == DRIVER_CE_PROFILE_CODE
    assert result["source"] == SOURCE_LEAD_APPLICATION
    assert {item["disposition"] for item in result["items"]} == {DISPOSITION_QA_ONLY}
    assert [item["source_key"] for item in result["items"]] == ["lead.answers.start"]


def test_cl5_mapped_members_absent_ignore_dropped() -> None:
    result = resolve_qa(DRIVER_CE_PROFILE_CODE, _answers())
    assert result["ok"] is True
    keys = [item["source_key"] for item in result["items"]]
    assert "lead.answers.phone" not in keys
    assert "lead.answers.utm" not in keys
    dumped = str(result["items"])
    assert _PHONE not in dumped
    for item in result["items"]:
        assert "qualified_code" not in item
        assert not is_field_member(DRIVER_CE_PROFILE_CODE, item["source_key"])


def test_cl5_question_text_is_not_a_qualified_field_and_no_extra_write() -> None:
    minted = resolve_qa(
        DRIVER_CE_PROFILE_CODE,
        [
            {
                "source_key": "Telefon?",
                "question_label": "Telefon?",
                "answer": "+48",
                "disposition": DISPOSITION_QA_ONLY,
                "qualified_code": "phone",
            }
        ],
    )
    assert minted["ok"] is False
    assert minted["error"] == ERROR_MINTED_FIELD_SEMANTICS

    extra = resolve_qa(
        DRIVER_CE_PROFILE_CODE,
        {"answers": _answers(), "write_to": "extra"},
    )
    assert extra["error"] == ERROR_WRITE_TO_EXTRA
    copied = resolve_qa(
        DRIVER_CE_PROFILE_CODE,
        {"answers": _answers(), "source": "extra"},
    )
    assert copied["error"] == ERROR_WRITE_TO_EXTRA

    on_membership = resolve_qa(
        DRIVER_CE_PROFILE_CODE,
        [
            {
                "source_key": _PHONE,
                "question_label": "Phone",
                "answer": "+48",
                "disposition": DISPOSITION_QA_ONLY,
            }
        ],
    )
    assert on_membership["error"] == ERROR_QA_ON_MEMBERSHIP


def test_cl5_survives_convert_and_rejects_hide() -> None:
    result = resolve_qa(DRIVER_CE_PROFILE_CODE, _answers())
    assert result["survives_convert"] is True
    hidden = resolve_qa(
        DRIVER_CE_PROFILE_CODE,
        {"answers": _answers(), "hide_after_convert": True},
    )
    assert hidden["ok"] is False
    assert hidden["error"] == ERROR_HIDDEN_AFTER_CONVERT


def test_cl5_recognizes_map_but_does_not_execute() -> None:
    unknown = resolve_qa(
        DRIVER_CE_PROFILE_CODE,
        [
            {
                "source_key": "lead.answers.start",
                "question_label": "When?",
                "answer": "Monday",
                "disposition": "archive",
            }
        ],
    )
    assert unknown["error"] == ERROR_UNKNOWN_DISPOSITION

    executed = resolve_qa(
        DRIVER_CE_PROFILE_CODE,
        {"answers": _answers(), "execute_map": True},
    )
    assert executed["ok"] is False
    assert executed["error"] == ERROR_MAP_IS_CL6

    item_execute = resolve_qa(
        DRIVER_CE_PROFILE_CODE,
        [
            {
                "source_key": "lead.answers.phone",
                "question_label": "Telefon?",
                "answer": "+48",
                "disposition": DISPOSITION_MAP,
                "qualified_code": _PHONE,
                "flight_snapshot": {"phone": "+48"},
            }
        ],
    )
    assert item_execute["error"] == ERROR_MAP_IS_CL6
    runtime = _RUNTIME.read_text(encoding="utf-8")
    assert "def execute_map" not in runtime
    assert "flight_snapshot" in runtime.lower()
    assert "CL6" in runtime


def test_cl5_d4_places_qa_zone_information_stays_card() -> None:
    assert _ZONE.is_file()
    assert _QA.is_file()
    zone = _ZONE.read_text(encoding="utf-8")
    qa = _QA.read_text(encoding="utf-8")
    panel = _PANEL.read_text(encoding="utf-8")
    assert "CandidateInformationLayout" in panel
    assert "CandidateQaPanel" in panel
    assert LAYOUT_CONTRACT_ID in zone
    assert PAGE_TYPE_CANDIDATE_CARD in zone
    assert 'data-host-region="information"' in zone
    assert "intake.form" not in zone
    assert CONTRACT_ID not in zone
    assert 'data-host-region="qa"' not in zone
    assert CONTRACT_ID in qa
    assert 'data-host-region="qa"' in qa
    assert 'data-source="lead_application"' in qa
    assert 'data-survives-convert="true"' in qa
    assert 'data-layout-widget="false"' in qa
    assert 'data-writes-to-extra="false"' in qa
    assert 'data-executes-map="false"' in qa
    for spec in PAGE_TYPE_CATALOG.values():
        assert spec["widgets"] == frozenset({FIELD_WIDGET})
        assert "qa" not in spec["widgets"]
        assert "qa_block" not in spec["widgets"]


def test_cl5_does_not_ship_flight_e8_or_drop_columns() -> None:
    runtime = _RUNTIME.read_text(encoding="utf-8")
    lowered = runtime.lower()
    assert "no db column drop" in lowered
    assert "q&a" in lowered or "qa" in lowered
    assert "flight" in lowered
    assert "DROP COLUMN" not in runtime
    assert "alembic" in lowered
    assert "No alembic" in runtime or "no alembic" in lowered
    assert "e8" in lowered
    assert "dr1-runtime" in lowered or "DR1-runtime" in runtime


def test_cl5_qa_boundary_guard() -> None:
    result = subprocess.run(
        [sys.executable, str(_GUARD)],
        cwd=_REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_cl5_named_ci_gate() -> None:
    ci = _CI.read_text(encoding="utf-8")
    assert "CL5 Q&A Gate" in ci
    assert "test_cl5_qa_gate.py" in ci


def test_cl5_gate_filename() -> None:
    assert Path(__file__).name == "test_cl5_qa_gate.py"
