"""Forms Product Layer P2.3 — Composition Commands contract tests."""

from __future__ import annotations

import pytest

from backend.app.forms_platform.builder import (
    BUILDER_COMPOSITION_COMMANDS_CONTRACT,
    FormDraftComposition,
    add_instance,
    build_composition,
    build_instance,
    duplicate_instance,
    remove_instance,
    reorder_instance,
    replace_component_version,
    update_config,
)
from backend.app.forms_platform.errors import (
    FormsBuilderCompositionCommandError,
    FormsBuilderCompositionConfigError,
    FormsBuilderCompositionInvalidError,
)
from backend.app.forms_platform.field_catalog import (
    FieldCatalogRegistry,
    build_component_record,
    register_standard_library,
)


def _seed(registry: FieldCatalogRegistry) -> None:
    register_standard_library(registry)
    # Second version of text for explicit replace_component_version tests
    registry.register(
        build_component_record(
            component_id="forms.field.text",
            component_version="1.1.0",
            category="input",
            tags=("text",),
            descriptors={
                "builder": {
                    "label_key": "forms.field.text.label",
                    "icon": "text",
                    "category": "input",
                    "supports_preview": True,
                    "config_fields": [
                        {
                            "key": "label",
                            "value_type": "string",
                            "required": False,
                            "label_key": "forms.config.label",
                        },
                        {
                            "key": "help_text",
                            "value_type": "string",
                            "required": False,
                            "label_key": "forms.config.help_text",
                        },
                    ],
                },
                "public": {
                    "input_kind": "text",
                    "widget_token": "forms.widget.text",
                    "label_key": "forms.field.text.label",
                    "attributes": {},
                },
                "validation": {"value_type": "string", "required_default": False, "rules": []},
                "normalization": {
                    "value_type": "string",
                    "steps": [{"op": "trim", "params": {}}],
                },
            },
            require_complete_descriptors=True,
        )
    )


def _empty(registry: FieldCatalogRegistry) -> FormDraftComposition:
    return build_composition(draft_id="draft-1", instances=[], registry=registry)


def test_forms_p2_3_commands_contract_id():
    assert BUILDER_COMPOSITION_COMMANDS_CONTRACT == "forms.builder.composition_commands.v1"


def test_forms_p2_3_add_remove_immutable():
    registry = FieldCatalogRegistry()
    _seed(registry)
    draft = _empty(registry)
    next_draft = add_instance(
        draft,
        component_id="forms.field.text",
        component_version="1.0.0",
        config={"label": "A"},
        registry=registry,
    )
    assert draft.size == 0
    assert next_draft.size == 1
    assert next_draft.draft_id == draft.draft_id
    removed = remove_instance(next_draft, next_draft.instances[0].instance_id)
    assert next_draft.size == 1
    assert removed.size == 0


def test_forms_p2_3_unknown_component_typed_error():
    registry = FieldCatalogRegistry()
    _seed(registry)
    draft = _empty(registry)
    with pytest.raises(FormsBuilderCompositionInvalidError) as exc:
        add_instance(
            draft,
            component_id="forms.field.text",
            component_version="9.9.9",
            registry=registry,
        )
    assert exc.value.details.get("reason") == "unknown_component_or_version"


def test_forms_p2_3_reorder_preserves_content():
    registry = FieldCatalogRegistry()
    _seed(registry)
    draft = _empty(registry)
    draft = add_instance(
        draft, component_id="forms.field.text", component_version="1.0.0",
        config={"label": "A"}, instance_id="a", registry=registry,
    )
    draft = add_instance(
        draft, component_id="forms.field.email", component_version="1.0.0",
        config={"label": "B"}, instance_id="b", registry=registry,
    )
    before = draft.instances[0]
    moved = reorder_instance(draft, "a", to_index=1)
    assert moved.instance_order() == ("b", "a")
    after = moved.get_instance("a")
    assert after.component_id == before.component_id
    assert after.component_version == before.component_version
    assert after.config == before.config
    assert draft.instance_order() == ("a", "b")


def test_forms_p2_3_update_config_keeps_identity():
    registry = FieldCatalogRegistry()
    _seed(registry)
    draft = add_instance(
        _empty(registry),
        component_id="forms.field.text",
        component_version="1.0.0",
        config={"label": "Old"},
        instance_id="x",
        registry=registry,
    )
    updated = update_config(draft, "x", {"label": "New"}, registry=registry)
    inst = updated.get_instance("x")
    assert inst.component_id == "forms.field.text"
    assert inst.component_version == "1.0.0"
    assert inst.config == {"label": "New"}
    assert draft.get_instance("x").config == {"label": "Old"}
    with pytest.raises(FormsBuilderCompositionConfigError):
        update_config(draft, "x", {"not_a_field": 1}, registry=registry)


def test_forms_p2_3_duplicate_new_instance_id():
    registry = FieldCatalogRegistry()
    _seed(registry)
    draft = add_instance(
        _empty(registry),
        component_id="forms.field.text",
        component_version="1.0.0",
        config={"label": "A"},
        instance_id="src",
        registry=registry,
    )
    duped = duplicate_instance(draft, "src")
    assert duped.size == 2
    assert duped.instances[0].instance_id == "src"
    assert duped.instances[1].instance_id != "src"
    assert duped.instances[1].component_id == "forms.field.text"
    assert duped.instances[1].component_version == "1.0.0"
    assert duped.instances[1].config == {"label": "A"}


def test_forms_p2_3_replace_version_explicit_only():
    registry = FieldCatalogRegistry()
    _seed(registry)
    draft = add_instance(
        _empty(registry),
        component_id="forms.field.text",
        component_version="1.0.0",
        config={"label": "A"},
        instance_id="x",
        registry=registry,
    )
    # No automatic upgrade path exists on add/update
    assert draft.get_instance("x").component_version == "1.0.0"
    bumped = replace_component_version(
        draft, "x", component_version="1.1.0", registry=registry,
    )
    assert bumped.get_instance("x").component_version == "1.1.0"
    assert bumped.get_instance("x").component_id == "forms.field.text"
    assert draft.get_instance("x").component_version == "1.0.0"
    with pytest.raises(FormsBuilderCompositionInvalidError):
        replace_component_version(
            draft, "x", component_version="2.0.0", registry=registry,
        )


def test_forms_p2_3_instance_id_unique_on_add():
    registry = FieldCatalogRegistry()
    _seed(registry)
    draft = add_instance(
        _empty(registry),
        component_id="forms.field.text",
        component_version="1.0.0",
        instance_id="same",
        registry=registry,
    )
    with pytest.raises(FormsBuilderCompositionCommandError) as exc:
        add_instance(
            draft,
            component_id="forms.field.email",
            component_version="1.0.0",
            instance_id="same",
            registry=registry,
        )
    assert exc.value.details.get("reason") == "duplicate_instance_id"


def test_forms_p2_3_no_save_load_publish_surface():
    import backend.app.forms_platform.builder.commands as commands

    for name in ("save", "load", "save_draft", "load_draft", "publish", "persist"):
        assert not hasattr(commands, name)
