"""Forms Sprint 3 — publication version ledger contract tests."""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import select

from backend.app.db.session import async_session_maker
from backend.app.forms_platform.adapter import (
    commit_publish,
    get_version_for_audit,
    list_versions_for_audit,
    pin_submission_to_publication_version,
    resolve_publication,
    submission_entry,
)
from backend.app.forms_platform.errors import (
    FormsNotFoundError,
    FormsVersionPinnedError,
)
from backend.app.forms_platform.publication_versions import delete_publication_version
from backend.app.models.form_publication_version import FormPublicationVersion
from backend.app.models.tenant_lead_form import TenantLeadForm
from backend.tests.conftest import _init_data


async def _seed_form(tenant_id: str) -> str:
    form_id = str(uuid4())
    async with async_session_maker() as session:
        session.add(
            TenantLeadForm(
                id=form_id,
                tenant_id=tenant_id,
                title="Sprint 3 Form",
                public_slug=f"fs3-{form_id[:8]}",
                is_active=True,
                lifecycle_status="active",
                purpose="inquiry",
                published_version=1,
            )
        )
        await session.commit()
    return form_id


@pytest.mark.asyncio
async def test_forms_sprint3_commit_publish_appends_ledger():
    data = await _init_data()
    tenant_id = data["tenant_id"]
    form_id = await _seed_form(tenant_id)

    async with async_session_maker() as session:
        v2 = await commit_publish(session, tenant_id=tenant_id, form_id=form_id)
        await session.commit()
    assert v2["published_version"] == 2

    async with async_session_maker() as session:
        form = await session.get(TenantLeadForm, form_id)
        form.title = "Prep v3"
        await session.commit()

    async with async_session_maker() as session:
        v3 = await commit_publish(
            session, tenant_id=tenant_id, form_id=form_id, terms_version="t3"
        )
        await session.commit()
        versions = await list_versions_for_audit(
            session, tenant_id=tenant_id, form_id=form_id
        )
        hist_v2 = await get_version_for_audit(
            session, tenant_id=tenant_id, form_id=form_id, version=2
        )

    assert v3["published_version"] == 3
    assert [v["version"] for v in versions] == [2, 3]
    assert hist_v2["snapshot"]["title"] == "Sprint 3 Form"
    assert hist_v2["immutable"] is True
    assert hist_v2["audit_read_only"] is True
    # Current pointer denormalized — not full history
    async with async_session_maker() as session:
        form = await session.get(TenantLeadForm, form_id)
        assert form.published_version == 3
        assert (form.published_snapshot_v1 or {})["title"] == "Prep v3"


@pytest.mark.asyncio
async def test_forms_sprint3_idempotent_publish():
    data = await _init_data()
    tenant_id = data["tenant_id"]
    form_id = await _seed_form(tenant_id)
    key = f"idem-{uuid4().hex[:12]}"

    async with async_session_maker() as session:
        first = await commit_publish(
            session, tenant_id=tenant_id, form_id=form_id, idempotency_key=key
        )
        await session.commit()
    assert first["published_version"] == 2

    async with async_session_maker() as session:
        second = await commit_publish(
            session, tenant_id=tenant_id, form_id=form_id, idempotency_key=key
        )
        await session.commit()
        rows = (
            await session.scalars(
                select(FormPublicationVersion).where(
                    FormPublicationVersion.form_id == form_id
                )
            )
        ).all()

    assert second.get("idempotent_replay") is True
    assert second["replayed_version"] == 2
    assert len(rows) == 1
    assert first["published_version"] == second["published_version"]


@pytest.mark.asyncio
async def test_forms_sprint3_pinned_version_cannot_be_deleted():
    data = await _init_data()
    tenant_id = data["tenant_id"]
    form_id = await _seed_form(tenant_id)

    async with async_session_maker() as session:
        pub = await commit_publish(session, tenant_id=tenant_id, form_id=form_id)
        await session.commit()
    version = int(pub["published_version"])

    async with async_session_maker() as session:
        # Publish again so current pointer moves — older version becomes deletable only if unpinned
        await commit_publish(session, tenant_id=tenant_id, form_id=form_id)
        await pin_submission_to_publication_version(
            session, tenant_id=tenant_id, form_id=form_id, published_version=version
        )
        await session.commit()

    async with async_session_maker() as session:
        with pytest.raises(FormsVersionPinnedError) as exc:
            await delete_publication_version(
                session, tenant_id=tenant_id, form_id=form_id, version=version
            )
        assert exc.value.code == "forms_publication_version_pinned"


@pytest.mark.asyncio
async def test_forms_sprint3_tenant_isolation_on_ledger():
    data = await _init_data()
    tenant_id = data["tenant_id"]
    form_id = await _seed_form(tenant_id)

    async with async_session_maker() as session:
        await commit_publish(session, tenant_id=tenant_id, form_id=form_id)
        await session.commit()

    other = str(uuid4())
    async with async_session_maker() as session:
        with pytest.raises(FormsNotFoundError):
            await list_versions_for_audit(session, tenant_id=other, form_id=form_id)


@pytest.mark.asyncio
async def test_forms_sprint3_submission_entry_pins_ledger_version():
    data = await _init_data()
    tenant_id = data["tenant_id"]
    form_id = await _seed_form(tenant_id)

    async with async_session_maker() as session:
        pub = await commit_publish(session, tenant_id=tenant_id, form_id=form_id)
        await session.commit()

    entry = submission_entry(pub)
    assert entry["publication_version_pin"]["version"] == pub["published_version"]
    assert entry["publication_version_pin"]["form_id"] == form_id
