"""Forms Builder product surface — thin Catalog client (P2+).

P2.1: read model. P2.2: composition model. P2.3: immutable commands.
Persistence and UI belong to later P2 sprints.
"""

from __future__ import annotations

from backend.app.forms_platform.builder.commands import (
    BUILDER_COMPOSITION_COMMANDS_CONTRACT,
    add_instance,
    duplicate_instance,
    remove_instance,
    reorder_instance,
    replace_component_version,
    update_config,
)
from backend.app.forms_platform.builder.composition import (
    BUILDER_COMPOSITION_CONTRACT,
    CompositionInstance,
    CompositionIssue,
    FormDraftComposition,
    build_composition,
    build_instance,
    new_draft_id,
    new_instance_id,
    parse_composition,
)
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
    "BUILDER_COMPOSITION_COMMANDS_CONTRACT",
    "BUILDER_COMPOSITION_CONTRACT",
    "BUILDER_READ_MODEL_CONTRACT",
    "BuilderCategoryGroup",
    "BuilderComponentView",
    "BuilderConfigFieldView",
    "BuilderPaletteItem",
    "BuilderReadModel",
    "CompositionInstance",
    "CompositionIssue",
    "FormDraftComposition",
    "add_instance",
    "build_composition",
    "build_instance",
    "builder_read_model",
    "duplicate_instance",
    "new_draft_id",
    "new_instance_id",
    "parse_composition",
    "remove_instance",
    "reorder_instance",
    "replace_component_version",
    "update_config",
]
