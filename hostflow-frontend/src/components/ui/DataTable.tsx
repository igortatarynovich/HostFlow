import type { MouseEvent, ReactNode } from 'react'
import clsx from 'clsx'

import { Checkbox } from './Checkbox'
import { ColumnDragGlyph } from './kitGlyphs'
import { SortControl, type SortControlDirection } from './SortControl'

export type DataTableAlign = 'left' | 'right' | 'center'

export const DATA_TABLE_SURFACE_CLASS =
  'card relative m-0 flex min-h-0 flex-1 flex-col rounded-lg border border-slate-200 bg-white shadow-sm'

export const DATA_TABLE_SCROLL_CLASS =
  'min-h-0 flex-1 overflow-auto overscroll-contain rounded-b-lg'

export const DATA_TABLE_FOOTER_CLASS =
  'shrink-0 border-t border-slate-200/80 px-4 pb-4 pt-3 text-sm leading-relaxed text-slate-600'

const CHECKBOX_WIDTH = 56

export interface DataTableColumn<T> {
  /** Stable key for the column (`field_id`). */
  key: string
  /** Header cell content. Use a label when `sortable` — `SortControl` wraps it. */
  header: ReactNode
  /** Cell renderer for a row. Domain cells stay in the module. */
  render: (row: T, index: number) => ReactNode
  width?: number | string
  minWidth?: number | string
  maxWidth?: number | string
  align?: DataTableAlign
  /** Tighter horizontal padding (px-3) for high-density columns. */
  compact?: boolean
  /** Right-aligned numeric columns get tabular figures. */
  tabularNums?: boolean
  sortable?: boolean
  headerClassName?: string
  cellClassName?: string
}

export interface DataTableSelection {
  isSelected: (id: string) => boolean
  onToggle: (id: string, checked: boolean) => void
  onToggleAll: (checked: boolean) => void
  allSelected: boolean
  someSelected?: boolean
}

export type DataTableSortState = {
  columnKey: string
  direction: SortControlDirection
}

/**
 * Optional Candidates / TABLE_V1 column-layout controller (resize, reorder).
 * ListWorkspace (K2) will own persistence; DataTable only renders the frame.
 */
export type DataTableColumnLayout = {
  getColumnWidth: (columnKey: string) => number
  reorderColumns: (fromKey: string, toKey: string) => void
  onResizeStart: (columnKey: string, clientX: number) => void
  draggingColumnKey: string | null
  setDraggingColumnKey: (key: string | null) => void
  dragOverColumnKey: string | null
  setDragOverColumnKey: (key: string | null) => void
}

export interface DataTableProps<T> {
  columns: DataTableColumn<T>[]
  rows: T[]
  rowKey: (row: T) => string
  onRowClick?: (row: T, index: number, event: MouseEvent<HTMLTableRowElement>) => void
  isRowActive?: (row: T) => boolean
  rowClassName?: (row: T, index: number) => string | undefined
  loading?: boolean
  /** Rendered inside the table body when there are no rows and not loading. */
  emptyState?: ReactNode
  /** Optional footer strip (row counts, pagination). */
  footer?: ReactNode
  /** Optional leading checkbox column for bulk selection. */
  selection?: DataTableSelection
  sort?: DataTableSortState | null
  onSortChange?: (next: DataTableSortState) => void
  /** Advanced: resize / reorder. Omit for declarative lists (Vacancies/Companies today). */
  columnLayout?: DataTableColumnLayout
  layoutCustomize?: boolean
  customizeBanner?: ReactNode
  loadingOverlay?: ReactNode
  resourceId?: string
  className?: string
  ariaLabel?: string
  /** Engine compat: custom leading column when `selection` is omitted. */
  renderLeadingHeader?: () => ReactNode
  renderLeadingCell?: (row: T, index: number) => ReactNode
  /** Engine compat: replace `<td>` sequence. */
  renderBodyRow?: (row: T, index: number) => ReactNode
  onRowMouseDown?: (row: T, index: number, event: MouseEvent<HTMLTableRowElement>) => void
  onRowContextMenu?: (row: T, index: number, event: MouseEvent<HTMLTableRowElement>) => void
  getRowRef?: (row: T, index: number, node: HTMLTableRowElement | null) => void
  getRowDataAttrs?: (row: T, index: number) => Record<string, string | undefined>
}

