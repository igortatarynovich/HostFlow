"""Forms Builder product surface — thin Catalog client (P2+).

P2.1 exposes a read model only. Later P2 sprints add draft assembly,
commands, persistence, and UI — not this package yet.
"""

from __future__ import annotations

from backend.app.forms_platform.builder.read_model import (
    BUILDER_READ_MODEL_CONTRACT,
    BuilderCategoryGroup,
    BuilderComponentView,
    BuilderConfigFieldView,
    BuilderPaletteItem,
    BuilderReadModel,
    builder_read_model,
)

__all__ = [
    "BUILDER_READ_MODEL_CONTRACT",
    "BuilderCategoryGroup",
    "BuilderComponentView",
    "BuilderConfigFieldView",
    "BuilderPaletteItem",
    "BuilderReadModel",
    "builder_read_model",
]
