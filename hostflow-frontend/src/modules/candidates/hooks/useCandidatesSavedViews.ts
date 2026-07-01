import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { patchUserMe } from '../../../api/users'
import type { UserSavedView, UserPreferences } from '../../../api/types'

type UseCandidatesSavedViewsArgs = {
  preferences: UserPreferences | null
  updatePreferences: (prefs: UserPreferences) => void
  filtersHydrated: boolean
  applyViewFilters: (filters: Record<string, any> | undefined) => void
  skipDefaultView?: boolean
}

export function useCandidatesSavedViews({
  preferences,
  updatePreferences,
  filtersHydrated,
  applyViewFilters,
  skipDefaultView,
}: UseCandidatesSavedViewsArgs) {
  const vacancySavedViews = useMemo(() => preferences?.saved_views?.vacancies ?? [], [preferences?.saved_views?.vacancies])

  const [savedViews, setSavedViews] = useState<UserSavedView[]>(preferences?.saved_views?.candidates ?? [])
  const [saveViewOpen, setSaveViewOpen] = useState(false)
  const [saveViewName, setSaveViewName] = useState('')

  const appliedDefaultIdRef = useRef<string | null>(null)

  useEffect(() => {
    setSavedViews(preferences?.saved_views?.candidates ?? [])
  }, [preferences?.saved_views?.candidates])

  const syncCandidateViews = useCallback(
    async (next: UserSavedView[]) => {
      setSavedViews(next)
      try {
        const result = await patchUserMe({
          preferences: {
            saved_views: {
              candidates: next,
              vacancies: vacancySavedViews,
            },
          },
        } as any)
        updatePreferences(result.preferences as UserPreferences)
      } catch (err) {
        console.warn('[Candidates] failed to persist saved views', err)
        setSavedViews(preferences?.saved_views?.candidates ?? [])
      }
    },
    [updatePreferences, vacancySavedViews, preferences?.saved_views?.candidates],
  )

  const applyView = useCallback(
    (view: UserSavedView) => {
      applyViewFilters(view.filters ?? {})
    },
    [applyViewFilters],
  )

  const deleteView = useCallback(
    async (id: string) => {
      const next = savedViews.filter((view) => view.id !== id)
      await syncCandidateViews(next)
    },
    [savedViews, syncCandidateViews],
  )

  useEffect(() => {
    if (!filtersHydrated) return
    if (skipDefaultView) return
    const defaultView = savedViews.find((view) => view.is_default)
    if (defaultView && appliedDefaultIdRef.current !== defaultView.id) {
      applyViewFilters(defaultView.filters ?? {})
      appliedDefaultIdRef.current = defaultView.id
    }
  }, [filtersHydrated, savedViews, applyViewFilters])

  return {
    savedViews,
    saveViewOpen,
    setSaveViewOpen,
    saveViewName,
    setSaveViewName,
    syncCandidateViews,
    applyView,
    deleteView,
  }
}

