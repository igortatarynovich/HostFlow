// @vitest-environment node
import { describe, expect, it } from 'vitest'
import { renderToStaticMarkup } from 'react-dom/server'
import EntityListShell from '../EntityListShell'
import EntityListBulkBar from '../EntityListBulkBar'

describe('EntityListShell', () => {
  it('renders zones in ADR-010 order', () => {
    const html = renderToStaticMarkup(
      <EntityListShell
        resourceLabel="test"
        zones={{
          header: <div data-zone="header">H</div>,
          insights: <div data-zone="insights">I</div>,
          toolbar: <div data-zone="toolbar">T</div>,
          activeFilters: <div data-zone="filters">F</div>,
          table: <div data-zone="table">Table</div>,
          pagination: <div data-zone="pagination">P</div>,
          bulkBar: <div data-zone="bulk">B</div>,
        }}
        selection={{ selectedCount: 2, onClearSelection: () => {} }}
      />,
    )
    const headerIdx = html.indexOf('data-zone="header"')
    const insightsIdx = html.indexOf('data-zone="insights"')
    const toolbarIdx = html.indexOf('data-zone="toolbar"')
    const filtersIdx = html.indexOf('data-zone="filters"')
    const tableIdx = html.indexOf('data-zone="table"')
    const bulkIdx = html.indexOf('data-entity-list-bulk')
    const paginationIdx = html.indexOf('data-zone="pagination"')
    expect(headerIdx).toBeLessThan(insightsIdx)
    expect(insightsIdx).toBeLessThan(toolbarIdx)
    expect(toolbarIdx).toBeLessThan(filtersIdx)
    expect(filtersIdx).toBeLessThan(tableIdx)
    expect(tableIdx).toBeLessThan(bulkIdx)
    expect(bulkIdx).toBeLessThan(paginationIdx)
  })

  it('hides bulk zone when selection is empty', () => {
    const html = renderToStaticMarkup(
      <EntityListShell
        zones={{
          table: <table><tbody><tr><td>x</td></tr></tbody></table>,
          bulkBar: <EntityListBulkBar selectedCount={0} onClearSelection={() => {}} />,
        }}
        selection={{ selectedCount: 0, onClearSelection: () => {} }}
      />,
    )
    expect(html).not.toContain('data-entity-list-bulk')
  })

  it('shows bulk zone when selection is non-empty', () => {
    const html = renderToStaticMarkup(
      <EntityListShell
        zones={{
          table: <table><tbody><tr><td>x</td></tr></tbody></table>,
          bulkBar: <EntityListBulkBar selectedCount={3} onClearSelection={() => {}} />,
        }}
        selection={{ selectedCount: 3, onClearSelection: () => {} }}
      />,
    )
    expect(html).toContain('data-entity-list-bulk')
    expect(html).toContain('Selected: 3')
  })
})
