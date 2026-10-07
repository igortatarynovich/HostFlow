"""ADR-043 Slice 2 — immutable Profile Version requirement bindings."""

from __future__ import annotations

from datetime import date
import uuid

import pytest
from sqlalchemy import select

from backend.app.entity_profile.publication_versions import publish_entity_profile
from backend.app.models.entity_profile import (
    EpEntityProfile,
    EpEntityProfileVersionDocument,
    EpEntityProfileVersionField,
)
from backend.app.models.field_registry import FrCanonicalField
from backend.app.models.ref_document_type import (
    RefDocumentType,
    RefDocumentTypeVersion,
)


async def _make_profile(db, *, tenant_id: str) -> EpEntityProfile:
    profile = EpEntityProfile(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        profile_code=f"recruitment.candidate.bindings_{uuid.uuid4().hex[:8]}",
        registry_version="entity_profile_v1",
        status="active",
        name="Bindings profile",
        entity_type="candidate",
        module_owner="recruitment",
        version=1,
        config={},
    )
    db.add(profile)
    await db.flush()
    return profile


async def _make_field(
    db,
    *,
    tenant_id: str,
    qualified_code: str,
) -> FrCanonicalField:
    field = FrCanonicalField(
        id=str(uuid.uuid4()),
        module="recruitment",
        tenant_id=tenant_id,
        code=qualified_code.split(".")[-1],
        qualified_code=qualified_code,
        registry_version="field_registry_v1",
        status="active",
        name=qualified_code,
        description=None,
        config={},
        is_system=False,
        entity_type="candidate",
        field_type="text",
        label_key=None,
        ownership="recruitment",
        reference_domain=None,
        pii_class=None,
    )
    db.add(field)
    await db.flush()
    return field


