import { useCallback, useEffect, useState } from 'react'
import type { PublicStatusState } from '../../api/publicIntake'
import { getPublicStatus } from '../../api/publicIntake'
import { useI18n } from '../../i18n'

export type PublicStatusHook = {
  loading: boolean
  error: string | null
  state: PublicStatusState | null
  refresh: () => Promise<void>
}

export function usePublicStatus(token?: string): PublicStatusHook {
  const { t } = useI18n()
  const [state, setState] = useState<PublicStatusState | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    if (!token) return
    setLoading(true)
    setError(null)
    try {
      const data = await getPublicStatus(token)
      setState(data)
    } catch (err: any) {
      setError(err?.response?.data?.detail || err?.message || t('public.status_page.errors.load'))
    } finally {
      setLoading(false)
    }
  }, [token, t])

  useEffect(() => {
    refresh()
  }, [refresh])

  return {
    loading,
    error,
    state,
    refresh,
  }
}
