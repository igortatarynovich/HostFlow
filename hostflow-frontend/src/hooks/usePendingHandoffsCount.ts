import { useEffect, useRef, useState } from 'react'
import { getPendingWithCandidates } from '../api/handoffs'
import { useAuth } from '../store/useAuth'
import { isHttpUnauthorized, isTransientRequestError } from '../utils/errorHandling'
import { nextPollDelayMs } from '../utils/pollBackoff'
import { usePermissions } from './usePermissions'

/**
 * Pending inbound handoffs for a *client* workspace (bell badge).
 * Agency recruiters must not poll this — it is a client-inbox query and 502s spam the console.
 * Call once from AppShell and pass the count down — do not mount this hook twice.
 */
export function usePendingHandoffsCount(): number {
  const { me } = useAuth()
  const { can, isClientTenant } = usePermissions()
  const [count, setCount] = useState(0)
  const canViewInbox = can('companies.view') && isClientTenant
  const inFlightRef = useRef(false)

  useEffect(() => {
    if (!canViewInbox || !me?.tenant_id) {
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
        if (isHttpUnauthorized(err)) {
          cancelled = true
          return
        }
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
  }, [canViewInbox, me?.tenant_id])

  return count
}
