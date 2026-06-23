"""P2B — Process Engine transition gate bridge tests."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select, text

from backend.app.entity_profile.constants import DRIVER_CE_PROFILE_CODE
from backend.app.entity_profile.seed import ensure_tenant_entity_profile_defaults
from backend.app.models.candidate import Candidate
from backend.app.models.candidate_profile import CandidateProfile
from backend.app.models.vacancy import Vacancy
from backend.app.process_engine.constants import RECRUITMENT_MODULE
from backend.app.process_engine.evaluator_adapter import TransitionEvaluatorAdapter
from backend.app.requirement_rules.constants import REQUIREMENT_EVALUATION_V1
from backend.app.entity_profile.manifests.recruitment import recruitment_candidate_driver_ce_profile
from backend.app.requirement_rules.evaluator import evaluate_requirement_rules
from backend.app.requirement_rules.transition_bridge import (
    READY_FOR_HANDOFF_STAGE,
    TRANSITION_CONTEXT,
    is_ready_for_handoff_gate,
    map_requirement_evaluation_to_transition_gate,
    merge_transition_requirement_gate,
)


def _profile_view_from_manifest() -> dict:
    manifest = recruitment_candidate_driver_ce_profile()
    return {
        "entity_profile_code": manifest["profile_code"],
        "profile_code": manifest["profile_code"],
        "profile": {
            "profile_code": manifest["profile_code"],
            "entity_type": manifest["entity_type"],
            "document_pack_code": manifest["document_pack_code"],
            "process_profile_code": manifest["process_profile_code"],
        },
        "fields": manifest["fields"],
    }


def test_p2b_is_ready_for_handoff_gate() -> None:
    assert is_ready_for_handoff_gate("ready_for_handoff") is True
    assert is_ready_for_handoff_gate("READY_FOR_HANDOFF") is True
    assert is_ready_for_handoff_gate("docs_got") is False
    assert is_ready_for_handoff_gate(None) is False


def test_p2b_map_evaluation_to_transition_gate_blockers() -> None:
    evaluation = evaluate_requirement_rules(
        _profile_view_from_manifest(),
        context=TRANSITION_CONTEXT,
        normalized_payload={"recruitment.candidate.first_name": "Jan"},
        documents=[{"type": "passport", "status": "uploaded"}],
    )
    gate = map_requirement_evaluation_to_transition_gate(evaluation)
    assert gate["applied"] is True
    assert gate["satisfied"] is False
    assert gate["context"] == TRANSITION_CONTEXT
    assert "code95" in gate["missing_documents"]
    assert any(row["source_layer"] == "requirement_engine" for row in gate["blocking_reasons"])


def test_p2b_merge_blocks_transition_when_unsatisfied() -> None:
    report = {
        "transfer_allowed": True,
        "handoff_create_allowed": True,
        "ready": True,
        "package_ready": True,
        "blocking_reasons": [],
        "warnings": [],
        "missing_documents": [],
        "missing_data_fields": [],
        "source_layers": ["document_packs"],
    }
    gate = {
        "applied": True,
        "satisfied": False,
        "context": TRANSITION_CONTEXT,
        "blocking_reasons": [
            {
                "code": "document_required:code95",
                "message": "Required document missing: code95",
                "source_layer": "requirement_engine",
                "document_type_code": "code95",
            }
        ],
        "warnings": [],
        "missing_documents": ["code95"],
        "missing_data_fields": [],
        "requirement_engine": {"applied": True, "satisfied": False},
    }
    merged = merge_transition_requirement_gate(report, gate)
    assert merged["transfer_allowed"] is False
    assert merged["handoff_create_allowed"] is False
    assert "requirement_engine" in merged["source_layers"]
    assert any(
        row.get("source_layer") == "requirement_engine" and row.get("document_type_code") == "code95"
        for row in merged["blocking_reasons"]
    )
    assert merged.get("requirement_gate", {}).get("applied") is True


def test_p2b_merge_preserves_allowed_when_satisfied() -> None:
    report = {
        "transfer_allowed": True,
        "handoff_create_allowed": True,
        "blocking_reasons": [],
        "warnings": [],
        "missing_documents": [],
        "missing_data_fields": [],
        "source_layers": ["document_packs"],
    }
    gate = {
        "applied": True,
        "satisfied": True,
        "context": TRANSITION_CONTEXT,
        "blocking_reasons": [],
        "warnings": [],
        "missing_documents": [],
        "missing_data_fields": [],
        "requirement_engine": {"applied": True, "satisfied": True},
    }
    merged = merge_transition_requirement_gate(report, gate)
    assert merged["transfer_allowed"] is True
    assert "requirement_engine" in merged["source_layers"]


@pytest.mark.anyio
async def test_p2b_evaluator_legacy_fallback_without_profile(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _resolve(db, *, tenant_id, candidate_id, target_stage=None, require_destination=False):
        return {
            "transfer_allowed": True,
            "handoff_create_allowed": True,
            "blocking_reasons": [],
            "source_layers": ["document_packs"],
            "policy_version": "transfer_policy_v1",
        }

    monkeypatch.setattr(
        "backend.app.process_engine.evaluator_adapter.TransferPolicyResolver.resolve",
        _resolve,
    )
    monkeypatch.setattr(
        TransitionEvaluatorAdapter,
        "_resolve_recruitment_target_system_stage",
        AsyncMock(return_value=READY_FOR_HANDOFF_STAGE),
    )
    monkeypatch.setattr(
        "backend.app.requirement_rules.transition_bridge.evaluate_ready_for_handoff_requirement_gate",
        AsyncMock(return_value=None),
    )

    report = await TransitionEvaluatorAdapter.evaluate_transition(
        db=None,  # type: ignore[arg-type]
        tenant_id="tenant-1",
        module=RECRUITMENT_MODULE,
        entity_type="candidate",
        entity_id="cand-legacy",
        target_system_stage=READY_FOR_HANDOFF_STAGE,
    )
    assert report["transfer_allowed"] is True
    assert "requirement_engine" not in report.get("source_layers", [])


@pytest.mark.anyio
async def test_p2b_evaluator_blocks_missing_documents(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _resolve(db, *, tenant_id, candidate_id, target_stage=None, require_destination=False):
        return {
            "transfer_allowed": True,
            "handoff_create_allowed": True,
            "blocking_reasons": [],
            "missing_documents": [],
            "missing_data_fields": [],
            "source_layers": ["document_packs"],
            "policy_version": "transfer_policy_v1",
        }

    gate = {
        "applied": True,
        "satisfied": False,
        "context": TRANSITION_CONTEXT,
        "entity_profile_code": DRIVER_CE_PROFILE_CODE,
        "blocking_reasons": [
            {
                "code": "document_required:passport",
                "message": "Required document missing: passport",
                "source_layer": "requirement_engine",
                "document_type_code": "passport",
            },
            {
                "code": "document_required:code95",
                "message": "Required document missing: code95",
                "source_layer": "requirement_engine",
                "document_type_code": "code95",
            },
        ],
        "warnings": [],
        "missing_documents": ["passport", "code95"],
        "missing_data_fields": [],
        "requirement_engine": {
            "applied": True,
            "satisfied": False,
            "evaluation_version": REQUIREMENT_EVALUATION_V1,
        },
    }

    monkeypatch.setattr(
        "backend.app.process_engine.evaluator_adapter.TransferPolicyResolver.resolve",
        _resolve,
    )
    monkeypatch.setattr(
        TransitionEvaluatorAdapter,
        "_resolve_recruitment_target_system_stage",
        AsyncMock(return_value=READY_FOR_HANDOFF_STAGE),
    )
    monkeypatch.setattr(
        "backend.app.requirement_rules.transition_bridge.evaluate_ready_for_handoff_requirement_gate",
        AsyncMock(return_value=gate),
    )

    report = await TransitionEvaluatorAdapter.evaluate_transition(
        db=None,  # type: ignore[arg-type]
        tenant_id="tenant-1",
        module=RECRUITMENT_MODULE,
        entity_type="candidate",
        entity_id="cand-blocked",
        target_system_stage=READY_FOR_HANDOFF_STAGE,
    )
    assert report["transfer_allowed"] is False
    assert "requirement_engine" in report["source_layers"]
    assert "passport" in report["missing_documents"]
    assert any(row.get("source_layer") == "requirement_engine" for row in report["blocking_reasons"])

    err = await TransitionEvaluatorAdapter.assert_transition_allowed(
        db=None,  # type: ignore[arg-type]
        tenant_id="tenant-1",
        module=RECRUITMENT_MODULE,
        entity_type="candidate",
        entity_id="cand-blocked",
        target_system_stage=READY_FOR_HANDOFF_STAGE,
    )
    assert err.get("code") == "transfer_blocked"
    assert any(row.get("source_layer") == "requirement_engine" for row in err.get("blocking_reasons") or [])


@pytest.mark.anyio
async def test_p2b_integration_full_package_allows_transition(db, tenant_id: str) -> None:
    try:
        await db.execute(text("SELECT 1 FROM ep_entity_profiles LIMIT 1"))
    except Exception as exc:
        pytest.skip(f"Entity Profile tables not available: {exc}")

    from backend.app.seed_candidate_profiles import ensure_driver_ce_default_profile

    company_row = (
        await db.execute(
            text("SELECT id FROM companies WHERE tenant_id = :tid LIMIT 1"),
            {"tid": tenant_id},
        )
    ).first()
    if not company_row:
        pytest.skip("No company for tenant")
    company_id = company_row[0]

    await ensure_tenant_entity_profile_defaults(db, tenant_id)
    await ensure_driver_ce_default_profile(db, tenant_id)

    profile = (
        await db.execute(
            select(CandidateProfile).where(
                CandidateProfile.tenant_id == tenant_id,
                CandidateProfile.code == "driver_ce_default",
            )
        )
    ).scalar_one_or_none()
    assert profile is not None

    vacancy = Vacancy(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        company_id=company_id,
        title=f"P2B vacancy {uuid.uuid4().hex[:6]}",
        candidate_profile_id=profile.id,
    )
    db.add(vacancy)
    await db.flush()

    candidate = Candidate(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        first_name="Jan",
        last_name="Kowalski",
        phone="+48123456789",
        email="jan@example.com",
        vacancy_id=vacancy.id,
        company_id=company_id,
    )
    db.add(candidate)
    await db.commit()

    from backend.app.requirement_rules.transition_bridge import evaluate_ready_for_handoff_requirement_gate

    gate = await evaluate_ready_for_handoff_requirement_gate(
        db,
        tenant_id=tenant_id,
        candidate_id=str(candidate.id),
    )
    assert gate is not None
    assert gate["entity_profile_code"] == DRIVER_CE_PROFILE_CODE
    assert gate["satisfied"] is False
    assert "passport" in gate["missing_documents"]

    # Satisfied evaluation with full document set (unit-level via evaluator)
    evaluation = evaluate_requirement_rules(
        _profile_view_from_manifest(),
        context=TRANSITION_CONTEXT,
        normalized_payload={
            "recruitment.candidate.first_name": "Jan",
            "recruitment.candidate.last_name": "Kowalski",
            "recruitment.candidate.contacts.phone": "+48123456789",
        },
        documents=[
            {"document_type_code": "passport", "status": "approved", "has_files": True},
            {"document_type_code": "driver_license", "status": "approved", "has_files": True},
            {"document_type_code": "code95", "status": "approved", "has_files": True},
            {"document_type_code": "tacho_card", "status": "approved", "has_files": True},
        ],
    )
    assert evaluation["satisfied"] is True
    satisfied_gate = map_requirement_evaluation_to_transition_gate(evaluation)
    assert satisfied_gate["satisfied"] is True
    assert satisfied_gate["blocking_reasons"] == []
