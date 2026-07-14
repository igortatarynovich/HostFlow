import { useCallback, useEffect, useState } from 'react'

import {
  getSetupReadiness,
  type SetupReadinessSnapshot,
} from '../api/onboarding'

export type UseSetupReadinessOptions = {
  enabled?: boolean
}

export function useSetupReadiness(options: UseSetupReadinessOptions = {}) {
  const { enabled = true } = options
  const [snapshot, setSnapshot] = useState<SetupReadinessSnapshot | null>(null)
  const [loading, setLoading] = useState(enabled)
  const [error, setError] = useState<unknown>(null)

  const refresh = useCallback(async () => {
    if (!enabled) {
      setSnapshot(null)
      setLoading(false)
      setError(null)
      return null
    }
    setLoading(true)
    setError(null)
    try {
      const data = await getSetupReadiness()
      setSnapshot(data)
      return data
    } catch (err) {
      setError(err)
      setSnapshot(null)
      return null
    } finally {
      setLoading(false)
    }
  }, [enabled])

  useEffect(() => {
    void refresh()
  }, [refresh])

  return {
    snapshot,
    loading,
    error,
    refresh,
    ready: Boolean(snapshot?.ready),
  }
}
