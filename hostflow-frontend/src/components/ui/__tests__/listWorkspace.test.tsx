import { type ReactElement } from 'react'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'

import { I18nProvider } from '../../../i18n'
import { ListWorkspace, useListWorkspace, type ListDefinition } from '../ListWorkspace'

type Row = { id: string; title: string; status: string }

const ROWS: Row[] = [
  { id: '1', title: 'Warehouse', status: 'open' },
  { id: '2', title: 'Driver', status: 'closed' },
]

const definition: ListDefinition<Row> = {
  resourceId: 'vacancies',
  pagination: { mode: 'paged', pageSize: 20 },
  search: { enabled: true },
  filters: [{ fieldId: 'status', kind: 'enum', label: 'Status', widget: 'chips', options: [
    { value: '', label: 'All' },
    { value: 'open', label: 'Open' },
  ] }],
  sort: { defaultColumnId: 'title', defaultDirection: 'asc' },
  selection: { enabled: true },
  bulkActions: [{ id: 'archive', label: 'Archive', onAction: vi.fn() }],
  columns: [
    { id: 'title', fieldId: 'title', kind: 'text', label: 'Title', sortable: true, cell: (row) => row.title },
    { id: 'status', fieldId: 'status', kind: 'enum', label: 'Status', cell: (row) => row.status },
  ],
  copy: { searchPlaceholder: 'Search vacancies', paginationSummary: (total) => `${total} total` },
}

function Harness() {
  const controller = useListWorkspace(definition)
  return (
    <ListWorkspace
      controller={controller}
      rows={ROWS}
      rowKey={(row) => row.id}
      total={2}
    />
  )
}

function wrap(ui: ReactElement) {
  return render(
    <MemoryRouter>
      <I18nProvider initialLocale="en">{ui}</I18nProvider>
    </MemoryRouter>,
  )
}

describe('kit ListWorkspace orchestration', () => {
  it('owns search, table representation, and pagination without page-supplied wiring', () => {
    wrap(<Harness />)
    expect(document.querySelector('[data-collection-orchestration="collection_orchestration"]')).not.toBeNull()
    expect(document.querySelector('[data-list-workspace="v1"]')).not.toBeNull()
    expect(screen.getByRole('searchbox', { name: 'Search vacancies' })).toBeInTheDocument()
    expect(screen.getByRole('table', { name: 'vacancies' })).toBeInTheDocument()
    expect(screen.getByText('Warehouse')).toBeInTheDocument()
    expect(screen.getByText('2 total')).toBeInTheDocument()
  })

  it('hides bulk until selection is non-empty', async () => {
    const user = userEvent.setup()
    wrap(<Harness />)
    expect(document.querySelector('[data-entity-list-bulk]')).toBeNull()
    const checkboxes = screen.getAllByRole('checkbox')
    await user.click(checkboxes[0])
    expect(document.querySelector('[data-entity-list-bulk]')).not.toBeNull()
    expect(screen.getByText('Archive')).toBeInTheDocument()
  })

  it('owns sort state from definition columns', async () => {
    const user = userEvent.setup()
    wrap(<Harness />)
    await user.click(screen.getByRole('button', { name: 'Title' }))
    expect(screen.getByRole('table')).toBeInTheDocument()
  })
})
