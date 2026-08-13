import clsx from 'clsx'
import type { FormEvent, MouseEvent, ReactNode, Ref } from 'react'

import { BulkActionBar } from './BulkActionBar'
import { Chip } from './Chip'
import {
  DataTable,
  type DataTableAlign,
  type DataTableColumn,
  type DataTableSelection,
  type DataTableSortState,
} from './DataTable'
import { Pagination } from './Pagination'
import { SearchField } from './SearchField'
import { Toolbar } from '../layout/Toolbar'

/** Field kinds — ADR-010 §3. */
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

export type ListColumnDef<T> = {
  id: string
  fieldId: string
  kind: ListFieldKind
  label: string
  sortable?: boolean
  defaultSortDirection?: 'asc' | 'desc'
  align?: DataTableAlign
  compact?: boolean
  tabularNums?: boolean
  cellClassName?: string
  /** Domain cell — stays in the module. */
  cell: (row: T) => ReactNode
}

export type ListDefinition<T> = {
  resourceId: string
  columns: ListColumnDef<T>[]
  density?: 'comfortable' | 'compact'
  pagination?: 'paged' | 'infinite'
}

export type ListWorkspaceSearch = {
  placeholder?: string
  name?: string
  defaultValue?: string
  value?: string
  onChange?: (value: string) => void
}

export type ListWorkspaceSort = {
  columnKey: string
  direction: 'asc' | 'desc'
  onChange: (next: DataTableSortState) => void
}

export type ListWorkspacePagination = {
  page: number
  pageSize: number
  total: number
  onPageChange: (page: number) => void
  summary?: ReactNode
  previousLabel?: string
  nextLabel?: string
  pageLabel?: (page: number, totalPages: number) => string
}

export type ListWorkspaceSelection = DataTableSelection & {
  selectedCount: number
  onClearSelection: () => void
}

export type SavedViewChipItem = {
  id: string
  name: string
}

export type SavedViewChipsProps = {
  views: SavedViewChipItem[]
  onApply: (view: SavedViewChipItem) => void
  onRemove?: (id: string) => void
  untitledLabel?: string
  removeLabel?: string
}

export function SavedViewChips({
  views,
  onApply,
  onRemove,
  untitledLabel = 'Untitled',
  removeLabel = 'Remove view',
}: SavedViewChipsProps) {
  if (views.length === 0) return null
  return (
    <div className="mx-4 flex flex-wrap items-center gap-2">
      {views.map((view) => (
        <span key={view.id} className="inline-flex items-center gap-1">
          <Chip
            behavior="action"
            size="md"
            label={view.name || untitledLabel}
            onClick={() => onApply(view)}
          />
          {onRemove ? (
            <button
              type="button"
              className="text-sm leading-none text-slate-400 hover:text-rose-700"
              aria-label={removeLabel}
              onClick={() => onRemove(view.id)}
            >
              ×
            </button>
          ) : null}
        </span>
      ))}
    </div>
  )
}

export type ListWorkspaceProps<T> = {
  definition: ListDefinition<T>
  rows: T[]
  rowKey: (row: T) => string
  loading?: boolean
  error?: ReactNode
  emptyState?: ReactNode
  search?: ListWorkspaceSearch
  searchInputRef?: Ref<HTMLInputElement>
  /** Domain filter controls (chips, pickers). Live in the toolbar next to search. */
  filters?: ReactNode
  toolbarActions?: ReactNode
  viewSwitcher?: ReactNode
  savedViews?: ReactNode
  sort?: ListWorkspaceSort
  pagination?: ListWorkspacePagination
  selection?: ListWorkspaceSelection
  bulkActions?: ReactNode
  bulkSelectedLabel?: (count: number) => string
  bulkClearLabel?: string
  onRowClick?: (row: T, index: number, event: MouseEvent<HTMLTableRowElement>) => void
  isRowActive?: (row: T) => boolean
  header?: ReactNode
  insights?: ReactNode
  onToolbarSubmit?: (event: FormEvent<HTMLFormElement>) => void
  ariaLabel?: string
  className?: string
}

function Zone({ children, className }: { children: ReactNode; className?: string }) {
  if (children == null || children === false) return null
  return <div className={className}>{children}</div>
}

/**
 * Public operational list pattern (ADR-044). Hosts one DataTable.
 * Modules pass ListDefinition + domain cells; they do not fork a table or toolbar.
 */
