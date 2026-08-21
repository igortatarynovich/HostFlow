import type { ListDefinition, ListQueryState, ListRepresentationId } from './types'
import { LIST_REPRESENTATION_TABLE } from './types'

export function filterUrlKey(filter: { fieldId: string; urlKey?: string }): string {
  return filter.urlKey ?? filter.fieldId
}

export function defaultPageSize<T>(definition: ListDefinition<T>): number {
  return definition.pagination?.pageSize ?? 20
}

export function defaultSortColumnId<T>(definition: ListDefinition<T>): string {
  if (definition.sort?.defaultColumnId) return definition.sort.defaultColumnId
  const sortable = definition.columns.find((column) => column.sortable)
  return sortable?.id ?? definition.columns[0]?.id ?? ''
}

export function defaultSortDirection<T>(definition: ListDefinition<T>): 'asc' | 'desc' {
  if (definition.sort?.defaultDirection) return definition.sort.defaultDirection
  const column = definition.columns.find((item) => item.id === defaultSortColumnId(definition))
  return column?.defaultSortDirection ?? 'desc'
}

export function defaultRepresentation<T>(definition: ListDefinition<T>): ListRepresentationId {
  return definition.defaultRepresentation ?? LIST_REPRESENTATION_TABLE
}

export function emptyListQuery<T>(definition: ListDefinition<T>): ListQueryState {
  return {
    q: '',
    filters: {},
    sortColumnId: defaultSortColumnId(definition),
    sortDirection: defaultSortDirection(definition),
    page: 1,
    pageSize: defaultPageSize(definition),
    representation: defaultRepresentation(definition),
  }
}

export function resolveSortColumnId<T>(definition: ListDefinition<T>, raw: string | null | undefined): string {
  const fallback = defaultSortColumnId(definition)
  if (!raw) return fallback
  const match = definition.columns.find(
    (column) => column.id === raw || column.fieldId === raw || column.sortField === raw,
  )
  return match?.id ?? fallback
}

export function sortApiField<T>(definition: ListDefinition<T>, columnId: string): string {
  const column = definition.columns.find((item) => item.id === columnId)
  return column?.sortField ?? column?.fieldId ?? columnId
}

export function querySnapshot(query: ListQueryState, definition: ListDefinition<unknown>): Record<string, string> {
  const out: Record<string, string> = {}
  if (query.q) out.q = query.q
  if (query.sortColumnId && query.sortColumnId !== defaultSortColumnId(definition)) {
    out.sort = query.sortColumnId
  }
  if (query.sortDirection && query.sortDirection !== defaultSortDirection(definition)) {
    out.dir = query.sortDirection
  }
  if (query.representation && query.representation !== defaultRepresentation(definition)) {
    out.view = query.representation
  }
  for (const filter of definition.filters ?? []) {
    const key = filterUrlKey(filter)
    const value = query.filters[key]
    if (value) out[key] = value
  }
  return out
}

export function parseListQuery(
  params: URLSearchParams | Record<string, string>,
  definition: ListDefinition<unknown>,
): ListQueryState {
  const get = (key: string) => {
    if (params instanceof URLSearchParams) return params.get(key) ?? ''
    return params[key] ?? ''
  }
  const filters: Record<string, string> = {}
  for (const filter of definition.filters ?? []) {
    const key = filterUrlKey(filter)
    const value = get(key).trim()
    if (value) filters[key] = value
  }
  const pageRaw = parseInt(get('page') || '1', 10)
  const page = Number.isFinite(pageRaw) && pageRaw > 0 ? pageRaw : 1
  const dirRaw = get('dir')
  const sortDirection: 'asc' | 'desc' = dirRaw === 'asc' || dirRaw === 'desc' ? dirRaw : defaultSortDirection(definition)
  const viewRaw = get('view')
  const representation =
    viewRaw === LIST_REPRESENTATION_TABLE || !viewRaw
      ? defaultRepresentation(definition)
      : defaultRepresentation(definition)

  return {
    q: get(definition.search?.urlKey ?? 'q').trim(),
    filters,
    sortColumnId: resolveSortColumnId(definition, get('sort') || null),
    sortDirection,
    page,
    pageSize: defaultPageSize(definition),
    representation,
  }
}

export function serializeListQuery(query: ListQueryState, definition: ListDefinition<unknown>): URLSearchParams {
  const next = new URLSearchParams()
  const qKey = definition.search?.urlKey ?? 'q'
  if (query.q) next.set(qKey, query.q)
  if (query.page > 1) next.set('page', String(query.page))
  if (query.sortColumnId && query.sortColumnId !== defaultSortColumnId(definition)) {
    next.set('sort', query.sortColumnId)
  }
  if (query.sortDirection !== defaultSortDirection(definition)) {
    next.set('dir', query.sortDirection)
  }
  if (query.representation !== defaultRepresentation(definition)) {
    next.set('view', query.representation)
  }
  for (const filter of definition.filters ?? []) {
    const key = filterUrlKey(filter)
    const value = query.filters[key]
    if (value) next.set(key, value)
  }
  return next
}

export function listQueryIsEmpty(query: ListQueryState, definition: ListDefinition<unknown>): boolean {
  const defaults = emptyListQuery(definition)
  const noFilters = Object.values(query.filters).every((value) => !value)
  return (
    !query.q &&
    noFilters &&
    query.page === 1 &&
    query.sortColumnId === defaults.sortColumnId &&
    query.sortDirection === defaults.sortDirection
  )
}

export function applySearch(query: ListQueryState, q: string): ListQueryState {
  return { ...query, q: q.trim(), page: 1 }
}

export function applyFilter(query: ListQueryState, urlKey: string, value: string): ListQueryState {
  const filters = { ...query.filters }
  if (!value) delete filters[urlKey]
  else filters[urlKey] = value
  return { ...query, filters, page: 1 }
}

export function resetFilters(query: ListQueryState): ListQueryState {
  return { ...query, q: '', filters: {}, page: 1 }
}

export function applySort(
  query: ListQueryState,
  columnId: string,
  direction: 'asc' | 'desc',
  defaultDirection?: 'asc' | 'desc',
): ListQueryState {
  if (query.sortColumnId !== columnId) {
    return { ...query, sortColumnId: columnId, sortDirection: defaultDirection ?? direction, page: 1 }
  }
  return { ...query, sortColumnId: columnId, sortDirection: direction, page: 1 }
}

export function applyPage(query: ListQueryState, page: number): ListQueryState {
  return { ...query, page: Math.max(1, page) }
}

export function listQuerySignature(query: ListQueryState): string {
  const filterPart = Object.keys(query.filters)
    .sort()
    .map((key) => `${key}=${query.filters[key]}`)
    .join('&')
  return [
    `q=${query.q}`,
    `sort=${query.sortColumnId}:${query.sortDirection}`,
    `page=${query.page}`,
    `size=${query.pageSize}`,
    `view=${query.representation}`,
    filterPart,
  ].join('|')
}
