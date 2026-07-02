"""Shared helpers for Candidate Evidence integration + handoff contract tests."""

from __future__ import annotations

import uuid
from datetime import date, timedelta
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.entity_profile.constants import DRIVER_CE_PROFILE_CODE
from backend.app.entity_profile.seed import ensure_tenant_entity_profile_defaults
from backend.app.models.candidate import Candidate
from backend.app.models.candidate_profile import CandidateProfile
from backend.app.models.vacancy import Vacancy

REQUIREMENT_FULFILLMENT_REQUIRED_KEYS = frozenset(
    {
        "requirement_code",
        "evidence_id",
        "evidence_variant_code",
        "documents",
    }
)
REQUIREMENT_FULFILLMENT_DOCUMENT_KEYS = frozenset(
    {
        "document_id",
        "document_type_code",
    }
)


def assert_handoff_requirement_fulfillments_contract(
    fulfillments: list[dict[str, Any]],
    *,
    min_count: int = 0,
) -> None:
    """Guard: handoff snapshot requirement_fulfillments[] shape (Recruitment → HR boundary)."""
    assert isinstance(fulfillments, list), "requirement_fulfillments must be a list"
    assert len(fulfillments) >= min_count
    for row in fulfillments:
        assert isinstance(row, dict), "each fulfillment must be an object"
        missing = REQUIREMENT_FULFILLMENT_REQUIRED_KEYS - set(row.keys())
        assert not missing, f"fulfillment missing keys: {sorted(missing)}"
        assert str(row["requirement_code"] or "").strip(), "requirement_code required"
        assert str(row["evidence_variant_code"] or "").strip(), "evidence_variant_code required"
        assert str(row["evidence_id"] or "").strip(), "evidence_id required"
        documents = row.get("documents")
        assert isinstance(documents, list), "documents must be a list"
        for doc in documents:
            assert isinstance(doc, dict), "each document ref must be an object"
            doc_missing = REQUIREMENT_FULFILLMENT_DOCUMENT_KEYS - set(doc.keys())
            assert not doc_missing, f"document ref missing keys: {sorted(doc_missing)}"
            assert str(doc["document_id"] or "").strip(), "document_id required"
            assert str(doc["document_type_code"] or "").strip(), "document_type_code required"
            assert "extracted_fields" in doc, "extracted_fields key must be present (may be empty dict)"


async def skip_unless_entity_profile_tables(db: AsyncSession) -> None:
    try:
        await db.execute(text("SELECT 1 FROM ep_entity_profiles LIMIT 1"))
    except Exception as exc:
        pytest.skip(f"Entity Profile tables not available: {exc}")


async def skip_unless_candidate_evidence_table(db: AsyncSession) -> None:
    try:
        await db.execute(text("SELECT 1 FROM candidate_evidence LIMIT 1"))
    except Exception as exc:
        pytest.skip(f"candidate_evidence table not available (run alembic upgrade head): {exc}")


async def setup_driver_ce_candidate(
    db: AsyncSession,
    tenant_id: str,
) -> tuple[Candidate, str]:
    """Create vacancy-bound candidate with driver_ce entity profile. Returns (candidate, company_id)."""
    await skip_unless_entity_profile_tables(db)
    await skip_unless_candidate_evidence_table(db)

    from backend.app.seed_candidate_profiles import ensure_driver_ce_default_profile

    company_row = (
        await db.execute(
            text("SELECT id FROM companies WHERE tenant_id = :tid LIMIT 1"),
            {"tid": tenant_id},
        )
    ).first()
    if not company_row:
        pytest.skip("No company for tenant")
    company_id = str(company_row[0])

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
        title=f"Evidence test {uuid.uuid4().hex[:6]}",
        candidate_profile_id=profile.id,
    )
    db.add(vacancy)
    await db.flush()

    candidate = Candidate(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        company_id=company_id,
        vacancy_id=vacancy.id,
        first_name="Evidence",
        last_name=f"Test{uuid.uuid4().hex[:4]}",
        phone="+48123456789",
        email=f"evidence-{uuid.uuid4().hex[:6]}@example.com",
    )
    db.add(candidate)
    await db.commit()
    await db.refresh(candidate)
    return candidate, company_id


async def post_document(
    client: AsyncClient,
    headers: dict[str, str],
    *,
    candidate_id: str,
    doc_type: str,
    status: str = "approved",
    expires_at: str | None = None,
    meta: dict[str, Any] | None = None,
) -> str:
    payload: dict[str, Any] = {
        "candidate_id": candidate_id,
        "type": doc_type,
        "status": status,
        "extra": {"title": doc_type},
    }
    if expires_at:
        payload["expires_at"] = expires_at
    if meta:
        payload["meta"] = meta
    resp = await client.post("/api/v1/documents/", headers=headers, json=payload)
    assert resp.status_code == 200, resp.text
    return str(resp.json()["id"])


