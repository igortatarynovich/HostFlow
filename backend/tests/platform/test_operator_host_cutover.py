"""Operator Host Cutover (ADR-042) — machine invariants.

Fits uses existing process and must not become Ready or Transfer.
A Fits candidate who has not passed existing recruitment readiness cannot Transfer.
RFE is assembled from existing Candidate readiness at the Candidate→HR boundary.
"""

from __future__ import annotations

import ast
from pathlib import Path
from types import SimpleNamespace

import pytest

from backend.app.modules.recruitment.services.operator_host_cutover import record_fits_decision_on_lead
from backend.app.modules.recruitment.services.ready_for_employment_package import (
    FITS_DECISION_KEY,
    OPEN_CANDIDATE_NEXT,
    PREP_KEY,
    build_ready_for_employment_package_v1,
    candidate_stage_is_transfer_ready,
    package_fingerprint_v1,
)
from backend.app.reference.ready_for_employment import (
    validate_ready_for_employment_package_v1,
)

_REPO = Path(__file__).resolve().parents[3]
_FITS_MUT = _REPO / "backend" / "app" / "modules" / "applications" / "mutations.py"
_ORCH = _REPO / "backend" / "app" / "modules" / "recruitment" / "services" / "operator_host_cutover.py"
_PKG = _REPO / "backend" / "app" / "modules" / "recruitment" / "services" / "ready_for_employment_package.py"
_HANDOFF = _REPO / "backend" / "app" / "services" / "handoff.py"
_ROUTER = _REPO / "backend" / "app" / "modules" / "applications" / "router.py"
_DECISION = (
    _REPO
    / "hostflow-frontend"
    / "src"
    / "platform"
    / "application-workspace"
    / "resolveRecruitmentApplicationDecision.ts"
)


def test_cutover_files_exist() -> None:
    assert _ORCH.is_file()
    assert _PKG.is_file()
    assert "recruitment_fits_application" in _FITS_MUT.read_text(encoding="utf-8")
    assert "/{application_id}/fits" in _ROUTER.read_text(encoding="utf-8")


def test_fits_source_does_not_offer_handoff_or_set_ready() -> None:
    src = _FITS_MUT.read_text(encoding="utf-8")
    tree = ast.parse(src)
    fits_fn = next(
        n for n in tree.body if isinstance(n, ast.AsyncFunctionDef) and n.name == "recruitment_fits_application"
    )
    dumped = ast.dump(fits_fn)
    assert "create_handoff" not in dumped
    assert "offer_handoff" not in dumped
    assert "ready_for_handoff" not in dumped
    orch = _ORCH.read_text(encoding="utf-8")
    record_fn = ast.parse(orch)
    record = next(
        n for n in record_fn.body if isinstance(n, ast.FunctionDef) and n.name == "record_fits_decision_on_lead"
    )
    rec_dump = ast.dump(record)
    assert "create_handoff" not in rec_dump
    assigns = [
        n
        for n in ast.walk(record)
        if isinstance(n, ast.Assign)
        and any(isinstance(t, ast.Attribute) and t.attr == "stage" for t in n.targets)
    ]
    assert assigns == []


def test_create_handoff_does_not_bump_stage_to_ready() -> None:
    src = _HANDOFF.read_text(encoding="utf-8")
    tree = ast.parse(src)
    fn = next(n for n in tree.body if isinstance(n, ast.AsyncFunctionDef) and n.name == "create_handoff")
    assigns = [
        n
        for n in ast.walk(fn)
        if isinstance(n, ast.Assign)
        and any(isinstance(t, ast.Attribute) and t.attr == "stage" for t in n.targets)
    ]
    assert assigns == []


def test_application_ui_has_fits_and_no_employment_verbs() -> None:
    text = _DECISION.read_text(encoding="utf-8")
    assert "id: 'fits'" in text
    assert "formalize" not in text.lower()
    assert "transfer-to-employment" not in text
    assert "offer_handoff" not in text


