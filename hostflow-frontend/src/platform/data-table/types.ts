/**
 * HostFlow UI Platform — DataTable Engine contracts.
 * Module-agnostic: describes fields, not domain entities.
 */

import type { ReactNode } from 'react'
import type { StatusBadgeSemantic } from '../../components/ui/statusBadgeSemantics'
import type { EntityLinkDescriptor } from '../entity-links'

export type { EntityLinkDescriptor, EntityLinkRole } from '../entity-links'

/** Field value kind — drives filter UI and default cell renderer. */
export type FieldKind =
  | 'text'
  | 'number'
  | 'date'
  | 'datetime'
  | 'boolean'
  | 'enum'
  | 'ref'
  | 'user'
  | 'tags'
  | 'money'
  | 'custom'

/** Semantic color role — maps to platform badge palette (never raw Tailwind in pages). */
export type SemanticRole =
  | 'process_stage'
  | 'status'
  | 'source'
  | 'priority'
  | 'blocker'
  | 'success'
  | 'warning'
  | 'object_type'
  | 'neutral'

export type FieldDescriptor = {
  id: string
  label: string
  kind: FieldKind
  sortable?: boolean
  filterable?: boolean
  searchable?: boolean
  defaultWidth?: number
  pinned?: 'left' | 'right' | false
  semanticRole?: SemanticRole
  /** Maps enum/ref raw values → semantic role override */
  valueSemanticMap?: Record<string, SemanticRole>
  renderer?: string
}

export type ResourceSchema = {
  resourceId: string
  /** Entity Workspace links — primary + secondary (not a single column field). */
  entityLinks: EntityLinkDescriptor[]
  fields: FieldDescriptor[]
  /** field ids visible by default */
  defaultVisibleFieldIds: string[]
  defaultFieldOrder: string[]
  searchableFieldIds: string[]
  defaultColumnWidths?: Record<string, number>
}

export type FacetValue = {
  value: string
  label: string
  count: number
}

export type FacetMap = Record<string, FacetValue[]>

export type FacetFilterOption = {
  value: string
  label: string
  count?: number
}

export type DataTableSortState = {
  fieldId: string
  direction: 'asc' | 'desc'
}

export type ColumnVisibilityState = Record<string, boolean>

export type DataTableColumnLayoutState = {
  visibility: ColumnVisibilityState
  order: string[]
  widths: Record<string, number>
  orderedVisibleFieldIds: string[]
  getFieldWidth: (fieldId: string) => number
  setVisibility: (next: ColumnVisibilityState) => void
  toggleFieldVisible: (fieldId: string, visible: boolean) => void
  reorderFields: (fromId: string, toId: string) => void
  moveFieldRelative: (fieldId: string, delta: -1 | 1) => void
  handleResizeStart: (fieldId: string, clientX: number) => void
  resetLayout: () => void
  applyPersistedLayout: (payload: { order?: string[] | null; widths?: Record<string, number> | null; visibility?: ColumnVisibilityState | null }) => void
  draggingFieldId: string | null
  setDraggingFieldId: (id: string | null) => void
  dragOverFieldId: string | null
  setDragOverFieldId: (id: string | null) => void
}

export type DataTableEngineProps<TRow> = {
  schema: ResourceSchema
  layout: DataTableColumnLayoutState
  rows: TRow[]
  rowKey: (row: TRow) => string
  loading?: boolean
  emptyState?: ReactNode
  footer?: ReactNode
  /** Customize mode: drag reorder + resize handles in header */
  layoutCustomize?: boolean
  customizeBanner?: ReactNode
  loadingOverlay?: ReactNode
  ariaLabel?: string
  /** Leading column (e.g. checkbox) — not part of schema fields */
  renderLeadingHeader?: () => ReactNode
  renderLeadingCell?: (row: TRow, index: number) => ReactNode
  renderFieldHeader: (fieldId: string) => ReactNode
  renderFieldCell?: (fieldId: string, row: TRow, index: number) => ReactNode
  renderHeaderResizeHandle?: (fieldId: string) => ReactNode
  getRowClassName?: (row: TRow, index: number) => string | undefined
  onRowClick?: (row: TRow, index: number, event: React.MouseEvent<HTMLTableRowElement>) => void
  onRowMouseDown?: (row: TRow, index: number, event: React.MouseEvent<HTMLTableRowElement>) => void
  onRowContextMenu?: (row: TRow, index: number, event: React.MouseEvent<HTMLTableRowElement>) => void
  getRowRef?: (row: TRow, index: number, node: HTMLTableRowElement | null) => void
  getRowDataAttrs?: (row: TRow, index: number) => Record<string, string | undefined>
  /** Full `<tr>` cell content — when set, renderFieldCell / renderLeadingCell are ignored */
  renderBodyRow?: (row: TRow, index: number) => ReactNode
}

export type SemanticRolePalette = Record<SemanticRole, StatusBadgeSemantic>
