"""Forms Product Layer P2.4 — Draft Persistence contract tests."""

from __future__ import annotations

import pytest

from backend.app.forms_platform.builder import (
    BUILDER_COMPOSITION_CONTRACT,
    BUILDER_DRAFT_PERSISTENCE_CONTRACT,
    InMemoryDraftStore,
    add_instance,
    build_composition,
    build_instance,
)
from backend.app.forms_platform.errors import (
    FormsBuilderDraftArchivedError,
    FormsBuilderDraftConflictError,
    FormsBuilderDraftNotFoundError,
    FormsBuilderCompositionInvalidError,
)
from backend.app.forms_platform.field_catalog import (
    FieldCatalogRegistry,
    register_standard_library,
)


def _registry() -> FieldCatalogRegistry:
    registry = FieldCatalogRegistry()
    register_standard_library(registry)
    return registry


def _draft(registry: FieldCatalogRegistry, draft_id: str = "draft-a"):
    empty = build_composition(draft_id=draft_id, instances=[], registry=registry)
    return add_instance(
        empty,
        component_id="forms.field.text",
        component_version="1.0.0",
        config={"label": "A"},
        instance_id="i1",
        registry=registry,
    )


def test_forms_p2_4_persistence_contract_id():
    assert BUILDER_DRAFT_PERSISTENCE_CONTRACT == "forms.builder.draft_persistence.v1"


def test_forms_p2_4_create_get_preserves_composition_contract():
    registry = _registry()
    store = InMemoryDraftStore()
    composition = _draft(registry)
    record = store.create(tenant_id="t1", composition=composition, registry=registry)
    assert record.revision == 1
    assert record.status == "active"
    assert record.composition_contract == BUILDER_COMPOSITION_CONTRACT
    assert record.composition["contract"] == BUILDER_COMPOSITION_CONTRACT
    assert record.composition["draft_id"] == composition.draft_id
    assert "source" not in record.composition
    got = store.get(tenant_id="t1", draft_id=composition.draft_id)
    assert got.composition == record.composition
    assert got.composition_model().instance_order() == ("i1",)


def test_forms_p2_4_tenant_isolation():
    registry = _registry()
    store = InMemoryDraftStore()
    composition = _draft(registry, "shared-id")
    store.create(tenant_id="t1", composition=composition, registry=registry)
    with pytest.raises(FormsBuilderDraftNotFoundError):
        store.get(tenant_id="t2", draft_id="shared-id")
    other = _draft(registry, "shared-id")
    store.create(tenant_id="t2", composition=other, registry=registry)
    assert store.get(tenant_id="t1", draft_id="shared-id").tenant_id == "t1"
    assert store.get(tenant_id="t2", draft_id="shared-id").tenant_id == "t2"


def test_forms_p2_4_update_requires_expected_revision():
    registry = _registry()
    store = InMemoryDraftStore()
    composition = _draft(registry)
    tip = store.create(tenant_id="t1", composition=composition, registry=registry)
    next_comp = add_instance(
        composition,
        component_id="forms.field.email",
        component_version="1.0.0",
        config={"label": "E"},
        instance_id="i2",
        registry=registry,
    )
    with pytest.raises(FormsBuilderDraftConflictError) as exc:
        store.update(
            tenant_id="t1",
            draft_id=tip.draft_id,
            composition=next_comp,
            expected_revision=99,
            registry=registry,
        )
    assert exc.value.code == "forms_builder_draft_revision_conflict"
    updated = store.update(
        tenant_id="t1",
        draft_id=tip.draft_id,
        composition=next_comp,
        expected_revision=1,
        registry=registry,
    )
    assert updated.revision == 2
    assert tip.revision == 1  # prior tip record unchanged
    # Immutable revision history
    rev1 = store.get_revision_payload(tenant_id="t1", draft_id=tip.draft_id, revision=1)
    rev2 = store.get_revision_payload(tenant_id="t1", draft_id=tip.draft_id, revision=2)
    assert len(rev1["instances"]) == 1
    assert len(rev2["instances"]) == 2


def test_forms_p2_4_unknown_component_rejected_not_replaced():
    registry = _registry()
    store = InMemoryDraftStore()
    bad = build_composition(
        draft_id="bad",
        instances=[
            build_instance(
                component_id="forms.field.text",
                component_version="9.9.9",
                require_catalog=False,
            )
        ],
        require_valid=False,
    )
    with pytest.raises(FormsBuilderCompositionInvalidError):
        store.create(tenant_id="t1", composition=bad, registry=registry)


def test_forms_p2_4_list_and_archive():
    registry = _registry()
    store = InMemoryDraftStore()
    a = store.create(tenant_id="t1", composition=_draft(registry, "a"), registry=registry)
    store.create(tenant_id="t1", composition=_draft(registry, "b"), registry=registry)
    assert [r.draft_id for r in store.list(tenant_id="t1")] == ["a", "b"]
    archived = store.archive(tenant_id="t1", draft_id="a", expected_revision=a.revision)
    assert archived.status == "archived"
    assert [r.draft_id for r in store.list(tenant_id="t1")] == ["b"]
    assert [r.draft_id for r in store.list(tenant_id="t1", include_archived=True)] == ["a", "b"]
    with pytest.raises(FormsBuilderDraftArchivedError):
        store.update(
            tenant_id="t1",
            draft_id="a",
            composition=_draft(registry, "a"),
            expected_revision=archived.revision,
            registry=registry,
        )


def test_forms_p2_4_no_publish_side_effects_on_store():
    store = InMemoryDraftStore()
    for name in ("publish", "commit_publish", "save_publication"):
        assert not hasattr(store, name)
