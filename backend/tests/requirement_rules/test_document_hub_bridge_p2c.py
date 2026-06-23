"""P2C — Document Hub consumer bridge tests."""

from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest
from sqlalchemy import select, text

from backend.app.entity_profile.constants import DRIVER_CE_PROFILE_CODE
from backend.app.entity_profile.manifests.recruitment import recruitment_candidate_driver_ce_profile
from backend.app.entity_profile.seed import ensure_tenant_entity_profile_defaults
from backend.app.entity_profile.vacancy_bridge import resolve_entity_profile_hints_from_vacancy
from backend.app.models.candidate import Candidate
from backend.app.models.candidate_profile import CandidateProfile
from backend.app.models.vacancy import Vacancy
from backend.app.modules.documents.owner_summary import compute_owner_summary
from backend.app.requirement_rules.constants import REQUIREMENT_EVALUATION_V1
from backend.app.requirement_rules.document_hub_bridge import (
    SOURCE_LAYER,
    evaluate_candidate_document_hub_requirements,
    map_requirement_evaluation_to_document_hub,
    merge_requirement_engine_into_owner_summary,
)
from backend.app.requirement_rules.evaluator import evaluate_requirement_rules
from backend.app.requirement_rules.readiness_bridge import resolve_entity_profile_code_for_candidate
from backend.app.services.document_ruleset import load_default_ruleset


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


def test_p2c_driver_ce_required_documents_from_engine() -> None:
    evaluation = evaluate_requirement_rules(
        _profile_view_from_manifest(),
        context="readiness",
        normalized_payload={},
        documents=[],
    )
    hub = map_requirement_evaluation_to_document_hub(evaluation)

    assert hub["applied"] is True
    assert hub["source_layer"] == SOURCE_LAYER
    assert hub["entity_profile_code"] == DRIVER_CE_PROFILE_CODE
    assert hub["evaluation_version"] == REQUIREMENT_EVALUATION_V1

    required_codes = {row["document_type_code"] for row in hub["required_documents"]}
    assert required_codes == {"passport", "driver_license", "code95", "tacho_card"}
    assert all(row["source_layer"] == SOURCE_LAYER for row in hub["required_documents"])
    assert hub["missing_documents"] == sorted(required_codes)
    assert hub["satisfied_documents"] == []


def test_p2c_satisfied_documents_when_approved() -> None:
    evaluation = evaluate_requirement_rules(
        _profile_view_from_manifest(),
        context="readiness",
        normalized_payload={},
        documents=[
            {"type": "passport", "status": "approved", "has_files": True},
            {"type": "driver_license", "status": "approved", "has_files": True},
            {"type": "code95", "status": "approved", "has_files": True},
            {"type": "tacho_card", "status": "approved", "has_files": True},
        ],
    )
    hub = map_requirement_evaluation_to_document_hub(evaluation)

    assert hub["satisfied_documents"] == ["code95", "driver_license", "passport", "tacho_card"]
    assert hub["missing_documents"] == []
    statuses = {row["document_type_code"]: row["status"] for row in hub["required_documents"]}
    assert all(status == "satisfied" for status in statuses.values())


def test_p2c_missing_documents_when_absent() -> None:
    evaluation = evaluate_requirement_rules(
        _profile_view_from_manifest(),
        context="readiness",
        normalized_payload={},
        documents=[{"type": "passport", "status": "uploaded", "has_files": True}],
    )
    hub = map_requirement_evaluation_to_document_hub(evaluation)

    assert hub["satisfied_documents"] == []
    assert set(hub["missing_documents"]) == {"passport", "driver_license", "code95", "tacho_card"}

    by_code = {row["document_type_code"]: row for row in hub["required_documents"]}
    assert by_code["passport"]["status"] == "missing"
    assert by_code["code95"]["status"] == "missing"
    assert by_code["code95"]["source_layer"] == SOURCE_LAYER


def test_p2c_merge_into_owner_summary_overlays_requirement_engine() -> None:
    evaluation = evaluate_requirement_rules(
        _profile_view_from_manifest(),
        context="readiness",
        normalized_payload={},
        documents=[{"type": "passport", "status": "uploaded", "has_files": True}],
    )
    hub = map_requirement_evaluation_to_document_hub(evaluation)
    legacy_summary = compute_owner_summary(
        {"position_category": "driver"},
        load_default_ruleset(),
        [{"type": "passport", "status": "uploaded"}],
    )

    merged = merge_requirement_engine_into_owner_summary(legacy_summary, hub)

    assert merged["source_layer"] == SOURCE_LAYER
    assert merged["requirement_engine"]["applied"] is True
    assert set(merged["required"]["missing_types"]) == {"passport", "driver_license", "code95", "tacho_card"}
    assert merged["required"]["ready_types"] == []
    assert set(merged["checklist"]["requiredTypes"]) == {
        "passport",
        "driver_license",
        "code95",
        "tacho_card",
    }
    assert merged["checklist"]["source_layer"] == SOURCE_LAYER


@pytest.mark.anyio
async def test_p2c_legacy_fallback_when_no_entity_profile(db, tenant_id: str) -> None:
    cand = SimpleNamespace(
        id="cand-no-profile",
        tenant_id=tenant_id,
        vacancy_id=None,
    )
    code = await resolve_entity_profile_code_for_candidate(db, tenant_id=tenant_id, candidate=cand)  # type: ignore[arg-type]
    assert code is None

    result = await evaluate_candidate_document_hub_requirements(db, tenant_id=tenant_id, candidate=cand)  # type: ignore[arg-type]
    assert result is None


@pytest.mark.anyio
async def test_p2c_evaluates_via_requirement_engine_with_vacancy(db, tenant_id: str) -> None:
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
        title=f"P2C vacancy {uuid.uuid4().hex[:6]}",
        candidate_profile_id=profile.id,
    )
    db.add(vacancy)
    await db.flush()

    entity_code, _, _ = await resolve_entity_profile_hints_from_vacancy(
        db,
        tenant_id=tenant_id,
        vacancy_id=vacancy.id,
    )
    assert entity_code == DRIVER_CE_PROFILE_CODE

    candidate = Candidate(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        first_name="Anna",
        last_name="Nowak",
        phone="+48123456789",
        vacancy_id=vacancy.id,
        company_id=company_id,
    )
    db.add(candidate)
    await db.commit()

    hub = await evaluate_candidate_document_hub_requirements(
        db,
        tenant_id=tenant_id,
        candidate=candidate,
    )
    assert hub is not None
    assert hub["applied"] is True
    assert hub["source_layer"] == SOURCE_LAYER
    assert hub["entity_profile_code"] == DRIVER_CE_PROFILE_CODE

    required_codes = {row["document_type_code"] for row in hub["required_documents"]}
    assert required_codes == {"passport", "driver_license", "code95", "tacho_card"}
    assert hub["missing_documents"] == sorted(required_codes)
    assert hub["satisfied_documents"] == []
