from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select

from backend.app.db.session import async_session_maker
from backend.app.models import Candidate, Document, RefDocumentType, Tenant
from backend.app.models.enums import DocumentKind, DocumentProcessType, DocumentRequestedFrom, DocumentStatus
from backend.app.services.document_reference_sync import seed_and_sync_document_references
from backend.app.services.document_type_canonical_bridge import (
    build_legacy_to_ref_canonical_map,
    legacy_codes_for_ref_canonical,
    normalize_legacy_doc_type,
)

pytestmark = pytest.mark.anyio


def test_tacho_card_and_psych_tests_map_to_ref_canonical() -> None:
    assert normalize_legacy_doc_type("tacho_card") == "tachograph_card"
    assert normalize_legacy_doc_type("psych_tests") == "psychotest"
    assert normalize_legacy_doc_type("code95") == "code_95"
    assert normalize_legacy_doc_type("driver_license") == "driver_license"


def test_aliases_share_ref_canonical() -> None:
    tacho_aliases = legacy_codes_for_ref_canonical("tachograph_card")
    assert "tacho_card" in tacho_aliases
    assert "tachograph" in tacho_aliases

    psycho_aliases = legacy_codes_for_ref_canonical("psychotest")
    assert "psych_tests" in psycho_aliases
    assert "psycho_test" in psycho_aliases


def test_supplemental_and_ref_codes_in_map() -> None:
    mapping = build_legacy_to_ref_canonical_map()
    assert mapping["id"] == "id_card"
    assert mapping["contract"] == "employment_contract"
    assert mapping["passport"] == "passport"


async def test_sync_reassigns_misclassified_document_type_ids() -> None:
    async with async_session_maker() as session:
        await seed_and_sync_document_references(session)
        await session.commit()

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
                first_name="Bridge",
                last_name="Sync",
            )
        )
        other_type = (
            await session.execute(select(RefDocumentType).where(RefDocumentType.code == "other"))
        ).scalar_one()
        tacho_doc = Document(
            tenant_id=tenant_id,
            candidate_id=candidate_id,
            kind=DocumentKind.driver,
            doc_type="tacho_card",
            document_type_id=other_type.id,
            status=DocumentStatus.approved,
            requested_from=DocumentRequestedFrom.driver,
            process_type=DocumentProcessType.tachograph_card,
        )
        session.add(tacho_doc)
        await session.commit()
        doc_id = tacho_doc.id

    async with async_session_maker() as session:
        await seed_and_sync_document_references(session)
        await session.commit()

    async with async_session_maker() as session:
        tacho_type = (
            await session.execute(select(RefDocumentType).where(RefDocumentType.code == "tachograph_card"))
        ).scalar_one()
        doc = await session.get(Document, doc_id)
        assert doc is not None
        assert doc.document_type_id == tacho_type.id
