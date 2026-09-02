import type { Application } from '../../api/types/application'

export const APPLICATION_CALL_REACHED_CODES = [
  'interested',
  'not_interested',
  'callback_requested',
] as const

export const APPLICATION_CALL_NO_ANSWER_CODES = ['no_answer', 'unavailable', 'wrong_number'] as const

export type ApplicationCallResultCode =
  | (typeof APPLICATION_CALL_REACHED_CODES)[number]
  | 'answered'
  | (typeof APPLICATION_CALL_NO_ANSWER_CODES)[number]

export type ApplicationCallResultEntry = {
  result: string
  note?: string | null
  at?: string | null
  by?: string | null
  next_contact_at?: string | null
}

function asRecord(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return null
  return value as Record<string, unknown>
}

export function parseApplicationCallResultEntry(value: unknown): ApplicationCallResultEntry | null {
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

export function applicationLatestCallResult(application: Application): ApplicationCallResultEntry | null {
  return parseApplicationCallResultEntry(application.extensions?.call_result_v1)
}

export function applicationCallResultHistory(application: Application): ApplicationCallResultEntry[] {
  const raw = application.extensions?.call_results_v1
  if (!Array.isArray(raw)) {
    const latest = applicationLatestCallResult(application)
    return latest ? [latest] : []
  }
  const items = raw.map(parseApplicationCallResultEntry).filter((row): row is ApplicationCallResultEntry => Boolean(row))
  return items.slice().reverse()
}
