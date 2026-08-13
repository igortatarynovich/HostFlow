import { type ReactElement, useState } from 'react'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'

import { I18nProvider } from '../../../i18n'
import { DataTable } from '../DataTable'

type Row = { id: string; name: string; stage: string }

const ROWS: Row[] = [
  { id: '1', name: 'Ada', stage: 'new' },
  { id: '2', name: 'Ben', stage: 'offer' },
]

function wrap(ui: ReactElement) {
  return render(
    <MemoryRouter>
      <I18nProvider initialLocale="en">{ui}</I18nProvider>
    </MemoryRouter>,
  )
}

describe('kit DataTable', () => {
  it('renders column headers and domain cells', () => {
    wrap(
      <DataTable
        ariaLabel="People"
        columns={[
          { key: 'name', header: 'Name', render: (row) => row.name },
          { key: 'stage', header: 'Stage', render: (row) => row.stage },
        ]}
        rows={ROWS}
        rowKey={(row) => row.id}
      />,
    )
    const table = screen.getByRole('table', { name: 'People' })
    expect(table.closest('[data-datatable="v1"]')).not.toBeNull()
    expect(screen.getByRole('columnheader', { name: 'Name' })).toBeInTheDocument()
    expect(screen.getByText('Ada')).toBeInTheDocument()
    expect(screen.getByText('offer')).toBeInTheDocument()
  })

  it('keeps selection clicks off row navigation', async () => {
    const user = userEvent.setup()
    const onRowClick = vi.fn()
    const onToggle = vi.fn()
    wrap(
      <DataTable
        columns={[{ key: 'name', header: 'Name', render: (row) => row.name }]}
        rows={ROWS}
        rowKey={(row) => row.id}
        onRowClick={onRowClick}
        selection={{
          isSelected: () => false,
          onToggle,
          onToggleAll: vi.fn(),
          allSelected: false,
        }}
      />,
    )
    await user.click(screen.getAllByRole('checkbox', { name: 'Select row' })[0])
    expect(onToggle).toHaveBeenCalledWith('1', true)
    expect(onRowClick).not.toHaveBeenCalled()
  })

  it('sorts from the header without a custom header tree', async () => {
    const user = userEvent.setup()
    function Harness() {
      const [sort, setSort] = useState<{ columnKey: string; direction: 'asc' | 'desc' } | null>(null)
      return (
        <DataTable
          columns={[{ key: 'name', header: 'Name', sortable: true, render: (row) => row.name }]}
          rows={ROWS}
          rowKey={(row) => row.id}
          sort={sort}
          onSortChange={setSort}
        />
      )
    }
    wrap(<Harness />)
    expect(screen.getByRole('columnheader', { name: 'Name' })).toHaveAttribute('aria-sort', 'none')
    await user.click(screen.getByRole('button', { name: 'Name' }))
    expect(screen.getByRole('columnheader', { name: 'Name' })).toHaveAttribute('aria-sort', 'ascending')
    await user.click(screen.getByRole('button', { name: 'Name' }))
    expect(screen.getByRole('columnheader', { name: 'Name' })).toHaveAttribute('aria-sort', 'descending')
  })

  it('shows empty chrome when there are no rows', () => {
    wrap(
      <DataTable
        columns={[{ key: 'name', header: 'Name', render: (row: Row) => row.name }]}
        rows={[]}
        rowKey={(row) => row.id}
        emptyState="No people"
      />,
    )
    expect(screen.getByText('No people')).toBeInTheDocument()
  })
})
