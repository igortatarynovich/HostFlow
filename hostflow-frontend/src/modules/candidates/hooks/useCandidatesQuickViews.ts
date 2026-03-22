import { useCallback, useEffect, useMemo, useState } from 'react'
import { QUICK_DOC_STATUS_SETS } from '../constants'
import type { DateRangeFilter } from '../types'

type QuickViewKey =
  | 'my_work_today'
  | 'overdue_next_action'
  | 'no_next_action'
  | 'docs_incomplete'
  | 'ready_for_handoff'
  | 'new_this_week'

type QuickDocFilter = {
  key: string
  label: string
  statuses: string[]
  active: boolean
}

type UseCandidatesQuickViewsArgs = {
  t: (key: string, options?: any) => string
  searchParams: URLSearchParams
  setSearchParams: (next: URLSearchParams, opts?: { replace?: boolean }) => void
  filtersHydrated: boolean
  handleResetFilters: () => void
  preferredManagerId: string
  docsStatusFilter: string[]
  setDocsStatusFilter: (value: string[]) => void
  setManagerFilter: (value: string[]) => void
  setCreatedRange: (value: DateRangeFilter) => void
  setHandoffStatusFilter: (value: string) => void
}

export function useCandidatesQuickViews({
  t,
  searchParams,
  setSearchParams,
  filtersHydrated,
  handleResetFilters,
  preferredManagerId,
  docsStatusFilter,
  setDocsStatusFilter,
  setManagerFilter,
  setCreatedRange,
  setHandoffStatusFilter,
}: UseCandidatesQuickViewsArgs) {
  type QuickViewParam = QuickViewKey | ''

  const QUICK_FILTERS_STORAGE_KEY = 'hf:candidates:quickFiltersExpanded'
  const [quickFiltersExpanded, setQuickFiltersExpanded] = useState(() => {
    try {
      return window.localStorage.getItem(QUICK_FILTERS_STORAGE_KEY) === '1'
    } catch {
      return false
    }
  })

  useEffect(() => {
    try {
      window.localStorage.setItem(QUICK_FILTERS_STORAGE_KEY, quickFiltersExpanded ? '1' : '0')
    } catch {
      /* ignore */
    }
  }, [quickFiltersExpanded])

  const quickViewParam = (searchParams.get('qv') || '') as QuickViewParam

  const quickDocFilters = useMemo<QuickDocFilter[]>(() => {
    const entries: Array<{ key: string; label: string; statuses: string[] }> = [
      { key: 'ready', label: t('app.candidates.filters.quick_docs_ready'), statuses: QUICK_DOC_STATUS_SETS.ready },
      {
        key: 'attention',
        label: t('app.candidates.filters.quick_docs_attention'),
        statuses: QUICK_DOC_STATUS_SETS.attention,
      },
      { key: 'pending', label: t('app.candidates.filters.quick_docs_pending'), statuses: QUICK_DOC_STATUS_SETS.pending },
    ]

    return entries.map((entry) => {
      const active =
        docsStatusFilter.length === entry.statuses.length && entry.statuses.every((status) => docsStatusFilter.includes(status))
      return { ...entry, active }
    })
  }, [docsStatusFilter, t])

  const toggleQuickDocFilter = useCallback(
    (statuses: string[], active: boolean) => {
      if (active) setDocsStatusFilter([])
      else setDocsStatusFilter(statuses)
    },
    [setDocsStatusFilter],
  )

  const applyQuickViewFilters = useCallback(
    (key: QuickViewKey, opts?: { syncUrl?: boolean }) => {
      const syncUrl = opts?.syncUrl ?? false

      const next = new URLSearchParams(searchParams)
      if (syncUrl) next.set('qv', key)
      if (syncUrl) setSearchParams(next, { replace: true })

      const setTodayRange = (start: Date, end: Date) => {
        setCreatedRange({
          from: start.toISOString().slice(0, 10),
          to: end.toISOString().slice(0, 10),
        })
      }

      // Always start from a clean slate for deterministic presets.
      handleResetFilters()

      switch (key) {
        case 'my_work_today': {
          const todayStart = new Date()
          todayStart.setHours(0, 0, 0, 0)
          const todayEnd = new Date()
          todayEnd.setHours(23, 59, 59, 999)
          setManagerFilter(preferredManagerId ? [preferredManagerId] : [])
          setTodayRange(todayStart, todayEnd)
          break
        }
        case 'new_this_week': {
          const end = new Date()
          end.setHours(23, 59, 59, 999)
          const start = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000)
          start.setHours(0, 0, 0, 0)
          setTodayRange(start, end)
          break
        }
        case 'docs_incomplete': {
          // incomplete = attention + pending
          setDocsStatusFilter([...QUICK_DOC_STATUS_SETS.attention, ...QUICK_DOC_STATUS_SETS.pending])
          break
        }
        case 'ready_for_handoff': {
          setHandoffStatusFilter('pending')
          setDocsStatusFilter(['ready'])
          break
        }
        default:
          break
      }
    },
    [
      handleResetFilters,
      preferredManagerId,
      searchParams,
      setCreatedRange,
      setDocsStatusFilter,
      setHandoffStatusFilter,
      setManagerFilter,
      setSearchParams,
    ],
  )

  useEffect(() => {
    if (!filtersHydrated) return
    if (!quickViewParam) return

    const key = quickViewParam as QuickViewKey
    if (['my_work_today', 'docs_incomplete', 'ready_for_handoff', 'new_this_week'].includes(key)) {
      applyQuickViewFilters(key, { syncUrl: false })
    }
  }, [applyQuickViewFilters, filtersHydrated, quickViewParam])

  return {
    quickViewParam,
    quickFiltersExpanded,
    setQuickFiltersExpanded,
    quickDocFilters,
    toggleQuickDocFilter,
    applyQuickViewFilters,
  }
}

