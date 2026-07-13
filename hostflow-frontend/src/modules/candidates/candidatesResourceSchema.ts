import type { ResourceSchema } from '../../platform/data-table'
import { DEFAULT_COLUMN_ORDER, DEFAULT_VISIBLE_COLS } from './constants'

export const CANDIDATES_RESOURCE_ID = 'candidates'

type TFn = (key: string, options?: { defaultValue?: string }) => string

const COLUMN_FIELD_DEFS: Array<{
  id: string
  labelKey: string
  defaultLabel: string
  kind: ResourceSchema['fields'][number]['kind']
  sortable?: boolean
  filterable?: boolean
  searchable?: boolean
  semanticRole?: ResourceSchema['fields'][number]['semanticRole']
}> = [
  { id: 'name', labelKey: 'app.candidates.table.name', defaultLabel: 'Name', kind: 'text', sortable: true, searchable: true },
  { id: 'email', labelKey: 'app.candidates.table.email', defaultLabel: 'Email', kind: 'text', sortable: true, searchable: true },
  { id: 'phone', labelKey: 'app.candidates.table.phone', defaultLabel: 'Phone', kind: 'text', sortable: true, searchable: true },
  { id: 'citizenship', labelKey: 'app.candidates.table.citizenship', defaultLabel: 'Citizenship', kind: 'text', sortable: true, filterable: true },
  { id: 'vacancy', labelKey: 'app.candidates.table.vacancy', defaultLabel: 'Vacancy', kind: 'ref', sortable: true, filterable: true },
  { id: 'short', labelKey: 'app.candidates.table.short_id', defaultLabel: 'ID', kind: 'text', sortable: true, searchable: true },
  { id: 'manager', labelKey: 'app.candidates.table.manager', defaultLabel: 'Manager', kind: 'user', sortable: true, filterable: true },
  { id: 'stage', labelKey: 'app.candidates.table.stage', defaultLabel: 'Stage', kind: 'enum', sortable: true, filterable: true, semanticRole: 'process_stage' },
  { id: 'risk', labelKey: 'app.candidates.table.risk', defaultLabel: 'Risk', kind: 'number', sortable: true },
  { id: 'created', labelKey: 'app.candidates.table.created', defaultLabel: 'Created', kind: 'datetime', sortable: true },
  { id: 'firstContact', labelKey: 'app.candidates.table.first_contact', defaultLabel: 'First contact', kind: 'datetime', sortable: true },
  { id: 'preferredChannel', labelKey: 'app.candidates.table.preferred_channel', defaultLabel: 'Channel', kind: 'enum', filterable: true },
  { id: 'inPoland', labelKey: 'app.candidates.table.in_poland', defaultLabel: 'In Poland', kind: 'enum', filterable: true },
  { id: 'polandBasis', labelKey: 'app.candidates.table.poland_basis', defaultLabel: 'Poland basis', kind: 'enum', filterable: true },
  { id: 'trailerTypes', labelKey: 'app.candidates.table.trailer_types', defaultLabel: 'Trailer types', kind: 'tags', filterable: true },
  { id: 'reasons', labelKey: 'app.candidates.table.reasons', defaultLabel: 'Reasons', kind: 'tags', sortable: true, filterable: true },
  { id: 'is_favorite', labelKey: 'app.candidates.table.favorite', defaultLabel: 'Favorite', kind: 'boolean', sortable: true, filterable: true },
  { id: 'docsStatus', labelKey: 'app.candidates.table.docs_status', defaultLabel: 'Documents', kind: 'enum', sortable: true, filterable: true, semanticRole: 'status' },
  { id: 'docsOrdered', labelKey: 'app.candidates.table.docs_ordered', defaultLabel: 'Docs ordered', kind: 'date', sortable: true },
  { id: 'docsValid', labelKey: 'app.candidates.table.docs_valid', defaultLabel: 'Docs valid from', kind: 'date', sortable: true },
  { id: 'docsFiles', labelKey: 'app.candidates.table.docs_files', defaultLabel: 'Docs files', kind: 'boolean', sortable: true },
  { id: 'intakeKind', labelKey: 'app.candidates.table.intake_kind', defaultLabel: 'Intake', kind: 'enum', filterable: true },
]

/** Candidates list → platform ResourceSchema (config only; cells stay in module adapters). */
export function buildCandidatesResourceSchema(t: TFn): ResourceSchema {
  const defaultVisibleFieldIds = Object.entries(DEFAULT_VISIBLE_COLS)
    .filter(([, visible]) => visible)
    .map(([id]) => id)

  return {
    resourceId: CANDIDATES_RESOURCE_ID,
    entityLinks: [
      { id: 'candidate-card', role: 'primary', fieldId: 'name', label: t('app.candidates.table.name', { defaultValue: 'Name' }) },
      { id: 'vacancy-link', role: 'secondary', fieldId: 'vacancy', label: t('app.candidates.table.vacancy', { defaultValue: 'Vacancy' }) },
    ],
    fields: COLUMN_FIELD_DEFS.map((col) => ({
      id: col.id,
      label: t(col.labelKey, { defaultValue: col.defaultLabel }),
      kind: col.kind,
      sortable: col.sortable,
      filterable: col.filterable,
      searchable: col.searchable,
      semanticRole: col.semanticRole,
    })),
    defaultVisibleFieldIds,
    defaultFieldOrder: DEFAULT_COLUMN_ORDER,
    searchableFieldIds: ['name', 'email', 'phone', 'short'],
  }
}
