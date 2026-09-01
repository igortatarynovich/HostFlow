import type { Lead } from '../api/types'

export type LeadIntakeFormAnswerRow = {
  name: string
  label: string
  value: string
}

const SKIP_NAMES = new Set([
  'id',
  'lead_id',
  'leadgen_id',
  'external_id',
  'ad_id',
  'adset_id',
  'adgroup_id',
  'form_id',
  'created_time',
  'campaign_id',
])

const STANDARD_FIELD_LABELS: Record<string, string> = {
  full_name: 'Full name',
  first_name: 'First name',
  last_name: 'Last name',
  phone: 'Phone',
  phone_number: 'Phone',
  email: 'Email',
  city: 'City',
  country: 'Country',
}

function asRecord(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return null
  return value as Record<string, unknown>
}

function formatValues(values: unknown): string {
  if (Array.isArray(values)) {
    return values
      .map((v) => String(v ?? '').trim())
      .filter(Boolean)
      .join(', ')
  }
  const s = String(values ?? '').trim()
  return s
}

function looksLikeHumanQuestion(raw: string): boolean {
  const s = raw.trim()
  if (!s) return false
  if (s.includes(' ') || s.includes('?')) return true
  return /[^\u0000-\u007f]/.test(s)
}

function humanizeFieldName(raw: string): string {
  return raw.replace(/[_]+/g, ' ').replace(/\s+/g, ' ').trim()
}

function shouldSkipName(name: string): boolean {
  const key = name.trim().toLowerCase()
  if (!key) return true
  if (SKIP_NAMES.has(key)) return true
  if (key.startsWith('utm')) return true
  return false
}

function lookupStoredLabel(
  name: string,
  row: Record<string, unknown>,
  labels: Record<string, unknown> | null,
): string | null {
  const fromRow = String(row.label ?? row.question ?? '').trim()
  if (fromRow && fromRow.toLowerCase() !== name.toLowerCase()) return fromRow
  if (fromRow && looksLikeHumanQuestion(fromRow)) return fromRow
  if (labels) {
    const mapped = labels[name] ?? labels[name.toLowerCase()]
    const s = String(mapped ?? '').trim()
    if (s) return s
  }
  return fromRow || null
}

function resolveLabel(name: string, stored: string | null): string {
  if (stored && (looksLikeHumanQuestion(stored) || stored.toLowerCase() !== name.toLowerCase())) {
    return stored
  }
  const standard = STANDARD_FIELD_LABELS[name.toLowerCase()]
  if (standard) return standard
  if (looksLikeHumanQuestion(name)) return name.replace(/[_]+/g, ' ').trim()
  return stored || humanizeFieldName(name)
}

/** Meta / form answers — human question text, not field_code. */
export function leadIntakeFormAnswerRows(lead: Lead | null | undefined): LeadIntakeFormAnswerRow[] {
  const n = asRecord(lead?.normalized)
  const raw = n?.field_answers
  if (!Array.isArray(raw)) return []
  const labels = asRecord(n?.form_question_labels_v1)
  const out: LeadIntakeFormAnswerRow[] = []
  const seen = new Set<string>()
  for (const item of raw) {
    const row = asRecord(item)
    if (!row) continue
    const name = String(row.name ?? '').trim()
    if (shouldSkipName(name)) continue
    const value = formatValues(row.values)
    if (!value) continue
    const key = name.toLowerCase()
    if (seen.has(key)) continue
    seen.add(key)
    const stored = lookupStoredLabel(name, row, labels)
    out.push({ name, label: resolveLabel(name, stored), value })
  }
  return out
}
