import { getBillingQuotaHeadroom, type BillingQuotaHeadroom } from './billing'

const TTL_MS = 2 * 60 * 1000

let cache: { headroom: BillingQuotaHeadroom; at: number } | null = null
let inflight: Promise<BillingQuotaHeadroom> | null = null

export function invalidateBillingQuotaHeadroomCache(): void {
  cache = null
}

export function primeBillingQuotaHeadroomCache(headroom: BillingQuotaHeadroom): void {
  cache = { headroom, at: Date.now() }
}

export async function getBillingQuotaHeadroomCached(): Promise<BillingQuotaHeadroom> {
  const now = Date.now()
  if (cache && now - cache.at < TTL_MS) {
    return cache.headroom
  }
  if (!inflight) {
    inflight = getBillingQuotaHeadroom()
      .then((headroom) => {
        cache = { headroom, at: Date.now() }
        return headroom
      })
      .finally(() => {
        inflight = null
      })
  }
  return inflight
}
