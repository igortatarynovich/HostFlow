"""PEM-1 Policy Composition proof gate.

Dual-boundary Part A (blocking) + Part B (satisfied) on one continuous identity.
Not a Kernel re-proof. Not Walks 1–4.
First unexpected red → STOP (expected policy blocks are Part A evidence).
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from backend.app.modules.boundary.public import ready as boundary_ready
from backend.app.modules.employment.public import commands as employment_public
from backend.app.modules.recruitment.public import ready as recruitment_public
from backend.app.modules.workforce.public import started as workforce_started
from backend.app.reference.employment_formalize import ACTION_CONTRACT_BASIS
from backend.app.reference.employment_start_allowed import (
    ADMIT_RULESET_ID_KEY,
    DECISION_MISSING,
    DECISION_START_ALLOWED,
    REQ_BHP,
    REQ_CONTRACT,
    REQ_MEDICAL,
    RULESET_PEM1,
)
from backend.app.reference.employment_started import (
    DECISION_STARTED,
    PHYSICAL_START_META_KEY,
)
from backend.app.reference.recruitment_ready_policy import (
    CAP_DOCUMENT_PACKS,
    CAP_RECRUITMENT_PACKAGE,
    COMPOSITION_DRIVER,
    DECISION_ALLOWED,
    DECISION_BLOCKED,
    DECISION_MISSING,
    READY_COMPOSITION_ID_KEY,
)
from backend.app.services.employment_start_allowed_evidence import (
    project_bhp_evidence_view,
    project_contract_evidence_view,
    project_medical_evidence_view,
)

_REPO_ROOT = Path(__file__).resolve().parents[3]
_BRIEF = _REPO_ROOT / "docs" / "specs" / "tasks" / "pem1-policy-composition.md"
_CI = _REPO_ROOT / ".github" / "workflows" / "backend-ci.yml"
_GATE = Path(__file__)

_TENANT = "11111111-1111-1111-1111-111111111111"
_CANDIDATE = "pem1aaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
_APPLICATION = "pem1eeee-eeee-eeee-eeee-eeeeeeeeeeee"
_HANDOFF = "pem1hhhh-hhhh-hhhh-hhhh-hhhhhhhhhhhh"
_EMPLOYEE = "pem1ffff-ffff-ffff-ffff-ffffffffffff"
_ACTOR = "pem1dddd-dddd-dddd-dddd-dddddddddddd"
_DRIVER_CAPS = {
    CAP_DOCUMENT_PACKS,
    CAP_RECRUITMENT_PACKAGE,
    "field_requirements",
    "requirement_engine",
    "operational_requirements",
    "recruiter_confirmation",
}


def _rfe_package() -> dict:
    return {
        "contract_id": boundary_ready.CONTRACT_ID,
        "tenant_id": _TENANT,
        "person": {
            "person_id": _CANDIDATE,
            "identity_facts": {
                "citizenship": "PL",
                "first_name": "Ada",
                "last_name": "PemOne",
            },
        },
        "target_work": {
            "vacancy_id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
            "employer_id": "cccccccc-cccc-cccc-cccc-cccccccccccc",
            "employment_country": "PL",
            "start_date": "2026-10-01",
            "position_category": "driver",
        },
        "recruitment_facts": {"language_ok": True},
        "evidence": {"source": "pem1_witness", "document_ids": []},
        "fits_decision": {
            "decision": "fits",
            "decided_at": "2026-09-18T10:00:00+00:00",
            "actor_id": _ACTOR,
        },
        "context_refs": {"application_id": _APPLICATION},
    }


def _admit_ctx() -> dict:
    return {
        "employment_country": "PL",
        "pathway_id": "pl_eu_eea_free_movement",
        "contract_type": "employment_contract",
        "employer_id": "cccccccc-cccc-cccc-cccc-cccccccccccc",
        "post_key": "driver_ce",
        "planned_start_date": "2026-10-01",
        ADMIT_RULESET_ID_KEY: RULESET_PEM1,
        "vacancy_id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
    }


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
                "post_key": "driver_ce",
                "working_conditions_ref": "std-driver",
            },
        }
    )


def _ok_bhp():
    return project_bhp_evidence_view(
        {
            "id": "doc-bhp",
            "type": "bhp_training",
            "meta": {
                "training_date": "2026-09-15",
                "training_kind": "introductory",
                "employer_id": "cccccccc-cccc-cccc-cccc-cccccccccccc",
                "post_key": "driver_ce",
            },
        }
    )


def test_pem1_gate_filename() -> None:
    assert _GATE.name == "test_pem1_policy_composition_gate.py"


def test_pem1_brief_dual_boundary_locks() -> None:
    text = _BRIEF.read_text(encoding="utf-8")
    assert "**Status:** **PASS**" in text or "Status:** **PASS**" in text
    assert "Dual-boundary lock" in text or "dual-boundary" in text.lower()
    assert "Recruitment boundary" in text
    assert "Employment boundary" in text
    assert "Witness journal — 2026-09-18" in text
    assert "next_action" in text
    assert "Kernel immutability" in text or "must not** change Kernel" in text
    assert COMPOSITION_DRIVER in text or "driver" in text
    assert "PEM-1" in text


def test_ci_wires_pem1_gate() -> None:
    assert "test_pem1_policy_composition_gate.py" in _CI.read_text(encoding="utf-8")


def _minimal_candidate() -> SimpleNamespace:
    return SimpleNamespace(
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


def _patch_destination_and_gates(monkeypatch: pytest.MonkeyPatch) -> None:
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


def _patch_ready_capabilities_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    """Empty dossier under driver — capability layers report composition missing."""
    monkeypatch.setattr(
        "backend.app.services.transfer_policy_resolver.resolve_workforce_eligibility_via_contract",
        AsyncMock(
            return_value={
                "eligibility_status": "blocked",
                "allowed_operations": {"handoff_to_hr": False},
                "missing_documents": ["driver_qualification_card", "code95"],
                "pending_verification_documents": [],
                "blocking_reasons": [
                    {
                        "code": "missing_required_document",
                        "message": "Missing driver qualification card",
                        "document_code": "driver_qualification_card",
                    }
                ],
            }
        ),
    )
    monkeypatch.setattr(
        "backend.app.services.recruitment_package_readiness.evaluate_recruitment_package",
        AsyncMock(
            return_value={
                "ready": False,
                "blocks": [{"code": "package_block_incomplete", "message": "Recruitment package incomplete"}],
                "blocking_blocks": [],
                "missing_data_fields": [],
            }
        ),
    )
    monkeypatch.setattr(
        "backend.app.field_registry.requirement_evaluator.evaluate_field_requirements_for_candidate",
        AsyncMock(return_value={"blocking_reasons": [], "missing_fields": []}),
    )
    monkeypatch.setattr(
        "backend.app.services.operational_requirements_service.evaluate_operational_requirements_for_candidate",
        AsyncMock(return_value=[]),
    )
    monkeypatch.setattr(
        "backend.app.services.operational_requirements_service.operational_requirement_blocking_reasons",
        lambda _rows: [],
    )
    monkeypatch.setattr(
        "backend.app.requirement_rules.readiness_bridge.resolve_entity_profile_code_for_candidate",
        AsyncMock(return_value=None),
    )
    # Reference docs / R5 — avoid live DB; empty pack still leaves eligibility missing.
    monkeypatch.setattr(
        "backend.app.services.transfer_policy_resolver.ReferenceServiceFacade.get_applicable_documents",
        AsyncMock(return_value=[]),
    )
    monkeypatch.setattr(
        "backend.app.reference.document_policy_overlay_store.load_persisted_tenant_delta",
        AsyncMock(return_value={}),
    )


def _patch_ready_capabilities_satisfied(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "backend.app.services.transfer_policy_resolver.resolve_workforce_eligibility_via_contract",
        AsyncMock(
            return_value={
                "eligibility_status": "eligible",
                "allowed_operations": {"handoff_to_hr": True},
                "missing_documents": [],
                "pending_verification_documents": [],
                "blocking_reasons": [],
                "readiness_profiles": {
                    "hr_ready": {"status": "ready"},
                    "recruitment_ready": {"status": "ready"},
                },
            }
        ),
    )
    monkeypatch.setattr(
        "backend.app.services.recruitment_package_readiness.evaluate_recruitment_package",
        AsyncMock(
            return_value={
                "ready": True,
                "blocks": [],
                "blocking_blocks": [],
                "missing_data_fields": [],
            }
        ),
    )
    monkeypatch.setattr(
        "backend.app.field_registry.requirement_evaluator.evaluate_field_requirements_for_candidate",
        AsyncMock(return_value={"blocking_reasons": [], "missing_fields": []}),
    )
    monkeypatch.setattr(
        "backend.app.services.operational_requirements_service.evaluate_operational_requirements_for_candidate",
        AsyncMock(return_value=[]),
    )
    monkeypatch.setattr(
        "backend.app.services.operational_requirements_service.operational_requirement_blocking_reasons",
        lambda _rows: [],
    )
    monkeypatch.setattr(
        "backend.app.requirement_rules.readiness_bridge.resolve_entity_profile_code_for_candidate",
        AsyncMock(return_value=None),
    )
    monkeypatch.setattr(
        "backend.app.services.transfer_policy_resolver.ReferenceServiceFacade.get_applicable_documents",
        AsyncMock(return_value=[]),
    )
    monkeypatch.setattr(
        "backend.app.reference.document_policy_overlay_store.load_persisted_tenant_delta",
        AsyncMock(return_value={}),
    )
    monkeypatch.setattr(
        "backend.app.reference.requirement_policy_consumer_parity.r5_required_set",
        lambda *_a, **_k: set(),
    )
    monkeypatch.setattr(
        "backend.app.services.transfer_policy_resolver._pending_confirmations",
        lambda *_a, **_k: [],
    )


@pytest.mark.anyio
async def test_pem1_continuous_dual_boundary_witness(monkeypatch: pytest.MonkeyPatch) -> None:
    """One PEM-1 identity: Ready A→B → RFE → Admit A→B → Started → Workforce."""
    cand = _minimal_candidate()

    class _CandResult:
        def scalar_one_or_none(self):
            return cand

    db = SimpleNamespace(
        execute=AsyncMock(return_value=_CandResult()),
        get=AsyncMock(),
        flush=AsyncMock(),
        scalar=AsyncMock(return_value=None),
    )
    _patch_destination_and_gates(monkeypatch)

    # ----- Recruitment Part A: driver + missing -----
    _patch_ready_capabilities_missing(monkeypatch)
    ready_a = await recruitment_public.evaluate_ready_transfer(
        db,
        tenant_id=_TENANT,
        candidate_id=_CANDIDATE,
        ready_context={READY_COMPOSITION_ID_KEY: COMPOSITION_DRIVER},
    )
    assert ready_a.get("composition_id") == COMPOSITION_DRIVER, (
        f"STOP policy/rule (Ready composition): expected driver, got {ready_a!r}"
    )
    assert ready_a.get("decision") in {DECISION_MISSING, DECISION_BLOCKED}, (
        f"STOP policy/rule (Recruitment Part A): expected missing/blocked, got {ready_a!r}"
    )
    assert ready_a.get("transfer_allowed") is False
    next_a = ready_a.get("next_action") or {}
    assert isinstance(next_a, dict) and next_a.get("code"), (
        f"STOP policy/rule (Recruitment Part A next_action): {ready_a!r}"
    )
    src = str(next_a.get("source_layer") or "")
    assert src in _DRIVER_CAPS or src == CAP_DOCUMENT_PACKS or src == CAP_RECRUITMENT_PACKAGE, (
        f"STOP policy/rule: next_action not composition-driven: {next_a!r}"
    )
    # Route intact: structured verdict returned (not topology collapse).
    assert "decision" in ready_a and "composition_id" in ready_a

    # ----- Recruitment Part B: same person, satisfy Ready -----
    _patch_ready_capabilities_satisfied(monkeypatch)
    ready_b = await recruitment_public.evaluate_ready_transfer(
        db,
        tenant_id=_TENANT,
        candidate_id=_CANDIDATE,
        ready_context={READY_COMPOSITION_ID_KEY: COMPOSITION_DRIVER},
    )
    assert ready_b.get("composition_id") == COMPOSITION_DRIVER
    assert ready_b.get("decision") == DECISION_ALLOWED, (
        f"STOP policy/rule (Recruitment Part B): expected allowed, got {ready_b!r}"
    )
    assert ready_b.get("transfer_allowed") is True
    assert ready_b.get("candidate_id") == _CANDIDATE

    pkg = _rfe_package()
    errs = boundary_ready.validate_ready_for_employment_package_v1(pkg)
    assert errs == [], f"STOP kernel/integration (RFE after Ready): {errs}"

    # ----- Employment accept (topology unchanged) -----
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
    db.get = AsyncMock(side_effect=lambda _m, id_: handoff if str(id_) == _HANDOFF else None)

    async def _accept(_db, *, handoff_id, reviewed_by_user_id, tenant_id):  # noqa: ARG001
        handoff.status = "accepted"
        return handoff, None

    monkeypatch.setattr("backend.app.services.handoff.accept_handoff", _accept)
    monkeypatch.setattr(
        "backend.app.services.employment_accept_orchestrator.log_audit_event",
        AsyncMock(),
    )
    accept = await employment_public.apply_employment_accept_policy(
        db,
        tenant_id=_TENANT,
        handoff_id=_HANDOFF,
        actor_id=_ACTOR,
        package=pkg,
    )
    assert accept.get("accepted") is True, f"STOP kernel/integration (accept): {accept!r}"

    # Formalize / ensure (Kernel path; not PEM-1 policy content)
    monkeypatch.setattr(
        "backend.app.services.employment_formalize_orchestrator.ensure_employee_after_formalize_apply",
        AsyncMock(
            return_value=SimpleNamespace(
                employee_id=_EMPLOYEE,
                employee_created=True,
                wrote=True,
                skipped_reason=None,
                linked_handoff_id=_HANDOFF,
            )
        ),
    )
    formalize = await employment_public.formalize_employment_for_handoff(
        db,
        tenant_id=_TENANT,
        handoff_id=_HANDOFF,
        package=pkg,
        employment_context=_admit_ctx(),
        confirmed_actions=[ACTION_CONTRACT_BASIS],
        authoritative_apply=True,
        actor_user_id=_ACTOR,
    )
    assert formalize.get("employee_id") == _EMPLOYEE, f"STOP kernel (formalize): {formalize!r}"

    import backend.app.services.employment_start_allowed_orchestrator as admit_orch

    monkeypatch.setattr(
        admit_orch,
        "resolve_employee_for_handoff",
        AsyncMock(return_value=employee),
    )
    monkeypatch.setattr(admit_orch, "list_active_exceptions", AsyncMock(return_value=[]))

    # ----- Employment Part A: PEM-1 Admit + missing -----
    monkeypatch.setattr(
        admit_orch,
        "_load_evidence_views",
        AsyncMock(return_value=(None, None, None)),
    )
    admit_a = await employment_public.evaluate_start_allowed_for_handoff(
        db,
        tenant_id=_TENANT,
        handoff_id=_HANDOFF,
        employment_context=_admit_ctx(),
    )
    assert admit_a.get("ruleset_id") == RULESET_PEM1, (
        f"STOP policy/rule (Admit composition): {admit_a!r}"
    )
    assert admit_a.get("decision") == DECISION_MISSING, (
        f"STOP policy/rule (Employment Part A): expected missing, got {admit_a!r}"
    )
    assert admit_a.get("start_allowed") is False
    primary = (admit_a.get("primary_item") or {}).get("code")
    assert primary in {REQ_CONTRACT, REQ_MEDICAL, REQ_BHP, "planned_start_date"}, (
        f"STOP policy/rule: Admit next_action not PEM-1 composition: {admit_a!r}"
    )
    required = {a.get("code") for a in (admit_a.get("required_actions") or [])}
    assert {REQ_CONTRACT, REQ_MEDICAL, REQ_BHP} <= required or primary == REQ_CONTRACT

    # Progression: contract only → still missing next composition requirement
    monkeypatch.setattr(
        admit_orch,
        "_load_evidence_views",
        AsyncMock(return_value=(_ok_contract(), None, None)),
    )
    admit_mid = await employment_public.evaluate_start_allowed_for_handoff(
        db,
        tenant_id=_TENANT,
        handoff_id=_HANDOFF,
        employment_context=_admit_ctx(),
    )
    assert admit_mid.get("start_allowed") is False
    assert admit_mid.get("decision") == DECISION_MISSING
    mid_code = (admit_mid.get("primary_item") or {}).get("code")
    assert mid_code in {REQ_MEDICAL, REQ_BHP, "planned_start_date"}, (
        f"STOP policy/rule (Admit progression): after contract expected next PEM-1 req, got {admit_mid!r}"
    )
    assert mid_code != REQ_CONTRACT, "STOP policy/rule: next_action did not advance after satisfied contract"

    # ----- Employment Part B: satisfy Contract/Medical/BHP -----
    monkeypatch.setattr(
        admit_orch,
        "_load_evidence_views",
        AsyncMock(return_value=(_ok_contract(), _ok_medical(), _ok_bhp())),
    )
    admit_b = await employment_public.evaluate_start_allowed_for_handoff(
        db,
        tenant_id=_TENANT,
        handoff_id=_HANDOFF,
        employment_context=_admit_ctx(),
    )
    assert admit_b.get("ruleset_id") == RULESET_PEM1
    assert admit_b.get("decision") == DECISION_START_ALLOWED, (
        f"STOP policy/rule (Employment Part B): {admit_b!r}"
    )
    assert admit_b.get("start_allowed") is True

    monkeypatch.setattr(
        "backend.app.services.employment_started_orchestrator._resolve_handoff_employee",
        AsyncMock(return_value=employee),
    )
    monkeypatch.setattr(
        "backend.app.services.employment_started_orchestrator.evaluate_start_allowed_for_handoff",
        AsyncMock(return_value=admit_b),
    )
    monkeypatch.setattr(
        "backend.app.services.employment_started_orchestrator.log_audit_event",
        AsyncMock(),
    )
    started = await employment_public.confirm_employment_started_for_handoff(
        db,
        tenant_id=_TENANT,
        handoff_id=_HANDOFF,
        actor_id=_ACTOR,
        package=pkg,
        employment_context=_admit_ctx(),
        start_confirmation={"confirmed": True, "start_date": "2026-10-01"},
    )
    assert started.get("decision") == DECISION_STARTED, f"STOP kernel (Confirm): {started!r}"
    assert started.get("started") is True
    assert str(started.get("employee_id")) == _EMPLOYEE

    async def _find(_db, tenant_id, candidate_id):  # noqa: ARG001
        assert str(candidate_id) == _CANDIDATE
        return employee

    monkeypatch.setattr(
        "backend.app.services.workforce_employees.find_employee_by_candidate",
        _find,
    )
    monkeypatch.setattr(
        "backend.app.services.workforce_employees.ensure_hr_profiles_bundle",
        AsyncMock(),
    )
    found = await workforce_started.find_employee_by_candidate(db, _TENANT, _CANDIDATE)
    assert found is not None and str(found.id) == _EMPLOYEE
    assert PHYSICAL_START_META_KEY in (found.meta or {})
    await workforce_started.ensure_hr_profiles_bundle(db, _TENANT, _EMPLOYEE)
