import type { Lead } from '../api/types'
import type { LeadCallResultCode } from '../api/client'

export type LeadCallResultEntry = {
  result: LeadCallResultCode | string
  note?: string | null
  at?: string | null
  by?: string | null
  next_contact_at?: string | null
}

export const LEAD_CALL_REACHED_CODES: LeadCallResultCode[] = [
  'interested',
  'not_interested',
  'callback_requested',
]

export const LEAD_CALL_NO_ANSWER_CODES: LeadCallResultCode[] = [
  'no_answer',
  'unavailable',
  'wrong_number',
]

export const LEAD_CALL_RESULT_CODES: LeadCallResultCode[] = [
  ...LEAD_CALL_REACHED_CODES,
  'answered',
  ...LEAD_CALL_NO_ANSWER_CODES,
]

function asRecord(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return null
  return value as Record<string, unknown>
}

export function parseLeadCallResultEntry(value: unknown): LeadCallResultEntry | null {
  const o = asRecord(value)
  if (!o) return null
  const result = String(o.result || '').trim()
  if (!result) return null
  return {
    result,
    note: o.note != null ? String(o.note) : null,
    at: o.at != null ? String(o.at) : null,
    by: o.by != null ? String(o.by) : null,
    next_contact_at: o.next_contact_at != null ? String(o.next_contact_at) : null,
  }
}

/** Latest call result (`normalized.call_result_v1`). */
export function leadLatestCallResult(lead: Lead | null | undefined): LeadCallResultEntry | null {
  const n = asRecord(lead?.normalized)
  if (!n) return null
  return parseLeadCallResultEntry(n.call_result_v1)
}

/** Call history newest-first (`normalized.call_results_v1`). */
export function leadCallResultHistory(lead: Lead | null | undefined): LeadCallResultEntry[] {
  const n = asRecord(lead?.normalized)
  if (!n) return []
  const raw = n.call_results_v1
  if (!Array.isArray(raw)) {
    const latest = parseLeadCallResultEntry(n.call_result_v1)
    return latest ? [latest] : []
  }
  const items = raw.map(parseLeadCallResultEntry).filter((x): x is LeadCallResultEntry => Boolean(x))
  return items.slice().reverse()
}
