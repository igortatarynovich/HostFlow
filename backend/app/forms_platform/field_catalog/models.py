"""Forms Field Catalog P1.1 — component identity record (no descriptors yet)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from backend.app.forms_platform.field_catalog.versioning import (
    ComponentSemver,
    parse_component_version,
)


@dataclass(frozen=True, slots=True)
class ComponentRecord:
    """Minimal registrable component identity for P1.1 (platform-wide, not tenant)."""

    component_id: str
    component_version: str
    category: str | None = None
    tags: tuple[str, ...] = ()
    # Opaque reserved bag for later descriptors (P1.2); ignored by registry logic.
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

    @property
    def semver(self) -> ComponentSemver:
        return parse_component_version(self.component_version)

    def to_dict(self) -> dict[str, Any]:
        return {
            "component_id": self.component_id,
            "component_version": self.component_version,
            "category": self.category,
            "tags": list(self.tags),
            "metadata": dict(self.metadata),
        }
