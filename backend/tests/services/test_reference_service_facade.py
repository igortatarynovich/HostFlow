from __future__ import annotations

import uuid

import pytest

from backend.app.db.session import async_session_maker
from backend.app.models import Candidate, Tenant
from backend.app.reference.core_immutable_catalogs import CATALOG_VERSION
from backend.app.schemas.reference_core_immutable import CoreImmutableSnapshotOut
from backend.app.schemas.reference_field_schema import ReferenceFieldSchemaSnapshotOut
from backend.app.schemas.reference_legal_document import LegalDocumentSnapshotOut
from backend.app.schemas.reference_rule_pack import ReferenceRulePackFoundationSnapshotOut
from backend.app.schemas.reference_tenant_override import ReferenceTenantOverrideFoundationSnapshotOut
from backend.app.schemas.reference_workforce_transport import ReferenceWorkforceTransportSnapshotOut
from backend.app.services.document_reference_sync import seed_and_sync_document_references
from backend.app.services.reference_service_facade import ReferenceContext, ReferenceServiceFacade

pytestmark = pytest.mark.anyio


async def test_reference_facade_bundle_shape_stable() -> None:
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
        session.add(
            Candidate(
                id=candidate_id,
                tenant_id=tenant_id,
                first_name="Ref",
                last_name="Facade",
            )
        )
        await session.commit()

        out = await ReferenceServiceFacade.get_reference_bundle(
            session,
            context=ReferenceContext(
                tenant_id=tenant_id,
                module="recruitment",
                entity_type="candidate",
                entity_id=candidate_id,
                candidate_id=candidate_id,
                work_country="PL",
                citizenship="UA",
                locale="en",
            ),
        )

        assert set(out.keys()) == {"version", "context_echo", "items", "applicability", "errors"}
        ver = out["version"]
        assert set(ver.keys()) == {"contract_version", "reference_version", "calculated_at"}
        assert out["context_echo"]["tenant_id"] == tenant_id
        assert isinstance(out["items"], list)
        assert any(i.get("item_type") == "country" for i in out["items"])
        assert any(i.get("item_type") == "language" for i in out["items"])
        assert all((i.get("source") or {}).get("code") == "core_immutable_catalogs" for i in out["items"] if i.get("item_type") in {"country", "language"})
        assert out["version"]["reference_version"].startswith(CATALOG_VERSION)
        assert isinstance(out["errors"], list)
        assert isinstance((out["applicability"] or {}).get("expected_documents"), list)


async def test_reference_facade_country_and_doc_profile() -> None:
    async with async_session_maker() as session:
        await seed_and_sync_document_references(session)
        tenant_id = str(uuid.uuid4())

        ctx = ReferenceContext(tenant_id=tenant_id, module="hr", entity_type="employee", locale="en")
        country = await ReferenceServiceFacade.get_country_profile(session, country_code="PL", context=ctx)
        assert country["profile"]["country_code"] == "PL"
        assert country["profile"]["alpha3"] == "POL"
        assert country["profile"]["numeric"] == "616"
        assert "groups" in country["profile"]

        doc = await ReferenceServiceFacade.get_document_type_profile(session, code="passport", context=ctx)
        assert doc["profile"]["document_code"] == "passport"
        assert "required_fields" in doc["profile"]


def test_reference_facade_core_immutable_snapshot_contract() -> None:
    snap = ReferenceServiceFacade.get_core_immutable_snapshot()
    assert set(snap.keys()) == {
        "contract_version",
        "reference_version",
        "catalog_version",
        "countries",
        "languages",
    }
    assert isinstance(snap["countries"], list)
    assert isinstance(snap["languages"], list)
    assert len(snap["countries"]) >= 1
    assert len(snap["languages"]) >= 1
    typed = CoreImmutableSnapshotOut.model_validate(snap)
    assert typed.catalog_version.startswith("ref4-phase1a-core-immutable-")


def test_reference_facade_core_immutable_snapshot_compatibility_check() -> None:
    out = ReferenceServiceFacade.compatibility_check_core_immutable_snapshot()
    assert set(out.keys()) == {
        "valid",
        "errors",
        "warnings",
        "contract_version",
        "reference_version",
    }
    assert out["valid"] is True
    assert out["errors"] == []


def test_reference_facade_legal_document_snapshot_contract() -> None:
    snap = ReferenceServiceFacade.get_legal_document_snapshot()
    assert set(snap.keys()) == {
        "contract_version",
        "reference_version",
        "catalog_version",
        "citizenships",
        "legal_statuses",
        "permit_types",
        "visa_types",
        "document_categories",
        "document_types",
    }
    assert len(snap["citizenships"]) >= 1
    assert len(snap["document_types"]) >= 1
    typed = LegalDocumentSnapshotOut.model_validate(snap)
    assert typed.catalog_version.startswith("ref4-phase1b-legal-document-")


