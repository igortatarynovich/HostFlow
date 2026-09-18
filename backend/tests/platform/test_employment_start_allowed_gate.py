"""Employment Start Allowed Gate (PEM-1 machine foundation / slice 1).

Derived admit-to-work. No mint. No UI. No ESO-5 semantic change.
"""

from __future__ import annotations

from pathlib import Path

from backend.app.reference.employment_start_allowed import (
    ADAPT_REL,
    APPLY_API,
    ARCH_REL,
    DECISION_BLOCKED,
    DECISION_MISSING,
    DECISION_REJECTED_PATCH,
    DECISION_START_ALLOWED,
    DECISION_UNSUPPORTED,
    DECISION_VALUES,
    EVALUATE_API,
    EXCEPTION_BHP_SUCCESSIVE,
    FACT_PLANNED_START,
    FORBIDDEN_REQUIREMENT_CODES,
    FOUNDATION_REL,
    PEM1_EXCEPTION_ALLOWLIST,
    POLICY_ID,
    REQ_BHP,
    REQ_CONTRACT,
    REQ_MEDICAL,
    apply_employment_start_allowed_v1,
    evaluate_employment_start_allowed_v1,
    prove_bhp_successive_exception,
)
from backend.app.services.employment_start_allowed_evidence import (
    project_bhp_evidence_view,
    project_contract_evidence_view,
    project_medical_evidence_view,
)

_REPO_ROOT = Path(__file__).resolve().parents[3]
_ARCH = _REPO_ROOT / ARCH_REL
_ADAPT = _REPO_ROOT / ADAPT_REL
_FOUNDATION = _REPO_ROOT / FOUNDATION_REL
_CI = _REPO_ROOT / ".github" / "workflows" / "backend-ci.yml"
_MODULE = _REPO_ROOT / "backend" / "app" / "reference" / "employment_start_allowed.py"
_EVIDENCE = _REPO_ROOT / "backend" / "app" / "services" / "employment_start_allowed_evidence.py"
_EXC_MODEL = _REPO_ROOT / "backend" / "app" / "models" / "workforce_start_allowed_exception.py"
_HANDOFF_EMP = _REPO_ROOT / "backend" / "app" / "services" / "workforce_employees.py"


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


def test_start_allowed_gate_filename() -> None:
    assert Path(__file__).name == "test_employment_start_allowed_gate.py"


def test_start_allowed_policy_id_and_apis() -> None:
    assert POLICY_ID == "employment_start_allowed.v1"
    assert EVALUATE_API == "evaluate_employment_start_allowed_v1"
    assert APPLY_API == "apply_employment_start_allowed_v1"
    assert "def evaluate_employment_start_allowed_v1(" in _MODULE.read_text(encoding="utf-8")
    assert DECISION_VALUES == (
        DECISION_START_ALLOWED,
        DECISION_MISSING,
        DECISION_BLOCKED,
        DECISION_UNSUPPORTED,
        DECISION_REJECTED_PATCH,
    )
    assert EXCEPTION_BHP_SUCCESSIVE in PEM1_EXCEPTION_ALLOWLIST
    assert PEM1_EXCEPTION_ALLOWLIST[EXCEPTION_BHP_SUCCESSIVE] == REQ_BHP


def test_start_allowed_requires_employee() -> None:
    r = evaluate_employment_start_allowed_v1(employee_id=None, employment_context=_pem1_ctx())
    assert r["decision"] == DECISION_BLOCKED
    assert r["start_allowed"] is False


def test_start_allowed_unsupported_non_pem1() -> None:
    r = evaluate_employment_start_allowed_v1(
        employee_id="e1",
        employment_context=_pem1_ctx(pathway_id="pl_third_country_work_authorization"),
    )
    assert r["decision"] == DECISION_UNSUPPORTED
    assert r["start_allowed"] is False


def test_start_allowed_missing_without_evidence() -> None:
    r = evaluate_employment_start_allowed_v1(employee_id="e1", employment_context=_pem1_ctx())
    assert r["decision"] == DECISION_MISSING
    assert r["primary_item"]["code"] == REQ_CONTRACT
    assert r["start_allowed"] is False
    codes = {a["code"] for a in r["required_actions"]}
    assert codes == {REQ_CONTRACT, REQ_MEDICAL, REQ_BHP}
    assert not (codes & FORBIDDEN_REQUIREMENT_CODES)


