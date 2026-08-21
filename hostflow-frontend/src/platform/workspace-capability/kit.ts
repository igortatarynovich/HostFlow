/**
 * Platform kit — what every screen is assembled FROM.
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

/** PRIMITIVES_V1 locked families. Checkbox/Radio/Toggle are gaps, not silent locals. */
export const KIT_UI_PRIMITIVE_IDS = [
  'status_badge',
  'chip',
  'select',
  'button',
  'input',
] as const

export type KitUiPrimitiveId = (typeof KIT_UI_PRIMITIVE_IDS)[number]

export const KIT_UI_PRIMITIVE_SOT = 'docs/specs/frontend/PRIMITIVES_V1.md' as const

export const KIT_TABLE_FRAME_IDS = ['table_v1_entity_list'] as const

export type KitTableFrameId = (typeof KIT_TABLE_FRAME_IDS)[number]

export const KIT_TABLE_SOT = 'docs/specs/frontend/TABLE_V1.md' as const

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

/** Named, not invented locally. Runtime of these is a later named slice. */
export const KIT_WIDGET_GAP_IDS = [
  'filter_bar',
  'modal',
  'checkbox',
  'radio',
  'toggle',
] as const

export type KitWidgetGapId = (typeof KIT_WIDGET_GAP_IDS)[number]

export const KIT_LAYER_ORDER = [
  'data_types',
  'fields',
  'ui_primitives',
  'widgets',
  'tables',
  'hosts',
] as const
