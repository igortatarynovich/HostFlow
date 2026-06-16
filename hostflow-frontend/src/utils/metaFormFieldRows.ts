/**
 * PR-1: merge Meta form field names + sample values for the human field table in Meta Leads admin.
 */

export type MetaFormFieldMappingRow = {
  sourceText: string
  target: string
}

export type MetaFormFieldRow = {
  /** Normalized lowercase key used for matching rules. */
  name: string
  /** Display label (original casing when known). */
  displayName: string
  sampleValue: string | null
  mapped: boolean
  /** Target from mapping rules when mapped. */
  target: string | null
}

export function mappingRowCoversSource(row: MetaFormFieldMappingRow, key: string): boolean {
  const nk = key.trim().toLowerCase()
  if (!nk) return false
  const parts = row.sourceText
    .split(',')
    .map((s) => s.trim().toLowerCase())
    .filter(Boolean)
  return parts.includes(nk)
}

function resolveTargetForSource(name: string, rows: MetaFormFieldMappingRow[]): string | null {
  for (const row of rows) {
    if (mappingRowCoversSource(row, name)) {
      const t = row.target.trim()
      if (t) return t
    }
  }
  return null
}

/** First non-empty value from Meta field_data in a stored webhook payload preview JSON. */
export function collectFieldEntriesFromMetaPayloadPreview(json: string): Record<string, string> {
  const out: Record<string, string> = {}
  try {
    const root = JSON.parse(json) as Record<string, unknown>
    const entry = (Array.isArray(root.entry) ? root.entry[0] : null) as Record<string, unknown> | null
    const changes = entry && Array.isArray(entry.changes) ? (entry.changes[0] as Record<string, unknown>) : null
    const value = (changes?.value ?? root) as Record<string, unknown>
    const fieldData = value?.field_data
    if (!Array.isArray(fieldData)) return out
    for (const item of fieldData) {
      if (!item || typeof item !== 'object') continue
      const rawName = String((item as Record<string, unknown>).name ?? '').trim()
      if (!rawName) continue
      const key = rawName.toLowerCase()
      const values = (item as Record<string, unknown>).values
      let sample = ''
      if (Array.isArray(values) && values.length > 0) {
        sample = values
          .map((v) => String(v ?? '').trim())
          .filter(Boolean)
          .join(', ')
      }
      if (sample && !out[key]) out[key] = sample
      else if (!out[key]) out[key] = sample
    }
  } catch {
    // ignore invalid preview JSON
  }
  return out
}

export function collectRawFieldNamesFromNormalizedPreview(json: string): string[] {
  const out = new Set<string>()
  try {
    const o = JSON.parse(json) as unknown
    if (!o || typeof o !== 'object' || Array.isArray(o)) return []
    const raw = (o as Record<string, unknown>).raw_field_names
    if (!Array.isArray(raw)) return []
    for (const item of raw) {
      const s = String(item ?? '')
        .trim()
        .toLowerCase()
      if (s) out.add(s)
    }
  } catch {
    // ignore
  }
  return [...out]
}

export type BuildMetaFormFieldRowsInput = {
  graphFields: Array<{ name: string; value_preview?: string | null }>
  incomingPayloads: string[]
  incomingNormalized: string[]
  mappingRows: MetaFormFieldMappingRow[]
}

/**
 * Merge field names from Graph, incoming payloads, and raw_field_names.
 * Value priority: Graph value_preview → parsed field_data → null.
 */
export function buildMetaFormFieldRows(input: BuildMetaFormFieldRowsInput): MetaFormFieldRow[] {
  const byName = new Map<string, { displayName: string; sampleValue: string | null }>()

  const ensure = (name: string, displayName?: string) => {
    const key = name.trim().toLowerCase()
    if (!key) return
    const existing = byName.get(key)
    const label = displayName?.trim() || existing?.displayName || name.trim() || key
    if (!existing) {
      byName.set(key, { displayName: label, sampleValue: null })
    } else if (displayName?.trim()) {
      existing.displayName = displayName.trim()
    }
  }

  const setSample = (name: string, value: string | null | undefined, priority: 'low' | 'high') => {
    const key = name.trim().toLowerCase()
    if (!key) return
    const v = value != null ? String(value).trim() : ''
    if (!v) return
    ensure(key, name)
    const row = byName.get(key)!
    if (priority === 'high' || !row.sampleValue) row.sampleValue = v
  }

  for (const payload of input.incomingPayloads) {
    const entries = collectFieldEntriesFromMetaPayloadPreview(payload)
    for (const [key, val] of Object.entries(entries)) {
      ensure(key, key)
      setSample(key, val, 'low')
    }
  }

  for (const norm of input.incomingNormalized) {
    for (const key of collectRawFieldNamesFromNormalizedPreview(norm)) {
      ensure(key, key)
    }
  }

  for (const field of input.graphFields) {
    const key = String(field.name ?? '')
      .trim()
      .toLowerCase()
    if (!key) continue
    ensure(key, field.name)
    setSample(key, field.value_preview, 'high')
  }

  const rows: MetaFormFieldRow[] = []
  for (const [name, meta] of byName.entries()) {
    const target = resolveTargetForSource(name, input.mappingRows)
    rows.push({
      name,
      displayName: meta.displayName,
      sampleValue: meta.sampleValue,
      mapped: target != null,
      target,
    })
  }

  rows.sort((a, b) => a.displayName.localeCompare(b.displayName, undefined, { sensitivity: 'base' }))
  return rows
}
