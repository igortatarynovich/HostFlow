"""ADR-043 Step 7B — Recruitment Profile HTTP authoring surface."""

from __future__ import annotations

from datetime import date
import inspect
import uuid

from httpx import AsyncClient
import pytest
from sqlalchemy import select

from backend.app.api.v1.platform import entity_profiles as entity_profiles_api
from backend.app.entity_profile.publication_versions import publish_entity_profile
from backend.app.entity_profile.recruitment_policy import (
    load_recruitment_profile_policy,
)
from backend.app.models.entity_profile import EpEntityProfile
from backend.app.models.field_registry import FrCanonicalField
from backend.app.models.ref_document_type import (
    RefDocumentType,
    RefDocumentTypeVersion,
)


CREATE_URL = "/api/v1/platform/entity-profiles/recruitment"


async def _make_field(db, *, tenant_id: str, suffix: str) -> FrCanonicalField:
    qualified_code = f"recruitment.candidate.api_{suffix}_{uuid.uuid4().hex[:8]}"
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
        code=f"step7b_{suffix}_{uuid.uuid4().hex[:8]}",
        public_name=f"Step 7B {suffix}",
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
    module_owner: str = "recruitment",
    entity_type: str = "candidate",
    is_system: bool = False,
    profile_code: str | None = None,
    config: dict | None = None,
) -> EpEntityProfile:
    profile = EpEntityProfile(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        profile_code=profile_code or f"api.profile.{uuid.uuid4().hex[:8]}",
        registry_version="entity_profile_v1",
        status="active",
        name="API profile",
        description="API profile description",
        is_system=is_system,
        entity_type=entity_type,
        module_owner=module_owner,
        default_layout_code="api.layout",
        version=1,
        config=dict(config or {}),
    )
    db.add(profile)
    await db.flush()
    return profile


def _create_payload(*, profile_code: str | None = None) -> dict:
    return {
        "profile_code": profile_code or f"tenant.api.{uuid.uuid4().hex[:8]}",
        "name": "Tenant API profile",
        "description": "Created through Step 7B",
        "default_layout_code": "tenant.api.layout",
        "config": {"theme": "compact"},
        "fields": [],
        "documents": [],
    }


@pytest.mark.anyio
async def test_create_returns_persisted_v1_with_canonical_bindings(
    client: AsyncClient,
    db,
    tenant_id: str,
    manager_headers: dict[str, str],
) -> None:
    first_field = await _make_field(db, tenant_id=tenant_id, suffix="first")
    second_field = await _make_field(db, tenant_id=tenant_id, suffix="second")
    document_type, document_version = await _make_document_version(db, suffix="create")
    await db.commit()
    payload = _create_payload()
    payload["fields"] = [
        {
            "canonical_field_id": second_field.id,
            "qualified_code": second_field.qualified_code,
            "requirement_level": "required",
            "sort_order": 20,
        },
        {
            "canonical_field_id": first_field.id,
            "qualified_code": first_field.qualified_code,
            "requirement_level": "hidden",
            "sort_order": 10,
        },
    ]
    payload["documents"] = [
        {
            "document_type_version_id": document_version.id,
            "requirement_level": "preferred",
            "sort_order": 30,
        }
    ]

    response = await client.post(CREATE_URL, headers=manager_headers, json=payload)

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["version"] == 1
    assert body["profile_code"] == payload["profile_code"]
    assert body["tenant_id"] == tenant_id
    assert body["module_owner"] == "recruitment"
    assert body["entity_type"] == "candidate"
    assert body["name"] == payload["name"]
    assert body["description"] == payload["description"]
    assert body["default_layout_code"] == payload["default_layout_code"]
    assert body["config"] == payload["config"]
    assert body["published_at"]
    assert [item["canonical_field_id"] for item in body["fields"]] == [
        first_field.id,
        second_field.id,
    ]
    assert body["documents"] == [
        {
            "document_type_id": document_type.id,
            "document_type_code": document_type.code,
            "document_type_version_id": document_version.id,
            "document_type_version_code": document_version.version_code,
            "requirement_level": "preferred",
            "sort_order": 30,
        }
    ]

    db.expire_all()
    head = await db.get(EpEntityProfile, body["entity_profile_id"])
    assert head is not None
    assert head.is_system is False
    assert head.published_version == 1


