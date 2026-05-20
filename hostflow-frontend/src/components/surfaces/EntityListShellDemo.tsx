import { useMemo, useState } from 'react'
import EntityListActiveFilters from './EntityListActiveFilters'
import EntityListBulkBar from './EntityListBulkBar'
import EntityListPagination from './EntityListPagination'
import EntityListSelectionCheckbox from './EntityListSelectionCheckbox'
import EntityListShell from './EntityListShell'
import EntityListTableFrame from './EntityListTableFrame'
import {
  ENTITY_LIST_DEMO_DEFINITION,
  ENTITY_LIST_DEMO_ROWS,
  type EntityListDemoRow,
} from './entityListShell.fixture'
import type { EntityListTableFrameStatus } from './entityListTypes'
import { useEntityListSelection } from './useEntityListSelection'

const PAGE_SIZE = 4

function statusChipClass(status: string): string {
  if (status === 'open') return 'border-emerald-200 bg-emerald-50 text-emerald-800'
  if (status === 'paused') return 'border-amber-200 bg-amber-50 text-amber-900'
  if (status === 'closed') return 'border-slate-200 bg-slate-100 text-slate-600'
  return 'border-slate-200 bg-white text-slate-600'
}

/** Domain cell — stays outside EntityListShell (2A acceptance). */
function DemoStatusCell({ status }: { status: string }) {
  return (
    <span className={`inline-flex border px-2 py-0.5 text-xs font-medium ${statusChipClass(status)}`}>
      {status}
    </span>
  )
}

