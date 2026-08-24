"""Entity Field Composition CL2 — membership runtime gate.

Seals Entity Profile membership projection for driver_ce: canonical fields
+ baseline presence (intake / card_save) + pack/layout/process refs.
No layout runtime. No transition/handoff on Profile fields. No column drop.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from backend.app.entity_profile.constants import (
    DRIVER_CE_DOCUMENT_PACK_CODE,
    DRIVER_CE_PROFILE_CODE,
    DRIVER_CE_SCREENING_PACK_CODE,
)
from backend.app.entity_profile.membership_runtime import (
    CONTRACT_ID,
    FORBIDDEN_PROFILE_CONTEXTS,
    MEMBERSHIP_CONTEXTS,
    contract_metadata,
    is_field_member,
    presence_level,
    resolve_membership,
)
from backend.app.field_registry.constants import DEFAULT_CANDIDATE_LAYOUT_CODE

_REPO_ROOT = Path(__file__).resolve().parents[3]
_BRIEF = _REPO_ROOT / "docs" / "specs" / "tasks" / "entity-field-composition-cl2-membership.md"
_RUNTIME = _REPO_ROOT / "backend" / "app" / "entity_profile" / "membership_runtime.py"
_GUARD = _REPO_ROOT / "scripts" / "architecture" / "check_entity_profile_membership_boundary.py"
_CI = _REPO_ROOT / ".github" / "workflows" / "backend-ci.yml"

_DRIVER_CE_MEMBERS = frozenset(
    {
        "recruitment.candidate.first_name",
        "recruitment.candidate.last_name",
        "recruitment.candidate.contacts.phone",
        "recruitment.candidate.contacts.email",
        "platform.identity.citizenship",
        "platform.identity.birth_date",
        "platform.identity.address",
        "recruitment.candidate.experience.years_ce",
        "recruitment.candidate.experience.trailer_types[]",
        "recruitment.candidate.experience.route_types[]",
        "recruitment.candidate.personal.in_poland",
    }
)

_NOT_MEMBERS = frozenset(
    {
        "recruitment.candidate.operations.stage",
        "recruitment.candidate.agreements.general",
        "recruitment.candidate.contacts.phone_country_code",
    }
)


def test_cl2_brief_and_runtime_exist() -> None:
    assert _BRIEF.is_file()
    assert _RUNTIME.is_file()
    brief = _BRIEF.read_text(encoding="utf-8")
    assert "CL2 Gate" in brief
    assert "Membership runtime" in brief or "membership runtime" in brief.lower()


def test_cl2_contract_metadata() -> None:
    meta = contract_metadata()
    assert meta["contract_id"] == CONTRACT_ID
    assert CONTRACT_ID == "entity_profile_membership.v1"


def test_cl2_driver_ce_membership_matches_inventory_codes() -> None:
    membership = resolve_membership(DRIVER_CE_PROFILE_CODE)
    assert membership is not None
    assert membership["contract_id"] == CONTRACT_ID
    assert membership["profile_code"] == DRIVER_CE_PROFILE_CODE
    codes = {row["qualified_code"] for row in membership["fields"]}
    assert codes == _DRIVER_CE_MEMBERS
    assert membership["custom_fields"] == []
    assert all(row["is_member"] is True for row in membership["fields"])
    assert all(row["kind"] == "canonical" for row in membership["fields"])


def test_cl2_is_field_member_producer() -> None:
    assert is_field_member(DRIVER_CE_PROFILE_CODE, "recruitment.candidate.first_name")
    assert is_field_member(DRIVER_CE_PROFILE_CODE, "platform.identity.address")
    for code in _NOT_MEMBERS:
        assert not is_field_member(DRIVER_CE_PROFILE_CODE, code)
    assert not is_field_member("not.a.profile", "recruitment.candidate.first_name")
    assert resolve_membership("not.a.profile") is None


def test_cl2_baseline_presence_omits_transition_handoff() -> None:
    membership = resolve_membership(DRIVER_CE_PROFILE_CODE)
    assert membership is not None
    dumped = json.dumps(membership)
    assert "transition" not in dumped
    assert "handoff" not in dumped
    assert "transition_level" not in dumped
    for row in membership["fields"]:
        assert set(row["presence"]) == MEMBERSHIP_CONTEXTS
        assert "transition" not in row
        assert "handoff" not in row

    assert presence_level(
        DRIVER_CE_PROFILE_CODE, "recruitment.candidate.first_name", "intake"
    ) == "required"
    assert presence_level(
        DRIVER_CE_PROFILE_CODE, "recruitment.candidate.contacts.phone", "card_save"
    ) == "required"
    assert presence_level(
        DRIVER_CE_PROFILE_CODE, "platform.identity.address", "card_save"
    ) == "required"
    for ctx in FORBIDDEN_PROFILE_CONTEXTS:
        assert (
            presence_level(DRIVER_CE_PROFILE_CODE, "platform.identity.address", ctx)
            is None
        )


def test_cl2_screening_is_pack_ref_not_field_required() -> None:
    membership = resolve_membership(DRIVER_CE_PROFILE_CODE)
    assert membership is not None
    refs = membership["refs"]
    assert refs["screening_pack_code"] == DRIVER_CE_SCREENING_PACK_CODE
    assert refs["document_pack_code"] == DRIVER_CE_DOCUMENT_PACK_CODE
    assert refs["default_layout_code"] == DEFAULT_CANDIDATE_LAYOUT_CODE
    assert refs["process_profile_code"]
    years = next(
        row
        for row in membership["fields"]
        if row["qualified_code"] == "recruitment.candidate.experience.years_ce"
    )
    assert years["presence"]["card_save"] == "required"
    assert "screening" not in years
    assert years.get("kind") != "screening"


def test_cl2_does_not_ship_layout_or_drop_columns() -> None:
    runtime = _RUNTIME.read_text(encoding="utf-8")
    lowered = runtime.lower()
    assert "no db column drop" in lowered or "no column drop" in lowered
    assert "layout" in lowered
    assert "DROP COLUMN" not in runtime
    assert "alembic" not in lowered
    assert "transition" in lowered
    assert "handoff" in lowered


def test_cl2_membership_boundary_guard() -> None:
    result = subprocess.run(
        [sys.executable, str(_GUARD)],
        cwd=_REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_cl2_named_ci_gate() -> None:
    ci = _CI.read_text(encoding="utf-8")
    assert "CL2 Membership Gate" in ci
    assert "test_cl2_membership_gate.py" in ci


def test_cl2_gate_filename() -> None:
    assert Path(__file__).name == "test_cl2_membership_gate.py"