@pytest.mark.anyio
async def test_template_create_does_not_copy_template_requirements(
    client: AsyncClient,
    db,
    tenant_id: str,
    manager_headers: dict[str, str],
) -> None:
    template = await _make_profile(
        db,
        tenant_id="",
        is_system=True,
        config={"field_configs": {"legacy": True}, "theme": "platform"},
    )
    field = await _make_field(db, tenant_id="", suffix="template")
    _, document_version = await _make_document_version(db, suffix="template")
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
    await db.commit()

    response = await client.post(
        CREATE_URL,
        headers=manager_headers,
        json={
            "profile_code": f"tenant.template.{uuid.uuid4().hex[:8]}",
            "template_profile_code": template.profile_code,
        },
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["name"] == template.name
    assert body["config"] == {"theme": "platform"}
    assert body["fields"] == []
    assert body["documents"] == []


@pytest.mark.anyio
async def test_deprecated_explicit_config_is_422(
    client: AsyncClient,
    manager_headers: dict[str, str],
) -> None:
    payload = _create_payload()
    payload["config"] = {"field_configs": {"legacy": True}}

    response = await client.post(CREATE_URL, headers=manager_headers, json=payload)

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "recruitment_profile_authoring_invalid"
    assert "field_configs" in response.json()["detail"]["message"]


@pytest.mark.anyio
async def test_duplicate_profile_code_is_409(
    client: AsyncClient,
    manager_headers: dict[str, str],
) -> None:
    payload = _create_payload()
    first = await client.post(CREATE_URL, headers=manager_headers, json=payload)
    second = await client.post(CREATE_URL, headers=manager_headers, json=payload)

    assert first.status_code == 201, first.text
    assert second.status_code == 409
    assert second.json()["detail"]["code"] == "recruitment_profile_already_exists"


@pytest.mark.anyio
async def test_invalid_template_is_422(
    client: AsyncClient,
    manager_headers: dict[str, str],
) -> None:
    payload = _create_payload()
    payload["template_profile_code"] = "missing.platform.template"

    response = await client.post(CREATE_URL, headers=manager_headers, json=payload)

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "recruitment_profile_template_invalid"


@pytest.mark.anyio
@pytest.mark.parametrize("binding_kind", ("field", "document"))
async def test_invalid_binding_is_422_and_leaves_no_partial_profile(
    client: AsyncClient,
    db,
    tenant_id: str,
    manager_headers: dict[str, str],
    binding_kind: str,
) -> None:
    payload = _create_payload()
    if binding_kind == "field":
        payload["fields"] = [
            {
                "canonical_field_id": str(uuid.uuid4()),
                "qualified_code": "recruitment.candidate.unknown",
                "requirement_level": "required",
            }
        ]
    else:
        payload["documents"] = [
            {
                "document_type_version_id": str(uuid.uuid4()),
                "requirement_level": "required",
            }
        ]

    response = await client.post(CREATE_URL, headers=manager_headers, json=payload)

    assert response.status_code == 422
    db.expire_all()
    head = await db.scalar(
        select(EpEntityProfile).where(
            EpEntityProfile.tenant_id == tenant_id,
            EpEntityProfile.profile_code == payload["profile_code"],
        )
    )
    assert head is None


@pytest.mark.anyio
async def test_revision_returns_v2_and_preserves_v1(
    client: AsyncClient,
    db,
    tenant_id: str,
    manager_headers: dict[str, str],
) -> None:
    first_field = await _make_field(db, tenant_id=tenant_id, suffix="revision_v1")
    second_field = await _make_field(db, tenant_id=tenant_id, suffix="revision_v2")
    await db.commit()
    create_payload = _create_payload()
    create_payload["fields"] = [
        {
            "canonical_field_id": first_field.id,
            "qualified_code": first_field.qualified_code,
            "requirement_level": "optional",
        }
    ]
    created = await client.post(CREATE_URL, headers=manager_headers, json=create_payload)
    assert created.status_code == 201, created.text
    v1 = created.json()

    revised = await client.post(
        f"{CREATE_URL}/{v1['entity_profile_id']}/versions",
        headers=manager_headers,
        json={
            "expected_published_version": 1,
            "fields": [
                {
                    "canonical_field_id": second_field.id,
                    "qualified_code": second_field.qualified_code,
                    "requirement_level": "required",
                }
            ],
            "documents": [],
        },
    )

    assert revised.status_code == 201, revised.text
    v2 = revised.json()
    assert v2["version"] == 2
    assert v2["fields"][0]["canonical_field_id"] == second_field.id
    policy_v1 = await load_recruitment_profile_policy(
        db,
        tenant_id=tenant_id,
        profile_version_id=v1["profile_version_id"],
    )
    assert policy_v1.profile_version == 1
    assert policy_v1.fields[0].canonical_field_id == first_field.id
    assert policy_v1.fields[0].requirement_level == "optional"


@pytest.mark.anyio
async def test_stale_revision_is_structured_409(
    client: AsyncClient,
    manager_headers: dict[str, str],
) -> None:
    created = await client.post(
        CREATE_URL, headers=manager_headers, json=_create_payload()
    )
    entity_profile_id = created.json()["entity_profile_id"]

    response = await client.post(
        f"{CREATE_URL}/{entity_profile_id}/versions",
        headers=manager_headers,
        json={"expected_published_version": 2},
    )

    assert response.status_code == 409
    detail = response.json()["detail"]
    assert detail["code"] == "recruitment_profile_version_conflict"
    assert detail["expected_version"] == 2
    assert detail["current_version"] == 1


@pytest.mark.anyio
async def test_revision_missing_profile_is_404(
    client: AsyncClient,
    manager_headers: dict[str, str],
) -> None:
    response = await client.post(
        f"{CREATE_URL}/{uuid.uuid4()}/versions",
        headers=manager_headers,
        json={"expected_published_version": 1},
    )
    assert response.status_code == 404


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
    client: AsyncClient,
    db,
    tenant_id: str,
    manager_headers: dict[str, str],
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
        db, tenant_id=tenant_id, entity_profile_id=profile.id
    )
    await db.commit()

    response = await client.post(
        f"{CREATE_URL}/{profile.id}/versions",
        headers=manager_headers,
        json={"expected_published_version": published.version},
    )
    assert response.status_code == 404