def test_start_allowed_document_exists_not_enough() -> None:
    contract = project_contract_evidence_view({"id": "x", "type": "employment_contract", "meta": {}})
    assert contract is not None
    assert contract["written_instrument_confirmed"] is False
    r = evaluate_employment_start_allowed_v1(
        employee_id="e1",
        employment_context=_pem1_ctx(),
        contract_view=contract,
        medical_view=_ok_medical(),
        bhp_view=_ok_bhp(),
    )
    assert r["decision"] == DECISION_MISSING
    assert r["primary_item"]["code"] == REQ_CONTRACT


def test_start_allowed_draft_preview_not_proof() -> None:
    view = project_contract_evidence_view(
        {"id": "d", "generation_kind": "contract_draft_preview", "meta": {"signed_at": "2026-09-01"}}
    )
    assert view is not None
    assert view["written_instrument_confirmed"] is False


def test_start_allowed_medical_needs_planned_start_not_today() -> None:
    r = evaluate_employment_start_allowed_v1(
        employee_id="e1",
        employment_context=_pem1_ctx(planned_start_date=None),
        contract_view=_ok_contract(),
        medical_view=_ok_medical(),
        bhp_view=_ok_bhp(),
    )
    assert r["decision"] == DECISION_MISSING
    assert r["primary_item"]["code"] == FACT_PLANNED_START
    assert r["start_allowed"] is False


def test_start_allowed_medical_expires_before_start() -> None:
    med = project_medical_evidence_view(
        {
            "id": "m",
            "meta": {
                "expires_at": "2026-09-30",
                "fit_for_work": True,
                "applies_to_post": "driver_ce",
                "conditions_match": True,
            },
        }
    )
    r = evaluate_employment_start_allowed_v1(
        employee_id="e1",
        employment_context=_pem1_ctx(planned_start_date="2026-10-01"),
        contract_view=_ok_contract(),
        medical_view=med,
        bhp_view=_ok_bhp(),
    )
    assert r["decision"] == DECISION_MISSING
    assert r["primary_item"]["code"] == REQ_MEDICAL


def test_start_allowed_complete_with_evidence() -> None:
    r = evaluate_employment_start_allowed_v1(
        employee_id="e1",
        employment_context=_pem1_ctx(),
        contract_view=_ok_contract(),
        medical_view=_ok_medical(),
        bhp_view=_ok_bhp(),
    )
    assert r["decision"] == DECISION_START_ALLOWED
    assert r["start_allowed"] is True
    assert r["started"] is False
    assert r["manual_override"] is False
    assert r["employee_minted_by_this_policy"] is False


def test_start_allowed_exception_only_allowlisted_and_proven() -> None:
    bad = apply_employment_start_allowed_v1(
        employee_id="e1",
        employment_context=_pem1_ctx(),
        contract_view=_ok_contract(),
        medical_view=_ok_medical(),
        bhp_view=None,
        resolution_patch={"exception": {"exception_code": "made_up", "facts": {}}},
    )
    assert bad["decision"] == DECISION_REJECTED_PATCH
    assert bad["rejection_reason"] == "exception_code_not_allowlisted"

    weak = apply_employment_start_allowed_v1(
        employee_id="e1",
        employment_context=_pem1_ctx(),
        contract_view=_ok_contract(),
        medical_view=_ok_medical(),
        resolution_patch={
            "exception": {
                "exception_code": EXCEPTION_BHP_SUCCESSIVE,
                "facts": {
                    "employer_id": "cccccccc-cccc-cccc-cccc-cccccccccccc",
                    "post_key": "driver_ce",
                    "prior_contract_ref": "c-1",
                    "prior_contract_end_date": "2026-09-01",
                    "current_contract_start_date": "2026-10-01",
                    "successive": True,
                },
            }
        },
    )
    assert weak["decision"] == DECISION_REJECTED_PATCH
    assert weak["rejection_reason"] == "exception_succession_not_proven"
    assert "succession_gap_too_large" in weak["succession_violations"]

    assert prove_bhp_successive_exception(
        {
            "employer_id": "e",
            "post_key": "p",
            "prior_contract_ref": "c",
            "prior_contract_end_date": "2026-09-30",
            "current_contract_start_date": "2026-10-01",
            "successive": True,
        }
    ) == []

    ok = apply_employment_start_allowed_v1(
        employee_id="e1",
        employment_context=_pem1_ctx(),
        contract_view=_ok_contract(),
        medical_view=_ok_medical(),
        resolution_patch={
            "exception": {
                "exception_code": EXCEPTION_BHP_SUCCESSIVE,
                "facts": {
                    "employer_id": "cccccccc-cccc-cccc-cccc-cccccccccccc",
                    "post_key": "driver_ce",
                    "prior_contract_ref": "c-1",
                    "prior_contract_end_date": "2026-09-30",
                    "current_contract_start_date": "2026-10-01",
                    "successive": True,
                },
            }
        },
    )
    assert ok["decision"] == DECISION_START_ALLOWED
    assert ok["start_allowed"] is True


