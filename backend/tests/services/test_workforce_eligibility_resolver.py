from __future__ import annotations

from datetime import date, timedelta
import json
import uuid

import pytest
from sqlalchemy import select

from backend.app.db.session import async_session_maker
from backend.app.models import (
    Candidate,
    Document,
    RefPack,
    Tenant,
    TenantDocumentPackEnablement,
    WorkforceEmployee,
)
from backend.app.models.enums import DocumentKind, DocumentProcessType, DocumentRequestedFrom, DocumentStatus
from backend.app.services.document_reference_sync import seed_and_sync_document_references
from backend.app.services.workforce_eligibility_resolver import WorkforceEligibilityContext, WorkforceEligibilityResolver

pytestmark = pytest.mark.anyio


async def _seed() -> None:
    async with async_session_maker() as session:
        await seed_and_sync_document_references(session)
        await session.commit()


async def _tenant_candidate_employee(session, tenant_id: str, candidate_id: str, employee_id: str) -> None:
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
            first_name="M5",
            last_name="Candidate",
            extra=json.dumps({"citizenship": "UA", "work_country": "PL", "position_category": "driver"}),
        )
    )
    session.add(
        WorkforceEmployee(
            id=employee_id,
            tenant_id=tenant_id,
            candidate_id=candidate_id,
            display_name="M5 Candidate",
            status="onboarding",
        )
    )


async def _enable_pack(session, tenant_id: str, code: str) -> None:
    pack = (await session.execute(select(RefPack).where(RefPack.code == code))).scalar_one()
    session.add(TenantDocumentPackEnablement(tenant_id=tenant_id, pack_id=pack.id, enabled=True))


async def test_blocked_when_required_docs_missing() -> None:
    await _seed()
    tenant_id = str(uuid.uuid4())
    candidate_id = str(uuid.uuid4())
    employee_id = str(uuid.uuid4())

    async with async_session_maker() as session:
        await _tenant_candidate_employee(session, tenant_id, candidate_id, employee_id)
        await _enable_pack(session, tenant_id, "pl_non_eu_worker")
        await _enable_pack(session, tenant_id, "pl_transport_driver")
        await session.commit()

        result = await WorkforceEligibilityResolver.resolve(
            session,
            context=WorkforceEligibilityContext(
                tenant_id=tenant_id,
                employee_id=employee_id,
                citizenship="UA",
                work_country="PL",
                position_category="driver",
                stage="hr",
            ),
        )

        assert result["eligibility_status"] in {"pending_documents", "blocked"}
        assert result["compliance_status"] == "blocked"
        assert result["subject_type"] == "employee"
        assert result["subject_id"] == employee_id
        assert result["allowed_operations"]["assign_route"] is False
        assert result["allowed_operations"]["route_assignment"] is False
        assert result["allowed_operations"]["submit_to_client"] is False
        assert "work_permit" in result["missing_documents"]
        assert "upload_document" in result["next_required_actions"]
        assert "calculated_at" in result
        assert result["source_context"]["tenant_id"] == tenant_id
        assert "hr_ready" in result["readiness_profiles"]
        assert isinstance(result["readiness_profiles"]["hr_ready"], dict)
        assert all(
            str(b.get("severity") or "") in {"critical", "high", "medium", "low", "info"}
            for b in (result.get("blocking_reasons") or [])
        )
        assert all(
            b.get("domain") in {
                "legal_stay",
                "right_to_work",
                "identity",
                "driver_compliance",
                "medical",
                "hr_onboarding",
                "payroll",
                "client_specific",
                "operational",
            }
            for b in (result.get("blocking_reasons") or [])
        )
        assert all(
            str(b.get("impact") or "")
            in {
                "legal_blocker",
                "dispatch_blocker",
                "onboarding_delay",
                "compliance_risk",
                "payroll_risk",
                "document_missing",
                "verification_pending",
            }
            for b in (result.get("blocking_reasons") or [])
        )
        assert all(
            all(op in {
                "submit_to_client",
                "handoff_to_hr",
                "approve_hr_verification",
                "sign_contract",
                "activate_employee",
                "assign_route",
                "start_work",
                "payroll_ready",
            } for op in (b.get("affected_operations") or []))
            for b in (result.get("blocking_reasons") or [])
        )
        assert all(
            str(b.get("resolution_action") or "") in {"upload_document", "renew_document"}
            for b in (result.get("blocking_reasons") or [])
        )


async def test_eligible_when_required_docs_present_and_valid() -> None:
    await _seed()
    tenant_id = str(uuid.uuid4())
    candidate_id = str(uuid.uuid4())
    employee_id = str(uuid.uuid4())

    async with async_session_maker() as session:
        await _tenant_candidate_employee(session, tenant_id, candidate_id, employee_id)
        await _enable_pack(session, tenant_id, "pl_non_eu_worker")
        await _enable_pack(session, tenant_id, "pl_transport_driver")

        for code in [
            "work_permit",
            "residence_card",
            "visa",
            "driver_license",
            "code_95",
            "tachograph_card",
            "medical_certificate",
            "psychotest",
        ]:
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
        await session.commit()

        result = await WorkforceEligibilityResolver.resolve(
            session,
            context=WorkforceEligibilityContext(
                tenant_id=tenant_id,
                employee_id=employee_id,
                citizenship="UA",
                work_country="PL",
                position_category="driver",
                stage="hr",
            ),
        )

        assert result["eligibility_status"] == "eligible"
        assert result["compliance_status"] == "compliant"
        assert all(result["allowed_operations"][k] for k in result["allowed_operations"])


