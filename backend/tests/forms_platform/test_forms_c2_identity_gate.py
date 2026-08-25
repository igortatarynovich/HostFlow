"""Forms Platform C2 — Contract Identity Gate.

Identity on publication versions; canonical hash; immutability; fail-closed backfill.
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from backend.app.forms_platform.canonical import canonical_jcs, schema_hash_sha256
from backend.app.forms_platform.compatibility import COMPATIBLE_TUPLES, assert_compatible_tuple
from backend.app.forms_platform.constants import (
    ADAPTER_ID,
    LIFECYCLE_ARCHIVED,
    OBJECT_KIND_PUBLICATION_VERSION,
    PUBLIC_CONTRACT_ID,
    PUBLIC_CONTRACT_VERSION,
)
from backend.app.forms_platform.contract_identity import (
    IDENTITY_KEYS,
    backfill_snapshot_identity,
    forbid_identity_or_schema_mutation,
    freeze_contract_identity,
    identity_from_snapshot,
    reconstruct_contract_identity,
)
from backend.app.forms_platform.errors import (
    FormsIdentityIncompatibleError,
    FormsIdentityUnreconstructableError,
    FormsPublicationVersionImmutableError,
    FormsSchemaHashMismatchError,
    FormsVersionNotFoundError,
)
from backend.app.forms_platform.schema import build_field_schema_v1


def test_c2_schema_hash_independent_of_key_order() -> None:
    a = {"schema_contract": "forms.field_schema.v1", "fields": [{"id": "a", "type": "text", "required": True}]}
    b = {"fields": [{"required": True, "type": "text", "id": "a"}], "schema_contract": "forms.field_schema.v1"}
    assert canonical_jcs(a) == canonical_jcs(b)
    assert schema_hash_sha256(a) == schema_hash_sha256(b)
    assert len(schema_hash_sha256(a)) == 64


def test_c2_identity_excludes_lifecycle_and_requires_declared_tuple() -> None:
    schema = build_field_schema_v1(fields=[{"id": "n.first", "type": "text", "required": True}])
    identity = freeze_contract_identity(schema)
    assert set(identity.to_dict()) == set(IDENTITY_KEYS)
    assert "lifecycle_status" not in identity.to_dict()
    assert identity.contract_id == PUBLIC_CONTRACT_ID
    assert identity.public_contract_version == PUBLIC_CONTRACT_VERSION
    assert identity.adapter_version == ADAPTER_ID
    assert identity.object_kind == OBJECT_KIND_PUBLICATION_VERSION
    assert identity.schema_hash == schema_hash_sha256(schema)
    assert_compatible_tuple(
        manifest_version=identity.manifest_version,
        public_contract_version=identity.public_contract_version,
        adapter_version=identity.adapter_version,
    )
    assert len(COMPATIBLE_TUPLES) >= 1


def test_c2_hash_mismatch_and_undeclared_tuple_fail_closed() -> None:
    schema = build_field_schema_v1(fields=[{"id": "n.first", "type": "text", "required": True}])
    identity = freeze_contract_identity(schema)
    other = build_field_schema_v1(fields=[{"id": "n.other", "type": "text", "required": True}])
    with pytest.raises(FormsSchemaHashMismatchError):
        identity_from_snapshot(
            {"field_schema": other, "contract_identity": identity.to_dict()}
        )
    with pytest.raises(FormsIdentityIncompatibleError):
        assert_compatible_tuple(
            manifest_version="9.9.9",
            public_contract_version="v9",
            adapter_version=ADAPTER_ID,
        )


def test_c2_legacy_without_schema_is_unreconstructable() -> None:
    with pytest.raises(FormsIdentityUnreconstructableError):
        reconstruct_contract_identity({"title": "old", "immutable": True})
    with pytest.raises(FormsIdentityUnreconstructableError):
        backfill_snapshot_identity({"title": "old"})


def test_c2_backfill_reconstructs_when_schema_frozen() -> None:
    schema = build_field_schema_v1(fields=[{"id": "n.first", "type": "text", "required": True}])
    snap, wrote = backfill_snapshot_identity({"field_schema": schema, "title": "legacy"})
    assert wrote is True
    assert set(snap["contract_identity"]) == set(IDENTITY_KEYS)
    again, wrote2 = backfill_snapshot_identity(snap)
    assert wrote2 is False
    assert again["contract_identity"] == snap["contract_identity"]


def test_c2_forbid_schema_identity_mutation() -> None:
    schema = build_field_schema_v1(fields=[{"id": "n.first", "type": "text", "required": True}])
    identity = freeze_contract_identity(schema)
    stored = {"field_schema": schema, "contract_identity": identity.to_dict()}
    forbid_identity_or_schema_mutation(stored=stored, attempted=dict(stored))
    mutated = {"field_schema": schema, "contract_identity": {**identity.to_dict(), "schema_hash": "0" * 64}}
    with pytest.raises(FormsPublicationVersionImmutableError):
        forbid_identity_or_schema_mutation(stored=stored, attempted=mutated)


@pytest.mark.asyncio
async def test_c2_publish_resolve_submit_bind_frozen_version() -> None:
    from backend.app.db.session import async_session_maker
    from backend.app.forms_platform.adapter import (
        commit_publish,
        resolve_publication,
        submission_entry,
    )
    from backend.app.forms_platform.publication_versions import replace_publication_snapshot
    from backend.app.forms_platform.submission_envelope import persist_submission_envelope
    from backend.app.forms_platform.validation import validate_submission
    from backend.app.models.tenant_lead_form import TenantLeadForm
    from backend.tests.conftest import _init_data

    data = await _init_data()
    tenant_id = data["tenant_id"]
    form_id = str(uuid4())
    async with async_session_maker() as session:
        session.add(
            TenantLeadForm(
                id=form_id,
                tenant_id=tenant_id,
                title="C2 Form",
                public_slug=f"c2-{form_id[:8]}",
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
            fields=[{"id": "n.first", "type": "text", "required": True}],
        )
        await session.commit()

    identity = pub["contract_identity"]
    assert identity["object_kind"] == OBJECT_KIND_PUBLICATION_VERSION
    assert "lifecycle_status" not in identity
    assert pub["lifecycle_status"] == "active"
    pinned = int(pub["published_version"])

    async with async_session_maker() as session:
        by_version = await resolve_publication(
            session, tenant_id=tenant_id, form_id=form_id, version=pinned
        )
        assert by_version["contract_identity"] == identity
        entry = submission_entry(by_version)
        assert entry["publication_version_pin"]["version"] == pinned
        assert entry["contract_identity"] == identity
        with pytest.raises(FormsVersionNotFoundError):
            await resolve_publication(
                session, tenant_id=tenant_id, form_id=form_id, version=pinned + 10
            )
        with pytest.raises(FormsPublicationVersionImmutableError):
            await replace_publication_snapshot(
                session,
                tenant_id=tenant_id,
                form_id=form_id,
                version=pinned,
                snapshot={"field_schema": {"schema_contract": "mutated"}},
            )

        answer = validate_submission(
            pub["field_schema"],
            {"values": {"n.first": "Ada"}},
            published_version=pinned,
            form_id=form_id,
        )
        env = await persist_submission_envelope(
            session, tenant_id=tenant_id, form_id=form_id, answer=answer
        )
        await session.commit()
    assert env["publication_version_pin"]["version"] == pinned
    assert env["contract_identity"] == identity

    async with async_session_maker() as session:
        form = await session.get(TenantLeadForm, form_id)
        form.lifecycle_status = LIFECYCLE_ARCHIVED
        await session.commit()
    async with async_session_maker() as session:
        from backend.app.forms_platform.errors import FormsArchivedError

        with pytest.raises(FormsArchivedError):
            await persist_submission_envelope(
                session, tenant_id=tenant_id, form_id=form_id, answer=answer
            )


@pytest.mark.asyncio
async def test_c2_backfill_legacy_snapshot_or_fail_close() -> None:
    from backend.app.db.session import async_session_maker
    from backend.app.forms_platform.publication_versions import (
        append_publication_version,
        backfill_publication_version_identity,
    )
    from backend.app.models.tenant_lead_form import TenantLeadForm
    from backend.app.models.mixins import now_utc
    from backend.tests.conftest import _init_data

    data = await _init_data()
    tenant_id = data["tenant_id"]
    form_id = str(uuid4())
    schema = build_field_schema_v1(fields=[{"id": "n.first", "type": "text", "required": True}])
    async with async_session_maker() as session:
        session.add(
            TenantLeadForm(
                id=form_id,
                tenant_id=tenant_id,
                title="Legacy C2",
                public_slug=f"c2l-{form_id[:8]}",
                is_active=True,
                lifecycle_status="active",
                purpose="inquiry",
                published_version=1,
            )
        )
        await session.commit()

    async with async_session_maker() as session:
        await append_publication_version(
            session,
            tenant_id=tenant_id,
            form_id=form_id,
            version=2,
            snapshot={"title": "no schema", "immutable": True},
            consent_pin={},
            idempotency_key=None,
            published_at=now_utc(),
        )
        await append_publication_version(
            session,
            tenant_id=tenant_id,
            form_id=form_id,
            version=3,
            snapshot={"title": "has schema", "field_schema": schema, "immutable": True},
            consent_pin={},
            idempotency_key=None,
            published_at=now_utc(),
        )
        await session.commit()

    async with async_session_maker() as session:
        with pytest.raises(FormsIdentityUnreconstructableError):
            await backfill_publication_version_identity(
                session, tenant_id=tenant_id, form_id=form_id, version=2
            )
        filled = await backfill_publication_version_identity(
            session, tenant_id=tenant_id, form_id=form_id, version=3
        )
        await session.commit()
    assert filled["backfilled"] is True
    assert filled["contract_identity"]["schema_hash"] == schema_hash_sha256(schema)
    assert filled["contract_identity"]["adapter_version"] == ADAPTER_ID
