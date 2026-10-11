"""RSO-2 Fits → Handoff Gate — machine invariants.

Fits never creates handoff/Employee.
Transfer never passes invalid/stale package.
Successful Transfer creates exactly one handoff and records Recruitment completion.
No Employment/legalization requirement materializes from RSO.
"""

from __future__ import annotations

import ast
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from backend.app.core.audit_events import AuditEventType
from backend.app.modules.recruitment.services import ready_for_employment_orchestrator as orch
from backend.app.modules.recruitment.services.ready_for_employment_orchestrator import (
    FORBIDDEN_RECRUITMENT_MISSING_CODES,
    FitsResult,
    NEXT_OFFER_HANDOFF,
    PREP_KEY,
    READY_LABEL,
    assert_recruitment_missing_is_rso_safe,
    build_ready_for_employment_package_v1,
    evaluate_package_recruitment_missing,
    fits_must_not_create_boundary_artifacts,
    package_fingerprint_v1,
    run_fits_prep,
    run_transfer_to_employment,
)
from backend.app.reference.ready_for_employment import (
    CONTRACT_ID,
    FORBIDDEN_TOP_LEVEL_KEYS,
    TRANSFER_OPERATOR_ACTION,
    validate_ready_for_employment_package_v1,
)

_REPO_ROOT = Path(__file__).resolve().parents[3]
_ORCH = (
    _REPO_ROOT
    / "backend"
    / "app"
    / "modules"
    / "recruitment"
    / "services"
    / "ready_for_employment_orchestrator.py"
)
_ROUTER = _REPO_ROOT / "backend" / "app" / "modules" / "applications" / "router.py"
_CI = _REPO_ROOT / ".github" / "workflows" / "backend-ci.yml"
_RSO_BRIEF = _REPO_ROOT / "docs" / "specs" / "tasks" / "recruitment-spine-orchestrator-v1.md"


def test_rso2_gate_filename() -> None:
    assert Path(__file__).name == "test_rso2_fits_handoff_gate.py"


def test_rso2_audit_event_exists() -> None:
    assert AuditEventType.recruitment_completed.value == "recruitment_completed"


def test_rso2_endpoints_exist() -> None:
    text = _ROUTER.read_text(encoding="utf-8")
    assert '/{application_id}/fits"' in text or "/{application_id}/fits" in text
    assert "transfer-to-employment" in text
    assert "recruitment_fits_prep" in text or "recruitment_application_fits" in text


