import type { Lead } from '../api/types'
import { leadIntakeFormAnswerRows } from './leadIntakeFormAnswers'
import { leadLatestCallResult } from './leadCallResult'

type TFn = (key: string, opts?: { defaultValue?: string; values?: Record<string, string | number> }) => string

function asRecord(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return null
  return value as Record<string, unknown>
}

function blob(n: Record<string, unknown>): string {
  const parts: string[] = []
  for (const key of ['documents', 'driving_license_category', 'code_95', 'driver_card']) {
    const v = n[key]
    if (v == null) continue
    parts.push(String(v))
  }
  const answers = n.field_answers
  if (Array.isArray(answers)) {
    for (const row of answers) {
      if (!row || typeof row !== 'object') continue
      const name = String((row as Record<string, unknown>).name || '')
      const values = (row as Record<string, unknown>).values
      parts.push(name, Array.isArray(values) ? values.join(' ') : String(values || ''))
    }
  }
  return parts.join(' ').toLowerCase()
}

/** Compact flags for the intake queue row (visible before opening the lead). */
export function leadIntakeQueueFlags(lead: Lead, t: TFn): string[] {
  const n = asRecord(lead.normalized) || {}
  const flags: string[] = []
  const text = blob(n)
  const answers = leadIntakeFormAnswerRows(lead)
  const answerBlob = answers.map((r) => `${r.label} ${r.value}`).join(' ').toLowerCase()
  const hay = `${text} ${answerBlob}`

  if (/\bc\s*\+\s*e\b/.test(hay) || hay.includes('c+e') || hay.includes('ce+e')) {
    flags.push('C+E')
  }
  if (/\bcode\s*95\b/.test(hay) || hay.includes('code95') || hay.includes('kod 95') || hay.includes('kod_95')) {
    flags.push(t('app.leads.intake_workspace.queue.flag_code95', { defaultValue: 'Code95 ✓' }))
  }
  if (n.in_poland === true || /\bin poland\b/.test(hay) || hay.includes('польш')) {
    flags.push(t('app.leads.intake_workspace.queue.flag_pl', { defaultValue: 'PL ✓' }))
  }
  if (/\b8\s*mies|8\s*month|более 8|more than 8|pobyt/.test(hay)) {
    flags.push(t('app.leads.intake_workspace.queue.flag_stay', { defaultValue: 'pobyt >8 mies.' }))
  }
  return flags.slice(0, 4)
}

export function leadIntakeLastActivityAt(lead: Lead): string | null {
  const call = leadLatestCallResult(lead)
  if (call?.at) return call.at
  const n = asRecord(lead.normalized)
  const ir = asRecord(n?.intake_resolution_v1)
  const decided = String(ir?.decided_at || ir?.updated_at || '').trim()
  if (decided) return decided
  if (lead.next_action_due_at) return String(lead.next_action_due_at)
  return lead.created_at || null
}

export function leadIntakeLastActivityLabel(lead: Lead, t: TFn): string | null {
  const call = leadLatestCallResult(lead)
  if (call?.result) {
    return t(`app.leads.detail.call_result.results.${call.result}`, { defaultValue: String(call.result) })
  }
  return null
}
