import { useCallback, useEffect, useState } from 'react'

import { getClientNextAction } from '../../api/client'
import type { NextActionDTO } from '../../api/nextAction'

interface UseClientNextActionResult {
  data: NextActionDTO | null
  loading: boolean
  error: unknown
  refresh: () => void
}

/**
 * Fetches the single primary "what to do next" for a client workspace.
 *
 * The client Workspace exists because there is WORK with this counterparty,
 * regardless of how the row was created (Sales, manual, import, API), so the
 * CTA is available for a client of any origin. Mirrors the backend
 * `compute_client_next_action` / `GET /companies/{id}/next-action`.
 *
 * Pass `companyId = null` (e.g. the "new" draft or an operating company) to
 * keep the hook inert — it will not fetch and returns a null DTO.
 */
export function useClientNextAction(companyId: string | null | undefined): UseClientNextActionResult {
  const [data, setData] = useState<NextActionDTO | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<unknown>(null)
  const [nonce, setNonce] = useState(0)

  const refresh = useCallback(() => setNonce((n) => n + 1), [])

  useEffect(() => {
    const id = (companyId || '').trim()
    if (!id || id === 'new') {
      setData(null)
      setLoading(false)
      setError(null)
      return
    }
    let cancelled = false
    setLoading(true)
    setError(null)
    getClientNextAction(id)
      .then((dto) => {
        if (!cancelled) setData(dto)
      })
      .catch((err) => {
        if (!cancelled) setError(err)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [companyId, nonce])

  return { data, loading, error, refresh }
}

export default useClientNextAction
