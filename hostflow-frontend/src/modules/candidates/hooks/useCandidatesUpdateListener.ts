// src/modules/candidates/hooks/useCandidatesUpdateListener.ts
//
// Cross-page / cross-tab listener that refreshes the Candidates list
// after a candidate is edited elsewhere (e.g. on the candidate card,
// in another browser tab via `localStorage`'s `storage` event, or after
// returning to the page via the back button).
//
// Two paired effects:
//
//   1. Route-change refetch — when the user navigates back to
//      `/crm/candidates`, force a full reload of the list unless the
//      candidate was edited within the past 10 s (in which case the
//      sibling `candidate-updated` listener will surgically refresh it).
//
//   2. Update broadcast listener — registers a `candidate-updated`
//      `CustomEvent` listener, a `storage` listener (cross-tab), and a
//      window-`focus` listener; debounces them, deduplicates rapid
//      duplicates per candidate id (500 ms guard), invalidates the
//      relevant caches and triggers a refetch.
//
// Extracted from inline `useEffect` blocks in `src/pages/Candidates.tsx`
// (Phase 1 #4 god-component split).

import type { MutableRefObject } from 'react'
import { useEffect } from 'react'
import { CRM_APP_PATHS } from '../../../app/crmAppPaths.generated'
import { candidateListCache } from '../internal'

const RECENT_EDIT_WINDOW_MS = 10_000
const DUPLICATE_GUARD_MS = 500
const REFETCH_DEBOUNCE_MS = 300
const FOCUS_DEBOUNCE_MS = 1_000
const INITIAL_CHECK_DELAY_MS = 3_000
const STORAGE_KEY = 'hf:candidate-updated'

interface LoadOptions {
  force?: boolean
  allowCache?: boolean
}

export interface CandidatesUpdateListenerCtx {
  pathname: string
  prevLocationRef: MutableRefObject<string | null>
  cacheKey: string
  listStorageKey: string
  load: (opts: LoadOptions) => Promise<unknown>
  recentlyUpdatedIdsRef: MutableRefObject<Map<string, number>>
  lastUpdateTimeRef: MutableRefObject<Map<string, number>>
  updateInProgressRef: MutableRefObject<Set<string>>
}

export function useCandidatesUpdateListener(ctx: CandidatesUpdateListenerCtx): void {
  const {
    pathname,
    prevLocationRef,
    cacheKey,
    listStorageKey,
    load,
    recentlyUpdatedIdsRef,
    lastUpdateTimeRef,
    updateInProgressRef,
  } = ctx

  // 1) Route-change refetch.
  useEffect(() => {
    const prevPath = prevLocationRef.current
    if (prevPath && prevPath !== pathname && pathname === CRM_APP_PATHS.candidates) {
      let shouldFullReload = true
      try {
        const updateData = localStorage.getItem(STORAGE_KEY)
        if (updateData) {
          const data = JSON.parse(updateData)
          if (
            data &&
            data.candidateId &&
            data.timestamp &&
            Date.now() - data.timestamp < RECENT_EDIT_WINDOW_MS
          ) {
            shouldFullReload = false
          }
        }
      } catch {
        /* ignore */
      }

      if (shouldFullReload) {
        candidateListCache.delete(cacheKey)
        try {
          localStorage.removeItem(listStorageKey)
        } catch {
          /* ignore */
        }
        void load({ force: true, allowCache: false })
      }
    }
    prevLocationRef.current = pathname
  }, [pathname, prevLocationRef, cacheKey, listStorageKey, load])

  // 2) Update broadcast listener (custom event + storage + focus).
  useEffect(() => {
    const handleCandidateUpdate = (event?: CustomEvent<{ candidateId: string }>) => {
      const candidateId = event?.detail?.candidateId
      if (!candidateId) return

      const now = Date.now()
      const lastUpdate = lastUpdateTimeRef.current.get(candidateId) || 0
      if (updateInProgressRef.current.has(candidateId) || now - lastUpdate < DUPLICATE_GUARD_MS) {
        return
      }

      updateInProgressRef.current.add(candidateId)
      lastUpdateTimeRef.current.set(candidateId, now)

      candidateListCache.delete(cacheKey)
      try {
        localStorage.removeItem(listStorageKey)
      } catch {
        /* ignore */
      }

      // Mark recently-updated so the candidate stays visible for the next 60 s
      // even if it would otherwise be filtered out.
      recentlyUpdatedIdsRef.current.set(candidateId, now)

      setTimeout(() => {
        load({ force: true, allowCache: false })
          .then(() => {
            updateInProgressRef.current.delete(candidateId)
          })
          .catch(() => {
            updateInProgressRef.current.delete(candidateId)
          })
      }, REFETCH_DEBOUNCE_MS)
    }

    const eventHandler = (e: Event) => {
      const customEvent = e as CustomEvent<{ candidateId: string }>
      handleCandidateUpdate(customEvent)
    }
    window.addEventListener('candidate-updated', eventHandler)

    const handleStorageChange = (e: StorageEvent) => {
      if (e.key === STORAGE_KEY && e.newValue) {
        try {
          const data = JSON.parse(e.newValue)
          if (data && data.candidateId) {
            handleCandidateUpdate(
              new CustomEvent('candidate-updated', { detail: { candidateId: data.candidateId } }),
            )
          }
        } catch {
          /* ignore */
        }
      }
    }
    window.addEventListener('storage', handleStorageChange)

    let checkTimeout: ReturnType<typeof setTimeout> | null = null
    const checkForUpdates = () => {
      if (checkTimeout) clearTimeout(checkTimeout)
      checkTimeout = setTimeout(() => {
        try {
          const updateData = localStorage.getItem(STORAGE_KEY)
          if (updateData) {
            const data = JSON.parse(updateData)
            if (
              data &&
              data.candidateId &&
              data.timestamp &&
              Date.now() - data.timestamp < RECENT_EDIT_WINDOW_MS
            ) {
              if (!updateInProgressRef.current.has(data.candidateId)) {
                handleCandidateUpdate(
                  new CustomEvent('candidate-updated', { detail: { candidateId: data.candidateId } }),
                )
              }
            }
          }
        } catch {
          /* ignore */
        }
      }, FOCUS_DEBOUNCE_MS)
    }

    const handleFocus = () => checkForUpdates()
    window.addEventListener('focus', handleFocus)

    const initialCheckTimeout = setTimeout(checkForUpdates, INITIAL_CHECK_DELAY_MS)

    return () => {
      window.removeEventListener('candidate-updated', eventHandler)
      window.removeEventListener('storage', handleStorageChange)
      window.removeEventListener('focus', handleFocus)
      if (checkTimeout) clearTimeout(checkTimeout)
      clearTimeout(initialCheckTimeout)
    }
  }, [cacheKey, listStorageKey, load, recentlyUpdatedIdsRef, lastUpdateTimeRef, updateInProgressRef])
}
