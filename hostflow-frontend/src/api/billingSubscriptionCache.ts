import { getBillingSubscription, type BillingSubscription } from './billing'

const TTL_MS = 2 * 60 * 1000

let cache: { sub: BillingSubscription; at: number } | null = null
let inflight: Promise<BillingSubscription> | null = null

export const BILLING_SUBSCRIPTION_UPDATED_EVENT = 'hf:billing-subscription-updated'

/** Drop cache (e.g. logout); components should refetch on next read. */
export function invalidateBillingSubscriptionCache(): void {
  cache = null
}

/** After Settings → Billing loads full summary, sync cache so Work hub / dashboard see the new plan without waiting for TTL. */
export function primeBillingSubscriptionCache(sub: BillingSubscription): void {
  cache = { sub, at: Date.now() }
}

export function dispatchBillingSubscriptionUpdated(): void {
  if (typeof window === 'undefined') return
  window.dispatchEvent(new Event(BILLING_SUBSCRIPTION_UPDATED_EVENT))
}

/**
 * Deduplicates parallel calls and reuses fresh data for TTL (§2.14 paywall surfaces).
 */
export async function getBillingSubscriptionCached(): Promise<BillingSubscription> {
  const now = Date.now()
  if (cache && now - cache.at < TTL_MS) {
    return cache.sub
  }
  if (!inflight) {
    inflight = getBillingSubscription()
      .then((sub) => {
        cache = { sub, at: Date.now() }
        return sub
      })
      .finally(() => {
        inflight = null
      })
  }
  return inflight
}
