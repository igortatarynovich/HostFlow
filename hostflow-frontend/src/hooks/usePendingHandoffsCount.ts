import { useEffect, useRef, useState } from 'react'
import { getPendingWithCandidates } from '../api/handoffs'
import { useAuth } from '../store/useAuth'
import { isTransientRequestError } from '../utils/errorHandling'
import { nextPollDelayMs } from '../utils/pollBackoff'
import { usePermissions } from './usePermissions'

/**
 * Returns the count of pending handoffs for the current user's tenant (client mode).
 * Used to show badge on "Procesowani" and in notifications.
 * Call once from AppShell and pass the count down — do not mount this hook twice.
 */
export function usePendingHandoffsCount(): number {
  const { me } = useAuth()
  const { can } = usePermissions()
  const [count, setCount] = useState(0)
  const canViewCompanies = can('companies.view')
  const inFlightRef = useRef(false)

  useEffect(() => {
    if (!canViewCompanies || !me?.tenant_id) {
      setCount(0)
      return
    }

    let cancelled = false
    let timeout: number
    let consecutiveFailures = 0

    const fetchCount = async () => {
      if (cancelled || inFlightRef.current) return
      inFlightRef.current = true
      try {
        const items = await getPendingWithCandidates(undefined, me.tenant_id)
        if (cancelled) return
        consecutiveFailures = 0
        setCount(Array.isArray(items) ? items.length : 0)
      } catch (err) {
        if (cancelled) return
        consecutiveFailures += 1
        if (!isTransientRequestError(err)) {
          console.warn('[Handoffs] pending count failed', err)
        }
      } finally {
        inFlightRef.current = false
        if (!cancelled) {
          timeout = window.setTimeout(fetchCount, nextPollDelayMs(consecutiveFailures))
        }
      }
    }

    void fetchCount()

    return () => {
      cancelled = true
      window.clearTimeout(timeout)
    }
  }, [canViewCompanies, me?.tenant_id])

  return count
}
