"""Forms Product Layer P2.3 — Composition Commands.

Contract id: forms.builder.composition_commands.v1

Immutable domain commands over FormDraftComposition.
No persistence, no publish, no UI / drag-and-drop semantics.
"""

from __future__ import annotations

from typing import Any, Mapping

from backend.app.forms_platform.builder.composition import (
    CompositionInstance,
    FormDraftComposition,
    build_instance,
    new_instance_id,
)
from backend.app.forms_platform.errors import (
    FormsBuilderCompositionCommandError,
    FormsBuilderCompositionInvalidError,
    FormsCatalogComponentNotFoundError,
)
from backend.app.forms_platform.field_catalog.registry import (
    FieldCatalogRegistry,
    platform_registry,
)
from backend.app.forms_platform.field_catalog.versioning import parse_component_version

BUILDER_COMPOSITION_COMMANDS_CONTRACT = "forms.builder.composition_commands.v1"


def _registry(registry: FieldCatalogRegistry | None) -> FieldCatalogRegistry:
    return registry if registry is not None else platform_registry()


def _index_of(draft: FormDraftComposition, instance_id: str) -> int:
    iid = str(instance_id or "").strip()
    for i, inst in enumerate(draft.instances):
        if inst.instance_id == iid:
            return i
    raise FormsBuilderCompositionCommandError(
        details={
            "reason": "instance_not_found",
            "instance_id": iid,
            "draft_id": draft.draft_id,
        },
    )


def _with_instances(
    draft: FormDraftComposition,
    instances: list[CompositionInstance] | tuple[CompositionInstance, ...],
) -> FormDraftComposition:
    return FormDraftComposition(
        draft_id=draft.draft_id,
        instances=tuple(instances),
    )


def add_instance(
    draft: FormDraftComposition,
    *,
    component_id: str,
    component_version: str,
    config: Mapping[str, Any] | None = None,
    index: int | None = None,
    instance_id: str | None = None,
    registry: FieldCatalogRegistry | None = None,
) -> FormDraftComposition:
    """Append or insert a new Catalog-backed instance. Returns a new composition."""
    target = _registry(registry)
    inst = build_instance(
        component_id=component_id,
        component_version=component_version,
        config=config,
        instance_id=instance_id,
        registry=target,
        require_catalog=True,
    )
    items = list(draft.instances)
    if any(existing.instance_id == inst.instance_id for existing in items):
        raise FormsBuilderCompositionCommandError(
            details={
                "reason": "duplicate_instance_id",
                "instance_id": inst.instance_id,
                "draft_id": draft.draft_id,
            },
        )
    if index is None:
        items.append(inst)
    else:
        if index < 0 or index > len(items):
            raise FormsBuilderCompositionCommandError(
                details={
                    "reason": "index_out_of_range",
                    "index": index,
                    "size": len(items),
                },
            )
        items.insert(index, inst)
    return _with_instances(draft, items)


def remove_instance(
    draft: FormDraftComposition,
    instance_id: str,
) -> FormDraftComposition:
    """Remove one instance by id. Returns a new composition."""
    idx = _index_of(draft, instance_id)
    items = list(draft.instances)
    del items[idx]
    return _with_instances(draft, items)


def reorder_instance(
    draft: FormDraftComposition,
    instance_id: str,
    *,
    to_index: int,
) -> FormDraftComposition:
    """Move an instance to ``to_index`` without changing instance content."""
    from_index = _index_of(draft, instance_id)
    items = list(draft.instances)
    if to_index < 0 or to_index >= len(items):
        raise FormsBuilderCompositionCommandError(
            details={
                "reason": "index_out_of_range",
                "index": to_index,
                "size": len(items),
            },
        )
    if from_index == to_index:
        return _with_instances(draft, items)
    inst = items.pop(from_index)
    items.insert(to_index, inst)
    return _with_instances(draft, items)


def update_config(
    draft: FormDraftComposition,
    instance_id: str,
    config: Mapping[str, Any],
    *,
    registry: FieldCatalogRegistry | None = None,
) -> FormDraftComposition:
    """Replace instance config only — component identity/version stay pinned."""
    target = _registry(registry)
    idx = _index_of(draft, instance_id)
    current = draft.instances[idx]
    updated = build_instance(
        component_id=current.component_id,
        component_version=current.component_version,
        config=config,
        instance_id=current.instance_id,
        registry=target,
        require_catalog=True,
    )
    # Guard: identity must not change
    if (
        updated.component_id != current.component_id
        or updated.component_version != current.component_version
        or updated.instance_id != current.instance_id
    ):
        raise FormsBuilderCompositionCommandError(
            details={"reason": "identity_mutation_forbidden", "instance_id": instance_id},
        )
    items = list(draft.instances)
    items[idx] = updated
    return _with_instances(draft, items)


def duplicate_instance(
    draft: FormDraftComposition,
    instance_id: str,
    *,
    index: int | None = None,
) -> FormDraftComposition:
    """Clone an instance with a new instance_id. Catalog pin and config copied."""
    idx = _index_of(draft, instance_id)
    source = draft.instances[idx]
    clone = CompositionInstance(
        instance_id=new_instance_id(),
        component_id=source.component_id,
        component_version=source.component_version,
        config=dict(source.config),
    )
    items = list(draft.instances)
    insert_at = idx + 1 if index is None else index
    if insert_at < 0 or insert_at > len(items):
        raise FormsBuilderCompositionCommandError(
            details={
                "reason": "index_out_of_range",
                "index": insert_at,
                "size": len(items),
            },
        )
    items.insert(insert_at, clone)
    return _with_instances(draft, items)


def replace_component_version(
    draft: FormDraftComposition,
    instance_id: str,
    *,
    component_version: str,
    config: Mapping[str, Any] | None = None,
    registry: FieldCatalogRegistry | None = None,
) -> FormDraftComposition:
    """Explicit version pin change for one instance. Never auto-upgrades.

    ``component_id`` stays the same. Config defaults to the previous config and
    is re-validated against the target Catalog version's builder descriptor.
    """
    target = _registry(registry)
    idx = _index_of(draft, instance_id)
    current = draft.instances[idx]
    new_ver = str(parse_component_version(component_version))
    if new_ver == current.component_version:
        # No-op still returns a new composition object (immutability contract).
        return _with_instances(draft, list(draft.instances))

    try:
        target.get(current.component_id, new_ver)
    except FormsCatalogComponentNotFoundError as exc:
        raise FormsBuilderCompositionInvalidError(
            details={
                "reason": "unknown_component_or_version",
                "instance_id": current.instance_id,
                "component_id": current.component_id,
                "component_version": new_ver,
                **dict(exc.details),
            },
        ) from exc

    cfg = dict(current.config if config is None else config)
    updated = build_instance(
        component_id=current.component_id,
        component_version=new_ver,
        config=cfg,
        instance_id=current.instance_id,
        registry=target,
        require_catalog=True,
    )
    if updated.component_id != current.component_id:
        raise FormsBuilderCompositionCommandError(
            details={"reason": "component_id_mutation_forbidden", "instance_id": instance_id},
        )
    items = list(draft.instances)
    items[idx] = updated
    return _with_instances(draft, items)
