import { useCallback, useEffect, useRef, useState } from 'react'

import { getVacancyNextAction, type VacancyNextActionDTO } from '../../api/vacancies'

/**
 * Imperative React-Query-less hook for the per-vacancy primary "next action".
 *
 * Mirrors `useLeadNextAction` / `useCandidateNextAction`: fetch on mount +
 * when the entity id changes, expose `refetch` for callers that mutate
 * lifecycle state (status flip, archive toggle, recruiter assign), plus a
 * `vacancy-updated` window-event listener so siblings on the page can punch
 * a refresh without holding a `refetch` reference.
 *
 * NOTE: callers that mutate a vacancy and want the badge to update should
 * dispatch `new CustomEvent('vacancy-updated', { detail: { vacancyId } })`.
 * We deliberately mirror the same event shape used by candidate / lead so
 * the surface stays predictable.
 */
export interface UseVacancyNextActionResult {
  data: VacancyNextActionDTO | null
  loading: boolean
  error: unknown
  refetch: () => Promise<void>
}

export function useVacancyNextAction(
  vacancyId: string | null | undefined,
  refreshKey: number = 0,
): UseVacancyNextActionResult {
  const [data, setData] = useState<VacancyNextActionDTO | null>(null)
  const [loading, setLoading] = useState<boolean>(false)
  const [error, setError] = useState<unknown>(null)

  // Guard against late responses overwriting newer ones — common when the
  // user opens vacancies fast through the kanban / list.
  const requestSeq = useRef(0)
  const mounted = useRef(true)
  useEffect(() => {
    mounted.current = true
    return () => {
      mounted.current = false
    }
  }, [])

  const refetch = useCallback(async () => {
    if (!vacancyId) {
      setData(null)
      setError(null)
      return
    }
    const seq = ++requestSeq.current
    setLoading(true)
    setError(null)
    try {
      const dto = await getVacancyNextAction(vacancyId)
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
  }, [vacancyId])

  useEffect(() => {
    if (!vacancyId) {
      setData(null)
      return
    }
    void refetch()
  }, [vacancyId, refreshKey, refetch])

  useEffect(() => {
    if (!vacancyId) return
    const handler = (event: Event) => {
      const detail = (event as CustomEvent<{ vacancyId?: string }>).detail
      if (!detail || detail.vacancyId === vacancyId) {
        void refetch()
      }
    }
    window.addEventListener('vacancy-updated', handler as EventListener)
    return () => {
      window.removeEventListener('vacancy-updated', handler as EventListener)
    }
  }, [vacancyId, refetch])

  return { data, loading, error, refetch }
}
