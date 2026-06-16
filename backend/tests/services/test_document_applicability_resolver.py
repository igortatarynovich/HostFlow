from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select

from backend.app.db.session import async_session_maker
from backend.app.models import RefDocumentType, RefPack, Tenant, TenantDocumentPackEnablement, TenantDocumentTypeOverride
from backend.app.services.document_applicability_resolver import (
    DocumentApplicabilityContext,
    DocumentApplicabilityResolver,
)
from backend.app.services.document_reference_sync import seed_and_sync_document_references

pytestmark = pytest.mark.anyio


async def _seed() -> None:
    async with async_session_maker() as session:
        await seed_and_sync_document_references(session)
        await session.commit()


async def _tenant(session, tenant_id: str) -> None:
    session.add(
        Tenant(
            id=tenant_id,
            name=f"Tenant {tenant_id[:8]}",
            slug=f"tenant-{tenant_id[:8]}",
            api_key=f"api-{tenant_id[:8]}",
            is_active=True,
        )
    )


async def _enable_pack(session, tenant_id: str, code: str, *, enabled: bool = True) -> None:
    pack = (await session.execute(select(RefPack).where(RefPack.code == code))).scalar_one()
    session.add(TenantDocumentPackEnablement(tenant_id=tenant_id, pack_id=pack.id, enabled=enabled))


async def test_seed_creates_base_m4_packs() -> None:
    await _seed()
    async with async_session_maker() as session:
        rows = (await session.execute(select(RefPack.code))).all()
        codes = {str(x[0]) for x in rows}
        assert "pl_base_hr" in codes
        assert "pl_non_eu_worker" in codes
        assert "pl_transport_driver" in codes
        assert "eu_driver_compliance" in codes
        assert "client_specific_requirements" in codes


async def test_non_eu_worker_pack_adds_immigration_docs() -> None:
    await _seed()
    tenant_id = str(uuid.uuid4())
    async with async_session_maker() as session:
        await _tenant(session, tenant_id)
        await _enable_pack(session, tenant_id, "pl_non_eu_worker")
        await session.commit()

        out = await DocumentApplicabilityResolver.resolve_expected_documents(
            session,
            context=DocumentApplicabilityContext(
                tenant_id=tenant_id,
                citizenship="ua",
                work_country="PL",
                position_category="driver",
                stage="recruitment",
            ),
        )
        by_code = {x["document_code"]: x for x in out}
        assert by_code["work_permit"]["required"] is True
        assert by_code["residence_card"]["required"] is True
        assert "visa" in by_code


async def test_transport_driver_pack_adds_driver_compliance_set() -> None:
    await _seed()
    tenant_id = str(uuid.uuid4())
    async with async_session_maker() as session:
        await _tenant(session, tenant_id)
        await _enable_pack(session, tenant_id, "pl_transport_driver")
        await session.commit()

        out = await DocumentApplicabilityResolver.resolve_expected_documents(
            session,
            context=DocumentApplicabilityContext(tenant_id=tenant_id, work_country="PL", position_category="driver"),
        )
        codes = {x["document_code"] for x in out if x.get("required")}
        assert {"driver_license", "code_95", "medical_certificate", "psychotest", "tachograph_card"}.issubset(codes)


async def test_eu_driver_does_not_require_non_eu_work_permit() -> None:
    await _seed()
    tenant_id = str(uuid.uuid4())
    async with async_session_maker() as session:
        await _tenant(session, tenant_id)
        await _enable_pack(session, tenant_id, "pl_non_eu_worker")
        await _enable_pack(session, tenant_id, "pl_transport_driver")
        await session.commit()

        out = await DocumentApplicabilityResolver.resolve_expected_documents(
            session,
            context=DocumentApplicabilityContext(tenant_id=tenant_id, citizenship="pl", work_country="PL", position_category="driver"),
        )
        by_code = {x["document_code"]: x for x in out}
        assert by_code["work_permit"]["required"] is False


async def test_disabled_pack_has_no_effect() -> None:
    await _seed()
    tenant_id = str(uuid.uuid4())
    async with async_session_maker() as session:
        await _tenant(session, tenant_id)
        await _enable_pack(session, tenant_id, "pl_transport_driver", enabled=False)
        await session.commit()

        out = await DocumentApplicabilityResolver.resolve_expected_documents(
            session,
            context=DocumentApplicabilityContext(tenant_id=tenant_id, work_country="PL", position_category="driver"),
        )
        assert out == []


async def test_tenant_override_can_raise_requirement_but_not_drop_compliance_critical() -> None:
    await _seed()
    tenant_id = str(uuid.uuid4())
    async with async_session_maker() as session:
        await _tenant(session, tenant_id)
        await _enable_pack(session, tenant_id, "client_specific_requirements")
        await _enable_pack(session, tenant_id, "pl_non_eu_worker")

        # Raise optional->required for "other".
        other = (await session.execute(select(RefDocumentType).where(RefDocumentType.code == "other"))).scalar_one()
        session.add(
            TenantDocumentTypeOverride(
                tenant_id=tenant_id,
                document_type_id=other.id,
                scope_type="tenant",
                required_level="required",
                enabled=True,
            )
        )

        # Try to drop compliance-critical "work_permit".
        wp = (await session.execute(select(RefDocumentType).where(RefDocumentType.code == "work_permit"))).scalar_one()
        session.add(
            TenantDocumentTypeOverride(
                tenant_id=tenant_id,
                document_type_id=wp.id,
                scope_type="tenant",
                required_level="optional",
                enabled=True,
            )
        )
        await session.commit()

        out = await DocumentApplicabilityResolver.resolve_expected_documents(
            session,
            context=DocumentApplicabilityContext(tenant_id=tenant_id, citizenship="ua", work_country="PL"),
        )
        by_code = {x["document_code"]: x for x in out}
        assert by_code["other"]["required"] is True
        assert by_code["other"]["tenant_override_changed"] is True
        assert by_code["work_permit"]["required"] is True


async def test_unknown_context_is_safe_and_returns_minimal_set() -> None:
    await _seed()
    tenant_id = str(uuid.uuid4())
    async with async_session_maker() as session:
        await _tenant(session, tenant_id)
        await _enable_pack(session, tenant_id, "client_specific_requirements")
        await session.commit()

        out = await DocumentApplicabilityResolver.resolve_expected_documents(
            session,
            context=DocumentApplicabilityContext(tenant_id=tenant_id),
        )
        assert out
        assert any(x["document_code"] == "other" for x in out)
        assert all("source_pack" in x and "reason" in x for x in out)
