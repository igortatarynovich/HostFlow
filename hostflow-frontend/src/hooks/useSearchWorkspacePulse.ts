import { useCallback, useEffect, useState } from 'react'
import { getSearchWorkspacePulse, type SearchWorkspacePulse } from '../api/searchWorkspace'

function isNotFoundError(err: unknown): boolean {
  return (err as { response?: { status?: number } })?.response?.status === 404
}

export function useSearchWorkspacePulse(searchId: string, options?: { enabled?: boolean }) {
  const enabled = options?.enabled !== false
  const [pulse, setPulse] = useState<SearchWorkspacePulse | null>(null)
  const [loading, setLoading] = useState(true)
  const [notFound, setNotFound] = useState(false)

  const refresh = useCallback(async () => {
    if (!searchId || !enabled || notFound) return
    setLoading(true)
    try {
      const data = await getSearchWorkspacePulse(searchId)
      setPulse(data)
      setNotFound(false)
    } catch (err) {
      setPulse(null)
      if (isNotFoundError(err)) setNotFound(true)
    } finally {
      setLoading(false)
    }
  }, [enabled, notFound, searchId])

  useEffect(() => {
    if (!enabled || notFound) {
      setLoading(false)
      return
    }
    void refresh()
    const timer = window.setInterval(() => void refresh(), 5 * 60 * 1000)
    return () => window.clearInterval(timer)
  }, [enabled, notFound, refresh])

  return { pulse, loading, refresh, notFound }
}
