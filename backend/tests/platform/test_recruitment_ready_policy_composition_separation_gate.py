"""Recruitment Ready policy / composition separation gate.

Proves one runtime path: resolve → applicable evaluate → aggregate for three
compositions on one architecture:

  [] (empty) → allowed  (requirements NOT invoked; minimal fixture)
  driver + unsatisfied → missing (+ next_action)
  driver + satisfied → allowed

Resolver is a separate authority; empty is a registered composition, not bypass.
Cold-process import of recruitment.public.ready must succeed.
"""

from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from backend.app.modules.recruitment.public import ready as ready_public
from backend.app.reference.recruitment_ready_policy import (
    AGGREGATE_API,
    COMPOSITION_DRIVER,
    COMPOSITION_EMPTY,
    DECISION_ALLOWED,
    DECISION_MISSING,
    READY_COMPOSITION_ID_KEY,
    RESOLVE_API,
    SEPARATION_REL,
    aggregate_ready_verdict_v1,
    resolve_ready_composition_v1,
)
from backend.app.services.transfer_policy_resolver import (
    RECRUITMENT_CONFIRMED_BLOCKS_EXTRA_KEY,
    TransferPolicyResolver,
)

_REPO_ROOT = Path(__file__).resolve().parents[3]
_POLICY = _REPO_ROOT / "backend" / "app" / "reference" / "recruitment_ready_policy.py"
_TRANSFER = _REPO_ROOT / "backend" / "app" / "services" / "transfer_policy_resolver.py"
_READY_PUBLIC = (
    _REPO_ROOT / "backend" / "app" / "modules" / "recruitment" / "public" / "ready.py"
)
_BRIEF = _REPO_ROOT / SEPARATION_REL
_CI = _REPO_ROOT / ".github" / "workflows" / "backend-ci.yml"
_GATE = Path(__file__)
_L2 = _REPO_ROOT / "docs" / "specs" / "workflows" / "transfer-policy.md"

_POLICY_EVAL_PATCHES = (
    "backend.app.services.recruitment_package_readiness.evaluate_recruitment_package",
    "backend.app.field_registry.requirement_evaluator.evaluate_field_requirements_for_candidate",
    "backend.app.services.operational_requirements_service.evaluate_operational_requirements_for_candidate",
    "backend.app.services.transfer_policy_resolver.resolve_workforce_eligibility_via_contract",
)


def _minimal_candidate() -> SimpleNamespace:
    """Minimal fixture that does NOT satisfy legacy driver requirements."""
    return SimpleNamespace(
        id="cand-empty-preflight",
        tenant_id="tenant-1",
        deleted_at=None,
        stage="new",
        company_id=None,
        own_company_id=None,
        vacancy_id=None,
        phone=None,
        email=None,
        _get_extra=lambda: {RECRUITMENT_CONFIRMED_BLOCKS_EXTRA_KEY: []},
        _get_personal_data=lambda: {},
    )


def _db_for(cand: SimpleNamespace) -> SimpleNamespace:
    class _Result:
        def scalar_one_or_none(self):
            return cand

    return SimpleNamespace(execute=AsyncMock(return_value=_Result()))


def _patch_routing(monkeypatch: pytest.MonkeyPatch) -> None:
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


def test_ready_composition_separation_gate_filename() -> None:
    assert _GATE.name == "test_recruitment_ready_policy_composition_separation_gate.py"


def test_ready_composition_apis_and_brief() -> None:
    assert RESOLVE_API == "resolve_ready_composition_v1"
    assert AGGREGATE_API == "aggregate_ready_verdict_v1"
    text = _POLICY.read_text(encoding="utf-8")
    assert f"def {RESOLVE_API}(" in text
    assert f"def {AGGREGATE_API}(" in text
    assert _BRIEF.is_file()
    brief = _BRIEF.read_text(encoding="utf-8")
    assert "Implementation locks" in brief
    assert "**Status:** **PASS**" in brief or "Status:** **PASS**" in brief


def test_resolver_is_separate_authority_ast() -> None:
    """TransferPolicyResolver.resolve must call resolve_ready_composition_v1."""
    tree = ast.parse(_TRANSFER.read_text(encoding="utf-8"))
    resolve_method = None
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "TransferPolicyResolver":
            for item in node.body:
                if (
                    isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and item.name == "resolve"
                ):
                    resolve_method = item
    assert resolve_method is not None
    calls: set[str] = set()
    for n in ast.walk(resolve_method):
        if isinstance(n, ast.Call):
            if isinstance(n.func, ast.Name):
                calls.add(n.func.id)
            elif isinstance(n.func, ast.Attribute):
                calls.add(n.func.attr)
    assert "resolve_ready_composition_v1" in calls
    assert "aggregate_ready_verdict_v1" in calls


def test_no_bypass_flags_in_ready_policy() -> None:
    text = _POLICY.read_text(encoding="utf-8") + _TRANSFER.read_text(encoding="utf-8")
    # Mentions in ban docs are OK; executable bypass paths are not.
    assert "if kernel_mode" not in text
    assert "kernel_mode =" not in text
    assert "skip_requirements" not in text.replace(
        "not a kernel_mode / skip_requirements bypass.", ""
    )
    assert "neutral=true" not in text
    assert "neutral = True" not in text


