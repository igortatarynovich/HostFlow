from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select

from backend.app.db.session import async_session_maker
from backend.app.models import Candidate, CandidateHandoff, Document, Tenant
from backend.app.models.enums import DocumentKind, DocumentProcessType, DocumentRequestedFrom, DocumentStatus
from backend.app.services.document_reference_sync import seed_and_sync_document_references
from backend.app.services.handoff_snapshot import build_handoff_snapshot_payload_v1

pytestmark = pytest.mark.anyio


async def test_handoff_snapshot_contains_canonical_runtime_metadata() -> None:
    async with async_session_maker() as session:
        await seed_and_sync_document_references(session)

        tenant_id = str(uuid.uuid4())
        candidate_id = str(uuid.uuid4())

        session.add(
            Tenant(
                id=tenant_id,
                name=f"Tenant {tenant_id[:8]}",
                slug=f"tenant-{tenant_id[:8]}",
                api_key=f"api-{tenant_id[:8]}",
                is_active=True,
            )
        )
        candidate = Candidate(
            id=candidate_id,
            tenant_id=tenant_id,
            first_name="Snap",
            last_name="Shot",
        )
        session.add(candidate)
        await session.flush()

        session.add(
            Document(
                tenant_id=tenant_id,
                candidate_id=candidate_id,
                kind=DocumentKind.driver,
                doc_type="legacy_unknown_type",
                status=DocumentStatus.missing,
                requested_from=DocumentRequestedFrom.driver,
                process_type=DocumentProcessType.none,
            )
        )

        handoff = CandidateHandoff(
            id=str(uuid.uuid4()),
            agency_tenant_id=tenant_id,
            client_tenant_id=str(uuid.uuid4()),
            candidate_id=candidate_id,
            handoff_type="candidate_handoff",
            destination="hr",
            requested_by_user_id=str(uuid.uuid4()),
            status="pending",
        )
        await session.commit()

        payload = await build_handoff_snapshot_payload_v1(
            session,
            handoff=handoff,
            candidate=candidate,
        )

        assert isinstance(payload.get("documents"), list)
        assert payload["documents"], "Expected at least one document in snapshot"
        first = payload["documents"][0]
        assert "canonical" in first
        assert first["canonical"]["code"] == "other"
        assert first["canonical"]["fallback_used"] is True
        assert "criticality" in first["canonical"]
        assert "expected_documents" in payload
        assert isinstance(payload["expected_documents"], list)
        assert "requirement_fulfillments" in payload
        assert isinstance(payload["requirement_fulfillments"], list)


async def test_handoff_snapshot_expected_documents_contract_fields() -> None:
    async with async_session_maker() as session:
        await seed_and_sync_document_references(session)

        tenant_id = str(uuid.uuid4())
        candidate_id = str(uuid.uuid4())

        session.add(
            Tenant(
                id=tenant_id,
                name=f"Tenant {tenant_id[:8]}",
                slug=f"tenant-{tenant_id[:8]}",
                api_key=f"api-{tenant_id[:8]}",
                is_active=True,
            )
        )
        candidate = Candidate(
            id=candidate_id,
            tenant_id=tenant_id,
            first_name="Prep",
            last_name="Contract",
        )
        handoff = CandidateHandoff(
            id=str(uuid.uuid4()),
            agency_tenant_id=tenant_id,
            client_tenant_id=str(uuid.uuid4()),
            candidate_id=candidate_id,
            handoff_type="candidate_handoff",
            destination="hr",
            requested_by_user_id=str(uuid.uuid4()),
            status="pending",
        )
        session.add(candidate)
        await session.commit()

        mocked_expected = [
            {
                "document_code": "passport",
                "required": True,
                "reason": "Required by Poland Base HR",
                "source_pack": "pl_base_hr",
                "criticality": "required",
                "due_point": "before_client_submission",
                "status": "missing",
            }
        ]
        with patch(
            "backend.app.services.handoff_snapshot.ReferenceServiceFacade.get_applicable_documents",
            AsyncMock(return_value=mocked_expected),
        ):
            payload = await build_handoff_snapshot_payload_v1(
                session,
                handoff=handoff,
                candidate=candidate,
            )

        expected = payload.get("expected_documents") or []
        assert expected
        row = expected[0]
        assert row["document_code"] == "passport"
        assert row["required"] is True
        assert row["reason"]
        assert row["source_pack"]
        assert row["criticality"]
        assert row["due_point"]
        assert row["status"] == "missing"
