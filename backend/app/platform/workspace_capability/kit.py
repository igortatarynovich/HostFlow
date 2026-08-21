"""Platform kit — data types, fields, primitives, widgets, tables.

Summary (gate-checked against Field Registry manifests):
16 data types · 6 primitives · 78 fields · 16 widgets · 1 table frame · 2 hosts

Not a fifth capability class. Field types reference Field Registry §4.
Fields stay in Field Registry (no parallel dictionary).
Filters belong to ListWorkspace zones — not a filter_bar widget.
Tabs belong to host chrome — not a kit widget.
"""

from __future__ import annotations

KIT_DATA_TYPE_IDS: tuple[str, ...] = (
    "text",
    "textarea",
    "phone_e164",
    "email",
    "date",
    "datetime",
    "boolean",
    "integer",
    "decimal",
    "code",
    "code_alpha2",
    "reference_code",
    "reference_code[]",
    "json_object",
    "computed",
    "custom_field",
)

KIT_FIELD_SOT = "docs/specs/platform/field-registry-card-configuration.md"
KIT_ENTITY_PROFILE_SOT = "docs/specs/platform/entity-profile-definition-registry.md"
KIT_UI_PRIMITIVE_SOT = "docs/specs/frontend/PRIMITIVES_V1.md"
KIT_TABLE_SOT = "docs/specs/frontend/TABLE_V1.md"

KIT_REGISTERED_FIELD_COUNT = 78
KIT_CANDIDATE_FIELD_COUNT = 18
KIT_SALES_UNCANONICAL_TYPE_COUNT = 18

KIT_UI_PRIMITIVE_IDS: tuple[str, ...] = (
    "status_badge",
    "chip",
    "select",
    "button",
    "input",
    "checkbox",
)

KIT_PROOF_BLOCKER_PRIMITIVE_IDS: tuple[str, ...] = ()
KIT_HARDENING_PRIMITIVE_IDS: tuple[str, ...] = ("input_runtime",)

KIT_TABLE_FRAME_IDS: tuple[str, ...] = ("table_v1_entity_list",)

KIT_LIST_WORKSPACE_ZONE_IDS: tuple[str, ...] = (
    "search",
    "filters",
    "sort",
    "pagination",
    "bulk",
    "saved_views",
)

KIT_HOST_NAVIGATION_SOT = (
    "host_chrome: EntityWorkspaceNavTabs | ListWorkspaceStatusTabs | ApplicationWorkspace tabs"
)

KIT_WIDGET_CLASS_IDS: tuple[str, ...] = (
    "field_row",
    "identity_header",
    "status_projection",
    "summary_cards",
    "contacts",
    "notes",
    "consent",
    "tasks",
    "relations",
    "decision_zone",
    "context_rail",
    "data_table",
    "timeline",
    "communication",
    "forms",
    "documents",
)

KIT_WIDGET_GAP_IDS: tuple[str, ...] = ("modal", "radio", "toggle")

KIT_LAYER_ORDER: tuple[str, ...] = (
    "data_types",
    "fields",
    "ui_primitives",
    "widgets",
    "tables",
    "hosts",
)
