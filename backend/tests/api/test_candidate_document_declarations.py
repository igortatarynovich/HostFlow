"""ADR-043 Step 8 — candidate document declaration state."""

from __future__ import annotations

from datetime import date
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select

from backend.app.entity_profile.publication_versions import publish_entity_profile
from backend.app.models.candidate_evidence import CandidateEvidence
from backend.app.models.document import Document
from backend.app.models.entity_profile import EpEntityProfile
from backend.app.models.enums import DocumentStatus
from backend.app.models.recruitment_candidate_document_declaration import (
    RecruitmentCandidateDocumentDeclaration,
)
from backend.app.models.ref_document_type import (
    RefDocumentType,
    RefDocumentTypeVersion,
)

pytestmark = pytest.mark.anyio


async def _make_document_version(
    db,
    *,
    suffix: str,
) -> RefDocumentTypeVersion:
    document_type = RefDocumentType(
        id=str(uuid.uuid4()),
        code=f"step8_{suffix}_{uuid.uuid4().hex[:8]}",
        public_name=f"Step 8 {suffix}",
        status="active",
        origin="system",
        category_code="identity",
        criticality="informational",
    )
    db.add(document_type)
    await db.flush()

    version = RefDocumentTypeVersion(
        id=str(uuid.uuid4()),
        document_type_id=document_type.id,
        version_code="v1",
        valid_from=date(2026, 1, 1),
        schema_json={},
        expiry_rules_json={},
        automation_flags_json={},
        verification_profile_json={},
        stage_applicability_json={},
        position_applicability_json={},
        entity_applicability_json={},
        business_purposes_json={},
        status_model="evidence",
    )
    db.add(version)
    await db.flush()
    return version


async def _make_recruitment_profile_version(
    db,
    *,
    tenant_id: str,
    document_version: RefDocumentTypeVersion,
):
    profile = EpEntityProfile(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        profile_code=f"step8.profile.{uuid.uuid4().hex[:8]}",
        registry_version="entity_profile_v1",
        status="active",
        name="Step 8 declaration profile",
        entity_type="candidate",
        module_owner="recruitment",
        version=1,
        config={},
    )
    db.add(profile)
    await db.flush()

    return await publish_entity_profile(
        db,
        tenant_id=tenant_id,
        entity_profile_id=profile.id,
        field_bindings=[],
        document_bindings=[
            {
                "document_type_version_id": document_version.id,
                "requirement_level": "required",
                "sort_order": 10,
            }
        ],
    )


def _url(
    *,
    candidate_id: str,
    profile_version_id: str,
    document_type_version_id: str,
) -> str:
    return (
        f"/api/v1/candidates/{candidate_id}/requirements"
        f"/profile-versions/{profile_version_id}"
        f"/documents/{document_type_version_id}/declaration"
    )


async def _evidence_count(db, *, tenant_id: str, candidate_id: str) -> int:
    return int(
        (
            await db.execute(
                select(func.count(CandidateEvidence.id)).where(
                    CandidateEvidence.tenant_id == tenant_id,
                    CandidateEvidence.candidate_id == candidate_id,
                )
            )
        ).scalar_one()
    )


