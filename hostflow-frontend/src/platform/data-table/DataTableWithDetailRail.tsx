import clsx from 'clsx'
import type { DataTableWithDetailRailProps } from './detailRailTypes'
import { DetailRail } from './DetailRail'

/**
 * @deprecated Compose `useSelectionModel` + `DataTableEngine` + `DetailRail` separately.
 * Table emits entity ids; Selection Model owns rail state; Detail Rail is independent.
 */
export function DataTableWithDetailRail<TRow>({
  toolbar,
  statusTabs,
  filterRow,
  bulkBar,
  selectedRow,
  onSelectedRowChange,
  rowId,
  buildDetailRailModel,
  detailRailLoading = false,
  railWidthPx,
  onDetailRailClose,
  children,
}: DataTableWithDetailRailProps<TRow>) {
  const selectedRowId = selectedRow ? rowId(selectedRow) : null

  const handleClose = () => {
    onSelectedRowChange(null)
    onDetailRailClose?.()
  }

  return (
    <div className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden" data-list-workspace="table-detail-rail-v1">
      {toolbar ? <div className="shrink-0 border-b border-slate-200 bg-white px-4 py-3">{toolbar}</div> : null}
      {statusTabs ? <div className="shrink-0 border-b border-slate-100 bg-white px-4 py-2">{statusTabs}</div> : null}
      {filterRow ? <div className="shrink-0 border-b border-slate-100 bg-slate-50/80 px-4 py-2">{filterRow}</div> : null}
      {bulkBar ? <div className="shrink-0">{bulkBar}</div> : null}

      <div className="flex min-h-0 min-w-0 flex-1 overflow-hidden">
        <div className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden">
          {children({
            selectedRowId,
            onRowSelect: (row) => {
              const id = rowId(row)
              if (selectedRowId === id) {
                onSelectedRowChange(row)
                return
              }
              onSelectedRowChange(row)
            },
            isRowActive: (row) => selectedRowId != null && rowId(row) === selectedRowId,
          })}
        </div>
        <DetailRail
          open={selectedRow != null}
          loading={detailRailLoading}
          onClose={handleClose}
          widthPx={railWidthPx}
          model={selectedRow ? buildDetailRailModel(selectedRow) : null}
        />
      </div>
    </div>
  )
}