def test_start_allowed_force_override_rejected() -> None:
    r = apply_employment_start_allowed_v1(
        employee_id="e1",
        employment_context=_pem1_ctx(),
        resolution_patch={"allow_anyway": True, "start_allowed": True},
    )
    assert r["decision"] == DECISION_REJECTED_PATCH
    assert r["rejection_reason"] == "manual_override_forbidden"
    assert r["start_allowed"] is False


def test_start_allowed_derived_state_replay() -> None:
    """snapshot = audit; evaluator = authority — invalidation must drop start_allowed."""
    ctx = _pem1_ctx()
    contract = _ok_contract()
    medical = _ok_medical()
    bhp = _ok_bhp()
    first = evaluate_employment_start_allowed_v1(
        employee_id="e1",
        employment_context=ctx,
        contract_view=contract,
        medical_view=medical,
        bhp_view=bhp,
    )
    assert first["start_allowed"] is True
    snapshot = dict(first)  # audit copy

    # Evidence becomes invalid (medical expires before start)
    medical_bad = project_medical_evidence_view(
        {
            "id": "doc-med",
            "meta": {
                "expires_at": "2026-09-01",
                "fit_for_work": True,
                "applies_to_post": "driver_ce",
                "conditions_match": True,
            },
        }
    )
    second = evaluate_employment_start_allowed_v1(
        employee_id="e1",
        employment_context=ctx,
        contract_view=contract,
        medical_view=medical_bad,
        bhp_view=bhp,
    )
    assert second["start_allowed"] is False
    assert second["decision"] == DECISION_MISSING
    # Old snapshot must not retain authority
    assert snapshot["start_allowed"] is True
    assert second["start_allowed"] is not snapshot["start_allowed"]
    assert second.get("decision_snapshot_is_authority") is False


def test_start_allowed_one_primary_item() -> None:
    r = evaluate_employment_start_allowed_v1(employee_id="e1", employment_context=_pem1_ctx())
    assert r["decision"] == DECISION_MISSING
    assert isinstance(r["primary_item"], dict)
    assert r["primary_item"]["code"] == r["active_missing"][0]["code"]


def test_start_allowed_docs_and_artifacts_exist() -> None:
    assert _ARCH.is_file()
    assert _ADAPT.is_file()
    assert _FOUNDATION.is_file()
    assert _EVIDENCE.is_file()
    assert _EXC_MODEL.is_file()
    text = _FOUNDATION.read_text(encoding="utf-8")
    assert "derived-state replay" in text or "derived state" in text.lower() or "Derived-state" in text
    assert "handoff_from_candidate" in text


def test_start_allowed_slice1_does_not_touch_mint_module_imports() -> None:
    """Slice 1 must not call or import handoff_from_candidate / create_employee."""
    for path in (_MODULE, _EVIDENCE, _EXC_MODEL):
        text = path.read_text(encoding="utf-8")
        assert "handoff_from_candidate" not in text
        assert "create_employee(" not in text
    assert _HANDOFF_EMP.is_file()
    assert "async def handoff_from_candidate" in _HANDOFF_EMP.read_text(encoding="utf-8")


def test_start_allowed_ci_job_wired() -> None:
    ci = _CI.read_text(encoding="utf-8")
    assert "employment-start-allowed-gate" in ci or "test_employment_start_allowed_gate.py" in ci
