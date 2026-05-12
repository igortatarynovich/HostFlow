import type { Lead } from '../api/types'

/** Lead is in duplicate-review *context* (queue, badge, panel visibility). */
export function leadInDuplicateReviewContext(lead: Pick<Lead, 'status' | 'error' | 'normalized'> | null): boolean {
  if (!lead) return false
  if (lead.status === 'duplicate_review') return true
  const err = String(lead.error || '').trim()
  if (err.startsWith('DUPLICATE_REVIEW_')) return true
  const raw = lead.normalized?.duplicate_match_v1
  if (raw && typeof raw === 'object' && !Array.isArray(raw) && Object.keys(raw as object).length > 0) {
    return true
  }
  return false
}

/** Operator may call POST /duplicate-decision (API requires this status). */
export function leadDuplicateDecisionActionsOpen(lead: Pick<Lead, 'status'> | null): boolean {
  return lead?.status === 'duplicate_review'
}

export function readDuplicateMatchV1(
  normalized: Record<string, unknown> | null | undefined,
): Record<string, unknown> | null {
  const raw = normalized?.duplicate_match_v1
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return null
  return raw as Record<string, unknown>
}