async def test_expired_critical_document_blocks_route_assignment() -> None:
    await _seed()
    tenant_id = str(uuid.uuid4())
    candidate_id = str(uuid.uuid4())
    employee_id = str(uuid.uuid4())

    async with async_session_maker() as session:
        await _tenant_candidate_employee(session, tenant_id, candidate_id, employee_id)
        await _enable_pack(session, tenant_id, "pl_transport_driver")

        session.add(
            Document(
                tenant_id=tenant_id,
                candidate_id=candidate_id,
                kind=DocumentKind.driver,
                doc_type="driver_license",
                expire_date=date.today() - timedelta(days=2),
                status=DocumentStatus.approved,
                requested_from=DocumentRequestedFrom.driver,
                process_type=DocumentProcessType.none,
            )
        )
        await session.commit()

        result = await WorkforceEligibilityResolver.resolve(
            session,
            context=WorkforceEligibilityContext(
                tenant_id=tenant_id,
                employee_id=employee_id,
                citizenship="PL",
                work_country="PL",
                position_category="driver",
                stage="hr",
            ),
        )

        assert result["eligibility_status"] in {"expired_critical_documents", "blocked"}
        assert "driver_license" in result["expired_documents"]
        assert result["allowed_operations"]["route_assignment"] is False


async def test_compliance_risk_when_doc_expires_soon() -> None:
    await _seed()
    tenant_id = str(uuid.uuid4())
    candidate_id = str(uuid.uuid4())
    employee_id = str(uuid.uuid4())

    async with async_session_maker() as session:
        await _tenant_candidate_employee(session, tenant_id, candidate_id, employee_id)
        await _enable_pack(session, tenant_id, "pl_non_eu_worker")
        await _enable_pack(session, tenant_id, "pl_transport_driver")

        for code in [
            "work_permit",
            "residence_card",
            "visa",
            "driver_license",
            "code_95",
            "tachograph_card",
            "medical_certificate",
            "psychotest",
        ]:
            session.add(
                Document(
                    tenant_id=tenant_id,
                    candidate_id=candidate_id,
                    kind=DocumentKind.driver,
                    doc_type=code,
                    expire_date=date.today() + timedelta(days=(5 if code == "work_permit" else 120)),
                        status=DocumentStatus.approved,
                    requested_from=DocumentRequestedFrom.driver,
                    process_type=DocumentProcessType.none,
                )
            )
        await session.commit()

        result = await WorkforceEligibilityResolver.resolve(
            session,
            context=WorkforceEligibilityContext(
                tenant_id=tenant_id,
                employee_id=employee_id,
                citizenship="UA",
                work_country="PL",
                position_category="driver",
                stage="hr",
            ),
        )

        assert result["eligibility_status"] == "compliance_risk"
        assert result["compliance_status"] == "partially_compliant"
        assert "work_permit_expires_in_7_days" in result["warnings"]


async def test_unverified_critical_doc_blocks_hr_verification() -> None:
    await _seed()
    tenant_id = str(uuid.uuid4())
    candidate_id = str(uuid.uuid4())
    employee_id = str(uuid.uuid4())

    async with async_session_maker() as session:
        await _tenant_candidate_employee(session, tenant_id, candidate_id, employee_id)
        await _enable_pack(session, tenant_id, "pl_non_eu_worker")

        session.add(
            Document(
                tenant_id=tenant_id,
                candidate_id=candidate_id,
                kind=DocumentKind.driver,
                doc_type="work_permit",
                expire_date=date.today() + timedelta(days=120),
                status=DocumentStatus.requested,
                requested_from=DocumentRequestedFrom.driver,
                process_type=DocumentProcessType.none,
            )
        )
        await session.commit()

        result = await WorkforceEligibilityResolver.resolve(
            session,
            context=WorkforceEligibilityContext(
                tenant_id=tenant_id,
                employee_id=employee_id,
                citizenship="UA",
                work_country="PL",
                position_category="driver",
                stage="hr",
            ),
        )

        assert "work_permit" in result["pending_verification_documents"]
        assert result["allowed_operations"]["approve_hr_verification"] is False
        blockers = [b for b in (result.get("blocking_reasons") or []) if b.get("document_code") == "work_permit"]
        assert blockers
        assert any(b.get("code") == "pending_document_verification" for b in blockers)
        assert all(str(b.get("resolution_action") or "") == "verify_document" for b in blockers)


async def test_candidate_subject_decision_contract_shape() -> None:
    await _seed()
    tenant_id = str(uuid.uuid4())
    candidate_id = str(uuid.uuid4())
    employee_id = str(uuid.uuid4())

    async with async_session_maker() as session:
        await _tenant_candidate_employee(session, tenant_id, candidate_id, employee_id)
        await _enable_pack(session, tenant_id, "pl_non_eu_worker")
        await session.commit()

        result = await WorkforceEligibilityResolver.resolve(
            session,
            context=WorkforceEligibilityContext(
                tenant_id=tenant_id,
                candidate_id=candidate_id,
                citizenship="UA",
                work_country="PL",
                position_category="driver",
                stage="recruitment",
            ),
        )

        assert result["subject_type"] == "candidate"
        assert result["subject_id"] == candidate_id
        assert set(result["allowed_operations"].keys()) >= {
            "submit_to_client",
            "handoff_to_hr",
            "approve_hr_verification",
            "sign_contract",
            "activate_employee",
            "assign_route",
            "start_work",
            "payroll_ready",
        }
        assert set(result["readiness_profiles"].keys()) >= {
            "recruitment_ready",
            "client_ready",
            "hr_ready",
            "employment_ready",
            "route_ready",
            "payroll_ready",
        }
        for profile in result["readiness_profiles"].values():
            assert set(profile.keys()) >= {
                "status",
                "blockers",
                "warnings",
                "missing_requirements",
                "affected_operations",
                "next_actions",
            }
