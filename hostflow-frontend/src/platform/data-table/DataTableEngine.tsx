import { DataTable, type DataTableColumn } from '../../components/ui/DataTable'
import type { DataTableEngineProps } from './types'

/**
 * Schema-driven adapter over the public kit `DataTable`.
 * Not a second table — pages must import `DataTable` from `components/ui`.
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
  getRowClassName,
  onRowClick,
  onRowMouseDown,
  onRowContextMenu,
  getRowRef,
  getRowDataAttrs,
  renderBodyRow,
}: DataTableEngineProps<TRow>) {
  const visibleFieldIds = layout.orderedVisibleFieldIds.filter((id) => layout.visibility[id])
  const columns: DataTableColumn<TRow>[] = visibleFieldIds.map((fieldId) => ({
    key: fieldId,
    header: renderFieldHeader(fieldId),
    render: (row, index) => renderFieldCell?.(fieldId, row, index) ?? null,
  }))

  return (
    <DataTable
      columns={columns}
      rows={rows}
      rowKey={rowKey}
      loading={loading}
      emptyState={emptyState}
      footer={footer}
      ariaLabel={ariaLabel}
      resourceId={schema.resourceId}
      layoutCustomize={layoutCustomize}
      customizeBanner={customizeBanner}
      loadingOverlay={loadingOverlay}
      columnLayout={{
        getColumnWidth: layout.getFieldWidth,
        reorderColumns: layout.reorderFields,
        onResizeStart: layout.handleResizeStart,
        draggingColumnKey: layout.draggingFieldId,
        setDraggingColumnKey: layout.setDraggingFieldId,
        dragOverColumnKey: layout.dragOverFieldId,
        setDragOverColumnKey: layout.setDragOverFieldId,
      }}
      renderLeadingHeader={renderLeadingHeader}
      renderLeadingCell={renderLeadingCell}
      renderBodyRow={renderBodyRow}
      rowClassName={getRowClassName}
      onRowClick={onRowClick}
      onRowMouseDown={onRowMouseDown}
      onRowContextMenu={onRowContextMenu}
      getRowRef={getRowRef}
      getRowDataAttrs={getRowDataAttrs}
    />
  )
}
