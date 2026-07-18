"""Forms Field Catalog — component identity + optional P1.2 descriptors."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from backend.app.forms_platform.field_catalog.descriptors import (
    ComponentDescriptors,
    parse_descriptors,
)
from backend.app.forms_platform.field_catalog.versioning import (
    ComponentSemver,
    parse_component_version,
)


@dataclass(frozen=True, slots=True)
class ComponentRecord:
    """Platform-wide component identity; descriptors optional until P1.3 stdlib."""

    component_id: str
    component_version: str
    category: str | None = None
    tags: tuple[str, ...] = ()
    descriptors: ComponentDescriptors = field(default_factory=ComponentDescriptors)
    # Opaque reserved bag (non-descriptor metadata only).
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        cid = str(self.component_id or "").strip()
        if not cid:
            raise ValueError("component_id is required")
        ver = parse_component_version(self.component_version)
        object.__setattr__(self, "component_id", cid)
        object.__setattr__(self, "component_version", str(ver))
        tags = tuple(str(t).strip() for t in (self.tags or ()) if str(t).strip())
        object.__setattr__(self, "tags", tags)
        cat = self.category
        if cat is not None:
            cat_s = str(cat).strip()
            object.__setattr__(self, "category", cat_s or None)
        meta = dict(self.metadata or {})
        object.__setattr__(self, "metadata", meta)
        if not isinstance(self.descriptors, ComponentDescriptors):
            raise TypeError("descriptors must be ComponentDescriptors")
        # Re-bind identity onto descriptor docs if present
        rebound = parse_descriptors(
            {
                k: getattr(self.descriptors, k).payload
                for k in ("builder", "public", "validation", "normalization")
                if getattr(self.descriptors, k) is not None
            },
            component_id=cid,
            component_version=str(ver),
        )
        object.__setattr__(self, "descriptors", rebound)

    @property
    def semver(self) -> ComponentSemver:
        return parse_component_version(self.component_version)

    def to_dict(self) -> dict[str, Any]:
        return {
            "component_id": self.component_id,
            "component_version": self.component_version,
            "category": self.category,
            "tags": list(self.tags),
            "descriptors": self.descriptors.to_dict(),
            "metadata": dict(self.metadata),
        }


def build_component_record(
    *,
    component_id: str,
    component_version: str,
    category: str | None = None,
    tags: tuple[str, ...] | list[str] = (),
    descriptors: Mapping[str, Any] | ComponentDescriptors | None = None,
    metadata: dict[str, Any] | None = None,
    require_complete_descriptors: bool = False,
) -> ComponentRecord:
    """Factory: validates descriptor payloads at construction / registration time."""
    if isinstance(descriptors, ComponentDescriptors):
        desc = descriptors
        if require_complete_descriptors and not desc.is_complete:
            from backend.app.forms_platform.errors import FormsCatalogDescriptorMissingError
            from backend.app.forms_platform.field_catalog.descriptors import DESCRIPTOR_KINDS

            missing = [k for k in DESCRIPTOR_KINDS if getattr(desc, k) is None]
            raise FormsCatalogDescriptorMissingError(
                details={"kinds": missing, "reason": "incomplete_descriptors"},
            )
    else:
        desc = parse_descriptors(
            descriptors,
            component_id=component_id,
            component_version=component_version,
            require_complete=require_complete_descriptors,
        )
    return ComponentRecord(
        component_id=component_id,
        component_version=component_version,
        category=category,
        tags=tuple(tags),
        descriptors=desc,
        metadata=dict(metadata or {}),
    )