@pytest.mark.parametrize(
    "state",
    [
        "unknown",
        "does_not_have",
        "has_document",
        "upload_requested",
    ],
)
async def test_declaration_states_persist_without_creating_evidence(
    client: AsyncClient,
    manager_headers: dict[str, str],
    db,
    tenant_id: str,
    candidate_id: str,
    state: str,
) -> None:
    document_version = await _make_document_version(db, suffix=state)
    profile_version = await _make_recruitment_profile_version(
        db,
        tenant_id=tenant_id,
        document_version=document_version,
    )
    await db.commit()

    url = _url(
        candidate_id=candidate_id,
        profile_version_id=profile_version.id,
        document_type_version_id=document_version.id,
    )

    before = await _evidence_count(
        db,
        tenant_id=tenant_id,
        candidate_id=candidate_id,
    )

    response = await client.put(
        url,
        headers=manager_headers,
        json={"state": state},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["candidate_id"] == candidate_id
    assert body["entity_profile_version_id"] == profile_version.id
    assert body["document_type_version_id"] == document_version.id
    assert body["state"] == state
    assert body["updated_by"]
    assert body["created_at"]
    assert body["updated_at"]

    read_response = await client.get(url, headers=manager_headers)
    assert read_response.status_code == 200, read_response.text
    assert read_response.json()["state"] == state

    after = await _evidence_count(
        db,
        tenant_id=tenant_id,
        candidate_id=candidate_id,
    )
    assert after == before


async def test_missing_declaration_reads_as_unknown_without_persisting_row(
    client: AsyncClient,
    manager_headers: dict[str, str],
    db,
    tenant_id: str,
    candidate_id: str,
) -> None:
    document_version = await _make_document_version(db, suffix="default")
    profile_version = await _make_recruitment_profile_version(
        db,
        tenant_id=tenant_id,
        document_version=document_version,
    )
    await db.commit()

    url = _url(
        candidate_id=candidate_id,
        profile_version_id=profile_version.id,
        document_type_version_id=document_version.id,
    )

    response = await client.get(url, headers=manager_headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["state"] == "unknown"
    assert body["updated_by"] is None
    assert body["created_at"] is None
    assert body["updated_at"] is None

    row = (
        await db.execute(
            select(RecruitmentCandidateDocumentDeclaration).where(
                RecruitmentCandidateDocumentDeclaration.tenant_id == tenant_id,
                RecruitmentCandidateDocumentDeclaration.candidate_id == candidate_id,
                RecruitmentCandidateDocumentDeclaration.entity_profile_version_id
                == profile_version.id,
                RecruitmentCandidateDocumentDeclaration.document_type_version_id
                == document_version.id,
            )
        )
    ).scalar_one_or_none()
    assert row is None


async def test_explicit_unknown_is_persisted(
    client: AsyncClient,
    manager_headers: dict[str, str],
    db,
    tenant_id: str,
    candidate_id: str,
) -> None:
    document_version = await _make_document_version(db, suffix="explicit_unknown")
    profile_version = await _make_recruitment_profile_version(
        db,
        tenant_id=tenant_id,
        document_version=document_version,
    )
    await db.commit()

    url = _url(
        candidate_id=candidate_id,
        profile_version_id=profile_version.id,
        document_type_version_id=document_version.id,
    )
    response = await client.put(
        url,
        headers=manager_headers,
        json={"state": "unknown"},
    )
    assert response.status_code == 200, response.text

    row = (
        await db.execute(
            select(RecruitmentCandidateDocumentDeclaration).where(
                RecruitmentCandidateDocumentDeclaration.tenant_id == tenant_id,
                RecruitmentCandidateDocumentDeclaration.candidate_id == candidate_id,
                RecruitmentCandidateDocumentDeclaration.entity_profile_version_id
                == profile_version.id,
                RecruitmentCandidateDocumentDeclaration.document_type_version_id
                == document_version.id,
            )
        )
    ).scalar_one_or_none()
    assert row is not None
    assert row.state == "unknown"


async def test_invalid_declaration_state_is_rejected(
    client: AsyncClient,
    manager_headers: dict[str, str],
    db,
    tenant_id: str,
    candidate_id: str,
) -> None:
    document_version = await _make_document_version(db, suffix="invalid")
    profile_version = await _make_recruitment_profile_version(
        db,
        tenant_id=tenant_id,
        document_version=document_version,
    )
    await db.commit()

    response = await client.put(
        _url(
            candidate_id=candidate_id,
            profile_version_id=profile_version.id,
            document_type_version_id=document_version.id,
        ),
        headers=manager_headers,
        json={"state": "approved"},
    )
    assert response.status_code == 422, response.text


async def test_document_must_belong_to_exact_profile_version(
    client: AsyncClient,
    manager_headers: dict[str, str],
    db,
    tenant_id: str,
    candidate_id: str,
) -> None:
    bound_document = await _make_document_version(db, suffix="bound")
    unrelated_document = await _make_document_version(db, suffix="unrelated")
    profile_version = await _make_recruitment_profile_version(
        db,
        tenant_id=tenant_id,
        document_version=bound_document,
    )
    await db.commit()

    response = await client.put(
        _url(
            candidate_id=candidate_id,
            profile_version_id=profile_version.id,
            document_type_version_id=unrelated_document.id,
        ),
        headers=manager_headers,
        json={"state": "has_document"},
    )
    assert response.status_code == 404, response.text


async def test_repeated_put_updates_same_declaration_instance(
    client: AsyncClient,
    manager_headers: dict[str, str],
    db,
    tenant_id: str,
    candidate_id: str,
) -> None:
    document_version = await _make_document_version(db, suffix="idempotent")
    profile_version = await _make_recruitment_profile_version(
        db,
        tenant_id=tenant_id,
        document_version=document_version,
    )
    await db.commit()

    url = _url(
        candidate_id=candidate_id,
        profile_version_id=profile_version.id,
        document_type_version_id=document_version.id,
    )

    first = await client.put(
        url,
        headers=manager_headers,
        json={"state": "does_not_have"},
    )
    assert first.status_code == 200, first.text

    second = await client.put(
        url,
        headers=manager_headers,
        json={"state": "has_document"},
    )
    assert second.status_code == 200, second.text
    assert second.json()["state"] == "has_document"

    rows = (
        await db.execute(
            select(RecruitmentCandidateDocumentDeclaration).where(
                RecruitmentCandidateDocumentDeclaration.tenant_id == tenant_id,
                RecruitmentCandidateDocumentDeclaration.candidate_id == candidate_id,
                RecruitmentCandidateDocumentDeclaration.entity_profile_version_id
                == profile_version.id,
                RecruitmentCandidateDocumentDeclaration.document_type_version_id
                == document_version.id,
            )
        )
    ).scalars().all()

    assert len(rows) == 1
    assert rows[0].state == "has_document"



async def test_upload_requested_materializes_canonical_document_slot(
    client: AsyncClient,
    manager_headers: dict[str, str],
    db,
    tenant_id: str,
    candidate_id: str,
) -> None:
    document_version = await _make_document_version(db, suffix="upload_slot")
    document_type = await db.get(RefDocumentType, document_version.document_type_id)
    assert document_type is not None

    profile_version = await _make_recruitment_profile_version(
        db,
        tenant_id=tenant_id,
        document_version=document_version,
    )
    await db.commit()

    before_evidence = await _evidence_count(
        db,
        tenant_id=tenant_id,
        candidate_id=candidate_id,
    )

    response = await client.put(
        _url(
            candidate_id=candidate_id,
            profile_version_id=profile_version.id,
            document_type_version_id=document_version.id,
        ),
        headers=manager_headers,
        json={"state": "upload_requested"},
    )
    assert response.status_code == 200, response.text

    body = response.json()
    assert body["state"] == "upload_requested"
    assert body["upload_document_id"]

    document = await db.get(Document, body["upload_document_id"])
    assert document is not None
    assert document.tenant_id == tenant_id
    assert document.candidate_id == candidate_id
    assert document.status == DocumentStatus.requested
    assert document.doc_type == document_type.code
    assert document.document_type_id == document_type.id
    assert document.document_type_version_id == document_version.id
    assert document.files == []
    assert document.meta["request_kind"] == "profile_declaration"
    assert document.meta["entity_profile_version_id"] == profile_version.id
    assert document.meta["document_type_version_id"] == document_version.id

    after_evidence = await _evidence_count(
        db,
        tenant_id=tenant_id,
        candidate_id=candidate_id,
    )
    assert after_evidence == before_evidence


async def test_repeated_upload_requested_reuses_same_document_slot(
    client: AsyncClient,
    manager_headers: dict[str, str],
    db,
    tenant_id: str,
    candidate_id: str,
) -> None:
    document_version = await _make_document_version(db, suffix="slot_idempotent")
    profile_version = await _make_recruitment_profile_version(
        db,
        tenant_id=tenant_id,
        document_version=document_version,
    )
    await db.commit()

    url = _url(
        candidate_id=candidate_id,
        profile_version_id=profile_version.id,
        document_type_version_id=document_version.id,
    )

    first = await client.put(
        url,
        headers=manager_headers,
        json={"state": "upload_requested"},
    )
    assert first.status_code == 200, first.text
    first_document_id = first.json()["upload_document_id"]
    assert first_document_id

    second = await client.put(
        url,
        headers=manager_headers,
        json={"state": "upload_requested"},
    )
    assert second.status_code == 200, second.text
    assert second.json()["upload_document_id"] == first_document_id

    documents = (
        await db.execute(
            select(Document).where(
                Document.tenant_id == tenant_id,
                Document.candidate_id == candidate_id,
                Document.document_type_version_id == document_version.id,
                Document.deleted_at.is_(None),
            )
        )
    ).scalars().all()

    profile_slots = [
        document
        for document in documents
        if isinstance(document.meta, dict)
        and document.meta.get("request_kind") == "profile_declaration"
        and document.meta.get("entity_profile_version_id") == profile_version.id
    ]
    assert len(profile_slots) == 1
    assert profile_slots[0].id == first_document_id


async def test_declaration_change_does_not_delete_or_satisfy_upload_slot(
    client: AsyncClient,
    manager_headers: dict[str, str],
    db,
    tenant_id: str,
    candidate_id: str,
) -> None:
    document_version = await _make_document_version(db, suffix="slot_lifecycle")
    profile_version = await _make_recruitment_profile_version(
        db,
        tenant_id=tenant_id,
        document_version=document_version,
    )
    await db.commit()

    url = _url(
        candidate_id=candidate_id,
        profile_version_id=profile_version.id,
        document_type_version_id=document_version.id,
    )

    requested = await client.put(
        url,
        headers=manager_headers,
        json={"state": "upload_requested"},
    )
    assert requested.status_code == 200, requested.text
    document_id = requested.json()["upload_document_id"]
    assert document_id

    evidence_before = await _evidence_count(
        db,
        tenant_id=tenant_id,
        candidate_id=candidate_id,
    )

    declared = await client.put(
        url,
        headers=manager_headers,
        json={"state": "has_document"},
    )
    assert declared.status_code == 200, declared.text
    assert declared.json()["state"] == "has_document"
    assert declared.json()["upload_document_id"] == document_id

    document = await db.get(Document, document_id)
    assert document is not None
    assert document.deleted_at is None
    assert document.status == DocumentStatus.requested

    evidence_after = await _evidence_count(
        db,
        tenant_id=tenant_id,
        candidate_id=candidate_id,
    )
    assert evidence_after == evidence_before
