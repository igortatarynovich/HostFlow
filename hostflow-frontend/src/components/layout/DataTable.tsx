import type { ReactNode } from 'react'
import clsx from 'clsx'

export type DataTableAlign = 'left' | 'right' | 'center'

export interface DataTableColumn<T> {
  /** Stable key for the column. */
  key: string
  /** Header cell content. */
  header: ReactNode
  /** Cell renderer for a row. */
  render: (row: T, index: number) => ReactNode
  /** Fixed column width (px number or CSS width). */
  width?: number | string
  minWidth?: number | string
  align?: DataTableAlign
  /** Tighter horizontal padding (px-3) for high-density columns. */
  compact?: boolean
  /** Right-aligned numeric columns get tabular figures. */
  tabularNums?: boolean
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

export interface DataTableProps<T> {
  columns: DataTableColumn<T>[]
  rows: T[]
  rowKey: (row: T) => string
  onRowClick?: (row: T) => void
  isRowActive?: (row: T) => boolean
  rowClassName?: (row: T) => string | undefined
  loading?: boolean
  /** Rendered inside the table body when there are no rows and not loading. */
  emptyState?: ReactNode
  /** Optional footer strip (row counts, pagination). */
  footer?: ReactNode
  /** Optional leading checkbox column for bulk selection. */
  selection?: DataTableSelection
  className?: string
  ariaLabel?: string
}

function alignClass(align?: DataTableAlign) {
  if (align === 'right') return 'text-right'
  if (align === 'center') return 'text-center'
  return undefined
}

const CHECKBOX_WIDTH = 56

/**
 * Unified list table, modelled 1:1 on the Candidates table so every module
 * shares identical density, borders, sticky header, hover and scroll behaviour.
 *
 * - Card surface: `card m-0 flex-1` (full-bleed inside `PageShell`).
 * - Scroll: single `overflow-auto` viewport (horizontal + vertical).
 * - Header: sticky `h-11` slate row, `text-xs font-semibold`.
 * - Cells: `px-4 py-3` (`px-3` for `compact` columns), `text-sm`.
 * - Rows: `border-t`, `hover:bg-brand-50/50`, active row highlighted.
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
  className,
  ariaLabel,
}: DataTableProps<T>) {
  const totalColumns = columns.length + (selection ? 1 : 0)

  return (
    <div
      className={clsx(
        'card relative m-0 flex min-h-0 flex-1 flex-col rounded-lg border border-slate-200 bg-white shadow-sm',
        className,
      )}
    >
      <div className="min-h-0 flex-1 overflow-auto overscroll-contain rounded-b-lg">
        <table
          aria-label={ariaLabel}
          className="min-w-full border-separate border-spacing-0 text-sm"
        >
          <thead className="sticky top-0 z-10 bg-slate-50 shadow-[inset_0_-1px_0_0_rgb(226_232_240)]">
            <tr className="h-11 bg-slate-50 text-left">
              {selection ? (
                <th
                  scope="col"
                  className="border-b border-r border-slate-200 px-4 py-3 align-middle"
                  style={{ width: CHECKBOX_WIDTH, minWidth: CHECKBOX_WIDTH, maxWidth: CHECKBOX_WIDTH }}
                >
                  <input
                    type="checkbox"
                    aria-label="Select all rows"
                    checked={selection.allSelected}
                    ref={(el) => {
                      if (el) el.indeterminate = Boolean(selection.someSelected) && !selection.allSelected
                    }}
                    onChange={(e) => selection.onToggleAll(e.target.checked)}
                  />
                </th>
              ) : null}
              {columns.map((col, colIndex) => {
                const isLast = colIndex === columns.length - 1
                return (
                  <th
                    key={col.key}
                    scope="col"
                    style={{ width: col.width, minWidth: col.minWidth }}
                    className={clsx(
                      'border-b border-slate-200 align-middle whitespace-nowrap text-xs font-semibold text-slate-600',
                      col.compact ? 'px-3 py-3' : 'px-4 py-3',
                      !isLast && 'border-r',
                      alignClass(col.align),
                      col.headerClassName,
                    )}
                  >
                    {col.header}
                  </th>
                )
              })}
            </tr>
          </thead>
          <tbody>
            {loading ? (
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
                return (
                  <tr
                    key={id}
                    onClick={onRowClick ? () => onRowClick(row) : undefined}
                    className={clsx(
                      'border-t border-slate-200/90 transition-colors duration-150',
                      onRowClick && 'cursor-pointer',
                      active
                        ? 'border-l-[3px] border-l-brand-600 bg-brand-50/90'
                        : onRowClick && 'hover:bg-brand-50/50',
                      rowClassName?.(row),
                    )}
                  >
                    {selection ? (
                      <td
                        className="border-r border-slate-200 px-4 py-3 align-middle"
                        style={{ width: CHECKBOX_WIDTH, minWidth: CHECKBOX_WIDTH, maxWidth: CHECKBOX_WIDTH }}
                        onClick={(e) => e.stopPropagation()}
                      >
                        <input
                          type="checkbox"
                          aria-label="Select row"
                          checked={selection.isSelected(id)}
                          onChange={(e) => selection.onToggle(id, e.target.checked)}
                        />
                      </td>
                    ) : null}
                    {columns.map((col, colIndex) => {
                      const isLast = colIndex === columns.length - 1
                      return (
                        <td
                          key={col.key}
                          style={{ width: col.width, minWidth: col.minWidth }}
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
                  </tr>
                )
              })
            )}
          </tbody>
        </table>
      </div>
      {footer ? (
        <div className="shrink-0 border-t border-slate-200/80 px-4 pb-4 pt-3 text-sm leading-relaxed text-slate-600">
          {footer}
        </div>
      ) : null}
    </div>
  )
}
