"""Employment Start Allowed — mint timing cutover gate (slice 2).

Proves Formalize apply/complete → handoff_from_candidate → handoff-linked Employee
→ start_allowed evaluate, without evaluate-side mint and without ESO-5 enforcement.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from backend.app.reference.employment_start_allowed import (
    DECISION_MISSING,
    evaluate_employment_start_allowed_v1,
)
from backend.app.services.employment_formalize_employee_ensure import (
    ENSURE_API,
    MINT_CUTOVER_REL,
    POLICY_ID,
    SKIP_EVALUATE_OR_READ,
    SKIP_NOT_READY,
    employee_linked_handoff_id,
    ensure_employee_after_formalize_apply,
    should_mint_employee_after_formalize,
)
from backend.app.services.employment_start_allowed_evidence import (
    project_bhp_evidence_view,
    project_contract_evidence_view,
    project_medical_evidence_view,
)

_REPO_ROOT = Path(__file__).resolve().parents[3]
_BRIEF = _REPO_ROOT / MINT_CUTOVER_REL
_ENSURE = (
    _REPO_ROOT / "backend" / "app" / "services" / "employment_formalize_employee_ensure.py"
)
_HANDOFF_EMP = _REPO_ROOT / "backend" / "app" / "services" / "workforce_employees.py"
_CI = _REPO_ROOT / ".github" / "workflows" / "backend-ci.yml"
_FORMALIZE_ORCH = (
    _REPO_ROOT / "backend" / "app" / "services" / "employment_formalize_orchestrator.py"
)
_STARTED_REF = _REPO_ROOT / "backend" / "app" / "reference" / "employment_started.py"


def _pem1_ctx(**extra):
    ctx = {
        "employment_country": "PL",
        "pathway_id": "pl_eu_eea_free_movement",
        "contract_type": "employment_contract",
        "employer_id": "cccccccc-cccc-cccc-cccc-cccccccccccc",
        "post_key": "driver_ce",
        "planned_start_date": "2026-10-01",
    }
    ctx.update(extra)
    return ctx


def _ok_contract():
    return project_contract_evidence_view(
        {
            "id": "doc-contract",
            "type": "employment_contract",
            "meta": {
                "signed_at": "2026-09-20",
                "employer_name": "PL Sp. z o.o.",
                "start_at": "2026-10-01",
            },
        }
    )


def _ok_medical():
    return project_medical_evidence_view(
        {
            "id": "doc-med",
            "type": "medical_certificate",
            "meta": {
                "expires_at": "2026-12-01",
                "fit_for_work": True,
                "applies_to_post": "driver_ce",
                "conditions_match": True,
            },
        }
    )


def _ok_bhp():
    return project_bhp_evidence_view(
        {
            "id": "doc-bhp",
            "type": "bhp",
            "meta": {
                "training_date": "2026-09-15",
                "training_kind": "introductory",
                "employer_id": "cccccccc-cccc-cccc-cccc-cccccccccccc",
                "post_key": "driver_ce",
            },
        }
    )


def test_mint_cutover_gate_filename() -> None:
    assert Path(__file__).name == "test_employment_start_allowed_mint_cutover_gate.py"


def test_mint_cutover_brief_and_policy() -> None:
    assert _BRIEF.is_file()
    text = _BRIEF.read_text(encoding="utf-8")
    assert "authoritative" in text.lower()
    assert "evaluate" in text.lower()
    assert "handoff_from_candidate" in text
    assert POLICY_ID == "employment_formalize_employee_ensure.v1"
    assert ENSURE_API == "ensure_employee_after_formalize_apply"
    assert f"async def {ENSURE_API}(" in _ENSURE.read_text(encoding="utf-8")


def test_should_mint_only_on_authoritative_apply_and_ready() -> None:
    assert should_mint_employee_after_formalize(
        ready_to_create_employee=True, authoritative_apply=True
    )
    assert not should_mint_employee_after_formalize(
        ready_to_create_employee=True, authoritative_apply=False
    )
    assert not should_mint_employee_after_formalize(
        ready_to_create_employee=False, authoritative_apply=True
    )
    assert not should_mint_employee_after_formalize(
        ready_to_create_employee=False, authoritative_apply=False
    )


def test_handoff_from_candidate_is_candidate_scoped_idempotent() -> None:
    """Existing mint authority: one Employee per candidate (prove; do not invent another)."""
    src = _HANDOFF_EMP.read_text(encoding="utf-8")
    assert "async def handoff_from_candidate(" in src
    assert "find_employee_by_candidate" in src
    # Ensure seam must compose that primitive, not create_employee.
    ensure_src = _ENSURE.read_text(encoding="utf-8")
    assert "handoff_from_candidate" in ensure_src
    assert "create_employee(" not in ensure_src
    assert "ensure_hr_operational_context" in ensure_src


def test_ensure_seam_forbids_evaluate_side_mint_in_source() -> None:
    src = _ENSURE.read_text(encoding="utf-8")
    assert "SKIP_EVALUATE_OR_READ" in src
    assert "authoritative_apply" in src
    assert "ready_to_create_employee" in src


def test_no_eso5_start_allowed_enforcement_in_this_slice() -> None:
    """Slice 2 must not rewrite ESO-5 Confirm to require start_allowed."""
    if _STARTED_REF.is_file():
        text = _STARTED_REF.read_text(encoding="utf-8")
        assert "start_allowed" not in text or "require_start_allowed" not in text.lower()
    # Ensure module itself must not gate ESO-5.
    ensure_src = _ENSURE.read_text(encoding="utf-8")
    assert "employment_started" not in ensure_src
    assert "confirm_employment_started" not in ensure_src


def test_no_hr_frontend_in_mint_cutover_module_scope() -> None:
    ensure_src = _ENSURE.read_text(encoding="utf-8")
    assert "hostflow-frontend" not in ensure_src
    assert "tsx" not in ensure_src


def test_ci_registers_mint_cutover_gate() -> None:
    ci = _CI.read_text(encoding="utf-8")
    assert "employment-start-allowed-mint-cutover-gate" in ci
    assert "test_employment_start_allowed_mint_cutover_gate.py" in ci


def test_formalize_orchestrator_wire_contract_when_present() -> None:
    """If Formalize orchestrator is on tree, it must call ensure only via apply seam."""
    if not _FORMALIZE_ORCH.is_file():
        return
    text = _FORMALIZE_ORCH.read_text(encoding="utf-8")
    assert "ensure_employee_after_formalize_apply" in text
    assert "authoritative_apply" in text


def _mock_db(*, handoff, candidate, existing_employee=None):
    db = AsyncMock()

    async def _get(model, key):  # noqa: ANN001
        name = getattr(model, "__name__", str(model))
        if name == "CandidateHandoff":
            return handoff if str(key) == str(handoff.id) else None
        if name == "Candidate":
            return candidate if str(key) == str(candidate.id) else None
        return None

    db.get = AsyncMock(side_effect=_get)
    db.flush = AsyncMock()
    return db


@pytest.mark.anyio
async def test_evaluate_ready_does_not_call_handoff_from_candidate() -> None:
    handoff = SimpleNamespace(id="h1", candidate_id="c1")
    candidate = SimpleNamespace(id="c1")
    db = _mock_db(handoff=handoff, candidate=candidate)

    with (
        patch(
            "backend.app.services.employment_formalize_employee_ensure.we_svc.find_employee_by_candidate",
            new=AsyncMock(return_value=None),
        ),
        patch(
            "backend.app.services.employment_formalize_employee_ensure.we_svc.handoff_from_candidate",
            new=AsyncMock(),
        ) as mint,
    ):
        result = await ensure_employee_after_formalize_apply(
            db,
            tenant_id="t1",
            handoff_id="h1",
            actor_user_id="u1",
            ready_to_create_employee=True,
            authoritative_apply=False,
        )

    mint.assert_not_awaited()
    assert result.wrote is False
    assert result.employee_id is None
    assert result.skipped_reason == SKIP_EVALUATE_OR_READ


@pytest.mark.anyio
async def test_apply_not_ready_does_not_mint() -> None:
    handoff = SimpleNamespace(id="h1", candidate_id="c1")
    candidate = SimpleNamespace(id="c1")
    db = _mock_db(handoff=handoff, candidate=candidate)

    with (
        patch(
            "backend.app.services.employment_formalize_employee_ensure.we_svc.find_employee_by_candidate",
            new=AsyncMock(return_value=None),
        ),
        patch(
            "backend.app.services.employment_formalize_employee_ensure.we_svc.handoff_from_candidate",
            new=AsyncMock(),
        ) as mint,
    ):
        result = await ensure_employee_after_formalize_apply(
            db,
            tenant_id="t1",
            handoff_id="h1",
            actor_user_id="u1",
            ready_to_create_employee=False,
            authoritative_apply=True,
        )

    mint.assert_not_awaited()
    assert result.skipped_reason == SKIP_NOT_READY
    assert result.wrote is False


@pytest.mark.anyio
async def test_authoritative_apply_ready_mints_and_links_handoff() -> None:
    handoff = SimpleNamespace(id="h-apply", candidate_id="c1")
    candidate = SimpleNamespace(id="c1")
    emp = SimpleNamespace(id="e-new", meta={})
    db = _mock_db(handoff=handoff, candidate=candidate)

    with (
        patch(
            "backend.app.services.employment_formalize_employee_ensure.we_svc.find_employee_by_candidate",
            new=AsyncMock(return_value=None),
        ),
        patch(
            "backend.app.services.employment_formalize_employee_ensure.we_svc.handoff_from_candidate",
            new=AsyncMock(return_value=emp),
        ) as mint,
        patch(
            "backend.app.services.employment_formalize_employee_ensure.ensure_hr_operational_context",
            new=AsyncMock(),
        ) as ops,
        patch(
            "backend.app.services.tenant_hr_flags.delayed_hr_workforce_creation_enabled",
            new=AsyncMock(return_value=False),
        ),
    ):
        result = await ensure_employee_after_formalize_apply(
            db,
            tenant_id="t1",
            handoff_id="h-apply",
            actor_user_id="u1",
            ready_to_create_employee=True,
            authoritative_apply=True,
        )

    mint.assert_awaited_once()
    ops.assert_awaited_once()
    assert result.wrote is True
    assert result.employee_created is True
    assert result.employee_id == "e-new"
    assert result.linked_handoff_id == "h-apply"
    assert emp.meta.get("internal_hr_handoff_id") == "h-apply"


@pytest.mark.anyio
async def test_repeat_apply_same_handoff_same_employee_id() -> None:
    handoff = SimpleNamespace(id="h1", candidate_id="c1")
    candidate = SimpleNamespace(id="c1")
    emp = SimpleNamespace(id="e1", meta={"internal_hr_handoff_id": "h1"})
    db = _mock_db(handoff=handoff, candidate=candidate)

    with (
        patch(
            "backend.app.services.employment_formalize_employee_ensure.we_svc.find_employee_by_candidate",
            new=AsyncMock(return_value=emp),
        ),
        patch(
            "backend.app.services.employment_formalize_employee_ensure.we_svc.handoff_from_candidate",
            new=AsyncMock(return_value=emp),
        ) as mint,
        patch(
            "backend.app.services.employment_formalize_employee_ensure.ensure_hr_operational_context",
            new=AsyncMock(),
        ),
        patch(
            "backend.app.services.tenant_hr_flags.delayed_hr_workforce_creation_enabled",
            new=AsyncMock(return_value=False),
        ),
    ):
        first = await ensure_employee_after_formalize_apply(
            db,
            tenant_id="t1",
            handoff_id="h1",
            actor_user_id="u1",
            ready_to_create_employee=True,
            authoritative_apply=True,
        )
        second = await ensure_employee_after_formalize_apply(
            db,
            tenant_id="t1",
            handoff_id="h1",
            actor_user_id="u1",
            ready_to_create_employee=True,
            authoritative_apply=True,
        )

    assert first.employee_id == second.employee_id == "e1"
    assert first.employee_created is False
    assert second.employee_created is False
    assert mint.await_count == 2  # idempotent ensure; same row returned


@pytest.mark.anyio
async def test_cross_context_rebrands_linkage_without_second_mint_authority() -> None:
    """Same candidate → same Employee (existing semantics); linkage moves to current handoff."""
    handoff_b = SimpleNamespace(id="h-b", candidate_id="c1")
    candidate = SimpleNamespace(id="c1")
    emp = SimpleNamespace(id="e1", meta={"internal_hr_handoff_id": "h-a"})
    db = _mock_db(handoff=handoff_b, candidate=candidate)

    with (
        patch(
            "backend.app.services.employment_formalize_employee_ensure.we_svc.find_employee_by_candidate",
            new=AsyncMock(return_value=emp),
        ),
        patch(
            "backend.app.services.employment_formalize_employee_ensure.we_svc.handoff_from_candidate",
            new=AsyncMock(return_value=emp),
        ),
        patch(
            "backend.app.services.employment_formalize_employee_ensure.ensure_hr_operational_context",
            new=AsyncMock(),
        ),
        patch(
            "backend.app.services.tenant_hr_flags.delayed_hr_workforce_creation_enabled",
            new=AsyncMock(return_value=False),
        ),
    ):
        result = await ensure_employee_after_formalize_apply(
            db,
            tenant_id="t1",
            handoff_id="h-b",
            actor_user_id="u1",
            ready_to_create_employee=True,
            authoritative_apply=True,
        )

    assert result.employee_id == "e1"
    assert result.linked_handoff_id == "h-b"
    assert emp.meta.get("internal_hr_handoff_id") == "h-b"
    assert employee_linked_handoff_id(emp) == "h-b"


@pytest.mark.anyio
async def test_evaluate_does_not_surface_employee_linked_to_other_handoff() -> None:
    handoff = SimpleNamespace(id="h-b", candidate_id="c1")
    candidate = SimpleNamespace(id="c1")
    emp = SimpleNamespace(id="e1", meta={"internal_hr_handoff_id": "h-a"})
    db = _mock_db(handoff=handoff, candidate=candidate)

    with (
        patch(
            "backend.app.services.employment_formalize_employee_ensure.we_svc.find_employee_by_candidate",
            new=AsyncMock(return_value=emp),
        ),
        patch(
            "backend.app.services.employment_formalize_employee_ensure.we_svc.handoff_from_candidate",
            new=AsyncMock(),
        ) as mint,
    ):
        result = await ensure_employee_after_formalize_apply(
            db,
            tenant_id="t1",
            handoff_id="h-b",
            actor_user_id="u1",
            ready_to_create_employee=True,
            authoritative_apply=False,
        )

    mint.assert_not_awaited()
    assert result.employee_id is None
    assert result.skipped_reason == SKIP_EVALUATE_OR_READ


@pytest.mark.anyio
async def test_start_allowed_uses_handoff_linked_employee_before_eso5_confirm() -> None:
    """Completion proof: mint seam employee_id → start_allowed evaluate (no ESO-5)."""
    handoff = SimpleNamespace(id="h1", candidate_id="c1")
    candidate = SimpleNamespace(id="c1")
    emp = SimpleNamespace(id="e-linked", meta={})
    db = _mock_db(handoff=handoff, candidate=candidate)

    with (
        patch(
            "backend.app.services.employment_formalize_employee_ensure.we_svc.find_employee_by_candidate",
            new=AsyncMock(return_value=None),
        ),
        patch(
            "backend.app.services.employment_formalize_employee_ensure.we_svc.handoff_from_candidate",
            new=AsyncMock(return_value=emp),
        ),
        patch(
            "backend.app.services.employment_formalize_employee_ensure.ensure_hr_operational_context",
            new=AsyncMock(),
        ),
        patch(
            "backend.app.services.tenant_hr_flags.delayed_hr_workforce_creation_enabled",
            new=AsyncMock(return_value=False),
        ),
    ):
        minted = await ensure_employee_after_formalize_apply(
            db,
            tenant_id="t1",
            handoff_id="h1",
            actor_user_id="u1",
            ready_to_create_employee=True,
            authoritative_apply=True,
        )

    assert minted.employee_id == "e-linked"
    assert minted.linked_handoff_id == "h1"
    assert emp.meta.get("internal_hr_handoff_id") == "h1"

    # Wrong employee (other candidate case) must not be confused with linked one.
    foreign = "e-foreign"
    assert minted.employee_id != foreign

    allowed = evaluate_employment_start_allowed_v1(
        employee_id=minted.employee_id,
        employment_context=_pem1_ctx(),
        contract_view=_ok_contract(),
        medical_view=_ok_medical(),
        bhp_view=_ok_bhp(),
    )
    assert allowed["start_allowed"] is True
    assert allowed["employee_id"] == "e-linked"

    # Without evidence still evaluates on the *linked* employee (missing, not blocked for id).
    missing = evaluate_employment_start_allowed_v1(
        employee_id=minted.employee_id,
        employment_context=_pem1_ctx(),
    )
    assert missing["decision"] == DECISION_MISSING
    assert missing["employee_id"] == "e-linked"
