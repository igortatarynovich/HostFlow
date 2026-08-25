"""Forms Field Catalog P1.4 — Extension API (module component registration).

Public surface for modules to register components through the same Registry +
Descriptor validations as Basic. No Catalog-core special cases; no tenant packs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping

from backend.app.forms_platform.errors import (
    FormsAdapterError,
    FormsCatalogBasicOverrideError,
    FormsCatalogComponentDuplicateError,
    FormsCatalogExtensionModuleInvalidError,
)
from backend.app.forms_platform.field_catalog.models import (
    ComponentRecord,
    SOURCE_PLATFORM,
    build_component_record,
    module_source,
    parse_source,
)
from backend.app.forms_platform.field_catalog.registry import (
    FieldCatalogRegistry,
    platform_registry,
)
from backend.app.forms_platform.field_catalog.stdlib import STANDARD_COMPONENT_IDS

EXTENSION_CONTRACT = "forms.field_catalog.extension.v1"
BASIC_COMPONENT_IDS = frozenset(STANDARD_COMPONENT_IDS)


@dataclass(frozen=True, slots=True)
class ExtensionRegistrationFailure:
    component_id: str
    component_version: str | None
    error_code: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "component_id": self.component_id,
            "component_version": self.component_version,
            "error_code": self.error_code,
            "message": self.message,
            "details": dict(self.details),
        }


@dataclass(frozen=True, slots=True)
class ModuleRegistrationResult:
    """Partial-success result: one module failure does not wipe the Catalog."""

    module_id: str
    source: str
    registered: tuple[ComponentRecord, ...]
    failures: tuple[ExtensionRegistrationFailure, ...]

    @property
    def ok(self) -> bool:
        return len(self.failures) == 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract": EXTENSION_CONTRACT,
            "module_id": self.module_id,
            "source": self.source,
            "registered": [r.to_dict() for r in self.registered],
            "failures": [f.to_dict() for f in self.failures],
            "ok": self.ok,
        }


def _normalize_module_id(module_id: str) -> str:
    mid = str(module_id or "").strip().lower()
    if not mid or "/" in mid or " " in mid or mid.startswith("module:"):
        raise FormsCatalogExtensionModuleInvalidError(details={"module_id": module_id})
    # allow recruitment, hr, fleet.service-style ids
    allowed = set("abcdefghijklmnopqrstuvwxyz0123456789._-")
    if any(ch not in allowed for ch in mid):
        raise FormsCatalogExtensionModuleInvalidError(details={"module_id": module_id})
    return mid


def assert_not_basic_override(component_id: str) -> None:
    cid = str(component_id or "").strip()
    if cid in BASIC_COMPONENT_IDS:
        raise FormsCatalogBasicOverrideError(
            details={"component_id": cid, "reason": "basic_component_protected"},
        )


def get_component_source(record: ComponentRecord) -> str:
    """platform | module:<id> — Builder need not use this for listing."""
    return parse_source(record.source)


def register_extension_component(
    registry: FieldCatalogRegistry | None = None,
    *,
    module_id: str,
    component_id: str,
    component_version: str,
    descriptors: Mapping[str, Any],
    category: str | None = None,
    tags: tuple[str, ...] | list[str] = (),
    metadata: dict[str, Any] | None = None,
) -> ComponentRecord:
    """Register one extension component via public Registry + Descriptor validation.

    Raises on Basic override, duplicate version (no silent replace), or invalid descriptors.
    """
    target = registry if registry is not None else platform_registry()
    mid = _normalize_module_id(module_id)
    assert_not_basic_override(component_id)
    source = module_source(mid)
    meta = dict(metadata or {})
    meta["extension_contract"] = EXTENSION_CONTRACT
    record = build_component_record(
        component_id=component_id,
        component_version=component_version,
        category=category,
        tags=tags,
        descriptors=descriptors,
        metadata=meta,
        source=source,
        require_complete_descriptors=True,
    )
    # Explicit non-silent: duplicate raises FormsCatalogComponentDuplicateError
    return target.register(record)


def register_module_components(
    registry: FieldCatalogRegistry | None = None,
    *,
    module_id: str,
    components: Iterable[Mapping[str, Any]],
) -> ModuleRegistrationResult:
    """Register a module pack with isolated per-component errors.

    Components are applied in deterministic component_id ASC order so load order
    of packs does not change the final Catalog find() ordering.
    """
    target = registry if registry is not None else platform_registry()
    mid = _normalize_module_id(module_id)
    source = module_source(mid)

    items = list(components)
    # Deterministic processing order within the pack
    items.sort(key=lambda c: (str(c.get("component_id") or ""), str(c.get("component_version") or "")))

    registered: list[ComponentRecord] = []
    failures: list[ExtensionRegistrationFailure] = []

    for spec in items:
        cid = str(spec.get("component_id") or "").strip()
        ver = str(spec.get("component_version") or "").strip() or None
        try:
            rec = register_extension_component(
                target,
                module_id=mid,
                component_id=cid,
                component_version=str(spec.get("component_version") or ""),
                descriptors=spec.get("descriptors") or {},
                category=spec.get("category"),
                tags=tuple(spec.get("tags") or ()),
                metadata=dict(spec.get("metadata") or {}),
            )
            registered.append(rec)
        except FormsAdapterError as exc:
            failures.append(
                ExtensionRegistrationFailure(
                    component_id=cid or "unknown",
                    component_version=ver,
                    error_code=getattr(exc, "code", "forms_adapter_error"),
                    message=str(getattr(exc, "message", exc)),
                    details=dict(getattr(exc, "details", {}) or {}),
                )
            )
        except Exception as exc:  # noqa: BLE001 — isolate unexpected module errors
            failures.append(
                ExtensionRegistrationFailure(
                    component_id=cid or "unknown",
                    component_version=ver,
                    error_code="forms_catalog_extension_unexpected",
                    message=str(exc),
                    details={},
                )
            )

    return ModuleRegistrationResult(
        module_id=mid,
        source=source,
        registered=tuple(registered),
        failures=tuple(failures),
    )


def list_catalog_for_builder(registry: FieldCatalogRegistry | None = None) -> list[dict[str, Any]]:
    """Unified catalog read — no Basic/Extension split (Builder view)."""
    target = registry if registry is not None else platform_registry()
    # find() already deterministic: id ASC, version DESC
    return [
        {
            "component_id": r.component_id,
            "component_version": r.component_version,
            "category": r.category,
            "tags": list(r.tags),
            # source available for audit tooling, not required for Builder composition
            "source": get_component_source(r),
        }
        for r in target.find()
    ]
