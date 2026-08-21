import { describe, expect, it } from 'vitest'

import {
  applyFilter,
  applySearch,
  applySort,
  emptyListQuery,
  parseListQuery,
  serializeListQuery,
  sortApiField,
} from '../queryState'
import type { ListDefinition } from '../types'

type Row = { id: string; title: string }

const definition: ListDefinition<Row> = {
  resourceId: 'vacancies',
  pagination: { mode: 'paged', pageSize: 20 },
  filters: [
    { fieldId: 'status', kind: 'enum', label: 'Status', widget: 'chips' },
    { fieldId: 'company', kind: 'ref', label: 'Company', urlKey: 'company', widget: 'text' },
  ],
  sort: { defaultColumnId: 'title', defaultDirection: 'desc' },
  columns: [
    { id: 'title', fieldId: 'title', kind: 'text', label: 'Title', sortable: true, cell: (row) => row.title },
    { id: 'company', fieldId: 'company_id', sortField: 'company_name', kind: 'ref', label: 'Company', sortable: true, cell: () => null },
  ],
}

describe('collection orchestration query state', () => {
  it('round-trips search, filters, sort, and page through the URL', () => {
    const query = applySort(
      applyFilter(applySearch(emptyListQuery(definition), 'cook'), 'status', 'open'),
      'company',
      'asc',
    )
    const params = serializeListQuery(query, definition)
    expect(params.get('q')).toBe('cook')
    expect(params.get('status')).toBe('open')
    expect(params.get('sort')).toBe('company')
    expect(params.get('dir')).toBe('asc')
    expect(params.get('page')).toBeNull()

    const parsed = parseListQuery(params, definition)
    expect(parsed.q).toBe('cook')
    expect(parsed.filters.status).toBe('open')
    expect(parsed.sortColumnId).toBe('company')
    expect(parsed.sortDirection).toBe('asc')
    expect(sortApiField(definition, parsed.sortColumnId)).toBe('company_name')
  })

  it('accepts legacy saved-view sort fields as column ids', () => {
    const parsed = parseListQuery({ sort: 'company_name', dir: 'asc' }, definition)
    expect(parsed.sortColumnId).toBe('company')
  })

  it('omits default sort and page from the URL', () => {
    const params = serializeListQuery(emptyListQuery(definition), definition)
    expect(params.toString()).toBe('')
  })
})
