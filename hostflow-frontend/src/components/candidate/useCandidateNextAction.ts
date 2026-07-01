import { useCallback, useEffect, useRef, useState } from 'react'

import { getCandidateNextAction, type CandidateNextActionDTO } from '../../api/candidates'

/**
 * Imperative React Query-less hook for the per-candidate primary "next action".
 *
 * The codebase deliberately does NOT use `@tanstack/react-query`, so we mirror
 * the existing pattern (see `CandidateCard.tsx` reminder loaders): fetch on
 * mount + when the entity id changes, expose `refetch` so callers can punch a
 * fresh value after they mutate something (stage change, reminder create,
 * handoff submission, contact attempt — any event the DTO depends on).
 *
 * The `refreshKey` argument lets the parent invalidate without holding a
 * reference to `refetch` (cheaper to wire from many callers).
 */
export interface UseCandidateNextActionResult {
  data: CandidateNextActionDTO | null
  loading: boolean
  error: unknown
  refetch: () => Promise<void>
}

export function useCandidateNextAction(
  candidateId: string | null | undefined,
  refreshKey: number = 0,
): UseCandidateNextActionResult {
  const [data, setData] = useState<CandidateNextActionDTO | null>(null)
  const [loading, setLoading] = useState<boolean>(false)
  const [error, setError] = useState<unknown>(null)

  // Guard against late responses overwriting newer ones — common when the
  // user clicks through candidates fast.
  const requestSeq = useRef(0)
  const mounted = useRef(true)
  useEffect(() => {
    mounted.current = true
    return () => {
      mounted.current = false
    }
  }, [])

  const refetch = useCallback(async () => {
    if (!candidateId) {
      setData(null)
      setError(null)
      return
    }
    const seq = ++requestSeq.current
    setLoading(true)
    setError(null)
    try {
      const dto = await getCandidateNextAction(candidateId)
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
  }, [candidateId])

  useEffect(() => {
    if (!candidateId) {
      setData(null)
      return
    }
    void refetch()
  }, [candidateId, refreshKey, refetch])

  // Stage transitions dispatch a `candidate-updated` window event from
  // CandidateCard.tsx; we piggyback on it instead of asking every caller to
  // bump `refreshKey` after a stage change. Reminders / handoffs / contact
  // attempts still need explicit `bumpNextActionTick()` because they don't
  // dispatch this event today.
  useEffect(() => {
    if (!candidateId) return
    const handler = (event: Event) => {
      const detail = (event as CustomEvent<{ candidateId?: string }>).detail
      if (!detail || detail.candidateId === candidateId) {
        void refetch()
      }
    }
    window.addEventListener('candidate-updated', handler as EventListener)
    return () => {
      window.removeEventListener('candidate-updated', handler as EventListener)
    }
  }, [candidateId, refetch])

  return { data, loading, error, refetch }
}
