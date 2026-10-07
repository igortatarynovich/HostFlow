"""RSO-2B — Emit ready_for_employment.v1 on Transfer (manifest gate).

Named gate: rso2-emit-manifest-gate
Does not open RSO-2C / Slice 4 / Full Spine.
"""

from __future__ import annotations

import inspect
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from backend.app.reference.ready_for_employment import (
    CONTRACT_ID,
    is_valid_ready_for_employment_package_v1,
    validate_ready_for_employment_package_v1,
)
from backend.app.services import handoff as handoff_service
from backend.app.services.ready_for_employment_emit import (
    HandoffManifestValidationError,
    build_ready_for_employment_package_v1,
)

_REPO_ROOT = Path(__file__).resolve().parents[3]
_BRIEF = _REPO_ROOT / "docs" / "specs" / "tasks" / "recruitment-employment-handoff-rso2b-emit.md"
_EMIT = _REPO_ROOT / "backend" / "app" / "services" / "ready_for_employment_emit.py"
_SNAPSHOT = _REPO_ROOT / "backend" / "app" / "services" / "handoff_snapshot.py"
_HANDOFF = _REPO_ROOT / "backend" / "app" / "services" / "handoff.py"
_VAC_ROUTER = _REPO_ROOT / "backend" / "app" / "api" / "v1" / "vacancies" / "router.py"
_CI = _REPO_ROOT / ".github" / "workflows" / "backend-ci.yml"


def test_rso2_emit_gate_filename() -> None:
    assert Path(__file__).name == "test_rso2_emit_manifest_gate.py"


def test_brief_and_ci_wire() -> None:
    brief = _BRIEF.read_text(encoding="utf-8")
    assert "rso2-emit-manifest-gate" in brief
    assert "validate_ready_for_employment_package_v1" in brief
    assert "RSO-2C" in brief
    assert "Slice 4" in brief
    assert "create_handoff" in brief
    ci = _CI.read_text(encoding="utf-8")
    assert "test_rso2_emit_manifest_gate.py" in ci


def test_no_accept_or_employment_init_in_emit_path() -> None:
    emit = _EMIT.read_text(encoding="utf-8")
    snap = _SNAPSHOT.read_text(encoding="utf-8")
    assert "accept_handoff" not in emit
    assert "apply_employment_accept_policy" not in emit
    assert "handoff_from_candidate" not in emit
    assert "confirm_employment_started" not in emit
    assert "build_and_validate_ready_for_employment_package_v1" in snap
    create_fn = inspect.getsource(handoff_service.create_handoff)
    assert "accept_handoff(" not in create_fn
    assert "apply_employment_accept_policy" not in create_fn
    assert "persist_handoff_create_snapshot" in create_fn


def test_vacancy_router_has_handoff_lane_adapt() -> None:
    src = _VAC_ROUTER.read_text(encoding="utf-8")
    assert "vacancy_is_handoff_target_for_hr_lane" in src
    assert "is_hr_workspace_actor" in src


@pytest.mark.asyncio
async def test_build_package_validates_and_has_contract_id(monkeypatch: pytest.MonkeyPatch) -> None:
    db = AsyncMock()
    cand = MagicMock()
    cand.id = "cand-1"
    cand.first_name = "Ada"
    cand.last_name = "Lovelace"
    cand.vacancy_id = "vac-1"
    cand.company_id = "co-1"
    cand.own_company_id = None
    cand.recruiter_id = "rec-1"
    cand.stage = "ready_for_handoff"
    cand._get_personal_data = MagicMock(return_value={"citizenship": "UA"})
    cand._get_extra = MagicMock(return_value={})
    cand._get_contacts = MagicMock(return_value={"email": "ada@example.com", "phone": "+48111"})
    cand.email = "ada@example.com"
    cand.phone = "+48111"
    cand.birth_date = None
    cand.note = None
    cand.source = None
    cand.origin = None

    handoff = MagicMock()
    handoff.id = "ho-1"
    handoff.agency_tenant_id = "ten-1"
    handoff.application_id = "app-1"
    handoff.client_company_id = "co-1"
    handoff.to_company_id = None
    handoff.requested_by_user_id = "user-1"
    handoff.requested_at = None
    handoff.destination = "internal_hr"

    app = MagicMock()
    app.id = "app-1"
    app.vacancy_id = "vac-1"
    app.recruiter_id = "rec-1"
    app.status = "ready_for_handoff"
    app.lead_id = None
    app.source = "meta"

    vac = MagicMock()
    vac.id = "vac-1"
    vac.title = "Driver CE"
    vac.company_id = "co-1"

    async def _get(_model, key):
        if key == "vac-1":
            return vac
        return None

    db.get = AsyncMock(side_effect=_get)

    monkeypatch.setattr(
        "backend.app.services.ready_for_employment_emit.get_application_for_handoff",
        AsyncMock(return_value=app),
    )
    monkeypatch.setattr(
        "backend.app.services.ready_for_employment_emit.list_candidate_documents",
        AsyncMock(return_value=[]),
    )
    monkeypatch.setattr(
        "backend.app.services.candidate_evidence_service.build_requirement_fulfillments_for_candidate",
        AsyncMock(return_value=[]),
    )
    pkg = await build_ready_for_employment_package_v1(db, handoff=handoff, candidate=cand)

    assert pkg["contract_id"] == CONTRACT_ID
    assert validate_ready_for_employment_package_v1(pkg) == []
    assert is_valid_ready_for_employment_package_v1(pkg)
    assert pkg["person"]["candidate_id"] == "cand-1"
    assert pkg["target_work"]["vacancy_id"] == "vac-1"
    assert pkg["target_work"]["employer_id"] == "co-1"
    assert pkg["fits_decision"]["decision"] == "fits"
    assert pkg["context_refs"]["application_id"] == "app-1"
    assert "document_refs" in pkg["evidence"]
    assert "files" not in pkg["evidence"]


def test_persist_internal_hr_uses_rfe_not_legacy_builder() -> None:
    src = _SNAPSHOT.read_text(encoding="utf-8")
    assert 'if dest == "internal_hr"' in src
    assert "build_and_validate_ready_for_employment_package_v1" in src
    assert "build_handoff_snapshot_payload_v1" in src


def test_handoff_manifest_validation_error_shape() -> None:
    err = HandoffManifestValidationError(["missing required key: fits_decision"])
    assert err.errors == ["missing required key: fits_decision"]
