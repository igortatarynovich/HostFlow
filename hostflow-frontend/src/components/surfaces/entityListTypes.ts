import type { ReactNode } from 'react'

/** Field kind for columns and filters (ADR-010 §3). */
export type EntityListFieldKind =
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

export type EntityListColumnDef<T = unknown> = {
  id: string
  fieldId: string
  kind: EntityListFieldKind
  label: string
  sortable?: boolean
  /** Domain renders the cell — shell never imports business cells. */
  cell?: (row: T) => ReactNode
}

export type EntityListFilterDef = {
  id: string
  fieldId: string
  kind: EntityListFieldKind
  label: string
}

/** Per-resource table config; lives in module, passed into list page — not into shell root. */
export type EntityListDefinition<T = unknown> = {
  resourceId: string
  columns: EntityListColumnDef<T>[]
  filters?: EntityListFilterDef[]
  density?: 'comfortable' | 'compact'
}

export type EntityListPaginationState = {
  page: number
  pageSize: number
  total: number
  onPageChange: (page: number) => void
  onPageSizeChange?: (size: number) => void
}

/** Controlled selection — state owned by list page / hook. */
export type EntityListSelectionState = {
  selectedCount: number
  onClearSelection: () => void
}

/**
 * ADR-010 zone slots. Empty zones are omitted; order is fixed in EntityListShell.
 * Domain supplies React nodes — no boolean toggles on shell.
 */
export type EntityListZones = {
  header?: ReactNode
  insights?: ReactNode
  toolbar?: ReactNode
  activeFilters?: ReactNode
  /** Table markup and row cells — domain-owned. */
  table: ReactNode
  pagination?: ReactNode
  /** Bulk actions UI; shell shows the zone only when selection is active. */
  bulkBar?: ReactNode
}

export type EntityListShellProps = {
  zones: EntityListZones
  selection?: EntityListSelectionState
  /** Accessible name for the list region (e.g. resource id). */
  resourceLabel?: string
  className?: string
}

export type EntityListTableFrameStatus = 'ready' | 'loading' | 'empty' | 'error'

export type EntityListTableFrameProps = {
  status: EntityListTableFrameStatus
  table?: ReactNode
  loading?: ReactNode
  empty?: ReactNode
  error?: ReactNode
  className?: string
}