async def get_checklist(
    client: AsyncClient,
    headers: dict[str, str],
    candidate_id: str,
) -> dict[str, Any]:
    resp = await client.get(
        f"/api/v1/candidates/{candidate_id}/requirements/checklist",
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


async def get_requirements_workspace(
    client: AsyncClient,
    headers: dict[str, str],
    candidate_id: str,
) -> dict[str, Any]:
    resp = await client.get(
        f"/api/v1/candidates/{candidate_id}/requirements/workspace",
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


def checklist_item(checklist: dict[str, Any], requirement_code: str) -> dict[str, Any]:
    for item in checklist.get("requirements") or []:
        if str(item.get("requirement_code") or "") == requirement_code:
            return item
    raise AssertionError(f"Requirement {requirement_code} not in checklist: {checklist}")


async def select_evidence(
    client: AsyncClient,
    headers: dict[str, str],
    *,
    candidate_id: str,
    requirement_code: str,
    evidence_variant_code: str,
) -> dict[str, Any]:
    resp = await client.post(
        f"/api/v1/candidates/{candidate_id}/requirements/{requirement_code}/select-evidence",
        headers=headers,
        json={"evidence_variant_code": evidence_variant_code},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


async def link_evidence_document(
    client: AsyncClient,
    headers: dict[str, str],
    *,
    candidate_id: str,
    evidence_id: str,
    document_id: str,
) -> None:
    resp = await client.post(
        f"/api/v1/candidates/{candidate_id}/requirements/evidence/{evidence_id}/documents",
        headers=headers,
        json={"document_id": document_id},
    )
    assert resp.status_code == 200, resp.text


async def approve_evidence_api(
    client: AsyncClient,
    headers: dict[str, str],
    *,
    candidate_id: str,
    evidence_id: str,
) -> dict[str, Any]:
    resp = await client.post(
        f"/api/v1/candidates/{candidate_id}/requirements/evidence/{evidence_id}/approve",
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


async def replace_evidence_api(
    client: AsyncClient,
    headers: dict[str, str],
    *,
    candidate_id: str,
    requirement_code: str,
    evidence_variant_code: str,
) -> dict[str, Any]:
    resp = await client.post(
        f"/api/v1/candidates/{candidate_id}/requirements/{requirement_code}/replace-evidence",
        headers=headers,
        json={"evidence_variant_code": evidence_variant_code},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


def future_expiry(days: int = 365) -> str:
    return (date.today() + timedelta(days=days)).isoformat()


def past_expiry(days: int = 30) -> str:
    return (date.today() - timedelta(days=days)).isoformat()


DRIVER_CE_REQUIREMENTS = (
    "identity_document",
    "legal_stay_confirmation",
    "driver_license_with_code95",
    "tachograph_card",
    "medical_fitness",
    "psychological_tests",
    "voivodeship_decision",
)

DRIVER_CE_EVIDENCE_FLOWS = (
    ("identity_document", "identity_any", "passport"),
    ("legal_stay_confirmation", "legal_stay_any", "karta_pobytu"),
    ("driver_license_with_code95", "combined_eu_license", "driver_license_code95"),
    ("tachograph_card", "tacho_any", "tacho_card"),
    ("medical_fitness", "medical_any", "medical_certificate"),
    ("psychological_tests", "psychological_any", "psychotest"),
    ("voivodeship_decision", "decision_any", "decision"),
)

RECRUITMENT_DOSSIER_CONFIRMED_BLOCKS = (
    "Contacts & address",
    "Passport / ID",
    "Legal stay",
    "Red paper",
    "Work permit",
    "Driver license",
    "Code95",
    "Tacho card",
    "Medical",
    "Psychological",
    "Work experience",
)


async def close_driver_ce_requirements(
    client: AsyncClient,
    headers: dict[str, str],
    *,
    candidate_id: str,
    include_dossier_confirmations: bool = True,
) -> None:
    """Approve all driver_ce evidence slots and patch data fields for workspace closure."""
    extra: dict[str, Any] = {
        "citizenship": "UA",
        "experience_eu_years": "5",
        "address": "Warsaw, Test Street 1",
    }
    if include_dossier_confirmations:
        extra["recruitment_dossier_confirmed_blocks"] = list(RECRUITMENT_DOSSIER_CONFIRMED_BLOCKS)

    patch_resp = await client.patch(
        f"/api/v1/candidates/{candidate_id}",
        headers=headers,
        json={
            "phone": "+48123456789",
            "extra": extra,
            "personal_data": {
                "address": "Warsaw, Test Street 1",
                "citizenship": "UA",
            },
        },
    )
    assert patch_resp.status_code == 200, patch_resp.text

    for requirement_code, variant_code, doc_type in DRIVER_CE_EVIDENCE_FLOWS:
        doc_id = await post_document(client, headers, candidate_id=candidate_id, doc_type=doc_type)
        evidence = await select_evidence(
            client,
            headers,
            candidate_id=candidate_id,
            requirement_code=requirement_code,
            evidence_variant_code=variant_code,
        )
        await link_evidence_document(
            client,
            headers,
            candidate_id=candidate_id,
            evidence_id=evidence["evidence_id"],
            document_id=doc_id,
        )
        await approve_evidence_api(
            client,
            headers,
            candidate_id=candidate_id,
            evidence_id=evidence["evidence_id"],
        )


async def ensure_tenant_link_internal_hr(
    client: AsyncClient,
    *,
    manager_headers: dict[str, str],
    tenant_id: str,
    company_id: str,
) -> None:
    lst = await client.get(
        f"/api/v1/tenants/{tenant_id}/links",
        headers=manager_headers,
    )
    assert lst.status_code == 200, lst.text
    for row in lst.json():
        if str(row.get("client_company_id") or "") == str(company_id):
            link_id = row["id"]
            patch = await client.patch(
                f"/api/v1/tenants/{tenant_id}/links/{link_id}",
                headers=manager_headers,
                json={
                    "handoff_enabled": True,
                    "handoff_to_client": True,
                    "handoff_to_internal_hr": True,
                },
            )
            assert patch.status_code == 200, patch.text
            return
    create = await client.post(
        f"/api/v1/tenants/{tenant_id}/links",
        headers=manager_headers,
        json={
            "client_company_id": company_id,
            "handoff_enabled": True,
            "handoff_to_client": True,
            "handoff_to_internal_hr": True,
        },
    )
    assert create.status_code == 201, create.text
