"""ADR-043 Step 7A — tenant-owned Recruitment Profile authoring."""

from __future__ import annotations

from datetime import date
from unittest.mock import AsyncMock
import uuid

import pytest
from sqlalchemy import select

from backend.app.entity_profile.exceptions import EntityProfileNotFoundError
from backend.app.entity_profile.publication_versions import publish_entity_profile
from backend.app.entity_profile.recruitment_policy import (
    load_recruitment_profile_policy,
)
from backend.app.entity_profile.recruitment_profile_authoring import (
    RecruitmentProfileAlreadyExistsError,
    RecruitmentProfileAuthoringError,
    RecruitmentProfileTemplateError,
    RecruitmentProfileVersionConflictError,
    create_recruitment_profile,
    publish_recruitment_profile_revision,
)
from backend.app.models.entity_profile import EpEntityProfile, EpEntityProfileField
from backend.app.models.field_registry import FrCanonicalField
from backend.app.models.ref_document_type import (
    RefDocumentType,
    RefDocumentTypeVersion,
)


async def _make_field(
    db,
    *,
    tenant_id: str,
    suffix: str,
) -> FrCanonicalField:
    qualified_code = f"recruitment.candidate.{suffix}_{uuid.uuid4().hex[:8]}"
    field = FrCanonicalField(
        id=str(uuid.uuid4()),
        module="recruitment",
        tenant_id=tenant_id,
        code=qualified_code.rsplit(".", 1)[-1],
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


async def _make_document_version(
    db,
    *,
    suffix: str,
) -> tuple[RefDocumentType, RefDocumentTypeVersion]:
    document_type = RefDocumentType(
        id=str(uuid.uuid4()),
        code=f"step7a_{suffix}_{uuid.uuid4().hex[:8]}",
        public_name=f"Step 7A {suffix}",
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
    return document_type, version


async def _make_profile(
    db,
    *,
    tenant_id: str,
    profile_code: str | None = None,
    module_owner: str = "recruitment",
    entity_type: str = "candidate",
    is_system: bool = False,
    name: str = "Profile",
    description: str | None = None,
    default_layout_code: str | None = None,
    document_pack_code: str | None = None,
    process_profile_code: str | None = None,
    config: dict | None = None,
) -> EpEntityProfile:
    profile = EpEntityProfile(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        profile_code=profile_code or f"profile.{uuid.uuid4().hex[:8]}",
        registry_version="entity_profile_v1",
        status="active",
        name=name,
        description=description,
        is_system=is_system,
        entity_type=entity_type,
        module_owner=module_owner,
        default_layout_code=default_layout_code,
        document_pack_code=document_pack_code,
        process_profile_code=process_profile_code,
        version=1,
        config=dict(config or {}),
    )
    db.add(profile)
    await db.flush()
    return profile


@pytest.mark.anyio
async def test_create_tenant_profile_publishes_v1_with_explicit_bindings(
    db,
    tenant_id: str,
) -> None:
    field = await _make_field(db, tenant_id=tenant_id, suffix="create")
    document_type, document_version = await _make_document_version(
        db, suffix="create"
    )

    published = await create_recruitment_profile(
        db,
        tenant_id=tenant_id,
        profile_code=f"recruitment.candidate.{uuid.uuid4().hex[:8]}",
        name="Tenant recruitment profile",
        description="Tenant-owned",
        default_layout_code="recruitment.default",
        config={"presentation": "compact"},
        field_bindings=[
            {
                "canonical_field_id": field.id,
                "qualified_code": field.qualified_code,
                "requirement_level": "required",
                "sort_order": 11,
            }
        ],
        document_bindings=[
            {
                "document_type_version_id": document_version.id,
                "requirement_level": "preferred",
                "sort_order": 12,
            }
        ],
    )
    head = await db.get(EpEntityProfile, published.entity_profile_id)
    policy = await load_recruitment_profile_policy(
        db,
        tenant_id=tenant_id,
        profile_version_id=published.id,
    )

    assert published.version == 1
    assert head is not None
    assert head.published_version == 1
    assert head.tenant_id == tenant_id
    assert head.module_owner == "recruitment"
    assert head.entity_type == "candidate"
    assert head.is_system is False
    assert head.status == "active"
    assert policy.fields[0].canonical_field_id == field.id
    assert policy.fields[0].qualified_code == field.qualified_code
    assert policy.fields[0].requirement_level == "required"
    assert policy.fields[0].sort_order == 11
    assert policy.documents[0].document_type_id == document_type.id
    assert policy.documents[0].document_type_code == document_type.code
    assert policy.documents[0].document_type_version_id == document_version.id
    assert policy.documents[0].requirement_level == "preferred"
    assert policy.documents[0].sort_order == 12


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("tenant_id_value", "profile_code"),
    (("", "valid.code"), ("   ", "valid.code"), ("tenant", "")),
)
async def test_create_rejects_platform_scope_and_empty_identity(
    db,
    tenant_id_value: str,
    profile_code: str,
) -> None:
    with pytest.raises(RecruitmentProfileAuthoringError):
        await create_recruitment_profile(
            db,
            tenant_id=tenant_id_value,
            profile_code=profile_code,
            name="Rejected",
        )


@pytest.mark.anyio
async def test_duplicate_profile_code_is_rejected_within_tenant(
    db,
    tenant_id: str,
) -> None:
    profile_code = f"recruitment.candidate.{uuid.uuid4().hex[:8]}"
    await create_recruitment_profile(
        db,
        tenant_id=tenant_id,
        profile_code=profile_code,
        name="First",
    )

    with pytest.raises(RecruitmentProfileAlreadyExistsError):
        await create_recruitment_profile(
            db,
            tenant_id=tenant_id,
            profile_code=profile_code,
            name="Duplicate",
        )


@pytest.mark.anyio
async def test_platform_template_provides_metadata_defaults(db, tenant_id: str) -> None:
    template = await _make_profile(
        db,
        tenant_id="",
        module_owner="recruitment",
        entity_type="candidate",
        is_system=True,
        name="Platform default name",
        description="Platform default description",
        default_layout_code="platform.layout",
        config={"theme": "platform"},
    )

    published = await create_recruitment_profile(
        db,
        tenant_id=tenant_id,
        profile_code=f"tenant.profile.{uuid.uuid4().hex[:8]}",
        template_profile_code=template.profile_code,
    )
    head = await db.get(EpEntityProfile, published.entity_profile_id)

    assert head is not None
    assert head.name == template.name
    assert head.description == template.description
    assert head.default_layout_code == template.default_layout_code
    assert head.config == template.config
    assert head.is_system is False


@pytest.mark.anyio
async def test_explicit_metadata_overrides_template_defaults(
    db,
    tenant_id: str,
) -> None:
    template = await _make_profile(
        db,
        tenant_id="",
        is_system=True,
        name="Template name",
        description="Template description",
        default_layout_code="template.layout",
        config={"source": "template"},
    )

    published = await create_recruitment_profile(
        db,
        tenant_id=tenant_id,
        profile_code=f"tenant.override.{uuid.uuid4().hex[:8]}",
        template_profile_code=template.profile_code,
        name="Tenant name",
        description="Tenant description",
        default_layout_code="tenant.layout",
        config={"source": "tenant"},
    )
    head = await db.get(EpEntityProfile, published.entity_profile_id)

    assert head is not None
    assert head.name == "Tenant name"
    assert head.description == "Tenant description"
    assert head.default_layout_code == "tenant.layout"
    assert head.config == {"source": "tenant"}


@pytest.mark.anyio
@pytest.mark.parametrize(
    "deprecated_config",
    (
        {"field_configs": {"first_name": {"required": True}}},
        {"document_configs": {"passport": {"required": True}}},
        {
            "field_configs": {"first_name": {"required": True}},
            "document_configs": {"passport": {"required": True}},
        },
    ),
)
async def test_explicit_deprecated_candidate_profile_config_is_rejected(
    db,
    tenant_id: str,
    deprecated_config: dict,
) -> None:
    with pytest.raises(RecruitmentProfileAuthoringError) as exc_info:
        await create_recruitment_profile(
            db,
            tenant_id=tenant_id,
            profile_code=f"tenant.deprecated.{uuid.uuid4().hex[:8]}",
            name="Rejected legacy config",
            config=deprecated_config,
        )

    message = str(exc_info.value)
    for key in deprecated_config:
        assert key in message


@pytest.mark.anyio
async def test_template_deprecated_config_is_stripped_but_other_keys_are_preserved(
    db,
    tenant_id: str,
) -> None:
    template = await _make_profile(
        db,
        tenant_id="",
        is_system=True,
        config={
            "field_configs": {"first_name": {"required": True}},
            "document_configs": {"passport": {"required": True}},
            "required_documents": ["business-metadata"],
            "theme": {"density": "compact"},
        },
    )

    published = await create_recruitment_profile(
        db,
        tenant_id=tenant_id,
        profile_code=f"tenant.sanitized.{uuid.uuid4().hex[:8]}",
        template_profile_code=template.profile_code,
    )
    head = await db.get(EpEntityProfile, published.entity_profile_id)
    policy = await load_recruitment_profile_policy(
        db, tenant_id=tenant_id, profile_version_id=published.id
    )

    expected_config = {
        "required_documents": ["business-metadata"],
        "theme": {"density": "compact"},
    }
    assert head is not None
    assert head.config == expected_config
    assert published.config == expected_config
    assert policy.fields == ()
    assert policy.documents == ()


@pytest.mark.anyio
async def test_explicit_required_documents_config_is_preserved_without_fallback(
    db,
    tenant_id: str,
) -> None:
    expected_config = {
        "required_documents": ["legitimate-business-config"],
        "unrelated": True,
    }
    published = await create_recruitment_profile(
        db,
        tenant_id=tenant_id,
        profile_code=f"tenant.generic-config.{uuid.uuid4().hex[:8]}",
        name="Generic config profile",
        config=expected_config,
    )
    head = await db.get(EpEntityProfile, published.entity_profile_id)
    policy = await load_recruitment_profile_policy(
        db, tenant_id=tenant_id, profile_version_id=published.id
    )

    assert head is not None
    assert head.config == expected_config
    assert published.config == expected_config
    assert policy.fields == ()
    assert policy.documents == ()


@pytest.mark.anyio
async def test_template_requirements_mutable_fields_and_pack_are_not_copied(
    db,
    tenant_id: str,
) -> None:
    template = await _make_profile(
        db,
        tenant_id="",
        is_system=True,
        document_pack_code="legacy-template-pack",
        process_profile_code="legacy-template-process",
        config={"required_documents": ["legacy-config-document"]},
    )
    field = await _make_field(db, tenant_id="", suffix="template")
    _, document_version = await _make_document_version(db, suffix="template")
    db.add(
        EpEntityProfileField(
            id=str(uuid.uuid4()),
            entity_profile_id=template.id,
            qualified_code=field.qualified_code,
            canonical_field_id=field.id,
            sort_order=1,
            intake_level="required",
            card_save_level="required",
            transition_level="required",
            is_active=True,
        )
    )
    await publish_entity_profile(
        db,
        tenant_id="",
        entity_profile_id=template.id,
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

    published = await create_recruitment_profile(
        db,
        tenant_id=tenant_id,
        profile_code=f"tenant.empty.{uuid.uuid4().hex[:8]}",
        template_profile_code=template.profile_code,
    )
    head = await db.get(EpEntityProfile, published.entity_profile_id)
    policy = await load_recruitment_profile_policy(
        db, tenant_id=tenant_id, profile_version_id=published.id
    )
    mutable_rows = list(
        (
            await db.scalars(
                select(EpEntityProfileField).where(
                    EpEntityProfileField.entity_profile_id == published.entity_profile_id
                )
            )
        ).all()
    )

    assert head is not None
    assert head.document_pack_code is None
    assert head.process_profile_code is None
    assert mutable_rows == []
    assert policy.fields == ()
    assert policy.documents == ()


@pytest.mark.anyio
async def test_non_platform_template_is_not_resolved(db, tenant_id: str) -> None:
    template = await _make_profile(
        db,
        tenant_id=tenant_id,
        is_system=True,
    )

    with pytest.raises(RecruitmentProfileTemplateError):
        await create_recruitment_profile(
            db,
            tenant_id=tenant_id,
            profile_code=f"tenant.profile.{uuid.uuid4().hex[:8]}",
            name="Tenant profile",
            template_profile_code=template.profile_code,
        )


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("module_owner", "entity_type", "is_system"),
    (
        ("hr", "candidate", True),
        ("recruitment", "workforce_employee", True),
        ("recruitment", "candidate", False),
    ),
)
async def test_wrong_platform_template_identity_is_rejected(
    db,
    tenant_id: str,
    module_owner: str,
    entity_type: str,
    is_system: bool,
) -> None:
    template = await _make_profile(
        db,
        tenant_id="",
        module_owner=module_owner,
        entity_type=entity_type,
        is_system=is_system,
    )

    with pytest.raises(RecruitmentProfileTemplateError):
        await create_recruitment_profile(
            db,
            tenant_id=tenant_id,
            profile_code=f"tenant.profile.{uuid.uuid4().hex[:8]}",
            name="Tenant profile",
            template_profile_code=template.profile_code,
        )


@pytest.mark.anyio
async def test_revision_publishes_v2_and_preserves_v1(
    db,
    tenant_id: str,
) -> None:
    first_field = await _make_field(db, tenant_id=tenant_id, suffix="v1")
    second_field = await _make_field(db, tenant_id=tenant_id, suffix="v2")
    _, first_document = await _make_document_version(db, suffix="v1")
    _, second_document = await _make_document_version(db, suffix="v2")
    v1 = await create_recruitment_profile(
        db,
        tenant_id=tenant_id,
        profile_code=f"tenant.revision.{uuid.uuid4().hex[:8]}",
        name="Revision profile",
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

    v2 = await publish_recruitment_profile_revision(
        db,
        tenant_id=tenant_id,
        entity_profile_id=v1.entity_profile_id,
        expected_published_version=1,
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
    policy_v1 = await load_recruitment_profile_policy(
        db, tenant_id=tenant_id, profile_version_id=v1.id
    )
    policy_v2 = await load_recruitment_profile_policy(
        db, tenant_id=tenant_id, profile_version_id=v2.id
    )

    assert v1.version == 1
    assert v2.version == 2
    assert policy_v1.fields[0].canonical_field_id == first_field.id
    assert policy_v1.fields[0].requirement_level == "optional"
    assert policy_v1.documents[0].document_type_version_id == first_document.id
    assert policy_v1.documents[0].requirement_level == "preferred"
    assert policy_v2.fields[0].canonical_field_id == second_field.id
    assert policy_v2.fields[0].requirement_level == "required"
    assert policy_v2.documents[0].document_type_version_id == second_document.id
    assert policy_v2.documents[0].requirement_level == "required"


@pytest.mark.anyio
async def test_stale_expected_version_is_rejected(db, tenant_id: str) -> None:
    v1 = await create_recruitment_profile(
        db,
        tenant_id=tenant_id,
        profile_code=f"tenant.stale.{uuid.uuid4().hex[:8]}",
        name="Stale profile",
    )

    with pytest.raises(RecruitmentProfileVersionConflictError) as exc_info:
        await publish_recruitment_profile_revision(
            db,
            tenant_id=tenant_id,
            entity_profile_id=v1.entity_profile_id,
            expected_published_version=0,
        )

    assert exc_info.value.expected_version == 0
    assert exc_info.value.current_version == 1


@pytest.mark.anyio
async def test_revision_tenant_mismatch_is_rejected(db, tenant_id: str) -> None:
    v1 = await create_recruitment_profile(
        db,
        tenant_id=tenant_id,
        profile_code=f"tenant.isolation.{uuid.uuid4().hex[:8]}",
        name="Tenant profile",
    )

    with pytest.raises(EntityProfileNotFoundError):
        await publish_recruitment_profile_revision(
            db,
            tenant_id=str(uuid.uuid4()),
            entity_profile_id=v1.entity_profile_id,
            expected_published_version=1,
        )


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("module_owner", "entity_type", "is_system"),
    (
        ("recruitment", "candidate", True),
        ("hr", "candidate", False),
        ("recruitment", "workforce_employee", False),
    ),
)
async def test_invalid_profile_identity_cannot_be_revised(
    db,
    tenant_id: str,
    module_owner: str,
    entity_type: str,
    is_system: bool,
) -> None:
    profile = await _make_profile(
        db,
        tenant_id=tenant_id,
        module_owner=module_owner,
        entity_type=entity_type,
        is_system=is_system,
    )
    published = await publish_entity_profile(
        db,
        tenant_id=tenant_id,
        entity_profile_id=profile.id,
    )

    with pytest.raises(EntityProfileNotFoundError):
        await publish_recruitment_profile_revision(
            db,
            tenant_id=tenant_id,
            entity_profile_id=profile.id,
            expected_published_version=published.version,
        )


@pytest.mark.anyio
async def test_empty_requirement_sets_do_not_fall_back(db, tenant_id: str) -> None:
    published = await create_recruitment_profile(
        db,
        tenant_id=tenant_id,
        profile_code=f"tenant.empty.{uuid.uuid4().hex[:8]}",
        name="Empty profile",
        config={"required_documents": ["legacy"]},
    )
    head = await db.get(EpEntityProfile, published.entity_profile_id)
    assert head is not None
    head.document_pack_code = "legacy-pack"
    head.process_profile_code = "legacy-process"
    await db.flush()

    policy = await load_recruitment_profile_policy(
        db, tenant_id=tenant_id, profile_version_id=published.id
    )
    assert policy.fields == ()
    assert policy.documents == ()


@pytest.mark.anyio
async def test_create_is_atomic_when_publication_validation_fails(
    db,
    tenant_id: str,
) -> None:
    profile_code = f"tenant.atomic.{uuid.uuid4().hex[:8]}"

    with pytest.raises(ValueError, match="Canonical field not found"):
        await create_recruitment_profile(
            db,
            tenant_id=tenant_id,
            profile_code=profile_code,
            name="Invalid profile",
            field_bindings=[
                {
                    "canonical_field_id": str(uuid.uuid4()),
                    "qualified_code": "recruitment.candidate.unknown",
                    "requirement_level": "required",
                }
            ],
        )

    head = await db.scalar(
        select(EpEntityProfile).where(
            EpEntityProfile.tenant_id == tenant_id,
            EpEntityProfile.profile_code == profile_code,
        )
    )
    assert head is None


@pytest.mark.anyio
async def test_authoring_service_never_commits(
    db,
    tenant_id: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    commit = AsyncMock(side_effect=AssertionError("service must not commit"))
    monkeypatch.setattr(db, "commit", commit)

    v1 = await create_recruitment_profile(
        db,
        tenant_id=tenant_id,
        profile_code=f"tenant.transaction.{uuid.uuid4().hex[:8]}",
        name="Transaction profile",
    )
    await publish_recruitment_profile_revision(
        db,
        tenant_id=tenant_id,
        entity_profile_id=v1.entity_profile_id,
        expected_published_version=1,
    )

    commit.assert_not_awaited()
