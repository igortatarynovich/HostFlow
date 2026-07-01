import { useCallback, useEffect, useState } from 'react'
import type { BillingQuotaHeadroom } from '../api/billing'
import { getBillingQuotaHeadroomCached } from '../api/billingQuotaHeadroomCache'
import { BILLING_SUBSCRIPTION_UPDATED_EVENT } from '../api/billingSubscriptionCache'

export type QuotaWarningKind = 'leads_monthly' | 'candidates_active' | 'storage'

export type QuotaWarningState = {
  kind: QuotaWarningKind
  /** 0–100, rounded */
  percentUsed: number
  used: number
  cap: number
}

function ratioUsed(used: number, cap: number): number | null {
  if (!Number.isFinite(used) || !Number.isFinite(cap) || cap <= 0) return null
  return used / cap
}

function buildWarnings(h: BillingQuotaHeadroom | null): QuotaWarningState[] {
  if (!h) return []
  const out: QuotaWarningState[] = []

  const leadsR = ratioUsed(h.leads_created_this_month, h.max_leads_created_per_month)
  if (leadsR != null && leadsR > 0.8) {
    out.push({
      kind: 'leads_monthly',
      percentUsed: Math.min(100, Math.round(leadsR * 100)),
      used: h.leads_created_this_month,
      cap: h.max_leads_created_per_month,
    })
  }

  const candR = ratioUsed(h.candidates_active_count, h.max_candidates_active)
  if (candR != null && candR > 0.8) {
    out.push({
      kind: 'candidates_active',
      percentUsed: Math.min(100, Math.round(candR * 100)),
      used: h.candidates_active_count,
      cap: h.max_candidates_active,
    })
  }

  const storageR = ratioUsed(h.storage_used_gb, h.max_storage_gb)
  if (storageR != null && storageR > 0.8) {
    out.push({
      kind: 'storage',
      percentUsed: Math.min(100, Math.round(storageR * 100)),
      used: h.storage_used_gb,
      cap: h.max_storage_gb,
    })
  }

  return out
}

/**
 * Loads quota headroom (cached) and exposes rows above 80% (soft warning band).
 */
export function useBillingQuotaWarnings() {
  const [warnings, setWarnings] = useState<QuotaWarningState[]>([])
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const headroom = await getBillingQuotaHeadroomCached()
      setWarnings(buildWarnings(headroom))
    } catch {
      setWarnings([])
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  useEffect(() => {
    if (typeof window === 'undefined') return
    const onBilling = () => void load()
    window.addEventListener(BILLING_SUBSCRIPTION_UPDATED_EVENT, onBilling)
    return () => window.removeEventListener(BILLING_SUBSCRIPTION_UPDATED_EVENT, onBilling)
  }, [load])

  const warningFor = useCallback(
    (kind: QuotaWarningKind) => warnings.find((w) => w.kind === kind) ?? null,
    [warnings],
  )

  return { loading, warnings, warningFor, reload: load }
}