def test_reference_facade_field_schema_snapshot_contract() -> None:
    snap = ReferenceServiceFacade.get_reference_field_schema_snapshot()
    assert set(snap.keys()) == {
        "contract_version",
        "reference_version",
        "catalog_version",
        "fields",
    }
    assert len(snap["fields"]) >= 1
    typed = ReferenceFieldSchemaSnapshotOut.model_validate(snap)
    assert typed.catalog_version.startswith("ref4-phase1c-field-schema-")
    keys = {item.field_key for item in typed.fields}
    assert {
        "workforce_category",
        "employment_type",
        "transport_mode",
        "transport_qualification_type",
        "driver_capability_class",
    }.issubset(keys)


def test_reference_facade_workforce_transport_snapshot_contract() -> None:
    snap = ReferenceServiceFacade.get_workforce_transport_snapshot()
    assert set(snap.keys()) == {
        "contract_version",
        "reference_version",
        "catalog_version",
        "workforce_categories",
        "employment_types",
        "transport_modes",
        "transport_qualification_types",
        "driver_capability_classes",
    }
    assert len(snap["workforce_categories"]) >= 1
    assert len(snap["driver_capability_classes"]) >= 1
    typed = ReferenceWorkforceTransportSnapshotOut.model_validate(snap)
    assert typed.catalog_version.startswith("ref4-phase1c-workforce-transport-")


def test_reference_facade_tenant_override_foundation_snapshot_contract() -> None:
    snap = ReferenceServiceFacade.get_tenant_override_foundation_snapshot()
    assert set(snap.keys()) == {
        "contract_version",
        "reference_version",
        "catalog_version",
        "override_types",
        "allowed_domains",
        "immutable_rules",
        "overlay_schema_contract",
    }
    typed = ReferenceTenantOverrideFoundationSnapshotOut.model_validate(snap)
    assert typed.catalog_version.startswith("ref4-phase1c-tenant-override-foundation-")


def test_reference_facade_tenant_override_foundation_snapshot_compatibility_check() -> None:
    out = ReferenceServiceFacade.compatibility_check_tenant_override_foundation_snapshot()
    assert set(out.keys()) == {
        "valid",
        "errors",
        "warnings",
        "contract_version",
        "reference_version",
    }
    assert out["valid"] is True
    assert out["errors"] == []


def test_reference_facade_rule_pack_foundation_snapshot_contract() -> None:
    snap = ReferenceServiceFacade.get_rule_pack_foundation_snapshot()
    assert set(snap.keys()) == {
        "contract_version",
        "reference_version",
        "catalog_version",
        "rule_pack_types",
        "rule_pack_metadata",
        "allowed_target_domains",
        "rule_pack_versions",
    }
    typed = ReferenceRulePackFoundationSnapshotOut.model_validate(snap)
    assert typed.catalog_version.startswith("ref4-phase1c-rule-pack-foundation-")


def test_reference_facade_rule_pack_foundation_snapshot_compatibility_check() -> None:
    out = ReferenceServiceFacade.compatibility_check_rule_pack_foundation_snapshot()
    assert set(out.keys()) == {
        "valid",
        "errors",
        "warnings",
        "contract_version",
        "reference_version",
    }
    assert out["valid"] is True
    assert out["errors"] == []


def test_reference_facade_seed_manifest_snapshot_contract() -> None:
    snap = ReferenceServiceFacade.get_reference_seed_manifest_snapshot()
    assert set(snap.keys()) == {
        "contract_version",
        "reference_version",
        "catalog_version",
        "seed_manifest",
        "reference_versions",
        "deterministic_checksum",
        "migration_boundary",
    }
    assert isinstance(snap["seed_manifest"], list)
    assert isinstance(snap["reference_versions"], dict)
    assert len(snap["deterministic_checksum"]) == 64
    assert set(snap["migration_boundary"].keys()) == {"phase_scope", "allowed", "blocked"}
    assert snap["catalog_version"].startswith("ref4-phase1c-seed-manifest-")


def test_reference_facade_seed_manifest_snapshot_compatibility_check() -> None:
    out = ReferenceServiceFacade.compatibility_check_reference_seed_manifest_snapshot()
    assert set(out.keys()) == {
        "valid",
        "errors",
        "warnings",
        "contract_version",
        "reference_version",
    }
    assert out["valid"] is True
    assert out["errors"] == []
