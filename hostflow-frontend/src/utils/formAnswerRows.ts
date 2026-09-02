export type FormAnswerRow = {
  name: string
  label: string
  value: string
}

export type FormAnswerSource = {
  fieldAnswers?: unknown
  additionalAnswers?: unknown
  labels?: unknown
  payload?: unknown
  contactFallback?: Record<string, unknown> | null
  /** Applications: questions only — hide contact identity, ads, links. */
  questionnaireOnly?: boolean
}

/** Meta ads / Graph attribution / Messenger links — not candidate or client answers. */
const SKIP_NAMES = new Set([
  'id',
  'lead_id',
  'leadgen_id',
  'external_id',
  'ad_id',
  'ad_name',
  'adset_id',
  'adset_name',
  'ad_set_id',
  'ad_set_name',
  'adgroup_id',
  'adgroup_name',
  'ad_group_id',
  'ad_group_name',
  'form_id',
  'form_name',
  'created_time',
  'campaign_id',
  'campaign_name',
  'page_id',
  'page_name',
  'created_at',
  'is_organic',
  'is_organic_lead',
  'platform',
  'publisher_platform',
  'placement',
  'inbox_url',
  'messenger',
  'retailer_item_id',
])

const CONTACT_IDENTITY_NAMES = new Set([
  'full_name',
  'first_name',
  'last_name',
  'phone',
  'phone_number',
  'email',
  'work_email',
])

function canonicalAnswerName(name: string): string {
  return name.trim().toLowerCase().replace(/[\s-]+/g, '_')
}

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

const CONTACT_FALLBACK_KEYS = ['full_name', 'first_name', 'last_name', 'phone', 'phone_number', 'email', 'city', 'country']

function asRecord(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return null
  return value as Record<string, unknown>
}

function formatValues(values: unknown): string {
  if (Array.isArray(values)) {
    return values
      .map((v) => maybeHumanizeAnswer(String(v ?? '').trim()))
      .filter(Boolean)
      .join(', ')
  }
  return maybeHumanizeAnswer(String(values ?? '').trim())
}

function sentenceCase(raw: string): string {
  const s = raw.trim()
  if (!s) return s
  return s.charAt(0).toUpperCase() + s.slice(1)
}

function looksLikeStructuredValue(raw: string): boolean {
  if (raw.includes('@')) return true
  if (/^https?:\/\//i.test(raw)) return true
  if (/^\+?\d[\d\s().-]{5,}$/.test(raw)) return true
  return false
}

function maybeHumanizeAnswer(raw: string): string {
  if (!raw) return ''
  if (looksLikeStructuredValue(raw)) return raw
  const humanized = !raw.includes('_') || raw.includes(' ') ? raw : humanizeFieldName(raw)
  return sentenceCase(humanized)
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

function shouldSkipName(name: string, questionnaireOnly: boolean): boolean {
  const key = canonicalAnswerName(name)
  if (!key) return true
  if (SKIP_NAMES.has(key)) return true
  if (key.startsWith('utm')) return true
  if (key.endsWith('_url')) return true
  if (questionnaireOnly && CONTACT_IDENTITY_NAMES.has(key)) return true
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
    return sentenceCase(humanizeFieldName(stored))
  }
  const standard = STANDARD_FIELD_LABELS[name.toLowerCase()]
  if (standard) return standard
  if (looksLikeHumanQuestion(name)) return sentenceCase(humanizeFieldName(name))
  return sentenceCase(stored || humanizeFieldName(name))
}

function rowValue(row: Record<string, unknown>): string {
  if (row.values != null) return formatValues(row.values)
  if (row.value != null) return formatValues(row.value)
  if (row.answers != null) return formatValues(row.answers)
  return ''
}

function collectFieldDataArrays(payload: unknown): Record<string, unknown>[] {
  const out: Record<string, unknown>[] = []
  const pushList = (raw: unknown) => {
    if (!Array.isArray(raw)) return
    for (const item of raw) {
      const row = asRecord(item)
      if (row) out.push(row)
    }
  }

  const rec = asRecord(payload)
  if (!rec) return out
  pushList(rec.field_data)

  const entry = Array.isArray(rec.entry) ? asRecord(rec.entry[0]) : null
  const change = entry && Array.isArray(entry.changes) ? asRecord(entry.changes[0]) : null
  const value = asRecord(change?.value)
  if (value) pushList(value.field_data)

  return out
}

function pushAnswer(
  out: FormAnswerRow[],
  seen: Set<string>,
  name: string,
  value: string,
  stored: string | null,
  questionnaireOnly: boolean,
): void {
  if (shouldSkipName(name, questionnaireOnly) || !value) return
  const key = name.toLowerCase()
  if (seen.has(key)) return
  seen.add(key)
  out.push({ name, label: resolveLabel(name, stored), value })
}

/** Form Q&A from Application (or any projected lists). No Lead type. */
export function formAnswerRowsFromSources(source: FormAnswerSource): FormAnswerRow[] {
  const labels = asRecord(source.labels)
  const questionnaireOnly = Boolean(source.questionnaireOnly)
  const out: FormAnswerRow[] = []
  const seen = new Set<string>()

  const ingestAnswerList = (raw: unknown) => {
    if (!Array.isArray(raw)) return
    for (const item of raw) {
      const row = asRecord(item)
      if (!row) continue
      const name = String(row.name ?? row.key ?? '').trim()
      const value = rowValue(row)
      const stored = lookupStoredLabel(name, row, labels)
      pushAnswer(out, seen, name, value, stored, questionnaireOnly)
    }
  }

  ingestAnswerList(source.fieldAnswers)
  ingestAnswerList(source.additionalAnswers)
  ingestAnswerList(collectFieldDataArrays(source.payload))

  if (out.length === 0 && source.contactFallback && !questionnaireOnly) {
    for (const key of CONTACT_FALLBACK_KEYS) {
      const value = formatValues(source.contactFallback[key])
      pushAnswer(out, seen, key, value, lookupStoredLabel(key, {}, labels), false)
    }
  }

  return out
}
