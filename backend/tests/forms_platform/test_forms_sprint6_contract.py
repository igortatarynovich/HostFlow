"""Forms Sprint 6 — submission envelope persistence contract tests."""

from __future__ import annotations

from uuid import uuid4

import pytest

from backend.app.db.session import async_session_maker
from backend.app.forms_platform.adapter import commit_publish
from backend.app.forms_platform.errors import FormsEnvelopeNotFoundError
from backend.app.forms_platform.submission_envelope import (
    get_submission_envelope,
    list_submission_envelopes,
    persist_submission_envelope,
    set_envelope_processing_status,
)
from backend.app.forms_platform.validation import validate_submission
from backend.app.models.form_submission_envelope import (
    STATUS_ACCEPTED,
    STATUS_HANDED_OFF,
    STATUS_REJECTED,
)
from backend.app.models.tenant_lead_form import TenantLeadForm
from backend.tests.conftest import _init_data


async def _seed_published(tenant_id: str) -> tuple[str, dict]:
    form_id = str(uuid4())
    async with async_session_maker() as session:
        session.add(
            TenantLeadForm(
                id=form_id,
                tenant_id=tenant_id,
                title="Sprint 6 Form",
                public_slug=f"fs6-{form_id[:8]}",
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
                {"id": "n.first", "type": "text", "required": True},
                {"id": "n.email", "type": "email", "required": True},
            ],
        )
        await session.commit()
    return form_id, pub


@pytest.mark.asyncio
async def test_forms_sprint6_persist_accepted_envelope_and_audit():
    data = await _init_data()
    tenant_id = data["tenant_id"]
    form_id, pub = await _seed_published(tenant_id)
    answer = validate_submission(
        pub["field_schema"],
        {"values": {"n.first": "Ada", "n.email": "Ada@Example.COM"}},
        published_version=pub["published_version"],
        form_id=form_id,
    )
    assert answer["ok"] is True

    async with async_session_maker() as session:
        env = await persist_submission_envelope(
            session,
            tenant_id=tenant_id,
            form_id=form_id,
            answer=answer,
            idempotency_key="idem-1",
        )
        await session.commit()
        got = await get_submission_envelope(session, tenant_id=tenant_id, envelope_id=env["id"])
        listed = await list_submission_envelopes(session, tenant_id=tenant_id, form_id=form_id)

    assert env["processing_status"] == STATUS_ACCEPTED
    assert env["content_immutable"] is True
    assert env["published_version"] == pub["published_version"]
    assert env["schema_contract"] == "forms.field_schema.v1"
    assert env["answer_contract"] == "forms.normalized_answers.v1"
    assert env["normalized_values"]["n.email"] == "ada@example.com"
    assert env["raw_values"]["n.email"] == "Ada@Example.COM"
    assert got["id"] == env["id"]
    assert len(listed) == 1


@pytest.mark.asyncio
async def test_forms_sprint6_idempotent_persist_and_rejected_status():
    data = await _init_data()
    tenant_id = data["tenant_id"]
    form_id, pub = await _seed_published(tenant_id)
    key = f"idem-{uuid4().hex[:8]}"
    good = validate_submission(
        pub["field_schema"],
        {"values": {"n.first": "Ada", "n.email": "a@b.co"}},
        published_version=pub["published_version"],
        form_id=form_id,
    )
    async with async_session_maker() as session:
        first = await persist_submission_envelope(
            session, tenant_id=tenant_id, form_id=form_id, answer=good, idempotency_key=key
        )
        await session.commit()
    async with async_session_maker() as session:
        second = await persist_submission_envelope(
            session, tenant_id=tenant_id, form_id=form_id, answer=good, idempotency_key=key
        )
        await session.commit()
        listed = await list_submission_envelopes(session, tenant_id=tenant_id, form_id=form_id)
    assert second.get("idempotent_replay") is True
    assert second["id"] == first["id"]
    assert len(listed) == 1

    bad = validate_submission(
        pub["field_schema"],
        {"values": {"n.email": "nope"}},
        published_version=pub["published_version"],
        form_id=form_id,
    )
    async with async_session_maker() as session:
        rejected = await persist_submission_envelope(
            session, tenant_id=tenant_id, form_id=form_id, answer=bad
        )
        await session.commit()
    assert rejected["processing_status"] == STATUS_REJECTED
    assert rejected["errors"]


@pytest.mark.asyncio
async def test_forms_sprint6_status_mutable_content_tenant_isolation():
    data = await _init_data()
    tenant_id = data["tenant_id"]
    form_id, pub = await _seed_published(tenant_id)
    answer = validate_submission(
        pub["field_schema"],
        {"values": {"n.first": "Ada", "n.email": "a@b.co"}},
        published_version=pub["published_version"],
        form_id=form_id,
    )
    async with async_session_maker() as session:
        env = await persist_submission_envelope(
            session, tenant_id=tenant_id, form_id=form_id, answer=answer
        )
        updated = await set_envelope_processing_status(
            session,
            tenant_id=tenant_id,
            envelope_id=env["id"],
            status=STATUS_HANDED_OFF,
        )
        await session.commit()
    assert updated["processing_status"] == STATUS_HANDED_OFF
    assert updated["normalized_values"] == env["normalized_values"]

    other = str(uuid4())
    async with async_session_maker() as session:
        with pytest.raises(FormsEnvelopeNotFoundError):
            await get_submission_envelope(session, tenant_id=other, envelope_id=env["id"])
