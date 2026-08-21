import type { MouseEvent, ReactNode } from 'react'

import {
  DataTable,
  type DataTableColumn,
  type DataTableSelection,
  type DataTableSortState,
} from '../../components/ui/DataTable'
import { LIST_REPRESENTATION_TABLE, type ListRepresentationId } from './types'

export type ListRepresentationRenderProps<T> = {
  representation: ListRepresentationId
  columns: DataTableColumn<T>[]
  rows: T[]
  rowKey: (row: T) => string
  loading?: boolean
  emptyState?: ReactNode
  onRowClick?: (row: T, index: number, event: MouseEvent<HTMLTableRowElement>) => void
  isRowActive?: (row: T) => boolean
  selection?: DataTableSelection
  sort: DataTableSortState | null
  onSortChange?: (next: DataTableSortState) => void
  ariaLabel?: string
  resourceId: string
}

/**
 * Representation registry. DataTable is the table renderer — not ListWorkspace itself.
 * Unknown ids fall back to table; they must not invent a second table stack.
 */
export function renderListRepresentation<T>(props: ListRepresentationRenderProps<T>) {
  const representation = props.representation || LIST_REPRESENTATION_TABLE
  if (representation !== LIST_REPRESENTATION_TABLE) {
    return renderTableRepresentation(props)
  }
  return renderTableRepresentation(props)
}

function renderTableRepresentation<T>({
  columns,
  rows,
  rowKey,
  loading,
  emptyState,
  onRowClick,
  isRowActive,
  selection,
  sort,
  onSortChange,
  ariaLabel,
  resourceId,
}: ListRepresentationRenderProps<T>) {
  return (
    <DataTable
      columns={columns}
      rows={rows}
      rowKey={rowKey}
      loading={loading}
      emptyState={emptyState}
      onRowClick={onRowClick}
      isRowActive={isRowActive}
      selection={selection}
      sort={sort}
      onSortChange={onSortChange}
      ariaLabel={ariaLabel ?? resourceId}
      resourceId={resourceId}
    />
  )
}

export function isRegisteredListRepresentation(id: string): id is ListRepresentationId {
  return id === LIST_REPRESENTATION_TABLE
}