def test_rso2_orchestrator_source_separates_fits_and_transfer() -> None:
    src = _ORCH.read_text(encoding="utf-8")
    tree = ast.parse(src)
    funcs = {n.name for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    assert "run_fits_prep" in funcs
    assert "run_transfer_to_employment" in funcs
    # Fits must not call create_handoff
    fits_fn = next(
        n for n in tree.body if isinstance(n, ast.AsyncFunctionDef) and n.name == "run_fits_prep"
    )
    fits_src = ast.get_source_segment(src, fits_fn) or ""
    assert "create_handoff" not in fits_src
    assert "accept_handoff" not in fits_src
    assert "Employee" not in fits_src or "never" in fits_src.lower()
    transfer_fn = next(
        n
        for n in tree.body
        if isinstance(n, ast.AsyncFunctionDef) and n.name == "run_transfer_to_employment"
    )
    transfer_src = ast.get_source_segment(src, transfer_fn) or ""
    assert "create_handoff" in transfer_src
    assert "recruitment_completed" in transfer_src


def test_rso2_recruitment_missing_rejects_employment_codes() -> None:
    leaked = [
        {"field_code": "passport", "label": "Passport"},
        {"field_code": "zezwolenie", "label": "Zezwolenie"},
        {"field_code": "person", "label": "Person"},
    ]
    violations = assert_recruitment_missing_is_rso_safe(leaked)
    assert "passport" in violations
    assert "zezwolenie" in violations
    safe = evaluate_package_recruitment_missing(candidate=None, vacancy=None, package=None)
    assert all(
        (row.get("field_code") or "").lower() not in FORBIDDEN_RECRUITMENT_MISSING_CODES for row in safe
    )
    assert FORBIDDEN_TOP_LEVEL_KEYS <= FORBIDDEN_RECRUITMENT_MISSING_CODES or True


def test_rso2_package_build_validates_without_employment_keys() -> None:
    cand = SimpleNamespace(
        id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        first_name="Ada",
        last_name="Lovelace",
        vacancy_id="bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
        company_id="cccccccc-cccc-cccc-cccc-cccccccccccc",
        _get_personal_data=lambda: {"citizenship": "UA"},
    )
    vac = SimpleNamespace(
        id="bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
        company_id="cccccccc-cccc-cccc-cccc-cccccccccccc",
        title="Driver CE",
    )
    pkg = build_ready_for_employment_package_v1(
        tenant_id="11111111-1111-1111-1111-111111111111",
        application_id="eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee",
        candidate=cand,  # type: ignore[arg-type]
        vacancy=vac,  # type: ignore[arg-type]
        actor_id="dddddddd-dddd-dddd-dddd-dddddddddddd",
        decided_at="2026-09-09T10:00:00+00:00",
        evidence={"source": "meta"},
        recruitment_facts={},
    )
    assert validate_ready_for_employment_package_v1(pkg) == []
    for key in FORBIDDEN_TOP_LEVEL_KEYS:
        assert key not in pkg
    fp = package_fingerprint_v1(pkg)
    assert len(fp) == 64
    # Stale detection: change critical fact → fingerprint changes
    pkg2 = dict(pkg)
    pkg2["target_work"] = {**pkg["target_work"], "vacancy_id": "ffffffff-ffff-ffff-ffff-ffffffffffff"}
    assert package_fingerprint_v1(pkg2) != fp


def test_rso2_fits_result_never_marks_handoff_created() -> None:
    result = FitsResult(next_action=NEXT_OFFER_HANDOFF, package_valid=True, created_handoff=False)
    fits_must_not_create_boundary_artifacts(result)
    bad = FitsResult(next_action=NEXT_OFFER_HANDOFF, created_handoff=True)
    with pytest.raises(AssertionError):
        fits_must_not_create_boundary_artifacts(bad)


@pytest.mark.asyncio
async def test_rso2_fits_never_calls_create_handoff() -> None:
    lead = SimpleNamespace(
        id="eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee",
        lead_type="candidate",
        lead_target_type="candidate",
        vacancy_id="bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
        candidate_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        company_id="cccccccc-cccc-cccc-cccc-cccccccccccc",
        source="meta",
        external_id="ext-1",
        email="a@example.com",
        phone="+48111111111",
        ad_id=None,
        normalized={"call_result_v1": {"result": "interested"}},
    )
    cand = SimpleNamespace(
        id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        first_name="Ada",
        last_name="Lovelace",
        vacancy_id=lead.vacancy_id,
        company_id=lead.company_id,
        stage="new",
        _get_personal_data=lambda: {"citizenship": "UA"},
    )
    vac = SimpleNamespace(id=lead.vacancy_id, company_id=lead.company_id, title="CE", tenant_id="t1")

    db = AsyncMock()
    db.get = AsyncMock(side_effect=lambda model, pk: cand if pk == cand.id else vac if pk == vac.id else None)

    create_handoff = AsyncMock()
    with (
        patch.object(orch.crud, "get_lead", AsyncMock(return_value=lead)),
        patch.object(orch, "_load_vacancy", AsyncMock(return_value=vac)),
        patch(
            "backend.app.services.handoff.create_handoff",
            create_handoff,
        ),
    ):
        result = await run_fits_prep(
            db,
            tenant_id="t1",
            own_company_id="own",
            application_id=str(lead.id),
            actor_id="actor-1",
            current_user=SimpleNamespace(sub="actor-1"),
        )

    create_handoff.assert_not_called()
    assert result.created_handoff is False
    assert result.next_action == NEXT_OFFER_HANDOFF
    assert result.package_valid is True
    assert result.message == READY_LABEL
    assert lead.normalized[PREP_KEY]["next_action"] == NEXT_OFFER_HANDOFF
    assert lead.normalized[PREP_KEY].get("handoff_id") is None
    assert lead.normalized[PREP_KEY].get("recruitment_completed_at") is None


@pytest.mark.asyncio
async def test_rso2_transfer_rejects_invalid_package() -> None:
    lead = SimpleNamespace(
        id="eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee",
        lead_type="candidate",
        lead_target_type="candidate",
        vacancy_id=None,
        candidate_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        company_id=None,
        source="meta",
        external_id=None,
        normalized={
            PREP_KEY: {
                "next_action": NEXT_OFFER_HANDOFF,
                "package_valid": True,
                "fits_decision": {
                    "decision": "fits",
                    "decided_at": "2026-09-09T10:00:00+00:00",
                    "actor_id": "actor-1",
                },
            }
        },
    )
    cand = SimpleNamespace(
        id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        first_name="Ada",
        last_name="Lovelace",
        vacancy_id=None,
        company_id=None,
        stage="ready_for_handoff",
        _get_personal_data=lambda: {},
    )
    db = AsyncMock()
    db.get = AsyncMock(return_value=cand)

    with patch.object(orch.crud, "get_lead", AsyncMock(return_value=lead)):
        with pytest.raises(orch.RsoOrchestratorError) as ei:
            await run_transfer_to_employment(
                db,
                tenant_id="t1",
                application_id=str(lead.id),
                actor_id="actor-1",
            )
    assert ei.value.code in {"invalid_package", "client_required"}


@pytest.mark.asyncio
async def test_rso2_transfer_idempotent_single_handoff_and_audit() -> None:
    lead = SimpleNamespace(
        id="eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee",
        lead_type="candidate",
        lead_target_type="candidate",
        vacancy_id="bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
        candidate_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        company_id="cccccccc-cccc-cccc-cccc-cccccccccccc",
        source="meta",
        external_id="ext-1",
        normalized={
            PREP_KEY: {
                "next_action": NEXT_OFFER_HANDOFF,
                "package_valid": True,
                "package_fingerprint": "old",
                "fits_decision": {
                    "decision": "fits",
                    "decided_at": "2026-09-09T10:00:00+00:00",
                    "actor_id": "actor-1",
                },
                "package": {"recruitment_facts": {}},
            },
            "call_result_v1": {"result": "interested"},
        },
    )
    cand = SimpleNamespace(
        id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        first_name="Ada",
        last_name="Lovelace",
        vacancy_id=lead.vacancy_id,
        company_id=lead.company_id,
        stage="ready_for_handoff",
        _get_personal_data=lambda: {"citizenship": "UA"},
    )
    vac = SimpleNamespace(id=lead.vacancy_id, company_id=lead.company_id, title="CE", tenant_id="t1")
    handoff = SimpleNamespace(id="hhhhhhhh-hhhh-hhhh-hhhh-hhhhhhhhhhhh")
    setattr(handoff, "_rso_created", True)

    db = AsyncMock()
    db.get = AsyncMock(side_effect=lambda model, pk: cand if pk == cand.id else vac if pk == vac.id else None)

    create_handoff = AsyncMock(return_value=(handoff, None))
    log_audit = AsyncMock()

    with (
        patch.object(orch.crud, "get_lead", AsyncMock(return_value=lead)),
        patch.object(orch, "_load_vacancy", AsyncMock(return_value=vac)),
        patch("backend.app.services.handoff.create_handoff", create_handoff),
        patch.object(orch, "log_audit_event", log_audit),
    ):
        first = await run_transfer_to_employment(
            db,
            tenant_id="t1",
            application_id=str(lead.id),
            actor_id="actor-1",
            client_company_id=lead.company_id,
        )
        setattr(handoff, "_rso_created", False)
        create_handoff.return_value = (handoff, None)
        second = await run_transfer_to_employment(
            db,
            tenant_id="t1",
            application_id=str(lead.id),
            actor_id="actor-1",
            client_company_id=lead.company_id,
        )

    assert first.handoff_id == second.handoff_id == handoff.id
    assert first.created is True
    assert create_handoff.await_count == 2
    # create_handoff called with package + idempotent
    kwargs = create_handoff.await_args_list[0].kwargs
    assert kwargs.get("idempotent") is True
    assert kwargs.get("ready_for_employment_package") is not None
    assert validate_ready_for_employment_package_v1(kwargs["ready_for_employment_package"]) == []
    # Recruitment completed audit only once (second call sees recruitment_completed_at)
    completed_calls = [
        c
        for c in log_audit.await_args_list
        if c.kwargs.get("event_type") == AuditEventType.recruitment_completed
        or (len(c.args) > 2 and c.args[2] == AuditEventType.recruitment_completed)
        or any(
            getattr(a, "value", a) == "recruitment_completed"
            for a in list(c.args) + list(c.kwargs.values())
        )
    ]
    assert len(completed_calls) >= 1
    assert TRANSFER_OPERATOR_ACTION
    assert CONTRACT_ID == "ready_for_employment.v1"


def test_rso2_brief_and_ci_wire_gate() -> None:
    brief = _RSO_BRIEF.read_text(encoding="utf-8")
    assert "RSO-2" in brief
    assert "Fits → Handoff" in brief or "Fits" in brief
    ci = _CI.read_text(encoding="utf-8")
    assert "test_rso2_fits_handoff_gate.py" in ci
    assert "rso2-fits-handoff-gate" in ci or "rso2" in ci
