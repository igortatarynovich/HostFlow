import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'

import {
  applyFilter,
  applyPage,
  applySearch,
  applySort,
  listQueryIsEmpty,
  parseListQuery,
  resetFilters,
  serializeListQuery,
} from './queryState'
import type { ListDefinition, ListQueryState, ListSavedViewRecord } from './types'

export type ListWorkspaceController<T> = {
  definition: ListDefinition<T>
  query: ListQueryState
  selectedIds: string[]
  visibleColumnIds: string[]
  setSearch: (value: string) => void
  setFilter: (urlKey: string, value: string) => void
  resetQueryFilters: () => void
  setSort: (columnId: string, direction: 'asc' | 'desc') => void
  setPage: (page: number) => void
  toggleRow: (id: string, checked: boolean) => void
  toggleAll: (ids: string[], checked: boolean) => void
  clearSelection: () => void
  setColumnVisible: (columnId: string, visible: boolean) => void
  applySavedView: (view: ListSavedViewRecord) => void
  saveCurrentView: (name: string) => void
  removeSavedView: (id: string) => void
}

function writeQuery(setSearchParams: (next: URLSearchParams, opts?: { replace?: boolean }) => void, query: ListQueryState, definition: ListDefinition<unknown>) {
  setSearchParams(serializeListQuery(query, definition), { replace: true })
}

export function useListWorkspace<T>(definition: ListDefinition<T>, options?: {
  initialFilters?: Record<string, string>
}): ListWorkspaceController<T> {
  const [searchParams, setSearchParams] = useSearchParams()
  const defaultViewApplied = useRef(false)
  const initialFiltersApplied = useRef(false)
  const definitionRef = useRef(definition)
  definitionRef.current = definition
  const paramKey = searchParams.toString()

  const query = useMemo(
    () => parseListQuery(searchParams, definitionRef.current),
    [paramKey, searchParams],
  )

  const commit = useCallback(
    (next: ListQueryState) => {
      writeQuery(setSearchParams, next, definitionRef.current)
    },
    [setSearchParams],
  )

  const defaultViewId = definition.savedViews?.views.find((view) => view.isDefault)?.id
  useEffect(() => {
    if (defaultViewApplied.current) return
    const def = definitionRef.current
    if (!listQueryIsEmpty(query, def)) {
      defaultViewApplied.current = true
      return
    }
    const defaultView = def.savedViews?.views.find((view) => view.isDefault)
    if (!defaultView) return
    defaultViewApplied.current = true
    commit(parseListQuery(defaultView.query, def))
  }, [commit, defaultViewId, query])

  useEffect(() => {
    if (initialFiltersApplied.current) return
    const initial = options?.initialFilters
    if (!initial || Object.keys(initial).length === 0) return
    const pending: Record<string, string> = {}
    for (const [key, value] of Object.entries(initial)) {
      if (value && !query.filters[key]) pending[key] = value
    }
    initialFiltersApplied.current = true
    if (Object.keys(pending).length === 0) return
    commit({ ...query, filters: { ...query.filters, ...pending }, page: 1 })
  }, [commit, options?.initialFilters, query])

  const [selectedIds, setSelectedIds] = useState<string[]>([])
  const querySignature = `${query.q}|${query.page}|${query.sortColumnId}|${query.sortDirection}|${JSON.stringify(query.filters)}`
  useEffect(() => {
    setSelectedIds([])
  }, [querySignature])

  const [hiddenColumnIds, setHiddenColumnIds] = useState<string[]>(() =>
    definition.columns.filter((column) => column.defaultHidden).map((column) => column.id),
  )

  const visibleColumnIds = useMemo(
    () => definition.columns.filter((column) => !hiddenColumnIds.includes(column.id)).map((column) => column.id),
    [definition.columns, hiddenColumnIds],
  )

  const setSearch = useCallback((value: string) => commit(applySearch(query, value)), [commit, query])
  const setFilter = useCallback(
    (urlKey: string, value: string) => commit(applyFilter(query, urlKey, value)),
    [commit, query],
  )
  const resetQueryFilters = useCallback(() => commit(resetFilters(query)), [commit, query])
  const setSort = useCallback(
    (columnId: string, direction: 'asc' | 'desc') => {
      const column = definition.columns.find((item) => item.id === columnId)
      commit(applySort(query, columnId, direction, column?.defaultSortDirection))
    },
    [commit, definition.columns, query],
  )
  const setPage = useCallback((page: number) => commit(applyPage(query, page)), [commit, query])

  const toggleRow = useCallback((id: string, checked: boolean) => {
    setSelectedIds((prev) => (checked ? Array.from(new Set([...prev, id])) : prev.filter((item) => item !== id)))
  }, [])
  const toggleAll = useCallback((ids: string[], checked: boolean) => {
    setSelectedIds(checked ? ids : [])
  }, [])
  const clearSelection = useCallback(() => setSelectedIds([]), [])

  const setColumnVisible = useCallback((columnId: string, visible: boolean) => {
    setHiddenColumnIds((prev) => {
      if (visible) return prev.filter((id) => id !== columnId)
      if (prev.includes(columnId)) return prev
      return [...prev, columnId]
    })
  }, [])

  const applySavedView = useCallback(
    (view: ListSavedViewRecord) => {
      commit(parseListQuery(view.query, definition))
    },
    [commit, definition],
  )

  const saveCurrentView = useCallback(
    (name: string) => {
      const trimmed = name.trim()
      if (!trimmed || !definition.savedViews?.onSave) return
      const snapshot = Object.fromEntries(serializeListQuery(query, definition).entries())
      delete snapshot.page
      const record: ListSavedViewRecord = {
        id:
          typeof crypto !== 'undefined' && 'randomUUID' in crypto
            ? crypto.randomUUID()
            : String(Date.now()),
        name: trimmed,
        query: snapshot,
      }
      const next = [...definition.savedViews.views.filter((view) => view.name !== trimmed), record]
      void definition.savedViews.onSave(record, next)
    },
    [definition, query],
  )

  const removeSavedView = useCallback(
    (id: string) => {
      if (!definition.savedViews?.onRemove) return
      const next = definition.savedViews.views.filter((view) => view.id !== id)
      void definition.savedViews.onRemove(id, next)
    },
    [definition.savedViews],
  )

  return {
    definition,
    query,
    selectedIds,
    visibleColumnIds,
    setSearch,
    setFilter,
    resetQueryFilters,
    setSort,
    setPage,
    toggleRow,
    toggleAll,
    clearSelection,
    setColumnVisible,
    applySavedView,
    saveCurrentView,
    removeSavedView,
  }
}
