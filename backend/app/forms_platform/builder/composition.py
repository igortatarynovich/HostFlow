"""Forms Product Layer P2.2 — Builder Composition Model.

Contract id: forms.builder.composition.v1

Canonical in-memory draft structure. No persistence, no publish side effects,
no UI layout coordinates. Validates against frozen Catalog public APIs only.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from typing import Any, Mapping

from backend.app.forms_platform.errors import (
    FormsBuilderCompositionConfigError,
    FormsBuilderCompositionInvalidError,
    FormsCatalogComponentNotFoundError,
)
from backend.app.forms_platform.field_catalog.registry import (
    FieldCatalogRegistry,
    platform_registry,
)
from backend.app.forms_platform.field_catalog.versioning import parse_component_version

BUILDER_COMPOSITION_CONTRACT = "forms.builder.composition.v1"


@dataclass(frozen=True, slots=True)
class CompositionIssue:
    code: str
    message: str
    instance_id: str | None = None
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "instance_id": self.instance_id,
            "details": dict(self.details),
        }


@dataclass(frozen=True, slots=True)
class CompositionInstance:
    """One placed component instance in a draft composition."""

    instance_id: str
    component_id: str
    component_version: str
    config: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        iid = str(self.instance_id or "").strip()
        cid = str(self.component_id or "").strip()
        if not iid:
            raise FormsBuilderCompositionInvalidError(
                details={"reason": "empty_instance_id"},
            )
        if not cid:
            raise FormsBuilderCompositionInvalidError(
                details={"reason": "empty_component_id", "instance_id": iid},
            )
        ver = str(parse_component_version(self.component_version))
        cfg = dict(self.config or {})
        # Forbidden: origin / executable descriptor payloads in instance storage
        for forbidden in ("source", "validation", "normalization", "public"):
            if forbidden in cfg:
                raise FormsBuilderCompositionInvalidError(
                    details={
                        "reason": "forbidden_config_key",
                        "key": forbidden,
                        "instance_id": iid,
                    },
                )
        object.__setattr__(self, "instance_id", iid)
        object.__setattr__(self, "component_id", cid)
        object.__setattr__(self, "component_version", ver)
        object.__setattr__(self, "config", cfg)

    @property
    def pinned_version(self) -> str:
        """Exact Catalog version pin — never auto-upgraded."""
        return self.component_version

    def to_dict(self) -> dict[str, Any]:
        return {
            "instance_id": self.instance_id,
            "component_id": self.component_id,
            "component_version": self.component_version,
            "config": dict(self.config),
        }


@dataclass(frozen=True, slots=True)
class FormDraftComposition:
    """Canonical Builder draft: stable identity + ordered instances.

    Order is the sequence of ``instances`` (index 0 = first). No UI x/y/layout.
    """

    draft_id: str
    instances: tuple[CompositionInstance, ...] = ()
    contract: str = BUILDER_COMPOSITION_CONTRACT

    def __post_init__(self) -> None:
        did = str(self.draft_id or "").strip()
        if not did:
            raise FormsBuilderCompositionInvalidError(
                details={"reason": "empty_draft_id"},
            )
        seen: set[str] = set()
        for inst in self.instances:
            if inst.instance_id in seen:
                raise FormsBuilderCompositionInvalidError(
                    details={
                        "reason": "duplicate_instance_id",
                        "instance_id": inst.instance_id,
                    },
                )
            seen.add(inst.instance_id)
        object.__setattr__(self, "draft_id", did)
        object.__setattr__(self, "instances", tuple(self.instances))
        object.__setattr__(self, "contract", BUILDER_COMPOSITION_CONTRACT)

    @property
    def size(self) -> int:
        return len(self.instances)

    def instance_order(self) -> tuple[str, ...]:
        return tuple(i.instance_id for i in self.instances)

    def get_instance(self, instance_id: str) -> CompositionInstance:
        iid = str(instance_id or "").strip()
        for inst in self.instances:
            if inst.instance_id == iid:
                return inst
        raise FormsBuilderCompositionInvalidError(
            details={"reason": "instance_not_found", "instance_id": iid},
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract": self.contract,
            "draft_id": self.draft_id,
            "instances": [i.to_dict() for i in self.instances],
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))

    def diagnose(
        self,
        registry: FieldCatalogRegistry | None = None,
    ) -> list[CompositionIssue]:
        """Diagnosable validity against Catalog — never silent replace."""
        target = registry if registry is not None else platform_registry()
        issues: list[CompositionIssue] = []
        for inst in self.instances:
            try:
                record = target.get(inst.component_id, inst.component_version)
            except FormsCatalogComponentNotFoundError as exc:
                issues.append(
                    CompositionIssue(
                        code="unknown_component_or_version",
                        message="Unknown component_id or component_version",
                        instance_id=inst.instance_id,
                        details=dict(exc.details),
                    )
                )
                continue

            builder = record.descriptors.builder
            if builder is None:
                issues.append(
                    CompositionIssue(
                        code="builder_descriptor_missing",
                        message="Component has no builder descriptor",
                        instance_id=inst.instance_id,
                        details={
                            "component_id": inst.component_id,
                            "component_version": inst.component_version,
                        },
                    )
                )
                continue

            allowed = {
                str(f.get("key"))
                for f in (builder.payload.get("config_fields") or [])
                if isinstance(f, dict) and f.get("key")
            }
            required = {
                str(f.get("key"))
                for f in (builder.payload.get("config_fields") or [])
                if isinstance(f, dict) and f.get("key") and f.get("required")
            }
            unknown_keys = sorted(set(inst.config) - allowed)
            if unknown_keys:
                issues.append(
                    CompositionIssue(
                        code="config_keys_not_in_descriptor",
                        message="config contains keys outside builder config_fields",
                        instance_id=inst.instance_id,
                        details={"keys": unknown_keys, "allowed": sorted(allowed)},
                    )
                )
            missing_required = sorted(k for k in required if k not in inst.config)
            if missing_required:
                issues.append(
                    CompositionIssue(
                        code="config_required_missing",
                        message="required config_fields missing from instance config",
                        instance_id=inst.instance_id,
                        details={"keys": missing_required},
                    )
                )
        return issues

    def assert_valid(self, registry: FieldCatalogRegistry | None = None) -> None:
        issues = self.diagnose(registry)
        if issues:
            raise FormsBuilderCompositionInvalidError(
                details={
                    "draft_id": self.draft_id,
                    "issues": [i.to_dict() for i in issues],
                },
            )

    def is_valid(self, registry: FieldCatalogRegistry | None = None) -> bool:
        return len(self.diagnose(registry)) == 0


def new_draft_id() -> str:
    return str(uuid.uuid4())


def new_instance_id() -> str:
    return str(uuid.uuid4())


def build_instance(
    *,
    component_id: str,
    component_version: str,
    config: Mapping[str, Any] | None = None,
    instance_id: str | None = None,
    registry: FieldCatalogRegistry | None = None,
    require_catalog: bool = True,
) -> CompositionInstance:
    """Build one instance. Optionally require exact Catalog presence (default)."""
    inst = CompositionInstance(
        instance_id=instance_id or new_instance_id(),
        component_id=component_id,
        component_version=component_version,
        config=dict(config or {}),
    )
    if require_catalog:
        target = registry if registry is not None else platform_registry()
        try:
            target.get(inst.component_id, inst.component_version)
        except FormsCatalogComponentNotFoundError as exc:
            raise FormsBuilderCompositionInvalidError(
                details={
                    "reason": "unknown_component_or_version",
                    "instance_id": inst.instance_id,
                    **dict(exc.details),
                },
            ) from exc
        # Config key check against builder descriptor
        draft = FormDraftComposition(draft_id="_", instances=(inst,))
        issues = [
            i
            for i in draft.diagnose(target)
            if i.code in {"config_keys_not_in_descriptor", "config_required_missing", "builder_descriptor_missing"}
        ]
        if issues:
            raise FormsBuilderCompositionConfigError(
                details={"instance_id": inst.instance_id, "issues": [i.to_dict() for i in issues]},
            )
    return inst


def build_composition(
    *,
    draft_id: str | None = None,
    instances: list[CompositionInstance] | tuple[CompositionInstance, ...] = (),
    registry: FieldCatalogRegistry | None = None,
    require_valid: bool = True,
) -> FormDraftComposition:
    """Assemble a draft composition. Order of ``instances`` is canonical order."""
    draft = FormDraftComposition(
        draft_id=draft_id or new_draft_id(),
        instances=tuple(instances),
    )
    if require_valid:
        draft.assert_valid(registry)
    return draft


def parse_composition(raw: Mapping[str, Any]) -> FormDraftComposition:
    """Parse a composition dict. Does not persist or publish."""
    if not isinstance(raw, Mapping):
        raise FormsBuilderCompositionInvalidError(details={"reason": "expected_object"})
    data = dict(raw)
    contract = str(data.get("contract") or BUILDER_COMPOSITION_CONTRACT).strip()
    if contract != BUILDER_COMPOSITION_CONTRACT:
        raise FormsBuilderCompositionInvalidError(
            details={"reason": "unsupported_contract", "contract": contract},
        )
    # Reject origin / layout / persistence / publish leakage at draft root
    forbidden_root = {
        "source",
        "validation",
        "normalization",
        "layout",
        "x",
        "y",
        "published_version",
        "publish",
    }
    leaked = sorted(set(data) & forbidden_root)
    if leaked:
        raise FormsBuilderCompositionInvalidError(
            details={"reason": "forbidden_root_fields", "fields": leaked},
        )
    raw_instances = data.get("instances", [])
    if not isinstance(raw_instances, list):
        raise FormsBuilderCompositionInvalidError(
            details={"reason": "instances_expected_array"},
        )
    instances: list[CompositionInstance] = []
    for i, item in enumerate(raw_instances):
        if not isinstance(item, Mapping):
            raise FormsBuilderCompositionInvalidError(
                details={"reason": "instance_expected_object", "index": i},
            )
        row = dict(item)
        for forbidden in ("source", "validation", "normalization", "x", "y", "layout"):
            if forbidden in row:
                raise FormsBuilderCompositionInvalidError(
                    details={
                        "reason": "forbidden_instance_field",
                        "field": forbidden,
                        "index": i,
                    },
                )
        instances.append(
            CompositionInstance(
                instance_id=str(row.get("instance_id") or ""),
                component_id=str(row.get("component_id") or ""),
                component_version=str(row.get("component_version") or ""),
                config=dict(row.get("config") or {}),
            )
        )
    return FormDraftComposition(
        draft_id=str(data.get("draft_id") or ""),
        instances=tuple(instances),
    )
