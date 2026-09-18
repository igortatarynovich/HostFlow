"""Baseline Full Spine Kernel Proof — single continuous P1→P6 witness.

Post-PMI, public-contract continuity. One new person/application.
First substantial red → STOP (do not probe remaining steps).
Does not open PEM-1. Does not run a second confidence walk.
"""

from __future__ import annotations

import ast
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from backend.app.modules.boundary.public import ready as boundary_ready
from backend.app.modules.employment.public import commands as employment_public
from backend.app.modules.recruitment.public import ready as recruitment_public
from backend.app.modules.workforce.public import started as workforce_started
from backend.app.reference.employment_formalize import ACTION_CONTRACT_BASIS
from backend.app.reference.employment_started import (
    DECISION_STARTED,
    PHYSICAL_START_META_KEY,
)

_REPO_ROOT = Path(__file__).resolve().parents[3]
_BRIEF = _REPO_ROOT / "docs" / "specs" / "tasks" / "baseline-full-spine-kernel-proof.md"
_CI = _REPO_ROOT / ".github" / "workflows" / "backend-ci.yml"
_GATE = Path(__file__)

# Shared witness identity (one person / application / handoff / employee).
_TENANT = "11111111-1111-1111-1111-111111111111"
_CANDIDATE = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
_APPLICATION = "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee"
_HANDOFF = "hhhhhhhh-hhhh-hhhh-hhhh-hhhhhhhhhhhh"
_EMPLOYEE = "ffffffff-ffff-ffff-ffff-ffffffffffff"
_ACTOR = "dddddddd-dddd-dddd-dddd-dddddddddddd"


def _rfe_package() -> dict:
    return {
        "contract_id": boundary_ready.CONTRACT_ID,
        "tenant_id": _TENANT,
        "person": {
            "person_id": _CANDIDATE,
            "identity_facts": {
                "citizenship": "PL",
                "first_name": "Ada",
                "last_name": "Kernel",
            },
        },
        "target_work": {
            "vacancy_id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
            "employer_id": "cccccccc-cccc-cccc-cccc-cccccccccccc",
            "employment_country": "PL",
            "start_date": "2026-09-18",
        },
        "recruitment_facts": {"language_ok": True},
        "evidence": {"source": "kernel_witness", "document_ids": []},
        "fits_decision": {
            "decision": "fits",
            "decided_at": "2026-09-18T08:00:00+00:00",
            "actor_id": _ACTOR,
        },
        "context_refs": {"application_id": _APPLICATION},
    }


def _employment_ctx() -> dict:
    return {
        "employment_country": "PL",
        "pathway_id": "pl_eu_eea_free_movement",
        "contract_type": "employment_contract",
        "admit_ruleset_id": "empty",
        "employer_id": "cccccccc-cccc-cccc-cccc-cccccccccccc",
        "vacancy_id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
    }


def test_kernel_proof_gate_filename() -> None:
    assert _GATE.name == "test_baseline_full_spine_kernel_proof_gate.py"


def test_kernel_brief_authorization_and_continuity() -> None:
    text = _BRIEF.read_text(encoding="utf-8")
    assert "**Status:** **PASS**" in text or "Status:** **PASS**" in text
    assert "Current authorization — 2026-09-18" in text
    assert "Public-contract continuity" in text
    assert "Witness journal — 2026-09-18" in text
    assert "historical evidence" in text.lower()
    assert "2026-09-15" in text  # STOP journal retained
    assert "PEM-1" in text
    assert "| P6 |" in text and "**PASS**" in text.split("## Witness journal", 1)[1]


def test_gate_imports_only_public_transition_surfaces() -> None:
    """Witness must execute transitions via *.public.* — not private Workforce helpers."""
    src = _GATE.read_text(encoding="utf-8")
    tree = ast.parse(src)
    banned_prefixes = (
        "backend.app.services.workforce_employees",
        "backend.app.services.handoff",
        "backend.app.services.ready_for_employment_emit",
        "backend.app.services.employment_formalize_employee_ensure",
    )
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            for banned in banned_prefixes:
                assert not node.module.startswith(banned), node.module
        if isinstance(node, ast.Import):
            for alias in node.names:
                for banned in banned_prefixes:
                    assert not alias.name.startswith(banned), alias.name


def test_ci_wires_kernel_proof_gate() -> None:
    ci = _CI.read_text(encoding="utf-8")
    assert "test_baseline_full_spine_kernel_proof_gate.py" in ci


