import { useCallback, useEffect, useRef, useState } from 'react'

import { getLeadNextAction, type LeadNextActionDTO } from '../../api/leads'

/**
 * Imperative React-Query-less hook for the per-lead primary "next action".
 *
 * Mirrors `useCandidateNextAction` (same fetch-on-mount + refresh-key +
 * window-event pattern). Listens for a `lead-updated` CustomEvent so a
 * stage / status / reminder mutation elsewhere in the page can punch a
 * fresh DTO without holding a `refetch` reference.
 *
 * NOTE: callers that mutate a lead and want the badge to update should
 * dispatch `new CustomEvent('lead-updated', { detail: { leadId } })`. We
 * deliberately reuse the same name shape as candidate-updated to keep the
 * event surface predictable.
 */
export interface UseLeadNextActionResult {
  data: LeadNextActionDTO | null
  loading: boolean
  error: unknown
  refetch: () => Promise<void>
}

export function useLeadNextAction(
  leadId: string | null | undefined,
  refreshKey: number = 0,
): UseLeadNextActionResult {
  const [data, setData] = useState<LeadNextActionDTO | null>(null)
  const [loading, setLoading] = useState<boolean>(false)
  const [error, setError] = useState<unknown>(null)

  // Guard against late responses overwriting newer ones — common when the
  // user clicks through leads fast in the split view.
  const requestSeq = useRef(0)
  const mounted = useRef(true)
  useEffect(() => {
    mounted.current = true
    return () => {
      mounted.current = false
    }
  }, [])

  const refetch = useCallback(async () => {
    if (!leadId) {
      setData(null)
      setError(null)
      return
    }
    const seq = ++requestSeq.current
    setLoading(true)
    setError(null)
    try {
      const dto = await getLeadNextAction(leadId)
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
  }, [leadId])

  useEffect(() => {
    if (!leadId) {
      setData(null)
      return
    }
    void refetch()
  }, [leadId, refreshKey, refetch])

  useEffect(() => {
    if (!leadId) return
    const handler = (event: Event) => {
      const detail = (event as CustomEvent<{ leadId?: string }>).detail
      if (!detail || detail.leadId === leadId) {
        void refetch()
      }
    }
    window.addEventListener('lead-updated', handler as EventListener)
    return () => {
      window.removeEventListener('lead-updated', handler as EventListener)
    }
  }, [leadId, refetch])

  return { data, loading, error, refetch }
}
