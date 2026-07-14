/**
 * Entity Model — single source of truth for one business object type.
 *
 * Dependency (strict):
 *   EntityModel → Entity Workspace UI
 *              → Detail Rail projection
 *              → Data Table projection (ResourceSchema)
 *
 * Modules define EntityModel once. Platform derives all surfaces.
 * Detail Rail and Data Table never invent fields or structure.
 */

import type { FieldDescriptor, FieldKind, SemanticRole } from '../data-table/types'

/** Canonical sections of the object passport — fixed platform vocabulary. */
export type EntitySectionId =
  | 'identity'
  | 'state'
  | 'ownership'
  | 'contacts'
  | 'actions'
  | 'documents'
  | 'timeline'
  | 'relations'
  | 'tasks'
  | 'outcome'

export const ENTITY_SECTION_ORDER: readonly EntitySectionId[] = [
  'identity',
  'state',
  'ownership',
  'contacts',
  'actions',
  'documents',
  'timeline',
  'relations',
  'tasks',
  'outcome',
] as const

/** Where a field may appear — platform reads flags, modules do not fork UI. */
export type EntityFieldProjection = {
  /** Collection / list column */
  showInTable?: boolean
  /** Decision Flow Detail Rail */
  showInRail?: boolean
  /** Global / list search */
  showInSearch?: boolean
  /** Entity Workspace summary strip */
  showInEntitySummary?: boolean
  /** Entity Context Rail (right panel in Entity Workspace) */
  showInContextRail?: boolean
  editable?: boolean
  filterable?: boolean
  searchable?: boolean
}

export type EntityFieldDescriptor = FieldDescriptor & {
  section: EntitySectionId
  projection: EntityFieldProjection
}

/**
 * Full digital passport schema for one resource (candidate, client, order, …).
 * Populated from API + module semantics; consumed by all projections.
 */
export type EntityModel = {
  resourceId: string
  /** Enabled sections for this resource — subset of ENTITY_SECTION_ORDER only. */
  sections: readonly EntitySectionId[]
  fields: readonly EntityFieldDescriptor[]
}

/** Build table ResourceSchema from entity model (table = projection). */
export function toResourceSchemaFromEntityModel(model: EntityModel): {
  resourceId: string
  entityLinks: []
  fields: FieldDescriptor[]
  defaultVisibleFieldIds: string[]
  defaultFieldOrder: string[]
  searchableFieldIds: string[]
} {
  const tableFields = model.fields.filter((f) => f.projection.showInTable)
  return {
    resourceId: model.resourceId,
    entityLinks: [],
    fields: tableFields.map(({ section: _section, projection: _projection, ...field }) => field),
    defaultVisibleFieldIds: tableFields.map((f) => f.id),
    defaultFieldOrder: tableFields.map((f) => f.id),
    searchableFieldIds: model.fields.filter((f) => f.projection.searchable).map((f) => f.id),
  }
}

/** Helper for module authors — keeps projection defaults explicit. */
export function entityField(
  partial: Omit<EntityFieldDescriptor, 'projection'> & { projection?: Partial<EntityFieldProjection> },
): EntityFieldDescriptor {
  return {
    ...partial,
    projection: {
      showInTable: false,
      showInRail: false,
      showInSearch: false,
      showInEntitySummary: false,
      editable: false,
      filterable: false,
      searchable: false,
      ...partial.projection,
    },
  }
}

export type { FieldKind, SemanticRole }