def test_fits_decision_does_not_mark_ready() -> None:
    lead = SimpleNamespace(normalized={}, next_action_type="fits")
    record_fits_decision_on_lead(lead, actor_id="u1", candidate_id="cand-1")
    assert lead.next_action_type == OPEN_CANDIDATE_NEXT
    assert lead.normalized[FITS_DECISION_KEY]["decision"] == "fits"
    assert lead.normalized[FITS_DECISION_KEY]["candidate_id"] == "cand-1"
    prep = lead.normalized.get(PREP_KEY) or {}
    assert prep.get("next_action") != "offer_handoff"
    assert prep.get("transfer_action") is None


def test_package_builder_is_valid_without_employment_keys() -> None:
    cand = SimpleNamespace(
        id="cand-1",
        first_name="Ada",
        last_name="Nowak",
        vacancy_id="vac-1",
        company_id="co-1",
        _get_personal_data=lambda: {"citizenship": "PL"},
    )
    vac = SimpleNamespace(id="vac-1", company_id="co-1", title="Driver")
    pkg = build_ready_for_employment_package_v1(
        tenant_id="t1",
        application_id="app-1",
        candidate=cand,  # type: ignore[arg-type]
        vacancy=vac,  # type: ignore[arg-type]
        actor_id="u1",
        decided_at="2026-09-10T00:00:00+00:00",
    )
    assert validate_ready_for_employment_package_v1(pkg) == []
    assert "employee_id" not in pkg
    fp = package_fingerprint_v1(pkg)
    assert len(fp) == 64


def test_new_stage_is_not_transfer_ready() -> None:
    assert candidate_stage_is_transfer_ready("new") is False
    assert candidate_stage_is_transfer_ready("contacted") is False
    assert candidate_stage_is_transfer_ready("ready_for_handoff") is True


def test_create_handoff_stage_gate_precedes_rfe_assemble() -> None:
    src = _HANDOFF.read_text(encoding="utf-8")
    stage_at = src.find('Only candidates at ready_for_handoff or ready_for_hr')
    assemble_at = src.find("assemble_ready_for_employment_for_candidate")
    assert stage_at != -1
    assert assemble_at != -1
    assert stage_at < assemble_at
    assert "candidate.stage = \"ready_for_handoff\"" not in src
    assert "candidate.stage = 'ready_for_handoff'" not in src


@pytest.mark.anyio
async def test_fits_candidate_at_new_cannot_transfer(monkeypatch: pytest.MonkeyPatch) -> None:
    """A Fits-entered candidate at existing default stage cannot Transfer.

    This is the #359 regression: Transfer must not succeed (or bump Ready)
    just because the person is already a Candidate.
    """
    from backend.app.services import company_module_enforcement
    from backend.app.services.handoff import create_handoff

    candidate = SimpleNamespace(id="cand-1", tenant_id="t1", stage="new")
    assemble_calls: list[object] = []

    class _Db:
        async def get(self, _model, _id):
            return candidate

    async def _ok(*_args, **_kwargs):
        return None

    async def _assemble(*_args, **_kwargs):
        assemble_calls.append(1)
        raise AssertionError("RFE must not assemble before existing recruitment readiness")

    monkeypatch.setattr(company_module_enforcement, "assert_recruitment_for_candidate", _ok)
    monkeypatch.setattr(company_module_enforcement, "assert_hr_for_candidate", _ok)
    monkeypatch.setattr(
        "backend.app.modules.recruitment.services.operator_host_cutover.assemble_ready_for_employment_for_candidate",
        _assemble,
    )

    handoff, err = await create_handoff(
        _Db(),  # type: ignore[arg-type]
        candidate_id="cand-1",
        agency_tenant_id="t1",
        client_company_id="co-1",
        requested_by_user_id="u1",
        destination="internal_hr",
    )
    assert handoff is None
    assert err == "Only candidates at ready_for_handoff or ready_for_hr can be transferred to internal HR"
    assert candidate.stage == "new"
    assert assemble_calls == []
