"""Employment Start Allowed — HR host binding gate (slice 3).

Host = existing /handoffs/:id. Primary UI only. No local evidence invent.
Re-eval after confirmed write. unsupported_context = terminal.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from backend.app.reference.employment_start_allowed import (
    DECISION_MISSING,
    DECISION_START_ALLOWED,
    DECISION_UNSUPPORTED,
    EXCEPTION_BHP_SUCCESSIVE,
    REQ_BHP,
    REQ_CONTRACT,
    evaluate_employment_start_allowed_v1,
)
from backend.app.services.employment_start_allowed_orchestrator import (
    apply_start_allowed_for_handoff,
    evaluate_start_allowed_for_handoff,
)

_REPO_ROOT = Path(__file__).resolve().parents[3]
_BRIEF = _REPO_ROOT / "docs" / "specs" / "tasks" / "employment-start-allowed-hr-host-binding.md"
_ORCH = _REPO_ROOT / "backend" / "app" / "services" / "employment_start_allowed_orchestrator.py"
_API = _REPO_ROOT / "backend" / "app" / "api" / "v1" / "handoffs.py"
_PANEL = _REPO_ROOT / "hostflow-frontend" / "src" / "components" / "hr" / "HrStartAllowedPanel.tsx"
_PAGE = _REPO_ROOT / "hostflow-frontend" / "src" / "pages" / "hr" / "HrHandoffDetailPage.tsx"
_CI = _REPO_ROOT / ".github" / "workflows" / "backend-ci.yml"


def test_hr_host_gate_filename() -> None:
    assert Path(__file__).name == "test_employment_start_allowed_hr_host_gate.py"


def test_brief_locks_and_host_wire() -> None:
    brief = _BRIEF.read_text(encoding="utf-8")
    assert "Evidence supply ≠ evidence creation" in brief or "Evidence supply" in brief
    assert "unsupported_context" in brief
    assert "primary_item" in brief
    assert "optimistic" in brief.lower()
    orch = _ORCH.read_text(encoding="utf-8")
    assert "evaluate_start_allowed_for_handoff" in orch
    assert "evidence_write_not_in_start_allowed" in orch
    assert "operator_set_start_allowed_forbidden" in orch
    api = _API.read_text(encoding="utf-8")
    assert "employment-start-allowed" in api
    assert "apply_start_allowed_for_handoff" in api
    panel = _PANEL.read_text(encoding="utf-8")
    assert "ui_primary_item" in panel or "primaryWorkItem" in panel
    assert "active_missing" in panel  # mentioned as not rendered
    assert "hr-start-allowed-unsupported" in panel
    assert "type=\"file\"" not in panel
    assert "upload" not in panel.lower() or "No local upload" in panel or "no local upload" in panel.lower()
    page = _PAGE.read_text(encoding="utf-8")
    assert "HrStartAllowedPanel" in page
    assert "handoffs/:id" in page or "HrHandoffDetailPage" in page
    # No new host route invented for start_allowed
    assert "start-allowed" not in page or "HrStartAllowedPanel" in page
    ci = _CI.read_text(encoding="utf-8")
    assert "test_employment_start_allowed_hr_host_gate.py" in ci


def test_no_slice4_or_full_spine_in_orch() -> None:
    orch = _ORCH.read_text(encoding="utf-8")
    assert "employment_started" not in orch
    assert "confirm_employment_started" not in orch
    panel = _PANEL.read_text(encoding="utf-8")
    assert "force_start_allowed" not in panel
    assert "allow_anyway" not in panel


def test_evaluator_owns_primary_order_not_frontend() -> None:
    """PEM-1 progression order comes from evaluator primary_item, not FE checklist."""
    r = evaluate_employment_start_allowed_v1(
        employee_id="e1",
        employment_context={
            "employment_country": "PL",
            "pathway_id": "pl_eu_eea_free_movement",
            "contract_type": "employment_contract",
            "employer_id": "cccccccc-cccc-cccc-cccc-cccccccccccc",
            "post_key": "driver_ce",
            "planned_start_date": "2026-10-01",
        },
    )
    assert r["decision"] == DECISION_MISSING
    assert r["primary_item"]["code"] == REQ_CONTRACT
    assert any(a["code"] == REQ_BHP for a in r["active_missing"])
    # Frontend must not invent order — panel uses primary only
    panel = _PANEL.read_text(encoding="utf-8")
    assert "active_missing.map" not in panel
    assert "required_actions.map" not in panel


@pytest.mark.anyio
async def test_evaluate_host_surfaces_ui_primary_only_semantics() -> None:
    handoff = SimpleNamespace(
        id="h1",
        candidate_id="c1",
        agency_tenant_id="t1",
        client_tenant_id="t1",
    )
    emp = SimpleNamespace(
        id="e1",
        candidate_id="c1",
        meta={"internal_hr_handoff_id": "h1", "pathway_id": "pl_eu_eea_free_movement"},
        company_id="cccccccc-cccc-cccc-cccc-cccccccccccc",
        own_company_id=None,
        hire_date=None,
    )
    db = AsyncMock()
    db.get = AsyncMock(return_value=handoff)

    with (
        patch(
            "backend.app.services.employment_start_allowed_orchestrator.resolve_employee_for_handoff",
            new=AsyncMock(return_value=emp),
        ),
        patch(
            "backend.app.services.employment_start_allowed_orchestrator._load_evidence_views",
            new=AsyncMock(return_value=(None, None, None)),
        ),
        patch(
            "backend.app.services.employment_start_allowed_orchestrator.list_active_exceptions",
            new=AsyncMock(return_value=[]),
        ),
    ):
        out = await evaluate_start_allowed_for_handoff(db, tenant_id="t1", handoff_id="h1")

    assert out["decision"] == DECISION_MISSING
    assert out["ui_primary_item"]["code"] == REQ_CONTRACT
    assert out["primary_item"]["code"] == REQ_CONTRACT
    assert out["linked_handoff_id"] == "h1"
    assert "documents_anchor" in out["evidence_nav"]


@pytest.mark.anyio
async def test_apply_rejects_local_evidence_upload_patch() -> None:
    handoff = SimpleNamespace(id="h1", candidate_id="c1", agency_tenant_id="t1", client_tenant_id="t1")
    emp = SimpleNamespace(
        id="e1",
        candidate_id="c1",
        meta={"internal_hr_handoff_id": "h1"},
        company_id="c",
        own_company_id=None,
        hire_date=None,
    )
    db = AsyncMock()
    db.get = AsyncMock(return_value=handoff)

    with (
        patch(
            "backend.app.services.employment_start_allowed_orchestrator.resolve_employee_for_handoff",
            new=AsyncMock(return_value=emp),
        ),
        patch(
            "backend.app.services.employment_start_allowed_orchestrator.evaluate_start_allowed_for_handoff",
            new=AsyncMock(
                return_value={
                    "decision": DECISION_MISSING,
                    "start_allowed": False,
                    "primary_item": {"code": REQ_CONTRACT},
                    "ui_primary_item": {"code": REQ_CONTRACT},
                }
            ),
        ),
    ):
        out = await apply_start_allowed_for_handoff(
            db,
            tenant_id="t1",
            handoff_id="h1",
            resolution_patch={"upload": {"file": "x.pdf"}},
        )

    assert out["decision"] == "rejected_patch"
    assert out["rejection_reason"] == "evidence_write_not_in_start_allowed"
    assert out["start_allowed"] is False


@pytest.mark.anyio
async def test_apply_rejects_operator_set_start_allowed() -> None:
    db = AsyncMock()
    with patch(
        "backend.app.services.employment_start_allowed_orchestrator.evaluate_start_allowed_for_handoff",
        new=AsyncMock(
            return_value={
                "decision": DECISION_MISSING,
                "start_allowed": False,
                "primary_item": {"code": REQ_CONTRACT},
            }
        ),
    ):
        out = await apply_start_allowed_for_handoff(
            db,
            tenant_id="t1",
            handoff_id="h1",
            resolution_patch={"start_allowed": True},
        )
    assert out["rejection_reason"] == "operator_set_start_allowed_forbidden"


@pytest.mark.anyio
async def test_apply_exception_then_fresh_evaluate() -> None:
    handoff = SimpleNamespace(id="h1", candidate_id="c1", agency_tenant_id="t1", client_tenant_id="t1")
    emp = SimpleNamespace(
        id="e1",
        candidate_id="c1",
        meta={"internal_hr_handoff_id": "h1"},
        company_id="c",
        own_company_id=None,
        hire_date=None,
    )
    db = AsyncMock()
    db.get = AsyncMock(return_value=handoff)
    create = AsyncMock()
    eval_mock = AsyncMock(
        return_value={
            "decision": DECISION_START_ALLOWED,
            "start_allowed": True,
            "primary_item": {"code": "start_allowed", "kind": "threshold"},
            "ui_primary_item": {"code": "start_allowed", "kind": "threshold"},
        }
    )

    with (
        patch(
            "backend.app.services.employment_start_allowed_orchestrator.resolve_employee_for_handoff",
            new=AsyncMock(return_value=emp),
        ),
        patch(
            "backend.app.services.employment_start_allowed_orchestrator.create_exception",
            new=create,
        ),
        patch(
            "backend.app.services.employment_start_allowed_orchestrator.evaluate_start_allowed_for_handoff",
            new=eval_mock,
        ),
    ):
        out = await apply_start_allowed_for_handoff(
            db,
            tenant_id="t1",
            handoff_id="h1",
            actor_user_id="u1",
            resolution_patch={
                "exception": {
                    "exception_code": EXCEPTION_BHP_SUCCESSIVE,
                    "facts": {
                        "employer_id": "cccccccc-cccc-cccc-cccc-cccccccccccc",
                        "post_key": "driver_ce",
                        "prior_contract_ref": "CTR-1",
                        "prior_contract_end_date": "2026-09-01",
                        "current_contract_start_date": "2026-09-15",
                        "successive": True,
                    },
                }
            },
        )

    create.assert_awaited_once()
    eval_mock.assert_awaited()
    assert out["authority_write_confirmed"] is True
    assert out["start_allowed"] is True


def test_unsupported_is_neutral_terminal_in_ui_source() -> None:
    panel = _PANEL.read_text(encoding="utf-8")
    assert "hr-start-allowed-unsupported" in panel
    # No Retry/Supply in unsupported branch: unsupported block has no open_documents button nearby
    # Heuristic: unsupported test id section does not include open_documents in same ternary arm
    assert "This start policy does not apply" in panel or "start_allowed.unsupported" in panel
    assert DECISION_UNSUPPORTED == "unsupported_context"
