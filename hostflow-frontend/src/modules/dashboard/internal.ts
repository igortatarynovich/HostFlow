/**
 * Page-local helpers and types for `pages/Dashboard.tsx` that don't fit into
 * the public type/utils/stageNormalize buckets but are still pure (no React).
 */
import type { Invoice } from '../../api/types'

export type TrialRetentionDay = 1 | 2 | 3 | 7

export type DigestBulkResultReport = {
  kind: 'remind' | 'claim'
  ok: number
  fail: number
  errors: string[]
}

export type InvoiceWithPaid = Invoice & { paid_amount?: number | null }

export function formatDigestBulkError(reason: unknown): string {
  const r = reason as { response?: { data?: { detail?: unknown } }; message?: string }
  const d = r?.response?.data
  const detail = d?.detail
  if (typeof detail === 'string') return detail.slice(0, 220)
  if (Array.isArray(detail)) {
    const msg = detail
      .map((x: { msg?: string; message?: string }) => x?.msg || x?.message || String(x))
      .join('; ')
    return msg.slice(0, 220)
  }
  return String(r?.message || reason || 'Error').slice(0, 220)
}
