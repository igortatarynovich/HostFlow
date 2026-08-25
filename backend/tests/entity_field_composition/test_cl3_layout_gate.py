"""Entity Field Composition CL3 — layout runtime gate.

Seals membership-filtered card layout for D4 Information zone.
No builder. No shared card+form template. No column drop.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from backend.app.entity_profile.constants import DRIVER_CE_PROFILE_CODE
from backend.app.entity_profile.layout_runtime import (
    CONTRACT_ID,
    PAGE_TYPE_CANDIDATE_CARD,
    PAGE_TYPE_INTAKE_FORM,
    contract_metadata,
    list_page_types,
    page_type_mode,
    resolve_layout,
)
from backend.app.entity_profile.membership_runtime import (
    CONTRACT_ID as MEMBERSHIP_CONTRACT_ID,
    is_field_member,
    resolve_membership,
)
from backend.app.field_registry.constants import DEFAULT_CANDIDATE_LAYOUT_CODE

_REPO_ROOT = Path(__file__).resolve().parents[3]
_BRIEF = _REPO_ROOT / "docs" / "specs" / "tasks" / "entity-field-composition-cl3-layout.md"
_RUNTIME = _REPO_ROOT / "backend" / "app" / "entity_profile" / "layout_runtime.py"
_GUARD = _REPO_ROOT / "scripts" / "architecture" / "check_entity_profile_layout_boundary.py"
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

_NOT_MEMBERS = (
    "recruitment.candidate.operations.stage",
    "recruitment.candidate.agreements.general",
    "recruitment.candidate.contacts.phone_country_code",
)


def test_cl3_brief_and_runtime_exist() -> None:
    assert _BRIEF.is_file()
    assert _RUNTIME.is_file()
    brief = _BRIEF.read_text(encoding="utf-8")
    assert "CL3 Gate" in brief
    assert "D4 Information zone" in brief or "Information zone" in brief


def test_cl3_contract_and_closed_page_types() -> None:
    meta = contract_metadata()
    assert meta["contract_id"] == CONTRACT_ID
    assert CONTRACT_ID == "entity_profile_layout.v1"
    assert set(list_page_types()) == {PAGE_TYPE_CANDIDATE_CARD, PAGE_TYPE_INTAKE_FORM}
    assert page_type_mode(PAGE_TYPE_CANDIDATE_CARD) == "card"
    assert page_type_mode(PAGE_TYPE_INTAKE_FORM) == "form"
    assert page_type_mode("admin.minted") is None


def test_cl3_driver_ce_card_is_membership_subset() -> None:
    membership = resolve_membership(DRIVER_CE_PROFILE_CODE)
    layout = resolve_layout(DRIVER_CE_PROFILE_CODE, PAGE_TYPE_CANDIDATE_CARD)
    assert membership is not None
    assert layout is not None
    assert layout["contract_id"] == CONTRACT_ID
    assert layout["membership_contract_id"] == MEMBERSHIP_CONTRACT_ID
    assert layout["page_type"] == PAGE_TYPE_CANDIDATE_CARD
    assert layout["mode"] == "card"
    assert layout["layout_code"] == DEFAULT_CANDIDATE_LAYOUT_CODE
    codes = [row["qualified_code"] for row in layout["fields"]]
    assert codes
    assert len(codes) == len(set(codes))
    for code in codes:
        assert is_field_member(DRIVER_CE_PROFILE_CODE, code)
        assert row_widget(layout, code) == "field"
    for code in _NOT_MEMBERS:
        assert code not in set(codes)
        assert not is_field_member(DRIVER_CE_PROFILE_CODE, code)


def row_widget(layout: dict, qualified_code: str) -> str:
    for row in layout["fields"]:
        if row["qualified_code"] == qualified_code:
            return str(row["widget"])
    raise AssertionError(qualified_code)


def test_cl3_card_presence_comes_from_membership_not_layout_required() -> None:
    layout = resolve_layout(DRIVER_CE_PROFILE_CODE, PAGE_TYPE_CANDIDATE_CARD)
    assert layout is not None
    dumped = json.dumps(layout)
    assert "transition" not in dumped
    assert "handoff" not in dumped
    phone = next(
        row
        for row in layout["fields"]
        if row["qualified_code"] == "recruitment.candidate.contacts.phone"
    )
    assert phone["presence"]["card_save"] == "required"
    assert "required" not in phone
    assert set(phone["presence"]) == {"card_save"}


def test_cl3_form_page_type_is_catalogued_not_resolved() -> None:
    assert PAGE_TYPE_INTAKE_FORM in list_page_types()
    assert resolve_layout(DRIVER_CE_PROFILE_CODE, PAGE_TYPE_INTAKE_FORM) is None
    assert resolve_layout(DRIVER_CE_PROFILE_CODE, "not.a.page") is None
    assert resolve_layout("not.a.profile", PAGE_TYPE_CANDIDATE_CARD) is None
    card = resolve_layout(DRIVER_CE_PROFILE_CODE, PAGE_TYPE_CANDIDATE_CARD)
    assert card is not None
    assert card["mode"] != page_type_mode(PAGE_TYPE_INTAKE_FORM)


def test_cl3_d4_information_zone_places_card_layout() -> None:
    assert _ZONE.is_file()
    zone = _ZONE.read_text(encoding="utf-8")
    panel = _PANEL.read_text(encoding="utf-8")
    assert "CandidateInformationLayout" in panel
    assert CONTRACT_ID in zone
    assert PAGE_TYPE_CANDIDATE_CARD in zone
    assert 'data-host-region="information"' in zone
    assert "data-entity-workspace-slot=\"overview\"" in panel
    assert "intake.form" not in zone


def test_cl3_does_not_ship_builder_or_drop_columns() -> None:
    runtime = _RUNTIME.read_text(encoding="utf-8")
    lowered = runtime.lower()
    assert "builder" in lowered
    assert "no db column drop" in lowered
    assert "DROP COLUMN" not in runtime
    assert "alembic" not in lowered


def test_cl3_layout_boundary_guard() -> None:
    result = subprocess.run(
        [sys.executable, str(_GUARD)],
        cwd=_REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_cl3_named_ci_gate() -> None:
    ci = _CI.read_text(encoding="utf-8")
    assert "CL3 Layout Gate" in ci
    assert "test_cl3_layout_gate.py" in ci


def test_cl3_gate_filename() -> None:
    assert Path(__file__).name == "test_cl3_layout_gate.py"
