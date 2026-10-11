"""ADR-043 migration step 6 — HR Employment Profile policy contract."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, fields as dataclass_fields
from datetime import date
import uuid

import pytest

from backend.app.entity_profile.hr_employment_policy import (
    CONTRACT_ID,
    HrEmploymentProfileDocumentPolicy,
    HrEmploymentProfileFieldPolicy,
    HrEmploymentProfilePolicy,
    HrEmploymentProfilePolicyResolutionError,
    load_hr_employment_profile_policy,
)
from backend.app.entity_profile.publication_versions import publish_entity_profile
from backend.app.models.entity_profile import EpEntityProfile, EpEntityProfileField
from backend.app.models.field_registry import FrCanonicalField
from backend.app.models.ref_document_type import (
    RefDocumentType,
    RefDocumentTypeVersion,
)


async def _make_profile(
    db,
    *,
    tenant_id: str,
    module_owner: str = "hr",
    entity_type: str = "workforce_employee",
) -> EpEntityProfile:
    profile = EpEntityProfile(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        profile_code=f"{module_owner}.{entity_type}.{uuid.uuid4().hex[:8]}",
        registry_version="entity_profile_v1",
        status="active",
        name="HR Employment policy test profile",
        entity_type=entity_type,
        module_owner=module_owner,
        document_pack_code="legacy-pack",
        process_profile_code="legacy-process",
        version=1,
        config={"legacy_requirement": "must-not-leak"},
    )
    db.add(profile)
    await db.flush()
    return profile


async def _make_field(
    db,
    *,
    tenant_id: str,
    suffix: str,
) -> FrCanonicalField:
    qualified_code = f"hr.workforce_employee.{suffix}_{uuid.uuid4().hex[:8]}"
    field = FrCanonicalField(
        id=str(uuid.uuid4()),
        module="hr",
        tenant_id=tenant_id,
        code=qualified_code.rsplit(".", 1)[-1],
        qualified_code=qualified_code,
        registry_version="field_registry_v1",
        status="active",
        name=qualified_code,
        description=None,
        config={},
        is_system=False,
        entity_type="workforce_employee",
        field_type="text",
        label_key=None,
        ownership="hr",
        reference_domain=None,
        pii_class=None,
    )
    db.add(field)
    await db.flush()
    return field


async def _make_document_version(
    db,
    *,
    suffix: str,
    version_code: str = "v1",
) -> tuple[RefDocumentType, RefDocumentTypeVersion]:
    document_type = RefDocumentType(
        id=str(uuid.uuid4()),
        code=f"hr_step6_{suffix}_{uuid.uuid4().hex[:8]}",
        public_name=f"HR Step 6 {suffix}",
        status="active",
        origin="system",
        category_code="employment",
        criticality="informational",
    )
    db.add(document_type)
    await db.flush()

    version = RefDocumentTypeVersion(
        id=str(uuid.uuid4()),
        document_type_id=document_type.id,
        version_code=version_code,
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
    return document_type, version


@pytest.mark.anyio
async def test_policy_returns_exact_provenance_levels_and_document_identities(
    db,
    tenant_id: str,
) -> None:
    profile = await _make_profile(db, tenant_id=tenant_id)
    field_bindings = []
    for sort_order, level in ((30, "required"), (10, "hidden"), (20, "optional")):
        field = await _make_field(db, tenant_id=tenant_id, suffix=level)
        field_bindings.append(
            {
                "canonical_field_id": field.id,
                "qualified_code": field.qualified_code,
                "requirement_level": level,
                "sort_order": sort_order,
            }
        )

    document_bindings = []
    expected_documents = {}
    for sort_order, level in ((30, "required"), (10, "hidden"), (20, "preferred")):
        document_type, document_version = await _make_document_version(
            db,
            suffix=level,
            version_code=f"{level}-v1",
        )
        document_bindings.append(
            {
                "document_type_version_id": document_version.id,
                "requirement_level": level,
                "sort_order": sort_order,
            }
        )
        expected_documents[level] = (document_type, document_version)

    published = await publish_entity_profile(
        db,
        tenant_id=tenant_id,
        entity_profile_id=profile.id,
        field_bindings=field_bindings,
        document_bindings=document_bindings,
    )

    policy = await load_hr_employment_profile_policy(
        db,
        tenant_id=tenant_id,
        profile_version_id=published.id,
    )

    assert policy.contract_version == "hr_employment_profile_policy.v1" == CONTRACT_ID
    assert policy.profile_version_id == published.id
    assert policy.entity_profile_id == profile.id
    assert policy.profile_code == profile.profile_code
    assert policy.profile_version == published.version == 1
    assert policy.tenant_id == tenant_id
    assert policy.module_owner == "hr"
    assert policy.entity_type == "workforce_employee"
    assert [item.requirement_level for item in policy.fields] == [
        "hidden",
        "optional",
        "required",
    ]
    assert [item.requirement_level for item in policy.documents] == [
        "hidden",
        "preferred",
        "required",
    ]

    for item in policy.documents:
        document_type, document_version = expected_documents[item.requirement_level]
        assert item.document_type_id == document_type.id
        assert item.document_type_code == document_type.code
        assert item.document_type_version_id == document_version.id
        assert item.document_type_version_code == document_version.version_code


@pytest.mark.anyio
async def test_each_published_version_keeps_its_own_bindings(
    db,
    tenant_id: str,
) -> None:
    profile = await _make_profile(db, tenant_id=tenant_id)
    first_field = await _make_field(db, tenant_id=tenant_id, suffix="first")
    second_field = await _make_field(db, tenant_id=tenant_id, suffix="second")
    first_type, first_document = await _make_document_version(db, suffix="first")
    second_type, second_document = await _make_document_version(db, suffix="second")

    v1 = await publish_entity_profile(
        db,
        tenant_id=tenant_id,
        entity_profile_id=profile.id,
        field_bindings=[
            {
                "canonical_field_id": first_field.id,
                "qualified_code": first_field.qualified_code,
                "requirement_level": "optional",
            }
        ],
        document_bindings=[
            {
                "document_type_version_id": first_document.id,
                "requirement_level": "preferred",
            }
        ],
    )
    profile.config = {"changed_before_v2": True}
    v2 = await publish_entity_profile(
        db,
        tenant_id=tenant_id,
        entity_profile_id=profile.id,
        field_bindings=[
            {
                "canonical_field_id": second_field.id,
                "qualified_code": second_field.qualified_code,
                "requirement_level": "required",
            }
        ],
        document_bindings=[
            {
                "document_type_version_id": second_document.id,
                "requirement_level": "required",
            }
        ],
    )

    policy_v1 = await load_hr_employment_profile_policy(
        db, tenant_id=tenant_id, profile_version_id=v1.id
    )
    policy_v2 = await load_hr_employment_profile_policy(
        db, tenant_id=tenant_id, profile_version_id=v2.id
    )

    assert policy_v1.profile_version == 1
    assert policy_v1.fields[0].canonical_field_id == first_field.id
    assert policy_v1.fields[0].requirement_level == "optional"
    assert policy_v1.documents[0].document_type_id == first_type.id
    assert policy_v1.documents[0].requirement_level == "preferred"
    assert policy_v2.profile_version == 2
    assert policy_v2.fields[0].canonical_field_id == second_field.id
    assert policy_v2.fields[0].requirement_level == "required"
    assert policy_v2.documents[0].document_type_id == second_type.id
    assert policy_v2.documents[0].requirement_level == "required"


@pytest.mark.anyio
async def test_mutable_head_cannot_change_or_contribute_to_published_policy(
    db,
    tenant_id: str,
) -> None:
    profile = await _make_profile(db, tenant_id=tenant_id)
    field = await _make_field(db, tenant_id=tenant_id, suffix="immutable")
    other_field = await _make_field(db, tenant_id=tenant_id, suffix="mutable")
    mutable_field = EpEntityProfileField(
        id=str(uuid.uuid4()),
        entity_profile_id=profile.id,
        qualified_code=field.qualified_code,
        canonical_field_id=field.id,
        sort_order=1,
        intake_level="optional",
        card_save_level="optional",
        transition_level="optional",
        is_active=True,
    )
    db.add(mutable_field)
    _, document_version = await _make_document_version(db, suffix="immutable")

    published = await publish_entity_profile(
        db,
        tenant_id=tenant_id,
        entity_profile_id=profile.id,
        field_bindings=[
            {
                "canonical_field_id": field.id,
                "qualified_code": field.qualified_code,
                "requirement_level": "required",
                "sort_order": 7,
            }
        ],
        document_bindings=[
            {
                "document_type_version_id": document_version.id,
                "requirement_level": "preferred",
                "sort_order": 8,
            }
        ],
    )

    mutable_field.canonical_field_id = other_field.id
    mutable_field.qualified_code = other_field.qualified_code
    mutable_field.intake_level = "hidden"
    mutable_field.transition_level = "hidden"
    mutable_field.sort_order = 999
    profile.document_pack_code = "replacement-pack"
    profile.process_profile_code = "replacement-process"
    profile.config = {
        "fields": [{"canonical_field_id": other_field.id, "required": False}],
        "documents": [{"document_type_code": "invented", "required": True}],
    }
    await db.flush()

    policy = await load_hr_employment_profile_policy(
        db,
        tenant_id=tenant_id,
        profile_version_id=published.id,
    )

    assert policy.fields == (
        HrEmploymentProfileFieldPolicy(
            canonical_field_id=field.id,
            qualified_code=field.qualified_code,
            requirement_level="required",
            sort_order=7,
        ),
    )
    assert len(policy.documents) == 1
    assert policy.documents[0].document_type_version_id == document_version.id
    assert policy.documents[0].requirement_level == "preferred"


@pytest.mark.anyio
async def test_policy_rejects_tenant_mismatch(db, tenant_id: str) -> None:
    profile = await _make_profile(db, tenant_id=tenant_id)
    published = await publish_entity_profile(
        db, tenant_id=tenant_id, entity_profile_id=profile.id
    )

    with pytest.raises(HrEmploymentProfilePolicyResolutionError):
        await load_hr_employment_profile_policy(
            db,
            tenant_id=str(uuid.uuid4()),
            profile_version_id=published.id,
        )


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("module_owner", "entity_type"),
    (
        ("recruitment", "workforce_employee"),
        ("hr", "candidate"),
        ("hr", "employment"),
    ),
)
async def test_policy_rejects_wrong_bounded_context_identity(
    db,
    tenant_id: str,
    module_owner: str,
    entity_type: str,
) -> None:
    profile = await _make_profile(
        db,
        tenant_id=tenant_id,
        module_owner=module_owner,
        entity_type=entity_type,
    )
    published = await publish_entity_profile(
        db, tenant_id=tenant_id, entity_profile_id=profile.id
    )

    with pytest.raises(HrEmploymentProfilePolicyResolutionError):
        await load_hr_employment_profile_policy(
            db,
            tenant_id=tenant_id,
            profile_version_id=published.id,
        )


@pytest.mark.anyio
async def test_empty_published_version_remains_empty_without_fallback(
    db,
    tenant_id: str,
) -> None:
    profile = await _make_profile(db, tenant_id=tenant_id)
    mutable_field = await _make_field(db, tenant_id=tenant_id, suffix="head_only")
    db.add(
        EpEntityProfileField(
            id=str(uuid.uuid4()),
            entity_profile_id=profile.id,
            qualified_code=mutable_field.qualified_code,
            canonical_field_id=mutable_field.id,
            sort_order=1,
            intake_level="required",
            card_save_level="required",
            transition_level="required",
            is_active=True,
        )
    )
    profile.document_pack_code = "must-not-fallback"
    profile.process_profile_code = "must-not-fallback"
    profile.config = {"required_documents": ["must-not-fallback"]}
    published = await publish_entity_profile(
        db, tenant_id=tenant_id, entity_profile_id=profile.id
    )

    policy = await load_hr_employment_profile_policy(
        db,
        tenant_id=tenant_id,
        profile_version_id=published.id,
    )

    assert policy.fields == ()
    assert policy.documents == ()


@pytest.mark.anyio
async def test_policy_order_is_sort_order_then_stable_identity(
    db,
    tenant_id: str,
) -> None:
    profile = await _make_profile(db, tenant_id=tenant_id)
    fields = [
        await _make_field(db, tenant_id=tenant_id, suffix=suffix)
        for suffix in ("order_a", "order_b", "order_c")
    ]
    documents = [
        await _make_document_version(db, suffix=suffix)
        for suffix in ("order_a", "order_b", "order_c")
    ]
    published = await publish_entity_profile(
        db,
        tenant_id=tenant_id,
        entity_profile_id=profile.id,
        field_bindings=[
            {
                "canonical_field_id": item.id,
                "qualified_code": item.qualified_code,
                "requirement_level": "optional",
                "sort_order": 5,
            }
            for item in reversed(fields)
        ],
        document_bindings=[
            {
                "document_type_version_id": version.id,
                "requirement_level": "preferred",
                "sort_order": 5,
            }
            for _, version in reversed(documents)
        ],
    )

    policy = await load_hr_employment_profile_policy(
        db, tenant_id=tenant_id, profile_version_id=published.id
    )

    assert [item.canonical_field_id for item in policy.fields] == sorted(
        item.id for item in fields
    )
    assert [item.document_type_version_id for item in policy.documents] == sorted(
        version.id for _, version in documents
    )


def test_contract_is_frozen_and_has_no_legacy_policy_source_fields() -> None:
    field = HrEmploymentProfileFieldPolicy("field-id", "hr.field", "hidden", 1)
    document = HrEmploymentProfileDocumentPolicy(
        "doc-id", "doc-code", "doc-version-id", "v1", "hidden", 2
    )
    policy = HrEmploymentProfilePolicy(
        contract_version=CONTRACT_ID,
        profile_version_id="profile-version-id",
        entity_profile_id="profile-id",
        profile_code="hr.workforce_employee.default",
        profile_version=1,
        tenant_id="tenant-id",
        module_owner="hr",
        entity_type="workforce_employee",
        fields=(field,),
        documents=(document,),
    )

    with pytest.raises(FrozenInstanceError):
        field.sort_order = 3  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        document.requirement_level = "required"  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        policy.profile_version = 2  # type: ignore[misc]

    assert [item.name for item in dataclass_fields(HrEmploymentProfilePolicy)] == [
        "contract_version",
        "profile_version_id",
        "entity_profile_id",
        "profile_code",
        "profile_version",
        "tenant_id",
        "module_owner",
        "entity_type",
        "fields",
        "documents",
    ]
    forbidden_fragments = (
        "policy_ref",
        "document_pack",
        "process",
        "vacancy",
        "r5",
        "requirement_source",
        "employment_id",
    )
    assert all(
        fragment not in item.name.lower()
        for item in dataclass_fields(HrEmploymentProfilePolicy)
        for fragment in forbidden_fragments
    )
