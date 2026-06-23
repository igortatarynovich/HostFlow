"""P2A — Readiness consumer bridge tests."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select, text

from backend.app.entity_profile.constants import DRIVER_CE_PROFILE_CODE
from backend.app.entity_profile.manifests.recruitment import recruitment_candidate_driver_ce_profile
from backend.app.entity_profile.seed import ensure_tenant_entity_profile_defaults
from backend.app.entity_profile.vacancy_bridge import resolve_entity_profile_hints_from_vacancy
from backend.app.models.candidate import Candidate
from backend.app.models.candidate_profile import CandidateProfile
from backend.app.models.vacancy import Vacancy
from backend.app.requirement_rules.constants import REQUIREMENT_EVALUATION_V1
from backend.app.requirement_rules.evaluator import evaluate_requirement_rules
from backend.app.requirement_rules.readiness_bridge import (
    build_normalized_payload_from_candidate,
    build_requirement_engine_section,
    evaluate_candidate_readiness_requirements,
    map_requirement_evaluation_to_package_fragments,
    resolve_entity_profile_code_for_candidate,
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


def test_p2a_payload_builder_maps_candidate_fields() -> None:
    cand = SimpleNamespace(
        first_name="Jan",
        last_name="Kowalski",
        phone="+48111222333",
        email="jan@example.com",
        _get_contacts=lambda: {},
        _get_personal_data=lambda: {"citizenship": "PL"},
        _get_extra=lambda: {"experience_eu_years": "5"},
    )
    payload = build_normalized_payload_from_candidate(cand)  # type: ignore[arg-type]
    assert payload["recruitment.candidate.first_name"] == "Jan"
    assert payload["recruitment.candidate.last_name"] == "Kowalski"
    assert payload["recruitment.candidate.contacts.phone"] == "+48111222333"
    assert payload["platform.identity.citizenship"] == "PL"


def test_p2a_map_evaluation_to_readiness_fragments() -> None:
    evaluation = evaluate_requirement_rules(
        _profile_view_from_manifest(),
        context="readiness",
        normalized_payload={"recruitment.candidate.first_name": "Jan"},
        documents=[{"type": "passport", "status": "uploaded", "has_files": True}],
    )
    fragments = map_requirement_evaluation_to_package_fragments(evaluation)
    assert "passport" in fragments["missing_documents"]
    assert "code95" in fragments["missing_documents"]
    assert "tacho_card" in fragments["missing_documents"]
    assert any(row["field_code"] == "last_name" for row in fragments["missing_data_fields"])
    assert any(row["source_layer"] == "requirement_engine" for row in fragments["blocking_reasons"])


def test_p2a_requirement_engine_section_shape() -> None:
    evaluation = evaluate_requirement_rules(
        _profile_view_from_manifest(),
        context="readiness",
        normalized_payload={},
        documents=[],
    )
    section = build_requirement_engine_section(evaluation)
    assert section["applied"] is True
    assert section["evaluation_version"] == REQUIREMENT_EVALUATION_V1
    assert section["entity_profile_code"] == DRIVER_CE_PROFILE_CODE
    assert section["satisfied"] is False
    assert len(section["required_documents"]) == 4


@pytest.mark.anyio
async def test_p2a_legacy_fallback_when_no_entity_profile(db, tenant_id: str) -> None:
    cand = SimpleNamespace(
        id="cand-no-profile",
        tenant_id=tenant_id,
        vacancy_id=None,
    )
    code = await resolve_entity_profile_code_for_candidate(db, tenant_id=tenant_id, candidate=cand)  # type: ignore[arg-type]
    assert code is None

    result = await evaluate_candidate_readiness_requirements(db, tenant_id=tenant_id, candidate=cand)  # type: ignore[arg-type]
    assert result is None


@pytest.mark.anyio
async def test_p2a_evaluates_via_requirement_engine_with_vacancy(db, tenant_id: str) -> None:
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
        title=f"P2A vacancy {uuid.uuid4().hex[:6]}",
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
        last_name="",
        phone="",
        vacancy_id=vacancy.id,
        company_id=company_id,
    )
    db.add(candidate)
    await db.commit()

    resolved = await resolve_entity_profile_code_for_candidate(db, tenant_id=tenant_id, candidate=candidate)
    assert resolved == DRIVER_CE_PROFILE_CODE

    evaluation = await evaluate_candidate_readiness_requirements(
        db,
        tenant_id=tenant_id,
        candidate=candidate,
    )
    assert evaluation is not None
    assert evaluation["evaluation_version"] == REQUIREMENT_EVALUATION_V1
    assert evaluation["satisfied"] is False

    missing_docs = {
        row.get("document_type_code")
        for row in evaluation.get("blockers") or []
        if row.get("document_type_code")
    }
    assert "passport" in missing_docs
    assert "code95" in missing_docs
    assert "tacho_card" in missing_docs

    missing_fields = {
        row.get("qualified_code")
        for row in evaluation.get("blockers") or []
        if row.get("qualified_code")
    }
    assert "recruitment.candidate.last_name" in missing_fields
    assert "recruitment.candidate.contacts.phone" in missing_fields


@pytest.mark.anyio
async def test_p2a_recruitment_package_embeds_requirement_engine(monkeypatch: pytest.MonkeyPatch) -> None:
    from backend.app.services.recruitment_package_readiness import evaluate_recruitment_package

    cand = SimpleNamespace(
        id="cand-pkg",
        tenant_id="tenant-1",
        vacancy_id=None,
        stage="docs_got",
        own_company_id=None,
        phone="+48111222333",
        email="a@b.c",
        first_name="Jan",
        last_name="Kowalski",
        _get_extra=lambda: {},
        _get_personal_data=lambda: {"address": "Street 1"},
        _get_contacts=lambda: {},
    )

    class _Result:
        def scalar_one_or_none(self):
            return cand

    db = SimpleNamespace(execute=AsyncMock(return_value=_Result()))

    async def _eligibility(*args, **kwargs):
        return {
            "eligibility_status": "eligible",
            "allowed_operations": {"handoff_to_hr": True},
            "readiness_profiles": {"hr_ready": {"status": "ready"}},
            "missing_documents": [],
            "pending_verification_documents": [],
        }

    async def _req_engine(*args, **kwargs):
        return {
            "evaluation_version": REQUIREMENT_EVALUATION_V1,
            "entity_profile_code": DRIVER_CE_PROFILE_CODE,
            "satisfied": False,
            "blockers": [
                {
                    "code": "document_required:code95",
                    "message": "Required document missing: code95",
                    "document_type_code": "code95",
                }
            ],
            "warnings": [],
            "required_fields": [],
            "required_documents": [{"document_type_code": "code95"}],
            "rule_sources_applied": [{"source": "document_pack"}],
            "context": "readiness",
        }

    monkeypatch.setattr(
        "backend.app.services.recruitment_package_readiness.resolve_workforce_eligibility_via_contract",
        _eligibility,
    )
    monkeypatch.setattr(
        "backend.app.requirement_rules.readiness_bridge.evaluate_candidate_readiness_requirements",
        _req_engine,
    )
    monkeypatch.setattr(
        "backend.app.services.recruitment_package_readiness._missing_contact_fields",
        AsyncMock(return_value=[]),
    )

    pkg = await evaluate_recruitment_package(db, tenant_id="tenant-1", candidate_id="cand-pkg")  # type: ignore[arg-type]
    assert pkg.get("requirement_engine", {}).get("applied") is True
    assert "code95" in pkg.get("missing_documents") or []


@pytest.mark.anyio
async def test_p2a_recruitment_package_legacy_without_requirement_engine(monkeypatch: pytest.MonkeyPatch) -> None:
    from backend.app.services.recruitment_package_readiness import evaluate_recruitment_package

    cand = SimpleNamespace(
        id="cand-legacy",
        tenant_id="tenant-1",
        vacancy_id=None,
        stage="docs_got",
        own_company_id=None,
        phone="+48111222333",
        email="a@b.c",
        first_name="Jan",
        last_name="Kowalski",
        _get_extra=lambda: {},
        _get_personal_data=lambda: {"address": "Street 1"},
        _get_contacts=lambda: {},
    )

    class _Result:
        def scalar_one_or_none(self):
            return cand

    db = SimpleNamespace(execute=AsyncMock(return_value=_Result()))

    async def _eligibility(*args, **kwargs):
        return {
            "eligibility_status": "eligible",
            "allowed_operations": {"handoff_to_hr": True},
            "readiness_profiles": {"hr_ready": {"status": "ready"}},
            "missing_documents": [],
            "pending_verification_documents": [],
        }

    monkeypatch.setattr(
        "backend.app.services.recruitment_package_readiness.resolve_workforce_eligibility_via_contract",
        _eligibility,
    )
    monkeypatch.setattr(
        "backend.app.requirement_rules.readiness_bridge.evaluate_candidate_readiness_requirements",
        AsyncMock(return_value=None),
    )
    monkeypatch.setattr(
        "backend.app.services.recruitment_package_readiness._missing_contact_fields",
        AsyncMock(return_value=[]),
    )

    pkg = await evaluate_recruitment_package(db, tenant_id="tenant-1", candidate_id="cand-legacy")  # type: ignore[arg-type]
    assert "requirement_engine" not in pkg
    assert "ready" in pkg
    assert "blocks" in pkg
