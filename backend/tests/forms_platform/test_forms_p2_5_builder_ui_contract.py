"""Forms Product Layer P2.5 — Minimal Builder UI / HTTP adapter contract tests."""

from __future__ import annotations

from backend.app.api.v1.platform.forms_builder import draft_id_for_form
from backend.app.forms_platform.builder.read_model import BuilderReadModel
from backend.app.forms_platform.field_catalog import (
    FieldCatalogRegistry,
    register_standard_library,
)


def test_forms_p2_5_draft_id_binding():
    assert draft_id_for_form("f1") == "form:f1"


def test_forms_p2_5_palette_from_read_model_for_ui():
    registry = FieldCatalogRegistry()
    register_standard_library(registry)
    items = BuilderReadModel(registry).list_palette()
    assert len(items) >= 12
    assert all(i.component_id and i.component_version for i in items)
    # UI must not need origin
    for item in items:
        assert "source" not in item.to_dict()
