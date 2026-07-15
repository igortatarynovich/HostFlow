import { useCallback, useEffect, useState } from 'react'

import { getClientPreparationChecklist } from '../../api/client'
import type { ClientPreparationChecklistDTO } from '../../api/clientPreparation'

interface UseClientPreparationChecklistResult {
  data: ClientPreparationChecklistDTO | null
  loading: boolean
  error: unknown
  refresh: () => void
}

export function useClientPreparationChecklist(
  companyId: string | null | undefined,
): UseClientPreparationChecklistResult {
  const [data, setData] = useState<ClientPreparationChecklistDTO | null>(null)
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
    getClientPreparationChecklist(id)
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

export default useClientPreparationChecklist
