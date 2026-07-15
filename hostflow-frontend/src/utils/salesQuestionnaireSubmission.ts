import type { Lead } from '../api/types'
import { readSalesQuestionnaireSummary } from './salesQuestionnaire'

export type LeadSubmissionV1 = {
  form_id?: string | null
  presentation_code?: string | null
  target_entity_profile_code?: string | null
  normalized_values?: Record<string, unknown> | null
  submitted_at?: string | null
  submission_id?: string | null
}

const DEFAULT_ENTITY_PROFILE_CODE = 'service_sales.targeted_advertising'
const DEFAULT_PLATFORM_PRESENTATION_CODE = 'service_sales.targeted_advertising.public_pl'

function record(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' && !Array.isArray(value) ? (value as Record<string, unknown>) : {}
}

export function readLeadSubmissions(lead: { normalized?: Record<string, unknown> | null }): LeadSubmissionV1[] {
  const rows = lead.normalized?.submissions_v1
  if (!Array.isArray(rows)) return []
  return rows.filter((row) => row && typeof row === 'object') as LeadSubmissionV1[]
}

/** Latest append-only submission snapshot — never merge across submissions. */
export function readLatestSubmission(lead: { normalized?: Record<string, unknown> | null }): LeadSubmissionV1 | null {
  const rows = readLeadSubmissions(lead)
  return rows.length > 0 ? rows[rows.length - 1] : null
}

export function resolveSubmissionEntityProfileCode(
  submission: LeadSubmissionV1 | null,
  lead: { normalized?: Record<string, unknown> | null },
): string {
  const fromSubmission = String(submission?.target_entity_profile_code || '').trim()
  if (fromSubmission) return fromSubmission
  const fromLead = String(lead.normalized?.entity_profile_code || '').trim()
  if (fromLead) return fromLead
  return DEFAULT_ENTITY_PROFILE_CODE
}

export function resolveSubmissionPresentationCode(submission: LeadSubmissionV1 | null): string | null {
  const code = String(submission?.presentation_code || '').trim()
  return code || null
}

export function defaultPlatformPresentationCode(): string {
  return DEFAULT_PLATFORM_PRESENTATION_CODE
}

function isEmptySubmissionValue(value: unknown): boolean {
  if (value == null) return true
  if (typeof value === 'string') return value.trim() === ''
  if (Array.isArray(value)) return value.every((item) => isEmptySubmissionValue(item))
  if (typeof value === 'boolean') return false
  return false
}

/** Map flat sales_questionnaire keys to qualified codes for legacy fallback. */
export function salesQuestionnaireToQualifiedValues(
  lead: { normalized?: Record<string, unknown> | null },
  entityProfileCode: string,
): Record<string, unknown> {
  const prefix = String(entityProfileCode || '').trim()
  const block = readSalesQuestionnaireSummary(lead)
  const out: Record<string, unknown> = {}
  for (const [key, raw] of Object.entries(block)) {
    if (key.endsWith('_label')) continue
    if (isEmptySubmissionValue(raw)) continue
    const qualified = key.includes('.') ? key : `${prefix}.${key}`
    out[qualified] = raw
  }
  return out
}

/**
 * Answer source for display: latest submission snapshot only, else flat sales_questionnaire fallback.
 */
export function readSubmissionAnswerValues(
  lead: Lead,
  submission: LeadSubmissionV1 | null,
  entityProfileCode: string,
): Record<string, unknown> {
  const normalized = record(submission?.normalized_values)
  if (Object.keys(normalized).length > 0) {
    const out: Record<string, unknown> = {}
    for (const [key, value] of Object.entries(normalized)) {
      if (isEmptySubmissionValue(value)) continue
      out[key] = value
    }
    return out
  }
  return salesQuestionnaireToQualifiedValues(lead, entityProfileCode)
}

export function submissionHasDisplayableAnswers(lead: Lead): boolean {
  const submission = readLatestSubmission(lead)
  const profileCode = resolveSubmissionEntityProfileCode(submission, lead)
  return Object.keys(readSubmissionAnswerValues(lead, submission, profileCode)).length > 0
}
