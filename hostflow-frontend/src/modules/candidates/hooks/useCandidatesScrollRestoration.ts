import { useCallback } from 'react'
import type { Dispatch, MutableRefObject, RefObject, SetStateAction } from 'react'
import type { AugmentedCandidate } from '../types'
import {
  RESTORE_SCROLL_MAX_ATTEMPTS,
  SCROLL_STATE_TTL_MS,
} from '../constants'

type UseCandidatesScrollRestorationArgs = {
  displayedItems: AugmentedCandidate[]
  setRecentlyOpenedId: Dispatch<SetStateAction<string | null>>
  getScrollContainer: () => HTMLElement | null
  outerScrollRef: RefObject<HTMLElement | null>
  scrollKey: string
  restoredScrollRef: MutableRefObject<boolean>
  restoreAttemptsRef: MutableRefObject<number>
}

export function useCandidatesScrollRestoration({
  displayedItems,
  setRecentlyOpenedId,
  getScrollContainer,
  outerScrollRef,
  scrollKey,
  restoredScrollRef,
  restoreAttemptsRef,
}: UseCandidatesScrollRestorationArgs) {
  const persistScrollState = useCallback(
    (candidateId?: string) => {
      try {
        const container = getScrollContainer()
        const containerTop = container?.scrollTop ?? null
        const outer = outerScrollRef.current
        const outerTop = (outer?.scrollTop ?? window.scrollY) || 0
        const idx = candidateId ? displayedItems.findIndex((it) => it.id === candidateId) : -1
        const payload = {
          top: outerTop,
          id: candidateId ?? null,
          ts: Date.now(),
          scrollContainerTop: containerTop,
          index: idx >= 0 ? idx : null,
          windowTop: outerTop,
        }
        localStorage.setItem(scrollKey, JSON.stringify(payload))
      } catch {
        /* ignore storage errors */
      }
    },
    [displayedItems, getScrollContainer, outerScrollRef, scrollKey],
  )

  const restoreScrollState = useCallback(() => {
    if (restoredScrollRef.current) return
    restoredScrollRef.current = true

    try {
      const raw = localStorage.getItem(scrollKey)
      if (!raw) return
      const parsed = JSON.parse(raw)
      if (!parsed || typeof parsed !== 'object') return

      const ts = typeof parsed.ts === 'number' ? parsed.ts : 0
      if (Date.now() - ts > SCROLL_STATE_TTL_MS) {
        // Remove stale state
        try {
          localStorage.removeItem(scrollKey)
        } catch {
          /* ignore */
        }
        return
      }

      const top = typeof parsed.top === 'number' ? parsed.top : 0
      const containerTop = typeof parsed.scrollContainerTop === 'number' ? parsed.scrollContainerTop : null
      const windowTop = typeof parsed.windowTop === 'number' ? parsed.windowTop : null
      const savedIndex = typeof parsed.index === 'number' ? parsed.index : null
      const id = typeof parsed.id === 'string' ? parsed.id : null

      if (id) setRecentlyOpenedId(id)

      const attemptRestore = () => {
        const container = getScrollContainer()

        if (windowTop !== null && windowTop > 0) {
          const outer = outerScrollRef.current
          if (outer) outer.scrollTo({ top: windowTop, behavior: 'auto' })
          else window.scrollTo({ top: windowTop, behavior: 'auto' })
        }

        const rowSelector = id ? `[data-candidate-id="${id}"]` : null
        const rowEl = rowSelector ? document.querySelector(rowSelector) as HTMLElement | null : null
        const targetRow = rowEl?.closest('tr') as HTMLElement | null ?? rowEl

        if (targetRow) {
          targetRow.scrollIntoView({ block: 'center', inline: 'nearest', behavior: 'auto' })
          return true
        }

        // если строка не отрендерена, попробуем виртуализатором проскроллить по индексу
        {
          const idx =
            savedIndex !== null
              ? savedIndex
              : id
                ? displayedItems.findIndex((item) => item.id === id)
                : -1
          if (idx >= 0) {
            queueMicrotask(() => {
              const row = document.querySelector(
                `[data-candidates-table-container] tr[data-index="${idx}"]`,
              ) as HTMLElement | null
              row?.scrollIntoView({ block: 'center', behavior: 'auto' })
            })
            return true
          }
        }

        if (container && containerTop !== null) {
          container.scrollTo({ top: containerTop, behavior: 'auto' })
          return true
        }

        return top === 0 ? false : true
      }

      const finalize = () => {
        // Keep saved state for next return; reset attempts counter.
        restoreAttemptsRef.current = 0
      }

      const runAttempt = () => {
        const ok = attemptRestore()
        if (ok) {
          finalize()
          restoredScrollRef.current = true
          return
        }

        restoreAttemptsRef.current += 1
        restoredScrollRef.current = false
        if (restoreAttemptsRef.current >= RESTORE_SCROLL_MAX_ATTEMPTS) {
          finalize()
          restoredScrollRef.current = true
          return
        }

        // give time to render more rows
        window.setTimeout(runAttempt, 150)
      }

      requestAnimationFrame(runAttempt)
    } catch {
      /* ignore malformed storage */
    }
  }, [
    displayedItems,
    getScrollContainer,
    outerScrollRef,
    restoredScrollRef,
    restoreAttemptsRef,
    scrollKey,
    setRecentlyOpenedId,
  ])

  return { persistScrollState, restoreScrollState }
}

