import clsx from 'clsx'
import { useEffect, useRef, useState, type MouseEvent, type ReactNode, type Ref } from 'react'

import { Toolbar } from '../../components/layout/Toolbar'
import { BulkActionBar } from '../../components/ui/BulkActionBar'
import { Button } from '../../components/ui/Button'
import { Chip } from '../../components/ui/Chip'
import type { DataTableColumn, DataTableSortState } from '../../components/ui/DataTable'
import { Pagination } from '../../components/ui/Pagination'
import { SearchField } from '../../components/ui/SearchField'
import { ListFilterZone } from './ListFilterZone'
import { renderListRepresentation } from './representations'
import { COLLECTION_ORCHESTRATION_ID } from './types'
import type { ListWorkspaceController } from './useListWorkspace'

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
  controller: ListWorkspaceController<T>
  rows: T[]
  rowKey: (row: T) => string
  total: number
  loading?: boolean
  error?: ReactNode
  emptyState?: ReactNode
  toolbarActions?: ReactNode
  onRowClick?: (row: T, index: number, event: MouseEvent<HTMLTableRowElement>) => void
  isRowActive?: (row: T) => boolean
  header?: ReactNode
  insights?: ReactNode
  ariaLabel?: string
  className?: string
}

function Zone({ children, className }: { children: ReactNode; className?: string }) {
  if (children == null || children === false) return null
  return <div className={className}>{children}</div>
}

function DebouncedSearch({
  value,
  placeholder,
  debounceMs,
  inputRef,
  onCommit,
}: {
  value: string
  placeholder: string
  debounceMs: number
  inputRef?: Ref<HTMLInputElement>
  onCommit: (value: string) => void
}) {
  const [draft, setDraft] = useState(value)
  useEffect(() => {
    setDraft(value)
  }, [value])
  useEffect(() => {
    if (draft === value) return
    const timer = window.setTimeout(() => onCommit(draft), debounceMs)
    return () => window.clearTimeout(timer)
  }, [debounceMs, draft, onCommit, value])

  return (
    <SearchField
      ref={inputRef}
      name="q"
      value={draft}
      onChange={(event) => setDraft(event.currentTarget.value)}
      onKeyDown={(event) => {
        if (event.key === 'Enter') {
          event.preventDefault()
          onCommit(draft)
        }
      }}
      placeholder={placeholder}
      className="min-h-[40px] min-w-[200px] flex-1"
      aria-label={placeholder}
    />
  )
}

/**
 * Collection orchestration shell (ADR-044). Owns query/filter/sort/pagination/
 * selection/saved-view chrome. DataTable is one representation renderer.
 */
