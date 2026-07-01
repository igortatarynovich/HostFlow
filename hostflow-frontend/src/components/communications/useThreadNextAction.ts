import { useCallback, useEffect, useRef, useState } from 'react'

import {
  getThreadNextAction,
  type ThreadNextActionDTO,
} from '../../api/communications/nextAction'

/**
 * Imperative React-Query-less hook for the per-thread primary "next action".
 *
 * Mirrors `useDocumentNextAction` / `useVacancyNextAction` /
 * `useLeadNextAction` / `useCandidateNextAction`: fetch on mount + when
 * the entity id changes, expose `refetch` for callers that mutate
 * lifecycle state (mark-as-read, send reply, archive, status change),
 * plus a `thread-updated` window-event listener so siblings on the page
 * can punch a refresh without holding a `refetch` reference.
 *
 * USAGE NOTE: a thread detail view renders ONE badge, so this hook fans
 * out to a single SELECT + one Reminder lookup. There is no fan-out
 * concern (unlike DocumentCard where N badges per candidate appear).
 *
 * The `refreshKey` accepts `string | number` so callers can pass either
 * a numeric tick they bump after mutations OR a string fingerprint of
 * thread lifecycle fields (`status|unread_count|sla_due_at|...`) that
 * the badge should follow without an explicit refresh action.
 */
export interface UseThreadNextActionResult {
  data: ThreadNextActionDTO | null
  loading: boolean
  error: unknown
  refetch: () => Promise<void>
}

export function useThreadNextAction(
  threadId: string | null | undefined,
  refreshKey: number | string = 0,
): UseThreadNextActionResult {
  const [data, setData] = useState<ThreadNextActionDTO | null>(null)
  const [loading, setLoading] = useState<boolean>(false)
  const [error, setError] = useState<unknown>(null)

  const requestSeq = useRef(0)
  const mounted = useRef(true)
  useEffect(() => {
    mounted.current = true
    return () => {
      mounted.current = false
    }
  }, [])

  const refetch = useCallback(async () => {
    if (!threadId) {
      setData(null)
      setError(null)
      return
    }
    const seq = ++requestSeq.current
    setLoading(true)
    setError(null)
    try {
      const dto = await getThreadNextAction(threadId)
      if (mounted.current && seq === requestSeq.current) {
        setData(dto)
      }
    } catch (err) {
      if (mounted.current && seq === requestSeq.current) {
        setError(err)
        setData(null)
      }
    } finally {
      if (mounted.current && seq === requestSeq.current) {
        setLoading(false)
      }
    }
  }, [threadId])

  useEffect(() => {
    if (!threadId) {
      setData(null)
      return
    }
    void refetch()
  }, [threadId, refreshKey, refetch])

  useEffect(() => {
    if (!threadId) return
    const handler = (event: Event) => {
      const detail = (event as CustomEvent<{ threadId?: string }>).detail
      if (!detail || detail.threadId === threadId) {
        void refetch()
      }
    }
    window.addEventListener('thread-updated', handler as EventListener)
    return () => {
      window.removeEventListener('thread-updated', handler as EventListener)
    }
  }, [threadId, refetch])

  return { data, loading, error, refetch }
}
