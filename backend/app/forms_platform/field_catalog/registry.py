"""Forms Field Catalog P1.1 — in-memory platform component registry.

Tenant-independent. No Builder, renderers, module extension API, or DB migration.
"""

from __future__ import annotations

from typing import Iterable

from backend.app.forms_platform.errors import (
    FormsCatalogComponentDuplicateError,
    FormsCatalogComponentNotFoundError,
    FormsCatalogVersionIncompatibleError,
)
from backend.app.forms_platform.field_catalog.models import ComponentRecord
from backend.app.forms_platform.field_catalog.versioning import (
    is_compatible,
    parse_component_version,
)

CATALOG_REGISTRY_CONTRACT = "forms.field_catalog.registry.v1"


class FieldCatalogRegistry:
    """Platform-wide component registry (not scoped by tenant)."""

    def __init__(self) -> None:
        # (component_id, version_str) → record
        self._by_key: dict[tuple[str, str], ComponentRecord] = {}
        # component_id → versions present (as strings)
        self._versions: dict[str, set[str]] = {}

    def clear(self) -> None:
        self._by_key.clear()
        self._versions.clear()

    def register(self, record: ComponentRecord) -> ComponentRecord:
        key = (record.component_id, record.component_version)
        if key in self._by_key:
            raise FormsCatalogComponentDuplicateError(
                details={
                    "component_id": record.component_id,
                    "component_version": record.component_version,
                },
            )
        self._by_key[key] = record
        self._versions.setdefault(record.component_id, set()).add(record.component_version)
        return record

    def get(self, component_id: str, component_version: str) -> ComponentRecord:
        cid = str(component_id or "").strip()
        ver = str(parse_component_version(component_version))
        record = self._by_key.get((cid, ver))
        if record is None:
            raise FormsCatalogComponentNotFoundError(
                details={"component_id": cid, "component_version": ver},
            )
        return record

    def find(
        self,
        *,
        query: str | None = None,
        category: str | None = None,
        component_id: str | None = None,
    ) -> list[ComponentRecord]:
        """Search registered components. Deterministic order: id ASC, version DESC."""
        q = str(query).strip().lower() if query else None
        cat = str(category).strip() if category else None
        cid_filter = str(component_id).strip() if component_id else None

        results: list[ComponentRecord] = []
        for record in self._by_key.values():
            if cid_filter and record.component_id != cid_filter:
                continue
            if cat is not None and (record.category or "") != cat:
                continue
            if q:
                hay = " ".join(
                    [
                        record.component_id.lower(),
                        (record.category or "").lower(),
                        " ".join(t.lower() for t in record.tags),
                    ]
                )
                if q not in hay:
                    continue
            results.append(record)

        results.sort(
            key=lambda r: (r.component_id, tuple(-x for x in r.semver.tuple)),
        )
        return results

    def list_versions(self, component_id: str) -> list[str]:
        cid = str(component_id or "").strip()
        versions = self._versions.get(cid)
        if not versions:
            raise FormsCatalogComponentNotFoundError(details={"component_id": cid})
        return sorted(versions, key=lambda v: parse_component_version(v).tuple)

    def resolve_compatible(
        self,
        component_id: str,
        requested_version: str,
    ) -> ComponentRecord:
        """Latest version compatible with requested (same major, >= requested)."""
        cid = str(component_id or "").strip()
        req = parse_component_version(requested_version)
        versions = self._versions.get(cid)
        if not versions:
            raise FormsCatalogComponentNotFoundError(
                details={"component_id": cid, "component_version": str(req)},
            )

        compatible = [
            v
            for v in versions
            if is_compatible(req, v)
        ]
        if not compatible:
            raise FormsCatalogVersionIncompatibleError(
                details={
                    "component_id": cid,
                    "requested_version": str(req),
                    "available_versions": sorted(
                        versions, key=lambda v: parse_component_version(v).tuple
                    ),
                },
            )
        best = max(compatible, key=lambda v: parse_component_version(v).tuple)
        return self.get(cid, best)

    def check_compatible(
        self,
        component_id: str,
        requested_version: str,
        candidate_version: str,
    ) -> bool:
        """True if candidate is registered and compatible with requested."""
        # Ensure both exist (exact get validates registration of candidate).
        self.get(component_id, candidate_version)
        # requested may be a constraint not itself registered
        parse_component_version(requested_version)
        return is_compatible(requested_version, candidate_version)

    def assert_compatible(
        self,
        component_id: str,
        requested_version: str,
        candidate_version: str,
    ) -> None:
        if not self.check_compatible(component_id, requested_version, candidate_version):
            raise FormsCatalogVersionIncompatibleError(
                details={
                    "component_id": str(component_id).strip(),
                    "requested_version": str(parse_component_version(requested_version)),
                    "candidate_version": str(parse_component_version(candidate_version)),
                },
            )


# Process-wide platform registry (tenant-independent). Tests should use a fresh instance
# or call reset_platform_registry().
_PLATFORM_REGISTRY = FieldCatalogRegistry()


def platform_registry() -> FieldCatalogRegistry:
    return _PLATFORM_REGISTRY


def reset_platform_registry() -> FieldCatalogRegistry:
    _PLATFORM_REGISTRY.clear()
    return _PLATFORM_REGISTRY


def register_components(records: Iterable[ComponentRecord], *, registry: FieldCatalogRegistry | None = None) -> None:
    target = registry if registry is not None else platform_registry()
    for record in records:
        target.register(record)