export function ListWorkspace<T>({
  controller,
  rows,
  rowKey,
  total,
  loading = false,
  error,
  emptyState,
  toolbarActions,
  onRowClick,
  isRowActive,
  header,
  insights,
  ariaLabel,
  className,
}: ListWorkspaceProps<T>) {
  const { definition, query } = controller
  const compact = definition.density === 'compact'
  const copy = definition.copy ?? {}
  const searchEnabled = definition.search?.enabled !== false
  const searchRef = useRef<HTMLInputElement>(null)
  const [columnsOpen, setColumnsOpen] = useState(false)
  const columnsRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!searchEnabled) return
    const onKey = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault()
        searchRef.current?.focus()
        searchRef.current?.select()
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [searchEnabled])

  useEffect(() => {
    if (!columnsOpen) return
    const handler = (event: Event) => {
      if (columnsRef.current && !columnsRef.current.contains(event.target as Node)) {
        setColumnsOpen(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [columnsOpen])

  const visibleColumns = definition.columns.filter((column) => controller.visibleColumnIds.includes(column.id))
  const columns: DataTableColumn<T>[] = visibleColumns.map((col) => ({
    key: col.id,
    header: col.label,
    sortable: Boolean(col.sortable),
    align: col.align,
    compact: compact || col.compact,
    tabularNums: col.tabularNums,
    cellClassName: col.cellClassName,
    render: (row) => col.cell(row),
  }))

  const selectedCount = controller.selectedIds.length
  const pageIds = rows.map((row) => rowKey(row))
  const allSelected = pageIds.length > 0 && pageIds.every((id) => controller.selectedIds.includes(id))
  const selectionEnabled = definition.selection?.enabled !== false
  const tableSelection = selectionEnabled
    ? {
        isSelected: (id: string) => controller.selectedIds.includes(id),
        onToggle: controller.toggleRow,
        onToggleAll: (checked: boolean) => controller.toggleAll(pageIds, checked),
        allSelected,
        someSelected: selectedCount > 0,
      }
    : undefined

  const handleSortChange = (next: DataTableSortState) => {
    controller.setSort(next.columnKey, next.direction)
  }

  const hasFilters = (definition.filters ?? []).length > 0
  const hasActiveFilters =
    Boolean(query.q) || Object.values(query.filters).some(Boolean)

  const toolbarInner = (
    <div className="flex flex-wrap items-center gap-2">
      {searchEnabled ? (
        <DebouncedSearch
          value={query.q}
          placeholder={copy.searchPlaceholder ?? 'Search'}
          debounceMs={definition.search?.debounceMs ?? 300}
          inputRef={searchRef}
          onCommit={controller.setSearch}
        />
      ) : null}
      <ListFilterZone definition={definition} query={query} onFilter={controller.setFilter} />
      {hasFilters || searchEnabled ? (
        <Button
          type="button"
          variant="secondary"
          size="sm"
          onClick={controller.resetQueryFilters}
          disabled={!hasActiveFilters}
        >
          {copy.resetLabel ?? 'Reset'}
        </Button>
      ) : null}
      {toolbarActions}
      <div className="relative" ref={columnsRef}>
        <Button
          type="button"
          variant="secondary"
          size="sm"
          onClick={() => setColumnsOpen((open) => !open)}
          title={copy.columnsLabel ?? 'Columns'}
        >
          ⋯
        </Button>
        {columnsOpen ? (
          <div className="absolute right-0 z-20 mt-2 w-56 rounded-lg border border-slate-200 bg-white p-3 shadow-md">
            <div className="text-xs font-semibold uppercase tracking-wide text-slate-400">
              {copy.columnsLabel ?? 'Columns'}
            </div>
            <div className="mt-2 space-y-1">
              {definition.columns.map((column) => (
                <label key={column.id} className="flex items-center gap-2 py-1 text-sm">
                  <input
                    type="checkbox"
                    checked={controller.visibleColumnIds.includes(column.id)}
                    onChange={(event) => controller.setColumnVisible(column.id, event.currentTarget.checked)}
                  />
                  {column.label}
                </label>
              ))}
            </div>
            {definition.savedViews?.enabled !== false && definition.savedViews?.onSave ? (
              <Button
                type="button"
                variant="primary"
                className="mt-3 w-full"
                onClick={() => {
                  const name = window.prompt(copy.saveViewPrompt ?? 'View name')?.trim()
                  if (!name) return
                  setColumnsOpen(false)
                  controller.saveCurrentView(name)
                }}
              >
                {copy.saveViewLabel ?? 'Save view'}
              </Button>
            ) : null}
          </div>
        ) : null}
      </div>
    </div>
  )

  const toolbar =
    searchEnabled || hasFilters || toolbarActions ? (
      <Toolbar>{toolbarInner}</Toolbar>
    ) : null

  const bulkActions = definition.bulkActions ?? []
  const showBulk = selectionEnabled && bulkActions.length > 0 && selectedCount > 0
  const bulkGroups = new Map<string, { label: string; actions: typeof bulkActions }>()
  const ungrouped: typeof bulkActions = []
  for (const action of bulkActions) {
    if (action.groupId) {
      const current = bulkGroups.get(action.groupId) ?? { label: action.groupLabel ?? action.groupId, actions: [] }
      current.actions.push(action)
      bulkGroups.set(action.groupId, current)
    } else {
      ungrouped.push(action)
    }
  }

  const savedViews = definition.savedViews?.views ?? []

  return (
    <section
      className={clsx('entity-list-shell crm-page-stack min-h-0 flex-1', className)}
      aria-label={ariaLabel ?? definition.resourceId}
      data-list-workspace="v1"
      data-collection-orchestration={COLLECTION_ORCHESTRATION_ID}
    >
      <Zone className="entity-list-zone entity-list-zone-header">{header}</Zone>
      <Zone className="entity-list-zone entity-list-zone-insights">{insights}</Zone>
      <Zone className="entity-list-zone entity-list-zone-toolbar">{toolbar}</Zone>
      <Zone className="entity-list-zone entity-list-zone-active-filters">
        <SavedViewChips
          views={savedViews.map((view) => ({ id: view.id, name: view.name }))}
          onApply={(view) => {
            const match = savedViews.find((item) => item.id === view.id)
            if (match) controller.applySavedView(match)
          }}
          onRemove={definition.savedViews?.onRemove ? controller.removeSavedView : undefined}
          untitledLabel={copy.untitledViewLabel}
          removeLabel={copy.removeViewLabel}
        />
      </Zone>

      <div className="entity-list-body flex min-h-0 min-w-0 flex-1 flex-col">
        <div className="entity-list-zone entity-list-zone-table entity-list-table-scroll min-h-0 min-w-0 flex-1">
          {error ??
            renderListRepresentation({
              representation: query.representation,
              columns,
              rows,
              rowKey,
              loading,
              emptyState,
              onRowClick,
              isRowActive,
              selection: tableSelection,
              sort: query.sortColumnId
                ? { columnKey: query.sortColumnId, direction: query.sortDirection }
                : null,
              onSortChange: handleSortChange,
              ariaLabel: ariaLabel ?? definition.resourceId,
              resourceId: definition.resourceId,
            })}
        </div>
        {showBulk ? (
          <div
            className="entity-list-zone entity-list-zone-bulk shrink-0"
            data-entity-list-bulk
            role="region"
            aria-label="Bulk actions"
          >
            <BulkActionBar
              selectedCount={selectedCount}
              onClearSelection={controller.clearSelection}
              selectedLabel={copy.bulkSelectedLabel}
              clearLabel={copy.bulkClearLabel}
              actions={
                <>
                  {[...bulkGroups.entries()].map(([groupId, group]) => (
                    <div key={groupId} className="flex items-center gap-1">
                      <span className="text-slate-500">{group.label}</span>
                      {group.actions.map((action) => (
                        <Button
                          key={action.id}
                          type="button"
                          variant="secondary"
                          size="xs"
                          onClick={() => void action.onAction(controller.selectedIds)}
                        >
                          {action.label}
                        </Button>
                      ))}
                    </div>
                  ))}
                  {ungrouped.map((action) => (
                    <Button
                      key={action.id}
                      type="button"
                      variant="secondary"
                      size="xs"
                      onClick={() => void action.onAction(controller.selectedIds)}
                    >
                      {action.label}
                    </Button>
                  ))}
                </>
              }
            />
          </div>
        ) : null}
      </div>

      {definition.pagination?.mode !== 'infinite' ? (
        <Zone className="entity-list-zone entity-list-zone-pagination shrink-0">
          <div className="mx-4 flex items-center justify-between gap-3">
            {copy.paginationSummary ? (
              <div className="text-slate-500">{copy.paginationSummary(total)}</div>
            ) : (
              <span />
            )}
            <Pagination
              page={query.page}
              pageSize={query.pageSize}
              total={total}
              onPageChange={controller.setPage}
              previousLabel={copy.previousPageLabel}
              nextLabel={copy.nextPageLabel}
              pageLabel={copy.pageLabel}
            />
          </div>
        </Zone>
      ) : null}
    </section>
  )
}
