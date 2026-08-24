"""Entity Field Composition CL4 — builder runtime gate.

Seals two-mode compile (card vs form) over a closed page-type catalog.
No Q&A. No Flight. No shared card+form template. No column drop.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from backend.app.entity_profile.builder_runtime import (
    ARTIFACT_FORM_DEFINITION,
    ARTIFACT_LAYOUT_INSTANCE,
    CONTRACT_ID,
    ERROR_DISALLOWED_WIDGET,
    ERROR_MINTED_FIELD_SEMANTICS,
    ERROR_MIXED_DRAFT,
    ERROR_MODE_MISMATCH,
    ERROR_NON_MEMBER_FIELD,
    ERROR_UNKNOWN_PAGE_TYPE,
    MODE_CARD,
    MODE_FORM,
    WRITES_TO_FORMS_PLATFORM,
    WRITES_TO_LAYOUT_REGISTRY,
    compile_draft,
    contract_metadata,
    list_builder_modes,
    palette,
)
from backend.app.entity_profile.constants import DRIVER_CE_PROFILE_CODE
from backend.app.entity_profile.layout_runtime import (
    CONTRACT_ID as LAYOUT_CONTRACT_ID,
    PAGE_TYPE_CANDIDATE_CARD,
    PAGE_TYPE_INTAKE_FORM,
    resolve_layout,
)
from backend.app.entity_profile.membership_runtime import is_field_member

_REPO_ROOT = Path(__file__).resolve().parents[3]
_BRIEF = _REPO_ROOT / "docs" / "specs" / "tasks" / "entity-field-composition-cl4-builder.md"
_RUNTIME = _REPO_ROOT / "backend" / "app" / "entity_profile" / "builder_runtime.py"
_GUARD = _REPO_ROOT / "scripts" / "architecture" / "check_entity_profile_builder_boundary.py"
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
_BUILDER = (
    _REPO_ROOT
    / "hostflow-frontend"
    / "src"
    / "platform"
    / "entity-workspace"
    / "CandidateCompositionBuilder.tsx"
)

_PHONE = "recruitment.candidate.contacts.phone"
_NOT_MEMBER = "recruitment.candidate.operations.stage"


def _card_draft(**extra):
    draft = {
        "profile_code": DRIVER_CE_PROFILE_CODE,
        "page_type": PAGE_TYPE_CANDIDATE_CARD,
        "mode": MODE_CARD,
        "placements": [{"qualified_code": _PHONE, "widget": "field"}],
    }
    draft.update(extra)
    return draft


def _form_draft(**extra):
    draft = {
        "profile_code": DRIVER_CE_PROFILE_CODE,
        "page_type": PAGE_TYPE_INTAKE_FORM,
        "mode": MODE_FORM,
        "placements": [{"qualified_code": _PHONE, "widget": "field"}],
    }
    draft.update(extra)
    return draft


def test_cl4_brief_and_runtime_exist() -> None:
    assert _BRIEF.is_file()
    assert _RUNTIME.is_file()
    brief = _BRIEF.read_text(encoding="utf-8")
    assert "CL4 Gate" in brief
    assert "**Phase class:** platform" in brief
    assert "## Original Goal → Completion Proof" in brief
    assert "D4 Information zone" in brief or "Information zone" in brief


def test_cl4_two_modes_closed_catalog() -> None:
    meta = contract_metadata()
    assert meta["contract_id"] == CONTRACT_ID
    assert CONTRACT_ID == "entity_profile_builder.v1"
    assert list_builder_modes() == (MODE_CARD, MODE_FORM)
    assert palette(DRIVER_CE_PROFILE_CODE, "admin.minted") is None
    assert compile_draft(_card_draft(page_type="admin.minted"))["error"] == ERROR_UNKNOWN_PAGE_TYPE


def test_cl4_palette_is_membership_plus_allowlisted_widgets() -> None:
    card = palette(DRIVER_CE_PROFILE_CODE, PAGE_TYPE_CANDIDATE_CARD)
    form = palette(DRIVER_CE_PROFILE_CODE, PAGE_TYPE_INTAKE_FORM)
    assert card is not None and form is not None
    assert card["mode"] == MODE_CARD
    assert form["mode"] == MODE_FORM
    assert card["writes_to"] == WRITES_TO_LAYOUT_REGISTRY
    assert form["writes_to"] == WRITES_TO_FORMS_PLATFORM
    assert card["widgets"] == ("field",)
    codes = {row["qualified_code"] for row in card["fields"]}
    assert _PHONE in codes
    assert _NOT_MEMBER not in codes
    for row in card["fields"]:
        assert is_field_member(DRIVER_CE_PROFILE_CODE, row["qualified_code"])


def test_cl4_card_compile_writes_layout_instance() -> None:
    result = compile_draft(_card_draft())
    assert result["ok"] is True
    assert result["artifact_kind"] == ARTIFACT_LAYOUT_INSTANCE
    assert result["writes_to"] == WRITES_TO_LAYOUT_REGISTRY
    artifact = result["artifact"]
    assert artifact["contract_id"] == LAYOUT_CONTRACT_ID
    assert artifact["page_type"] == PAGE_TYPE_CANDIDATE_CARD
    assert artifact["mode"] == MODE_CARD
    codes = [row["qualified_code"] for row in artifact["fields"]]
    assert codes == [_PHONE]
    for code in codes:
        assert is_field_member(DRIVER_CE_PROFILE_CODE, code)
    assert "required" not in artifact["fields"][0]
    assert set(artifact["fields"][0]["presence"]) == {"card_save"}


def test_cl4_form_compile_writes_form_definition_not_layout() -> None:
    result = compile_draft(_form_draft())
    assert result["ok"] is True
    assert result["artifact_kind"] == ARTIFACT_FORM_DEFINITION
    assert result["writes_to"] == WRITES_TO_FORMS_PLATFORM
    artifact = result["artifact"]
    assert artifact["page_type"] == PAGE_TYPE_INTAKE_FORM
    assert artifact["mode"] == MODE_FORM
    assert artifact.get("contract_id") != LAYOUT_CONTRACT_ID
    assert "layout_code" not in artifact
    assert resolve_layout(DRIVER_CE_PROFILE_CODE, PAGE_TYPE_INTAKE_FORM) is None
    assert "resolve_layout" not in _form_compile_source()


def _form_compile_source() -> str:
    runtime = _RUNTIME.read_text(encoding="utf-8")
    start = runtime.index("def _form_definition_artifact")
    return runtime[start:]


def test_cl4_card_and_form_are_different_artifacts() -> None:
    card = compile_draft(_card_draft())
    form = compile_draft(_form_draft())
    assert card["artifact_kind"] != form["artifact_kind"]
    assert card["writes_to"] != form["writes_to"]
    assert card["artifact"] != form["artifact"]
    assert {card["artifact_kind"], form["artifact_kind"]} == {
        ARTIFACT_LAYOUT_INSTANCE,
        ARTIFACT_FORM_DEFINITION,
    }


def test_cl4_rejects_mixed_mode_mismatch_non_member_widget_and_minted_name() -> None:
    mixed = compile_draft(
        {
            "profile_code": DRIVER_CE_PROFILE_CODE,
            "page_type": PAGE_TYPE_CANDIDATE_CARD,
            "mode": MODE_CARD,
            "card_placements": [{"qualified_code": _PHONE, "widget": "field"}],
            "form_placements": [{"qualified_code": _PHONE, "widget": "field"}],
        }
    )
    assert mixed["ok"] is False
    assert mixed["error"] == ERROR_MIXED_DRAFT

    mismatch = compile_draft(_card_draft(mode=MODE_FORM))
    assert mismatch["error"] == ERROR_MODE_MISMATCH

    non_member = compile_draft(
        _card_draft(placements=[{"qualified_code": _NOT_MEMBER, "widget": "field"}])
    )
    assert non_member["error"] == ERROR_NON_MEMBER_FIELD

    bad_widget = compile_draft(
        _card_draft(placements=[{"qualified_code": _PHONE, "widget": "qa_block"}])
    )
    assert bad_widget["error"] == ERROR_DISALLOWED_WIDGET

    minted = compile_draft(
        _card_draft(placements=[{"qualified_code": "phone", "widget": "field"}])
    )
    assert minted["error"] == ERROR_MINTED_FIELD_SEMANTICS


def test_cl4_d4_places_card_not_form() -> None:
    assert _ZONE.is_file()
    assert _BUILDER.is_file()
    zone = _ZONE.read_text(encoding="utf-8")
    builder = _BUILDER.read_text(encoding="utf-8")
    panel = _PANEL.read_text(encoding="utf-8")
    assert "CandidateInformationLayout" in panel
    assert "CandidateCompositionBuilder" in panel
    assert LAYOUT_CONTRACT_ID in zone
    assert PAGE_TYPE_CANDIDATE_CARD in zone
    assert "intake.form" not in zone
    assert CONTRACT_ID in builder
    assert 'data-builder-modes="card,form"' in builder
    assert 'data-artifact-kind="layout_instance"' in builder
    assert 'data-writes-to="layout_registry"' in builder
    assert 'data-places-on-d4="true"' in builder
    assert 'data-artifact-kind="form_definition"' in builder
    assert 'data-writes-to="forms_platform"' in builder
    assert 'data-places-on-d4="false"' in builder
    assert "intake.form" in builder


def test_cl4_does_not_ship_qa_flight_or_drop_columns() -> None:
    runtime = _RUNTIME.read_text(encoding="utf-8")
    lowered = runtime.lower()
    assert "no db column drop" in lowered
    assert "q&a" in lowered or "qa" in lowered
    assert "flight" in lowered
    assert "DROP COLUMN" not in runtime
    assert "alembic" in lowered
    assert "No alembic" in runtime or "no alembic" in lowered


def test_cl4_builder_boundary_guard() -> None:
    result = subprocess.run(
        [sys.executable, str(_GUARD)],
        cwd=_REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_cl4_named_ci_gate() -> None:
    ci = _CI.read_text(encoding="utf-8")
    assert "CL4 Builder Gate" in ci
    assert "test_cl4_builder_gate.py" in ci


def test_cl4_gate_filename() -> None:
    assert Path(__file__).name == "test_cl4_builder_gate.py"
