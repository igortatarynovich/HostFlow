import type { Lead } from '../api/types'

export const INTAKE_LIFECYCLE_VALUES = [
  'new',
  'in_progress',
  'converted',
  'rejected',
  'pool',
  'duplicate_review',
] as const

export type IntakeLifecycle = (typeof INTAKE_LIFECYCLE_VALUES)[number]

export const INTAKE_QUEUE_FILTERS = [
  'new',
  'in_progress',
  'needs_decision',
  'pool',
  'completed',
] as const

export type IntakeQueueFilter = (typeof INTAKE_QUEUE_FILTERS)[number]

const LEGACY_LANE_ALIASES: Record<string, IntakeQueueFilter> = {
  to_call: 'new',
  called: 'in_progress',
  rejected: 'completed',
  duplicate: 'needs_decision',
  converted: 'completed',
  pool: 'pool',
}

function asRecord(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return null
  return value as Record<string, unknown>
}

function irStatus(lead: Lead | null | undefined): string {
  const n = asRecord(lead?.normalized)
  const ir = asRecord(n?.intake_resolution_v1)
  return String(ir?.status || '')
    .trim()
    .toLowerCase()
}

function hasCallResult(lead: Lead | null | undefined): boolean {
  const n = asRecord(lead?.normalized)
  const call = asRecord(n?.call_result_v1)
  return Boolean(String(call?.result || '').trim())
}

/** Prefer API projection; derive the same funnel when the field is absent. */
export function leadIntakeLifecycle(lead: Lead | null | undefined): IntakeLifecycle {
  const fromApi = String(lead?.intake_lifecycle || '')
    .trim()
    .toLowerCase()
  if ((INTAKE_LIFECYCLE_VALUES as readonly string[]).includes(fromApi)) {
    return fromApi as IntakeLifecycle
  }
  if (!lead) return 'new'
  if (lead.candidate_id) return 'converted'
  const st = String(lead.status || '')
    .trim()
    .toLowerCase()
  const stage = String(lead.stage || '')
    .trim()
    .toLowerCase()
  const ir = irStatus(lead)
  const n = asRecord(lead.normalized)
  if (ir === 'rejected' || st === 'rejected') return 'rejected'
  if (ir === 'pooled' || ir === 'pool' || n?.recruitment_pool_intent_v1 === true) return 'pool'
  if (st === 'duplicate_review' || ir === 'duplicate_review' || ir === 'duplicate_review_requested') {
    return 'duplicate_review'
  }
  if (ir === 'converted' || stage === 'converted') return 'converted'
  if (ir === 'in_progress' || ir === 'qualified' || ir === 'info_requested') return 'in_progress'
  if (hasCallResult(lead)) return 'in_progress'
  if (stage === 'contacted' || stage === 'qualified') return 'in_progress'
  return 'new'
}

export function parseIntakeQueueFilter(raw: string | null | undefined): IntakeQueueFilter | '' {
  const key = String(raw || '')
    .trim()
    .toLowerCase()
  if ((INTAKE_QUEUE_FILTERS as readonly string[]).includes(key)) return key as IntakeQueueFilter
  return LEGACY_LANE_ALIASES[key] || ''
}

export function intakeLifecycleLabelKey(lifecycle: IntakeLifecycle): string {
  return `app.leads.intake_workspace.lifecycle.${lifecycle}`
}
