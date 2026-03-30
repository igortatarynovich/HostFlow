import { useCallback, useEffect, useMemo, useState } from 'react'

import {
  BILLING_SUBSCRIPTION_UPDATED_EVENT,
  getBillingSubscriptionCached,
} from '../api/billingSubscriptionCache'

/** Mirrors backend `plan_allows_team_tier_features` / NBA paywall (solo, trial, starter, …). */
const TEAM_TIER_BLOCKED_PLANS = new Set(['starter', 'trial', 'free', 'solo'])

export type TeamTierFeaturesState = {
  planCode: string | null
  planLoading: boolean
  /** Team, Pro, Business, etc. — bulk Meta auto-fix, funnel NBA insights, etc. */
  allowsTeamFeatures: boolean
}

/**
 * Plan tier for §2.14 paywall surfaces (Work hub, pipeline, dashboard auto-fix).
 * Reads **`getBillingSubscriptionCached`**; refetches on **`hf:billing-subscription-updated`** (Billing page / tenant change).
 */
export function useTeamTierFeatures(): TeamTierFeaturesState {
  const [planCode, setPlanCode] = useState<string | null>(null)
  const [planLoading, setPlanLoading] = useState(true)

  const load = useCallback(() => {
    let cancelled = false
    setPlanLoading(true)
    void (async () => {
      try {
        const sub = await getBillingSubscriptionCached()
        if (!cancelled) {
          setPlanCode(String(sub?.plan_code || 'starter').toLowerCase())
        }
      } catch {
        if (!cancelled) setPlanCode('starter')
      } finally {
        if (!cancelled) setPlanLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    const cancel = load()
    return () => {
      cancel()
    }
  }, [load])

  useEffect(() => {
    let cancelled = false
    const onUpdate = () => {
      void (async () => {
        setPlanLoading(true)
        try {
          const sub = await getBillingSubscriptionCached()
          if (!cancelled) {
            setPlanCode(String(sub?.plan_code || 'starter').toLowerCase())
          }
        } catch {
          if (!cancelled) setPlanCode('starter')
        } finally {
          if (!cancelled) setPlanLoading(false)
        }
      })()
    }
    window.addEventListener(BILLING_SUBSCRIPTION_UPDATED_EVENT, onUpdate)
    return () => {
      cancelled = true
      window.removeEventListener(BILLING_SUBSCRIPTION_UPDATED_EVENT, onUpdate)
    }
  }, [])

  const allowsTeamFeatures = useMemo(() => {
    const p = (planCode || 'starter').trim().toLowerCase()
    return !TEAM_TIER_BLOCKED_PLANS.has(p)
  }, [planCode])

  return { planCode, planLoading, allowsTeamFeatures }
}