def test_public_ready_accepts_selector_not_capability_list() -> None:
    src = _READY_PUBLIC.read_text(encoding="utf-8")
    assert "READY_COMPOSITION_ID_KEY" in src
    assert "evaluate_ready_transfer" in src
    assert '["package"' not in src
    assert "capability list" in src.lower() or "capability lists" in src.lower()
    # Public module must not eagerly import package readiness (cold-import lock).
    tree = ast.parse(src)
    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            mod = getattr(node, "module", None) or ""
            assert "recruitment_package_readiness" not in mod
            assert "transfer_policy_resolver" not in mod


def test_cold_process_import_recruitment_public_ready() -> None:
    probe = (
        "import importlib\n"
        "m = importlib.import_module('backend.app.modules.recruitment.public.ready')\n"
        "assert m.COMPOSITION_EMPTY == 'empty'\n"
        "r = m.resolve_ready_composition_v1({m.READY_COMPOSITION_ID_KEY: 'empty'})\n"
        "assert r['resolved'] is True and r['capabilities'] == []\n"
        "raise SystemExit(0)\n"
    )
    proc = subprocess.run(
        [sys.executable, "-c", probe],
        cwd=str(_REPO_ROOT),
        env={
            **dict(**{k: v for k, v in __import__("os").environ.items()}),
            "PYTHONPATH": f"{_REPO_ROOT}:{_REPO_ROOT / 'backend'}",
        },
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_empty_composition_registered_via_resolver() -> None:
    r = resolve_ready_composition_v1({READY_COMPOSITION_ID_KEY: COMPOSITION_EMPTY})
    assert r["resolved"] is True
    assert r["composition_id"] == COMPOSITION_EMPTY
    assert r["capabilities"] == []
    verdict = aggregate_ready_verdict_v1(
        composition_id=COMPOSITION_EMPTY,
        capabilities=[],
        blocking_reasons=[],
    )
    assert verdict["decision"] == DECISION_ALLOWED
    assert verdict["transfer_allowed"] is True


def test_default_without_selector_is_driver() -> None:
    r = resolve_ready_composition_v1({})
    assert r["resolved"] is True
    assert r["composition_id"] == COMPOSITION_DRIVER
    assert "recruitment_package" in r["capabilities"]


@pytest.mark.anyio
async def test_empty_allowed_without_invoking_policy_requirements(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """[] → allowed on minimal fixture; package/fields/ops/docs must NOT run."""
    cand = _minimal_candidate()
    db = _db_for(cand)
    _patch_routing(monkeypatch)

    spies: dict[str, AsyncMock] = {}
    for path in _POLICY_EVAL_PATCHES:
        spy = AsyncMock(side_effect=AssertionError(f"policy evaluator invoked: {path}"))
        spies[path] = spy
        monkeypatch.setattr(path, spy)

    report = await ready_public.evaluate_ready_transfer(
        db,
        tenant_id="tenant-1",
        candidate_id=str(cand.id),
        ready_context={READY_COMPOSITION_ID_KEY: COMPOSITION_EMPTY},
    )
    assert report["decision"] == DECISION_ALLOWED
    assert report["transfer_allowed"] is True
    assert report["composition_id"] == COMPOSITION_EMPTY
    assert report["required_confirmations"] == []
    assert report["missing_documents"] == []
    for spy in spies.values():
        spy.assert_not_called()


@pytest.mark.anyio
async def test_driver_unsatisfied_missing_with_next_action(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cand = _minimal_candidate()
    db = _db_for(cand)
    _patch_routing(monkeypatch)

    monkeypatch.setattr(
        "backend.app.services.transfer_policy_resolver.resolve_workforce_eligibility_via_contract",
        AsyncMock(
            return_value={
                "eligibility_status": "pending_documents",
                "allowed_operations": {"handoff_to_hr": False},
                "readiness_profiles": {"hr_ready": {"status": "blocked"}},
                "missing_documents": ["passport"],
                "pending_verification_documents": [],
                "blocking_reasons": [
                    {
                        "code": "missing_required_document",
                        "reason": "Required document 'passport' is missing.",
                        "document_code": "passport",
                    }
                ],
            }
        ),
    )
    monkeypatch.setattr(
        "backend.app.services.transfer_policy_resolver.ReferenceServiceFacade.get_applicable_documents",
        AsyncMock(return_value=[{"document_code": "passport", "required": True}]),
    )
    monkeypatch.setattr(
        "backend.app.reference.requirement_policy_consumer_parity.r5_required_set",
        lambda *_a, **_k: frozenset({"passport"}),
    )
    monkeypatch.setattr(
        "backend.app.reference.document_policy_overlay_store.load_persisted_tenant_delta",
        AsyncMock(return_value={}),
    )
    monkeypatch.setattr(
        "backend.app.services.recruitment_package_readiness.evaluate_recruitment_package",
        AsyncMock(
            return_value={
                "ready": False,
                "blocks": [{"document_key": "Passport / ID", "status": "missing"}],
                "blocking_blocks": ["Passport / ID"],
                "missing_data_fields": [
                    {"field_code": "phone", "label": "Phone"},
                ],
            }
        ),
    )
    monkeypatch.setattr(
        "backend.app.field_registry.requirement_evaluator.evaluate_field_requirements_for_candidate",
        AsyncMock(
            return_value={
                "missing_fields": [{"field_code": "phone", "label": "Phone"}],
                "blocking_reasons": [
                    {
                        "code": "missing_data_field",
                        "message": "Missing required data: Phone",
                        "field_code": "phone",
                    }
                ],
            }
        ),
    )
    monkeypatch.setattr(
        "backend.app.services.operational_requirements_service.evaluate_operational_requirements_for_candidate",
        AsyncMock(return_value=[{"requirement_code": "first_contact_completed"}]),
    )
    monkeypatch.setattr(
        "backend.app.services.operational_requirements_service.operational_requirement_blocking_reasons",
        lambda _rows: [
            {
                "code": "operational_requirement_open",
                "message": "First contact not completed",
                "requirement_code": "first_contact_completed",
            }
        ],
    )
    monkeypatch.setattr(
        "backend.app.requirement_rules.readiness_bridge.resolve_entity_profile_code_for_candidate",
        AsyncMock(return_value="driver"),
    )

    report = await TransferPolicyResolver.resolve(
        db,  # type: ignore[arg-type]
        tenant_id="tenant-1",
        candidate_id=str(cand.id),
        ready_context={READY_COMPOSITION_ID_KEY: COMPOSITION_DRIVER},
    )
    assert report["decision"] == DECISION_MISSING
    assert report["transfer_allowed"] is False
    assert report["composition_id"] == COMPOSITION_DRIVER
    assert report.get("next_action")
    assert report["next_action"].get("code")


@pytest.mark.anyio
async def test_driver_satisfied_allowed(monkeypatch: pytest.MonkeyPatch) -> None:
    cand = SimpleNamespace(
        id="cand-driver-ok",
        tenant_id="tenant-1",
        deleted_at=None,
        stage="docs_got",
        company_id="c1",
        own_company_id=None,
        vacancy_id="v1",
        phone="+48111222333",
        email="a@b.c",
        _get_extra=lambda: {RECRUITMENT_CONFIRMED_BLOCKS_EXTRA_KEY: ["Passport / ID"]},
        _get_personal_data=lambda: {"address": "Street 1"},
    )
    db = _db_for(cand)
    _patch_routing(monkeypatch)
    monkeypatch.setattr(
        "backend.app.services.transfer_policy_resolver.resolve_workforce_eligibility_via_contract",
        AsyncMock(
            return_value={
                "eligibility_status": "eligible",
                "allowed_operations": {"handoff_to_hr": True},
                "readiness_profiles": {"hr_ready": {"status": "ready"}},
                "missing_documents": [],
                "pending_verification_documents": [],
                "blocking_reasons": [],
            }
        ),
    )
    monkeypatch.setattr(
        "backend.app.services.transfer_policy_resolver.ReferenceServiceFacade.get_applicable_documents",
        AsyncMock(return_value=[{"document_code": "passport", "required": True}]),
    )
    monkeypatch.setattr(
        "backend.app.reference.requirement_policy_consumer_parity.r5_required_set",
        lambda *_a, **_k: frozenset(),
    )
    monkeypatch.setattr(
        "backend.app.reference.document_policy_overlay_store.load_persisted_tenant_delta",
        AsyncMock(return_value={}),
    )
    monkeypatch.setattr(
        "backend.app.services.recruitment_package_readiness.evaluate_recruitment_package",
        AsyncMock(
            return_value={
                "ready": True,
                "blocks": [{"document_key": "Passport / ID", "status": "ready"}],
                "blocking_blocks": [],
                "missing_data_fields": [],
            }
        ),
    )
    monkeypatch.setattr(
        "backend.app.field_registry.requirement_evaluator.evaluate_field_requirements_for_candidate",
        AsyncMock(return_value={"missing_fields": [], "blocking_reasons": []}),
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
        AsyncMock(return_value="driver"),
    )

    report = await TransferPolicyResolver.resolve(
        db,  # type: ignore[arg-type]
        tenant_id="tenant-1",
        candidate_id=str(cand.id),
        ready_context={READY_COMPOSITION_ID_KEY: COMPOSITION_DRIVER},
    )
    assert report["decision"] == DECISION_ALLOWED
    assert report["transfer_allowed"] is True
    assert report["composition_id"] == COMPOSITION_DRIVER


def test_ci_wires_ready_composition_gate() -> None:
    text = _CI.read_text(encoding="utf-8")
    assert "recruitment-ready-policy-composition-separation-gate" in text or (
        "test_recruitment_ready_policy_composition_separation_gate.py" in text
    )


def test_l2_transfer_policy_amended() -> None:
    text = _L2.read_text(encoding="utf-8")
    assert "resolve_ready_composition_v1" in text or "Ready composition" in text
    assert "canonical" in text.lower() or "decision" in text
