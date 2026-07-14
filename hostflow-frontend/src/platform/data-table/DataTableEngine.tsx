import clsx from 'clsx'
import type { DataTableEngineProps } from './types'

const CHECKBOX_WIDTH = 56

/**
 * Universal DataTable Engine — module-agnostic list shell.
 * Domain cell/header rendering is supplied by the consumer via render props.
 */
export function DataTableEngine<TRow>({
  schema,
  layout,
  rows,
  rowKey,
  loading = false,
  emptyState,
  footer,
  layoutCustomize = false,
  customizeBanner,
  loadingOverlay,
  ariaLabel,
  renderLeadingHeader,
  renderLeadingCell,
  renderFieldHeader,
  renderFieldCell,
  renderHeaderResizeHandle,
  getRowClassName,
  onRowClick,
  onRowMouseDown,
  onRowContextMenu,
  getRowRef,
  getRowDataAttrs,
  renderBodyRow,
}: DataTableEngineProps<TRow>) {
  const visibleFieldIds = layout.orderedVisibleFieldIds.filter((id) => layout.visibility[id])
  const totalColumns = visibleFieldIds.length + (renderLeadingHeader ? 1 : 0)

  const renderDraggableHeader = (fieldId: string) => {
    const width = layout.getFieldWidth(fieldId)
    const className = clsx(
      'group relative cursor-default border-r border-slate-200 py-3 align-middle whitespace-nowrap pointer-events-auto',
      layoutCustomize ? 'pl-2 pr-4' : 'px-4',
      layoutCustomize &&
        layout.dragOverFieldId === fieldId &&
        layout.draggingFieldId &&
        layout.draggingFieldId !== fieldId &&
        'bg-brand-100/70',
    )
    const style = { width: `${width}px`, minWidth: `${width}px`, maxWidth: `${width}px` }

    if (!layoutCustomize) {
      return (
        <th key={fieldId} className={className} style={style}>
          <div className="flex h-5 min-w-0 w-full items-center gap-2 overflow-hidden whitespace-nowrap">
            {renderFieldHeader(fieldId)}
          </div>
        </th>
      )
    }

    return (
      <th
        key={fieldId}
        className={className}
        style={style}
        onDragOver={(e) => {
          if (!layout.draggingFieldId || layout.draggingFieldId === fieldId) return
          e.preventDefault()
          e.stopPropagation()
          e.dataTransfer.dropEffect = 'move'
          if (layout.dragOverFieldId !== fieldId) layout.setDragOverFieldId(fieldId)
        }}
        onDragEnter={(e) => {
          if (!layout.draggingFieldId || layout.draggingFieldId === fieldId) return
          e.preventDefault()
        }}
        onDrop={(e) => {
          e.preventDefault()
          e.stopPropagation()
          const from =
            layout.draggingFieldId ||
            e.dataTransfer.getData('text/plain') ||
            e.dataTransfer.getData('application/x-hostflow-column')
          if (from) layout.reorderFields(from, fieldId)
          layout.setDragOverFieldId(null)
          layout.setDraggingFieldId(null)
        }}
        onDragLeave={(e) => {
          const next = e.relatedTarget as Node | null
          if (next && (e.currentTarget as HTMLElement).contains(next)) return
          if (layout.dragOverFieldId === fieldId) layout.setDragOverFieldId(null)
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
                layout.setDraggingFieldId(fieldId)
                layout.setDragOverFieldId(null)
                e.dataTransfer.effectAllowed = 'move'
                e.dataTransfer.setData('text/plain', fieldId)
                e.dataTransfer.setData('application/x-hostflow-column', fieldId)
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
                layout.setDraggingFieldId(null)
                layout.setDragOverFieldId(null)
              }}
              onClick={(e) => e.stopPropagation()}
            >
              <svg width="14" height="18" viewBox="0 0 14 18" fill="currentColor" className="opacity-90" aria-hidden>
                <circle cx="4" cy="3.5" r="1.35" />
                <circle cx="10" cy="3.5" r="1.35" />
                <circle cx="4" cy="9" r="1.35" />
                <circle cx="10" cy="9" r="1.35" />
                <circle cx="4" cy="14.5" r="1.35" />
                <circle cx="10" cy="14.5" r="1.35" />
              </svg>
            </span>
            <div className="flex min-h-8 min-w-0 flex-1 items-center gap-2 overflow-hidden whitespace-nowrap">
              {renderFieldHeader(fieldId)}
            </div>
          </div>
        </div>
        {renderHeaderResizeHandle?.(fieldId)}
      </th>
    )
  }

  return (
    <div
      className="card relative m-0 flex min-h-0 flex-1 flex-col rounded-lg border border-slate-200 bg-white shadow-sm"
      data-resource-id={schema.resourceId}
      data-datatable-engine="v1"
    >
      {layoutCustomize && customizeBanner ? (
        <div className="border-b border-brand-200/80 bg-brand-50 px-3 py-2 text-[11px] font-medium text-brand-900">
          {customizeBanner}
        </div>
      ) : null}
      {loadingOverlay}
      <div className="min-h-0 flex-1 overflow-auto overscroll-contain rounded-b-xl">
        <table aria-label={ariaLabel} className="min-w-full border-separate border-spacing-0 text-sm">
          <thead className="sticky top-0 z-10 bg-slate-50 shadow-[inset_0_-1px_0_0_rgb(226_232_240)]">
            <tr className="h-11 bg-slate-50 text-left">
              {renderLeadingHeader ? (
                <th
                  className="border-r border-slate-200 px-4 py-3 align-middle whitespace-nowrap"
                  style={{ width: CHECKBOX_WIDTH, minWidth: CHECKBOX_WIDTH, maxWidth: CHECKBOX_WIDTH }}
                >
                  {renderLeadingHeader()}
                </th>
              ) : null}
              {visibleFieldIds.map((fieldId) => renderDraggableHeader(fieldId))}
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
              rows.map((row, index) => {
                const id = rowKey(row)
                const dataAttrs = getRowDataAttrs?.(row, index) ?? {}
                return (
                  <tr
                    key={id}
                    ref={(node) => getRowRef?.(row, index, node)}
                    {...Object.fromEntries(Object.entries(dataAttrs).filter(([, v]) => v != null))}
                    tabIndex={-1}
                    onMouseDown={onRowMouseDown ? (e) => onRowMouseDown(row, index, e) : undefined}
                    onClick={onRowClick ? (e) => onRowClick(row, index, e) : undefined}
                    onContextMenu={onRowContextMenu ? (e) => onRowContextMenu(row, index, e) : undefined}
                    className={clsx(
                      'cursor-pointer border-t border-slate-200/90 transition-colors duration-150 hover:bg-brand-50/50',
                      getRowClassName?.(row, index),
                    )}
                  >
                    {renderBodyRow ? (
                      renderBodyRow(row, index)
                    ) : (
                      <>
                        {renderLeadingCell ? renderLeadingCell(row, index) : null}
                        {visibleFieldIds.map((fieldId) => {
                          const width = layout.getFieldWidth(fieldId)
                          return (
                            <td
                              key={fieldId}
                              className="border-r border-slate-200 align-middle px-4 py-3"
                              style={{ width: `${width}px`, minWidth: `${width}px`, maxWidth: `${width}px` }}
                            >
                              {renderFieldCell(fieldId, row, index)}
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
      {footer ? (
        <div className="shrink-0 border-t border-slate-200/80 px-4 pb-4 pt-3 text-sm leading-relaxed text-slate-600">{footer}</div>
      ) : null}
    </div>
  )
}
