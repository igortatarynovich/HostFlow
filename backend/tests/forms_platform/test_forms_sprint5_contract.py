"""Forms Sprint 5 — normalized answer contract tests."""

from __future__ import annotations

from uuid import uuid4

import pytest

from backend.app.db.session import async_session_maker
from backend.app.forms_platform.adapter import commit_publish
from backend.app.forms_platform.answers import ANSWER_CONTRACT, build_normalized_answers
from backend.app.forms_platform.schema import build_field_schema_v1
from backend.app.forms_platform.validation import (
    shared_intake_payload_from_answers,
    validate_submission,
)
from backend.app.models.tenant_lead_form import TenantLeadForm
from backend.tests.conftest import _init_data


def _schema():
    return build_field_schema_v1(
        fields=[
            {"id": "candidate.first_name", "type": "text", "required": True},
            {"id": "candidate.email", "type": "email", "required": True},
            {"id": "candidate.phone", "type": "phone", "required": False},
            {"id": "candidate.age", "type": "integer", "required": False},
            {"id": "candidate.active", "type": "boolean", "required": False},
            {"id": "candidate.dob", "type": "date", "required": False},
            {"id": "candidate.score", "type": "number", "required": False},
        ]
    )


def test_forms_sprint5_canonical_normalization():
    schema = _schema()
    result = build_normalized_answers(
        schema=schema,
        raw_values={
            "candidate.first_name": "  Ada   Lovelace ",
            "candidate.email": "Ada@Example.COM",
            "candidate.phone": "+48 600 100-200",
            "candidate.age": "42",
            "candidate.active": "yes",
            "candidate.dob": "1990-05-01T12:00:00Z",
            "candidate.score": "3.5",
        },
        published_version=7,
        form_id="form-1",
    )
    assert result["ok"] is True
    assert result["answer_contract"] == ANSWER_CONTRACT
    assert result["published_version"] == 7
    assert result["form_id"] == "form-1"
    n = result["normalized_values"]
    assert n["candidate.first_name"] == "Ada Lovelace"
    assert n["candidate.email"] == "ada@example.com"
    assert n["candidate.phone"] == "+48600100200"
    assert n["candidate.age"] == 42
    assert n["candidate.active"] is True
    assert n["candidate.dob"] == "1990-05-01"
    assert n["candidate.score"] == 3.5
    assert result["raw_values"]["candidate.email"] == "Ada@Example.COM"


def test_forms_sprint5_error_contract_has_message_key():
    schema = _schema()
    result = validate_submission(
        schema,
        {"values": {"candidate.email": "x", "evil": 1}},
        published_version=2,
        form_id="f1",
    )
    assert result["ok"] is False
    codes = {e["code"] for e in result["errors"]}
    assert "forms_required_field_missing" in codes or "forms_field_type_invalid" in codes
    assert "forms_unknown_field" in codes
    for err in result["errors"]:
        assert "field_id" in err
        assert "code" in err
        assert "message_key" in err
        assert err["message_key"].startswith("forms.validation.")


def test_forms_sprint5_unknown_rejected_after_flat_extract():
    schema = _schema()
    result = validate_submission(
        schema,
        {
            "contacts": {"ignored": True},
            "values": {
                "candidate.first_name": "Ada",
                "candidate.email": "ada@example.com",
                "not.in.schema": "x",
            },
        },
    )
    assert result["ok"] is False
    assert "not.in.schema" in result["raw_values"]
    assert "not.in.schema" not in result["normalized_values"]
    assert any(e["code"] == "forms_unknown_field" for e in result["errors"])


def test_forms_sprint5_shared_intake_handoff_no_domain_mapping():
    schema = _schema()
    result = validate_submission(
        schema,
        {
            "values": {
                "candidate.first_name": "Ada",
                "candidate.email": "ada@example.com",
            }
        },
        published_version=3,
        form_id="form-xyz",
    )
    handoff = shared_intake_payload_from_answers(result)
    assert "presentation_values_v1" in handoff
    assert handoff["presentation_values_v1"]["candidate.email"] == "ada@example.com"
    meta = handoff["forms_answer_contract_v1"]
    assert meta["answer_contract"] == ANSWER_CONTRACT
    assert meta["published_version"] == 3
    assert meta["form_id"] == "form-xyz"
    assert meta["schema_contract"] == "forms.field_schema.v1"
    # No domain/entity keys
    assert "candidate_id" not in handoff
    assert "lead" not in handoff
    assert "application" not in handoff


@pytest.mark.asyncio
async def test_forms_sprint5_answers_carry_publication_version():
    data = await _init_data()
    tenant_id = data["tenant_id"]
    form_id = str(uuid4())
    async with async_session_maker() as session:
        session.add(
            TenantLeadForm(
                id=form_id,
                tenant_id=tenant_id,
                title="Sprint 5",
                public_slug=f"fs5-{form_id[:8]}",
                is_active=True,
                lifecycle_status="active",
                purpose="inquiry",
                published_version=1,
            )
        )
        await session.commit()

    async with async_session_maker() as session:
        pub = await commit_publish(
            session,
            tenant_id=tenant_id,
            form_id=form_id,
            fields=[
                {"id": "candidate.first_name", "type": "text", "required": True},
                {"id": "candidate.email", "type": "email", "required": True},
            ],
        )
        await session.commit()

    result = validate_submission(
        pub["field_schema"],
        {"values": {"candidate.first_name": "Ada", "candidate.email": "a@b.co"}},
        published_version=pub["published_version"],
        form_id=form_id,
    )
    assert result["ok"] is True
    assert result["published_version"] == pub["published_version"]
    assert result["form_id"] == form_id
    assert result["intake_handoff"]["forms_answer_contract_v1"]["published_version"] == pub[
        "published_version"
    ]
