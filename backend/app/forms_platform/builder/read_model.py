"""Forms Product Layer P2.1 — Builder Read Model over frozen Field Catalog v1.

Contract id: forms.builder.read_model.v1

Reads the unified Catalog only via public Registry / Descriptor APIs.
Does not register components, load the Basic pack by module path, mutate Catalog, or branch on origin.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from backend.app.forms_platform.field_catalog.models import ComponentRecord
from backend.app.forms_platform.field_catalog.registry import (
    FieldCatalogRegistry,
    platform_registry,
)

BUILDER_READ_MODEL_CONTRACT = "forms.builder.read_model.v1"

# Sentinel category key for items without a category (grouping only).
UNCATEGORIZED = ""


@dataclass(frozen=True, slots=True)
class BuilderConfigFieldView:
    """Builder-facing config field from the Catalog builder descriptor."""

    key: str
    value_type: str
    required: bool
    enum_values: tuple[str, ...] | None
    default: Any
    label_key: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "value_type": self.value_type,
            "required": self.required,
            "enum_values": list(self.enum_values) if self.enum_values is not None else None,
            "default": self.default,
            "label_key": self.label_key,
        }


@dataclass(frozen=True, slots=True)
class BuilderPaletteItem:
    """Unified palette row — Basic and extension are indistinguishable here."""

    component_id: str
    component_version: str
    category: str | None
    tags: tuple[str, ...]
    label_key: str | None
    icon: str | None
    supports_preview: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "component_id": self.component_id,
            "component_version": self.component_version,
            "category": self.category,
            "tags": list(self.tags),
            "label_key": self.label_key,
            "icon": self.icon,
            "supports_preview": self.supports_preview,
        }


@dataclass(frozen=True, slots=True)
class BuilderComponentView:
    """Exact component+version read projection for Builder (config panel)."""

    component_id: str
    component_version: str
    category: str | None
    tags: tuple[str, ...]
    label_key: str | None
    icon: str | None
    supports_preview: bool
    config_fields: tuple[BuilderConfigFieldView, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "component_id": self.component_id,
            "component_version": self.component_version,
            "category": self.category,
            "tags": list(self.tags),
            "label_key": self.label_key,
            "icon": self.icon,
            "supports_preview": self.supports_preview,
            "config_fields": [f.to_dict() for f in self.config_fields],
        }


@dataclass(frozen=True, slots=True)
class BuilderCategoryGroup:
    category: str
    items: tuple[BuilderPaletteItem, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "category": self.category,
            "items": [i.to_dict() for i in self.items],
        }


def _builder_payload(record: ComponentRecord) -> dict[str, Any]:
    desc = record.descriptors.builder
    if desc is None:
        return {}
    return dict(desc.payload)


def _category_for(record: ComponentRecord, builder_payload: dict[str, Any]) -> str | None:
    # Prefer builder descriptor category; fall back to record category.
    raw = builder_payload.get("category")
    if raw is None:
        raw = record.category
    if raw is None:
        return None
    text = str(raw).strip()
    return text or None


def _config_fields(builder_payload: dict[str, Any]) -> tuple[BuilderConfigFieldView, ...]:
    raw = builder_payload.get("config_fields") or []
    out: list[BuilderConfigFieldView] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        enum_values = item.get("enum_values")
        out.append(
            BuilderConfigFieldView(
                key=str(item.get("key") or ""),
                value_type=str(item.get("value_type") or ""),
                required=bool(item.get("required", False)),
                enum_values=tuple(enum_values) if isinstance(enum_values, list) else None,
                default=item.get("default"),
                label_key=item.get("label_key"),
            )
        )
    return tuple(out)


def _palette_item(record: ComponentRecord) -> BuilderPaletteItem:
    payload = _builder_payload(record)
    return BuilderPaletteItem(
        component_id=record.component_id,
        component_version=record.component_version,
        category=_category_for(record, payload),
        tags=tuple(record.tags),
        label_key=payload.get("label_key"),
        icon=payload.get("icon"),
        supports_preview=bool(payload.get("supports_preview", False)),
    )


def _component_view(record: ComponentRecord) -> BuilderComponentView:
    payload = _builder_payload(record)
    return BuilderComponentView(
        component_id=record.component_id,
        component_version=record.component_version,
        category=_category_for(record, payload),
        tags=tuple(record.tags),
        label_key=payload.get("label_key"),
        icon=payload.get("icon"),
        supports_preview=bool(payload.get("supports_preview", False)),
        config_fields=_config_fields(payload),
    )


class BuilderReadModel:
    """Stable Builder-facing read API over a Field Catalog registry instance."""

    def __init__(self, registry: FieldCatalogRegistry | None = None) -> None:
        self._registry = registry if registry is not None else platform_registry()

    @property
    def contract(self) -> str:
        return BUILDER_READ_MODEL_CONTRACT

    @property
    def registry(self) -> FieldCatalogRegistry:
        return self._registry

    def list_palette(
        self,
        *,
        query: str | None = None,
        category: str | None = None,
        component_id: str | None = None,
    ) -> list[BuilderPaletteItem]:
        """Unified Catalog list projected for the palette (no private type store)."""
        # Catalog find handles query / component_id. Category filter uses the
        # Builder-facing projected category (descriptor preferred over record).
        records = self._registry.find(
            query=query,
            component_id=component_id,
        )
        items = [_palette_item(r) for r in records]
        if category is not None:
            wanted = str(category).strip()
            items = [i for i in items if (i.category or "") == wanted]
        return items

    def search(
        self,
        query: str,
        *,
        category: str | None = None,
    ) -> list[BuilderPaletteItem]:
        """Search / filter via Catalog find — same projection as list_palette."""
        return self.list_palette(query=query, category=category)

    def group_by_category(
        self,
        *,
        query: str | None = None,
    ) -> list[BuilderCategoryGroup]:
        """Category groups for palette UI. Order: category ASC, then Catalog find order."""
        items = self.list_palette(query=query)
        buckets: dict[str, list[BuilderPaletteItem]] = {}
        for item in items:
            key = item.category if item.category is not None else UNCATEGORIZED
            buckets.setdefault(key, []).append(item)
        groups: list[BuilderCategoryGroup] = []
        for key in sorted(buckets.keys()):
            groups.append(BuilderCategoryGroup(category=key, items=tuple(buckets[key])))
        return groups

    def get_component(
        self,
        component_id: str,
        component_version: str,
    ) -> BuilderComponentView:
        """Exact descriptor lookup by component_id + pinned version."""
        record = self._registry.get(component_id, component_version)
        return _component_view(record)

    def get_builder_descriptor_payload(
        self,
        component_id: str,
        component_version: str,
    ) -> dict[str, Any]:
        """Raw validated builder descriptor payload (config_fields source of truth).

        Does not execute or interpret validation / normalization descriptors.
        """
        desc = self._registry.get_descriptor(component_id, component_version, "builder")
        return dict(desc.payload)


def builder_read_model(registry: FieldCatalogRegistry | None = None) -> BuilderReadModel:
    return BuilderReadModel(registry)
