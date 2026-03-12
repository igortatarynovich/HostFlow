import { useEffect, useState } from 'react'
import { getPendingWithCandidates } from '../api/handoffs'
import { useAuth } from '../store/useAuth'
import { usePermissions } from './usePermissions'

/**
 * Returns the count of pending handoffs for the current user's tenant (client mode).
 * Used to show badge on "Procesowani" and in notifications.
 */
export function usePendingHandoffsCount(): number {
  const { me } = useAuth()
  const { can } = usePermissions()
  const [count, setCount] = useState(0)

  useEffect(() => {
    if (!can('companies.view') || !me?.tenant_id) {
      setCount(0)
      return
    }

    let cancelled = false
    let timeout: number

    const fetchCount = async () => {
      try {
        const items = await getPendingWithCandidates(undefined, me.tenant_id)
        if (!cancelled) {
          setCount(Array.isArray(items) ? items.length : 0)
        }
      } catch {
        if (!cancelled) setCount(0)
      } finally {
        if (!cancelled) {
          timeout = window.setTimeout(fetchCount, 60_000)
        }
      }
    }

    void fetchCount()

    return () => {
      cancelled = true
      window.clearTimeout(timeout)
    }
  }, [can, me?.tenant_id])

  return count
}
