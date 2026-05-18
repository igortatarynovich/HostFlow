import type { Lead } from '../api/types'
import { leadSupportsManualProcess } from './leadCrm'

/** Same set as backend ``_ALLOWED_LEAD_STATUSES`` in ``intake_decision.py`` (POST /leads/.../intake-decision). */
export const LEAD_INTAKE_DECISION_ALLOWED_STATUSES = new Set(['new', 'needs_routing', 'failed', 'duplicate_review'])

export function leadStatusAllowsIntakeDecision(lead: Pick<Lead, 'status'> | null): boolean {
  if (!lead) return false
  return LEAD_INTAKE_DECISION_ALLOWED_STATUSES.has(String(lead.status || '').trim().toLowerCase())
}

/** Canonical reject codes — must match backend ``INTAKE_REJECT_REASON_CODES``. */
export const INTAKE_REJECT_REASON_CODES = [
  'insufficient_experience',
  'missing_documents',
  'unsupported_citizenship',
  'language_mismatch',
  'invalid_contact',
  'no_response',
  'salary_mismatch',
  'unsuitable_route',
  'duplicate_spam',
  'not_interested',
  'other',
] as const

export type IntakeRejectReasonCode = (typeof INTAKE_REJECT_REASON_CODES)[number]

export type ManualProcessBlockCode =
  | 'INTAKE_REJECTED'
  | 'DUPLICATE_REVIEW_PENDING'
  | 'INTAKE_POOL_PATH_REQUIRED'
  | 'VACANCY_NOT_CONFIRMED'
  | 'INTAKE_ROUTING_INCOMPLETE'
  | 'INTAKE_INFO_REQUESTED'
  | 'INTAKE_IDENTITY_UNCLEAR'
  | 'LEAD_RODO_REQUIRED'

function normalizedRecord(lead: Lead | null): Record<string, unknown> {
  const n = lead?.normalized
  return n && typeof n === 'object' && !Array.isArray(n) ? (n as Record<string, unknown>) : {}
}

/** Mirrors backend ``lead_rodo_satisfied`` — art.14 closed at lead (sent / satisfied / source_provided / legacy sent_at). */
export type LeadRodoNoticeStatus =
  | 'sent'
  | 'failed'
  | 'pending_channel'
  | 'manual_required'
  | 'source_provided'

/** Mirrors backend ``lead_rodo_notice_status_from_normalized`` for lead rail UI. */
export function leadRodoNoticeStatus(
  lead: Pick<Lead, 'normalized' | 'candidate_id'> | null,
): LeadRodoNoticeStatus | null {
  if (!lead || lead.candidate_id) return null
  const n = normalizedRecord(lead as Lead)
  const raw = n.rodo
  const block = raw && typeof raw === 'object' && !Array.isArray(raw) ? (raw as Record<string, unknown>) : {}
  const st = String(block.status || '')
    .trim()
    .toLowerCase()
  if (st === 'source_provided') return 'source_provided'
  if (st === 'sent' || st === 'satisfied' || Boolean(String(block.sent_at || '').trim())) return 'sent'
  if (st === 'failed') return 'failed'
  if (st === 'pending_channel') return 'pending_channel'
  return 'manual_required'
}

export function leadRodoSatisfied(lead: Pick<Lead, 'normalized' | 'candidate_id'> | null): boolean {
  if (!lead || lead.candidate_id) return true
  const n = normalizedRecord(lead as Lead)
  const raw = n.rodo
  const block = raw && typeof raw === 'object' && !Array.isArray(raw) ? (raw as Record<string, unknown>) : {}
  const st = String(block.status || '')
    .trim()
    .toLowerCase()
  if (st === 'sent' || st === 'satisfied' || st === 'source_provided') return true
  return Boolean(String(block.sent_at || '').trim())
}

function intakeResolutionStatus(lead: Lead | null): string {
  const n = normalizedRecord(lead)
  const ir = n.intake_resolution_v1
  if (!ir || typeof ir !== 'object' || Array.isArray(ir)) return ''
  return String((ir as { status?: string }).status || '')
    .trim()
    .toLowerCase()
}

/**
 * Client-side hint mirroring ``manual_process_block_code`` so the Process control
 * can be disabled with an explanatory tooltip before the server returns 422.
 */
