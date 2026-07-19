"""Forms Builder product surface — thin Catalog client (P2+).

P2.1 read model · P2.2 composition · P2.3 commands · P2.4 draft persistence.
UI belongs to P2.5 (after UI gate).
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
from backend.app.forms_platform.builder.draft_persistence import (
    BUILDER_DRAFT_PERSISTENCE_CONTRACT,
    DraftRecord,
    InMemoryDraftStore,
    archive_draft,
    create_draft,
    get_draft,
    get_draft_revision,
    list_drafts,
    update_draft,
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
    "BUILDER_DRAFT_PERSISTENCE_CONTRACT",
    "BUILDER_READ_MODEL_CONTRACT",
    "BuilderCategoryGroup",
    "BuilderComponentView",
    "BuilderConfigFieldView",
    "BuilderPaletteItem",
    "BuilderReadModel",
    "CompositionInstance",
    "CompositionIssue",
    "DraftRecord",
    "FormDraftComposition",
    "InMemoryDraftStore",
    "add_instance",
    "archive_draft",
    "build_composition",
    "build_instance",
    "builder_read_model",
    "create_draft",
    "duplicate_instance",
    "get_draft",
    "get_draft_revision",
    "list_drafts",
    "new_draft_id",
    "new_instance_id",
    "parse_composition",
    "remove_instance",
    "reorder_instance",
    "replace_component_version",
    "update_config",
    "update_draft",
]
