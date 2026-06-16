from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select

from backend.app.db.session import async_session_maker
from backend.app.models import Candidate, Document, DocumentType, RefDocumentType, RefDocumentTypeVersion, Tenant
from backend.app.models.document_policy import DocumentPolicy, DocumentPolicyScope
from backend.app.models.enums import DocumentKind, DocumentProcessType, DocumentRequestedFrom, DocumentStatus
from backend.app.services.document_reference_sync import seed_and_sync_document_references


pytestmark = pytest.mark.anyio


async def _seed_once() -> None:
    async with async_session_maker() as session:
        await seed_and_sync_document_references(session)
        await session.commit()


async def test_seed_creates_canonical_types_and_is_idempotent() -> None:
    await _seed_once()
    await _seed_once()

    required_codes = {
        "passport",
        "id_card",
        "residence_card",
        "visa",
        "work_permit",
        "driver_license",
        "code_95",
        "tachograph_card",
        "medical_certificate",
        "psychotest",
        "employment_contract",
        "civil_contract",
        "zus_zua",
        "zus_zza",
        "tax_declaration",
        "other",
    }

    async with async_session_maker() as session:
        rows = (await session.execute(select(RefDocumentType.code, RefDocumentType.origin))).all()
        by_code = {str(code): str(origin) for code, origin in rows}
        assert required_codes.issubset(set(by_code.keys()))
        for code in required_codes:
            assert by_code[code] == "system"

        ver_rows = (
            await session.execute(
                select(RefDocumentTypeVersion.document_type_id, RefDocumentTypeVersion.version_code)
                .where(RefDocumentTypeVersion.version_code == "v1")
            )
        ).all()
        # exactly one v1 per canonical required type
        assert len({doc_id for doc_id, _ in ver_rows}) >= len(required_codes)


async def test_backfill_documents_sets_canonical_ids_and_unknown_maps_to_other() -> None:
    tenant_id = str(uuid.uuid4())
    candidate_id = str(uuid.uuid4())

    async with async_session_maker() as session:
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
                first_name="Doc",
                last_name="Candidate",
            )
        )
        session.add_all(
            [
                Document(
                    tenant_id=tenant_id,
                    candidate_id=candidate_id,
                    kind=DocumentKind.driver,
                    doc_type="passport",
                    status=DocumentStatus.missing,
                    requested_from=DocumentRequestedFrom.driver,
                    process_type=DocumentProcessType.none,
                ),
                Document(
                    tenant_id=tenant_id,
                    candidate_id=candidate_id,
                    kind=DocumentKind.driver,
                    doc_type="legacy_unknown_type",
                    status=DocumentStatus.missing,
                    requested_from=DocumentRequestedFrom.driver,
                    process_type=DocumentProcessType.none,
                ),
            ]
        )
        await session.commit()

        await seed_and_sync_document_references(session)
        await session.commit()

        docs = (await session.execute(select(Document).where(Document.tenant_id == tenant_id))).scalars().all()
        assert len(docs) == 2
        assert all(d.document_type_id for d in docs)
        assert all(d.document_type_version_id for d in docs)

        ref_rows = (await session.execute(select(RefDocumentType.id, RefDocumentType.code))).all()
        ref_by_id = {rid: code for rid, code in ref_rows}
        by_legacy = {d.doc_type: ref_by_id.get(d.document_type_id) for d in docs}
        assert by_legacy["passport"] == "passport"
        assert by_legacy["legacy_unknown_type"] == "other"


async def test_backfill_document_policy_from_legacy_document_type() -> None:
    tenant_id = str(uuid.uuid4())

    async with async_session_maker() as session:
        session.add(
            Tenant(
                id=tenant_id,
                name=f"Tenant {tenant_id[:8]}",
                slug=f"tenant-{tenant_id[:8]}",
                api_key=f"api-{tenant_id[:8]}",
                is_active=True,
            )
        )
        legacy = DocumentType(tenant_id=tenant_id, code="visa_d", name="Visa D")
        session.add(legacy)
        await session.flush()

        policy = DocumentPolicy(
            tenant_id=tenant_id,
            scope=DocumentPolicyScope.TENANT,
            scope_id=None,
            document_type_id=legacy.id,
            gates=["pre_handoff"],
            enabled=True,
        )
        session.add(policy)
        await session.commit()

        await seed_and_sync_document_references(session)
        await session.commit()

        refreshed = await session.get(DocumentPolicy, policy.id)
        assert refreshed is not None
        await session.refresh(refreshed)
        assert refreshed.ref_document_type_id is not None

        ref = await session.get(RefDocumentType, refreshed.ref_document_type_id)
        assert ref is not None
        assert ref.code == "visa"


async def test_tenant_custom_duplicate_system_code_blocked() -> None:
    await _seed_once()

    async with async_session_maker() as session:
        session.add(
            RefDocumentType(
                code="passport",
                public_name="Tenant Passport",
                status="active",
                origin="tenant_custom",
                category_code="identity",
                subcategory_code="passport",
                criticality="informational",
            )
        )
        with pytest.raises(Exception):
            await session.commit()
        await session.rollback()
