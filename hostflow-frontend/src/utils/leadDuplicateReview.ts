import type { Lead } from '../api/types'

function asRecord(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return null
  return value as Record<string, unknown>
}

/** Lead is in duplicate-review *context* (queue, badge, panel visibility). */
export function leadInDuplicateReviewContext(lead: Pick<Lead, 'status' | 'error' | 'normalized'> | null): boolean {
  if (!lead) return false
  if (lead.status === 'duplicate_review' || lead.status === 'duplicated') return true
  const err = String(lead.error || '').trim()
  if (err.startsWith('DUPLICATE_REVIEW_')) return true
  const n = asRecord(lead.normalized)
  const raw = n?.duplicate_match_v1
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
  return asRecord(normalized?.duplicate_match_v1)
}

export type DuplicatePriorSummary = {
  candidate_created: boolean
  candidate_id: string
  display_name?: string
  stage?: string
  status?: string
  reason?: string
  intake_status?: string
  intake_reason?: string
  source_lead_id?: string
  previous_duplicate_intakes?: number
  outcome?: string
}

function parsePrior(raw: unknown): DuplicatePriorSummary | null {
  const o = asRecord(raw)
  if (!o) return null
  const candidateId = String(o.candidate_id || '').trim()
  if (!candidateId) return null
  const created = o.candidate_created
  return {
    candidate_created: created === false ? false : true,
    candidate_id: candidateId,
    display_name: o.display_name != null ? String(o.display_name).trim() || undefined : undefined,
    stage: o.stage != null ? String(o.stage).trim() || undefined : undefined,
    status: o.status != null ? String(o.status).trim() || undefined : undefined,
    reason: o.reason != null ? String(o.reason).trim() || undefined : undefined,
    intake_status: o.intake_status != null ? String(o.intake_status).trim() || undefined : undefined,
    intake_reason: o.intake_reason != null ? String(o.intake_reason).trim() || undefined : undefined,
    source_lead_id: o.source_lead_id != null ? String(o.source_lead_id).trim() || undefined : undefined,
    previous_duplicate_intakes:
      typeof o.previous_duplicate_intakes === 'number' ? o.previous_duplicate_intakes : undefined,
    outcome: o.outcome != null ? String(o.outcome).trim() || undefined : undefined,
  }
}

/** Durable prior snapshot, then match.prior. */
export function readDuplicatePrior(
  normalized: Record<string, unknown> | null | undefined,
): DuplicatePriorSummary | null {
  const n = asRecord(normalized)
  if (!n) return null
  return parsePrior(n.duplicate_prior_v1) || parsePrior(asRecord(n.duplicate_match_v1)?.prior)
}

export function leadShowsDuplicateMark(lead: Pick<Lead, 'status' | 'error' | 'normalized'> | null): boolean {
  return leadInDuplicateReviewContext(lead)
}
