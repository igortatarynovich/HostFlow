/**
 * Platform kit — what every screen is assembled FROM.
 *
 * Summary (gate-checked against Field Registry manifests):
 * 16 data types · 5 primitives · 78 fields · 16 widgets · 1 table frame · 2 hosts
 *
 * Not a fifth capability class. Not a Notes/Consent kit.
 * Data types and fields are references to Field Registry (no second dictionary).
 * UI primitives and tables are references to PRIMITIVES_V1 / TABLE_V1.
 * Widgets are compositions of primitives + fields. Hosts place widgets via contributions.
 *
 * Constitution §0: there are no screens; there are compositions of primitives.
 */

/** Field Registry §4 — canonical types. Do not mint a parallel type list. */
export const KIT_DATA_TYPE_IDS = [
  'text',
  'textarea',
  'phone_e164',
  'email',
  'date',
  'datetime',
  'boolean',
  'integer',
  'decimal',
  'code',
  'code_alpha2',
  'reference_code',
  'reference_code[]',
  'json_object',
  'computed',
  'custom_field',
] as const

export type KitDataTypeId = (typeof KIT_DATA_TYPE_IDS)[number]

export const KIT_FIELD_SOT = 'docs/specs/platform/field-registry-card-configuration.md' as const

export const KIT_ENTITY_PROFILE_SOT =
  'docs/specs/platform/entity-profile-definition-registry.md' as const

/**
 * Snapshot of registered Field Registry rows. Gate asserts these against
 * live manifests — do not edit the numbers without adding a field to a manifest.
 */
export const KIT_REGISTERED_FIELD_COUNT = 78
export const KIT_CANDIDATE_FIELD_COUNT = 18
export const KIT_SALES_UNCANONICAL_TYPE_COUNT = 18

/** PRIMITIVES_V1 locked families. `input` family is locked; runtime wrapper is hardening. */
export const KIT_UI_PRIMITIVE_IDS = [
  'status_badge',
  'chip',
  'select',
  'button',
  'input',
] as const

export type KitUiPrimitiveId = (typeof KIT_UI_PRIMITIVE_IDS)[number]

export const KIT_UI_PRIMITIVE_SOT = 'docs/specs/frontend/PRIMITIVES_V1.md' as const

/**
 * boolean is a canonical data type. Consent proof cannot bind without a
 * checkbox primitive. Local `<input type="checkbox">` is forbidden.
 */
export const KIT_PROOF_BLOCKER_PRIMITIVE_IDS = ['checkbox'] as const

export type KitProofBlockerPrimitiveId = (typeof KIT_PROOF_BLOCKER_PRIMITIVE_IDS)[number]

/**
 * `input` is a locked family (CSS .input/.textarea/.label) but pages can still
 * assemble ad-hoc <input className="input">. Named hardening — not a new family id.
 */
export const KIT_HARDENING_PRIMITIVE_IDS = ['input_runtime'] as const

export type KitHardeningPrimitiveId = (typeof KIT_HARDENING_PRIMITIVE_IDS)[number]

export const KIT_TABLE_FRAME_IDS = ['table_v1_entity_list'] as const

export type KitTableFrameId = (typeof KIT_TABLE_FRAME_IDS)[number]

export const KIT_TABLE_SOT = 'docs/specs/frontend/TABLE_V1.md' as const

/**
 * ListWorkspace orchestration zones (ADR-010 / data-table).
 * Filters already live here. Do not mint a second filter_bar widget.
 * FILTER_BAR_V1, if extracted, is the renderer of zone `filters` — not a new class.
 */
export const KIT_LIST_WORKSPACE_ZONE_IDS = [
  'search',
  'filters',
  'sort',
  'pagination',
  'bulk',
  'saved_views',
] as const

export type KitListWorkspaceZoneId = (typeof KIT_LIST_WORKSPACE_ZONE_IDS)[number]

/**
 * Tabs SoT = host chrome, not a kit widget and not a missing primitive.
 * Entity Workspace K3: EntityWorkspaceNavTabs (navigation zone).
 * List / Application: ListWorkspaceStatusTabs / ApplicationWorkspace tabs.
 * Inventory tabs_* map here. Do not treat Tabs as an existing platform dependency
 * and do not register a tabs widget id.
 */
export const KIT_HOST_NAVIGATION_SOT =
  'host_chrome: EntityWorkspaceNavTabs | ListWorkspaceStatusTabs | ApplicationWorkspace tabs' as const

/**
 * Widget classes — compositions of primitives + fields.
 * Shared capabilities (notes, consent, …) are widgets in this kit, not the whole kit.
 */
export const KIT_WIDGET_CLASS_IDS = [
  'field_row',
  'identity_header',
  'status_projection',
  'summary_cards',
  'contacts',
  'notes',
  'consent',
  'tasks',
  'relations',
  'decision_zone',
  'context_rail',
  'data_table',
  'timeline',
  'communication',
  'forms',
  'documents',
] as const

export type KitWidgetClassId = (typeof KIT_WIDGET_CLASS_IDS)[number]

/** Deferred widgets. Not filter_bar (ListWorkspace). Not tabs (host chrome). Not checkbox (proof blocker primitive). */
export const KIT_WIDGET_GAP_IDS = ['modal', 'radio', 'toggle'] as const

export type KitWidgetGapId = (typeof KIT_WIDGET_GAP_IDS)[number]

export const KIT_LAYER_ORDER = [
  'data_types',
  'fields',
  'ui_primitives',
  'widgets',
  'tables',
  'hosts',
] as const