export function manualProcessBlockHint(lead: Lead | null): ManualProcessBlockCode | null {
  if (!lead || lead.candidate_id) return null
  if (!leadSupportsManualProcess(lead)) return null

  const n = normalizedRecord(lead)
  const irSt = intakeResolutionStatus(lead)
  if (irSt === 'rejected') return 'INTAKE_REJECTED'
  if (irSt === 'info_requested') return 'INTAKE_INFO_REQUESTED'

  const idv = n.intake_identity_v1
  if (idv && typeof idv === 'object' && !Array.isArray(idv)) {
    const st = String((idv as { status?: string }).status || '')
      .trim()
      .toLowerCase()
    if (st === 'unclear') return 'INTAKE_IDENTITY_UNCLEAR'
  }

  const st = String(lead.status || '')
    .trim()
    .toLowerCase()
  if (st === 'duplicate_review') return 'DUPLICATE_REVIEW_PENDING'

  const hasVac = Boolean(lead.vacancy_id)
  const poolIntent = Boolean(lead.funnel_id) || n.recruitment_pool_intent_v1 === true
  if (poolIntent && !hasVac) {
    if (!['pooled', 'qualified'].includes(irSt)) return 'INTAKE_POOL_PATH_REQUIRED'
    if (!leadRodoSatisfied(lead)) return 'LEAD_RODO_REQUIRED'
    return null
  }

  if (hasVac && !lead.vacancy_routing_confirmed) return 'VACANCY_NOT_CONFIRMED'
  if (hasVac && lead.vacancy_routing_confirmed && !leadRodoSatisfied(lead)) return 'LEAD_RODO_REQUIRED'
  if (!hasVac && !poolIntent) return 'INTAKE_ROUTING_INCOMPLETE'

  return null
}

export function parseProcessBlockedCodeFromAxios(err: unknown): ManualProcessBlockCode | null {
  const raw = (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail
  if (raw && typeof raw === 'object' && !Array.isArray(raw) && 'code' in raw) {
    const c = String((raw as { code?: string }).code || '').trim()
    if (c) return c as ManualProcessBlockCode
  }
  return null
}

export function manualProcessBlockedUserMessage(
  t: (key: string) => string,
  code: ManualProcessBlockCode,
): string {
  const k = `app.leads.messages.process_blocked.${code}`
  const v = t(k)
  return v === k ? code : v
}

/** Recruitment inbox: hide CRM-noise rail until routing / duplicate / intake guards clear. */
export function leadIntakeWorkspaceBlocking(lead: Lead | null, isServicesTenant: boolean): boolean {
  if (!lead || isServicesTenant || lead.candidate_id) return false
  if (!leadSupportsManualProcess(lead)) return false
  const hint = manualProcessBlockHint(lead)
  if (hint && hint !== 'LEAD_RODO_REQUIRED') return true
  const st = String(lead.status || '')
    .trim()
    .toLowerCase()
  return st === 'needs_routing'
}

export type LeadRoutingTableAction =
  | { kind: 'none' }
  | { kind: 'confirm_suggested'; vacancyId: string }
  | { kind: 'confirm_current'; vacancyId: string }
  | { kind: 'pick_vacancy' }

/**
 * Primary row action for recruitment leads stuck on routing (table + one-click confirm).
 * Duplicate-review / pool / identity blocks stay on the full intake panel.
 */
export function leadRoutingTableAction(lead: Lead | null, isServicesTenant: boolean): LeadRoutingTableAction {
  if (!lead || isServicesTenant || lead.candidate_id || !leadSupportsManualProcess(lead)) {
    return { kind: 'none' }
  }
  const st = String(lead.status || '')
    .trim()
    .toLowerCase()
  if (st === 'duplicate_review') return { kind: 'none' }

  const hint = manualProcessBlockHint(lead)
  if (
    hint === 'INTAKE_REJECTED' ||
    hint === 'INTAKE_INFO_REQUESTED' ||
    hint === 'INTAKE_IDENTITY_UNCLEAR' ||
    hint === 'INTAKE_POOL_PATH_REQUIRED'
  ) {
    return { kind: 'none' }
  }

  const suggested = lead.suggested_vacancy_id != null ? String(lead.suggested_vacancy_id).trim() : ''
  const vacId = lead.vacancy_id != null ? String(lead.vacancy_id).trim() : ''
  const hasVac = Boolean(vacId)
  const confirmed = Boolean(lead.vacancy_routing_confirmed)
  if (confirmed) return { kind: 'none' }

  if (suggested) {
    return { kind: 'confirm_suggested', vacancyId: suggested }
  }
  if (hint === 'VACANCY_NOT_CONFIRMED' && vacId) {
    return { kind: 'confirm_current', vacancyId: vacId }
  }
  if (hint === 'INTAKE_ROUTING_INCOMPLETE' || (st === 'needs_routing' && !hasVac)) {
    return { kind: 'pick_vacancy' }
  }
  return { kind: 'none' }
}
