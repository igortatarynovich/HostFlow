"""ADR-043 Step 7B.1 canonical Document Type Version authoring catalog."""

from __future__ import annotations

import inspect
import uuid
from datetime import date, timedelta

from httpx import AsyncClient
import pytest
from sqlalchemy import func, select

from backend.app.api.v1.platform import document_type_versions as catalog_api
from backend.app.models.document_type import DocumentType
from backend.app.models.ref_document_type import (
    RefDocumentType,
    RefDocumentTypeVersion,
)


CATALOG_URL = "/api/v1/platform/reference/document-type-versions"


async def _make_type(
    db,
    *,
    code: str,
    status: str = "active",
) -> RefDocumentType:
    row = RefDocumentType(
        id=str(uuid.uuid4()),
        code=code,
        public_name=f"Public {code}",
        description=f"Description {code}",
        status=status,
        origin="system",
        category_code="identity",
        subcategory_code="identity_primary",
        criticality="informational",
    )
    db.add(row)
    await db.flush()
    return row


async def _make_version(
    db,
    *,
    document_type_id: str,
    version_code: str,
    valid_from: date,
    valid_to: date | None = None,
    status_model: str = "evidence",
) -> RefDocumentTypeVersion:
    row = RefDocumentTypeVersion(
        id=str(uuid.uuid4()),
        document_type_id=document_type_id,
        version_code=version_code,
        valid_from=valid_from,
        valid_to=valid_to,
        schema_json={},
        expiry_rules_json={},
        automation_flags_json={},
        verification_profile_json={},
        stage_applicability_json={},
        position_applicability_json={},
        entity_applicability_json={},
        business_purposes_json={},
        status_model=status_model,
    )
    db.add(row)
    await db.flush()
    return row


@pytest.mark.anyio
async def test_catalog_returns_canonical_identity_and_deterministic_current_version(
    client: AsyncClient,
    db,
    manager_headers: dict[str, str],
) -> None:
    today = date.today()
    prefix = f"step7b1_{uuid.uuid4().hex[:8]}"
    first_type = await _make_type(db, code=f"{prefix}_a")
    older = await _make_version(
        db,
        document_type_id=first_type.id,
        version_code="v1",
        valid_from=today - timedelta(days=100),
    )
    current = await _make_version(
        db,
        document_type_id=first_type.id,
        version_code="v2",
        valid_from=today - timedelta(days=10),
        status_model="verification",
    )
    await _make_version(
        db,
        document_type_id=first_type.id,
        version_code="v3",
        valid_from=today + timedelta(days=10),
    )
    second_type = await _make_type(db, code=f"{prefix}_b")
    second_current = await _make_version(
        db,
        document_type_id=second_type.id,
        version_code="v1",
        valid_from=today,
        valid_to=today,
    )
    await db.commit()

    response = await client.get(CATALOG_URL, headers=manager_headers)

    assert response.status_code == 200, response.text
    items = [
        item
        for item in response.json()["items"]
        if item["document_type_code"].startswith(prefix)
    ]
    assert [item["document_type_code"] for item in items] == [
        first_type.code,
        second_type.code,
    ]
    assert items[0] == {
        "document_type_id": first_type.id,
        "document_type_code": first_type.code,
        "public_name": first_type.public_name,
        "description": first_type.description,
        "category_code": first_type.category_code,
        "subcategory_code": first_type.subcategory_code,
        "document_type_status": "active",
        "document_type_version_id": current.id,
        "version_code": "v2",
        "valid_from": current.valid_from.isoformat(),
        "valid_to": None,
        "status_model": "verification",
        "deprecation_reason": None,
    }
    assert items[0]["document_type_version_id"] != older.id
    assert items[1]["document_type_version_id"] == second_current.id


@pytest.mark.anyio
async def test_catalog_excludes_nonselectable_or_noncurrent_rows_and_legacy_authority(
    client: AsyncClient,
    db,
    tenant_id: str,
    manager_headers: dict[str, str],
) -> None:
    today = date.today()
    prefix = f"step7b1_state_{uuid.uuid4().hex[:8]}"
    for status in ("deprecated", "draft"):
        document_type = await _make_type(db, code=f"{prefix}_{status}", status=status)
        await _make_version(
            db,
            document_type_id=document_type.id,
            version_code="v1",
            valid_from=today - timedelta(days=1),
        )
    expired_type = await _make_type(db, code=f"{prefix}_expired")
    await _make_version(
        db,
        document_type_id=expired_type.id,
        version_code="v1",
        valid_from=today - timedelta(days=20),
        valid_to=today - timedelta(days=1),
    )
    legacy_code = f"{prefix}_legacy_only"
    db.add(
        DocumentType(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            code=legacy_code,
            name="Legacy-only document type",
        )
    )
    await db.commit()

    before_types = await db.scalar(select(func.count()).select_from(RefDocumentType))
    before_versions = await db.scalar(
        select(func.count()).select_from(RefDocumentTypeVersion)
    )
    response = await client.get(CATALOG_URL, headers=manager_headers)
    after_types = await db.scalar(select(func.count()).select_from(RefDocumentType))
    after_versions = await db.scalar(
        select(func.count()).select_from(RefDocumentTypeVersion)
    )

    assert response.status_code == 200, response.text
    returned_codes = {
        item["document_type_code"] for item in response.json()["items"]
    }
    assert not any(code.startswith(prefix) for code in returned_codes)
    assert legacy_code not in returned_codes
    assert (after_types, after_versions) == (before_types, before_versions)
    source = inspect.getsource(catalog_api)
    assert "backend.app.models.document_type" not in source
    assert ".commit(" not in source
    assert ".add(" not in source


@pytest.mark.anyio
async def test_catalog_enforces_platform_read_permission(
    client: AsyncClient,
    viewer_headers: dict[str, str],
) -> None:
    allowed = await client.get(CATALOG_URL, headers=viewer_headers)
    unauthenticated = await client.get(CATALOG_URL)

    assert allowed.status_code == 200, allowed.text
    assert unauthenticated.status_code in {401, 403}
    assert "Depends(require_trust_read())" in inspect.getsource(
        catalog_api.list_current_document_type_versions
    )
