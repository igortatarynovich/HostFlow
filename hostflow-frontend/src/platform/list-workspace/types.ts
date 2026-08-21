import type { ReactNode } from 'react'

import type { DataTableAlign } from '../../components/ui/DataTable'

/** Kit-layer id — platform capability, not a widget. */
export const COLLECTION_ORCHESTRATION_ID = 'collection_orchestration' as const

/** Only registered representation in this slice. Others must register, not fork DataTable. */
export const LIST_REPRESENTATION_TABLE = 'table' as const

export type ListRepresentationId = typeof LIST_REPRESENTATION_TABLE

export type ListFieldKind =
  | 'text'
  | 'number'
  | 'date'
  | 'datetime'
  | 'boolean'
  | 'enum'
  | 'ref'
  | 'user'
  | 'tags'
  | 'custom'

export type ListFilterWidget = 'chips' | 'text'

export type ListFilterOption = {
  value: string
  label: string
}

export type ListFilterDef = {
  fieldId: string
  kind: ListFieldKind
  label: string
  /** URL / saved-view key. Defaults to `fieldId`. */
  urlKey?: string
  /** API query key when different from `urlKey`. */
  queryKey?: string
  widget: ListFilterWidget
  placeholder?: string
  options?: ListFilterOption[]
}

export type ListColumnDef<T> = {
  id: string
  fieldId: string
  kind: ListFieldKind
  label: string
  sortable?: boolean
  /** API `order_by` when it differs from `fieldId`. */
  sortField?: string
  defaultSortDirection?: 'asc' | 'desc'
  defaultHidden?: boolean
  align?: DataTableAlign
  compact?: boolean
  tabularNums?: boolean
  cellClassName?: string
  cell: (row: T) => ReactNode
}

export type ListBulkAction = {
  id: string
  label: string
  groupId?: string
  groupLabel?: string
  onAction: (selectedIds: string[]) => void | Promise<void>
}

export type ListSavedViewRecord = {
  id: string
  name: string
  isDefault?: boolean
  /** URL-shaped snapshot (`q`, `sort`, `dir`, filter keys). */
  query: Record<string, string>
}

export type ListQueryState = {
  q: string
  filters: Record<string, string>
  sortColumnId: string
  sortDirection: 'asc' | 'desc'
  page: number
  pageSize: number
  representation: ListRepresentationId
}

export type ListDefinitionCopy = {
  searchPlaceholder?: string
  resetLabel?: string
  saveViewLabel?: string
  saveViewPrompt?: string
  columnsLabel?: string
  untitledViewLabel?: string
  removeViewLabel?: string
  bulkSelectedLabel?: (count: number) => string
  bulkClearLabel?: string
  previousPageLabel?: string
  nextPageLabel?: string
  pageLabel?: (page: number, totalPages: number) => string
  paginationSummary?: (total: number) => ReactNode
}

export type ListDefinition<T> = {
  resourceId: string
  columns: ListColumnDef<T>[]
  density?: 'comfortable' | 'compact'
  pagination?: {
    mode: 'paged' | 'infinite'
    pageSize?: number
  }
  search?: {
    enabled?: boolean
    debounceMs?: number
    urlKey?: string
  }
  filters?: ListFilterDef[]
  sort?: {
    defaultColumnId: string
    defaultDirection: 'asc' | 'desc'
  }
  selection?: {
    enabled?: boolean
  }
  bulkActions?: ListBulkAction[]
  savedViews?: {
    enabled?: boolean
    views: ListSavedViewRecord[]
    onSave?: (view: ListSavedViewRecord, nextViews: ListSavedViewRecord[]) => void | Promise<void>
    onRemove?: (id: string, nextViews: ListSavedViewRecord[]) => void | Promise<void>
  }
  representations?: ListRepresentationId[]
  defaultRepresentation?: ListRepresentationId
  copy?: ListDefinitionCopy
}

export type ListWorkspaceLabels = ListDefinitionCopy