export function ListWorkspace<T>({
  definition,
  rows,
  rowKey,
  loading = false,
  error,
  emptyState,
  search,
  searchInputRef,
  filters,
  toolbarActions,
  viewSwitcher,
  savedViews,
  sort,
  pagination,
  selection,
  bulkActions,
  bulkSelectedLabel,
  bulkClearLabel,
  onRowClick,
  isRowActive,
  header,
  insights,
  onToolbarSubmit,
  ariaLabel,
  className,
}: ListWorkspaceProps<T>) {
  const compact = definition.density === 'compact'
  const columns: DataTableColumn<T>[] = definition.columns.map((col) => ({
    key: col.id,
    header: col.label,
    sortable: Boolean(col.sortable && sort),
    align: col.align,
    compact: compact || col.compact,
    tabularNums: col.tabularNums,
    cellClassName: col.cellClassName,
    render: (row) => col.cell(row),
  }))

  const tableSelection = selection
    ? {
        isSelected: selection.isSelected,
        onToggle: selection.onToggle,
        onToggleAll: selection.onToggleAll,
        allSelected: selection.allSelected,
        someSelected: selection.someSelected,
      }
    : undefined

  const handleSortChange = (next: DataTableSortState) => {
    if (!sort) return
    if (next.columnKey !== sort.columnKey) {
      const col = definition.columns.find((c) => c.id === next.columnKey)
      sort.onChange({
        columnKey: next.columnKey,
        direction: col?.defaultSortDirection ?? next.direction,
      })
      return
    }
    sort.onChange(next)
  }

  const toolbarInner = (
    <div className="flex flex-wrap items-center gap-2">
      {search ? (
        <SearchField
          ref={searchInputRef}
          name={search.name ?? 'q'}
          defaultValue={search.defaultValue}
          value={search.value}
          onChange={
            search.onChange
              ? (e) => search.onChange?.(e.currentTarget.value)
              : undefined
          }
          placeholder={search.placeholder}
          className="min-h-[40px] min-w-[200px] flex-1"
          aria-label={search.placeholder ?? 'Search'}
        />
      ) : null}
      {filters}
      {viewSwitcher}
      {toolbarActions}
    </div>
  )

  const toolbar = search || filters || toolbarActions || viewSwitcher ? (
    <Toolbar>
      {onToolbarSubmit ? (
        <form onSubmit={onToolbarSubmit} className="flex min-w-0 flex-1 flex-col">
          {toolbarInner}
        </form>
      ) : (
        toolbarInner
      )}
    </Toolbar>
  ) : null

  const showBulk = Boolean(bulkActions) && (selection?.selectedCount ?? 0) > 0

  return (
    <section
      className={clsx('entity-list-shell crm-page-stack min-h-0 flex-1', className)}
      aria-label={ariaLabel ?? definition.resourceId}
      data-list-workspace="v1"
    >
      <Zone className="entity-list-zone entity-list-zone-header">{header}</Zone>
      <Zone className="entity-list-zone entity-list-zone-insights">{insights}</Zone>
      <Zone className="entity-list-zone entity-list-zone-toolbar">{toolbar}</Zone>
      <Zone className="entity-list-zone entity-list-zone-active-filters">{savedViews}</Zone>

      <div className="entity-list-body flex min-h-0 min-w-0 flex-1 flex-col">
        <div className="entity-list-zone entity-list-zone-table entity-list-table-scroll min-h-0 min-w-0 flex-1">
          {error ?? (
            <DataTable
              columns={columns}
              rows={rows}
              rowKey={rowKey}
              loading={loading}
              emptyState={emptyState}
              onRowClick={onRowClick}
              isRowActive={isRowActive}
              selection={tableSelection}
              sort={sort ? { columnKey: sort.columnKey, direction: sort.direction } : null}
              onSortChange={sort ? handleSortChange : undefined}
              ariaLabel={ariaLabel ?? definition.resourceId}
              resourceId={definition.resourceId}
            />
          )}
        </div>
        {showBulk && selection ? (
          <div
            className="entity-list-zone entity-list-zone-bulk shrink-0"
            data-entity-list-bulk
            role="region"
            aria-label="Bulk actions"
          >
            <BulkActionBar
              selectedCount={selection.selectedCount}
              onClearSelection={selection.onClearSelection}
              selectedLabel={bulkSelectedLabel}
              clearLabel={bulkClearLabel}
              actions={bulkActions}
            />
          </div>
        ) : null}
      </div>

      {pagination && definition.pagination !== 'infinite' ? (
        <Zone className="entity-list-zone entity-list-zone-pagination shrink-0">
          <div className="mx-4 flex items-center justify-between gap-3">
            {pagination.summary ? <div className="text-slate-500">{pagination.summary}</div> : <span />}
            <Pagination
              page={pagination.page}
              pageSize={pagination.pageSize}
              total={pagination.total}
              onPageChange={pagination.onPageChange}
              previousLabel={pagination.previousLabel}
              nextLabel={pagination.nextLabel}
              pageLabel={pagination.pageLabel}
            />
          </div>
        </Zone>
      ) : null}
    </section>
  )
}
