from __future__ import annotations

import json
import uuid
from datetime import date, timedelta

import pytest
from sqlalchemy import select

from backend.app.db.session import async_session_maker
from backend.app.models import ActivityLog, Candidate, Document, RefPack, Tenant, TenantDocumentPackEnablement
from backend.app.models.user import Role, User
from backend.app.models.enums import DocumentKind, DocumentProcessType, DocumentRequestedFrom, DocumentStatus
from backend.app.services.document_reference_sync import seed_and_sync_document_references
from backend.app.services.workforce_action_policy import WorkforceActionBlockedError, assert_operation_allowed

pytestmark = pytest.mark.anyio


async def _seed() -> None:
    async with async_session_maker() as session:
        await seed_and_sync_document_references(session)
        await session.commit()


async def _enable_pack(session, tenant_id: str, code: str) -> None:
    pack = (await session.execute(select(RefPack).where(RefPack.code == code))).scalar_one()
    session.add(TenantDocumentPackEnablement(tenant_id=tenant_id, pack_id=pack.id, enabled=True))


async def test_action_audit_written_for_blocked_and_allowed_attempts() -> None:
    await _seed()
    tenant_id = str(uuid.uuid4())
    candidate_id = str(uuid.uuid4())
    actor_id = str(uuid.uuid4())

    async with async_session_maker() as session:
        session.add(
            Tenant(
                id=tenant_id,
                name=f"Tenant {tenant_id[:8]}",
                slug=f"t-{tenant_id[:8]}",
                api_key=f"api-{tenant_id[:8]}",
                is_active=True,
            )
        )
        session.add(
            User(
                id=actor_id,
                tenant_id=tenant_id,
                email=f"actor-{actor_id[:8]}@example.com",
                password_hash="x",
                role=Role.hr_officer,
                is_active=True,
            )
        )
        cand = Candidate(
            id=candidate_id,
            tenant_id=tenant_id,
            first_name="A",
            last_name="B",
            extra=json.dumps({"citizenship": "UA", "work_country": "PL", "position_category": "driver"}),
        )
        session.add(cand)
        await _enable_pack(session, tenant_id, "pl_non_eu_worker")
        await _enable_pack(session, tenant_id, "pl_transport_driver")
        await session.commit()

        with pytest.raises(WorkforceActionBlockedError):
            await assert_operation_allowed(
                session,
                tenant_id=tenant_id,
                operation="contract_signing",
                actor_id=actor_id,
                candidate=cand,
                stage="hr",
            )

        for code in ["work_permit", "residence_card", "visa", "driver_license", "code_95", "tachograph_card", "medical_certificate", "psychotest"]:
            session.add(
                Document(
                    tenant_id=tenant_id,
                    candidate_id=candidate_id,
                    kind=DocumentKind.driver,
                    doc_type=code,
                    expire_date=date.today() + timedelta(days=120),
                    status=DocumentStatus.approved,
                    requested_from=DocumentRequestedFrom.driver,
                    process_type=DocumentProcessType.none,
                )
            )
        await session.flush()

        await assert_operation_allowed(
            session,
            tenant_id=tenant_id,
            operation="contract_signing",
            actor_id=actor_id,
            candidate=cand,
            stage="hr",
        )
        await session.commit()

        rows = (
            await session.execute(
                select(ActivityLog)
                .where(ActivityLog.tenant_id == tenant_id)
                .where(ActivityLog.action == "workforce.action.decision_event")
                .order_by(ActivityLog.created_at.asc())
            )
        ).scalars().all()

        assert len(rows) >= 2
        assert rows[-2].payload.get("result") == "blocked"
        assert rows[-2].payload.get("operation") == "contract_signing"
        assert rows[-2].payload.get("eligibility_status") in {"pending_documents", "blocked"}
        assert rows[-1].payload.get("result") == "allowed"
        assert rows[-1].payload.get("operation") == "contract_signing"
