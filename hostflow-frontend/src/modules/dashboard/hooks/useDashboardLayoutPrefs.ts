import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  DEFAULT_VISIBLE_WIDGETS,
  DEFAULT_VISIBLE_FILTERS,
  type DashboardWidgetId,
  type DashboardFilterId,
} from '../types'

export interface UseDashboardLayoutPrefsOptions {
  dashUserBase: string
  tenantId: string | null
}

export interface UseDashboardLayoutPrefsResult {
  visibleWidgetsKey: string
  visibleFiltersKey: string
  dashboardPresetKey: string
  visibleWidgets: Set<string>
  setVisibleWidgets: React.Dispatch<React.SetStateAction<Set<string>>>
  visibleFilters: Set<string>
  setVisibleFilters: React.Dispatch<React.SetStateAction<Set<string>>>
  isWidgetVisible: (id: DashboardWidgetId) => boolean
  isFilterVisible: (id: DashboardFilterId) => boolean
  toggleWidget: (id: DashboardWidgetId) => void
  toggleFilter: (id: DashboardFilterId) => void
  savedPreset: Record<string, unknown> | null
  setSavedPreset: React.Dispatch<React.SetStateAction<Record<string, unknown> | null>>
}

/**
 * Encapsulates dashboard layout-preference state:
 * - Per-user storage keys for visible widgets / filters / saved preset.
 * - One-shot migration from legacy tenant-scoped keys to user-scoped keys.
 * - Visible widgets / filters Sets persisted to localStorage on toggle.
 * - Saved preset hydration from storage.
 *
 * The actual save/load preset handlers live in the page since they touch
 * many other state setters (filters, dates, pivot, ...) and the load() call.
 */
export function useDashboardLayoutPrefs({
  dashUserBase,
  tenantId,
}: UseDashboardLayoutPrefsOptions): UseDashboardLayoutPrefsResult {
  const visibleWidgetsKey = useMemo(() => `${dashUserBase}:visibleWidgets`, [dashUserBase])
  const visibleFiltersKey = useMemo(() => `${dashUserBase}:visibleFilters`, [dashUserBase])
  const dashboardPresetKey = useMemo(() => `${dashUserBase}:preset`, [dashUserBase])

  useEffect(() => {
    const migrate = (suffix: string) => {
      const nk = `${dashUserBase}:${suffix}`
      const ok = `hf:dashboard:${tenantId}:${suffix}`
      try {
        if (!localStorage.getItem(nk) && localStorage.getItem(ok)) {
          localStorage.setItem(nk, localStorage.getItem(ok)!)
        }
      } catch {
        /* ignore */
      }
    }
    migrate('visibleWidgets')
    migrate('visibleFilters')
    migrate('preset')
    migrate('sections')
  }, [dashUserBase, tenantId])

  const loadVisibleWidgets = useCallback((): Set<string> => {
    try {
      const raw = localStorage.getItem(visibleWidgetsKey)
      if (raw) {
        const arr = JSON.parse(raw)
        if (Array.isArray(arr)) return new Set(arr)
      }
    } catch {
      /* ignore */
    }
    return new Set(DEFAULT_VISIBLE_WIDGETS)
  }, [visibleWidgetsKey])

  const loadVisibleFilters = useCallback((): Set<string> => {
    try {
      const raw = localStorage.getItem(visibleFiltersKey)
      if (raw) {
        const arr = JSON.parse(raw)
        if (Array.isArray(arr)) return new Set(arr)
      }
    } catch {
      /* ignore */
    }
    return new Set(DEFAULT_VISIBLE_FILTERS)
  }, [visibleFiltersKey])

  const [visibleWidgets, setVisibleWidgets] = useState<Set<string>>(loadVisibleWidgets)
  const [visibleFilters, setVisibleFilters] = useState<Set<string>>(loadVisibleFilters)

  useEffect(() => {
    setVisibleWidgets(loadVisibleWidgets())
    setVisibleFilters(loadVisibleFilters())
  }, [dashUserBase, loadVisibleWidgets, loadVisibleFilters])

  const isWidgetVisible = useCallback(
    (id: DashboardWidgetId) => visibleWidgets.has(id),
    [visibleWidgets],
  )
  const isFilterVisible = useCallback(
    (id: DashboardFilterId) => visibleFilters.has(id),
    [visibleFilters],
  )

  const toggleWidget = useCallback(
    (id: DashboardWidgetId) => {
      setVisibleWidgets((prev) => {
        const next = new Set(prev)
        if (next.has(id)) next.delete(id)
        else next.add(id)
        try {
          localStorage.setItem(visibleWidgetsKey, JSON.stringify([...next]))
        } catch {
          /* ignore */
        }
        return next
      })
    },
    [visibleWidgetsKey],
  )

  const toggleFilter = useCallback(
    (id: DashboardFilterId) => {
      setVisibleFilters((prev) => {
        const next = new Set(prev)
        if (next.has(id)) next.delete(id)
        else next.add(id)
        try {
          localStorage.setItem(visibleFiltersKey, JSON.stringify([...next]))
        } catch {
          /* ignore */
        }
        return next
      })
    },
    [visibleFiltersKey],
  )

  const [savedPreset, setSavedPreset] = useState<Record<string, unknown> | null>(null)

  useEffect(() => {
    try {
      const raw = localStorage.getItem(dashboardPresetKey)
      if (raw) setSavedPreset(JSON.parse(raw) as Record<string, unknown>)
    } catch {
      /* ignore */
    }
  }, [dashboardPresetKey])

  return {
    visibleWidgetsKey,
    visibleFiltersKey,
    dashboardPresetKey,
    visibleWidgets,
    setVisibleWidgets,
    visibleFilters,
    setVisibleFilters,
    isWidgetVisible,
    isFilterVisible,
    toggleWidget,
    toggleFilter,
    savedPreset,
    setSavedPreset,
  }
}
