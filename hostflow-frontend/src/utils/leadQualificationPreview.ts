/**
 * Shared reader for `normalized.lead_qualification_preview_v1` (Slice 2 / assisted-automatic fit snapshot).
 */

export type LeadQualificationPreviewV1 = {
  suggested_vacancy_id?: string | null
  fit_status?: string | null
  fit_reasons?: string[]
  blocked_auto_convert?: boolean
  evaluated_at?: string | null
}

export function readLeadQualificationPreview(normalized: unknown): LeadQualificationPreviewV1 | null {
  if (!normalized || typeof normalized !== 'object' || Array.isArray(normalized)) return null
  const raw = (normalized as Record<string, unknown>).lead_qualification_preview_v1
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return null
  const o = raw as Record<string, unknown>
  const fit_reasons = Array.isArray(o.fit_reasons)
    ? o.fit_reasons.map((x) => String(x)).filter(Boolean)
    : []
  return {
    suggested_vacancy_id: o.suggested_vacancy_id != null ? String(o.suggested_vacancy_id) : null,
    fit_status: o.fit_status != null ? String(o.fit_status) : null,
    fit_reasons,
    blocked_auto_convert: Boolean(o.blocked_auto_convert),
    evaluated_at: o.evaluated_at != null ? String(o.evaluated_at) : null,
  }
}

/** Translate `fit_reasons` codes (`reason:detail`) using `app.leads.qualification.reasons.*`. */
export function formatQualificationReasonLabel(code: string, t: (k: string) => string): string {
  const idx = code.indexOf(':')
  const base = idx === -1 ? code : code.slice(0, idx)
  const detail = idx === -1 ? '' : code.slice(idx + 1)
  const key = `app.leads.qualification.reasons.${base}`
  const translated = t(key)
  if (translated === key) {
    return code
  }
  return detail ? `${translated} (${detail})` : translated
}