function DemoVacancyTable({
  rows,
  selection,
}: {
  rows: EntityListDemoRow[]
  selection: ReturnType<typeof useEntityListSelection>
}) {
  return (
    <table className="w-full text-sm">
      <thead>
        <tr>
          <th className="w-10 border-b border-slate-200 px-3 py-3">
            <EntityListSelectionCheckbox
              checked={selection.pageAllSelected}
              indeterminate={selection.pageSomeSelected}
              ariaLabel="Select all on page"
              onChange={selection.togglePage}
            />
          </th>
          {ENTITY_LIST_DEMO_DEFINITION.columns.map((col) => (
            <th key={col.id} className="border-b border-slate-200 px-4 py-3 text-xs font-semibold text-slate-600">
              {col.label}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.map((row) => (
          <tr key={row.id} className="hover:bg-slate-50" data-row-id={row.id}>
            <td className="border-b border-slate-100 px-3 py-2">
              <EntityListSelectionCheckbox
                checked={selection.isRowSelected(row.id)}
                ariaLabel={`Select ${row.title}`}
                onChange={(checked) => selection.toggleRow(row.id, checked)}
              />
            </td>
            <td className="border-b border-slate-100 px-4 py-2 font-medium text-slate-900">{row.title}</td>
            <td className="border-b border-slate-100 px-4 py-2 text-slate-700">{row.companyName}</td>
            <td className="border-b border-slate-100 px-4 py-2">
              <DemoStatusCell status={row.status} />
            </td>
            <td className="border-b border-slate-100 px-4 py-2 text-slate-700">{row.candidateCount}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

/**
 * Phase 2A fixture: all ADR-010 zones + controlled selection + bulk bar.
 * Not mounted on Vacancies/Companies — use dev route `/app/dev/entity-list-shell`.
 */
export default function EntityListShellDemo() {
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState<string | null>(null)
  const [frameStatus, setFrameStatus] = useState<EntityListTableFrameStatus>('ready')

  const filtered = useMemo(() => {
    let rows = ENTITY_LIST_DEMO_ROWS
    if (statusFilter) rows = rows.filter((r) => r.status === statusFilter)
    const q = search.trim().toLowerCase()
    if (q) rows = rows.filter((r) => r.title.toLowerCase().includes(q) || r.companyName.toLowerCase().includes(q))
    return rows
  }, [search, statusFilter])

  const total = filtered.length
  const pageRows = useMemo(() => {
    const start = (page - 1) * PAGE_SIZE
    return filtered.slice(start, start + PAGE_SIZE)
  }, [filtered, page])

  const pageRowIds = useMemo(() => pageRows.map((r) => r.id), [pageRows])
  const selection = useEntityListSelection({ pageRowIds })

  const activeFilterChips =
    statusFilter || search.trim() ? (
      <>
        {statusFilter ? (
          <span className="entity-list-filter-chip border border-slate-200 bg-slate-50 px-2 py-1 text-xs text-slate-700">
            Status: {statusFilter}
            <button
              type="button"
              className="ml-2 text-slate-500 hover:text-slate-800"
              aria-label="Remove status filter"
              onClick={() => setStatusFilter(null)}
            >
              ×
            </button>
          </span>
        ) : null}
        {search.trim() ? (
          <span className="entity-list-filter-chip border border-slate-200 bg-slate-50 px-2 py-1 text-xs text-slate-700">
            Search: {search.trim()}
            <button
              type="button"
              className="ml-2 text-slate-500 hover:text-slate-800"
              aria-label="Clear search"
              onClick={() => setSearch('')}
            >
              ×
            </button>
          </span>
        ) : null}
      </>
    ) : null

  const tableStatus: EntityListTableFrameStatus =
    frameStatus !== 'ready'
      ? frameStatus
      : total === 0
        ? 'empty'
        : 'ready'

  return (
    <div className="crm-page-inset crm-page-stack flex min-h-0 flex-1 flex-col">
      <div className="flex flex-wrap items-center gap-2 border border-dashed border-slate-300 bg-slate-50 px-3 py-2 text-xs text-slate-600">
        <span className="font-medium text-slate-800">Phase 2A fixture</span>
        <span>Resource: {ENTITY_LIST_DEMO_DEFINITION.resourceId}</span>
        <span className="ml-auto flex flex-wrap gap-2">
          <label className="flex items-center gap-1">
            Frame:
            <select
              id="entity-list-demo-frame-status"
              aria-label="Frame"
              className="border border-slate-300 bg-white px-1 py-0.5 text-xs"
              value={frameStatus}
              onChange={(e) => setFrameStatus(e.target.value as EntityListTableFrameStatus)}
            >
              <option value="ready">ready</option>
              <option value="loading">loading</option>
              <option value="empty">empty</option>
              <option value="error">error</option>
            </select>
          </label>
        </span>
      </div>

      <EntityListShell
        resourceLabel="Vacancies list shell demo"
        selection={{
          selectedCount: selection.selectedCount,
          onClearSelection: selection.clearSelection,
        }}
        zones={{
          header: (
            <div className="flex flex-wrap items-center justify-between gap-3">
              <h1 className="text-2xl font-semibold text-slate-900">Vacancies (shell demo)</h1>
              <button type="button" className="btn-primary btn-sm">
                New vacancy
              </button>
            </div>
          ),
          insights: (
            <div className="flex flex-wrap gap-2 text-xs">
              <span className="border border-slate-200 bg-white px-2 py-1 text-slate-700">
                Open: {ENTITY_LIST_DEMO_ROWS.filter((r) => r.status === 'open').length}
              </span>
              <span className="border border-slate-200 bg-white px-2 py-1 text-slate-700">
                Filtered: {total}
              </span>
            </div>
          ),
          toolbar: (
            <div className="entity-list-toolbar flex flex-wrap items-center gap-2">
              <input
                type="search"
                className="h-9 min-w-[12rem] flex-1 border border-slate-300 px-3 text-sm"
                placeholder="Search title or company…"
                value={search}
                onChange={(e) => {
                  setSearch(e.target.value)
                  setPage(1)
                }}
              />
              <select
                className="h-9 border border-slate-300 bg-white px-2 text-sm"
                value={statusFilter ?? ''}
                onChange={(e) => {
                  setStatusFilter(e.target.value || null)
                  setPage(1)
                }}
              >
                <option value="">All statuses</option>
                <option value="open">open</option>
                <option value="paused">paused</option>
                <option value="closed">closed</option>
                <option value="draft">draft</option>
              </select>
            </div>
          ),
          activeFilters: activeFilterChips ? (
            <EntityListActiveFilters
              onResetAll={() => {
                setSearch('')
                setStatusFilter(null)
                setPage(1)
              }}
            >
              {activeFilterChips}
            </EntityListActiveFilters>
          ) : undefined,
          table: (
            <EntityListTableFrame
              status={tableStatus}
              table={<DemoVacancyTable rows={pageRows} selection={selection} />}
            />
          ),
          bulkBar: (
            <EntityListBulkBar
              selectedCount={selection.selectedCount}
              onClearSelection={selection.clearSelection}
              actions={
                <>
                  <button type="button" className="btn-secondary btn-xs">
                    Assign owner (demo)
                  </button>
                  <button type="button" className="btn-secondary btn-xs">
                    Export (demo)
                  </button>
                </>
              }
            />
          ),
          pagination: (
            <EntityListPagination
              page={page}
              pageSize={PAGE_SIZE}
              total={total}
              onPageChange={setPage}
            />
          ),
        }}
      />
    </div>
  )
}
