"""Forms Sprint 2 — runtime contract hardening tests.

publish lifecycle · activate/deactivate · stale version · idempotent resolve
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from backend.app.db.session import async_session_maker
from backend.app.forms_platform.adapter import (
    activate_endpoint,
    assert_submission_version_compatible,
    commit_publish,
    deactivate_endpoint,
    endpoint_from_publication,
    resolve_publication,
    submission_entry,
)
from backend.app.forms_platform.errors import (
    FormsInactiveError,
    FormsNotFoundError,
    FormsStaleVersionError,
)
from backend.app.models.tenant_lead_form import TenantLeadForm
from backend.tests.conftest import _init_data


async def _seed_form(tenant_id: str, *, slug: str | None = None) -> str:
    form_id = str(uuid4())
    async with async_session_maker() as session:
        session.add(
            TenantLeadForm(
                id=form_id,
                tenant_id=tenant_id,
                title="Sprint 2 Form",
                public_slug=slug or f"fs2-{form_id[:8]}",
                is_active=True,
                lifecycle_status="active",
                purpose="inquiry",
                published_version=1,
            )
        )
        await session.commit()
    return form_id


@pytest.mark.asyncio
async def test_forms_sprint2_commit_publish_freezes_immutable_snapshot():
    data = await _init_data()
    tenant_id = data["tenant_id"]
    form_id = await _seed_form(tenant_id)

    async with async_session_maker() as session:
        first = await commit_publish(
            session,
            tenant_id=tenant_id,
            form_id=form_id,
            terms_version="terms_2026_07",
            privacy_version="privacy_2026_07",
        )
        await session.commit()

    assert first["published_version"] == 2
    assert first["has_immutable_snapshot"] is True
    assert first["consent_pin"]["terms_version"] == "terms_2026_07"
    assert first["consent_pin"]["privacy_version"] == "privacy_2026_07"
    assert first["is_active"] is True

    async with async_session_maker() as session:
        form = await session.get(TenantLeadForm, form_id)
        assert form is not None
        snap = form.published_snapshot_v1 or {}
        assert snap["immutable"] is True
        assert snap["published_version"] == 2
        # Mutating live title must not rewrite frozen snapshot
        form.title = "Mutated live title"
        await session.commit()

    async with async_session_maker() as session:
        resolved = await resolve_publication(session, tenant_id=tenant_id, form_id=form_id)
        form = await session.get(TenantLeadForm, form_id)
        assert form.title == "Mutated live title"
        assert (form.published_snapshot_v1 or {})["title"] == "Sprint 2 Form"
        assert resolved["published_version"] == 2


@pytest.mark.asyncio
async def test_forms_sprint2_idempotent_resolve_and_deactivate_reactivate():
    data = await _init_data()
    tenant_id = data["tenant_id"]
    form_id = await _seed_form(tenant_id)

    async with async_session_maker() as session:
        a = await resolve_publication(session, tenant_id=tenant_id, form_id=form_id)
        b = await resolve_publication(session, tenant_id=tenant_id, form_id=form_id)
        assert a == b

        await commit_publish(session, tenant_id=tenant_id, form_id=form_id)
        await session.commit()

    async with async_session_maker() as session:
        inactive = await deactivate_endpoint(session, tenant_id=tenant_id, form_id=form_id)
        await session.commit()
    assert inactive["is_active"] is False

    async with async_session_maker() as session:
        with pytest.raises(FormsInactiveError) as exc:
            await resolve_publication(
                session, tenant_id=tenant_id, form_id=form_id, require_active=True
            )
        assert exc.value.code == "forms_endpoint_inactive"

        with pytest.raises(FormsInactiveError):
            endpoint_from_publication(inactive)

        with pytest.raises(FormsInactiveError):
            submission_entry(inactive)

        active = await activate_endpoint(session, tenant_id=tenant_id, form_id=form_id)
        await session.commit()
    assert active["is_active"] is True
    endpoint = endpoint_from_publication(active)
    assert endpoint.published_version >= 2


@pytest.mark.asyncio
async def test_forms_sprint2_stale_published_version_rejected():
    data = await _init_data()
    tenant_id = data["tenant_id"]
    form_id = await _seed_form(tenant_id)

    async with async_session_maker() as session:
        pub = await commit_publish(session, tenant_id=tenant_id, form_id=form_id)
        await session.commit()

    pinned = int(pub["published_version"])
    assert_submission_version_compatible(pub, client_published_version=pinned)

    with pytest.raises(FormsStaleVersionError) as exc:
        assert_submission_version_compatible(pub, client_published_version=pinned - 1)
    assert exc.value.code == "forms_stale_published_version"

    with pytest.raises(FormsStaleVersionError):
        assert_submission_version_compatible(pub, client_published_version=None)


@pytest.mark.asyncio
async def test_forms_sprint2_tenant_isolation_on_resolve():
    data = await _init_data()
    tenant_id = data["tenant_id"]
    form_id = await _seed_form(tenant_id)

    other_tenant = str(uuid4())
    async with async_session_maker() as session:
        with pytest.raises(FormsNotFoundError):
            await resolve_publication(session, tenant_id=other_tenant, form_id=form_id)


@pytest.mark.asyncio
async def test_forms_sprint2_second_publish_bumps_version_new_snapshot():
    data = await _init_data()
    tenant_id = data["tenant_id"]
    form_id = await _seed_form(tenant_id)

    async with async_session_maker() as session:
        v2 = await commit_publish(
            session, tenant_id=tenant_id, form_id=form_id, terms_version="t1"
        )
        await session.commit()
    assert v2["published_version"] == 2

    async with async_session_maker() as session:
        form = await session.get(TenantLeadForm, form_id)
        form.title = "Prep for v3"
        await session.commit()

    async with async_session_maker() as session:
        v3 = await commit_publish(
            session, tenant_id=tenant_id, form_id=form_id, terms_version="t2"
        )
        await session.commit()
        form = await session.get(TenantLeadForm, form_id)

    assert v3["published_version"] == 3
    assert (form.published_snapshot_v1 or {})["title"] == "Prep for v3"
    assert (form.published_snapshot_v1 or {})["consent_pin"]["terms_version"] == "t2"
