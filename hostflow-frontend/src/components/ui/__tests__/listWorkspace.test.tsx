import { type ReactElement } from 'react'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'

import { I18nProvider } from '../../../i18n'
import { ListWorkspace, type ListDefinition } from '../ListWorkspace'

type Row = { id: string; title: string; status: string }

const ROWS: Row[] = [
  { id: '1', title: 'Warehouse', status: 'open' },
  { id: '2', title: 'Driver', status: 'closed' },
]

const definition: ListDefinition<Row> = {
  resourceId: 'vacancies',
  pagination: 'paged',
  columns: [
    { id: 'title', fieldId: 'title', kind: 'text', label: 'Title', sortable: true, cell: (row) => row.title },
    { id: 'status', fieldId: 'status', kind: 'enum', label: 'Status', cell: (row) => row.status },
  ],
}

function wrap(ui: ReactElement) {
  return render(
    <MemoryRouter>
      <I18nProvider initialLocale="en">{ui}</I18nProvider>
    </MemoryRouter>,
  )
}

describe('kit ListWorkspace', () => {
  it('renders search, DataTable cells, and pagination from definition', () => {
    wrap(
      <ListWorkspace
        definition={definition}
        rows={ROWS}
        rowKey={(row) => row.id}
        search={{ placeholder: 'Search vacancies', defaultValue: '' }}
        pagination={{ page: 1, pageSize: 20, total: 2, onPageChange: vi.fn(), summary: '2 total' }}
      />,
    )
    expect(document.querySelector('[data-list-workspace="v1"]')).not.toBeNull()
    expect(screen.getByRole('searchbox', { name: 'Search vacancies' })).toBeInTheDocument()
    expect(screen.getByRole('table', { name: 'vacancies' })).toBeInTheDocument()
    expect(screen.getByText('Warehouse')).toBeInTheDocument()
    expect(screen.getByText('2 total')).toBeInTheDocument()
  })

  it('hides bulk until selection is non-empty', () => {
    const { rerender } = wrap(
      <ListWorkspace
        definition={definition}
        rows={ROWS}
        rowKey={(row) => row.id}
        selection={{
          isSelected: () => false,
          onToggle: vi.fn(),
          onToggleAll: vi.fn(),
          allSelected: false,
          selectedCount: 0,
          onClearSelection: vi.fn(),
        }}
        bulkActions={<button type="button">Archive</button>}
      />,
    )
    expect(document.querySelector('[data-entity-list-bulk]')).toBeNull()
    rerender(
      <MemoryRouter>
        <I18nProvider initialLocale="en">
          <ListWorkspace
            definition={definition}
            rows={ROWS}
            rowKey={(row) => row.id}
            selection={{
              isSelected: () => true,
              onToggle: vi.fn(),
              onToggleAll: vi.fn(),
              allSelected: true,
              selectedCount: 2,
              onClearSelection: vi.fn(),
            }}
            bulkActions={<button type="button">Archive</button>}
          />
        </I18nProvider>
      </MemoryRouter>,
    )
    expect(document.querySelector('[data-entity-list-bulk]')).not.toBeNull()
    expect(screen.getByText('Archive')).toBeInTheDocument()
  })

  it('sorts from definition columns', async () => {
    const user = userEvent.setup()
    const onChange = vi.fn()
    wrap(
      <ListWorkspace
        definition={definition}
        rows={ROWS}
        rowKey={(row) => row.id}
        sort={{ columnKey: 'title', direction: 'asc', onChange }}
      />,
    )
    await user.click(screen.getByRole('button', { name: 'Title' }))
    expect(onChange).toHaveBeenCalledWith({ columnKey: 'title', direction: 'desc' })
  })
})