async def _make_document_version(db) -> RefDocumentTypeVersion:
    document_type = RefDocumentType(
        id=str(uuid.uuid4()),
        code=f"slice2_{uuid.uuid4().hex[:8]}",
        public_name="Slice 2 document",
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


async def _field_rows(db, version_id: str) -> list[EpEntityProfileVersionField]:
    rows = await db.scalars(
        select(EpEntityProfileVersionField)
        .where(EpEntityProfileVersionField.entity_profile_version_id == version_id)
        .order_by(EpEntityProfileVersionField.sort_order.asc())
    )
    return list(rows.all())


async def _document_rows(
    db,
    version_id: str,
) -> list[EpEntityProfileVersionDocument]:
    rows = await db.scalars(
        select(EpEntityProfileVersionDocument)
        .where(EpEntityProfileVersionDocument.entity_profile_version_id == version_id)
        .order_by(EpEntityProfileVersionDocument.sort_order.asc())
    )
    return list(rows.all())


@pytest.mark.anyio
async def test_publish_atomically_freezes_field_and_document_bindings(
    db,
    tenant_id: str,
) -> None:
    profile = await _make_profile(db, tenant_id=tenant_id)
    field = await _make_field(
        db,
        tenant_id=tenant_id,
        qualified_code="platform.identity.first_name",
    )
    document_version = await _make_document_version(db)

    published = await publish_entity_profile(
        db,
        tenant_id=tenant_id,
        entity_profile_id=profile.id,
        field_bindings=[
            {
                "canonical_field_id": field.id,
                "qualified_code": field.qualified_code,
                "requirement_level": "required",
                "sort_order": 10,
            }
        ],
        document_bindings=[
            {
                "document_type_version_id": document_version.id,
                "requirement_level": "preferred",
                "sort_order": 20,
            }
        ],
    )

    fields = await _field_rows(db, published.id)
    documents = await _document_rows(db, published.id)

    assert len(fields) == 1
    assert fields[0].canonical_field_id == field.id
    assert fields[0].qualified_code == "platform.identity.first_name"
    assert fields[0].requirement_level == "required"
    assert fields[0].sort_order == 10

    assert len(documents) == 1
    assert documents[0].document_type_version_id == document_version.id
    assert documents[0].requirement_level == "preferred"
    assert documents[0].sort_order == 20


@pytest.mark.anyio
@pytest.mark.parametrize("level", ["hidden", "optional", "required"])
async def test_field_requirement_vocabulary_is_accepted(
    db,
    tenant_id: str,
    level: str,
) -> None:
    profile = await _make_profile(db, tenant_id=tenant_id)
    field = await _make_field(
        db,
        tenant_id=tenant_id,
        qualified_code=f"recruitment.candidate.field_{uuid.uuid4().hex[:8]}",
    )

    published = await publish_entity_profile(
        db,
        tenant_id=tenant_id,
        entity_profile_id=profile.id,
        field_bindings=[
            {
                "canonical_field_id": field.id,
                "qualified_code": field.qualified_code,
                "requirement_level": level,
            }
        ],
    )

    rows = await _field_rows(db, published.id)
    assert [row.requirement_level for row in rows] == [level]


@pytest.mark.anyio
@pytest.mark.parametrize("level", ["hidden", "preferred", "required"])
async def test_document_requirement_vocabulary_is_accepted(
    db,
    tenant_id: str,
    level: str,
) -> None:
    profile = await _make_profile(db, tenant_id=tenant_id)
    document_version = await _make_document_version(db)

    published = await publish_entity_profile(
        db,
        tenant_id=tenant_id,
        entity_profile_id=profile.id,
        document_bindings=[
            {
                "document_type_version_id": document_version.id,
                "requirement_level": level,
            }
        ],
    )

    rows = await _document_rows(db, published.id)
    assert [row.requirement_level for row in rows] == [level]


@pytest.mark.anyio
async def test_publish_rejects_invalid_requirement_levels(
    db,
    tenant_id: str,
) -> None:
    profile = await _make_profile(db, tenant_id=tenant_id)
    field = await _make_field(
        db,
        tenant_id=tenant_id,
        qualified_code="platform.identity.last_name",
    )
    document_version = await _make_document_version(db)

    with pytest.raises(ValueError, match="Invalid profile field requirement_level"):
        await publish_entity_profile(
            db,
            tenant_id=tenant_id,
            entity_profile_id=profile.id,
            field_bindings=[
                {
                    "canonical_field_id": field.id,
                    "qualified_code": field.qualified_code,
                    "requirement_level": "preferred",
                }
            ],
        )

    with pytest.raises(ValueError, match="Invalid profile document requirement_level"):
        await publish_entity_profile(
            db,
            tenant_id=tenant_id,
            entity_profile_id=profile.id,
            document_bindings=[
                {
                    "document_type_version_id": document_version.id,
                    "requirement_level": "optional",
                }
            ],
        )

    assert profile.published_version == 0


@pytest.mark.anyio
async def test_publish_rejects_field_identity_mismatch_and_unknown_references(
    db,
    tenant_id: str,
) -> None:
    profile = await _make_profile(db, tenant_id=tenant_id)
    field = await _make_field(
        db,
        tenant_id=tenant_id,
        qualified_code="platform.identity.phone",
    )

    with pytest.raises(ValueError, match="Canonical field binding identity mismatch"):
        await publish_entity_profile(
            db,
            tenant_id=tenant_id,
            entity_profile_id=profile.id,
            field_bindings=[
                {
                    "canonical_field_id": field.id,
                    "qualified_code": "platform.identity.email",
                    "requirement_level": "required",
                }
            ],
        )

    with pytest.raises(ValueError, match="Canonical field not found"):
        await publish_entity_profile(
            db,
            tenant_id=tenant_id,
            entity_profile_id=profile.id,
            field_bindings=[
                {
                    "canonical_field_id": str(uuid.uuid4()),
                    "qualified_code": "platform.identity.email",
                    "requirement_level": "required",
                }
            ],
        )

    with pytest.raises(ValueError, match="Document type version not found"):
        await publish_entity_profile(
            db,
            tenant_id=tenant_id,
            entity_profile_id=profile.id,
            document_bindings=[
                {
                    "document_type_version_id": str(uuid.uuid4()),
                    "requirement_level": "required",
                }
            ],
        )

    assert profile.published_version == 0


@pytest.mark.anyio
async def test_publish_rejects_duplicate_bindings(
    db,
    tenant_id: str,
) -> None:
    profile = await _make_profile(db, tenant_id=tenant_id)
    field = await _make_field(
        db,
        tenant_id=tenant_id,
        qualified_code="platform.identity.email",
    )
    document_version = await _make_document_version(db)

    with pytest.raises(ValueError, match="Duplicate profile field binding"):
        await publish_entity_profile(
            db,
            tenant_id=tenant_id,
            entity_profile_id=profile.id,
            field_bindings=[
                {
                    "canonical_field_id": field.id,
                    "qualified_code": field.qualified_code,
                    "requirement_level": "optional",
                },
                {
                    "canonical_field_id": field.id,
                    "qualified_code": field.qualified_code,
                    "requirement_level": "required",
                },
            ],
        )

    with pytest.raises(ValueError, match="Duplicate profile document binding"):
        await publish_entity_profile(
            db,
            tenant_id=tenant_id,
            entity_profile_id=profile.id,
            document_bindings=[
                {
                    "document_type_version_id": document_version.id,
                    "requirement_level": "preferred",
                },
                {
                    "document_type_version_id": document_version.id,
                    "requirement_level": "required",
                },
            ],
        )

    assert profile.published_version == 0


@pytest.mark.anyio
async def test_later_publication_cannot_change_prior_version_bindings(
    db,
    tenant_id: str,
) -> None:
    profile = await _make_profile(db, tenant_id=tenant_id)
    field = await _make_field(
        db,
        tenant_id=tenant_id,
        qualified_code=f"recruitment.candidate.history_{uuid.uuid4().hex[:8]}",
    )
    document_version = await _make_document_version(db)

    first = await publish_entity_profile(
        db,
        tenant_id=tenant_id,
        entity_profile_id=profile.id,
        field_bindings=[
            {
                "canonical_field_id": field.id,
                "qualified_code": field.qualified_code,
                "requirement_level": "optional",
            }
        ],
        document_bindings=[
            {
                "document_type_version_id": document_version.id,
                "requirement_level": "preferred",
            }
        ],
    )

    second = await publish_entity_profile(
        db,
        tenant_id=tenant_id,
        entity_profile_id=profile.id,
        field_bindings=[
            {
                "canonical_field_id": field.id,
                "qualified_code": field.qualified_code,
                "requirement_level": "required",
            }
        ],
        document_bindings=[
            {
                "document_type_version_id": document_version.id,
                "requirement_level": "required",
            }
        ],
    )

    first_fields = await _field_rows(db, first.id)
    first_documents = await _document_rows(db, first.id)
    second_fields = await _field_rows(db, second.id)
    second_documents = await _document_rows(db, second.id)

    assert first.version == 1
    assert second.version == 2

    assert first_fields[0].requirement_level == "optional"
    assert first_documents[0].requirement_level == "preferred"

    assert second_fields[0].requirement_level == "required"
    assert second_documents[0].requirement_level == "required"
