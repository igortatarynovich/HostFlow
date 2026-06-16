from __future__ import annotations

from datetime import date
import uuid

import pytest
from sqlalchemy import select

from backend.app.db.session import async_session_maker
from backend.app.models import Candidate, Document, RefDocumentType, RefDocumentTypeVersion, Tenant
from backend.app.models.enums import DocumentKind, DocumentProcessType, DocumentRequestedFrom, DocumentStatus
from backend.app.services.document_reference_sync import seed_and_sync_document_references
from backend.app.services.document_type_runtime_resolver import DocumentTypeRuntimeResolver

pytestmark = pytest.mark.anyio


async def _seed() -> None:
    async with async_session_maker() as session:
        await seed_and_sync_document_references(session)
        await session.commit()


async def _tenant_candidate(session, tenant_id: str, candidate_id: str) -> None:
    session.add(
        Tenant(
            id=tenant_id,
            name=f"Tenant {tenant_id[:8]}",
            slug=f"tenant-{tenant_id[:8]}",
            api_key=f"api-{tenant_id[:8]}",
            is_active=True,
        )
    )
    session.add(
        Candidate(
            id=candidate_id,
            tenant_id=tenant_id,
            first_name="Runtime",
            last_name="Resolver",
        )
    )


async def test_resolve_prefers_document_type_version_id() -> None:
    await _seed()
    tenant_id = str(uuid.uuid4())
    candidate_id = str(uuid.uuid4())

    async with async_session_maker() as session:
        await _tenant_candidate(session, tenant_id, candidate_id)
        passport_type = (
            await session.execute(select(RefDocumentType).where(RefDocumentType.code == "passport"))
        ).scalar_one()
        passport_ver = (
            await session.execute(
                select(RefDocumentTypeVersion)
                .where(RefDocumentTypeVersion.document_type_id == passport_type.id)
                .where(RefDocumentTypeVersion.version_code == "v1")
            )
        ).scalar_one()

        doc = Document(
            tenant_id=tenant_id,
            candidate_id=candidate_id,
            kind=DocumentKind.driver,
            doc_type="legacy_unknown",
            document_type_id=passport_type.id,
            document_type_version_id=passport_ver.id,
            status=DocumentStatus.missing,
            requested_from=DocumentRequestedFrom.driver,
            process_type=DocumentProcessType.none,
        )
        session.add(doc)
        await session.commit()

        resolved = await DocumentTypeRuntimeResolver.resolve_for_document(session, doc)
        assert resolved.canonical_code == "passport"
        assert resolved.document_type_version_id == passport_ver.id
        assert resolved.fallback_used is False


async def test_resolve_uses_document_type_id_latest_version_when_version_missing() -> None:
    await _seed()
    tenant_id = str(uuid.uuid4())
    candidate_id = str(uuid.uuid4())

    async with async_session_maker() as session:
        await _tenant_candidate(session, tenant_id, candidate_id)
        visa_type = (
            await session.execute(select(RefDocumentType).where(RefDocumentType.code == "visa"))
        ).scalar_one()

        # Create (or reuse) a newer version; resolver should pick latest by valid_from.
        v2 = (
            await session.execute(
                select(RefDocumentTypeVersion)
                .where(RefDocumentTypeVersion.document_type_id == visa_type.id)
                .where(RefDocumentTypeVersion.version_code == "v2")
            )
        ).scalar_one_or_none()
        if v2 is None:
            v2 = RefDocumentTypeVersion(
                document_type_id=visa_type.id,
                version_code="v2",
                valid_from=date(2027, 1, 1),
                schema_json={"required": ["number"]},
                expiry_rules_json={"has_expiry": True},
                automation_flags_json={},
                verification_profile_json={"manual_review_required": True},
                stage_applicability_json={},
                position_applicability_json={},
                entity_applicability_json={},
                business_purposes_json={"purposes": ["legal_stay"]},
                status_model="evidence",
            )
            session.add(v2)
            await session.flush()

        doc = Document(
            tenant_id=tenant_id,
            candidate_id=candidate_id,
            kind=DocumentKind.driver,
            doc_type="visa_d",
            document_type_id=visa_type.id,
            status=DocumentStatus.missing,
            requested_from=DocumentRequestedFrom.driver,
            process_type=DocumentProcessType.none,
        )
        session.add(doc)
        await session.commit()

        resolved = await DocumentTypeRuntimeResolver.resolve_for_document(session, doc)
        assert resolved.canonical_code == "visa"
        assert resolved.fallback_used is False


async def test_resolve_legacy_mapping_and_unknown_to_other() -> None:
    await _seed()
    tenant_id = str(uuid.uuid4())
    candidate_id = str(uuid.uuid4())

    async with async_session_maker() as session:
        await _tenant_candidate(session, tenant_id, candidate_id)

        known = Document(
            tenant_id=tenant_id,
            candidate_id=candidate_id,
            kind=DocumentKind.driver,
            doc_type="visa_d",
            status=DocumentStatus.missing,
            requested_from=DocumentRequestedFrom.driver,
            process_type=DocumentProcessType.none,
        )
        unknown = Document(
            tenant_id=tenant_id,
            candidate_id=candidate_id,
            kind=DocumentKind.driver,
            doc_type="totally_unknown_legacy",
            status=DocumentStatus.missing,
            requested_from=DocumentRequestedFrom.driver,
            process_type=DocumentProcessType.none,
        )
        session.add_all([known, unknown])
        await session.commit()

        r_known = await DocumentTypeRuntimeResolver.resolve_for_document(session, known)
        r_unknown = await DocumentTypeRuntimeResolver.resolve_for_document(session, unknown)

        assert r_known.canonical_code == "visa"
        assert r_known.fallback_used is True
        assert r_known.fallback_source == "legacy_doc_type"

        assert r_unknown.canonical_code == "other"
        assert r_unknown.fallback_used is True


async def test_missing_version_does_not_break_runtime() -> None:
    await _seed()
    tenant_id = str(uuid.uuid4())
    candidate_id = str(uuid.uuid4())

    async with async_session_maker() as session:
        await _tenant_candidate(session, tenant_id, candidate_id)
        t = RefDocumentType(
            code=f"tenant_custom_{uuid.uuid4().hex[:8]}",
            public_name="Tenant Custom",
            status="active",
            origin="tenant_custom",
            category_code="other",
            subcategory_code=None,
            criticality="informational",
        )
        session.add(t)
        await session.flush()

        doc = Document(
            tenant_id=tenant_id,
            candidate_id=candidate_id,
            kind=DocumentKind.driver,
            doc_type="tenant_custom",
            document_type_id=t.id,
            status=DocumentStatus.missing,
            requested_from=DocumentRequestedFrom.driver,
            process_type=DocumentProcessType.none,
        )
        session.add(doc)
        await session.commit()

        resolved = await DocumentTypeRuntimeResolver.resolve_for_document(session, doc)
        assert resolved.canonical_document_type_id == t.id
        assert resolved.document_type_version_id is None
        assert resolved.fallback_used is True
        assert resolved.fallback_source == "document_type_no_version"
