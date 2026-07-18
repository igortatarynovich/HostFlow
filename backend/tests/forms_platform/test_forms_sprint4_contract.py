"""Forms Sprint 4 — field schema + validation contract tests."""

from __future__ import annotations

from uuid import uuid4

import pytest

from backend.app.db.session import async_session_maker
from backend.app.forms_platform.adapter import commit_publish, get_version_for_audit
from backend.app.forms_platform.schema import (
    FIELD_SCHEMA_CONTRACT,
    build_field_schema_v1,
)
from backend.app.forms_platform.validation import (
    validate_submission,
    validate_submission_against_publication,
)
from backend.app.models.tenant_lead_form import TenantLeadForm
from backend.tests.conftest import _init_data


def _sample_schema() -> dict:
    return build_field_schema_v1(
        fields=[
            {"id": "recruitment.candidate.first_name", "type": "text", "required": True},
            {"id": "recruitment.candidate.contacts.email", "type": "email", "required": False},
            {"id": "recruitment.candidate.age", "type": "integer", "required": False},
        ],
        entity_profile_code="recruitment.candidate",
    )


async def _seed_form(tenant_id: str) -> str:
    form_id = str(uuid4())
    async with async_session_maker() as session:
        session.add(
            TenantLeadForm(
                id=form_id,
                tenant_id=tenant_id,
                title="Sprint 4 Form",
                public_slug=f"fs4-{form_id[:8]}",
                is_active=True,
                lifecycle_status="active",
                purpose="inquiry",
                published_version=1,
                target_entity_profile_code="recruitment.candidate",
            )
        )
        await session.commit()
    return form_id


def test_forms_sprint4_validate_required_and_unknown():
    schema = _sample_schema()
    ok = validate_submission(
        schema,
        {"values": {"recruitment.candidate.first_name": "Ada"}},
    )
    assert ok["ok"] is True
    assert ok["compat_mode"] == "field_schema_v1"

    missing = validate_submission(schema, {"values": {}})
    assert missing["ok"] is False
    assert any(e["code"] == "forms_required_field_missing" for e in missing["errors"])

    unknown = validate_submission(
        schema,
        {
            "values": {
                "recruitment.candidate.first_name": "Ada",
                "evil.field": "x",
            }
        },
    )
    assert unknown["ok"] is False
    assert any(e["code"] == "forms_unknown_field" for e in unknown["errors"])
    assert "evil.field" not in unknown["normalized_values"]


def test_forms_sprint4_type_validation_and_pre_schema_compat():
    schema = _sample_schema()
    bad_email = validate_submission(
        schema,
        {
            "values": {
                "recruitment.candidate.first_name": "Ada",
                "recruitment.candidate.contacts.email": "not-an-email",
            }
        },
    )
    assert bad_email["ok"] is False
    assert any(e["code"] == "forms_field_type_invalid" for e in bad_email["errors"])

    legacy = validate_submission(None, {"values": {"anything": 1}})
    assert legacy["ok"] is True
    assert legacy["compat_mode"] == "pre_schema"


@pytest.mark.asyncio
async def test_forms_sprint4_schema_frozen_in_publication_version():
    data = await _init_data()
    tenant_id = data["tenant_id"]
    form_id = await _seed_form(tenant_id)

    async with async_session_maker() as session:
        pub = await commit_publish(
            session,
            tenant_id=tenant_id,
            form_id=form_id,
            fields=[
                {"id": "recruitment.candidate.first_name", "type": "text", "required": True},
                {"id": "recruitment.candidate.contacts.email", "type": "email", "required": False},
            ],
        )
        await session.commit()
        version = int(pub["published_version"])
        hist = await get_version_for_audit(
            session, tenant_id=tenant_id, form_id=form_id, version=version
        )

    assert pub["has_field_schema"] is True
    assert pub["field_schema"]["schema_contract"] == FIELD_SCHEMA_CONTRACT
    assert hist["snapshot"]["field_schema"]["schema_contract"] == FIELD_SCHEMA_CONTRACT

    # Live title change must not alter frozen schema in ledger
    async with async_session_maker() as session:
        form = await session.get(TenantLeadForm, form_id)
        form.title = "Mutated"
        await session.commit()
        hist2 = await get_version_for_audit(
            session, tenant_id=tenant_id, form_id=form_id, version=version
        )
    assert hist2["snapshot"]["field_schema"] == hist["snapshot"]["field_schema"]
    assert hist2["snapshot"]["title"] == "Sprint 4 Form"

    # Version-specific validation uses frozen schema
    result = validate_submission_against_publication(
        hist2["snapshot"],
        {"values": {"recruitment.candidate.first_name": "Ada"}},
    )
    assert result["ok"] is True
    assert result["published_version"] == version

    # New publish with different schema — old version still validates old rules
    async with async_session_maker() as session:
        await commit_publish(
            session,
            tenant_id=tenant_id,
            form_id=form_id,
            fields=[{"id": "only.new.field", "type": "text", "required": True}],
        )
        await session.commit()
        old = await get_version_for_audit(
            session, tenant_id=tenant_id, form_id=form_id, version=version
        )
    old_check = validate_submission_against_publication(
        old["snapshot"],
        {"values": {"only.new.field": "x"}},
    )
    assert old_check["ok"] is False
    assert any(e["code"] == "forms_unknown_field" for e in old_check["errors"])


def test_forms_sprint4_no_dynamic_code_in_schema_module():
    from pathlib import Path

    root = Path(__file__).resolve().parents[3]
    for rel in (
        "backend/app/forms_platform/schema.py",
        "backend/app/forms_platform/validation.py",
    ):
        text = (root / rel).read_text(encoding="utf-8")
        assert "eval(" not in text
        assert "exec(" not in text
        assert "__import__(" not in text
        assert "importlib" not in text