@pytest.mark.anyio
async def test_success_is_committed_and_existing_get_still_resolves(
    client: AsyncClient,
    db,
    manager_headers: dict[str, str],
) -> None:
    payload = _create_payload()
    created = await client.post(CREATE_URL, headers=manager_headers, json=payload)
    assert created.status_code == 201, created.text
    body = created.json()

    db.expire_all()
    persisted = await db.get(EpEntityProfile, body["entity_profile_id"])
    assert persisted is not None
    assert persisted.published_version == 1

    existing_get = await client.get(
        f"/api/v1/platform/entity-profiles/{payload['profile_code']}",
        headers=manager_headers,
    )
    assert existing_get.status_code == 200, existing_get.text
    assert existing_get.json()["profile"]["profile_code"] == payload["profile_code"]


@pytest.mark.anyio
async def test_routes_precede_catch_all_and_require_write_permission(
    client: AsyncClient,
    viewer_headers: dict[str, str],
) -> None:
    paths = [route.path for route in entity_profiles_api.router.routes]
    assert paths.index("/platform/entity-profiles/recruitment") < paths.index(
        "/platform/entity-profiles/{profile_code}"
    )
    assert paths.index(
        "/platform/entity-profiles/recruitment/{entity_profile_id}/versions"
    ) < paths.index("/platform/entity-profiles/{profile_code}")
    assert "Depends(require_trust_write())" in inspect.getsource(
        entity_profiles_api.create_recruitment_profile_endpoint
    )
    assert "Depends(require_trust_write())" in inspect.getsource(
        entity_profiles_api.publish_recruitment_profile_revision_endpoint
    )

    forbidden = await client.post(
        CREATE_URL,
        headers=viewer_headers,
        json=_create_payload(),
    )
    assert forbidden.status_code == 403

    routed = await client.post(CREATE_URL, json={})
    assert routed.status_code in {401, 403}
