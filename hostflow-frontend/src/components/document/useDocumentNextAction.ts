import { useCallback, useEffect, useRef, useState } from 'react'

import { getDocumentNextAction, type DocumentNextActionDTO } from '../../api/documents'

/**
 * Imperative React-Query-less hook for the per-document primary "next action".
 *
 * Mirrors `useVacancyNextAction` / `useLeadNextAction` / `useCandidateNextAction`:
 * fetch on mount + when the entity id changes, expose `refetch` for callers
 * that mutate lifecycle state (status flip, file upload, approve/reject),
 * plus a `document-updated` window-event listener so siblings on the page
 * can punch a refresh without holding a `refetch` reference.
 *
 * USAGE NOTE: a single candidate documents tab can render N badges (one per
 * `DocumentCard`). That fans out to N parallel requests on mount, which is
 * acceptable today (typical N ≤ 20, each query is a few-row SELECT). If
 * this becomes a perf problem, replace this hook with a bulk
 * `POST /db/documents/next-actions` taking an array of IDs and broadcasting
 * via a shared context. Today's per-card hook keeps the integration trivial.
 */
export interface UseDocumentNextActionResult {
  data: DocumentNextActionDTO | null
  loading: boolean
  error: unknown
  refetch: () => Promise<void>
}

export function useDocumentNextAction(
  documentId: string | null | undefined,
  // Accepts any primitive — typical caller patterns are (a) a numeric tick
  // they bump after mutations or (b) a string fingerprint of the doc's
  // lifecycle fields (`status|expire_date|deleted_at|has_files`) so the
  // badge follows in-place edits without an explicit refresh action.
  refreshKey: number | string = 0,
): UseDocumentNextActionResult {
  const [data, setData] = useState<DocumentNextActionDTO | null>(null)
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
    if (!documentId) {
      setData(null)
      setError(null)
      return
    }
    const seq = ++requestSeq.current
    setLoading(true)
    setError(null)
    try {
      const dto = await getDocumentNextAction(documentId)
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
  }, [documentId])

  useEffect(() => {
    if (!documentId) {
      setData(null)
      return
    }
    void refetch()
  }, [documentId, refreshKey, refetch])

  useEffect(() => {
    if (!documentId) return
    const handler = (event: Event) => {
      const detail = (event as CustomEvent<{ documentId?: string }>).detail
      if (!detail || detail.documentId === documentId) {
        void refetch()
      }
    }
    window.addEventListener('document-updated', handler as EventListener)
    return () => {
      window.removeEventListener('document-updated', handler as EventListener)
    }
  }, [documentId, refetch])

  return { data, loading, error, refetch }
}