@pytest.mark.anyio
async def test_p1_to_p6_single_continuous_witness(monkeypatch: pytest.MonkeyPatch) -> None:
    """One continuous new-person witness. First red fails this test (STOP)."""
    pkg = _rfe_package()
    ctx = _employment_ctx()

    # --- mutable identity fixtures (persistence inspection allowed) ---
    candidate = SimpleNamespace(
        id=_CANDIDATE,
        tenant_id=_TENANT,
        deleted_at=None,
        stage="new",
        company_id=None,
        own_company_id=None,
        vacancy_id="bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
        phone=None,
        email=None,
        _get_extra=lambda: {},
        _get_personal_data=lambda: {},
    )
    handoff = SimpleNamespace(
        id=_HANDOFF,
        candidate_id=_CANDIDATE,
        application_id=_APPLICATION,
        agency_tenant_id=_TENANT,
        client_tenant_id=_TENANT,
        destination="internal_hr",
        status="pending_review",
        client_company_id=None,
    )
    employee = SimpleNamespace(
        id=_EMPLOYEE,
        candidate_id=_CANDIDATE,
        company_id=None,
        own_company_id=None,
        hire_date=None,
        meta={"internal_hr_handoff_id": _HANDOFF},
    )

    class _CandResult:
        def scalar_one_or_none(self):
            return candidate

    db = SimpleNamespace(
        execute=AsyncMock(return_value=_CandResult()),
        get=AsyncMock(side_effect=lambda _model, id_: handoff if str(id_) == _HANDOFF else None),
        flush=AsyncMock(),
    )

    # ========== P1: empty Ready → public allowed ==========
    async def _boom(*_a, **_k):
        raise AssertionError("Ready policy capability invoked under empty composition")

    monkeypatch.setattr(
        "backend.app.api.v1.candidates.pipeline_overrides_service.approved_handoff_relaxed_types",
        AsyncMock(return_value=set()),
    )
    monkeypatch.setattr(
        "backend.app.services.transfer_policy_resolver._resolve_destinations_for_candidate",
        AsyncMock(
            return_value=(
                ["internal_hr"],
                SimpleNamespace(
                    get_handoff_enabled=lambda: True,
                    get_handoff_to_client=lambda: False,
                    get_handoff_to_internal_hr=lambda: True,
                    get_workforce_handoff_on_ready_for_handoff_stage=lambda: False,
                ),
                {},
            )
        ),
    )
    monkeypatch.setattr(
        "backend.app.services.transfer_policy_resolver.resolve_hiring_pipeline_gates",
        AsyncMock(
            return_value=SimpleNamespace(
                stages_without_doc_pipeline_block=frozenset(),
                stages_verify_uploads_block_forward=frozenset(),
                stages_require_vacancy_for_forward=frozenset(),
            )
        ),
    )
    monkeypatch.setattr(
        "backend.app.services.transfer_policy_resolver.resolve_workforce_eligibility_via_contract",
        _boom,
    )
    monkeypatch.setattr(
        "backend.app.services.recruitment_package_readiness.evaluate_recruitment_package",
        _boom,
    )
    monkeypatch.setattr(
        "backend.app.field_registry.requirement_evaluator.evaluate_field_requirements_for_candidate",
        _boom,
    )
    monkeypatch.setattr(
        "backend.app.services.operational_requirements_service.evaluate_operational_requirements_for_candidate",
        _boom,
    )

    p1 = await recruitment_public.evaluate_ready_transfer(
        db,
        tenant_id=_TENANT,
        candidate_id=_CANDIDATE,
        ready_context={recruitment_public.READY_COMPOSITION_ID_KEY: recruitment_public.COMPOSITION_EMPTY},
    )
    assert p1["decision"] == recruitment_public.DECISION_ALLOWED, (
        f"STOP P1 kernel/policy: expected allowed, got {p1!r}"
    )
    assert p1["transfer_allowed"] is True

    # ========== P2: RFE via Boundary + Employment accept ==========
    errs = boundary_ready.validate_ready_for_employment_package_v1(pkg)
    assert errs == [], f"STOP P2 contract gap (Boundary RFE validate): {errs}"

    async def _accept_handoff(_db, *, handoff_id, reviewed_by_user_id, tenant_id):  # noqa: ARG001
        handoff.status = "accepted"
        return handoff, None

    monkeypatch.setattr(
        "backend.app.services.handoff.accept_handoff",
        _accept_handoff,
    )
    monkeypatch.setattr(
        "backend.app.services.employment_accept_orchestrator.log_audit_event",
        AsyncMock(),
    )

    p2 = await employment_public.apply_employment_accept_policy(
        db,
        tenant_id=_TENANT,
        handoff_id=_HANDOFF,
        actor_id=_ACTOR,
        package=pkg,
    )
    assert p2.get("accepted") is True, f"STOP P2 kernel/integration (Employment accept): {p2!r}"
    assert handoff.status == "accepted"
    assert str(handoff.candidate_id) == _CANDIDATE

    # ========== P3: Formalize / ensure Employee ==========
    ensure_result = SimpleNamespace(
        employee_id=_EMPLOYEE,
        employee_created=True,
        wrote=True,
        skipped_reason=None,
        linked_handoff_id=_HANDOFF,
    )
    monkeypatch.setattr(
        "backend.app.services.employment_formalize_orchestrator.ensure_employee_after_formalize_apply",
        AsyncMock(return_value=ensure_result),
    )

    p3 = await employment_public.formalize_employment_for_handoff(
        db,
        tenant_id=_TENANT,
        handoff_id=_HANDOFF,
        package=pkg,
        employment_context=ctx,
        confirmed_actions=[ACTION_CONTRACT_BASIS],
        authoritative_apply=True,
        actor_user_id=_ACTOR,
    )
    assert p3.get("ready_to_create_employee") is True, f"STOP P3 policy/kernel (formalize): {p3!r}"
    assert p3.get("employee_id") == _EMPLOYEE, f"STOP P3 kernel (ensure Employee): {p3!r}"
    assert p3.get("employee_ensure_wrote") is True

    # ========== P4: empty Admit → start_allowed ==========
    import backend.app.services.employment_start_allowed_orchestrator as admit_orch

    async def _resolve_employee(_db, *, tenant_id, handoff):  # noqa: ARG001
        return employee

    async def _load_evidence(_db, *, tenant_id, candidate_id):  # noqa: ARG001
        return None, None, None

    monkeypatch.setattr(admit_orch, "resolve_employee_for_handoff", _resolve_employee)
    monkeypatch.setattr(admit_orch, "_load_evidence_views", _load_evidence)
    monkeypatch.setattr(admit_orch, "list_active_exceptions", AsyncMock(return_value=[]))

    p4 = await employment_public.evaluate_start_allowed_for_handoff(
        db,
        tenant_id=_TENANT,
        handoff_id=_HANDOFF,
        employment_context=ctx,
    )
    assert p4.get("start_allowed") is True, f"STOP P4 policy/kernel (empty Admit): {p4!r}"

    # ========== P5: human Confirm → employment_started.v1 ==========
    monkeypatch.setattr(
        "backend.app.services.employment_started_orchestrator._resolve_handoff_employee",
        AsyncMock(return_value=employee),
    )
    monkeypatch.setattr(
        "backend.app.services.employment_started_orchestrator.evaluate_start_allowed_for_handoff",
        AsyncMock(return_value={"start_allowed": True, **p4}),
    )
    monkeypatch.setattr(
        "backend.app.services.employment_started_orchestrator.log_audit_event",
        AsyncMock(),
    )

    p5 = await employment_public.confirm_employment_started_for_handoff(
        db,
        tenant_id=_TENANT,
        handoff_id=_HANDOFF,
        actor_id=_ACTOR,
        package=pkg,
        employment_context=ctx,
        start_confirmation={"confirmed": True, "start_date": "2026-09-18"},
    )
    assert p5.get("decision") == DECISION_STARTED, f"STOP P5 kernel (Confirm/Started): {p5!r}"
    assert p5.get("started") is True
    assert str(p5.get("employee_id")) == _EMPLOYEE
    assert PHYSICAL_START_META_KEY in (employee.meta or {})

    # ========== P6: Workforce public accepts Started Employee ==========
    # Forbidden: proving continuity via private workforce_employees import in this gate.
    async def _find(_db, tenant_id, candidate_id):  # noqa: ARG001
        assert str(candidate_id) == _CANDIDATE
        assert str(tenant_id) == _TENANT
        return employee

    async def _ensure_bundle(_db, tenant_id, employee_id):  # noqa: ARG001
        assert str(employee_id) == _EMPLOYEE
        return None

    monkeypatch.setattr(
        "backend.app.services.workforce_employees.find_employee_by_candidate",
        _find,
    )
    monkeypatch.setattr(
        "backend.app.services.workforce_employees.ensure_hr_profiles_bundle",
        _ensure_bundle,
    )

    found = await workforce_started.find_employee_by_candidate(db, _TENANT, _CANDIDATE)
    assert found is not None, "STOP P6 contract gap: Workforce public cannot resolve Started Employee"
    assert str(found.id) == _EMPLOYEE
    assert PHYSICAL_START_META_KEY in (found.meta or {}), (
        "STOP P6 kernel: Workforce surface sees Employee without Started fact"
    )
    await workforce_started.ensure_hr_profiles_bundle(db, _TENANT, str(found.id))