function alignClass(align?: DataTableAlign) {
  if (align === 'right') return 'text-right'
  if (align === 'center') return 'text-center'
  return undefined
}

function columnBoxStyle(
  col: DataTableColumn<unknown>,
  columnLayout?: DataTableColumnLayout,
): { width?: number | string; minWidth?: number | string; maxWidth?: number | string } {
  if (columnLayout) {
    const width = `${columnLayout.getColumnWidth(col.key)}px`
    return { width, minWidth: width, maxWidth: width }
  }
  return { width: col.width, minWidth: col.minWidth, maxWidth: col.maxWidth }
}

/**
 * Public operational DataTable (ADR-044 / TABLE_V1).
 *
 * Capability bar: Candidates (sticky header, selection, sort, column resize/reorder, domain cell slots).
 * First page cutover is Vacancies in K2 — this component does not rewrite Candidates.
 */
export function DataTable<T>({
  columns,
  rows,
  rowKey,
  onRowClick,
  isRowActive,
  rowClassName,
  loading = false,
  emptyState,
  footer,
  selection,
  sort,
  onSortChange,
  columnLayout,
  layoutCustomize = false,
  customizeBanner,
  loadingOverlay,
  resourceId,
  className,
  ariaLabel,
  renderLeadingHeader,
  renderLeadingCell,
  renderBodyRow,
  onRowMouseDown,
  onRowContextMenu,
  getRowRef,
  getRowDataAttrs,
}: DataTableProps<T>) {
  const leading = Boolean(selection || renderLeadingHeader)
  const totalColumns = columns.length + (leading ? 1 : 0)
  const showCustomize = Boolean(layoutCustomize && columnLayout)

  const renderHeaderLabel = (col: DataTableColumn<T>) => {
    if (!col.sortable || !onSortChange) return col.header
    const active = sort?.columnKey === col.key
    return (
      <SortControl
        label={col.header}
        active={active}
        direction={active ? sort?.direction : 'asc'}
        onClick={() => {
          if (active) {
            onSortChange({
              columnKey: col.key,
              direction: sort?.direction === 'asc' ? 'desc' : 'asc',
            })
            return
          }
          onSortChange({ columnKey: col.key, direction: 'asc' })
        }}
      />
    )
  }

  const renderResizeHandle = (columnKey: string) => {
    if (!showCustomize || !columnLayout) return null
    return (
      <div
        className="absolute right-0 top-0 z-20 h-full w-1 cursor-col-resize bg-transparent transition-colors hover:bg-brand-400"
        onMouseDown={(e) => {
          e.preventDefault()
          e.stopPropagation()
          columnLayout.onResizeStart(columnKey, e.clientX)
        }}
      />
    )
  }

  const renderDataHeader = (col: DataTableColumn<T>, colIndex: number) => {
    const isLast = colIndex === columns.length - 1
    const style = columnBoxStyle(col as DataTableColumn<unknown>, columnLayout)
    const pad = col.compact ? 'px-3 py-3' : 'px-4 py-3'
    const ariaSort = col.sortable
      ? sort?.columnKey === col.key
        ? sort.direction === 'asc'
          ? 'ascending'
          : 'descending'
        : 'none'
      : undefined

    if (!showCustomize || !columnLayout) {
      return (
        <th
          key={col.key}
          scope="col"
          aria-sort={ariaSort}
          style={style}
          className={clsx(
            'border-b border-slate-200 align-middle whitespace-nowrap text-xs font-semibold text-slate-600',
            pad,
            !isLast && 'border-r',
            alignClass(col.align),
            col.headerClassName,
          )}
        >
          {renderHeaderLabel(col)}
        </th>
      )
    }

    const isDragOver =
      columnLayout.dragOverColumnKey === col.key &&
      columnLayout.draggingColumnKey &&
      columnLayout.draggingColumnKey !== col.key

    return (
      <th
        key={col.key}
        scope="col"
        aria-sort={ariaSort}
        style={style}
        className={clsx(
          'group relative cursor-default border-r border-slate-200 py-3 align-middle whitespace-nowrap pointer-events-auto',
          'pl-2 pr-4',
          isDragOver && 'bg-brand-100/70',
          alignClass(col.align),
          col.headerClassName,
        )}
        onDragOver={(e) => {
          if (!columnLayout.draggingColumnKey || columnLayout.draggingColumnKey === col.key) return
          e.preventDefault()
          e.stopPropagation()
          e.dataTransfer.dropEffect = 'move'
          if (columnLayout.dragOverColumnKey !== col.key) columnLayout.setDragOverColumnKey(col.key)
        }}
        onDragEnter={(e) => {
          if (!columnLayout.draggingColumnKey || columnLayout.draggingColumnKey === col.key) return
          e.preventDefault()
        }}
        onDrop={(e) => {
          e.preventDefault()
          e.stopPropagation()
          const from =
            columnLayout.draggingColumnKey ||
            e.dataTransfer.getData('text/plain') ||
            e.dataTransfer.getData('application/x-hostflow-column')
          if (from) columnLayout.reorderColumns(from, col.key)
          columnLayout.setDragOverColumnKey(null)
          columnLayout.setDraggingColumnKey(null)
        }}
        onDragLeave={(e) => {
          const next = e.relatedTarget as Node | null
          if (next && (e.currentTarget as HTMLElement).contains(next)) return
          if (columnLayout.dragOverColumnKey === col.key) columnLayout.setDragOverColumnKey(null)
        }}
      >
        <div className="flex min-h-[34px] items-stretch justify-between gap-1">
          <div className="flex min-h-[34px] min-w-0 flex-1 items-center gap-2 overflow-hidden">
            <span
              role="button"
              tabIndex={0}
              draggable
              className="inline-flex h-8 w-7 shrink-0 cursor-grab select-none items-center justify-center rounded-lg border border-slate-200 bg-slate-100/95 text-slate-600 shadow-sm hover:border-brand-300 hover:bg-brand-50 hover:text-brand-800 active:cursor-grabbing"
              onDragStart={(e) => {
                columnLayout.setDraggingColumnKey(col.key)
                columnLayout.setDragOverColumnKey(null)
                e.dataTransfer.effectAllowed = 'move'
                e.dataTransfer.setData('text/plain', col.key)
                e.dataTransfer.setData('application/x-hostflow-column', col.key)
                try {
                  const canvas = document.createElement('canvas')
                  canvas.width = 1
                  canvas.height = 1
                  e.dataTransfer.setDragImage(canvas, 0, 0)
                } catch {
                  /* ignore */
                }
              }}
              onDragEnd={() => {
                columnLayout.setDraggingColumnKey(null)
                columnLayout.setDragOverColumnKey(null)
              }}
              onClick={(e) => e.stopPropagation()}
            >
              <ColumnDragGlyph />
            </span>
            <div className="flex min-h-8 min-w-0 flex-1 items-center gap-2 overflow-hidden whitespace-nowrap text-xs font-semibold text-slate-600">
              {renderHeaderLabel(col)}
            </div>
          </div>
        </div>
        {renderResizeHandle(col.key)}
      </th>
    )
  }

  return (
    <div
      className={clsx(DATA_TABLE_SURFACE_CLASS, className)}
      data-datatable="v1"
      data-resource-id={resourceId}
    >
      {showCustomize && customizeBanner ? (
        <div className="border-b border-brand-200/80 bg-brand-50 px-3 py-2 text-[11px] font-medium text-brand-900">
          {customizeBanner}
        </div>
      ) : null}
      {loadingOverlay}
      <div className={DATA_TABLE_SCROLL_CLASS}>
        <table aria-label={ariaLabel} className="min-w-full border-separate border-spacing-0 text-sm">
          <thead className="sticky top-0 z-10 bg-slate-50 shadow-[inset_0_-1px_0_0_rgb(226_232_240)]">
            <tr className="h-11 bg-slate-50 text-left">
              {selection ? (
                <th
                  scope="col"
                  className="border-b border-r border-slate-200 px-4 py-3 align-middle"
                  style={{ width: CHECKBOX_WIDTH, minWidth: CHECKBOX_WIDTH, maxWidth: CHECKBOX_WIDTH }}
                >
                  <Checkbox
                    aria-label="Select all rows"
                    checked={selection.allSelected}
                    indeterminate={Boolean(selection.someSelected) && !selection.allSelected}
                    onChange={(e) => selection.onToggleAll(e.target.checked)}
                  />
                </th>
              ) : renderLeadingHeader ? (
                <th
                  scope="col"
                  className="border-b border-r border-slate-200 px-4 py-3 align-middle whitespace-nowrap"
                  style={{ width: CHECKBOX_WIDTH, minWidth: CHECKBOX_WIDTH, maxWidth: CHECKBOX_WIDTH }}
                >
                  {renderLeadingHeader()}
                </th>
              ) : null}
              {columns.map((col, colIndex) => renderDataHeader(col, colIndex))}
            </tr>
          </thead>
          <tbody>
            {loading && rows.length === 0 ? (
              <tr>
                <td colSpan={totalColumns} className="px-4 py-12 text-center text-slate-500">
                  <span className="inline-flex items-center gap-2 text-sm">
                    <span className="h-4 w-4 animate-spin rounded-full border-2 border-slate-300 border-t-brand-500" />
                    Loading…
                  </span>
                </td>
              </tr>
            ) : rows.length === 0 ? (
              <tr>
                <td colSpan={totalColumns} className="px-4 py-12 text-center text-slate-500">
                  {emptyState ?? 'No records'}
                </td>
              </tr>
            ) : (
              rows.map((row, rowIndex) => {
                const id = rowKey(row)
                const active = isRowActive?.(row) ?? false
                const dataAttrs = getRowDataAttrs?.(row, rowIndex) ?? {}
                return (
                  <tr
                    key={id}
                    ref={(node) => getRowRef?.(row, rowIndex, node)}
                    {...Object.fromEntries(Object.entries(dataAttrs).filter(([, v]) => v != null))}
                    tabIndex={onRowClick || onRowMouseDown ? -1 : undefined}
                    onMouseDown={onRowMouseDown ? (e) => onRowMouseDown(row, rowIndex, e) : undefined}
                    onClick={onRowClick ? (e) => onRowClick(row, rowIndex, e) : undefined}
                    onContextMenu={onRowContextMenu ? (e) => onRowContextMenu(row, rowIndex, e) : undefined}
                    className={clsx(
                      'border-t border-slate-200/90 transition-colors duration-150',
                      onRowClick && 'cursor-pointer',
                      active
                        ? 'border-l-[3px] border-l-brand-600 bg-brand-50/90'
                        : onRowClick && 'hover:bg-brand-50/50',
                      rowClassName?.(row, rowIndex),
                    )}
                  >
                    {renderBodyRow ? (
                      renderBodyRow(row, rowIndex)
                    ) : (
                      <>
                        {selection ? (
                          <td
                            className="border-r border-slate-200 px-4 py-3 align-middle"
                            style={{ width: CHECKBOX_WIDTH, minWidth: CHECKBOX_WIDTH, maxWidth: CHECKBOX_WIDTH }}
                            onClick={(e) => e.stopPropagation()}
                          >
                            <Checkbox
                              aria-label="Select row"
                              checked={selection.isSelected(id)}
                              onChange={(e) => selection.onToggle(id, e.target.checked)}
                            />
                          </td>
                        ) : renderLeadingCell ? (
                          renderLeadingCell(row, rowIndex)
                        ) : null}
                        {columns.map((col, colIndex) => {
                          const isLast = colIndex === columns.length - 1
                          const style = columnBoxStyle(col as DataTableColumn<unknown>, columnLayout)
                          return (
                            <td
                              key={col.key}
                              style={style}
                              className={clsx(
                                'border-slate-200 align-middle',
                                col.compact ? 'px-3 py-3' : 'px-4 py-3',
                                !isLast && 'border-r',
                                alignClass(col.align),
                                col.tabularNums && 'tabular-nums',
                                col.cellClassName,
                              )}
                            >
                              {col.render(row, rowIndex)}
                            </td>
                          )
                        })}
                      </>
                    )}
                  </tr>
                )
              })
            )}
          </tbody>
        </table>
      </div>
      {footer ? <div className={DATA_TABLE_FOOTER_CLASS}>{footer}</div> : null}
    </div>
  )
}
